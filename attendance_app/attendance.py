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
    The core data model for tracking classes, students, and assigned MACs.
    Includes methods for adding/removing classes & students, marking attendance,
    and saving/loading from a pickle database file.
    """

    def __init__(self, data_file='student_data.pkl', initial_scan_interval=10):
        """
        Initialize the AttendanceManager.
        :param data_file: Path to the pickle file storing class data.
        :param initial_scan_interval: Default time interval (in seconds) for scanning-based logic.
        """
        self.lock = threading.RLock()  # ensures thread safety on read/write
        self.data_file = data_file
        self.class_codes = ["CSCI", "MENG", "EENG", "ENGR", "SWEN", "ISEN", "CIS"]
        self.classes = {}  # dict: class_name -> dict with students, present, etc.
        self.current_scan_interval = initial_scan_interval
        self._load_database()

    def _initialize_class_data(self):
        """
        Creates and returns a dict for storing all necessary info about a single class.
        """
        return {
            'students': {},                 # student_id -> { 'name', 'photo_url', etc.}
            'present_students': set(),      # set of student_ids currently marked present
            'student_mac_addresses': defaultdict(set),  # student_id -> set of MACs
            'attendance_timestamps': {},    # student_id -> last seen datetime
        }

    def _load_database(self):
        """
        Attempt to load class data from the pickle file. If it doesn't exist or fails, we start fresh.
        """
        with self.lock:
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, 'rb') as f:
                        self.classes = pickle.load(f)
                    logging.info("Loaded attendance data successfully.")
                except Exception as e:
                    logging.error(f"Error loading data file: {e}")
                    self.classes = {}
            else:
                logging.warning("No existing data file found; starting fresh.")
                self.classes = {}

    def _save_database(self):
        """
        Save current data state to the pickle file in a thread-safe manner.
        """
        with self.lock:
            try:
                with open(self.data_file, 'wb') as f:
                    pickle.dump(self.classes, f)
                logging.info("Saved attendance data successfully.")
            except Exception as e:
                logging.error(f"Error saving data file: {e}")

    def register_class(self, class_name):
        """
        Create a new class if it doesn't exist already.
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
        Completely remove a class and all associated data (students, MACs, etc.).
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
        Delete all data in memory and on disk. Also remove any cached images if present.
        """
        with self.lock:
            self.classes = {}
            # Attempt to remove the pickle file
            if os.path.exists(self.data_file):
                try:
                    os.remove(self.data_file)
                    logging.info("Deleted database file.")
                except Exception as e:
                    logging.error(f"Error removing database file: {e}")
            else:
                logging.warning("No data file to remove.")

            # Attempt to remove the image_cache directory
            img_dir = os.path.join(os.getcwd(), 'image_cache')
            if os.path.exists(img_dir):
                import shutil
                try:
                    shutil.rmtree(img_dir)
                    logging.info("Removed the image_cache folder.")
                except Exception as e:
                    logging.error(f"Error removing image cache: {e}")

    def _generate_unique_student_id(self, class_name):
        """
        Generate a new numeric student ID for the given class, ensuring no collisions.
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
        :param class_name: Name of the class to which we add a student.
        :param student_data: Dict of student info (must contain 'name').
        """
        if not class_name:
            raise ValueError("Class name is required.")
        if 'name' not in student_data:
            raise ValueError("student_data must include 'name'.")

        with self.lock:
            # If the class doesn't exist, create it automatically (with a warning)
            if class_name not in self.classes:
                logging.warning(f"Class '{class_name}' not found; creating it automatically.")
                self.classes[class_name] = self._initialize_class_data()

            cdict = self.classes[class_name]
            sid = student_data.get('student_id') or self._generate_unique_student_id(class_name)
            student_data['student_id'] = sid

            # Check if we're updating an existing student or adding a new one
            if sid in cdict['students']:
                cdict['students'][sid].update(student_data)
                logging.info(f"Updated student '{sid}' in class '{class_name}'.")
            else:
                cdict['students'][sid] = student_data
                logging.info(f"Added new student '{sid}' to class '{class_name}'.")

            # Assign MAC if 'device_address' is provided
            dev_addr = student_data.get('device_address')
            if dev_addr:
                self.assign_mac_to_student(class_name, sid, dev_addr)

            self._save_database()

    def remove_student(self, class_name, student_id):
        """
        Remove a student from the specified class, including MAC addresses and presence data.
        :param class_name: Name of the class
        :param student_id: ID of the student to remove
        """
        with self.lock:
            if class_name not in self.classes:
                raise ValueError(f"Class '{class_name}' does not exist.")
            cdict = self.classes[class_name]
            if student_id not in cdict['students']:
                raise ValueError(f"Student '{student_id}' not found in class '{class_name}'.")

            # Remove all MAC addresses associated with the student
            macs = cdict['student_mac_addresses'].pop(student_id, set())
            for mac in macs:
                logging.info(f"Removing MAC {mac} from student '{student_id}' in '{class_name}'.")

            # Remove them from present_students and timestamps
            cdict['present_students'].discard(student_id)
            cdict['attendance_timestamps'].pop(student_id, None)

            # Finally remove the student record
            del cdict['students'][student_id]
            self._save_database()
            logging.info(f"Removed student '{student_id}' from class '{class_name}'.")

    def assign_mac_to_student(self, class_name, student_id, mac_address):
        """
        Assign a MAC address to a student, ensuring it's not assigned to another student.
        If it is, we unassign from that other student first.
        :param class_name: The class of the student
        :param student_id: The student's ID
        :param mac_address: The MAC address to assign
        """
        if not class_name or not student_id or not mac_address:
            raise ValueError("class_name, student_id, and mac_address are required.")
        mac_up = mac_address.upper()

        with self.lock:
            if class_name not in self.classes:
                raise ValueError(f"Class '{class_name}' does not exist.")

            # Unassign the MAC from any student in any class, if already assigned
            for cname, cdata in self.classes.items():
                for sid, macs in cdata['student_mac_addresses'].items():
                    if mac_up in macs and (cname != class_name or sid != student_id):
                        macs.discard(mac_up)
                        cdata['present_students'].discard(sid)
                        cdata['attendance_timestamps'].pop(sid, None)
                        logging.info(f"Removed MAC {mac_up} from student '{sid}' in '{cname}'.")

            # Now assign to the correct student
            cdict = self.classes[class_name]
            cdict['student_mac_addresses'][student_id].add(mac_up)
            s_info = cdict['students'].get(student_id)
            if s_info:
                # Reset manual override so scanning can affect them again
                s_info['manual_override'] = False

            self._save_database()
            logging.info(f"Assigned MAC {mac_up} to student '{student_id}' in '{class_name}'.")

    def unassign_mac_from_student(self, class_name, student_id, mac_address):
        """
        Remove a MAC address from a student's record, without assigning it elsewhere.
        :param class_name: The class of the student
        :param student_id: The student's ID
        :param mac_address: The MAC address to remove
        """
        mac_up = mac_address.upper()
        with self.lock:
            if class_name not in self.classes:
                raise ValueError(f"Class '{class_name}' does not exist.")

            cdict = self.classes[class_name]
            assigned = cdict['student_mac_addresses'].get(student_id, set())

            if mac_up in assigned:
                assigned.discard(mac_up)
                # Possibly also remove presence/timestamp so they're not present
                cdict['present_students'].discard(student_id)
                cdict['attendance_timestamps'].pop(student_id, None)
                logging.info(f"Removed MAC {mac_up} from student '{student_id}' in '{class_name}'.")
                self._save_database()

    def mark_as_present(self, class_name, student_id):
        """
        Manually mark a student as present, overriding scanning logic.
        :param class_name: The class in which to mark presence
        :param student_id: The student ID to mark present
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
        Manually mark a student as absent, overriding scanning logic.
        :param class_name: The class in which to mark absence
        :param student_id: The student ID to mark absent
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

    def get_class_codes(self):
        """
        Return a list copy of valid class codes currently recognized (like CSCI, MENG).
        """
        with self.lock:
            return list(self.class_codes)

    def register_class_code(self, code):
        """
        Add a new valid class code, e.g. 'MATH' or 'BIOL', used for detecting classes when importing.
        """
        code = code.strip().upper()
        with self.lock:
            if code and code not in self.class_codes:
                self.class_codes.append(code)
                logging.info(f"Registered new class code: {code}")
            else:
                raise ValueError(f"Class code '{code}' is invalid or already exists.")

    def set_scan_interval(self, new_interval):
        """
        Change how many seconds we treat as a scan interval for time-based counts.
        :param new_interval: The new scanning interval in seconds (must be > 0).
        """
        if new_interval <= 0:
            raise ValueError("Scan interval must be positive.")
        with self.lock:
            old = self.current_scan_interval
            self.current_scan_interval = new_interval
            logging.info(f"Scan interval changed from {old} to {new_interval}.")

    def update_from_scan(self, found_devices):
        """
        Update presence data based on newly discovered devices. If a student's MAC is in found_devices
        (and not manually overridden absent), mark them present. 
        :param found_devices: dict => {mac_upper: {name, rssi, timestamp, scan_count}, ...}
        """
        if not isinstance(found_devices, dict):
            logging.error("found_devices must be a dict, skipping update_from_scan.")
            return

        current_time = datetime.now()

        with self.lock:
            for cname, cdict in self.classes.items():
                newly_present = set()
                for sid, macs in cdict['student_mac_addresses'].items():
                    s_info = cdict['students'].get(sid)
                    override = False
                    if s_info:
                        override = s_info.get('manual_override', False)

                    # If manually overridden present, keep them present no matter what
                    if override and sid in cdict['present_students']:
                        newly_present.add(sid)
                        continue

                    # Else, check if at least one assigned MAC was found
                    for mac in macs:
                        if mac in found_devices:
                            newly_present.add(sid)
                            break

                # Instead of overwriting, we union so they remain present if they were previously present
                cdict['present_students'] |= newly_present

                # Update timestamps only for those newly discovered as present this cycle
                for sid in newly_present:
                    if sid not in cdict['attendance_timestamps']:
                        cdict['attendance_timestamps'][sid] = current_time

            self._save_database()
            logging.info("Updated attendance from scan results.")

    def get_all_students(self, class_name):
        """
        Return a copy of all student records in the specified class (dict of sid -> data).
        """
        with self.lock:
            if class_name in self.classes:
                return copy.deepcopy(self.classes[class_name]['students'])
            return {}

    def get_present_students(self, class_name):
        """
        Return a set of student IDs currently marked as present in the specified class.
        """
        with self.lock:
            if class_name in self.classes:
                return set(self.classes[class_name]['present_students'])
            return set()

    def get_attendance_timestamp(self, class_name, student_id):
        """
        Return the last attendance timestamp (datetime) for the student.
        If not found, return None.
        """
        with self.lock:
            if class_name not in self.classes:
                return None
            return self.classes[class_name]['attendance_timestamps'].get(student_id)

    def get_time_based_count(self, class_name, student_id):
        """
        Return how many scanning intervals have elapsed since the student was first
        marked present. If the student or timestamp is missing, return 0.
        """
        with self.lock:
            if class_name not in self.classes:
                return 0
            cdict = self.classes[class_name]
            if student_id not in cdict['attendance_timestamps']:
                return 0

            ts = cdict['attendance_timestamps'][student_id]
            elapsed = (datetime.now() - ts).total_seconds()

            if self.current_scan_interval <= 0:
                return 0

            intervals = max(1, int(elapsed / self.current_scan_interval))
            return intervals

    def list_macs_for_student(self, class_name, student_id):
        """
        Return the set of MAC addresses assigned to the specified student in the given class.
        """
        with self.lock:
            if class_name not in self.classes:
                return set()
            return set(self.classes[class_name]['student_mac_addresses'].get(student_id, set()))
