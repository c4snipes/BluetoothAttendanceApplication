# io_utils.py

import re
import logging
import time
import os
import csv
import threading
import queue
import pickle
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ==============================
# HTML Parsing Functions
# ==============================

def parse_html_file(html_file, valid_class_codes):
    """
    Parse an HTML file to extract classes/students.
    Returns a dict: { class_name: [ { 'name', 'student_id', 'email', 'photo_url'}, ... ], ... }
    """
    class_students = {}
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
    except Exception as e:
        logging.error(f"Failed to open/parse '{html_file}': {e}")
        return {}

    # Find headings that match valid class codes (e.g., "CSCI-101")
    headings = soup.find_all('h3')
    pattern = r'\b(' + '|'.join(valid_class_codes) + r')-\d{3}(?:-\d+)?(?:-\w+)?\b'

    for heading in headings:
        raw_text = heading.get_text(strip=True)
        match = re.search(pattern, raw_text)
        if match:
            class_name = match.group(0)
        else:
            continue

        table = heading.find_next_sibling('table')
        if not table:
            logging.warning(f"No <table> found after heading for '{class_name}'")
            continue

        tds = table.find_all('td', {'width': '180px'})
        st_list = []
        for td in tds:
            student = {}
            img_tag = td.find('img')
            if img_tag and 'src' in img_tag.attrs:
                student['photo_url'] = img_tag['src']
            else:
                student['photo_url'] = None

            parts = td.get_text(separator='|').split('|')
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) >= 1:
                student['name'] = parts[0]
            if len(parts) >= 2:
                student['student_id'] = parts[1]
            if len(parts) >= 3:
                student['email'] = parts[2]
            if not student['photo_url']:
                student['photo_url'] = generate_photo_url(student.get('name'), student.get('email')) or ""
            if 'name' not in student:
                logging.warning(f"Skipping entry with no name in {class_name}: {td}")
                continue
            st_list.append(student)
        if st_list:
            if class_name not in class_students:
                class_students[class_name] = []
            class_students[class_name].extend(st_list)
    return class_students

def is_valid_url(url, max_retries=3, backoff=1.0):
    """
    Return True if URL responds with HTTP 200.
    """
    if not url:
        return False
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, allow_redirects=True, timeout=5)
            if resp.status_code == 200:
                return True
            else:
                logging.error(f"is_valid_url: '{url}' responded with {resp.status_code}")
        except requests.exceptions.RequestException as e:
            logging.warning(f"Attempt {attempt} for '{url}' failed: {e}")
        if attempt < max_retries:
            time.sleep(backoff)
            backoff *= 2
    return False

def generate_photo_url(student_name, email=None):
    """
    Generate a candidate photo URL based on student name.
    """
    if not student_name:
        return None
    try:
        parts = student_name.strip().split()
        if len(parts) >= 2:
            first = parts[0].lower()
            last = ''.join(parts[1:]).lower()
            first_initial = first[0]
            base_filename = f"{last}{first_initial}"
            base_url = f"https://directoryphotos.example.edu/{base_filename}"
            if is_valid_url(base_url):
                return base_url
            for i in range(1, 6):
                candidate = f"{base_url}{i}"
                if is_valid_url(candidate):
                    return candidate
    except Exception as e:
        logging.error(f"Error generating photo URL: {e}")
    return None

# ==============================
# Import & Export Functionality
# ==============================

