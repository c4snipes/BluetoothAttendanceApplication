# gui.py

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
from widgets import create_notebook, create_settings_tab, create_class_tab_widgets_with_photos, create_scrollable_frame, bind_tab_dragging, ToolTip
import widgets

class AttendanceApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Bluetooth-Based Attendance System")
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Initialize image cache directory
        self.image_cache_dir = os.path.join(os.getcwd(), 'image_cache')
        if not os.path.exists(self.image_cache_dir):
            os.makedirs(self.image_cache_dir, exist_ok=True)


        # Initialize scan count and found devices
        self.scan_count = 0
        self.found_devices = {}

        # Initialize drag data for tab dragging
        self._drag_data = {"tab_index": None, "x": 0, "y": 0}

        # Initialize AttendanceManager
        self.attendance_manager = AttendanceManager()

        # Initialize ImportApp and Disseminate
        self.importer = ImportApp(self.attendance_manager)
        self.disseminate = Disseminate(self.master, self.attendance_manager)

        # Initialize Scanner
        self.scanner = Scanner(callback=self.handle_scan_results)
        self.scanning = False  # Scanning state

        # Create notebook (tabs)
        self.notebook = create_notebook(self.master)

        # Initialize class tabs
        self.class_widgets = {}
        self.create_class_tabs()

        # Setup logging in GUI
        self.setup_gui_logging()

        # Bind tab drag-and-drop functionality
        bind_tab_dragging(self.notebook, self.on_tab_press, self.on_tab_motion, self.on_tab_release)

    def create_class_tabs(self):
        """Create tabs for each class."""
        for class_name in self.attendance_manager.classes.keys():
            self.create_class_tab(class_name)

        # Create settings tab and assign the widgets to `settings_widgets`
        self.settings_widgets = create_settings_tab(
            self.notebook,
            self.attendance_manager.get_valid_class_codes(),
            list(self.attendance_manager.classes.keys())  # Pass class names
        )
        # Connect settings actions after `settings_widgets` has been assigned
        self.connect_settings_actions()

        # Create Logs tab
        self.create_logs_tab()

    def create_class_tab(self, class_name):
        class_frame = ttk.Frame(self.notebook)

        # Use the updated widgets from widgets.py
        class_widgets_tuple = create_class_tab_widgets_with_photos(class_frame)

        # Unpack the widgets
        (
            button_frame,
            present_frame_container,
            absent_frame_container,
            add_student_button,
            scan_toggle_button,
            interval_var,
            rssi_var,
            quit_button,
            export_button,
        ) = class_widgets_tuple

        # Create scrollable frames for present and absent students
        present_frame = create_scrollable_frame(present_frame_container)
        absent_frame = create_scrollable_frame(absent_frame_container)

        # Store the widgets for later use
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
            'tab_frame': class_frame,
        }

        # Set the scan button text based on current scanning state
        if self.scanning:
            scan_toggle_button.config(text="Stop Scanning")
        else:
            scan_toggle_button.config(text="Start Scanning")

        # Connect button signals
        add_student_button.config(command=lambda: self.add_student_dialog(class_name))
        scan_toggle_button.config(command=self.toggle_scanning)
        export_button.config(command=lambda: self.disseminate.export_attendance(class_name))
        quit_button.config(command=self.on_closing)

        # Initialize interval and RSSI settings
        interval_var.trace_add('write', lambda *args: self.update_scan_interval(int(interval_var.get().split()[0])))
        rssi_var.trace_add('write', lambda *args: self.scanner.update_rssi_threshold(self.parse_rssi_value(rssi_var.get())))

        # Populate students
        self.update_student_lists(class_name)

        # Add the tab to the notebook
        self.notebook.add(class_frame, text=class_name)

    def connect_settings_actions(self):
        """
        Connect actions to the widgets in the settings tab.
        """
        # Get the widgets from settings_widgets
        delete_button = self.settings_widgets['delete_button']
        theme_combo = self.settings_widgets['theme_combo']
        add_class_button = self.settings_widgets['add_class_button']
        class_entry = self.settings_widgets['class_entry']
        add_code_button = self.settings_widgets['add_code_button']
        new_code_entry = self.settings_widgets['new_code_entry']
        valid_class_codes_var = self.settings_widgets['valid_class_codes_var']
        import_html_button = self.settings_widgets['import_html_button']
        export_all_button = self.settings_widgets['export_all_button']
        class_combo = self.settings_widgets['class_combo']
        delete_class_button = self.settings_widgets['delete_class_button']

        # Connect actions
        delete_button.config(command=self.delete_database)
        theme_combo.bind('<<ComboboxSelected>>', lambda e: self.change_theme(theme_combo.get()))
        add_class_button.config(command=lambda: self.add_class(class_entry.get()))
        add_code_button.config(command=lambda: self.add_class_code(new_code_entry.get(), valid_class_codes_var))
        import_html_button.config(command=self.import_html_action)
        export_all_button.config(command=self.disseminate.export_all_classes)
        delete_class_button.config(command=lambda: self.delete_class(class_combo.get()))

    def update_scan_interval(self, new_interval):
        """
        Update the scan interval in both the Scanner and AttendanceManager.
        """
        self.scanner.update_scan_interval(new_interval)
        self.attendance_manager.set_scan_interval(new_interval)
        logging.info(f"Scan interval updated to {new_interval} seconds.")

    def change_theme(self, theme_name):
        """
        Change the application theme.
        """
        widgets.change_theme(theme_name)
        logging.info(f"Theme changed to {theme_name}.")

    def delete_class(self, class_name):
        """Delete an existing class."""
        if not class_name:
            messagebox.showwarning("No Class Selected", "Please select a class to delete.")
            return
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the class '{class_name}'? This action cannot be undone."):
            try:
                # Remove the tab
                class_tab = self.class_widgets[class_name]['tab_frame']
                self.notebook.forget(class_tab)
                # Remove class data
                self.attendance_manager.delete_class(class_name)
                # Remove from class_widgets
                del self.class_widgets[class_name]
                # Update class list in settings tab
                class_names = list(self.attendance_manager.classes.keys())
                self.settings_widgets['class_combo']['values'] = class_names
                messagebox.showinfo("Class Deleted", f"Class '{class_name}' has been deleted.")
                logging.info(f"Class '{class_name}' has been deleted.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete class '{class_name}': {e}")
                logging.error(f"Failed to delete class '{class_name}': {e}")

    def delete_database(self):
        """Delete the entire student database."""
        if messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete the entire student database? This action cannot be undone."):
            try:
                # Clear data from AttendanceManager
                self.attendance_manager.delete_database()
                # Remove all class tabs
                for class_name in list(self.class_widgets.keys()):
                    class_tab = self.class_widgets[class_name]['tab_frame']
                    self.notebook.forget(class_tab)
                    del self.class_widgets[class_name]
                # Update class list in settings tab
                self.settings_widgets['class_combo']['values'] = []
                messagebox.showinfo("Database Deleted", "Student database has been deleted.")
                logging.info("Student database has been deleted.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete database: {e}")
                logging.error(f"Failed to delete database: {e}")

    def add_class(self, class_name):
        """Add a new class and create its tab."""
        class_name = class_name.strip()
        if class_name:
            if class_name not in self.attendance_manager.classes:
                self.attendance_manager.add_class(class_name)
                self.create_class_tab(class_name)
                messagebox.showinfo("Class Added", f"Class '{class_name}' has been added.")
                logging.info(f"Class '{class_name}' has been added.")
                # Update class list in settings tab
                class_names = list(self.attendance_manager.classes.keys())
                self.settings_widgets['class_combo']['values'] = class_names
                # Clear the input field
                class_entry = self.settings_widgets['class_entry']
                class_entry.delete(0, tk.END)
            else:
                messagebox.showwarning("Duplicate Class", f"The class '{class_name}' already exists.")
        else:
            messagebox.showwarning("Input Error", "Class name cannot be empty.")
            # Clear the input field and set focus back to it
            class_entry = self.settings_widgets['class_entry']
            class_entry.delete(0, tk.END)
            class_entry.focus_set()

    def add_class_code(self, code, valid_class_codes_var):
        """Add a new class code for HTML parsing."""
        code = code.strip()
        if code:
            try:
                self.attendance_manager.add_valid_class_code(code)
                valid_class_codes_display = [c for c in self.attendance_manager.get_valid_class_codes() if c.isalpha()]
                valid_class_codes_var.set(", ".join(valid_class_codes_display))
                messagebox.showinfo("Code Added", f"Class code '{code}' has been added.")
                logging.info(f"Class code '{code}' has been added.")
                # Clear the input field
                new_code_entry = self.settings_widgets['new_code_entry']
                new_code_entry.delete(0, tk.END)
            except ValueError as ve:
                messagebox.showwarning("Input Error", str(ve))
        else:
            messagebox.showwarning("Input Error", "Class code cannot be empty.")

    def import_html_action(self):
        """
        Import students from an HTML file.
        """
        imported_classes = self.importer.import_html_action()
        if imported_classes:
            # Create tabs for any new classes imported
            for class_name in imported_classes:
                if class_name not in self.class_widgets:
                    self.create_class_tab(class_name)

            # Update class list in settings tab
            class_names = list(self.attendance_manager.classes.keys())
            self.settings_widgets['class_combo']['values'] = class_names


    def toggle_scanning(self):
        """Start or stop the Bluetooth scanning."""
        try:
            if self.scanning:
                # Currently scanning; stop scanning
                self.scanning = False
                self.scanner.stop_scanning()
                for class_name, widgets_dict in self.class_widgets.items():
                    widgets_dict['scan_toggle_button'].config(text="Start Scanning")
                logging.info("Scanning stopped.")
            else:
                # Currently not scanning; start scanning
                self.scanning = True
                self.scanner.start_scanning()
                for class_name, widgets_dict in self.class_widgets.items():
                    widgets_dict['scan_toggle_button'].config(text="Stop Scanning")
                logging.info("Scanning started.")
        except Exception as e:
            logging.error(f"Error toggling scanning: {e}")
            messagebox.showerror("Error", f"Failed to toggle scanning: {e}")



    def handle_scan_results(self, found_devices):
        """
        Called from the scanner's background thread whenever new devices are discovered.

        Since Tkinter must be updated from the main (GUI) thread, this method uses
        'self.master.after(0, ...)' to schedule '_on_scan_results' on the main thread.
        """
        # Schedule the real GUI update
        self.master.after(0, self._on_scan_results, found_devices)

    def _on_scan_results(self, found_devices):
        """
        Runs on the main (GUI) thread. Safe to update Tkinter widgets here.
        We store the discovered devices, update attendance, and refresh the UI.
        """
        try:
            self.found_devices = found_devices
            self.scan_count += 1
            logging.info(f"Handling scan results on main thread. Scan count: {self.scan_count}")

            # Let the AttendanceManager process these found devices
            self.attendance_manager.update_attendance(found_devices)

            # For each class, rebuild the student lists (present/absent frames, etc.)
            for class_name in self.class_widgets.keys():
                self.update_student_lists(class_name)
        except Exception as e:
            logging.error(f"Error in _on_scan_results: {e}")
        if not found_devices:
            logging.info("No devices discovered this scan cycle.")


    def update_student_lists(self, class_name):
        """Update the present and absent student lists for a class."""
        widgets_dict = self.class_widgets[class_name]
        present_frame = widgets_dict['present_frame']
        absent_frame = widgets_dict['absent_frame']

        # Clear existing widgets from frames
        for widget in present_frame.winfo_children():
            widget.destroy()
        for widget in absent_frame.winfo_children():
            widget.destroy()

        # Clear stored references
        widgets_dict['present_student_widgets'].clear()
        widgets_dict['absent_student_widgets'].clear()

        # Get students
        all_students = self.attendance_manager.get_all_students(class_name)
        present_students = self.attendance_manager.get_present_students(class_name)

        # Create student widgets
        for student_id, student_data in all_students.items():
            if student_id in present_students:
                frame = present_frame
                widgets_dict_key = 'present_student_widgets'
            else:
                frame = absent_frame
                widgets_dict_key = 'absent_student_widgets'

            student_widget = self.create_student_widget(frame, class_name, student_id, student_data)
            widgets_dict[widgets_dict_key][student_id] = student_widget

    def create_student_widget(self, parent_frame, class_name, student_id, student_data):
        """Create a widget for a single student."""
        student_frame = ttk.Frame(parent_frame)
        student_frame.pack(fill="x", padx=5, pady=5)
        
        # Configure grid in student_frame
        student_frame.columnconfigure(1, weight=1)  # Allow column 1 (info_label) to expand
        student_frame.columnconfigure(2, weight=0)  # Buttons won't expand
        
        # Create image label
        image_label = tk.Label(student_frame)
        image_label.grid(row=0, column=0, rowspan=2, padx=5, pady=5, sticky="nw")
        self.get_student_image(student_data, image_label)
        
        # Student info
        info_text = f"{student_data.get('name')} (ID: {student_id})"
        info_label = ttk.Label(student_frame, text=info_text, wraplength=200)
        info_label.grid(row=0, column=1, sticky="w")
        
        # Attendance count
        attendance_count = self.attendance_manager.get_attendance_count(class_name, student_id)
        count_label = ttk.Label(student_frame, text=f"Attendance Count: {attendance_count}")
        count_label.grid(row=1, column=1, sticky="w")
        
        # Buttons frame
        buttons_frame = ttk.Frame(student_frame)
        buttons_frame.grid(row=0, column=2, rowspan=2, padx=5, pady=5, sticky="ne")
        
        # Assign device button
        assign_button = ttk.Button(buttons_frame, text="Assign Device")
        assign_button.pack(fill="x", pady=2)
        assign_button.config(command=lambda: self.show_device_combobox(buttons_frame, class_name, student_id, assign_button))
        
        # Mark present/absent button
        present_students = self.attendance_manager.get_present_students(class_name)
        if student_id in present_students:
            mark_button = ttk.Button(buttons_frame, text="Mark Absent")
            mark_button.config(command=lambda: self.mark_student_absent(class_name, student_id))
        else:
            mark_button = ttk.Button(buttons_frame, text="Mark Present")
            mark_button.config(command=lambda: self.mark_student_present(class_name, student_id))
        mark_button.pack(fill="x", pady=2)
        
        # Delete student button ('x' symbol)
        delete_button = ttk.Button(buttons_frame, text="✕", width=3)
        delete_button.pack(pady=2)
        delete_button.config(command=lambda: self.delete_student_dialog(class_name, student_id))
        
        return student_frame

    def show_device_combobox(self, parent_frame, class_name, student_id, assign_button):
        """Show a combobox with available devices to assign to a student."""
        assign_button.pack_forget()

        # Get available devices
        devices = list(self.found_devices.keys())
        device_var = tk.StringVar()
        device_combobox = ttk.Combobox(parent_frame, textvariable=device_var, values=devices)
        device_combobox.pack(side="left", padx=2)

        def assign_device():
            device_address = device_var.get().strip()
            if device_address:
                self.attendance_manager.assign_device_to_student(class_name, student_id, device_address)
                messagebox.showinfo("Device Assigned", f"Device '{device_address}' assigned to student '{student_id}'.")
                logging.info(f"Device '{device_address}' assigned to student '{student_id}' in class '{class_name}'.")
            else:
                messagebox.showwarning("No Device Selected", "Please select a device to assign.")
            device_combobox.destroy()
            assign_button.pack(side="left", padx=2)
            # Reset manual override so scanner can update attendance
            student_data = self.attendance_manager.get_student_data(class_name, student_id)
            if student_data:
                student_data['manual_override'] = False
                self.attendance_manager.save_data()
                self.update_student_lists(class_name)

        assign_button_confirm = ttk.Button(parent_frame, text="Assign", command=assign_device)
        assign_button_confirm.pack(side="left", padx=2)

    def get_student_image(self, student, image_label):
        """
        Retrieve and display the student's image.
        Also saves the image to the local 'image_cache' folder as <student_id>.png.
        If 'skip_download_if_cached' is True, it will load from cache whenever possible.
        """
        # 1) Derive the student's ID for naming the file
        student_id = student.get('student_id') or "unknown"
        photo_url = student.get('photo_url')
        
        # 2) Create a safe filename from the student's ID
        sanitized_student_id = "".join(c for c in student_id if c.isalnum())
        cache_file = os.path.join(self.image_cache_dir, f"{sanitized_student_id}.png")

        # Set to False if you always want to re-download, ignoring the cache
        skip_download_if_cached = True  

        # (A) If want to skip the download and a cached file exists, try loading it
        if skip_download_if_cached and os.path.exists(cache_file):
            try:
                logging.info(f"Loading '{student_id}' image from cache: {cache_file}")
                # Load from disk and resize to (100x100)
                image = Image.open(cache_file).resize((100, 100), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                image_label.config(image=photo)
                image_label.image = photo  # Prevent garbage collection
                return
            except Exception as e:
                logging.warning(f"Failed to load cached image for '{student_id}': {e}")
                # If loading fails, we'll try to download below

        # (B) Download if no cached file or we want a fresh copy
        if photo_url and is_valid_url(photo_url):
            try:
                response = requests.get(photo_url, timeout=5)
                response.raise_for_status()
                # Create PIL image
                image = Image.open(BytesIO(response.content)).resize((100, 100), Image.Resampling.LANCZOS)
                
                # Display in Tkinter
                photo = ImageTk.PhotoImage(image)
                image_label.config(image=photo)
                image_label.image = photo

                # Save to cache
                try:
                    if not os.path.exists(self.image_cache_dir):
                        os.makedirs(self.image_cache_dir, exist_ok=True)
                    image.save(cache_file, format="PNG")
                    logging.info(f"Downloaded and cached image for '{student_id}' at '{cache_file}'.")
                except Exception as e:
                    logging.error(f"Error saving cached image for '{student_id}': {e}")

            except Exception as e:
                logging.error(f"Error downloading image for '{student_id}': {e}")
                image_label.config(image=self.get_placeholder_image())
        else:
            # (C) If no valid URL, load a placeholder
            image_label.config(image=self.get_placeholder_image())


    def get_placeholder_image(self):
        """Return a default placeholder image."""
        if not hasattr(self, 'placeholder_image'):
            # Create and store the placeholder image only once
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
        dialog.geometry("400x300")
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

        # Device Combobox
        ttk.Label(dialog, text="Device Address (Optional):").grid(row=3, column=0, padx=10, pady=10, sticky="e")
        device_var = tk.StringVar()
        device_addresses = list(self.found_devices.keys())
        device_combobox = ttk.Combobox(dialog, textvariable=device_var, values=device_addresses)
        device_combobox.grid(row=3, column=1, padx=10, pady=10)

        # Refresh Devices Button
        refresh_button = ttk.Button(dialog, text="Refresh Devices", command=lambda: self.refresh_device_combobox(device_combobox, device_var))
        refresh_button.grid(row=3, column=2, padx=5, pady=10)

        # Buttons
        def on_submit():
            try:
                logging.info("Submit button in Add Student dialog clicked.")
                name = name_entry.get().strip()
                student_id = id_entry.get().strip() or None
                photo_url = photo_entry.get().strip() or None
                device_address = device_var.get().strip() or None

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
                    'device_address': device_address,
                }
                if student_id:
                    student['student_id'] = student_id

                self.attendance_manager.add_student_to_class(class_name, student)
                self.update_student_lists(class_name)
                messagebox.showinfo("Success", f"Student '{name}' added to class '{class_name}'.")
                logging.info(f"Added student '{name}' to class '{class_name}'.")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add student: {e}")
                logging.error(f"Failed to add student '{name}' to class '{class_name}': {e}")
    
        submit_button = ttk.Button(dialog, text="Add Student", command=on_submit)
        submit_button.grid(row=4, column=0, columnspan=2, pady=20)

        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def refresh_device_combobox(self, device_combobox, device_var):
        """Refresh the list of available devices in the combobox."""
        device_addresses = list(self.found_devices.keys())
        device_combobox['values'] = device_addresses
        if device_addresses:
            device_var.set(device_addresses[0])  # Set default value
        else:
            device_var.set('')
        logging.info("Device combobox refreshed with available devices.")

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

    def delete_student_dialog(self, class_name, student_id):
        """Open a confirmation dialog to delete a student."""
        student_data = self.attendance_manager.classes[class_name]['students'].get(student_id, {})
        student_name = student_data.get('name', 'Unknown')

        confirm = messagebox.askyesno(
            "Delete Student",
            f"Are you sure you want to delete student '{student_name}' (ID: {student_id}) from class '{class_name}'?"
        )
        if confirm:
            try:
                self.attendance_manager.delete_student(class_name, student_id)
                # Delete cached image if exists
                self.delete_student_image(student_id)
                # Update the student lists in the GUI
                self.update_student_lists(class_name)
                messagebox.showinfo("Student Deleted", f"Student '{student_name}' has been deleted from class '{class_name}'.")
                logging.info(f"Deleted student '{student_id}' from class '{class_name}'.")
            except Exception as e:
                messagebox.showerror("Deletion Error", f"Failed to delete student: {e}")
                logging.error(f"Failed to delete student '{student_id}' from class '{class_name}': {e}")

    def delete_student_image(self, student_id):
        """Delete the cached image of a student."""
        sanitized_student_id = "".join(c for c in student_id if c.isalnum())
        image_path = os.path.join(self.image_cache_dir, f"{sanitized_student_id}.png")
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
                logging.info(f"Deleted cached image for student '{student_id}'.")
            except Exception as e:
                logging.error(f"Failed to delete cached image for student '{student_id}': {e}")

    def on_closing(self):
        """Handle closing the application."""
        if messagebox.askokcancel("Quit", "Do you really want to quit?"):
            if self.scanning:
                self.scanner.stop_scanning()
            self.master.destroy()

    # Methods for tab drag-and-drop
    def on_tab_press(self, event):
        """Handle tab press event for dragging."""
        x, y = event.x, event.y
        try:
            index = self.notebook.index("@%d,%d" % (x, y))
            self._drag_data = {"tab_index": index}
        except TclError:
            self._drag_data = {"tab_index": None}

    def on_tab_motion(self, event):
        """Handle tab dragging with the mouse."""
        x, y = event.x, event.y
        try:
            index = self.notebook.index("@%d,%d" % (x, y))
        except TclError:
            # No tab under cursor; do not proceed
            return

        # Only proceed if index is valid and different from the original
        if self._drag_data["tab_index"] is not None and index != self._drag_data["tab_index"]:
            self.swap_tabs(self._drag_data["tab_index"], index)
            self._drag_data["tab_index"] = index

    def on_tab_release(self, event):
        """Reset the drag data."""
        self._drag_data = {"tab_index": None}


    def swap_tabs(self, i, j):
        """Swap tabs at indices i and j."""
        # Get total number of tabs
        total_tabs = self.notebook.index("end")

        # Validate indices
        if i < 0 or j < 0 or i >= total_tabs or j >= total_tabs:
            return  # Indices out of bounds; do not proceed

        # Swap the tabs
        if i != j:
            # Remove tab at index i
            tab = self.notebook.tabs()[i]
            text = self.notebook.tab(tab, "text")
            # Store the tab content
            tab_content = self.notebook.nametowidget(tab)
            # Remove the tab
            self.notebook.forget(i)

            # Adjust index j if necessary
            if i < j:
                j -= 1  # Indices have shifted after removing tab at index i

            # Insert the tab at index j
            self.notebook.insert(j, tab_content)
            self.notebook.tab(tab_content, text=text)

    def setup_gui_logging(self):
        """Setup logging to display in the GUI."""
        # Create Logs tab if not already created
        if not hasattr(self, 'log_text_widget'):
            self.create_logs_tab()

        log_text_widget = self.log_text_widget

        class TextHandler(logging.Handler):
            """Logging handler to display logs in the Tkinter Text widget."""
            def __init__(self, text_widget):
                logging.Handler.__init__(self)
                self.text_widget = text_widget

            def emit(self, record):
                msg = self.format(record)
                def append():
                    self.text_widget.configure(state='normal')
                    self.text_widget.insert('end', msg + '\n')
                    self.text_widget.configure(state='disabled')
                    self.text_widget.see('end')
                self.text_widget.after(0, append)

        handler = TextHandler(log_text_widget)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

    def create_logs_tab(self):
        """Create a tab to display logs."""
        logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(logs_frame, text="Logs")

        log_text = tk.Text(logs_frame, wrap='word', state='disabled', width=80, height=20)
        log_text.pack(fill='both', expand=True)

        # Assign to instance variable
        self.log_text_widget = log_text