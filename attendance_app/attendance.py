# attendance.py

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

        :param data_file: Path to the data file for persistence.
        :param initial_scan_interval: Initial scan interval in seconds.
        """
        self.lock = threading.RLock()
        self.data_file = data_file
        self.valid_class_codes = ["CSCI", "MENG", "EENG", "ENGR", "SWEN", "ISEN", "CIS"]
        self.classes = {}  # class_name: class_data_dict
        self.current_scan_interval = initial_scan_interval  # in seconds
        self.load_data()

    def _initialize_class_data(self):
        """
        Initialize the data structure for a new class.

        :return: A dictionary representing the class data.
        """
        return {
            'students': {},  # student_id: student_data_dict
            'present_students': set(),  # Set of student IDs
            'student_mac_addresses': defaultdict(set),  # student_id: set of MAC addresses
            'attendance_timestamps': {},  # student_id: timestamp
        }

    def load_data(self):
        """
        Load attendance data from the data file.
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

    def add_class(self, class_name):
        """
        Add a new class if it does not exist.

        :param class_name: Name of the class to add.
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

    def _generate_unique_student_id(self, class_name):
        """
        Generate a unique student ID within the specified class.

        :param class_name: Name of the class.
        :return: A unique student ID as a string.
        """
        existing_ids = set(self.classes[class_name]['students'].keys())
        new_id = 1
        while str(new_id) in existing_ids:
            new_id += 1
        return str(new_id)

    def add_student_to_class(self, class_name, student):
        """
        Add a single student to a specific class.

        :param class_name: Name of the class.
        :param student: Dictionary containing student details.
        """
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
                # Generate a unique ID if not provided
                student_id = self._generate_unique_student_id(class_name)
                student['student_id'] = student_id

            self.classes[class_name]['students'][student_id] = student
            self.save_data()
            logging.info(f"Added student '{student_id}' to class '{class_name}'.")

    def assign_device_to_student(self, class_name, student_id, addr):
        """
        Assign a Bluetooth device (MAC address) to a student.

        :param class_name: Name of the class.
        :param student_id: ID of the student.
        :param addr: MAC address of the Bluetooth device.
        """
        if not class_name or not student_id or not addr:
            logging.error("Class name, student ID, and address cannot be empty.")
            raise ValueError("Class name, student ID, and address cannot be empty.")

        with self.lock:
            addr_upper = addr.upper()
            if class_name not in self.classes:
                logging.error(f"Class '{class_name}' does not exist.")
                raise ValueError(f"Class '{class_name}' does not exist.")

            # Remove the MAC address from any other student
            for cname, cdata in self.classes.items():
                for sid, macs in cdata['student_mac_addresses'].items():
                    if addr_upper in macs and (cname != class_name or sid != student_id):
                        macs.discard(addr_upper)
                        logging.info(f"Removed MAC address {addr_upper} from student '{sid}' in class '{cname}'.")
                        cdata['present_students'].discard(sid)
                        cdata['attendance_timestamps'].pop(sid, None)

            # Assign the MAC address to the correct student
            class_data = self.classes[class_name]
            class_data['student_mac_addresses'][student_id].add(addr_upper)
            self.save_data()
            logging.info(f"Assigned device {addr_upper} to student '{student_id}' in class '{class_name}'.")

    def remove_mac_from_student(self, class_name, student_id, addr):
        """
        Remove a MAC address from a student.

        :param class_name: Name of the class.
        :param student_id: ID of the student.
        :param addr: MAC address to remove.
        """
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

    def get_student_by_mac(self, addr):
        """
        Retrieve the student assigned to a particular MAC address.

        :param addr: MAC address to look up.
        :return: Tuple of (class_name, student_id) or (None, None) if not found.
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

        :return: Set of all assigned MAC addresses.
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

        :param found_devices: Dictionary of found devices from the scanner.
        :return: Dictionary of unassigned devices.
        """
        if not isinstance(found_devices, dict):
            logging.error("Invalid found_devices data provided.")
            return {}

        unassigned = {}
        assigned_macs = self.get_all_assigned_macs()
        for addr_upper, device_info in found_devices.items():
            if addr_upper not in assigned_macs:
                unassigned[addr_upper] = device_info
        logging.info(f"Identified {len(unassigned)} unassigned devices.")
        return unassigned

    def update_attendance(self, found_devices):
        """
        Update attendance based on detected Bluetooth devices.

        :param found_devices: Dictionary of found devices from the scanner.
        """
        if not isinstance(found_devices, dict):
            logging.error("Invalid found_devices data provided.")
            return

        with self.lock:
            current_time = datetime.now()
            for class_name, class_data in self.classes.items():
                newly_present = set()
                for student_id, macs in class_data['student_mac_addresses'].items():
                    for mac in macs:
                        if mac in found_devices:
                            newly_present.add(student_id)
                            if student_id not in class_data['attendance_timestamps']:
                                class_data['attendance_timestamps'][student_id] = current_time
                            break  # Stop checking after finding one MAC

                # Update present_students
                class_data['present_students'] = newly_present
                # Remove timestamps for students no longer present
                for student_id in list(class_data['attendance_timestamps'].keys()):
                    if student_id not in newly_present:
                        del class_data['attendance_timestamps'][student_id]
                self.save_data()
                logging.info(f"Updated attendance for class '{class_name}'. Present students: {len(newly_present)}.")

    def get_all_students(self, class_name):
        """
        Retrieve all students in a specific class.

        :param class_name: Name of the class.
        :return: Dictionary of student_id: student_data.
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

    def get_present_students(self, class_name):
        """
        Get a list of students marked as present in a specific class.

        :param class_name: Name of the class.
        :return: Set of student IDs.
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

        :param class_name: Name of the class.
        :param student_id: ID of the student.
        """
        if not class_name or not student_id:
            logging.error("Class name and student ID cannot be empty.")
            raise ValueError("Class name and student ID cannot be empty.")

        with self.lock:
            if class_name not in self.classes:
                logging.error(f"Class '{class_name}' does not exist.")
                raise ValueError(f"Class '{class_name}' does not exist.")

            class_data = self.classes[class_name]
            class_data['present_students'].add(student_id)
            class_data['attendance_timestamps'][student_id] = datetime.now()
            self.save_data()
            logging.info(f"Manually marked student '{student_id}' as present in class '{class_name}'.")

    def mark_student_absent(self, class_name, student_id):
        """
        Manually mark a student as absent.

        :param class_name: Name of the class.
        :param student_id: ID of the student.
        """
        if not class_name or not student_id:
            logging.error("Class name and student ID cannot be empty.")
            raise ValueError("Class name and student ID cannot be empty.")

        with self.lock:
            class_data = self.classes.get(class_name)
            if class_data:
                class_data['present_students'].discard(student_id)
                class_data['attendance_timestamps'].pop(student_id, None)
                self.save_data()
                logging.info(f"Manually marked student '{student_id}' as absent in class '{class_name}'.")
            else:
                logging.warning(f"Class '{class_name}' does not exist.")

    def get_assigned_macs_for_student(self, class_name, student_id):
        """
        Retrieve the MAC addresses assigned to a student.

        :param class_name: Name of the class.
        :param student_id: ID of the student.
        :return: Set of MAC addresses.
        """
        if not class_name or not student_id:
            logging.error("Class name and student ID cannot be empty.")
            return set()

        with self.lock:
            class_data = self.classes.get(class_name)
            if class_data:
                macs = class_data['student_mac_addresses'].get(student_id, set())
                return set(macs)
            else:
                logging.warning(f"Class '{class_name}' does not exist.")
                return set()

    def get_attendance_timestamp(self, class_name, student_id):
        """
        Retrieve the timestamp when a student was last marked present.

        :param class_name: Name of the class.
        :param student_id: ID of the student.
        :return: datetime object or None.
        """
        if not class_name or not student_id:
            logging.error("Class name and student ID cannot be empty.")
            return None

        with self.lock:
            class_data = self.classes.get(class_name)
            if class_data:
                timestamp = class_data['attendance_timestamps'].get(student_id)
                return timestamp
            else:
                logging.warning(f"Class '{class_name}' does not exist.")
                return None

    def get_valid_class_codes(self):
        """
        Return the list of valid class codes.

        :return: List of class codes.
        """
        with self.lock:
            return list(self.valid_class_codes)

    def get_attendance_count(self, class_name, student_id):
        """
        Get the number of scan intervals since the student was first detected.

        :param class_name: Name of the class.
        :param student_id: ID of the student.
        :return: Integer count of scan intervals.
        """
        if not class_name or not student_id:
            logging.error("Class name and student ID cannot be empty.")
            return 0

        with self.lock:
            class_data = self.classes.get(class_name)
            if class_data:
                timestamp = class_data['attendance_timestamps'].get(student_id)
                if not timestamp:
                    return 0  # Student not present

                elapsed_time = (datetime.now() - timestamp).total_seconds()
                scan_interval = self.current_scan_interval  # Use the current scan interval
                if scan_interval <= 0:
                    logging.error("Scan interval must be a positive integer.")
                    return 0
                count = max(1, int(elapsed_time / scan_interval))  # At least 1 if present
                return count
            else:
                logging.warning(f"Class '{class_name}' does not exist.")
                return 0


    def set_scan_interval(self, new_interval):
        """
        Update the current scan interval.

        :param new_interval: New scan interval in seconds.
        """
        if new_interval <= 0:
            logging.error("Scan interval must be a positive integer.")
            raise ValueError("Scan interval must be a positive integer.")

        with self.lock:
            old_interval = self.current_scan_interval
            self.current_scan_interval = new_interval
            logging.info(f"Scan interval updated from {old_interval} seconds to {new_interval} seconds.")

    def get_all_student_ids(self, class_name):
        """
        Retrieve all student IDs for a specific class.

        :param class_name: Name of the class.
        :return: List of student IDs.
        """
        if not class_name:
            logging.error("Class name cannot be empty.")
            return []

        with self.lock:
            class_data = self.classes.get(class_name)
            if class_data:
                return list(class_data['students'].keys())
            else:
                logging.warning(f"Class '{class_name}' does not exist.")
                return []
