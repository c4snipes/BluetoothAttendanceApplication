# gui.py

import os
import re
import threading
import logging
import requests
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from PIL import Image, ImageTk
from io import BytesIO
from datetime import datetime
from io_utils import AttendanceManager, ImportApp, Disseminate
from ui_components import (
    create_notebook,
    create_settings_tab,
    create_class_tab_widgets_with_photos,
    create_scrollable_frame,
    bind_tab_dragging,
    change_theme,
    ToolTip
)
from scanner import Scanner  # Assuming scanner.py is unchanged

class AttendanceApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Bluetooth-Based Attendance System")
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.image_cache = {}
        self.image_cache_dir = os.path.join(os.getcwd(), 'image_cache')
        if not os.path.exists(self.image_cache_dir):
            os.makedirs(self.image_cache_dir, exist_ok=True)

        self.scan_count = 0
        self.found_devices = {}

        # Initialize core components
        self.attendance_manager = AttendanceManager()
        self.importer = ImportApp(self.attendance_manager, master=self.master, parent_gui=self)
        self.disseminate = Disseminate(self.master, self.attendance_manager)
        self.scanner = Scanner(callback=self.handle_scan_results)
        self.scanning = False

        # Create notebook and tabs
        self.notebook = create_notebook(self.master)
        self.class_widgets = {}
        self.create_class_tabs()

        # Bind tab dragging (if desired)
        bind_tab_dragging(self.notebook, self.on_tab_press, self.on_tab_motion, self.on_tab_release)

    def create_class_tabs(self):
        for class_name in self.attendance_manager.classes.keys():
            self.create_class_tab(class_name)

        self.settings_widgets = create_settings_tab(
            self.notebook,
            self.attendance_manager.get_valid_class_codes(),
            list(self.attendance_manager.classes.keys())
        )
        self.connect_settings_actions()
        self.create_logs_tab()  # Optional, implement if needed

    def create_class_tab(self, class_name):
        class_frame = ttk.Frame(self.notebook)
        widgets_tuple = create_class_tab_widgets_with_photos(class_frame, self.attendance_manager)
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
        ) = widgets_tuple

        present_frame = create_scrollable_frame(present_frame_container)
        absent_frame = create_scrollable_frame(absent_frame_container)

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

        if self.scanning:
            scan_toggle_button.config(text="Stop Scanning")
        else:
            scan_toggle_button.config(text="Start Scanning")

        add_student_button.config(command=lambda: self.add_student_dialog(class_name))
        scan_toggle_button.config(command=self.toggle_scanning)
        export_button.config(command=lambda: self.disseminate.export_attendance(class_name))
        quit_button.config(command=self.on_closing)

        interval_var.trace_add('write', lambda *args: self.update_scan_interval(int(interval_var.get().split()[0])))
        rssi_var.trace_add('write', lambda *args: self.scanner.update_rssi_threshold(self.parse_rssi_value(rssi_var.get())))

        self.update_student_lists(class_name)
        self.notebook.add(class_frame, text=class_name)

    def connect_settings_actions(self):
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

        delete_button.config(command=self.delete_database)
        theme_combo.bind('<<ComboboxSelected>>', lambda e: change_theme(theme_combo.get()))
        add_class_button.config(command=lambda: self.add_class(class_entry.get()))
        add_code_button.config(command=lambda: self.add_class_code(new_code_entry.get(), valid_class_codes_var))
        import_html_button.config(command=self.import_html_action)
        export_all_button.config(command=self.disseminate.export_all_classes)
        delete_class_button.config(command=lambda: self.delete_class(class_combo.get()))

    def update_scan_interval(self, new_interval):
        self.scanner.update_scan_interval(new_interval)
        self.attendance_manager.current_scan_interval = new_interval
        logging.info(f"Scan interval updated to {new_interval} seconds.")

    def parse_rssi_value(self, rssi_string):
        match = re.search(r'>\s*(-\d+)\s*dBm', rssi_string)
        if match:
            return int(match.group(1))
        return -70

    def add_student_dialog(self, class_name):
        dialog = tk.Toplevel(self.master)
        dialog.title(f"Add Student to {class_name}")
        dialog.geometry("400x300")
        dialog.grab_set()

        ttk.Label(dialog, text="Student Name:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        name_entry = ttk.Entry(dialog, width=30)
        name_entry.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="Student ID (optional):").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        id_entry = ttk.Entry(dialog, width=30)
        id_entry.grid(row=1, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="Photo URL (optional):").grid(row=2, column=0, padx=10, pady=10, sticky="e")
        photo_entry = ttk.Entry(dialog, width=30)
        photo_entry.grid(row=2, column=1, padx=10, pady=10)

        def submit():
            name = name_entry.get().strip()
            student_id = id_entry.get().strip()
            photo_url = photo_entry.get().strip()
            if not name:
                messagebox.showwarning("Input Error", "Student name cannot be empty.")
                return
            student = {'name': name}
            if student_id:
                student['student_id'] = student_id
            if photo_url:
                student['photo_url'] = photo_url
            try:
                self.attendance_manager.add_student(class_name, student)
                messagebox.showinfo("Student Added", f"Student '{name}' added to class '{class_name}'.")
                dialog.destroy()
                self.update_student_lists(class_name)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add student: {e}")

        submit_button = ttk.Button(dialog, text="Add Student", command=submit)
        submit_button.grid(row=3, column=1, padx=10, pady=20)

    def delete_database(self):
        if messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete the entire student database?"):
            try:
                self.attendance_manager.delete_database()
                for class_name in list(self.class_widgets.keys()):
                    self.notebook.forget(self.class_widgets[class_name]['tab_frame'])
                    del self.class_widgets[class_name]
                self.settings_widgets['class_combo']['values'] = []
                messagebox.showinfo("Database Deleted", "Student database has been deleted.")
                logging.info("Student database has been deleted.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete database: {e}")

    def add_class(self, class_name):
        class_name = class_name.strip()
        if class_name:
            if class_name not in self.attendance_manager.classes:
                self.attendance_manager.add_class(class_name)
                self.create_class_tab(class_name)
                messagebox.showinfo("Class Added", f"Class '{class_name}' has been added.")
                new_names = list(self.attendance_manager.classes.keys())
                self.settings_widgets['class_combo']['values'] = new_names
            else:
                messagebox.showwarning("Duplicate Class", f"Class '{class_name}' already exists.")
        else:
            messagebox.showwarning("Input Error", "Class name cannot be empty.")

    def add_class_code(self, code, valid_class_codes_var):
        code = code.strip()
        if code:
            try:
                self.attendance_manager.valid_class_codes.append(code)
                valid_class_codes_display = [c for c in self.attendance_manager.get_valid_class_codes() if c.isalpha()]
                valid_class_codes_var.set(", ".join(valid_class_codes_display))
                messagebox.showinfo("Code Added", f"Class code '{code}' has been added.")
            except Exception as e:
                messagebox.showwarning("Input Error", str(e))
        else:
            messagebox.showwarning("Input Error", "Class code cannot be empty.")

    def import_html_action(self):
        self.importer.import_html_action()
        new_names = list(self.attendance_manager.classes.keys())
        self.settings_widgets['class_combo']['values'] = new_names

    def delete_class(self, class_name):
        if not class_name:
            messagebox.showwarning("No Class Selected", "Please select a class to delete.")
            return
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the class '{class_name}'?"):
            try:
                tab = self.class_widgets[class_name]['tab_frame']
                self.notebook.forget(tab)
                self.attendance_manager.delete_class(class_name)
                del self.class_widgets[class_name]
                new_names = list(self.attendance_manager.classes.keys())
                self.settings_widgets['class_combo']['values'] = new_names
                messagebox.showinfo("Class Deleted", f"Class '{class_name}' has been deleted.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete class: {e}")

    def toggle_scanning(self):
        try:
            if self.scanning:
                self.scanning = False
                self.scanner.stop_scanning()
                for cw in self.class_widgets.values():
                    cw['scan_toggle_button'].config(text="Start Scanning")
            else:
                self.scanning = True
                self.scanner.start_scanning()
                for cw in self.class_widgets.values():
                    cw['scan_toggle_button'].config(text="Stop Scanning")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle scanning: {e}")

    def handle_scan_results(self, found_devices):
        self.master.after(0, self._on_scan_results, found_devices)

    def _on_scan_results(self, found_devices):
        try:
            self.found_devices = found_devices
            self.scan_count += 1
            # self.attendance_manager.update_attendance(found_devices)
            for class_name in self.class_widgets.keys():
                self.update_student_lists(class_name)
        except Exception as e:
            logging.error(f"Error handling scan results: {e}")

    def update_student_lists(self, class_name):
        widgets_dict = self.class_widgets[class_name]
        for widget in widgets_dict['present_frame'].winfo_children():
            widget.destroy()
        for widget in widgets_dict['absent_frame'].winfo_children():
            widget.destroy()
        widgets_dict['present_student_widgets'].clear()
        widgets_dict['absent_student_widgets'].clear()
        all_students = self.attendance_manager.get_all_students(class_name)
        present_students = self.attendance_manager.classes[class_name]['present_students']
        for sid, sdata in all_students.items():
            if sid in present_students:
                frame = widgets_dict['present_frame']
                key = 'present_student_widgets'
            else:
                frame = widgets_dict['absent_frame']
                key = 'absent_student_widgets'
            student_widget = self.create_student_widget(frame, class_name, sid, sdata)
            widgets_dict[key][sid] = student_widget

    def create_student_widget(self, parent, class_name, student_id, student_data):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", padx=5, pady=5)
        image_label = tk.Label(frame)
        image_label.grid(row=0, column=0, rowspan=2, padx=5, pady=5, sticky="nw")
        if student_id in self.image_cache:
            photo = self.image_cache[student_id]
            image_label.config(image=photo)
            image_label.image = photo  # type: ignore
        else:
            photo = self.get_student_image(student_data, image_label)
            self.image_cache[student_id] = photo
        info_text = f"{student_data.get('name', 'Unknown')} (ID: {student_id})"
        info_label = ttk.Label(frame, text=info_text, wraplength=200)
        info_label.grid(row=0, column=1, sticky="w")
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=0, column=2, rowspan=2, padx=5, pady=5, sticky="ne")
        assign_btn = ttk.Button(btn_frame, text="Assign Device")
        assign_btn.pack(fill="x", pady=2)
        assign_btn.config(command=lambda: self.show_device_combobox(btn_frame, class_name, student_id, assign_btn))
        present_students = self.attendance_manager.classes[class_name]['present_students']
        if student_id in present_students:
            mark_btn = ttk.Button(btn_frame, text="Mark Absent")
            mark_btn.config(command=lambda: self.mark_student_absent(class_name, student_id))
        else:
            mark_btn = ttk.Button(btn_frame, text="Mark Present")
            mark_btn.config(command=lambda: self.mark_student_present(class_name, student_id))
        mark_btn.pack(fill="x", pady=2)
        delete_btn = ttk.Button(btn_frame, text="✕", width=3)
        delete_btn.pack(pady=2)
        delete_btn.config(command=lambda: self.delete_student_dialog(class_name, student_id))
        return frame

    def show_device_combobox(self, parent, class_name, student_id, assign_btn):
        assign_btn.pack_forget()
        device_mapping = {}
        display_values = []
        for mac in self.found_devices.keys():
            count = self.attendance_manager.get_attendance_count_by_mac(mac)
            short_mac = mac[-8:]
            display = f"{short_mac} (Count: {count})"
            device_mapping[display] = mac
            display_values.append(display)
        device_var = tk.StringVar()
        device_combobox = ttk.Combobox(parent, textvariable=device_var, values=display_values, state="readonly")
        device_combobox.pack(side="left", padx=2)
        def assign_device():
            chosen = device_var.get().strip()
            if chosen:
                full_mac = device_mapping.get(chosen)
                if full_mac:
                    self.attendance_manager.assign_device_to_student(class_name, student_id, full_mac)
                    messagebox.showinfo("Device Assigned", f"Device '{chosen}' assigned to student '{student_id}'.")
            else:
                messagebox.showwarning("No Device Selected", "Select a device to assign.")
            device_combobox.destroy()
            confirm_btn.destroy()
            assign_btn.pack(side="left", padx=2)
            student_data = self.attendance_manager.get_all_students(class_name).get(student_id)
            if student_data:
                student_data['manual_override'] = False
                self.attendance_manager.save_data()
                self.update_student_lists(class_name)
        confirm_btn = ttk.Button(parent, text="Assign", command=assign_device)
        confirm_btn.pack(side="left", padx=2)

    def get_student_image(self, student, label, size=(100, 100)):
        student_id = student.get('student_id') or "unknown"
        photo_url = student.get('photo_url')
        sanitized_id = "".join(c for c in student_id if c.isalnum())
        cache_file = os.path.join(self.image_cache_dir, f"{sanitized_id}.png")
        if os.path.exists(cache_file):
            try:
                from PIL import Image
                with Image.open(cache_file) as img:
                            resized = img.resize(size, Image.Resampling.LANCZOS)
                            photo = ImageTk.PhotoImage(resized)
                            label.config(image=photo)
                            label.image = photo
                            return photo
            except Exception as e:
                logging.warning(f"Error loading cached image for '{student_id}': {e}")
        if photo_url:
            try:
                response = requests.get(photo_url, timeout=5)
                response.raise_for_status()
                from PIL import Image
                from io import BytesIO
                with Image.open(BytesIO(response.content)) as img:
                    resized = img.resize(size, Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(resized)
                    label.config(image=photo)
                    label.image = photo
                    try:
                        resized.save(cache_file, format="PNG")
                    except Exception as save_err:
                        logging.error(f"Error saving image for '{student_id}': {save_err}")
                    return photo
            except Exception as e:
                logging.error(f"Error downloading image for '{student_id}': {e}")
        placeholder = self.get_placeholder_image()
        label.config(image=placeholder)
        label.image = placeholder
        return placeholder

    def get_placeholder_image(self):
        if not hasattr(self, 'placeholder_image'):
            from PIL import Image
            image = Image.new('RGB', (100, 100), color='gray')
            self.placeholder_image = ImageTk.PhotoImage(image)
        return self.placeholder_image

    def mark_student_present(self, class_name, student_id):
        try:
            with self.attendance_manager.lock:
                self.attendance_manager.classes[class_name]['present_students'].add(student_id)
                self.attendance_manager.save_data()
            self.update_student_lists(class_name)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to mark student present: {e}")
    
    def mark_student_absent(self, class_name, student_id):
        try:
            with self.attendance_manager.lock:
                self.attendance_manager.classes[class_name]['present_students'].discard(student_id)
                self.attendance_manager.save_data()
            self.update_student_lists(class_name)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to mark student absent: {e}")

    def delete_student_dialog(self, class_name, student_id):
        if messagebox.askyesno("Delete Student", f"Delete student '{student_id}' from class '{class_name}'?"):
            try:
                with self.attendance_manager.lock:
                    class_data = self.attendance_manager.classes.get(class_name)
                    if class_data:
                        class_data['students'].pop(student_id, None)
                        class_data.get('student_mac_addresses', {}).pop(student_id, None)
                        class_data['present_students'].discard(student_id)
                        class_data['attendance_timestamps'].pop(student_id, None)
                        self.attendance_manager.save_data()
                messagebox.showinfo("Student Deleted", f"Student '{student_id}' has been deleted.")
                self.update_student_lists(class_name)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete student: {e}")

    def create_logs_tab(self):
        # Optional: Implement logs tab if desired
        pass

    def on_tab_press(self, event):
        # Optional: Implement tab dragging if desired
        pass

    def on_tab_motion(self, event):
        # Optional: Implement tab dragging if desired
        pass

    def on_tab_release(self, event):
        # Optional: Implement tab dragging if desired
        pass

    def on_closing(self):
        if self.scanning:
            self.scanner.stop_scanning()
        self.master.destroy()
