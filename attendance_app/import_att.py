# import_att.py

import threading
from tkinter import filedialog, messagebox
import logging
from html_parse import parse_html_file, generate_photo_url, is_valid_url
from attendance import AttendanceManager

class ImportApp:
    """
    Class to handle importing students from HTML files into the AttendanceManager.
    """
    def __init__(self, attendance_manager):
        """
        Initialize the ImportApp with an AttendanceManager instance.

        :param attendance_manager: Instance of AttendanceManager.
        """
        self.attendance_manager = attendance_manager

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
                    for class_name, students in class_students.items():
                        # Add the class if it doesn't exist
                        self.attendance_manager.add_class(class_name)
                        # Import students into the class
                        self.import_students_with_photos(class_name, students)
                    messagebox.showinfo("Import Success", "Students imported successfully from HTML.")
                    logging.info("Imported students from HTML file.")
                    return list(class_students.keys())
                else:
                    messagebox.showwarning("No Classes Found", "No valid classes found in the HTML file.")
                    logging.warning("No valid classes found in the HTML file.")
            except Exception as e:
                messagebox.showerror(
                    "Import Error", f"Failed to import students from HTML: {e}"
                )
                logging.error(f"Failed to import students from HTML: {e}")
        else:
            logging.info("User canceled HTML import action.")
        return []

    def import_students_with_photos(self, class_name, students):
        """
        Import students with their photos into a specific class.

        :param class_name: Name of the class.
        :param students: List of student dictionaries.
        """
        for student in students:
            student_id = student.get('student_id')
            if not student_id:
                logging.warning(f"Student missing 'student_id' in class '{class_name}': {student}")
                continue  # Skip students without 'student_id'

            # Ensure student has a name
            if not student.get('name'):
                logging.warning(f"Student missing 'name' in class '{class_name}': {student}")
                continue  # Skip students without 'name'

            # Generate photo URL if not present
            if not student.get('photo_url'):
                photo_url = generate_photo_url(student['name'], student.get('email'))
                student['photo_url'] = photo_url if photo_url else ""

            # Validate the generated photo URL
            if student['photo_url'] and not is_valid_url(student['photo_url']):
                logging.warning(f"Invalid photo URL for student '{student_id}': {student['photo_url']}")
                student['photo_url'] = ""  # Remove invalid URL

            # Add or update the student in AttendanceManager
            try:
                self.attendance_manager.add_student_to_class(class_name, student)
                logging.info(f"Added student '{student_id}' to class '{class_name}'.")
            except ValueError as e:
                logging.error(f"Failed to add student '{student_id}' to class '{class_name}': {e}")
                continue  # Skip to the next student
