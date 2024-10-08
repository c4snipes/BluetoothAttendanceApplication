# gui.py


import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from attendance import AttendanceManager
from scanner import Scanner
from ml_model import MLModel
from datetime import datetime
import widgets
from PIL import Image, ImageTk
import requests
from io import BytesIO
from utils import log_message

class AttendanceApp:
    def __init__(self, master):
        self.master = master
        master.title("Bluetooth-Based Attendance Application")
        self.new_unassigned_devices = {}  # Add this line

        # Configure the master window to allow resizing
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        # Initialize modules
        self.attendance_manager = AttendanceManager()
        self.ml_model = MLModel()
        self.scanner = Scanner(callback=self.handle_scan_results, rssi_threshold=-70, scan_interval=10)

        # Initialize the valid class codes
        self.valid_class_codes = ["CSCI", "SWEN", "ENGR", "MENG"]

        # GUI Elements from widgets.py
        self.notebook = widgets.create_notebook(self.master)

        # Ensure the notebook expands with the window
        self.notebook.pack(fill='both', expand=True)
        
        self.unrecognized_devices = {}  # If used elsewhere

        # Create the Settings tab
        self.delete_button, self.theme_combo, self.add_class_button, self.class_entry, \
        self.add_code_button, self.new_code_entry, self.class_codes_display, self.import_html_button = widgets.create_settings_tab(self.notebook, self.valid_class_codes)

        # Bind events for settings
        self.add_code_button.config(command=self.add_new_class_code)
        self.import_html_button.config(command=self.import_class_from_html)
        self.delete_button.config(command=self.delete_database)
        self.theme_combo.bind('<<ComboboxSelected>>', self.change_theme)
        self.add_class_button.config(command=self.add_class)

        # Initialize class tabs
        self.class_widgets = {}  # class_name: widgets_dict
        self.create_class_tabs()

        # Start scanning
        self.scanner.start_scanning()

        # Bind the close event
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def add_new_class_code(self):
        """Add a new class code to the list of valid codes."""
        new_code = self.new_code_entry.get().strip().upper()
        if new_code and new_code not in self.valid_class_codes:
            self.valid_class_codes.append(new_code)
            self.class_codes_display.config(text=", ".join(self.valid_class_codes))
            self.new_code_entry.delete(0, tk.END)
            self.gui_log_message(f"Added new class code: {new_code}")
        elif new_code in self.valid_class_codes:
            messagebox.showwarning("Duplicate Code", f"The class code '{new_code}' already exists.")
        else:
            messagebox.showwarning("Invalid Input", "Please enter a valid class code.")
    def create_class_tabs(self):
        """Create tabs for all existing classes."""
        classes = self.attendance_manager.classes.keys()
        for class_name in classes:
            self.create_class_tab(class_name)

    def create_class_tab(self, class_name):
        class_frame = ttk.Frame(self.notebook)
        self.notebook.add(class_frame, text=class_name)

        # Create a notebook for subtabs within the class tab
        class_notebook = ttk.Notebook(class_frame)
        class_notebook.pack(fill='both', expand=True)

        # Create the Attendance tab
        attendance_tab = ttk.Frame(class_notebook)
        class_notebook.add(attendance_tab, text='Attendance')

        # Create the Device Assignment tab
        device_tab = ttk.Frame(class_notebook)
        class_notebook.add(device_tab, text='Device Assignment')

        # Now, create widgets for the Attendance tab
        button_frame, present_frame_container, absent_frame_container, \
        import_button, add_student_button, stop_scan_button, log_text, \
        interval_var, rssi_var, quit_button = widgets.create_class_tab_widgets_with_photos(attendance_tab)

        # Create scrollable frames for present and absent students
        present_frame = widgets.create_scrollable_frame(present_frame_container)
        absent_frame = widgets.create_scrollable_frame(absent_frame_container)

        # Create widgets for the Device Assignment tab
        devices_frame_widgets = widgets.create_device_assignment_tab(device_tab)

        # Store references to these widgets
        self.class_widgets[class_name] = {
            'attendance_tab': attendance_tab,
            'device_tab': device_tab,
            'button_frame': button_frame,
            'present_frame': present_frame,
            'absent_frame': absent_frame,
            'devices_listbox': devices_frame_widgets['devices_listbox'],
            'assign_device_button': devices_frame_widgets['assign_device_button'],
            'import_button': import_button,
            'add_student_button': add_student_button,
            'stop_scan_button': stop_scan_button,
            'log_text': log_text,
            'interval_var': interval_var,
            'rssi_var': rssi_var,
            'quit_button': quit_button,
            'present_student_widgets': {},
            'absent_student_widgets': {},
        }

        # Configure buttons
        import_button.config(command=lambda cn=class_name: self.import_students_from_html(cn))
        add_student_button.config(command=lambda cn=class_name: self.add_student(cn))
        stop_scan_button.config(command=self.toggle_scanning)
        quit_button.config(command=self.on_closing)

        # Assign Device button in Device Assignment tab
        assign_device_button = self.class_widgets[class_name]['assign_device_button']
        assign_device_button.config(command=lambda cn=class_name: self.assign_device_to_student_ui(cn))

        # Bind events to the dropdowns using 'write' instead of 'w'
        interval_var.trace_add('write', lambda *args, cn=class_name: self.update_scan_interval(cn))
        rssi_var.trace_add('write', lambda *args, cn=class_name: self.update_rssi_threshold(cn))

        # Update the student lists for this class
        self.update_student_lists(class_name)

    def delete_database(self):
        """Delete the student database."""
        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the student database?")
        if confirm:
            confirm_again = messagebox.askyesno("Confirm Delete", "This action cannot be undone. Are you absolutely sure?")
            if confirm_again:
                self.attendance_manager.delete_database()
                # Remove all class tabs
                for class_name in list(self.class_widgets.keys()):
                    self.remove_class_tab(class_name)
                self.class_widgets.clear()
                # Clear unrecognized devices
                self.new_unassigned_devices.clear()
                self.unrecognized_devices.clear()
                messagebox.showinfo("Database Deleted", "Student database has been deleted.")
                self.gui_log_message("Deleted student database.")
            else:
                messagebox.showinfo("Cancelled", "Database deletion has been cancelled.")
        else:
            messagebox.showinfo("Cancelled", "Database deletion has been cancelled.")

    def change_theme(self, event=None):
        """Change the application theme."""
        selected_theme = self.theme_combo.get()
        try:
            ttk.Style().theme_use(selected_theme)
            self.gui_log_message(f"Changed theme to {selected_theme}.")
        except Exception as e:
            messagebox.showerror("Theme Error", f"Failed to apply theme '{selected_theme}': {e}")
            self.gui_log_message(f"Failed to apply theme '{selected_theme}': {e}", "error")

    def add_class(self):
        """Add a new class."""
        class_name = self.class_entry.get().strip()
        if class_name:
            if class_name not in self.class_widgets:
                try:
                    self.attendance_manager.add_class(class_name)
                    self.create_class_tab(class_name)
                    self.class_entry.delete(0, tk.END)
                    self.gui_log_message(f"Added new class: {class_name}")
                except Exception as e:
                    messagebox.showerror("Add Class Error", f"Failed to add class '{class_name}': {e}")
                    self.gui_log_message(f"Failed to add class '{class_name}': {e}", "error")
            else:
                messagebox.showwarning("Duplicate Class", f"Class '{class_name}' already exists.")
        else:
            messagebox.showwarning("Input Error", "Please enter a class name.")

    def remove_class_tab(self, class_name):
        """Remove a class tab."""
        widgets = self.class_widgets[class_name]
        # Get the tab associated with the class
        class_tab = widgets['attendance_tab'].master.master
        self.notebook.forget(class_tab)
        del self.class_widgets[class_name]

    def toggle_scanning(self):
        """Toggle scanning for devices."""
        if self.scanner.scanning:
            self.scanner.stop_scanning()
            self.gui_log_message("Stopped scanning for devices.")
            # Update the button text to "Start Scanning"
            for widgets in self.class_widgets.values():
                widgets['stop_scan_button'].config(text='Start Scanning')
        else:
            self.scanner.start_scanning()
            self.gui_log_message("Started scanning for devices.")
            # Update the button text to "Stop Scanning"
            for widgets in self.class_widgets.values():
                widgets['stop_scan_button'].config(text='Stop Scanning')

    def on_closing(self):
        """Handle the window closing event."""
        self.scanner.stop_scanning()
        self.master.destroy()

    def import_students(self, class_name):
        """Import students from an HTML or CSV file into a class."""
        file_path = filedialog.askopenfilename(
            title="Select Student File",
            filetypes=[("HTML Files", "*.html"), ("CSV Files", "*.csv")]
        )
        if file_path:
            if file_path.lower().endswith('.html'):
                # Import from HTML
                self.import_students_from_html(class_name, file_path)
            elif file_path.lower().endswith('.csv'):
                # Existing CSV import
                self.import_students_from_csv(class_name, file_path)
            else:
                messagebox.showerror("Unsupported File", "Please select an HTML or CSV file.")
        else:
            messagebox.showwarning("No File Selected", "Please select a file to import.")

    def import_students_from_html(self, class_name, file_path):
        try:
            from html_parse import parse_html_file  # Assuming this is your custom HTML parser
            class_students = parse_html_file(file_path)  # Parse the HTML file
            
            if class_students:
                if class_name in class_students:
                    students = class_students[class_name]
                    self.attendance_manager.import_students_with_photos(class_name, students)
                    self.update_student_lists(class_name)
                    messagebox.showinfo("Success", f"Students imported successfully into class {class_name}.")
                    self.gui_log_message(f"Imported students from HTML file into class {class_name}.")
                else:
                    messagebox.showwarning("Class Not Found", f"Class {class_name} not found in the HTML file.")
                    self.gui_log_message(f"Class {class_name} not found in the HTML file.", "warning")
            else:
                messagebox.showwarning("No Students Found", "No students were found in the HTML file.")
                self.gui_log_message("No students were found in the HTML file.", "warning")
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import students into class {class_name}: {e}")
            self.gui_log_message(f"Failed to import students into class {class_name}: {e}", "error")
    def import_class_from_html(self):
        """Handles importing multiple classes and students from an HTML file."""
        file_path = filedialog.askopenfilename(
            title="Select HTML File",
            filetypes=[("HTML Files", "*.html")]
        )
        if not file_path:
            messagebox.showwarning("No File Selected", "Please select an HTML file to import.")
            return

        try:
            from html_parse import parse_html_file
            class_students = parse_html_file(file_path)  # Parse the HTML file for classes and students

            if class_students:
                # Define the list of valid class code prefixes
                valid_class_codes = ["CSCI", "SWEN", "ENGR", "MENG"]

                for class_name, students in class_students.items():
                    # Check if the class name contains any of the valid class codes
                    if any(code in class_name for code in valid_class_codes):
                        # Add the class if not already present
                        if class_name not in self.class_widgets:
                            self.attendance_manager.add_class(class_name)
                            self.create_class_tab(class_name)
                        
                        # Import the students for the class
                        self.attendance_manager.import_students_with_photos(class_name, students)
                        self.update_student_lists(class_name)
                    else:
                        # Log or ignore the class name if it doesn't match the valid codes
                        self.gui_log_message(f"Ignored class: {class_name}, does not match valid codes.", level="warning")

                messagebox.showinfo("Success", "Classes and students imported successfully from HTML.")
                self.gui_log_message("Imported classes and students from HTML.")
            else:
                messagebox.showwarning("No Data Found", "No valid class or student data found in the HTML file.")
                self.gui_log_message("No valid class or student data found in the HTML file.", "warning")
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import classes and students from HTML: {e}")
            self.gui_log_message(f"Failed to import classes and students from HTML: {e}", "error")

        

    def import_students_from_csv(self, class_name, file_path):
        try:
            students = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    student_name = line.strip()
                    if student_name:
                        student = {
                            'name': student_name,
                            'student_id': student_name,  # Using name as ID for simplicity
                            'email': '',
                            'photo_url': None
                        }
                        students.append(student)
            if students:
                self.attendance_manager.import_students_with_photos(class_name, students)
                self.update_student_lists(class_name)
                messagebox.showinfo("Success", f"Students imported successfully into class {class_name}.")
                self.gui_log_message(f"Imported students from CSV file into class {class_name}.")
            else:
                messagebox.showwarning("No Students Found", "No students were found in the CSV file.")
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import students into class {class_name}: {e}")
            self.gui_log_message(f"Failed to import students into class {class_name}: {e}", "error")

    def add_student(self, class_name):
        """Add a new student manually to a class."""
        
        def save_student(event=None):
            student_name = name_entry.get().strip()
            if student_name:
                # Create a student dictionary 
                student = {
                    'name': student_name,
                    'student_id': student_name,  # You might want to prompt for a unique ID
                    'email': '',  
                    'photo_url': None  # Optionally generate or set a photo URL
                }
                try:
                    self.attendance_manager.import_students_with_photos(class_name, [student])
                    self.update_student_lists(class_name)
                    self.gui_log_message(f"Added student {student_name} to class {class_name}.")
                    name_entry.delete(0, tk.END)  # Clear the entry field
                    messagebox.showinfo("Success", f"Student {student_name} added to class {class_name}.")
                    add_window.destroy()
                except Exception as e:
                    messagebox.showerror("Add Student Error", f"Failed to add student: {e}")
                    self.gui_log_message(f"Failed to add student {student_name} to class {class_name}: {e}", "error")
            else:
                messagebox.showwarning("Input Error", "Please enter a student name.")

        # Create the window for adding a new student
        add_window = tk.Toplevel(self.master)
        add_window.title(f"Add Student to {class_name}")

        name_label = ttk.Label(add_window, text="Student Name:")
        name_label.pack(pady=5)

        name_entry = ttk.Entry(add_window)
        name_entry.pack(pady=5)
        name_entry.focus_set()

        # Bind the Return key to save_student
        name_entry.bind('<Return>', save_student)

        save_button = ttk.Button(add_window, text="Add", command=save_student)
        save_button.pack(pady=5)

        close_button = ttk.Button(add_window, text="Close", command=add_window.destroy)
        close_button.pack(pady=5)


    def update_student_lists(self, class_name):
        widgets_dict = self.class_widgets.get(class_name)
        if not widgets_dict:
            return

        # Clear existing widgets in the frames
        for widget in widgets_dict['present_frame'].winfo_children():
            widget.destroy()
        for widget in widgets_dict['absent_frame'].winfo_children():
            widget.destroy()

        # Get student data
        class_data = self.attendance_manager.classes.get(class_name, {})
        students = class_data.get('students', {})
        present_students = class_data.get('present_students', set())

        num_present = len(present_students)
        num_absent = len(students) - num_present

        # Update Present Students
        for student_id in present_students:
            student = students.get(student_id)
            if student:
                student_widget = self.create_student_widget(widgets_dict['present_frame'], student, class_name, present=True)
                widgets_dict['present_student_widgets'][student_id] = student_widget

        # Update Absent Students
        for student_id, student in students.items():
            if student_id not in present_students:
                student_widget = self.create_student_widget(widgets_dict['absent_frame'], student, class_name, present=False)
                widgets_dict['absent_student_widgets'][student_id] = student_widget

        # Determine weights based on student counts
        if num_present + num_absent == 0:
            present_weight = 1
            absent_weight = 1
        else:
            present_weight = num_present if num_present > 0 else 1
            absent_weight = num_absent if num_absent > 0 else 1

        # Assign integer weights
        list_frame = widgets_dict['present_frame'].master
        list_frame.columnconfigure(0, weight=present_weight)
        list_frame.columnconfigure(1, weight=absent_weight)


    def create_student_widget(self, parent_frame, student, class_name, present):
        frame = ttk.Frame(parent_frame, relief='raised', borderwidth=1)
        frame.pack(padx=5, pady=5, fill='x')

        # Load student image
        image = self.get_student_image(student)
        image_label = ttk.Label(frame, image=image)
        image_label.image = image  # Keep a reference to avoid garbage collection
        image_label.pack(side='left', padx=5, pady=5)

        # Student name label
        name_label = ttk.Label(frame, text=student['name'])
        name_label.pack(side='left', padx=5)

        # Button to toggle attendance status
        if present:
            action_button = ttk.Button(frame, text="Mark Absent",
                                       command=lambda: self.mark_student_absent(class_name, student['student_id']))
        else:
            action_button = ttk.Button(frame, text="Mark Present",
                                       command=lambda: self.mark_student_present(class_name, student['student_id']))

        action_button.pack(side='right', padx=5, pady=5)

        return frame
    

    def get_student_image(self, student):
        url = student.get('photo_url')
        try:
            if url:
                log_message(f"Fetching image from URL: {url}", "info")
                response = requests.get(url, timeout=10)
                if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
                    img_data = response.content
                    image = Image.open(BytesIO(img_data))
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    image = image.resize((100, 100), Image.LANCZOS)
                else:
                    log_message(f"Invalid image or failed to load from URL: {url}", "warning")
                    image = Image.new('RGB', (100, 100), color='gray')  # Placeholder image
            else:
                log_message(f"No image URL for student {student['name']}", "warning")
                image = Image.new('RGB', (100, 100), color='gray')  # Placeholder

            return ImageTk.PhotoImage(image)
        except Exception as e:
            log_message(f"Error loading image for {student['name']}: {e}", "error")
            return ImageTk.PhotoImage(Image.new('RGB', (100, 100), color='gray'))  # Placeholder


    def mark_student_present(self, class_name, student_id):
        try:
            self.attendance_manager.mark_student_present(class_name, student_id)
            self.update_student_lists(class_name)
            self.gui_log_message(f"Marked {student_id} as present in class {class_name}.")
        except Exception as e:
            messagebox.showerror("Attendance Error", f"Failed to mark {student_id} as present: {e}")
            self.gui_log_message(f"Failed to mark {student_id} as present in class {class_name}: {e}", "error")

    def mark_student_absent(self, class_name, student_id):
        try:
            self.attendance_manager.mark_student_absent(class_name, student_id)
            self.update_student_lists(class_name)
            self.gui_log_message(f"Marked {student_id} as absent in class {class_name}.")
        except Exception as e:
            messagebox.showerror("Attendance Error", f"Failed to mark {student_id} as absent: {e}")
            self.gui_log_message(f"Failed to mark {student_id} as absent in class {class_name}: {e}", "error")

    def handle_scan_results(self, found_devices):
        try:
            # Update attendance based on found devices
            self.attendance_manager.update_attendance(found_devices)

            # Track first detected time for each device
            for addr, device_info in found_devices.items():
                if addr not in self.new_unassigned_devices:
                    device_info['first_detected'] = datetime.now()  # Store the first detection time
                    self.new_unassigned_devices[addr] = device_info
                else:
                    # Don't overwrite 'first_detected' if the device was already seen
                    if 'first_detected' not in self.new_unassigned_devices[addr]:
                        self.new_unassigned_devices[addr]['first_detected'] = datetime.now()

            # Refresh the GUI to show updated attendance and devices
            for class_name in list(self.class_widgets.keys()):
                self.master.after(0, self.update_student_lists, class_name)
                self.master.after(0, self.update_unrecognized_devices, class_name)
        except Exception as e:
            log_message(f"Error occurred during scanning: {e}", "error")




    def notify_new_device(self, addr, device_info):
        """Notify about a newly detected unassigned device."""
        name = device_info['name'] or 'Unknown'
        display_text = f"{name} ({addr})"

        # Insert the new device at the top of the listbox in each class
        for class_name, widgets in self.class_widgets.items():
            devices_listbox = widgets.get('devices_listbox')
            if devices_listbox:
                devices_listbox.insert(0, display_text)

        # Log that a new device has been detected
        self.gui_log_message(f"New device detected: {display_text}")


    def update_unrecognized_devices(self, class_name):
        """Refresh the Detected Devices list for a class."""
        widgets = self.class_widgets.get(class_name)
        if not widgets:
            return

        devices_listbox = widgets['devices_listbox']
        if devices_listbox.winfo_exists():
            devices_listbox.delete(0, tk.END)

            # Sort devices by the time they were first detected
            sorted_unrecognized = sorted(self.new_unassigned_devices.items(),
                                        key=lambda item: item[1]['first_detected'])

            for addr, device_info in sorted_unrecognized:
                name = device_info['name'] or 'Unknown'
                rssi = device_info['rssi']
                first_detected = device_info.get('first_detected').strftime('%H:%M:%S')
                display_name = f"{name} ({addr}) - RSSI: {rssi} - First Seen: {first_detected}"
                devices_listbox.insert(tk.END, display_name)




    def assign_device_to_student_ui(self, class_name):
        """Assign a selected device from the Detected Devices list to a student in a class."""
        # Get the class widgets and make sure they exist
        widgets = self.class_widgets.get(class_name)
        if not widgets:
            return

        devices_listbox = widgets['devices_listbox']

        # Ensure there is a device selected
        selected_index = devices_listbox.curselection()
        if selected_index:
            # Extract the device's address from the selection
            selected_device_info = devices_listbox.get(selected_index)
            addr = selected_device_info.split('(')[-1].split(')')[0]
            self.assign_device_to_student_from_ui(class_name, addr)
        else:
            messagebox.showwarning("No Device Selected", "Please select a device to assign.")


    def assign_device_to_student_from_ui(self, class_name, addr):
        """Open a window to assign a specific device to a student in a class."""
        assign_window = tk.Toplevel(self.master)
        assign_window.title(f"Assign Device {addr} to {class_name}")

        ttk.Label(assign_window, text=f"Select the student to assign device {addr} to:").pack(pady=5)

        # Create a listbox to display the students in the class
        student_listbox = tk.Listbox(assign_window)
        student_listbox.pack(pady=5, expand=True, fill=tk.BOTH)

        # Populate the listbox with students from the class
        students = self.attendance_manager.get_all_students(class_name)
        for student_id, student in students.items():
            display_text = f"{student_id} - {student['name']}"
            student_listbox.insert(tk.END, display_text)

        def assign_selected_student():
            # Get the selected student from the listbox
            selected_index = student_listbox.curselection()
            if selected_index:
                # Extract the student ID from the selection
                selected_student_info = student_listbox.get(selected_index)
                student_id = selected_student_info.split(' - ')[0]
                try:
                    # Assign the device to the student
                    self.attendance_manager.assign_device_to_student(class_name, student_id, addr)
                    self.gui_log_message(f"Assigned device {addr} to student {student_id} in class {class_name}.")
                    assign_window.destroy()  # Close the student selection window
                except Exception as e:
                    messagebox.showerror("Assignment Error", f"Failed to assign device: {e}")
                    self.gui_log_message(f"Failed to assign device {addr} to student {student_id}: {e}", "error")
            else:
                messagebox.showwarning("No Selection", "Please select a student.")

        # Add the assign button to confirm the student selection
        ttk.Button(assign_window, text="Assign Device", command=assign_selected_student).pack(pady=5)


    def update_scan_interval(self, class_name):
        """Update the scan interval based on user selection."""
        interval_var = self.class_widgets[class_name]['interval_var']
        selected_value = interval_var.get()
        try:
            interval_seconds = int(selected_value.split()[0])
            self.scanner.update_scan_interval(interval_seconds)
            self.gui_log_message(f"Updated scan interval to {interval_seconds} seconds.")
        except ValueError:
            messagebox.showerror("Input Error", "Invalid scan interval selected.")
            self.gui_log_message(f"Invalid scan interval selected: {selected_value}", "error")

    def update_rssi_threshold(self, class_name):
        """Update the RSSI threshold based on user selection."""
        rssi_var = self.class_widgets[class_name]['rssi_var']
        selected_value = rssi_var.get()
        rssi_mapping = {
            'Very Close (> -50 dBm)': -50,
            'Close (> -60 dBm)': -60,
            'Medium (> -70 dBm)': -70,
            'Far (> -80 dBm)': -80,
            'Very Far (> -90 dBm)': -90
        }
        try:
            new_threshold = rssi_mapping[selected_value]
            self.scanner.update_rssi_threshold(new_threshold)
            self.gui_log_message(f"Updated RSSI threshold to {new_threshold} dBm.")
        except KeyError:
            messagebox.showerror("Input Error", "Invalid RSSI threshold selected.")
            self.gui_log_message(f"Invalid RSSI threshold selected: {selected_value}", "error")

    def gui_log_message(self, message, level="info"):
        """Append a message to the log text box and log file."""
        current_time = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{current_time}] {message}\n"

        # Log to the GUI
        for widgets in self.class_widgets.values():
            log_text = widgets.get('log_text')
            if log_text and log_text.winfo_exists():
                log_text.configure(state='normal')
                log_text.insert(tk.END, log_entry)
                log_text.configure(state='disabled')
                log_text.see(tk.END)

        # Log to the file or console
        log_message(message, level)