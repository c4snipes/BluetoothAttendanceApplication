'''# attendance.py

import pickle
import os
from utils import log_message
from datetime import datetime
import csv
import threading

class AttendanceManager:
    def __init__(self):
        self.student_mac_addresses = {}  # Mapping from student names to sets of MAC addresses
        self.present_students = set()
        self.all_students = []
        self.attendance_logs = {}
        self.attendance_log_file = 'attendance_log.csv'
        self.current_arrival_times = {}  # Maps student names to their arrival time
        self.unrecognized_devices = {}

        # Load existing data
        self.load_data()

        # Lock for thread-safe operations
        self.lock = threading.Lock()

    def load_data(self):
        if os.path.exists('student_mappings.pkl'):
            with open('student_mappings.pkl', 'rb') as f:
                data = pickle.load(f)
                # Convert lists back to sets
                self.student_mac_addresses = {student: set(macs) for student, macs in data.get('student_mac_addresses', {}).items()}
                self.all_students = data.get('all_students', [])
                self.attendance_logs = data.get('attendance_logs', {})
        else:
            self.student_mac_addresses = {}
            self.all_students = []
            self.attendance_logs = {}

    def save_data(self):
        # Convert sets to lists before saving
        data = {
            'student_mac_addresses': {student: list(macs) for student, macs in self.student_mac_addresses.items()},
            'all_students': self.all_students,
            'attendance_logs': self.attendance_logs
        }
        with open('student_mappings.pkl', 'wb') as f:
            pickle.dump(data, f)

    def import_students(self, file_path):
        with open(file_path, 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader, None)  # Skip header if there is one
            self.all_students = [row[0].strip() for row in reader if row]
        self.save_data()

    def add_student(self, student_name):
        self.all_students.append(student_name)
        self.save_data()

    def mark_present(self, student):
        self.present_students.add(student)
        self.record_arrival_time(student)

    def mark_absent(self, student):
        self.present_students.discard(student)
        self.record_departure_time(student)

    def update_attendance(self, found_devices):
        with self.lock:
            new_present_students = set()
            detected_mac_addresses = set(addr.upper() for addr in found_devices.keys())

            for student, mac_addresses in self.student_mac_addresses.items():
                if detected_mac_addresses & mac_addresses:
                    new_present_students.add(student)

            previous_present_students = self.present_students.copy()
            self.present_students = new_present_students

            # Record arrival and departure times
            self.record_attendance_times(previous_present_students, new_present_students)

            return new_present_students

    def record_arrival_time(self, student):
        current_time = datetime.now()
        self.current_arrival_times[student] = current_time
        log_message(f"{student} has arrived.")

    def record_departure_time(self, student):
        current_time = datetime.now()
        date_str = current_time.strftime('%Y-%m-%d')
        time_str = current_time.strftime('%H:%M:%S')

        arrival_time = self.current_arrival_times.pop(student, None)
        if arrival_time:
            arrival_time_str = arrival_time.strftime('%H:%M:%S')
            departure_time_str = time_str
            mac_addresses = ', '.join(self.student_mac_addresses.get(student, []))

            if student not in self.attendance_logs:
                self.attendance_logs[student] = []

            self.attendance_logs[student].append({
                'date': date_str,
                'arrival_time': arrival_time_str,
                'departure_time': departure_time_str,
                'mac_address': mac_addresses
            })

            self.save_data()
            log_message(f"{student} has left.")

    def record_attendance_times(self, previous_present_students, new_present_students):
        # Students who have just arrived
        arrived_students = new_present_students - previous_present_students
        for student in arrived_students:
            self.record_arrival_time(student)

        # Students who have just left
        left_students = previous_present_students - new_present_students
        for student in left_students:
            self.record_departure_time(student)

    def assign_device_to_student(self, student, addr):
        with self.lock:
            addr_upper = addr.upper()
            if student not in self.student_mac_addresses:
                self.student_mac_addresses[student] = set()
            self.student_mac_addresses[student].add(addr_upper)
            self.save_data()

    def get_unrecognized_devices(self, found_devices):
        assigned_macs = set().union(*self.student_mac_addresses.values())
        self.unrecognized_devices = {}
        for addr, (name, rssi) in found_devices.items():
            addr_upper = addr.upper()
            if addr_upper not in assigned_macs:
                self.unrecognized_devices[addr_upper] = (name, rssi)
        return self.unrecognized_devices

    def get_unassigned_devices(self, found_devices):
        assigned_macs = set().union(*self.student_mac_addresses.values())
        unassigned_devices = {addr: (name, rssi) for addr, (name, rssi) in found_devices.items() if addr.upper() not in assigned_macs}
        return unassigned_devices

    def log_attendance(self):
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.attendance_log_file, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for student in self.present_students:
                writer.writerow([date_str, student])
'''