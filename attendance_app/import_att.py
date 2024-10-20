# import_att.py

import os
import threading
from tkinter import filedialog, messagebox
import requests
from html_parse import parse_html_file, generate_photo_url
from utils import log_message, is_valid_url
from attendance import AttendanceManager


class importApp:
    """
    Class to handle importing students from HTML files into the AttendanceManager.
    """
    def __init__(self, attendance_manager):
        """
        Initialize the importApp with an AttendanceManager instance.

        :param attendance_manager: Instance of AttendanceManager.
        """
        self.attendance_manager = attendance_manager
        self.lock = threading.RLock()  # Ensure thread safety

    def import_html_action(self):
        """
        Handle the action of importing students from an HTML file.

        :return: List of imported class names.
        """
        # Open a file dialog to select the HTML file
        file_path = filedialog.askopenfilename(
            title="Select HTML File",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
        )
        if file_path:
            try:
                # Parse the HTML file and get class-student mappings
                valid_class_codes = self.attendance_manager.get_valid_class_codes()
                class_students = parse_html_file(file_path, valid_class_codes)

                if class_students:
                    with self.lock:
                        for class_name, students in class_students.items():
                            # Add the class if it doesn't exist
                            self.attendance_manager.add_class(class_name)
                            # Import students into the class
                            self.import_students_with_photos(class_name, students)
                    messagebox.showinfo("Import Success", "Students imported successfully from HTML.")
                    log_message("Imported students from HTML file.")
                    return list(class_students.keys())
                else:
                    messagebox.showwarning("No Classes Found", "No valid classes found in the HTML file.")
                    log_message("No valid classes found in the HTML file.", "warning")
            except Exception as e:
                messagebox.showerror(
                    "Import Error", f"Failed to import students from HTML: {e}"
                )
                log_message(
                    f"Failed to import students from HTML: {e}", "error"
                )
        return []

    def import_students_with_photos(self, class_name, students):
        """
        Import students with their photos into a specific class.

        :param class_name: Name of the class.
        :param students: List of student dictionaries.
        """
        with self.lock:
            for student in students:
                student_id = student.get('student_id')
                if not student_id:
                    log_message(f"Student missing 'student_id' in class {class_name}: {student}", "warning")
                    continue  # Skip students without 'student_id'

                # Generate photo URL if not present
                if 'photo_url' not in student or not student['photo_url']:
                    photo_url = generate_photo_url(student['name'], student.get('email'))
                    student['photo_url'] = photo_url if photo_url else ""

                # Validate the generated photo URL
                if student['photo_url'] and not is_valid_url(student['photo_url']):
                    log_message(f"Invalid photo URL for student '{student_id}': {student['photo_url']}", "warning")
                    student['photo_url'] = ""  # Remove invalid URL

                # Add or update the student in AttendanceManager
                self.attendance_manager.add_student_to_class(class_name, student)

        # Save data after importing all students
        self.attendance_manager.save_data()
        log_message(f"Imported {len(students)} students into class '{class_name}'.")


    def is_valid_url(url):
        """
        Validate if a URL is accessible.

        :param url: URL to validate.
        :return: True if accessible, False otherwise.
        """
        try:
            response = requests.get(url, allow_redirects=True, stream=True, timeout=5)
            return response.status_code == 200
        except Exception as e:
            log_message(f"Error validating URL {url}: {e}", "error")
            return False
