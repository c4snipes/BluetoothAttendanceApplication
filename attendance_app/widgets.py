# widgets.py

import tkinter as tk
from tkinter import ttk
import platform
from tkinter import messagebox
from utils import log_message
from widgets import ToolTip  # Ensure this is correctly imported or defined in the same file
import re


def create_notebook(master):
    """
    Create a Notebook widget for tabbed interfaces.

    :param master: Parent Tkinter widget.
    :return: ttk.Notebook instance.
    """
    notebook = ttk.Notebook(master)
    notebook.pack(fill="both", expand=True)
    return notebook


def create_settings_tab(notebook, valid_class_codes, attendance_manager, disseminate):
    """
    Create the Settings tab within the Notebook.

    :param notebook: The ttk.Notebook instance.
    :param valid_class_codes: List of valid class codes.
    :param attendance_manager: Instance of AttendanceManager.
    :param disseminate: Instance of Disseminate for export functions.
    :return: Tuple of widgets for further configuration.
    """
    settings_frame = ttk.Frame(notebook)
    notebook.add(settings_frame, text="Settings")

    settings_main_frame = ttk.Frame(settings_frame)
    settings_main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Configure settings_main_frame to expand
    settings_main_frame.columnconfigure(1, weight=1)

    row_counter = 0

    # Delete Student Database Section
    delete_label = ttk.Label(settings_main_frame, text="Delete Student Database")
    delete_label.grid(row=row_counter, column=0, sticky="w", pady=5)

    delete_button = ttk.Button(settings_main_frame, text="Delete Database",
                               command=lambda: delete_database(attendance_manager))
    delete_button.grid(row=row_counter, column=1, sticky="w", pady=5)

    row_counter += 1

    # Change Theme Section
    theme_label = ttk.Label(settings_main_frame, text="Change Application Theme")
    theme_label.grid(row=row_counter, column=0, sticky="w", pady=5)

    style = ttk.Style()
    theme_combo = ttk.Combobox(
        settings_main_frame, values=sorted(style.theme_names()), state="readonly"
    )
    theme_combo.grid(row=row_counter, column=1, sticky="w", pady=5)
    current_theme = style.theme_use()
    theme_combo.set(current_theme)

    # Bind theme change
    theme_combo.bind('<<ComboboxSelected>>', lambda event: change_theme(theme_combo.get()))

    row_counter += 1

    # Class Management Section
    class_label = ttk.Label(settings_main_frame, text="Add New Class")
    class_label.grid(row=row_counter, column=0, sticky="w", pady=5)

    class_entry = ttk.Entry(settings_main_frame)
    class_entry.grid(row=row_counter, column=1, sticky="ew", pady=5)

    add_class_button = ttk.Button(settings_main_frame, text="Add Class",
                                  command=lambda: add_class(attendance_manager, class_entry.get(),
                                                           class_entry, class_codes_display, notebook, disseminate))
    add_class_button.grid(row=row_counter, column=2, sticky="w", pady=5)

    row_counter += 1

    # Display Current Class Codes Section
    class_codes_label = ttk.Label(settings_main_frame, text="Current Class Codes:")
    class_codes_label.grid(row=row_counter, column=0, sticky="w", pady=5)

    # Only show valid class codes (ensure only valid ones are registered)
    valid_class_codes_display = [code for code in valid_class_codes if code.isalpha()]
    class_codes_display = ttk.Label(
        settings_main_frame, text=", ".join(valid_class_codes_display)
    )
    class_codes_display.grid(row=row_counter, column=1, sticky="w", pady=5)

    row_counter += 1

    # Add New Class Code Section
    new_code_label = ttk.Label(
        settings_main_frame, text="Add New Class Identifier for HTML Parsing:"
    )
    new_code_label.grid(row=row_counter, column=0, sticky="w", pady=5)

    row_counter += 1

    new_code_help = ttk.Label(
        settings_main_frame,
        text="(Used to identify classes when importing from HTML files)",
        foreground="gray",
    )
    new_code_help.grid(row=row_counter, column=0, columnspan=3, sticky="w", pady=5)

    row_counter += 1

    new_code_entry = ttk.Entry(settings_main_frame)
    new_code_entry.grid(row=row_counter, column=1, sticky="ew", pady=5)

    add_code_button = ttk.Button(settings_main_frame, text="Add Code",
                                 command=lambda: add_class_code(attendance_manager, new_code_entry.get(),
                                                              class_codes_display))
    add_code_button.grid(row=row_counter, column=2, sticky="w", pady=5)

    row_counter += 1

    # Import HTML Section
    import_html_label = ttk.Label(settings_main_frame, text="Import Classes from HTML")
    import_html_label.grid(row=row_counter, column=0, sticky="w", pady=5)

    import_html_button = ttk.Button(settings_main_frame, text="Import HTML",
                                    command=lambda: import_html(attendance_manager, disseminate))
    import_html_button.grid(row=row_counter, column=1, sticky="w", pady=5)

    row_counter += 1

    # Export All Classes Section
    export_all_label = ttk.Label(
        settings_main_frame, text="Export Attendance for All Classes"
    )
    export_all_label.grid(row=row_counter, column=0, sticky="w", pady=5)

    export_all_button = ttk.Button(settings_main_frame, text="Export All",
                                   command=lambda: disseminate.export_all_classes())
    export_all_button.grid(row=row_counter, column=1, sticky="w", pady=5)

    return (
        delete_button,
        theme_combo,
        add_class_button,
        class_entry,
        add_code_button,
        new_code_entry,
        class_codes_display,
        import_html_button,
        export_all_button,
    )


