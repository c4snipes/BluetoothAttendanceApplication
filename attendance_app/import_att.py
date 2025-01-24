# import_att.py
import tkinter as tk
from tkinter import filedialog, messagebox
import logging
import threading
import queue

from html_parse import parse_html_file, generate_photo_url, is_valid_url

class ImportApp:
    """
    Manages importing class/student data from an HTML file in a background thread to avoid freezing the GUI.
    """

    def __init__(self, attendance_manager, master=None, parent_gui=None):
        """
        :param attendance_manager: The AttendanceManager instance
        :param master: A Tk root or parent widget
        :param parent_gui: A reference to the main GUI (AttendanceApp) so we can create new tabs
        """
        self.attendance_manager = attendance_manager
        self.master = master
        self.parent_gui = parent_gui
        self._import_queue = queue.Queue()
        self._thread = None
        self._progress_popup = None

    def import_html_action(self):
        """
        Prompt user to pick an .html file, then parse/import in a background thread.
        """
        file_path = filedialog.askopenfilename(
            title="Select HTML File",
            filetypes=[("HTML files", "*.html *.htm"), ("All files", "*.*")]
        )
        if not file_path:
            logging.info("User canceled HTML import.")
            return

        self._show_progress_popup("Importing from large HTML...")

        # Start background thread to parse the file
        self._thread = threading.Thread(
            target=self._parse_and_import,
            args=(file_path,),
            daemon=True
        )
        self._thread.start()

        # Periodically check if the thread is done
        self._check_thread_result()

    def _check_thread_result(self):
        """
        Check if the background thread has posted results to _import_queue. If not, re-check after 200ms.
        """
        try:
            success, msg, class_names = self._import_queue.get_nowait()
        except queue.Empty:
            if self.master:
                self.master.after(200, self._check_thread_result)
            return

        # If we get here, the thread is done
        self._close_progress_popup()

        if success:
            if class_names:
                # Create tabs for new classes
                for cname in class_names:
                    if self.parent_gui and cname not in self.parent_gui.class_widgets:
                        self.parent_gui.create_class_tab(cname)

                messagebox.showinfo("Import Success", msg)
                logging.info(msg)
            else:
                # No classes were found but success is True
                messagebox.showwarning("No Classes Found", msg)
                logging.warning(msg)
        else:
            # success == False => Some error occurred
            messagebox.showerror("Import Error", msg)
            logging.error(msg)

    def _parse_and_import(self, file_path):
        """
        Worker thread: parse the HTML, import classes & students, then queue the result.
        """
        try:
            valid_codes = self.attendance_manager.get_class_codes()
            class_students = parse_html_file(file_path, valid_codes)

            if class_students:
                for cname, stlist in class_students.items():
                    # Ensure the class is created
                    self.attendance_manager.register_class(cname)
                    for student in stlist:
                        # Possibly re-check or generate photo_url
                        if not student.get('photo_url'):
                            gen = generate_photo_url(student.get('name'), student.get('email'))
                            student['photo_url'] = gen or ""
                        if student['photo_url'] and not is_valid_url(student['photo_url']):
                            logging.warning(f"Invalid photo URL for {student.get('student_id')}: {student['photo_url']}")
                            student['photo_url'] = ""

                        # If they have no student_id, skip or log
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
        """
        Display a small "Please Wait" window while the import is happening.
        """
        if not self.master:
            return

        self._progress_popup = tk.Toplevel(self.master)
        self._progress_popup.title("Importing...")
        self._progress_popup.geometry("300x100")
        self._progress_popup.resizable(False, False)
        self._progress_popup.grab_set()

        label = tk.Label(self._progress_popup, text=msg)
        label.pack(pady=20, padx=20)

        # Disable user from closing this window
        self._progress_popup.protocol("WM_DELETE_WINDOW", lambda: None)

        # Center it on screen
        self._progress_popup.update_idletasks()
        x = (self._progress_popup.winfo_screenwidth() // 2) - (self._progress_popup.winfo_width() // 2)
        y = (self._progress_popup.winfo_screenheight() // 2) - (self._progress_popup.winfo_height() // 2)
        self._progress_popup.geometry(f"+{x}+{y}")

    def _close_progress_popup(self):
        """
        Close the progress window if it exists.
        """
        if self._progress_popup:
            self._progress_popup.destroy()
            self._progress_popup = None
