import pickle
import threading
import os
import logging
from collections import defaultdict
from datetime import datetime
import copy

class AttendanceManager:
    def __init__(self, data_file='student_data.pkl', initial_scan_interval=10):
        """
        Initialize the AttendanceManager.
        """
        self.lock = threading.RLock()
        self.data_file = data_file
        self.valid_class_codes = ["CSCI", "MENG", "EENG", "ENGR", "SWEN", "ISEN", "CIS"]
        self.classes = {}  # class_name: class_data_dict
        self.current_scan_interval = initial_scan_interval  # in seconds
        self.mac_scan_counts = {}  # Mapping from MAC address (uppercase) to individual scan count
        self.blacklist = set()  # Set of blacklisted MAC addresses (uppercase)
        self.load_data()

    def _initialize_class_data(self):
        """
        Initialize the data structure for a new class.
        """
        return {
            'students': {},  # student_id: student_data_dict
            'present_students': set(),  # Set of student IDs
            'student_mac_addresses': defaultdict(set),  # student_id: set of MAC addresses
            'attendance_timestamps': {},  # student_id: timestamp
        }

    def _migrate_class_data(self):
        """
        Ensure that each class in self.classes has all required keys.
        This helps to migrate older saved data to the new format.
        """
        modified = False
        for class_name, class_data in self.classes.items():
            if 'students' not in class_data:
                class_data['students'] = {}
                modified = True
            if 'present_students' not in class_data:
                class_data['present_students'] = set()
                modified = True
            if 'student_mac_addresses' not in class_data:
                class_data['student_mac_addresses'] = defaultdict(set)
                modified = True
            if 'attendance_timestamps' not in class_data:
                class_data['attendance_timestamps'] = {}
                modified = True
        if modified:
            self.save_data()

    def load_data(self):
        """
        Load attendance data from the data file.
        """
        with self.lock:
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, 'rb') as f:
                        self.classes = pickle.load(f)
                    # Migrate old data structure to new format if needed
                    self._migrate_class_data()
                    logging.info("Loaded attendance data successfully.")
                except Exception as e:
                    logging.error(f"Error loading data file: {e}")
                    self.classes = {}
            else:
                self.classes = {}
                logging.warning("No existing data file found. Starting fresh.")

    def save_data(self):
        """
        Save attendance data to the data file.
        """
        with self.lock:
            try:
                with open(self.data_file, 'wb') as f:
                    pickle.dump(self.classes, f)
                logging.info("Saved attendance data successfully.")
            except Exception as e:
                logging.error(f"Error saving data file: {e}")

    def get_valid_class_codes(self):
        """
        Getter for valid class codes.
        """
        return self.valid_class_codes

    def add_class(self, class_name):
        """
        Add a new class if it does not exist.
        """
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
        """
        Alias for add_class to register a class.
        """
        self.add_class(class_name)

    def delete_class(self, class_name):
        """
        Delete a class from the attendance data.
        """
        if not class_name:
            logging.error("Class name cannot be empty.")
            raise ValueError("Class name cannot be empty.")

        with self.lock:
            if class_name in self.classes:
                del self.classes[class_name]
                self.save_data()
                logging.info(f"Class '{class_name}' has been deleted.")
            else:
                logging.warning(f"Attempted to delete non-existent class '{class_name}'.")

    def delete_database(self):
        """
        Delete the student database and reset class data.
        """
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

            image_cache_dir = os.path.join(os.getcwd(), 'image_cache')
            if os.path.exists(image_cache_dir):
                try:
                    import shutil
                    shutil.rmtree(image_cache_dir)
                    logging.info("Deleted cached image folder successfully.")
                except Exception as e:
                    logging.error(f"Error deleting cached image folder: {e}")
            else:
                logging.warning("Cached image folder does not exist. Nothing to delete.")

    def _generate_unique_student_id(self, class_name):
        """
        Generate a unique student ID within the specified class.
        """
        existing_ids = set(self.classes[class_name]['students'].keys())
        new_id = 1
        while str(new_id) in existing_ids:
            new_id += 1
        return str(new_id)

    def add_student(self, class_name, student):
        """
        Add a single student to a specific class.
        """
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
        """
        Assign a Bluetooth device (MAC address) to a student.
        Also handle reassignment by updating presence.
        """
        try:
            if not class_name or not student_id or not addr:
                logging.error("Class name, student ID, and address cannot be empty.")
                raise ValueError("Class name, student ID, and address cannot be empty.")

            with self.lock:
                addr_upper = addr.upper()
                if addr_upper in self.blacklist:
                    self.blacklist.discard(addr_upper)
                    logging.info(f"Removed MAC address {addr_upper} from blacklist due to assignment.")

                for cname, cdata in self.classes.items():
                    for sid, macs in cdata['student_mac_addresses'].items():
                        if addr_upper in macs and (cname != class_name or sid != student_id):
                            macs.discard(addr_upper)
                            logging.info(f"Removed MAC address {addr_upper} from student '{sid}' in class '{cname}'.")
                            cdata['present_students'].discard(sid)
                            cdata['attendance_timestamps'].pop(sid, None)

                class_data = self.classes[class_name]
                class_data['student_mac_addresses'][student_id].add(addr_upper)
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

    def remove_mac_from_student(self, class_name, student_id, addr):
        """
        Remove a MAC address from a student.
        """
        try:
            if not class_name or not student_id or not addr:
                logging.error("Class name, student ID, and address cannot be empty.")
                raise ValueError("Class name, student ID, and address cannot be empty.")

            with self.lock:
                addr_upper = addr.upper()
                if class_name not in self.classes:
                    logging.error(f"Class '{class_name}' does not exist.")
                    raise ValueError(f"Class '{class_name}' does not exist.")

                class_data = self.classes[class_name]
                macs = class_data['student_mac_addresses'].get(student_id, set())
                if addr_upper in macs:
                    macs.discard(addr_upper)
                    logging.info(f"Removed MAC address {addr_upper} from student '{student_id}' in class '{class_name}'.")
                    self.save_data()
                else:
                    logging.warning(f"MAC address {addr_upper} not found for student '{student_id}' in class '{class_name}'.")
        except Exception as e:
            logging.error(f"Error removing MAC address from student '{student_id}' in class '{class_name}': {e}")
            raise

    def get_student_by_mac(self, addr):
        """
        Retrieve the student assigned to a particular MAC address.
        """
        if not addr:
            logging.error("Address cannot be empty.")
            return None, None

        addr_upper = addr.upper()
        with self.lock:
            for class_name, class_data in self.classes.items():
                for student_id, macs in class_data['student_mac_addresses'].items():
                    if addr_upper in macs:
                        logging.info(f"Found student '{student_id}' in class '{class_name}' for MAC address {addr_upper}.")
                        return class_name, student_id
        logging.warning(f"No student found for MAC address {addr_upper}.")
        return None, None

    def get_all_assigned_macs(self):
        """
        Retrieve all assigned MAC addresses across all classes.
        """
        with self.lock:
            assigned = set()
            for class_data in self.classes.values():
                for macs in class_data['student_mac_addresses'].values():
                    assigned.update(macs)
            return assigned

    def get_unassigned_devices(self, found_devices):
        """
        Identify devices that are detected but not assigned to any student.
        """
        if not isinstance(found_devices, dict):
            logging.error("Invalid found_devices data provided.")
            return {}

        unassigned = {}
        assigned_macs = self.get_all_assigned_macs()
        for addr_upper, device_info in found_devices.items():
            if addr_upper not in assigned_macs and addr_upper not in self.blacklist:
                unassigned[addr_upper] = device_info
        logging.info(f"Identified {len(unassigned)} unassigned devices.")
        return unassigned

    def update_attendance(self, found_devices):
        """
        Update attendance based on detected Bluetooth devices, respecting manual overrides.
        Also updates individual MAC scan counts.
        """
        if not isinstance(found_devices, dict):
            logging.error("Invalid found_devices data provided.")
            return

        with self.lock:
            current_time = datetime.now()
            for class_name, class_data in self.classes.items():
                newly_present = set()
                for student_id, macs in class_data['student_mac_addresses'].items():
                    student_data = class_data['students'].get(student_id, {})
                    manual_override = student_data.get('manual_override', False)

                    if manual_override:
                        if student_id in class_data['present_students']:
                            newly_present.add(student_id)
                        continue

                    for mac in macs:
                        if mac in self.blacklist:
                            continue
                        if mac in found_devices:
                            self.mac_scan_counts[mac] = self.mac_scan_counts.get(mac, 0) + 1
                            newly_present.add(student_id)
                            if student_id not in class_data['attendance_timestamps']:
                                class_data['attendance_timestamps'][student_id] = current_time
                            break

                class_data['present_students'] = newly_present
                for student_id in list(class_data['attendance_timestamps'].keys()):
                    if student_id not in newly_present:
                        del class_data['attendance_timestamps'][student_id]
                self.save_data()
                logging.info(f"Updated attendance for class '{class_name}'. Present students: {len(newly_present)}.")

    def get_all_students(self, class_name):
        """
        Retrieve all students in a specific class.
        """
        if not class_name:
            logging.error("Class name cannot be empty.")
            return {}

        with self.lock:
            class_data = self.classes.get(class_name)
            if class_data:
                return copy.deepcopy(class_data['students'])
            else:
                logging.warning(f"Class '{class_name}' does not exist.")
                return {}

    def get_student_data(self, class_name, student_id):
        """
        Retrieve data for a specific student.
        """
        with self.lock:
            class_data = self.classes.get(class_name)
            if class_data:
                return class_data['students'].get(student_id)
            return None

    def get_present_students(self, class_name):
        """
        Get a list of students marked as present in a specific class.
        """
        if not class_name:
            logging.error("Class name cannot be empty.")
            return set()

        with self.lock:
            class_data = self.classes.get(class_name)
            if class_data:
                return set(class_data['present_students'])
            else:
                logging.warning(f"Class '{class_name}' does not exist.")
                return set()

    def mark_student_present(self, class_name, student_id):
        """
        Manually mark a student as present.
        """
        try:
            if not class_name or not student_id:
                logging.error("Class name and student ID cannot be empty.")
                raise ValueError("Class name and student ID cannot be empty.")

            with self.lock:
                if class_name not in self.classes:
                    logging.error(f"Class '{class_name}' does not exist.")
                    raise ValueError(f"Class '{class_name}' does not exist.")

                class_data = self.classes[class_name]
                student_data = class_data['students'].get(student_id)
                if student_data:
                    class_data['present_students'].add(student_id)
                    class_data['attendance_timestamps'][student_id] = datetime.now()
                    student_data['manual_override'] = True
                    self.save_data()
                    logging.info(f"Manually marked student '{student_id}' as present in class '{class_name}'.")
                else:
                    logging.warning(f"Student '{student_id}' not found in class '{class_name}'.")
        except Exception as e:
            logging.error(f"Error marking student '{student_id}' as present in class '{class_name}': {e}")
            raise

    def mark_student_absent(self, class_name, student_id):
        """
        Manually mark a student as absent.
        """
        try:
            if not class_name or not student_id:
                logging.error("Class name and student ID cannot be empty.")
                raise ValueError("Class name and student ID cannot be empty.")

            with self.lock:
                class_data = self.classes.get(class_name)
                if class_data:
                    student_data = class_data['students'].get(student_id)
                    if student_data:
                        class_data['present_students'].discard(student_id)
                        class_data['attendance_timestamps'].pop(student_id, None)
                        student_data['manual_override'] = True
                        self.save_data()
                        logging.info(f"Manually marked student '{student_id}' as absent in class '{class_name}'.")
                    else:
                        logging.warning(f"Student '{student_id}' not found in class '{class_name}'.")
                else:
                    logging.warning(f"Class '{class_name}' does not exist.")
        except Exception as e:
            logging.error(f"Error marking student '{student_id}' as absent in class '{class_name}': {e}")
            raise

    def get_attendance_count_by_mac(self, mac):
        """
        Retrieve the individual scan count for a given MAC address.
        """
        if not mac:
            return 0
        return self.mac_scan_counts.get(mac.upper(), 0)

    def get_time_based_count(self, class_name, student_id):
        """
        Calculate the time-based count for a student by summing the counts of their assigned MAC addresses.
        """
        count = 0
        with self.lock:
            class_data = self.classes.get(class_name)
            if class_data:
                macs = class_data['student_mac_addresses'].get(student_id, set())
                for mac in macs:
                    count += self.get_attendance_count_by_mac(mac)
        return count

    def load_blacklist(self, file_path):
        """
        Load a blacklist of MAC addresses from a .txt file.
        Each line in the file should be a MAC address.
        """
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
        """
        Return the current blacklist of MAC addresses.
        """
        return self.blacklist