def create_class_tab_widgets_with_photos(parent_frame):
    """
    Create widgets for the Class tab, including buttons and student lists.

    :param parent_frame: The parent frame where widgets will be placed.
    :return: Tuple of widgets for further configuration.
    """
    # Main frame inside the attendance tab
    main_frame = ttk.Frame(parent_frame)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Configure grid to allow resizing
    main_frame.columnconfigure(0, weight=1)
    main_frame.rowconfigure(1, weight=1)
    main_frame.rowconfigure(2, weight=0)

    button_frame = ttk.Frame(main_frame)
    button_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

    button_frame.columnconfigure(0, weight=0)
    button_frame.columnconfigure(1, weight=0)
    button_frame.columnconfigure(2, weight=0)
    button_frame.columnconfigure(3, weight=0)
    button_frame.columnconfigure(4, weight=0)
    button_frame.columnconfigure(5, weight=0)
    button_frame.columnconfigure(6, weight=0)
    button_frame.columnconfigure(7, weight=0)
    button_frame.columnconfigure(8, weight=1)
    button_frame.rowconfigure(0, weight=0)

    # Place buttons using grid
    import_button = ttk.Button(button_frame, text="Import Students")
    import_button.grid(row=0, column=0, padx=5, sticky="w")

    add_student_button = ttk.Button(button_frame, text="Add Student")
    add_student_button.grid(row=0, column=1, padx=5, sticky="w")

    stop_scan_button = ttk.Button(button_frame, text="Stop Scanning")
    stop_scan_button.grid(row=0, column=2, padx=5, sticky="w")

    export_button = ttk.Button(button_frame, text="Export Attendance")
    export_button.grid(row=0, column=3, padx=5, sticky="w")

    # Add Scan Interval Dropdown
    interval_label = ttk.Label(button_frame, text="Scan Interval:")
    interval_label.grid(row=0, column=4, padx=5, sticky="e")

    interval_options = [
        "5 seconds",
        "10 seconds",
        "15 seconds",
        "30 seconds",
        "60 seconds",
    ]
    interval_var = tk.StringVar(value="10 seconds")
    interval_dropdown = ttk.Combobox(
        button_frame,
        textvariable=interval_var,
        values=interval_options,
        state="readonly",
        width=10,
    )
    interval_dropdown.grid(row=0, column=5, padx=5, sticky="w")

    # Add Signal Strength Dropdown
    rssi_label = ttk.Label(button_frame, text="Signal Strength:")
    rssi_label.grid(row=0, column=6, padx=5, sticky="e")

    rssi_options = [
        "Very Close (> -50 dBm)",
        "Close (> -60 dBm)",
        "Medium (> -70 dBm)",
        "Far (> -80 dBm)",
        "Very Far (> -90 dBm)",
    ]
    rssi_var = tk.StringVar(value="Medium (> -70 dBm)")
    rssi_dropdown = ttk.Combobox(
        button_frame,
        textvariable=rssi_var,
        values=rssi_options,
        state="readonly",
        width=18,
    )
    rssi_dropdown.grid(row=0, column=7, padx=5, sticky="w")

    quit_button = ttk.Button(button_frame, text="Quit")
    quit_button.grid(row=0, column=8, padx=5, sticky="e")

    list_frame = ttk.Frame(main_frame)
    list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    list_frame.columnconfigure(0, weight=1)
    list_frame.columnconfigure(1, weight=1)
    list_frame.rowconfigure(0, weight=1)

    present_frame_container = ttk.Frame(list_frame)
    present_frame_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    absent_frame_container = ttk.Frame(list_frame)
    absent_frame_container.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

    for frame in [present_frame_container, absent_frame_container]:
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

    present_label = ttk.Label(present_frame_container, text="Present")
    present_label.grid(row=0, column=0, pady=5)

    absent_label = ttk.Label(absent_frame_container, text="Absent")
    absent_label.grid(row=0, column=0, pady=5)

    log_frame = ttk.Frame(main_frame)
    log_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)

    log_text = tk.Text(log_frame, height=5, state="disabled", wrap="word")
    log_text.grid(row=0, column=0, sticky="nsew")

    return (
        button_frame,
        present_frame_container,
        absent_frame_container,
        import_button,
        add_student_button,
        stop_scan_button,
        log_text,
        interval_var,
        rssi_var,
        quit_button,
        export_button,
    )


