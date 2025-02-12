# attendance.py

import pickle
import threading
import os
import logging
from collections import defaultdict
from datetime import datetime
import copy

class AttendanceManager:
    """
    The core data model for tracking classes, students, and assigned MAC addresses.
    MAC addresses are stored along with the scan count when they were first seen.
    Also supports a blacklist for devices known not to belong to students.
    """

    def __init__(self, data_file='student_data.pkl', initial_scan_interval=10):
        self.lock = threading.RLock()  # ensures thread safety on read/write
        self.data_file = data_file
        self.class_codes = ["CSCI", "MENG", "EENG", "ENGR", "SWEN", "ISEN", "CIS"]
        self.classes = {}  # Mapping: class_name -> class_data dictionary
        self.current_scan_interval = initial_scan_interval
        self.blacklisted_macs = set()  # Set of MAC addresses to ignore
        self._load_database()

    def _initialize_class_data(self):
        """
        Returns a dictionary for a new class's data.
        'student_mac_addresses' now maps each student_id to a dictionary:
          { MAC_address: first_seen_scan_count, ... }
        """
        return {
            'students': {},                 # student_id -> student data dict
            'present_students': set(),      # set of student_ids currently present
            'student_mac_addresses': defaultdict(dict),  # student_id -> { mac: scan_count, ... }
            'attendance_timestamps': {},    # student_id -> datetime of first detection
        }

    def _load_database(self):
        """
        Load the persistent data (classes, class_codes, scan interval, and blacklist) from disk.
        """
        with self.lock:
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, 'rb') as f:
                        data = pickle.load(f)
                    if isinstance(data, dict) and "classes" in data:
                        self.classes = data.get("classes", {})
                        self.class_codes = data.get("class_codes", self.class_codes)
                        self.current_scan_interval = data.get("current_scan_interval", self.current_scan_interval)
                        self.blacklisted_macs = set(data.get("blacklisted_macs", []))
                    else:
                        # Fallback if the file was saved using an older format.
                        self.classes = data
                    logging.info("Loaded attendance data successfully.")
                except Exception as e:
                    logging.error(f"Error loading data file: {e}")
                    self.classes = {}
                    self.blacklisted_macs = set()
            else:
                logging.warning("No existing data file found; starting fresh.")
                self.classes = {}
                self.blacklisted_macs = set()

    def _save_database(self):
        """
        Save the current data (classes, class codes, scan interval, and blacklist) to disk.
        """
        with self.lock:
            try:
                data = {
                    "classes": self.classes,
                    "class_codes": self.class_codes,
                    "current_scan_interval": self.current_scan_interval,
                    "blacklisted_macs": list(self.blacklisted_macs)
                }
                with open(self.data_file, 'wb') as f:
                    pickle.dump(data, f)
                logging.info("Saved attendance data successfully.")
            except Exception as e:
                logging.error(f"Error saving data file: {e}")

    def register_class(self, class_name):
        """
        Create a new class if it doesn't already exist.
        :param class_name: e.g. "CSCI-101"
        """
        if not class_name:
            raise ValueError("Class name cannot be empty.")
        with self.lock:
            if class_name not in self.classes:
                self.classes[class_name] = self._initialize_class_data()
                self._save_database()
                logging.info(f"Registered new class: {class_name}")
            else:
                logging.warning(f"Class '{class_name}' already exists.")

    def remove_class(self, class_name):
        """
        Completely remove a class and all associated data.
        :param class_name: Name of the class to remove.
        """
        if not class_name:
            raise ValueError("Class name cannot be empty.")
        with self.lock:
            if class_name in self.classes:
                del self.classes[class_name]
                self._save_database()
                logging.info(f"Removed class '{class_name}'.")
            else:
                logging.warning(f"Class '{class_name}' not found to remove.")

    def purge_database(self):
        """
        Delete all in-memory data and remove the persistent file.
        """
        with self.lock:
            self.classes = {}
            self.blacklisted_macs = set()
            if os.path.exists(self.data_file):
                try:
                    os.remove(self.data_file)
                    logging.info("Deleted database file.")
                except Exception as e:
                    logging.error(f"Error removing database file: {e}")

    def _generate_unique_student_id(self, class_name):
        """
        Generate a new numeric student ID for the given class.
        """
        cdata = self.classes[class_name]
        existing_ids = cdata['students'].keys()
        new_id = 1
        while str(new_id) in existing_ids:
            new_id += 1
        return str(new_id)

    def add_student(self, class_name, student_data):
        """
        Add or update a student in the specified class.
        :param class_name: Name of the class.
        :param student_data: Dict of student info (must include 'name').
        """
        if not class_name:
            raise ValueError("Class name is required.")
        if 'name' not in student_data:
            raise ValueError("student_data must include 'name'.")
        with self.lock:
            if class_name not in self.classes:
                logging.warning(f"Class '{class_name}' not found; creating it automatically.")
                self.classes[class_name] = self._initialize_class_data()
            cdict = self.classes[class_name]
            sid = student_data.get('student_id') or self._generate_unique_student_id(class_name)
            student_data['student_id'] = sid
            if sid in cdict['students']:
                cdict['students'][sid].update(student_data)
                logging.info(f"Updated student '{sid}' in class '{class_name}'.")
            else:
                cdict['students'][sid] = student_data
                logging.info(f"Added new student '{sid}' to class '{class_name}'.")
            # If a device_address is provided, assign it
            dev_addr = student_data.get('device_address')
            if dev_addr:
                self.assign_mac_to_student(class_name, sid, dev_addr)
            self._save_database()

    def remove_student(self, class_name, student_id):
        """
        Remove a student from the specified class.
        """
        with self.lock:
            if class_name not in self.classes:
                raise ValueError(f"Class '{class_name}' does not exist.")
            cdict = self.classes[class_name]
            if student_id not in cdict['students']:
                raise ValueError(f"Student '{student_id}' not found in class '{class_name}'.")
            # Remove assigned MACs, presence data, and timestamps
            cdict['student_mac_addresses'].pop(student_id, None)
            cdict['present_students'].discard(student_id)
            cdict['attendance_timestamps'].pop(student_id, None)
            del cdict['students'][student_id]
            self._save_database()
            logging.info(f"Removed student '{student_id}' from class '{class_name}'.")

    def assign_mac_to_student(self, class_name, student_id, mac_address, scan_count=0):
        """
        Assign a MAC address (with its first-seen scan count) to a student.
        Unassigns the MAC from any other student if necessary.
        :param class_name: The class name.
        :param student_id: The student's ID.
        :param mac_address: The MAC address to assign.
        :param scan_count: The scan count when the MAC was first seen.
        """
        if not class_name or not student_id or not mac_address:
            raise ValueError("class_name, student_id, and mac_address are required.")
        mac_up = mac_address.upper()
        with self.lock:
            # Unassign the MAC from any other student
            for cname, cdata in self.classes.items():
                for sid, macs in cdata['student_mac_addresses'].items():
                    if mac_up in macs and (cname != class_name or sid != student_id):
                        del macs[mac_up]
            cdict = self.classes[class_name]
            cdict['student_mac_addresses'][student_id][mac_up] = scan_count
            s_info = cdict['students'].get(student_id)
            if s_info:
                s_info['manual_override'] = False  # reset any manual override
            self._save_database()
            logging.info(f"Assigned MAC {mac_up} (Count: {scan_count}) to student '{student_id}' in '{class_name}'.")

    def unassign_mac_from_student(self, class_name, student_id, mac_address):
        """
        Remove a MAC address from a student's record.
        """
        mac_up = mac_address.upper()
        with self.lock:
            if class_name not in self.classes:
                raise ValueError(f"Class '{class_name}' does not exist.")
            cdict = self.classes[class_name]
            assigned = cdict['student_mac_addresses'].get(student_id, {})
            if mac_up in assigned:
                del assigned[mac_up]
                cdict['present_students'].discard(student_id)
                cdict['attendance_timestamps'].pop(student_id, None)
                logging.info(f"Removed MAC {mac_up} from student '{student_id}' in '{class_name}'.")
                self._save_database()

    def list_macs_for_student(self, class_name, student_id):
        """
        Return a dictionary mapping assigned MAC addresses to their first-seen scan counts.
        """
        with self.lock:
            if class_name in self.classes:
                return dict(self.classes[class_name]['student_mac_addresses'].get(student_id, {}))
            return {}

    # --- Blacklist Methods ---

    def blacklist_mac(self, mac):
        """
        Add a MAC address to the blacklist and unassign it from any student.
        :param mac: The MAC address to blacklist.
        """
        mac = mac.upper()
        with self.lock:
            self.blacklisted_macs.add(mac)
            for cname, cdata in self.classes.items():
                for sid, macs in cdata['student_mac_addresses'].items():
                    if mac in macs:
                        del macs[mac]
            self._save_database()
            logging.info(f"Blacklisted MAC: {mac}")

    def remove_blacklisted_mac(self, mac):
        """
        Remove a MAC address from the blacklist.
        """
        mac = mac.upper()
        with self.lock:
            if mac in self.blacklisted_macs:
                self.blacklisted_macs.remove(mac)
                self._save_database()
                logging.info(f"Removed {mac} from blacklist.")

    def get_blacklisted_macs(self):
        """
        Return the set of blacklisted MAC addresses.
        """
        with self.lock:
            return set(self.blacklisted_macs)

    # --- Presence and Attendance Methods ---

    def mark_as_present(self, class_name, student_id):
        """
        Manually mark a student as present.
        """
        with self.lock:
            if class_name not in self.classes:
                raise ValueError(f"Class '{class_name}' does not exist.")
            cdict = self.classes[class_name]
            if student_id not in cdict['students']:
                raise ValueError(f"Student '{student_id}' not found in '{class_name}'.")
            cdict['present_students'].add(student_id)
            cdict['attendance_timestamps'][student_id] = datetime.now()
            cdict['students'][student_id]['manual_override'] = True
            self._save_database()
            logging.info(f"Manually marked '{student_id}' PRESENT in '{class_name}'.")

    def mark_as_absent(self, class_name, student_id):
        """
        Manually mark a student as absent.
        """
        with self.lock:
            if class_name not in self.classes:
                raise ValueError(f"Class '{class_name}' does not exist.")
            cdict = self.classes[class_name]
            if student_id not in cdict['students']:
                raise ValueError(f"Student '{student_id}' not found in '{class_name}'.")
            cdict['present_students'].discard(student_id)
            cdict['attendance_timestamps'].pop(student_id, None)
            cdict['students'][student_id]['manual_override'] = True
            self._save_database()
            logging.info(f"Manually marked '{student_id}' ABSENT in '{class_name}'.")

    def update_from_scan(self, found_devices):
        """
        Update presence data based on discovered devices.
        :param found_devices: A dict mapping MAC addresses to device info.
        (Note: Devices in the blacklist should already be filtered out.)
        """
        if not isinstance(found_devices, dict):
            logging.error("found_devices must be a dict, skipping update_from_scan.")
            return
        current_time = datetime.now()
        with self.lock:
            for cname, cdata in self.classes.items():
                newly_present = set()
                for sid, macs in cdata['student_mac_addresses'].items():
                    s_info = cdata['students'].get(sid)
                    override = s_info.get('manual_override', False) if s_info else False
                    if override and sid in cdata['present_students']:
                        newly_present.add(sid)
                        continue
                    for mac in macs.keys():
                        if mac in found_devices:
                            newly_present.add(sid)
                            break
                cdata['present_students'] |= newly_present
                for sid in newly_present:
                    if sid not in cdata['attendance_timestamps']:
                        cdata['attendance_timestamps'][sid] = current_time
            self._save_database()
            logging.info("Updated attendance from scan results.")

    def get_all_students(self, class_name):
        """
        Return a copy of all student records for a class.
        """
        with self.lock:
            if class_name in self.classes:
                return copy.deepcopy(self.classes[class_name]['students'])
            return {}

    def get_present_students(self, class_name):
        """
        Return the set of student IDs currently marked as present.
        """
        with self.lock:
            if class_name in self.classes:
                return set(self.classes[class_name]['present_students'])
            return set()

    def get_attendance_timestamp(self, class_name, student_id):
        """
        Return the last seen timestamp (as a datetime) for a student.
        """
        with self.lock:
            if class_name not in self.classes:
                return None
            return self.classes[class_name]['attendance_timestamps'].get(student_id)

    def get_time_based_count(self, class_name, student_id):
        """
        Calculate the number of scan intervals that have passed since the student was first seen.
        """
        with self.lock:
            if class_name not in self.classes:
                return 0
            cdata = self.classes[class_name]
            if student_id not in cdata['attendance_timestamps']:
                return 0
            ts = cdata['attendance_timestamps'][student_id]
            elapsed = (datetime.now() - ts).total_seconds()
            if self.current_scan_interval <= 0:
                return 0
            intervals = max(1, int(elapsed / self.current_scan_interval))
            return intervals

    # --- Class Code and Scan Interval Methods ---

    def get_class_codes(self):
        """
        Return a list of valid class codes.
        """
        with self.lock:
            return list(self.class_codes)

    def register_class_code(self, code):
        """
        Add a new class code (e.g. 'MATH' or 'BIOL') if it doesn't already exist.
        :param code: The code to add.
        """
        code = code.strip().upper()
        with self.lock:
            if code and code not in self.class_codes:
                self.class_codes.append(code)
                self._save_database()
                logging.info(f"Registered new class code: {code}")
            else:
                raise ValueError(f"Class code '{code}' is invalid or already exists.")

    def set_scan_interval(self, new_interval):
        """
        Set a new scan interval (in seconds) for time-based attendance calculations.
        :param new_interval: The new scan interval (must be positive).
        """
        if new_interval <= 0:
            raise ValueError("Scan interval must be positive.")
        with self.lock:
            old = self.current_scan_interval
            self.current_scan_interval = new_interval
            logging.info(f"Scan interval changed from {old} to {new_interval}.")
            self._save_database()
