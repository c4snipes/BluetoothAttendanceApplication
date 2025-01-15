# import_att.py

import tkinter as tk
from tkinter import filedialog, messagebox
import logging
import threading
import queue

from html_parse import parse_html_file, generate_photo_url, is_valid_url

class ImportApp:
    """
    Class to handle importing students from HTML files into the AttendanceManager,
    using a background thread to avoid freezing the UI for large files.
    """
    def __init__(self, attendance_manager, master=None):
        """
        :param attendance_manager: The AttendanceManager instance.
        :param master: (Optional) The parent Tk widget for dialogs.
        """
        self.attendance_manager = attendance_manager
        self.master = master
        # We'll use a queue to pass results from the worker thread back to the main thread
        self._import_queue = queue.Queue()
        self._thread = None
        self._progress_popup = None

    def import_html_action(self):
        """
        Start the import by opening a file dialog, then spawn a thread to parse the file.
        """
        file_path = filedialog.askopenfilename(
            title="Select HTML File",
            filetypes=[("HTML files", ("*.html", "*.htm")), ("All files", "*.*")]
        )
        if not file_path:
            logging.info("User canceled HTML import action.")
            return []
        # Easiest fix: return an empty list instead of None
    
        # Show a "please wait" popup (optional)
        self._show_progress_popup("Importing from large HTML...")

        # Create and start a background thread
        self._thread = threading.Thread(
            target=self._parse_and_import,
            args=(file_path,),
            daemon=True
        )
        self._thread.start()

        # Periodically check if the thread has results
        self._check_thread_result()

    def _check_thread_result(self):
        """
        Called periodically on the main thread to check if the worker thread is done.
        If not done, we re-schedule it. If done, we handle the result.
        """
        try:
            success, message, class_names = self._import_queue.get_nowait()
        except queue.Empty:
            # Not done yet, check again in 200 ms
            if self.master:
                self.master.after(200, self._check_thread_result)
            return

        # The thread is done, close the progress popup
        self._close_progress_popup()

        if success:
            # If classes were found
            if class_names:
                messagebox.showinfo("Import Success", message)
                logging.info(message)
            else:
                # No valid classes found
                messagebox.showwarning("No Classes Found", message)
                logging.warning(message)
        else:
            # Error/exception
            messagebox.showerror("Import Error", message)
            logging.error(message)

    def _parse_and_import(self, file_path):
        """
        The worker thread function. We parse the HTML (via parse_html_file)
        and import the students into the AttendanceManager. 
        Then we put the result into the queue.
        """
        try:
            valid_class_codes = self.attendance_manager.get_valid_class_codes()
            class_students = parse_html_file(file_path, valid_class_codes)

            if class_students:
                # Import them into the manager
                for class_name, students in class_students.items():
                    self.attendance_manager.add_class(class_name)
                    self.import_students_with_photos(class_name, students)
                
                msg = f"Students imported successfully from '{file_path}'."
                self._import_queue.put((True, msg, list(class_students.keys())))
            else:
                msg = f"No valid classes found in the HTML file '{file_path}'."
                self._import_queue.put((True, msg, []))
        except Exception as e:
            msg = f"Failed to import students from '{file_path}': {e}"
            self._import_queue.put((False, msg, []))

    def import_students_with_photos(self, class_name, students):
        """
        Actually add each student to the manager, generating/validating photo URLs
        if needed. This runs in the worker thread as well.
        """
        for student in students:
            student_id = student.get('student_id')
            if not student_id:
                logging.warning(f"Missing student_id in class '{class_name}': {student}")
                continue

            if not student.get('name'):
                logging.warning(f"Missing name in class '{class_name}': {student}")
                continue

            # Possibly generate or check photo_url
            if not student.get('photo_url'):
                photo_url = generate_photo_url(student['name'], student.get('email'))
                student['photo_url'] = photo_url if photo_url else ""

            if student['photo_url'] and not is_valid_url(student['photo_url']):
                logging.warning(f"Invalid photo URL for student '{student_id}': {student['photo_url']}")
                student['photo_url'] = ""

            try:
                self.attendance_manager.add_student_to_class(class_name, student)
                logging.info(f"Imported student '{student_id}' in class '{class_name}'.")
            except ValueError as ve:
                logging.error(f"Error adding student '{student_id}' to class '{class_name}': {ve}")
                # skip to next

    # ------------- UI HELPER METHODS -------------
    def _show_progress_popup(self, msg):
        """Show a small popup to let the user know we're busy."""
        if not self.master:
            return
        self._progress_popup = tk.Toplevel(self.master)
        self._progress_popup.title("Please Wait")
        self._progress_popup.geometry("300x100")
        self._progress_popup.resizable(False, False)
        self._progress_popup.grab_set()

        label = tk.Label(self._progress_popup, text=msg)
        label.pack(pady=20, padx=20)

        # Optionally disable close button
        self._progress_popup.protocol("WM_DELETE_WINDOW", lambda: None)

        # Center it
        self._progress_popup.update_idletasks()
        x = (self._progress_popup.winfo_screenwidth() // 2) - (self._progress_popup.winfo_width() // 2)
        y = (self._progress_popup.winfo_screenheight() // 2) - (self._progress_popup.winfo_height() // 2)
        self._progress_popup.geometry(f"+{x}+{y}")

    def _close_progress_popup(self):
        """Close the 'Please Wait' popup if it exists."""
        if self._progress_popup:
            self._progress_popup.destroy()
            self._progress_popup = None