def create_scrollable_frame(parent):
    """
    Create a scrollable frame within a given parent frame.

    :param parent: The parent Tkinter widget.
    :return: The scrollable frame.
    """
    canvas = tk.Canvas(parent)
    v_scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=v_scrollbar.set)

    # Add scrollbars to the grid layout
    canvas.grid(row=0, column=0, sticky="nsew")
    v_scrollbar.grid(row=0, column=1, sticky="ns")

    parent.grid_rowconfigure(0, weight=1)
    parent.grid_columnconfigure(0, weight=1)

    # Bind scroll events
    def _on_mousewheel(event):
        if platform.system() == "Darwin":
            canvas.yview_scroll(int(-1 * (event.delta)), "units")
        else:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    return scrollable_frame


def change_theme(theme_name):
    """
    Change the application theme.

    :param theme_name: The name of the theme to apply.
    """
    style = ttk.Style()
    style.theme_use(theme_name)


def delete_database(attendance_manager):
    """
    Handle the deletion of the student database with user confirmation.

    :param attendance_manager: Instance of AttendanceManager.
    """
    if messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete the student database? This action cannot be undone."):
        attendance_manager.delete_database()
        messagebox.showinfo("Database Deleted", "Student database has been deleted.")
    else:
        log_message("Database deletion canceled by user.", "info")


def add_class(attendance_manager, class_name, class_entry, class_codes_display, notebook, disseminate):
    """
    Add a new class to the AttendanceManager and create its corresponding tab.

    :param attendance_manager: Instance of AttendanceManager.
    :param class_name: Name of the class to add.
    :param class_entry: Tkinter Entry widget for class name input.
    :param class_codes_display: Tkinter Label widget displaying current class codes.
    :param notebook: ttk.Notebook instance.
    :param disseminate: Instance of Disseminate for export functions.
    """
    class_name = class_name.strip()
    if class_name:
        attendance_manager.add_class(class_name)
        create_class_tab(notebook, class_name, attendance_manager, disseminate)
        class_entry.delete(0, tk.END)
        messagebox.showinfo("Class Added", f"Class '{class_name}' has been added.")
    else:
        messagebox.showwarning("Input Error", "Class name cannot be empty.")


def add_class_code(attendance_manager, new_code, class_codes_display):
    """
    Add a new class code for HTML parsing.

    :param attendance_manager: Instance of AttendanceManager.
    :param new_code: The new class code to add.
    :param class_codes_display: Tkinter Label widget displaying current class codes.
    """
    new_code = new_code.strip().upper()
    if new_code and new_code.isalpha():
        if new_code not in attendance_manager.valid_class_codes:
            attendance_manager.valid_class_codes.append(new_code)
            class_codes_display.config(text=", ".join(attendance_manager.valid_class_codes))
            messagebox.showinfo("Success", f"Added new class code: {new_code}")
            log_message(f"Added new class code: {new_code}")
        else:
            messagebox.showwarning("Duplicate Code", f"The class code '{new_code}' already exists.")
    else:
        messagebox.showerror("Invalid Code", "Please enter a valid class code consisting of alphabetic characters only.")


def import_html(attendance_manager, disseminate):
    """
    Handle the import of students from an HTML file.

    :param attendance_manager: Instance of AttendanceManager.
    :param disseminate: Instance of Disseminate for export functions.
    """
    from import_att import importApp  # Ensure importApp is correctly imported
    importer = importApp(attendance_manager)
    imported_classes = importer.import_html_action()
    if imported_classes:
        for class_name in imported_classes:
            if class_name not in [ttk.Notebook.tab(i, "text") for i in range(ttk.Notebook.index("end"))]:
                create_class_tab(disseminate.master.notebook, class_name, attendance_manager, disseminate)
            # Update the GUI lists for the class
            # This assumes you have a method to refresh the GUI, adjust as necessary
            # For example:
            # update_student_lists(class_name)
        messagebox.showinfo("Import Success", "Students imported successfully from HTML.")
    else:
        messagebox.showwarning("Import Warning", "No classes were imported from the HTML file.")


def create_class_tab(notebook, class_name, attendance_manager, disseminate):
    """
    Create a new tab for the specified class.

    :param notebook: ttk.Notebook instance.
    :param class_name: Name of the class.
    :param attendance_manager: Instance of AttendanceManager.
    :param disseminate: Instance of Disseminate for export functions.
    """
    from gui import AttendanceApp  # Ensure this is correctly imported if necessary
    # Here, it's assumed that the AttendanceApp has a method to create class tabs.
    # This function can be adjusted based on the actual implementation of the main application.
    pass  # Implement based on main application structure


class ToolTip:
    """
    Create a tooltip for a given widget.
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # Remove window decorations
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            background="yellow",
            relief="solid",
            borderwidth=1,
            font=("Arial", 10),
        )
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