class ImportApp:
    """
    Manages importing class/student data from an HTML file in a background thread.
    """
    def __init__(self, attendance_manager, master=None, parent_gui=None):
        self.attendance_manager = attendance_manager
        self.master = master
        self.parent_gui = parent_gui
        self._import_queue = queue.Queue()
        self._thread = None
        self._progress_popup = None

    def import_html_action(self):
        file_path = filedialog.askopenfilename(
            title="Select HTML File",
            filetypes=[("HTML files", "*.html *.htm"), ("All files", "*.*")]
        )
        if not file_path:
            logging.info("User canceled HTML import.")
            return
        self._show_progress_popup("Importing from HTML...")
        self._thread = threading.Thread(
            target=self._parse_and_import,
            args=(file_path,),
            daemon=True
        )
        self._thread.start()
        self._check_thread_result()

    def _check_thread_result(self):
        try:
            success, msg, class_names = self._import_queue.get_nowait()
        except queue.Empty:
            if self.master:
                self.master.after(200, self._check_thread_result)
            return
        self._close_progress_popup()
        if success:
            if class_names:
                for cname in class_names:
                    if self.parent_gui and cname not in self.parent_gui.class_widgets:
                        self.parent_gui.create_class_tab(cname)
                messagebox.showinfo("Import Success", msg)
                logging.info(msg)
            else:
                messagebox.showwarning("No Classes Found", msg)
                logging.warning(msg)
        else:
            messagebox.showerror("Import Error", msg)
            logging.error(msg)

    def _parse_and_import(self, file_path):
        try:
            valid_codes = self.attendance_manager.get_valid_class_codes()
            class_students = parse_html_file(file_path, valid_codes)
            if class_students:
                for cname, stlist in class_students.items():
                    self.attendance_manager.register_class(cname)
                    for student in stlist:
                        if not student.get('photo_url'):
                            gen = generate_photo_url(student.get('name'), student.get('email'))
                            student['photo_url'] = gen or ""
                        if student['photo_url'] and not is_valid_url(student['photo_url']):
                            logging.warning(f"Invalid photo URL for {student.get('student_id')}: {student['photo_url']}")
                            student['photo_url'] = ""
                        if not student.get('student_id'):
                            logging.warning(f"Missing student_id in {cname}: {student}")
                            continue
                        try:
                            self.attendance_manager.add_student(cname, student)
                            logging.info(f"Imported {student['student_id']} in {cname}")
                        except Exception as e:
                            logging.error(f"Error adding {student['student_id']} to {cname}: {e}")
                msg = f"Students imported from '{file_path}'."
                self._import_queue.put((True, msg, list(class_students.keys())))
            else:
                msg = f"No valid classes found in '{file_path}'."
                self._import_queue.put((True, msg, []))
        except Exception as e:
            msg = f"Failed to import from '{file_path}': {e}"
            self._import_queue.put((False, msg, []))

    def _show_progress_popup(self, msg):
        if not self.master:
            return
        self._progress_popup = tk.Toplevel(self.master)
        self._progress_popup.title("Importing...")
        self._progress_popup.geometry("300x100")
        self._progress_popup.resizable(False, False)
        self._progress_popup.grab_set()
        label = tk.Label(self._progress_popup, text=msg)
        label.pack(pady=20, padx=20)
        self._progress_popup.protocol("WM_DELETE_WINDOW", lambda: None)
        self._progress_popup.update_idletasks()
        x = (self._progress_popup.winfo_screenwidth() - self._progress_popup.winfo_width()) // 2
        y = (self._progress_popup.winfo_screenheight() - self._progress_popup.winfo_height()) // 2
        self._progress_popup.geometry(f"+{x}+{y}")

    def _close_progress_popup(self):
        if self._progress_popup:
            self._progress_popup.destroy()
            self._progress_popup = None

