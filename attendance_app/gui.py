# gui.py

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import logging
from io import BytesIO
import re
import requests
from attendance import AttendanceManager
from scanner import Scanner
from export import Disseminate
from import_att import ImportApp
import widgets
from html_parse import is_valid_url
from widgets import ToolTip

class AttendanceApp:
    def __init__(self, master):
        self.master = master
        master.title("Bluetooth-Based Attendance Application")
        master.geometry("1024x768")  # Set a default window size

        # Initialize AttendanceManager and Scanner
        self.attendance_manager = AttendanceManager()
        self.scanner = Scanner(callback=self.handle_scan_results)
        self.importer = ImportApp(self.attendance_manager)
        self.disseminate = Disseminate(self.master, self.attendance_manager)
        self.found_devices = {}
        self.scan_count = 0
        self.scanning = False  # Initialize scanning flag

        # Create the notebook (tabbed interface)
        self.notebook = widgets.create_notebook(master)

        # Setup centralized logging
        self.setup_gui_logging()

        # Initialize class tabs
        self.class_widgets = {}
        self.create_class_tabs()

        # Bind the close event
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_class_tabs(self):
        """Create tabs for each class."""
        for class_name in self.attendance_manager.classes.keys():
            self.create_class_tab(class_name)

        # Create settings tab and assign the widgets to `settings_widgets`
        self.settings_widgets = widgets.create_settings_tab(
            self.notebook,
            self.attendance_manager.get_valid_class_codes()
        )
        # Connect settings actions after `settings_widgets` has been assigned
        self.connect_settings_actions()

    def create_class_tab(self, class_name):
        class_frame = ttk.Frame(self.notebook)
        self.notebook.add(class_frame, text=class_name)

        # Use the widgets from widgets.py
        class_widgets_tuple = widgets.create_class_tab_widgets_with_photos(class_frame)

        # Unpack the widgets
        (
            button_frame,
            present_frame_container,
            absent_frame_container,
            import_button,
            add_student_button,
            scan_toggle_button,
            interval_var,
            rssi_var,
            quit_button,
            export_button,
        ) = class_widgets_tuple

        # Create scrollable frames for present and absent students
        present_frame = widgets.create_scrollable_frame(present_frame_container)
        absent_frame = widgets.create_scrollable_frame(absent_frame_container)

        # Store the widgets for later use
        self.class_widgets[class_name] = {
            'present_frame': present_frame,
            'absent_frame': absent_frame,
            'import_button': import_button,
            'add_student_button': add_student_button,
            'scan_toggle_button': scan_toggle_button,
            'interval_var': interval_var,
            'rssi_var': rssi_var,
            'quit_button': quit_button,
            'export_button': export_button,
            'present_student_widgets': {},
            'absent_student_widgets': {},
        }

        # Set the scan button text based on current scanning state
        if self.scanning:
            scan_toggle_button.config(text="Stop Scanning")
        else:
            scan_toggle_button.config(text="Start Scanning")

        # Connect button signals
        import_button.config(command=self.import_html_action)
        add_student_button.config(command=lambda: self.add_student_dialog(class_name))
        scan_toggle_button.config(command=self.toggle_scanning)
        export_button.config(command=lambda: self.disseminate.export_attendance(class_name))
        quit_button.config(command=self.on_closing)

        # Initialize interval and RSSI settings
        interval_var.trace_add('write', lambda *args: self.scanner.update_scan_interval(int(interval_var.get().split()[0])))
        rssi_var.trace_add('write', lambda *args: self.scanner.update_rssi_threshold(self.parse_rssi_value(rssi_var.get())))

        # Populate students
        self.update_student_lists(class_name)

    def connect_settings_actions(self):
        settings_widgets = self.settings_widgets
        delete_button = settings_widgets['delete_button']
        theme_combo = settings_widgets['theme_combo']
        add_class_button = settings_widgets['add_class_button']
        class_entry = settings_widgets['class_entry']
        add_code_button = settings_widgets['add_code_button']
        new_code_entry = settings_widgets['new_code_entry']
        valid_class_codes_var = settings_widgets['valid_class_codes_var']
        import_html_button = settings_widgets['import_html_button']
        export_all_button = settings_widgets['export_all_button']

        delete_button.config(command=self.delete_database)
        theme_combo.bind('<<ComboboxSelected>>', lambda event: widgets.change_theme(theme_combo.get()))
        add_class_button.config(command=lambda: self.add_class(class_entry.get()))
        add_code_button.config(command=lambda: self.add_class_code(new_code_entry.get(), valid_class_codes_var))
        export_all_button.config(command=self.disseminate.export_all_classes)
        import_html_button.config(command=self.import_html_action)

    def setup_gui_logging(self):
        """
        Configure logging to send log messages to the centralized Logs tab.
        """
        # Create Logs tab
        log_text = self.create_logs_tab()

        # Define a custom handler that appends to the centralized log_text widget
        class CentralizedGUIHandler(logging.Handler):
            def __init__(self, log_widget):
                super().__init__()
                self.log_widget = log_widget
                self.log_widget.configure(state='disabled')  # Make the widget read-only

            def emit(self, record):
                msg = self.format(record)
                self.log_widget.after(0, self.append_message, msg)

            def append_message(self, msg):
                self.log_widget.configure(state='normal')
                self.log_widget.insert(tk.END, msg + '\n')
                self.log_widget.configure(state='disabled')
                self.log_widget.see(tk.END)

        # Create the handler
        centralized_gui_handler = CentralizedGUIHandler(log_text)
        centralized_gui_handler.setLevel(logging.DEBUG)
        gui_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        centralized_gui_handler.setFormatter(gui_formatter)

        # Get the root logger and add handlers
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        # Remove existing handlers to prevent duplicate logs
        if logger.hasHandlers():
            logger.handlers.clear()

        # Add file handler
        file_handler = logging.FileHandler('application.log')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Add the centralized GUI handler
        logger.addHandler(centralized_gui_handler)

    def create_logs_tab(self):
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="Logs")

        log_text = tk.Text(log_frame, height=15, state='disabled', wrap='word')
        log_text.pack(fill='both', expand=True, padx=10, pady=10)

        return log_text

    def import_html_action(self):
        """Handle the action triggered by the 'Import HTML' button."""
        updated_classes = self.importer.import_html_action()
        for class_name in updated_classes:
            if class_name not in self.class_widgets:
                self.create_class_tab(class_name)
            self.update_student_lists(class_name)

    def toggle_scanning(self):
        """
        Toggle the scanning state between active and inactive.
        """
        if self.scanning:
            # Currently scanning; stop scanning
            self.scanner.stop_scanning()
            self.scanning = False
            logging.info("Scanning stopped by user.")
            # Update button text to "Start Scanning" for all class tabs
            for class_widget in self.class_widgets.values():
                class_widget['scan_toggle_button'].config(text="Start Scanning")
        else:
            # Currently not scanning; start scanning
            self.scanner.start_scanning()
            self.scanning = True
            logging.info("Scanning started by user.")
            # Update button text to "Stop Scanning" for all class tabs
            for class_widget in self.class_widgets.values():
                class_widget['scan_toggle_button'].config(text="Stop Scanning")

    def delete_database(self):
        """Delete the student database."""
        if messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete the student database? This action cannot be undone."):
            self.attendance_manager.delete_database()
            # Remove all class tabs
            for class_name in list(self.class_widgets.keys()):
                self.notebook.forget(self.class_widgets[class_name]['present_frame'].master.master)
                del self.class_widgets[class_name]
            messagebox.showinfo("Database Deleted", "The student database has been deleted.")
            logging.info("Student database deleted.")
        else:
            logging.info("Database deletion canceled by user.")

    def handle_scan_results(self, found_devices):
        self.scan_count += 1
        for addr, device_info in found_devices.items():
            if addr not in self.found_devices:
                device_info['first_seen_scan'] = self.scan_count
                self.found_devices[addr] = device_info
            else:
                self.found_devices[addr].update(device_info)
                self.found_devices[addr]['last_seen_scan'] = self.scan_count

        to_remove = [addr for addr, info in self.found_devices.items()
                     if self.scan_count - info.get('last_seen_scan', self.scan_count) > 10]
        for addr in to_remove:
            del self.found_devices[addr]

        self.attendance_manager.update_attendance(self.found_devices)
        self.refresh_gui()

    def refresh_gui(self):
        for class_name in list(self.class_widgets.keys()):
            self.update_student_lists(class_name)

    def update_student_lists(self, class_name):
        class_widgets = self.class_widgets[class_name]
        present_frame = class_widgets['present_frame']
        absent_frame = class_widgets['absent_frame']

        for frame in [present_frame, absent_frame]:
            for widget in frame.winfo_children():
                widget.destroy()

        class_data = self.attendance_manager.classes.get(class_name, {})
        students = class_data.get('students', {})
        present_students = class_data.get('present_students', set())

        for student_id, student in students.items():
            present = student_id in present_students
            self.create_student_widget(
                present_frame if present else absent_frame,
                student, student_id, class_name, present
            )

    def create_student_widget(self, parent_frame, student, student_id, class_name, present):
        frame = ttk.Frame(parent_frame, relief='raised', borderwidth=1)
        frame.pack(padx=5, pady=5, fill='x', expand=True)

        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)

        image_label = ttk.Label(frame)
        image_label.grid(row=0, column=0, rowspan=2, padx=5, pady=5)
        self.get_student_image(student, image_label)  # Asynchronously load the image

        info_frame = ttk.Frame(frame)
        info_frame.grid(row=0, column=1, sticky='w')

        name_label = ttk.Label(info_frame, text=student.get('name', ''), font=('Arial', 12, 'bold'))
        name_label.pack(anchor='w')

        assigned_macs = self.attendance_manager.get_assigned_macs_for_student(class_name, student_id)
        if assigned_macs:
            mac_display = ', '.join([mac[-4:] for mac in assigned_macs])
            mac_label = ttk.Label(info_frame, text=f"MAC: {mac_display}", foreground='blue')
            mac_label.pack(anchor='w')

            # Use the tooltip from widgets.py
            full_macs_text = '\n'.join(assigned_macs)
            ToolTip(mac_label, full_macs_text)

        if present:
            action_button = ttk.Button(frame, text="Mark Absent",
                                       command=lambda: self.mark_student_absent(class_name, student_id))
        else:
            action_button = ttk.Button(frame, text="Mark Present",
                                       command=lambda: self.mark_student_present(class_name, student_id))
        action_button.grid(row=0, column=2, sticky='e', padx=5, pady=5)

        device_var = tk.StringVar()
        device_options, device_info_map = self.get_device_options()

        device_combo = ttk.Combobox(frame, textvariable=device_var, values=device_options, state='readonly', width=35)
        device_combo.grid(row=1, column=1, padx=5, sticky='w')
        device_combo.set("Select Device")
        device_combo.bind('<<ComboboxSelected>>', lambda e: self.on_device_selected(e, class_name, student_id, device_info_map))

        assign_button = ttk.Button(frame, text="Assign",
                                   command=lambda: self.assign_device_to_student_from_combobox(
                                       class_name, student_id, device_var.get(), device_info_map))
        assign_button.grid(row=1, column=2, padx=5, pady=5, sticky='w')

    def get_device_options(self):
        device_options = []
        device_info_map = {}
        for addr, device_info in self.found_devices.items():
            addr_short = addr[-4:]
            scans_since_first_seen = self.scan_count - device_info.get('first_seen_scan', self.scan_count) + 1
            display_text = f"{device_info.get('name') or 'Unknown'} ({addr_short}) - Scans: {scans_since_first_seen}"

            prev_class_name, prev_student_id = self.attendance_manager.get_student_by_mac(addr)
            if prev_student_id:
                display_text += " [Assigned]"
                device_info_map[display_text] = {
                    'addr': addr,
                    'assigned': True,
                    'student_id': prev_student_id,
                    'class_name': prev_class_name
                }
            else:
                device_info_map[display_text] = {'addr': addr, 'assigned': False}

            device_options.append(display_text)
        return device_options, device_info_map

    def on_device_selected(self, event, class_name, student_id, device_info_map):
        selection = event.widget.get()
        device_info = device_info_map.get(selection)
        if device_info and device_info['assigned']:
            prev_class_name = device_info['class_name']
            prev_student_id = device_info['student_id']
            messagebox.showinfo("Device Assigned",
                                f"This device is already assigned to {prev_student_id} in class {prev_class_name}.")

    def assign_device_to_student_from_combobox(self, class_name, student_id, selection, device_info_map):
        if not selection or selection == "Select Device":
            messagebox.showwarning("No Selection", "Please select a device to assign.")
            return
        device_info = device_info_map.get(selection)
        if not device_info:
            messagebox.showerror("Assignment Error", "Invalid device selected.")
            return
        full_addr = device_info['addr']

        prev_class_name, prev_student_id = self.attendance_manager.get_student_by_mac(full_addr)
        if prev_student_id:
            self.attendance_manager.remove_mac_from_student(prev_class_name, prev_student_id, full_addr)
            logging.info(f"Removed device {full_addr} from student {prev_student_id} in class {prev_class_name}.")
            self.mark_student_absent(prev_class_name, prev_student_id)
            logging.info(f"Marked {prev_student_id} as absent in class {prev_class_name} due to device reassignment.")
            self.update_student_lists(prev_class_name)

        self.attendance_manager.assign_device_to_student(class_name, student_id, full_addr)
        logging.info(f"Assigned device {full_addr} to student {student_id} in class {class_name}.")
        self.mark_student_present(class_name, student_id)
        logging.info(f"Marked {student_id} as present in class {class_name} due to device assignment.")

        self.update_student_lists(class_name)

    def get_student_image(self, student, image_label):
        """Retrieve and process the student's image asynchronously."""
        def fetch_image():
            photo_url = student.get('photo_url')
            if photo_url:
                try:
                    response = requests.get(photo_url, timeout=5)
                    response.raise_for_status()
                    image_data = response.content
                    image = Image.open(BytesIO(image_data))
                    image = image.resize((100, 100), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    self.master.after(0, lambda: image_label.config(image=photo))
                    image_label.image = photo  # Prevent garbage collection
                    logging.info(f"Loaded image for student '{student.get('student_id', 'Unknown')}'.")
                except (requests.exceptions.RequestException, IOError) as e:
                    logging.error(f"Failed to load image for student {student.get('student_id', 'Unknown')}: {e}")
                    self.master.after(0, lambda: image_label.config(image=self.get_placeholder_image()))
            else:
                self.master.after(0, lambda: image_label.config(image=self.get_placeholder_image()))

        threading.Thread(target=fetch_image, daemon=True).start()

    def get_placeholder_image(self):
        """Return a default placeholder image."""
        if not hasattr(self, 'placeholder_image'):
            # Create a simple placeholder image
            image = Image.new('RGB', (100, 100), color='gray')
            self.placeholder_image = ImageTk.PhotoImage(image)
        return self.placeholder_image

    def parse_rssi_value(self, rssi_string):
        """Parse the RSSI threshold string from the GUI and return an integer value."""
        match = re.search(r'>\s*(-\d+)\s*dBm', rssi_string)
        if match:
            return int(match.group(1))
        else:
            # Default RSSI threshold
            return -70

    def add_student_dialog(self, class_name):
        """Open a dialog to add a new student with optional Student ID and Photo URL."""
        logging.info(f"Opening Add Student dialog for class '{class_name}'.")
        dialog = tk.Toplevel(self.master)
        dialog.title(f"Add Student to {class_name}")
        dialog.geometry("400x250")
        dialog.grab_set()  # Make the dialog modal

        # Labels and Entry Fields
        ttk.Label(dialog, text="Student Name:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        name_entry = ttk.Entry(dialog, width=30)
        name_entry.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="Student ID (Optional):").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        id_entry = ttk.Entry(dialog, width=30)
        id_entry.grid(row=1, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="Photo URL (Optional):").grid(row=2, column=0, padx=10, pady=10, sticky="e")
        photo_entry = ttk.Entry(dialog, width=30)
        photo_entry.grid(row=2, column=1, padx=10, pady=10)

        # Buttons
        def on_submit():
            logging.info("Submit button in Add Student dialog clicked.")
            name = name_entry.get().strip()
            student_id = id_entry.get().strip() or None
            photo_url = photo_entry.get().strip() or None

            if not name:
                messagebox.showerror("Input Error", "Student name is required.")
                logging.warning("Add Student dialog submission failed: Missing student name.")
                return

            # Optional: Validate Photo URL if provided
            if photo_url and not is_valid_url(photo_url):
                if not messagebox.askyesno("Invalid URL", "The provided Photo URL is invalid. Do you want to proceed without it?"):
                    logging.info("Add Student dialog submission canceled due to invalid Photo URL.")
                    return
                photo_url = None

            # Prepare student data
            student = {
                'name': name,
                'photo_url': photo_url,
            }
            if student_id:
                student['student_id'] = student_id

            try:
                self.attendance_manager.add_student_to_class(class_name, student)
                self.update_student_lists(class_name)
                messagebox.showinfo("Success", f"Student '{name}' added to class '{class_name}'.")
                logging.info(f"Added student '{name}' to class '{class_name}'.")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add student: {e}")
                logging.error(f"Failed to add student '{name}' to class '{class_name}': {e}")

        submit_button = ttk.Button(dialog, text="Add Student", command=on_submit)
        submit_button.grid(row=3, column=0, columnspan=2, pady=20)

        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def add_class_code(self, new_code, valid_class_codes_var):
        """Add a new class code to the list of valid class codes."""
        new_code = new_code.strip().upper()
        if new_code and new_code.isalpha():
            if new_code not in self.attendance_manager.valid_class_codes:
                self.attendance_manager.valid_class_codes.append(new_code)
                valid_class_codes_var.set(", ".join(self.attendance_manager.valid_class_codes))
                messagebox.showinfo("Success", f"Added new class code: {new_code}")
                logging.info(f"Added new class code: {new_code}")
            else:
                messagebox.showwarning("Duplicate Code", f"The class code {new_code} already exists.")
        else:
            messagebox.showerror("Invalid Code", "Please enter a valid class code consisting of alphabetic characters only.")

    def add_class(self, class_name):
        """Add a new class and create its tab."""
        class_name = class_name.strip()
        if class_name:
            if class_name not in self.attendance_manager.classes:
                self.attendance_manager.add_class(class_name)
                self.create_class_tab(class_name)
                messagebox.showinfo("Class Added", f"Class '{class_name}' has been added.")
                logging.info(f"Class '{class_name}' has been added.")
            else:
                messagebox.showwarning("Duplicate Class", f"The class '{class_name}' already exists.")
        else:
            messagebox.showwarning("Input Error", "Class name cannot be empty.")
            # Clear the input field and set focus back to it
            class_entry = self.settings_widgets['class_entry']
            class_entry.delete(0, tk.END)
            class_entry.focus_set()

    def mark_student_present(self, class_name, student_id):
        """Mark a student as present and update the GUI."""
        self.attendance_manager.mark_student_present(class_name, student_id)
        logging.info(f"Manually marked student '{student_id}' as present in class '{class_name}'.")
        self.update_student_lists(class_name)

    def mark_student_absent(self, class_name, student_id):
        """Mark a student as absent and update the GUI."""
        self.attendance_manager.mark_student_absent(class_name, student_id)
        logging.info(f"Manually marked student '{student_id}' as absent in class '{class_name}'.")
        self.update_student_lists(class_name)

    def on_closing(self):
        """Handle closing the application."""
        if messagebox.askokcancel("Quit", "Do you really want to quit?"):
            if self.scanning:
                self.scanner.stop_scanning()
            self.master.destroy()
