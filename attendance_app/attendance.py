# attendance.py

import pickle
import threading
import os
from collections import defaultdict
from utils import log_message

class AttendanceManager:
    def __init__(self, data_file='student_data.pkl'):
        self.lock = threading.RLock()
        self.data_file = data_file
        self.classes = {}  # class_name: class_data_dict
        self.load_data()

    def _initialize_class_data(self):
        return {
            'students': {},  # student_id: student_data_dict
            'present_students': set(),
            'absent_students': set(),
            'student_mac_addresses': defaultdict(set),
        }

    def load_data(self):
        with self.lock:
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, 'rb') as f:
                        self.classes = pickle.load(f)
                except Exception as e:
                    log_message(f"Error loading data file: {e}", "error")
                    self.classes = {}
            else:
                self.classes = {}


    def save_data(self):
        with self.lock:
            with open(self.data_file, 'wb') as f:
                pickle.dump(self.classes, f)

    def add_class(self, class_name):
        with self.lock:
            if class_name not in self.classes:
                self.classes[class_name] = self._initialize_class_data()
                self.save_data()
                log_message(f"Added new class: {class_name}")

    def delete_database(self):
        """
        Delete the student database.
        """
        with self.lock:
            # Clear class data
            self.classes = {}
            # Delete data file
            if os.path.exists(self.data_file):
                os.remove(self.data_file)
            log_message("Deleted student database.")


    def import_students_with_photos(self, class_name, students):
        if class_name not in self.classes:
            self.classes[class_name] = self._initialize_class_data()
        for student in students:
            student_id = student['student_id']
            self.classes[class_name]['students'][student_id] = student



    def assign_device_to_student(self, class_name, student_id, addr):
        with self.lock:
            addr_upper = addr.upper()
            if class_name not in self.classes:
                return
            class_data = self.classes[class_name]
            # Remove the MAC address from any other student in this class
            for sid, macs in class_data['student_mac_addresses'].items():
                if addr_upper in macs and sid != student_id:
                    macs.discard(addr_upper)
                    log_message(f"Removed MAC address {addr_upper} from student {sid} in class {class_name}")
            # Assign the MAC address to the student
            class_data['student_mac_addresses'][student_id].add(addr_upper)
            self.save_data()
            log_message(f"Assigned device {addr_upper} to {student_id} in class {class_name}.")


    def get_all_assigned_macs(self):
        """
        Retrieve all assigned MAC addresses.
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

        :param found_devices: Dictionary of found devices {addr: device_info}.
        :return: Dictionary of unassigned devices {addr: device_info}.
        """
        unassigned = {}
        assigned_macs = self.get_all_assigned_macs()
        for addr_upper, device_info in found_devices.items():
            if addr_upper not in assigned_macs:
                unassigned[addr_upper] = device_info
        return unassigned

    def update_attendance(self, found_devices):
        with self.lock:
            for class_name, class_data in self.classes.items():
                newly_present = set()
                for student_id, macs in class_data['student_mac_addresses'].items():
                    for mac in macs:
                        if mac in found_devices:
                            if student_id not in class_data['present_students']:
                                newly_present.add(student_id)
                                log_message(f"Marked {student_id} as present in class {class_name} with MAC {mac}")
                            break  # Avoid multiple logs for multiple devices

                # Update present and absent sets
                class_data['present_students'].update(newly_present)
                class_data['absent_students'].difference_update(newly_present)
            self.save_data()

    def get_all_students(self, class_name):
        with self.lock:
            class_data = self.classes.get(class_name, self._initialize_class_data())
            return dict(class_data['students'])

    def get_present_students(self, class_name):
        with self.lock:
            class_data = self.classes.get(class_name, self._initialize_class_data())
            return set(class_data['present_students'])

    def mark_student_present(self, class_name, student_id):
        with self.lock:
            if class_name not in self.classes:
                log_message(f"Class {class_name} does not exist.", "error")
                raise ValueError(f"Class {class_name} does not exist.")
            class_data = self.classes[class_name]
            class_data['present_students'].add(student_id)
            class_data['absent_students'].discard(student_id)
            self.save_data()
            log_message(f"Manually marked {student_id} as present in class {class_name}.")


    def mark_student_absent(self, class_name, student_id):
        with self.lock:
            class_data = self.classes.get(class_name, self._initialize_class_data())
            class_data['present_students'].discard(student_id)
            class_data['absent_students'].add(student_id)
            self.save_data()
            log_message(f"Manually marked {student_id} as absent in class {class_name}.")
            
    def get_assigned_macs_for_student(self, class_name, student_id):
        with self.lock:
            class_data = self.classes.get(class_name, {})
            macs = class_data.get('student_mac_addresses', {}).get(student_id, set())
            return macs
