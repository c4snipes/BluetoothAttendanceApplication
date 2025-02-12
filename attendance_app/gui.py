import os
import re
import threading
import logging
import requests
import tkinter as tk
from tkinter import TclError, ttk, messagebox, filedialog
from PIL import Image, ImageTk
from io import BytesIO
from datetime import datetime

from attendance import AttendanceManager
from scanner import Scanner
from export import Disseminate
from import_att import ImportApp
from html_parse import is_valid_url
from widgets import (
    create_notebook,
    create_settings_tab,
    create_class_tab_widgets_with_photos,
    create_scrollable_frame,
    bind_tab_dragging
)

class AttendanceApp:
    """
    The main GUI application class. Creates tabs for each class, a settings tab, and a logs tab.
    Manages scanning, attendance updates, and user interactions.
    """

    def __init__(self, master: tk.Tk):
        """
        Initialize the main window and all sub-components.
        :param master: The root Tk window
        """
        self.master = master
        self.master.title("Bluetooth-Based Attendance System")
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)  # confirm on close
        self.master.resizable(True, True)  # allow diagonal resizing

        # Cache for PhotoImages (avoids reloading them each time)
        self.image_cache = {}

        # Image cache folder
        self.image_cache_dir = os.path.join(os.getcwd(), 'image_cache')
        if not os.path.exists(self.image_cache_dir):
            os.makedirs(self.image_cache_dir, exist_ok=True)

        # Bluetooth scanning state
        self.scan_count = 0
        self.found_devices = {}  # { mac_upper: {...info...}, ...}
        self._drag_data = {"tab_index": None, "x": 0, "y": 0}

        # Initialize the core manager
        self.attendance_manager = AttendanceManager()

        # Create importer (HTML -> attendance) and exporter (attendance -> CSV)
        self.importer = ImportApp(self.attendance_manager, master=self.master, parent_gui=self)
        self.disseminate = Disseminate(self.master, self.attendance_manager)

        # The Scanner object (background thread scanning)
        self.scanner = Scanner(callback=self.handle_scan_results)
        self.scanning = False

        # Create Notebook for tabbed UI
        self.notebook = create_notebook(self.master)

        # Store references to class tab widgets
        self.class_widgets = {}

        # Create tabs for existing classes, plus settings & logs
        self.create_class_tabs()

        # Set up logging to appear in a GUI text widget
        self.setup_gui_logging()

        # Enable tab drag-and-drop reordering
        bind_tab_dragging(self.notebook, self.on_tab_press, self.on_tab_motion, self.on_tab_release)

    def create_class_tabs(self):
        """
        Create a tab for every existing class, plus a Settings tab and a Logs tab.
        """
        # 1) Create a tab for each class
        for class_name in self.attendance_manager.classes.keys():
            self.create_class_tab(class_name)

        # 2) Create the Settings tab
        self.settings_widgets = create_settings_tab(
            self.notebook,
            self.attendance_manager.get_class_codes(),
            list(self.attendance_manager.classes.keys())
        )
        self.connect_settings_actions()

        # 3) Create the Logs tab
        self.create_logs_tab()

    def create_class_tab(self, class_name: str):
        """
        Add a new tab for the given class, including Present/Absent frames.
        :param class_name: The name of the class to create a tab for.
        """
        class_frame = ttk.Frame(self.notebook)

        (
            button_frame,
            present_frame_container,
            absent_frame_container,
            add_student_button,
            scan_toggle_button,
            interval_var,
            rssi_var,
            quit_button,
            export_button
        ) = create_class_tab_widgets_with_photos(class_frame, self.attendance_manager)

        # Make these frames scrollable
        present_frame = create_scrollable_frame(present_frame_container)
        absent_frame = create_scrollable_frame(absent_frame_container)

        # Store references
        self.class_widgets[class_name] = {
            'present_frame': present_frame,
            'absent_frame': absent_frame,
            'add_student_button': add_student_button,
            'scan_toggle_button': scan_toggle_button,
            'interval_var': interval_var,
            'rssi_var': rssi_var,
            'quit_button': quit_button,
            'export_button': export_button,
            'present_student_widgets': {},
            'absent_student_widgets': {},
            'tab_frame': class_frame
        }

        # Update the scan button text based on whether scanning is currently active
        if self.scanning:
            scan_toggle_button.config(text="Stop Scanning")
        else:
            scan_toggle_button.config(text="Start Scanning")

        # Wire up buttons
        add_student_button.config(command=lambda: self.add_student_dialog(class_name))
        scan_toggle_button.config(command=self.toggle_scanning)
        export_button.config(command=lambda: self.disseminate.export_attendance(class_name))
        quit_button.config(command=lambda: self.on_closing())

        # When user changes scan interval, update both the scanner and attendance_manager
        def on_interval_change(*_):
            val_str = interval_var.get()
            parts = val_str.split()
            if parts:
                try:
                    new_int = int(parts[0])  # e.g. "10 seconds" => 10
                    self.scanner.update_scan_interval(new_int)
                    self.attendance_manager.set_scan_interval(new_int)
                    logging.info(f"Scan interval updated to {new_int} seconds.")
                except ValueError:
                    logging.warning(f"Ignored invalid scan interval entry: {val_str}")
        interval_var.trace_add('write', on_interval_change)

        # When user changes RSSI threshold, update the scanner
        def on_rssi_change(*_):
            rssi_str = rssi_var.get()  # e.g. "Medium (> -70 dBm)"
            match = re.search(r'>\s*(-\d+)\s*dBm', rssi_str)
            if match:
                try:
                    new_thresh = int(match.group(1))
                    self.scanner.update_rssi_threshold(new_thresh)
                except ValueError:
                    logging.warning(f"Could not parse RSSI threshold from: {rssi_str}")
        rssi_var.trace_add('write', on_rssi_change)

        # Initially populate present/absent
        self.update_student_lists(class_name)

        # Finally, add the tab to the notebook
        self.notebook.add(class_frame, text=class_name)

    def connect_settings_actions(self):
        """
        Wire up callbacks for the controls in the Settings tab
        (add class, delete class, import, etc.).
        """
        w = self.settings_widgets
        delete_button = w['delete_button']
        theme_combo = w['theme_combo']
        add_class_button = w['add_class_button']
        class_entry = w['class_entry']
        add_code_button = w['add_code_button']
        new_code_entry = w['new_code_entry']
        valid_class_codes_var = w['valid_class_codes_var']
        import_html_button = w['import_html_button']
        export_all_button = w['export_all_button']
        class_combo = w['class_combo']
        delete_class_button = w['delete_class_button']

        delete_button.config(command=self.delete_database)
        theme_combo.bind('<<ComboboxSelected>>', lambda e: self.change_theme(theme_combo.get()))
        add_class_button.config(command=lambda: self.add_class(class_entry.get()))
        add_code_button.config(command=lambda: self.add_class_code(new_code_entry.get(), valid_class_codes_var))
        import_html_button.config(command=self.import_html_action)
        export_all_button.config(command=self.disseminate.export_all_classes)
        delete_class_button.config(command=lambda: self.delete_class(class_combo.get()))

    def delete_database(self):
        """
        Prompt user to confirm, then purge all data in the manager (and image cache).
        """
        if messagebox.askyesno("Confirm Deletion", "This will remove all data. Proceed?"):
            try:
                self.attendance_manager.purge_database()
                # Remove all class tabs from the notebook
                for cname in list(self.class_widgets.keys()):
                    frame = self.class_widgets[cname]['tab_frame']
                    self.notebook.forget(frame)
                    del self.class_widgets[cname]
                # Clear the class dropdown
                self.settings_widgets['class_combo']['values'] = []
                messagebox.showinfo("Deleted", "All data removed.")
                logging.info("Database purged.")
            except Exception as e:
                messagebox.showerror("Error", str(e))
                logging.error(f"Error purging database: {e}")

    def delete_class(self, class_name: str):
        """
        Remove a specific class from the database and its corresponding tab.
        :param class_name: Name of class to remove
        """
        if not class_name:
            messagebox.showwarning("No Class", "Select a class to delete.")
            return
        if messagebox.askyesno("Confirm", f"Delete class '{class_name}'?"):
            try:
                tab_frame = self.class_widgets[class_name]['tab_frame']
                self.notebook.forget(tab_frame)
                del self.class_widgets[class_name]

                self.attendance_manager.remove_class(class_name)

                # Update the combo box to remove the class
                class_names = list(self.attendance_manager.classes.keys())
                self.settings_widgets['class_combo']['values'] = class_names
                messagebox.showinfo("Deleted", f"Class '{class_name}' removed.")
            except Exception as ex:
                logging.error(f"delete_class error: {ex}")
                messagebox.showerror("Error", str(ex))

    def add_class(self, class_name: str):
        """
        Prompt the manager to create a new class, then create a corresponding tab.
        :param class_name: Name of new class
        """
        class_name = class_name.strip()
        if class_name:
            try:
                self.attendance_manager.register_class(class_name)
                self.create_class_tab(class_name)
                messagebox.showinfo("Class Added", f"'{class_name}' created.")
                class_names = list(self.attendance_manager.classes.keys())
                self.settings_widgets['class_combo']['values'] = class_names
                self.settings_widgets['class_entry'].delete(0, tk.END)
            except Exception as e:
                messagebox.showerror("Error", str(e))
        else:
            messagebox.showwarning("Empty", "Class name cannot be empty.")
            self.settings_widgets['class_entry'].focus_set()

    def add_class_code(self, code: str, valid_class_codes_var: tk.StringVar):
        """
        Add a new code (e.g. 'CSCI') to the known list of valid codes.
        :param code: The code to add
        :param valid_class_codes_var: The stringVar we update to display codes
        """
        code = code.strip()
        if code:
            try:
                self.attendance_manager.register_class_code(code)
                updated_codes = self.attendance_manager.get_class_codes()
                valid_class_codes_var.set(", ".join([c for c in updated_codes if c.isalpha()]))
                messagebox.showinfo("Added", f"Code '{code}' added.")
                self.settings_widgets['new_code_entry'].delete(0, tk.END)
            except ValueError as ve:
                messagebox.showwarning("Warning", str(ve))
        else:
            messagebox.showwarning("Empty", "Class code is empty.")

    def import_html_action(self):
        """
        Trigger HTML import in a background thread to avoid blocking the GUI.
        """
        logging.info("User clicked 'Import HTML'. Starting background import...")
        self.importer.import_html_action()

    def change_theme(self, theme_name: str):
        """
        Switch ttk theme (look & feel).
        """
        style = ttk.Style()
        try:
            style.theme_use(theme_name)
            logging.info(f"Theme changed to {theme_name}")
        except Exception as e:
            logging.error(f"Error changing theme: {e}")

    def toggle_scanning(self):
        """
        Start scanning if not already, or prompt user to force-quit if they want to stop.
        """
        if not self.scanning:
            # Start scanning
            self.scanning = True
            self.scanner.start_scanning()

            # Update button text on all class tabs
            for cname, cw in self.class_widgets.items():
                cw['scan_toggle_button'].config(text="Stop Scanning")

            logging.info("Scanning started.")
        else:
            # If the user tries to stop scanning, show a message about force-quitting
            answer = messagebox.askyesno(
                "Cannot Stop Scanning",
                "We cannot safely stop scanning after it has started.\n\n"
                "Do you want to force quit the application now?\n"
                "(All data has been saved automatically.)"
            )
            if answer:
                logging.info("User chose to force quit instead of stopping scanning.")
                self.on_closing()
            else:
                logging.info("User canceled the force-quit option; continuing to scan.")

    def handle_scan_results(self, found_devices: dict):
        """
        Called from the scanner background thread. We schedule a main-thread update
        so we don't modify GUI elements off the main thread.
        """
        self.master.after(0, self._on_scan_results, found_devices)

    def _on_scan_results(self, found_devices: dict):
        """
        Runs on the main thread to update internal data and refresh the GUI with new scan results.
        Now filters out blacklisted MAC addresses.
        """
        try:
            self.scan_count += 1
            # Filter out devices in the blacklist:
            blacklisted = self.attendance_manager.get_blacklisted_macs()
            filtered_devices = {mac: info for mac, info in found_devices.items() if mac not in blacklisted}
            self.found_devices = filtered_devices
            logging.info(f"Handling scan results, scan_count={self.scan_count}")
            self.attendance_manager.update_from_scan(filtered_devices)
            # Refresh each class tab to reflect updated attendance
            for cname in self.class_widgets.keys():
                self.update_student_lists(cname)
        except Exception as e:
            logging.error(f"_on_scan_results error: {e}")

    def update_student_lists(self, class_name: str):
        """
        Rebuild the Present/Absent frames for the specified class, based on the manager's data.
        """
        cw = self.class_widgets[class_name]
        present_frame = cw['present_frame']
        absent_frame = cw['absent_frame']

        # Clear existing widgets from each frame
        for child in present_frame.winfo_children():
            child.destroy()
        for child in absent_frame.winfo_children():
            child.destroy()

        cw['present_student_widgets'].clear()
        cw['absent_student_widgets'].clear()

        # Retrieve all students, figure out who is present
        all_students = self.attendance_manager.get_all_students(class_name)
        present_students = self.attendance_manager.get_present_students(class_name)

        # Recreate widgets for each student
        for sid, sdata in all_students.items():
            if sid in present_students:
                container = present_frame
                dict_key = 'present_student_widgets'
            else:
                container = absent_frame
                dict_key = 'absent_student_widgets'

            widget = self.create_student_widget(container, class_name, sid, sdata)
            cw[dict_key][sid] = widget

    def create_student_widget(self, parent_frame: ttk.Frame, class_name: str, student_id: str, student_data: dict):
        """
        Creates a single row showing the student's photo, name, assigned MAC, presence controls, etc.
        """
        student_frame = ttk.Frame(parent_frame)
        student_frame.pack(fill="x", padx=5, pady=5)

        # Photo
        photo_label = tk.Label(student_frame)
        photo_label.grid(row=0, column=0, rowspan=2, padx=5, pady=5, sticky="nw")
        photo_img = self.get_student_image(student_data, photo_label)
        photo_label.config(image=photo_img)  # type: ignore
        photo_label.image = photo_img        # type: ignore

        info_text = f"{student_data.get('name','Unknown')} (ID: {student_id})"
        info_label = ttk.Label(student_frame, text=info_text, wraplength=200)
        info_label.grid(row=0, column=1, sticky="w")

        # Show assigned MAC(s)
        assigned_macs = self.attendance_manager.list_macs_for_student(class_name, student_id)
        assigned_str = ", ".join(assigned_macs) if assigned_macs else "Unassigned"
        assigned_label = ttk.Label(student_frame, text=f"Assigned: {assigned_str}")
        assigned_label.grid(row=1, column=1, sticky="w")

        # Controls
        controls_frame = ttk.Frame(student_frame)
        controls_frame.grid(row=0, column=2, rowspan=2, padx=5, pady=5, sticky="ne")

        # Show the device dropdown for quick assignment
        self.show_device_dropdown(controls_frame, class_name, student_id)

        # Mark Present/Absent button
        present_students = self.attendance_manager.get_present_students(class_name)
        if student_id in present_students:
            mark_btn = ttk.Button(
                controls_frame,
                text="Mark Absent",
                command=lambda: self.mark_student_absent(class_name, student_id)
            )
        else:
            mark_btn = ttk.Button(
                controls_frame,
                text="Mark Present",
                command=lambda: self.mark_student_present(class_name, student_id)
            )
        mark_btn.pack(fill="x", pady=2)

        # Delete button
        del_btn = ttk.Button(
            controls_frame,
            text="✕",
            width=3,
            command=lambda: self.delete_student_dialog(class_name, student_id)
        )
        del_btn.pack(pady=2)

        return student_frame

    def show_device_dropdown(self, parent_frame: ttk.Frame, class_name: str, student_id: str):
        """
        Create a Combobox listing discovered devices (with scan counts) as well as already assigned MACs.
        Selecting one assigns the MAC to the student.
        """
        # Start with the found devices from the scanner:
        device_list = list(self.found_devices.items())
        device_list.sort(key=lambda x: x[1]["scan_count"])
        display_map = {}
        for mac, info in device_list:
            short_mac = mac[-8:]
            count = info["scan_count"]
            # Check if the MAC is already assigned (to any student)
            is_assigned = False
            with self.attendance_manager.lock:
                for cname, cdata in self.attendance_manager.classes.items():
                    for sid, macs in cdata['student_mac_addresses'].items():
                        if mac.upper() in macs:
                            is_assigned = True
                            break
                    if is_assigned:
                        break
            label_text = f"{short_mac} (Count: {count})"
            if is_assigned:
                label_text += " - assigned"
            display_map[label_text] = mac

        # Also include any MACs already assigned to THIS student that might not be in found_devices.
        assigned_macs = self.attendance_manager.list_macs_for_student(class_name, student_id)
        for mac, count in assigned_macs.items():
            label = f"{mac[-8:]} (Count: {count}) - assigned"
            display_map[label] = mac

        var = tk.StringVar()
        combo = ttk.Combobox(
            parent_frame,
            textvariable=var,
            values=list(display_map.keys()),
            state="readonly",
            width=20
        )
        combo.pack(pady=2)

        def on_select(_evt=None):
            chosen = var.get().strip()
            if chosen not in display_map:
                messagebox.showwarning("No Match", "Please select a valid device from the dropdown.")
                return
            real_mac = display_map[chosen]
            # If the chosen MAC came from found_devices, get its scan_count; otherwise, use stored count.
            if real_mac in self.found_devices:
                count = self.found_devices[real_mac]["scan_count"]
            else:
                # fall back to 0 if not currently found
                count = 0
            try:
                self.attendance_manager.assign_mac_to_student(class_name, student_id, real_mac, scan_count=count)
                sdata = self.attendance_manager.classes[class_name]['students'].get(student_id, {})
                st_name = sdata.get('name', f'ID: {student_id}')
                messagebox.showinfo("Assigned", f"Assigned '{real_mac}' (Count: {count}) to {st_name} (ID: {student_id}).")
            except Exception as e:
                logging.error(f"Error assigning MAC '{real_mac}' to {student_id}: {e}")
                messagebox.showerror("Error", str(e))
            finally:
                self.update_student_lists(class_name)

        combo.bind("<<ComboboxSelected>>", on_select)
        combo.bind("<Return>", on_select)

    def mark_student_present(self, class_name: str, student_id: str):
        """
        Manually mark a student present, overriding scanning.
        """
        try:
            self.attendance_manager.mark_as_present(class_name, student_id)
            logging.info(f"Manually marked {student_id} present in {class_name}.")
            self.update_student_lists(class_name)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def mark_student_absent(self, class_name: str, student_id: str):
        """
        Manually mark a student absent, overriding scanning.
        """
        try:
            self.attendance_manager.mark_as_absent(class_name, student_id)
            logging.info(f"Manually marked {student_id} absent in {class_name}.")
            self.update_student_lists(class_name)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_student_dialog(self, class_name: str, student_id: str):
        """
        Ask user confirmation, then remove a student from the class if yes.
        """
        st_data = self.attendance_manager.classes[class_name]['students'].get(student_id, {})
        st_name = st_data.get('name', 'Unknown')
        if messagebox.askyesno(
            "Delete Student",
            f"Remove '{st_name}' (ID: {student_id}) from '{class_name}'?"
        ):
            try:
                self.attendance_manager.remove_student(class_name, student_id)
                self.delete_student_image(student_id)
                self.update_student_lists(class_name)
                messagebox.showinfo("Deleted", f"Student '{st_name}' removed.")
            except Exception as e:
                messagebox.showerror("Error", str(e))
                logging.error(f"Error deleting student: {e}")

    def delete_student_image(self, student_id: str):
        """
        Remove the student's cached image file if it exists.
        """
        sid = "".join(c for c in student_id if c.isalnum())
        path = os.path.join(self.image_cache_dir, f"{sid}.png")
        if os.path.exists(path):
            try:
                os.remove(path)
                logging.info(f"Deleted cached image for '{student_id}'.")
            except Exception as e:
                logging.error(f"Failed removing image for {student_id}: {e}")

    def get_student_image(self, student_data: dict, label_widget: tk.Label, size=(100,100)):
        """
        Return a PhotoImage for the student's photo. If not cached locally,
        attempt to download from 'photo_url'. If that fails, use placeholder.
        """
        sid = student_data.get('student_id', 'unknown')
        if sid in self.image_cache:
            return self.image_cache[sid]

        cache_file = os.path.join(self.image_cache_dir, f"{sid}.png")

        # Check local cache first
        if os.path.exists(cache_file):
            try:
                from PIL import Image, ImageTk
                with Image.open(cache_file) as img:
                    resized = img.resize(size, Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(resized)
                    self.image_cache[sid] = photo
                    return photo
            except Exception as e:
                logging.warning(f"Error loading cached image for '{sid}': {e}")

        # Attempt to download
        url = student_data.get('photo_url')
        if url and is_valid_url(url):
            try:
                resp = requests.get(url, timeout=5)
                resp.raise_for_status()
                from PIL import Image, ImageTk
                with Image.open(BytesIO(resp.content)) as img:
                    resized = img.resize(size, Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(resized)
                    # Cache both in memory and on disk
                    resized.save(cache_file, "PNG")
                    self.image_cache[sid] = photo
                    return photo
            except Exception as e:
                logging.error(f"Error downloading {sid} image: {e}")

        # If no valid image found, return placeholder
        return self.get_placeholder_image()

    def get_placeholder_image(self) -> ImageTk.PhotoImage:
        """
        Return a simple gray placeholder image used when a student's photo can't be loaded.
        """
        if hasattr(self, '_placeholder_image'):
            return self._placeholder_image
        from PIL import Image, ImageTk
        img = Image.new('RGB', (100,100), color='gray')
        self._placeholder_image = ImageTk.PhotoImage(img)
        return self._placeholder_image

    def on_closing(self):
        """
        Prompt user before closing, then shut down the scanner (if needed) and destroy the main window.
        """
        if messagebox.askokcancel("Quit", "Close application?"):
            if self.scanning:
                self.scanner.stop_scanning()
            self.master.destroy()

    #
    #  Draggable tabs logic
    #
    def on_tab_press(self, event):
        """
        Capture which tab is pressed for drag-and-drop reordering.
        """
        x, y = event.x, event.y
        try:
            idx = self.notebook.index(f"@{x},{y}")
            self._drag_data["tab_index"] = idx
        except TclError:
            self._drag_data["tab_index"] = None

    def on_tab_motion(self, event):
        """
        Handle dragging the tab to reorder.
        """
        x, y = event.x, event.y
        try:
            idx = self.notebook.index(f"@{x},{y}")
        except TclError:
            return
        if self._drag_data["tab_index"] is not None and idx != self._drag_data["tab_index"]:
            self.swap_tabs(self._drag_data["tab_index"], idx)
            self._drag_data["tab_index"] = idx

    def on_tab_release(self, event):
        """
        Clear drag data on release.
        """
        self._drag_data = {"tab_index": None}

    def swap_tabs(self, i: int, j: int):
        """
        Swap tab i with tab j in the notebook.
        """
        total = self.notebook.index("end")
        if i < 0 or j < 0 or i >= total or j >= total:
            return
        if i == j:
            return

        tab_id = self.notebook.tabs()[i]
        text = self.notebook.tab(tab_id, "text")
        content = self.notebook.nametowidget(tab_id)
        self.notebook.forget(i)
        if i < j:
            j -= 1
        self.notebook.insert(j, content)
        self.notebook.tab(content, text=text)

    def setup_gui_logging(self):
        """
        Redirect log messages into a text widget in the 'Logs' tab,
        so the user can see logs in the GUI.
        """
        if not hasattr(self, 'log_text_widget'):
            self.create_logs_tab()

        class TextHandler(logging.Handler):
            def __init__(self, text_widget: tk.Text):
                super().__init__()
                self.text_widget = text_widget

            def emit(self, record):
                msg = self.format(record)

                def append():
                    self.text_widget.config(state='normal')
                    self.text_widget.insert('end', msg + '\n')
                    self.text_widget.config(state='disabled')
                    self.text_widget.see('end')

                self.text_widget.after(0, append)

        handler = TextHandler(self.log_text_widget)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

    def create_logs_tab(self):
        """
        Create a tab to display log messages in a scrollable Text widget.
        """
        logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(logs_frame, text="Logs")

        self.log_text_widget = tk.Text(logs_frame, wrap='word', state='disabled', width=80, height=20)
        self.log_text_widget.pack(fill='both', expand=True)

    def add_student_dialog(self, class_name: str) -> None:
        """
        Show a dialog box to add a new student to the specified class.
        """
        logging.info(f"Opening Add Student dialog for class '{class_name}'.")
        dialog = tk.Toplevel(self.master)
        dialog.title(f"Add Student to {class_name}")
        dialog.geometry("400x280")
        dialog.grab_set()

        # Basic fields
        ttk.Label(dialog, text="Student Name:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        name_ent = ttk.Entry(dialog, width=30)
        name_ent.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(dialog, text="Student ID (Optional):").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        sid_ent = ttk.Entry(dialog, width=30)
        sid_ent.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(dialog, text="Photo URL (Optional):").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        url_ent = ttk.Entry(dialog, width=30)
        url_ent.grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(dialog, text="Device MAC (Optional):").grid(row=3, column=0, padx=10, pady=5, sticky="e")
        dev_var = tk.StringVar()
        dev_combo = ttk.Combobox(dialog, textvariable=dev_var, values=list(self.found_devices.keys()))
        dev_combo.grid(row=3, column=1, padx=10, pady=5)

        def refresh_devices():
            """
            Let the user refresh the list of recently found devices in the combobox.
            """
            dev_list = list(self.found_devices.keys())
            dev_combo['values'] = dev_list
            if dev_list:
                dev_var.set(dev_list[0])
            else:
                dev_var.set('')

        refresh_btn = ttk.Button(dialog, text="Refresh", command=refresh_devices)
        refresh_btn.grid(row=3, column=2, padx=5, pady=5)

        def on_submit():
            """
            Validate user input, then add the new student to the manager.
            """
            name = name_ent.get().strip()
            if not name:
                messagebox.showerror("Error", "Student name is required.")
                return

            sid = sid_ent.get().strip() or None
            url = url_ent.get().strip() or None
            dev = dev_var.get().strip() or None

            # If the user provided a URL, check if it's valid
            if url and not is_valid_url(url):
                if not messagebox.askyesno("Invalid URL", "Provided URL seems invalid. Continue without photo?"):
                    return
                url = None

            student = {
                'name': name,
                'student_id': sid,
                'photo_url': url,
                'device_address': dev
            }
            try:
                self.attendance_manager.add_student(class_name, student)
                self.update_student_lists(class_name)
                messagebox.showinfo("Added", f"Student '{name}' added to '{class_name}'.")
                dialog.destroy()
            except Exception as e:
                logging.error(f"Error adding student: {e}")
                messagebox.showerror("Error", str(e))

        submit_btn = ttk.Button(dialog, text="Add Student", command=on_submit)
        submit_btn.grid(row=4, column=0, columnspan=3, pady=10)

        # Center the dialog on screen
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