class Disseminate:
    """
    Handles exporting attendance data to CSV or exporting MAC addresses to a text file.
    """
    def __init__(self, master, attendance_manager):
        self.master = master
        self.attendance_manager = attendance_manager

    def export_all_classes(self):
        directory = filedialog.askdirectory(title="Select Directory to Save CSVs")
        if directory:
            try:
                fields = self.select_export_fields()
                if not fields:
                    messagebox.showwarning("No Fields", "No fields chosen for export.")
                    logging.warning("User chose no fields to export.")
                    return
                for cname in self.attendance_manager.classes:
                    self.export_attendance(cname, directory, fields, bulk_export=True)
                messagebox.showinfo("Export Complete", "Exported all classes to CSV.")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))
                logging.error(f"export_all_classes error: {e}")
        else:
            logging.info("User canceled export_all_classes selection.")

    def export_attendance(self, class_name, directory=None, selected_fields=None, bulk_export=False):
        all_fields = ["Student ID", "Name", "MAC Addresses", "Time-Based Count", "Last Seen Time"]
        if not bulk_export and selected_fields is None:
            selected_fields = self.select_export_fields()
            if not selected_fields:
                return
        if bulk_export and selected_fields is None:
            logging.error("Bulk export requires selected_fields but got None.")
            return
        if directory:
            file_path = os.path.join(directory, f"{class_name}_attendance.csv")
        else:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialfile=f"{class_name}_attendance.csv",
                title="Save CSV As"
            )
        if not file_path:
            logging.info("User canceled single-class export.")
            return
        if not bulk_export and os.path.exists(file_path):
            if not messagebox.askyesno("Overwrite?", f"File '{os.path.basename(file_path)}' exists. Overwrite?"):
                return
        try:
            with open(file_path, "w", newline='', encoding='utf-8') as csvf:
                writer = csv.writer(csvf)
                writer.writerow(selected_fields if selected_fields is not None else [])
                students = self.attendance_manager.get_all_students(class_name)
                fields = selected_fields if selected_fields is not None else []
                for sid, sdata in students.items():
                    row = []
                    if "Student ID" in fields:
                        row.append(sid)
                    if "Name" in fields:
                        row.append(sdata.get("name", ""))
                    if "MAC Addresses" in fields:
                        macs = self.attendance_manager.classes[class_name]['student_mac_addresses'].get(sid, set())
                        if macs:
                            macs_list = [f"{mac} (Count: {self.attendance_manager.get_attendance_count_by_mac(mac)})" for mac in macs]
                            row.append(", ".join(macs_list))
                        else:
                            row.append("Unassigned")
                    if "Time-Based Count" in fields:
                        tcount = self.attendance_manager.get_time_based_count(class_name, sid)
                        row.append(tcount)
                    if "Last Seen Time" in fields:
                        ts = self.attendance_manager.classes[class_name]['attendance_timestamps'].get(sid)
                        row.append(ts.strftime('%Y-%m-%d %H:%M:%S') if ts else "Never")
                    writer.writerow(row)
            if bulk_export:
                logging.info(f"Exported '{class_name}' to '{file_path}'.")
            else:
                messagebox.showinfo("Exported", f"Exported '{class_name}' to '{file_path}'.")
        except Exception as e:
            logging.error(f"Failed to export {class_name}: {e}")
            messagebox.showerror("Export Error", str(e))

    def export_mac_addresses(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile="mac_addresses.txt",
            title="Save MAC Addresses As"
        )
        if not file_path:
            logging.info("User canceled MAC addresses export.")
            return
        try:
            assigned_macs = self.attendance_manager.get_all_assigned_macs()
            with open(file_path, "w", encoding='utf-8') as f:
                for mac in assigned_macs:
                    count = self.attendance_manager.get_attendance_count_by_mac(mac)
                    f.write(f"{mac} (Count: {count})\n")
            messagebox.showinfo("Exported", f"Exported MAC addresses to '{file_path}'.")
        except Exception as e:
            logging.error(f"Failed to export MAC addresses: {e}")
            messagebox.showerror("Export Error", str(e))

    def select_export_fields(self):
        fields = ["Student ID", "Name", "MAC Addresses", "Time-Based Count", "Last Seen Time"]
        selected = []
        popup = tk.Toplevel(self.master)
        popup.title("Select Export Fields")
        popup.geometry("320x300")
        popup.resizable(False, False)
        popup.grab_set()
        checks = {}
        frm = ttk.Frame(popup)
        frm.pack(pady=10, padx=10, anchor='w')
        for f in fields:
            var = tk.BooleanVar(value=True)
            cb = ttk.Checkbutton(frm, text=f, variable=var)
            cb.pack(anchor='w', pady=2)
            checks[f] = var
        btn_frame = ttk.Frame(popup)
        btn_frame.pack(pady=10)
        def on_confirm():
            chosen = [f for f, var in checks.items() if var.get()]
            if chosen:
                selected.extend(chosen)
                popup.destroy()
            else:
                messagebox.showwarning("No Fields", "Select at least one field to export.")
        def on_cancel():
            popup.destroy()
        def on_select_all():
            for var in checks.values():
                var.set(True)
        def on_deselect_all():
            for var in checks.values():
                var.set(False)
        export_btn = ttk.Button(btn_frame, text="Export", command=on_confirm)
        export_btn.grid(row=0, column=0, padx=5)
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=on_cancel)
        cancel_btn.grid(row=0, column=1, padx=5)
        sa_btn = ttk.Button(btn_frame, text="Select All", command=on_select_all)
        sa_btn.grid(row=1, column=0, padx=5, pady=5)
        da_btn = ttk.Button(btn_frame, text="Deselect All", command=on_deselect_all)
        da_btn.grid(row=1, column=1, padx=5, pady=5)
        popup.wait_window()
        return selected

