import logging
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import csv
import os
from attendance import AttendanceManager

class Disseminate:
    """
    Handles the exporting of attendance data to CSV files.
    Provides methods to export an individual class or all classes at once.
    """

    def __init__(self, master, attendance_manager: AttendanceManager):
        """
        :param master: A Tk root or parent widget
        :param attendance_manager: The AttendanceManager instance
        """
        self.master = master
        self.attendance_manager = attendance_manager

    def export_all_classes(self):
        """
        Export attendance for every class to a chosen directory.
        First prompts user to choose a directory and which columns to export.
        """
        directory = filedialog.askdirectory(title="Select Directory to Save CSVs")
        if directory:
            try:
                fields = self.select_export_fields()
                if not fields:
                    messagebox.showwarning("No Fields", "No fields chosen for export.")
                    logging.warning("User chose no fields to export.")
                    return

                # Export each known class
                for cname in self.attendance_manager.classes:
                    self.export_attendance(cname, directory, fields, bulk_export=True)

                messagebox.showinfo("Export Complete", "Exported all classes to CSV.")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))
                logging.error(f"export_all_classes error: {e}")
        else:
            logging.info("User canceled export_all_classes selection.")

    def export_attendance(self, class_name, directory=None, selected_fields=None, bulk_export=False):
        """
        Export attendance for a single class to CSV.
        :param class_name: Name of the class to export
        :param directory: If given, place CSV here; else we ask user.
        :param selected_fields: Columns chosen by the user
        :param bulk_export: If True, skip the prompt for fields again.
        """
        all_fields = ["Student ID", "Name", "MAC Addresses", "Time-Based Count", "Last Seen Time"]

        # If we're not doing bulk export, we might need to prompt for fields again
        if not bulk_export and selected_fields is None:
            selected_fields = self.select_export_fields()
            if not selected_fields:
                return

        # If bulk_export is True but selected_fields is None, that's an error
        if bulk_export and selected_fields is None:
            logging.error("Bulk export requires selected_fields but got None.")
            return

        # Ensure selected_fields is a list
        if selected_fields is None:
            selected_fields = []

        # Determine the file path
        if directory:
            file_path = os.path.join(directory, f"{class_name}_attendance.csv")
        else:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialfile=f"{class_name}_attendance.csv",
                title="Save CSV As"
            )

        if not file_path:
            logging.info("User canceled single-class export.")
            return

        # Prompt user if file exists
        if not bulk_export and os.path.exists(file_path):
            if not messagebox.askyesno("Overwrite?", f"File '{os.path.basename(file_path)}' exists. Overwrite?"):
                return

        try:
            with open(file_path, "w", newline='', encoding='utf-8') as csvf:
                writer = csv.writer(csvf)
                writer.writerow(selected_fields)

                # Gather data for this class
                students = self.attendance_manager.get_all_students(class_name)

                for sid, sdata in students.items():
                    row = []
                    # Fill in each column
                    if "Student ID" in selected_fields:
                        row.append(sid)
                    if "Name" in selected_fields:
                        row.append(sdata.get("name", ""))
                    if "MAC Addresses" in selected_fields:
                        macs = self.attendance_manager.list_macs_for_student(class_name, sid)
                        row.append(", ".join(macs) if macs else "Unassigned")
                    if "Time-Based Count" in selected_fields:
                        tcount = self.attendance_manager.get_time_based_count(class_name, sid)
                        row.append(tcount)
                    if "Last Seen Time" in selected_fields:
                        ts = self.attendance_manager.get_attendance_timestamp(class_name, sid)
                        if ts:
                            row.append(ts.strftime('%Y-%m-%d %H:%M:%S'))
                        else:
                            row.append("Never")

                    writer.writerow(row)

            if bulk_export:
                logging.info(f"Exported '{class_name}' to '{file_path}'.")
            else:
                messagebox.showinfo("Exported", f"Exported '{class_name}' to '{file_path}'.")

        except Exception as e:
            logging.error(f"Failed to export {class_name}: {e}")
            messagebox.showerror("Export Error", str(e))

    def select_export_fields(self):
        """
        Prompt the user to select which columns they want to export.
        Returns a list of chosen fields, or [] if none are selected.
        """
        fields = ["Student ID", "Name", "MAC Addresses", "Time-Based Count", "Last Seen Time"]
        selected = []

        popup = tk.Toplevel(self.master)
        popup.title("Select Export Fields")
        popup.geometry("320x300")
        popup.resizable(False, False)
        popup.grab_set()

        checks = {}
        frm = ttk.Frame(popup)
        frm.pack(pady=10, padx=10, anchor='w')

        # Create a checkbox for each possible field
        for f in fields:
            var = tk.BooleanVar(value=True)
            cb = ttk.Checkbutton(frm, text=f, variable=var)
            cb.pack(anchor='w', pady=2)
            checks[f] = var

        btn_frame = ttk.Frame(popup)
        btn_frame.pack(pady=10)

        def on_confirm():
            chosen = [f for f, var in checks.items() if var.get()]
            if chosen:
                selected.extend(chosen)
                popup.destroy()
            else:
                messagebox.showwarning("No Fields", "Select at least one field to export.")

        def on_cancel():
            popup.destroy()

        def on_select_all():
            for var in checks.values():
                var.set(True)

        def on_deselect_all():
            for var in checks.values():
                var.set(False)

        export_btn = ttk.Button(btn_frame, text="Export", command=on_confirm)
        export_btn.grid(row=0, column=0, padx=5)

        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=on_cancel)
        cancel_btn.grid(row=0, column=1, padx=5)

        # "Select All" and "Deselect All" buttons
        sa_btn = ttk.Button(btn_frame, text="Select All", command=on_select_all)
        sa_btn.grid(row=1, column=0, padx=5, pady=(5,0))

        da_btn = ttk.Button(btn_frame, text="Deselect All", command=on_deselect_all)
        da_btn.grid(row=1, column=1, padx=5, pady=(5,0))

        # Keep your update_button logic, to enable/disable the Export button
        def update_button(*_):
            if any(var.get() for var in checks.values()):
                export_btn.config(state='normal')
            else:
                export_btn.config(state='disabled')

        for var in checks.values():
            var.trace_add('write', update_button)
        update_button()

        # center on screen
        popup.update_idletasks()
        x = (self.master.winfo_screenwidth() // 2) - (popup.winfo_width() // 2)
        y = (self.master.winfo_screenheight() // 2) - (popup.winfo_height() // 2)
        popup.geometry(f"+{x}+{y}")

        # Block until the user closes the popup
        self.master.wait_window(popup)
        return selected
