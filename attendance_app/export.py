# export.py

import logging
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import csv
import os

class Disseminate:
    def __init__(self, master, attendance_manager):
        """
        Initialize the Disseminate class.

        :param master: The root Tkinter window or a parent widget.
        :param attendance_manager: An instance of AttendanceManager.
        """
        self.master = master
        self.attendance_manager = attendance_manager

    def export_all_classes(self):
        """
        Export attendance data for all classes to a user-specified directory.
        The user selects which fields to include in the export once for all classes.
        """
        directory = filedialog.askdirectory(title="Select Directory to Save Attendance Files")
        if directory:
            try:
                # Prompt user to select fields once for all classes
                selected_fields = self.select_export_fields()
                if not selected_fields:
                    messagebox.showwarning("No Fields Selected", "No fields selected for export.")
                    logging.warning("User did not select any fields for export.")
                    return

                for class_name in self.attendance_manager.classes:
                    self.export_attendance(class_name, directory, selected_fields, bulk_export=True)
                messagebox.showinfo("Export Success", "Attendance exported for all classes successfully.")
                logging.info("Exported attendance for all classes.")
            except Exception as e:
                messagebox.showerror("Export All Error", f"Failed to export attendance: {e}")
                logging.error(f"Failed to export attendance for all classes: {e}")
        else:
            logging.info("Export all classes operation canceled by user.")

    def export_attendance(self, class_name, directory=None, selected_fields=None, bulk_export=False):
        """
        Export attendance data for a specific class.

        :param class_name: Name of the class to export.
        :param directory: Directory to save the CSV file. If None, prompts user to select.
        :param selected_fields: List of fields to include in the export. If None, prompts user.
        :param bulk_export: Boolean indicating if it's a bulk export (used to suppress individual field selection).
        """
        # List of exportable fields
        all_fields = ["Student ID", "Name", "MAC Address", "Attendance Count", "Last Seen Time"]

        # If not bulk export and selected_fields not provided, prompt for field selection
        if not bulk_export and selected_fields is None:
            selected_fields = self.select_export_fields()
            if not selected_fields:
                messagebox.showwarning("No Fields Selected", "No fields selected for export.")
                logging.warning("User did not select any fields for export.")
                return

        # If bulk_export and selected_fields not provided, handle error
        if bulk_export and selected_fields is None:
            logging.error("Selected fields must be provided for bulk export.")
            return

        # Determine file path
        if directory:
            file_path = os.path.join(directory, f"{class_name}_attendance.csv")
        else:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialfile=f"{class_name}_attendance.csv",
                title="Save Attendance As"
            )

        if file_path:
            try:
                # Check if file already exists and confirm overwrite
                if not bulk_export and os.path.exists(file_path):
                    if not messagebox.askyesno("Overwrite Confirmation", f"The file '{os.path.basename(file_path)}' already exists. Do you want to overwrite it?"):
                        logging.info(f"User canceled overwriting the file '{file_path}'.")
                        return

                with open(file_path, "w", newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(selected_fields or [])  # Write selected fields as headers

                    # Gather and write student data
                    students = self.attendance_manager.get_all_students(class_name)
                    for student_id, student in students.items():
                        row = []
                        if selected_fields and "Student ID" in selected_fields:
                            row.append(student_id)
                        if selected_fields and "Name" in selected_fields:
                            row.append(student.get("name", ""))
                        if selected_fields and "MAC Address" in selected_fields:
                            macs = self.attendance_manager.get_assigned_macs_for_student(class_name, student_id)
                            row.append(', '.join(macs) if macs else "Unassigned")
                        if selected_fields and "Attendance Count" in selected_fields:
                            count = self.attendance_manager.get_attendance_count(class_name, student_id)
                            row.append(count)
                        if selected_fields and "Last Seen Time" in selected_fields:
                            timestamp = self.attendance_manager.get_attendance_timestamp(class_name, student_id)
                            row.append(timestamp.strftime('%Y-%m-%d %H:%M:%S') if timestamp else "Never")
                        writer.writerow(row)
                if bulk_export:
                    logging.info(f"Exported attendance for class '{class_name}' to '{file_path}'.")
                else:
                    messagebox.showinfo("Export Success", f"Attendance for class '{class_name}' exported successfully.")
                    logging.info(f"Exported attendance for class '{class_name}' to '{file_path}'.")
            except Exception as e:
                if bulk_export:
                    messagebox.showerror("Export Error", f"Failed to export attendance for class '{class_name}': {e}")
                    logging.error(f"Failed to export attendance for class '{class_name}': {e}")
                else:
                    messagebox.showerror("Export Error", f"Failed to export attendance: {e}")
                    logging.error(f"Failed to export attendance for class '{class_name}': {e}")
        else:
            if not bulk_export:
                logging.info("Export attendance operation canceled by user.")
            # No action needed if bulk export and file path is not provided

    def select_export_fields(self):
        """
        Prompt the user to select which fields to include in the export.

        :return: A list of selected fields (e.g. ["Student ID", "Name", ...]).
        """
        selected_fields = []

        # Create a new Toplevel window
        export_popup = tk.Toplevel(self.master)
        export_popup.title("Select Fields to Export")
        export_popup.geometry("300x250")
        export_popup.resizable(False, False)
        export_popup.grab_set()  # Make the popup modal

        # List of exportable fields
        fields = ["Student ID", "Name", "MAC Address", "Attendance Count", "Last Seen Time"]

        # Dictionary to store Checkbutton variables
        checkboxes = {}

        # A frame to place the checkboxes in
        checkbox_frame = ttk.Frame(export_popup)
        checkbox_frame.pack(pady=10, padx=10, anchor='w')

        # Create checkboxes for each field, default them all to True
        for field in fields:
            var = tk.BooleanVar(value=True)
            cb = ttk.Checkbutton(checkbox_frame, text=field, variable=var)
            cb.pack(anchor='w', pady=2)
            checkboxes[field] = var

        # Button frame for "Export" and "Cancel" buttons
        button_frame = ttk.Frame(export_popup)
        button_frame.pack(pady=10)

        # Define the callbacks (on_export_confirm & on_export_cancel)

        def on_export_confirm():
            """
            Gather selected fields and close the dialog.
            """
            selected = [f for f, var in checkboxes.items() if var.get()]
            if selected:
                selected_fields.extend(selected)
                export_popup.destroy()
            else:
                messagebox.showwarning("No Fields Selected", "Please select at least one field to export.")
                logging.warning("User attempted to export without selecting any fields.")

        def on_export_cancel():
            export_popup.destroy()

        # 1) Define the Export button FIRST
        export_btn = ttk.Button(button_frame, text="Export", command=on_export_confirm)
        export_btn.grid(row=0, column=0, padx=5)

        # 2) Define the Cancel button
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=on_export_cancel)
        cancel_btn.grid(row=0, column=1, padx=5)

        # 3) Now define the function that references `export_btn`
        def update_export_button(*args):
            """
            Enable or disable the "Export" button based on whether at least
            one checkbox is selected.
            """
            if any(var.get() for var in checkboxes.values()):
                export_btn.config(state='normal')
            else:
                export_btn.config(state='disabled')

        # Bind each checkbox variable to update_export_button on change
        for var in checkboxes.values():
            var.trace_add('write', update_export_button)

        # Manually call once so it sets the correct initial state
        update_export_button()

        # Center the popup on screen
        export_popup.update_idletasks()
        x = (self.master.winfo_screenwidth() // 2) - (export_popup.winfo_width() // 2)
        y = (self.master.winfo_screenheight() // 2) - (export_popup.winfo_height() // 2)
        export_popup.geometry(f"+{x}+{y}")

        # Wait until the popup is closed
        self.master.wait_window(export_popup)

        return selected_fields
