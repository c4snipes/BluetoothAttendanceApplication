# gui.py

from io import BytesIO
import os
import re
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
from datetime import datetime
import requests
import export  # Import the export function
from html_parse import parse_html_file
from attendance import AttendanceManager
from scanner import Scanner
from utils import log_message
import utils
import widgets
from widgets import ToolTip
from import_att import importApp
from export import Disseminate

class AttendanceApp:
    def __init__(self, master):
        self.master = master
        master.title("Bluetooth-Based Attendance Application")
        master.geometry("1024x768")  # Set a default window size

        # Initialize threading lock
        self.lock = threading.RLock()

        # Initialize AttendanceManager and Scanner
        self.attendance_manager = AttendanceManager()
        self.scanner = Scanner(callback=self.handle_scan_results)
        self.importion = importApp(self.attendance_manager)
        self.disseminate = Disseminate(self.master, self.attendance_manager)
        self.found_devices = {}
        self.scan_count = 0

        # Create the notebook (tabbed interface)
        self.notebook = widgets.create_notebook(master)

        # Initialize class tabs
        self.class_widgets = {}
        self.create_class_tabs()
        
        # Start scanning devices
        self.scanning = True
        self.scanner.start_scanning()

        # Bind the close event
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_class_tabs(self):
        """Create tabs for each class."""
        for class_name in self.attendance_manager.classes.keys():
            self.create_class_tab(class_name)
        # Optionally, create a settings tab
        settings_tab = widgets.create_settings_tab(self.notebook, self.attendance_manager.get_valid_class_codes())
        # Connect settings actions
        self.connect_settings_actions()

    def stop_scanning(self):
        """Stop Bluetooth scanning."""
        if self.scanning:
            self.scanner.stop_scanning()
            self.scanning = False
            log_message("Scanning stopped.")

    def delete_database(self):
        """Delete the student database."""
        with self.lock:
            self.attendance_manager.delete_database()
            # Optionally, refresh the GUI after deletion
            for class_name in list(self.class_widgets.keys()):
                self.notebook.forget(self.class_widgets[class_name]['present_frame'].master)
                del self.class_widgets[class_name]
            messagebox.showinfo("Database Deleted", "The student database has been deleted.")

    def on_closing(self):
        """Handle closing the application."""
        self.stop_scanning()
        self.master.destroy()

    def create_class_tab(self, class_name):
        class_frame = ttk.Frame(self.notebook)
        self.notebook.add(class_frame, text=class_name)

        # Use the widgets from widgets.py
        class_widgets = widgets.create_class_tab_widgets_with_photos(class_frame)

        # Unpack the widgets
        (
            button_frame,
            present_frame_container,
            absent_frame_container,
            import_button,
            add_student_button,
            stop_scan_button,
            log_text,
            interval_var,
            rssi_var,
            quit_button,
            export_button,
            export_all_button,  # Ensure this is included based on previous corrections
        ) = class_widgets

        # Create scrollable frames for present and absent students
        present_frame = widgets.create_scrollable_frame(present_frame_container)
        absent_frame = widgets.create_scrollable_frame(absent_frame_container)

        # Store the widgets for later use
        self.class_widgets[class_name] = {
            'present_frame': present_frame,
            'absent_frame': absent_frame,
            'import_button': import_button,
            'add_student_button': add_student_button,
            'stop_scan_button': stop_scan_button,
            'log_text': log_text,
            'interval_var': interval_var,
            'rssi_var': rssi_var,
            'quit_button': quit_button,
            'export_button': export_button,
            'export_all_button': export_all_button,
            'present_student_widgets': {},
            'absent_student_widgets': {},
        }

        # Connect button signals
        import_button.config(command=self.import_html_action)
        add_student_button.config(command=lambda: self.add_student_dialog(class_name))  # Updated
        stop_scan_button.config(command=self.stop_scanning)
        # For exporting attendance for a single class
        export_button.config(command=lambda: self.disseminate.export_attendance(class_name))
        # For exporting all classes
        export_all_button.config(command=lambda: self.disseminate.export_all_classes())
        quit_button.config(command=self.on_closing)
        
        # Initialize interval and RSSI settings
        interval_var.trace_add('write', lambda *args: self.scanner.update_scan_interval(int(interval_var.get().split()[0])))
        rssi_var.trace_add('write', lambda *args: self.scanner.update_rssi_threshold(self.parse_rssi_value(rssi_var.get())))

        # Populate students
        self.update_student_lists(class_name)

    def connect_settings_actions(self):
        (
            delete_button,
            theme_combo,
            add_class_button,
            class_entry,
            add_code_button,
            new_code_entry,
            class_codes_display,
            import_html_button,
            export_all_button,
        ) = self.settings_widgets

        delete_button.config(command=self.delete_database)
        theme_combo.bind('<<ComboboxSelected>>', lambda event: widgets.change_theme(theme_combo.get()))
        add_class_button.config(command=lambda: self.attendance_manager.add_class(class_entry.get()))
        add_code_button.config(command=lambda: self.add_class_code(new_code_entry.get(), class_codes_display))
        # Update this line to correctly reference the export_all_classes function
        export_all_button.config(command=lambda: self.disseminate.export_all_classes())

        # Update to call import_students_from_html
        import_html_button.config(command=self.import_html_action)

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

        name_label = ttk.Label(info_frame, text=student['name'], font=('Arial', 12, 'bold'))
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
                                    command=lambda: self.attendance_manager.mark_student_absent(class_name, student_id))
        else:
            action_button = ttk.Button(frame, text="Mark Present",
                                    command=lambda: self.attendance_manager.mark_student_present(class_name, student_id))
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

    def import_html_action(self):
        """Handle the action triggered by the 'Import HTML' button."""
        updated_classes = self.importion.import_html_action()
        for class_name in updated_classes:
            if class_name not in self.class_widgets:
                self.create_class_tab(class_name)
            self.update_student_lists(class_name)

    def get_device_options(self):
        device_options = []
        device_info_map = {}
        for addr, device_info in self.found_devices.items():
            addr_short = addr[-4:]
            scans_since_first_seen = self.scan_count - device_info.get('first_seen_scan', self.scan_count) + 1
            display_text = f"{device_info['name'] or 'Unknown'} ({addr_short}) - Scans: {scans_since_first_seen}"

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
            log_message(f"Removed device {full_addr} from student {prev_student_id} in class {prev_class_name}.")
            self.attendance_manager.mark_student_absent(prev_class_name, prev_student_id)
            log_message(f"Marked {prev_student_id} as absent in class {prev_class_name} due to device reassignment.")
            self.update_student_lists(prev_class_name)

        self.attendance_manager.assign_device_to_student(class_name, student_id, full_addr)
        log_message(f"Assigned device {full_addr} to student {student_id} in class {class_name}.")
        self.attendance_manager.mark_student_present(class_name, student_id)
        log_message(f"Marked {student_id} as present in class {class_name} due to device assignment.")

        self.update_student_lists(class_name)

    def refresh_gui(self):
        for class_name in list(self.class_widgets.keys()):
            self.update_student_lists(class_name)

    def get_student_image(self, student, image_label):
        """Retrieve and process the student's image asynchronously."""
        def fetch_image():
            photo_url = student.get('photo_url')
            if photo_url:
                try:
                    response = requests.get(photo_url, timeout=5)
                    image_data = response.content
                    image = Image.open(BytesIO(image_data))
                    image = image.resize((100, 100), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    self.master.after(0, lambda: image_label.config(image=photo))
                    image_label.image = photo
                except Exception as e:
                    log_message(f"Failed to load image for student {student['student_id']}: {e}", "error")
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

    def add_class_code(self, new_code, class_codes_display):
        """Add a new class code to the list of valid class codes."""
        new_code = new_code.strip().upper()
        if new_code and new_code.isalpha():
            if new_code not in self.attendance_manager.valid_class_codes:
                self.attendance_manager.valid_class_codes.append(new_code)
                class_codes_display.config(text=", ".join(self.attendance_manager.valid_class_codes))
                messagebox.showinfo("Success", f"Added new class code: {new_code}")
                log_message(f"Added new class code: {new_code}")
            else:
                messagebox.showwarning("Duplicate Code", f"The class code {new_code} already exists.")
        else:
            messagebox.showerror("Invalid Code", "Please enter a valid class code consisting of alphabetic characters only.")

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
            name = name_entry.get().strip()
            student_id = id_entry.get().strip() or None
            photo_url = photo_entry.get().strip() or None

            if not name:
                messagebox.showerror("Input Error", "Student name is required.")
                return

            # Optional: Validate Photo URL if provided
            if photo_url and not utils.is_valid_url(photo_url):
                if not messagebox.askyesno("Invalid URL", "The provided Photo URL is invalid. Do you want to proceed without it?"):
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
                log_message(f"Added student '{name}' to class '{class_name}'.")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add student: {e}")
                log_message(f"Failed to add student '{name}' to class '{class_name}': {e}", "error")

        submit_button = ttk.Button(dialog, text="Add Student", command=on_submit)
        submit_button.grid(row=3, column=0, columnspan=2, pady=20)

        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