# ==============================
# Persistence for Attendance Data
# (This section remains in the core data module)
# ==============================

class AttendanceManager:
    """
    Core class for managing attendance data.
    """
    def __init__(self, data_file='student_data.pkl', initial_scan_interval=10):
        self.lock = threading.RLock()
        self.data_file = data_file
        self.valid_class_codes = ["CSCI", "MENG", "EENG", "ENGR", "SWEN", "ISEN", "CIS"]
        self.classes = {}  # class_name: class_data_dict
        self.current_scan_interval = initial_scan_interval
        self.mac_scan_counts = {}  # Individual MAC counts
        self.blacklist = set()
        self.load_data()

    def _initialize_class_data(self):
        return {
            'students': {},
            'present_students': set(),
            'student_mac_addresses': {},
            'attendance_timestamps': {},
        }

    def _migrate_class_data(self):
        modified = False
        for class_name, class_data in self.classes.items():
            if 'students' not in class_data:
                class_data['students'] = {}
                modified = True
            if 'present_students' not in class_data:
                class_data['present_students'] = set()
                modified = True
            if 'student_mac_addresses' not in class_data:
                class_data['student_mac_addresses'] = {}
                modified = True
            if 'attendance_timestamps' not in class_data:
                class_data['attendance_timestamps'] = {}
                modified = True
        if modified:
            self.save_data()

    def load_data(self):
        with self.lock:
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, 'rb') as f:
                        self.classes = pickle.load(f)
                    self._migrate_class_data()
                    logging.info("Loaded attendance data successfully.")
                except Exception as e:
                    logging.error(f"Error loading data file: {e}")
                    self.classes = {}
            else:
                self.classes = {}
                logging.warning("No existing data file found. Starting fresh.")

    def save_data(self):
        with self.lock:
            try:
                with open(self.data_file, 'wb') as f:
                    pickle.dump(self.classes, f)
                logging.info("Saved attendance data successfully.")
            except Exception as e:
                logging.error(f"Error saving data file: {e}")

    def get_valid_class_codes(self):
        return self.valid_class_codes

    def add_class(self, class_name):
        if not class_name:
            logging.error("Class name cannot be empty.")
            raise ValueError("Class name cannot be empty.")
        with self.lock:
            if class_name not in self.classes:
                self.classes[class_name] = self._initialize_class_data()
                self.save_data()
                logging.info(f"Added new class: {class_name}")
            else:
                logging.warning(f"Class '{class_name}' already exists.")

    def register_class(self, class_name):
        self.add_class(class_name)

    def delete_class(self, class_name):
        if not class_name:
            logging.error("Class name cannot be empty.")
            raise ValueError("Class name cannot be empty.")
        with self.lock:
            if class_name in self.classes:
                del self.classes[class_name]
                self.save_data()
                logging.info(f"Deleted class: {class_name}")
            else:
                logging.warning(f"Attempted to delete non-existent class '{class_name}'.")

    def delete_database(self):
        with self.lock:
            self.classes = {}
            if os.path.exists(self.data_file):
                try:
                    os.remove(self.data_file)
                    logging.info("Deleted student database successfully.")
                except Exception as e:
                    logging.error(f"Error deleting data file: {e}")
            else:
                logging.warning("Data file does not exist. Nothing to delete.")

    def _generate_unique_student_id(self, class_name):
        existing_ids = set(self.classes[class_name]['students'].keys())
        new_id = 1
        while str(new_id) in existing_ids:
            new_id += 1
        return str(new_id)

    def add_student(self, class_name, student):
        try:
            if not class_name:
                logging.error("Class name cannot be empty.")
                raise ValueError("Class name cannot be empty.")
            if not isinstance(student, dict) or 'name' not in student:
                logging.error("Invalid student data provided.")
                raise ValueError("Invalid student data provided.")
            with self.lock:
                if class_name not in self.classes:
                    self.classes[class_name] = self._initialize_class_data()
                    logging.warning(f"Class '{class_name}' did not exist. Created new class.")
                student_id = student.get('student_id')
                if not student_id:
                    student_id = self._generate_unique_student_id(class_name)
                    student['student_id'] = student_id
                if student_id in self.classes[class_name]['students']:
                    self.classes[class_name]['students'][student_id].update(student)
                    logging.info(f"Updated student '{student_id}' in class '{class_name}'.")
                else:
                    self.classes[class_name]['students'][student_id] = student
                    logging.info(f"Added student '{student_id}' to class '{class_name}'.")
                device_address = student.get('device_address')
                if device_address:
                    self.assign_device_to_student(class_name, student_id, device_address)
                self.save_data()
        except Exception as e:
            logging.error(f"Error adding student to class '{class_name}': {e}")
            raise

    def assign_device_to_student(self, class_name, student_id, addr):
        try:
            if not class_name or not student_id or not addr:
                logging.error("Class name, student ID, and address cannot be empty.")
                raise ValueError("Class name, student ID, and address cannot be empty.")
            with self.lock:
                addr_upper = addr.upper()
                if addr_upper in self.blacklist:
                    self.blacklist.discard(addr_upper)
                    logging.info(f"Removed MAC {addr_upper} from blacklist due to assignment.")
                for cname, cdata in self.classes.items():
                    for sid, macs in cdata.get('student_mac_addresses', {}).items():
                        if addr_upper in macs and (cname != class_name or sid != student_id):
                            macs.discard(addr_upper)
                            logging.info(f"Removed MAC {addr_upper} from student '{sid}' in class '{cname}'.")
                            cdata['present_students'].discard(sid)
                            cdata['attendance_timestamps'].pop(sid, None)
                class_data = self.classes[class_name]
                class_data.setdefault('student_mac_addresses', {}).setdefault(student_id, set()).add(addr_upper)
                student_data = class_data['students'].get(student_id)
                if student_data:
                    student_data['manual_override'] = False
                class_data['present_students'].add(student_id)
                class_data['attendance_timestamps'][student_id] = datetime.now()
                self.save_data()
                logging.info(f"Assigned device {addr_upper} to student '{student_id}' in class '{class_name}'.")
        except Exception as e:
            logging.error(f"Error assigning device to student '{student_id}' in class '{class_name}': {e}")
            raise

    def get_all_students(self, class_name):
        if not class_name:
            logging.error("Class name cannot be empty.")
            return {}
        with self.lock:
            class_data = self.classes.get(class_name)
            if class_data:
                return class_data['students'].copy()
            else:
                logging.warning(f"Class '{class_name}' does not exist.")
                return {}

    def get_attendance_count_by_mac(self, mac):
        if not mac:
            return 0
        return self.mac_scan_counts.get(mac.upper(), 0)

    def get_time_based_count(self, class_name, student_id):
        count = 0
        with self.lock:
            class_data = self.classes.get(class_name)
            if class_data:
                macs = class_data.get('student_mac_addresses', {}).get(student_id, set())
                for mac in macs:
                    count += self.get_attendance_count_by_mac(mac)
        return count

    def load_blacklist(self, file_path):
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            for line in lines:
                mac = line.strip().upper()
                if mac:
                    self.blacklist.add(mac)
            logging.info(f"Loaded blacklist with {len(self.blacklist)} MAC addresses from '{file_path}'.")
        except Exception as e:
            logging.error(f"Error loading blacklist from '{file_path}': {e}")
            raise

    def get_blacklist(self):
        return self.blacklist
