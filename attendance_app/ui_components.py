# ui_components.py

import tkinter as tk
from tkinter import ttk
import platform

class ToolTip:
    """
    Creates a tooltip for a given widget.
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.widget.bind("<Destroy>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        try:
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
            self.tooltip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            label = tk.Label(tw, text=self.text, background="#FFFFE0",
                             relief="solid", borderwidth=1, font=("Arial", 10))
            label.pack()
        except Exception:
            pass

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

def create_notebook(master):
    """
    Creates and packs a Notebook widget.
    """
    notebook = ttk.Notebook(master)
    notebook.pack(fill="both", expand=True)
    return notebook

def create_settings_tab(notebook, valid_class_codes, class_names):
    """
    Creates a Settings tab with controls for database actions, theme changes, and class management.
    """
    settings_frame = ttk.Frame(notebook)
    notebook.add(settings_frame, text="Settings")
    settings_main_frame = ttk.Frame(settings_frame)
    settings_main_frame.pack(fill="both", expand=True, padx=10, pady=10)
    settings_main_frame.columnconfigure(1, weight=1)
    row = 0

    delete_label = ttk.Label(settings_main_frame, text="Delete Student Database")
    delete_label.grid(row=row, column=0, sticky="w", pady=5)
    delete_button = ttk.Button(settings_main_frame, text="Delete Database")
    delete_button.grid(row=row, column=1, sticky="w", pady=5)
    row += 1

    theme_label = ttk.Label(settings_main_frame, text="Change Application Theme")
    theme_label.grid(row=row, column=0, sticky="w", pady=5)
    style = ttk.Style()
    theme_combo = ttk.Combobox(settings_main_frame, values=sorted(style.theme_names()), state="readonly")
    theme_combo.grid(row=row, column=1, sticky="w", pady=5)
    current_theme = style.theme_use()
    theme_combo.set(current_theme)
    row += 1

    class_label = ttk.Label(settings_main_frame, text="Add New Class")
    class_label.grid(row=row, column=0, sticky="w", pady=5)
    class_entry = ttk.Entry(settings_main_frame)
    class_entry.grid(row=row, column=1, sticky="ew", pady=5)
    add_class_button = ttk.Button(settings_main_frame, text="Add Class")
    add_class_button.grid(row=row, column=2, sticky="w", pady=5)
    row += 1

    class_codes_label = ttk.Label(settings_main_frame, text="Current Class Codes:")
    class_codes_label.grid(row=row, column=0, sticky="w", pady=5)
    valid_class_codes_display = [code for code in valid_class_codes if code.isalpha()]
    valid_class_codes_var = tk.StringVar(value=", ".join(valid_class_codes_display))
    class_codes_display = ttk.Label(settings_main_frame, textvariable=valid_class_codes_var)
    class_codes_display.grid(row=row, column=1, sticky="w", pady=5)
    row += 1

    new_code_label = ttk.Label(settings_main_frame, text="Add New Class Identifier for HTML Parsing:")
    new_code_label.grid(row=row, column=0, sticky="w", pady=5)
    row += 1

    new_code_help = ttk.Label(settings_main_frame,
                              text="(Used to identify classes when importing from HTML files)",
                              foreground="gray")
    new_code_help.grid(row=row, column=0, columnspan=3, sticky="w", pady=5)
    row += 1

    new_code_entry = ttk.Entry(settings_main_frame)
    new_code_entry.grid(row=row, column=1, sticky="ew", pady=5)
    add_code_button = ttk.Button(settings_main_frame, text="Add Code")
    add_code_button.grid(row=row, column=2, sticky="w", pady=5)
    row += 1

    import_html_label = ttk.Label(settings_main_frame, text="Import Classes from HTML")
    import_html_label.grid(row=row, column=0, sticky="w", pady=5)
    import_html_button = ttk.Button(settings_main_frame, text="Import HTML")
    import_html_button.grid(row=row, column=1, sticky="w", pady=5)
    row += 1

    export_all_label = ttk.Label(settings_main_frame, text="Export Attendance for All Classes")
    export_all_label.grid(row=row, column=0, sticky="w", pady=5)
    export_all_button = ttk.Button(settings_main_frame, text="Export All")
    export_all_button.grid(row=row, column=1, sticky="w", pady=5)
    row += 1

    delete_class_label = ttk.Label(settings_main_frame, text="Delete Existing Class")
    delete_class_label.grid(row=row, column=0, sticky="w", pady=5)
    class_combo = ttk.Combobox(settings_main_frame, values=class_names, state="readonly")
    class_combo.grid(row=row, column=1, sticky="w", pady=5)
    delete_class_button = ttk.Button(settings_main_frame, text="Delete Class")
    delete_class_button.grid(row=row, column=2, sticky="w", pady=5)

    return {
        'delete_button': delete_button,
        'theme_combo': theme_combo,
        'add_class_button': add_class_button,
        'class_entry': class_entry,
        'add_code_button': add_code_button,
        'new_code_entry': new_code_entry,
        'valid_class_codes_var': valid_class_codes_var,
        'import_html_button': import_html_button,
        'export_all_button': export_all_button,
        'class_combo': class_combo,
        'delete_class_button': delete_class_button,
    }

def create_class_tab_widgets_with_photos(parent_frame, attendance_manager):
    """
    Creates the widgets for a class tab with sections for present and absent students.
    """
    main_frame = ttk.Frame(parent_frame)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)
    main_frame.columnconfigure(0, weight=1)
    main_frame.rowconfigure(1, weight=1)
    button_frame = ttk.Frame(main_frame)
    button_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
    for i in range(9):
        button_frame.columnconfigure(i, weight=1 if i == 8 else 0)
    add_student_button = ttk.Button(button_frame, text="Add Student")
    add_student_button.grid(row=0, column=0, padx=5, sticky="w")
    scan_toggle_button = ttk.Button(button_frame, text="Start Scanning")
    scan_toggle_button.grid(row=0, column=1, padx=5, sticky="w")
    export_button = ttk.Button(button_frame, text="Export Attendance")
    export_button.grid(row=0, column=2, padx=5, sticky="w")
    interval_label = ttk.Label(button_frame, text="Scan Interval:")
    interval_label.grid(row=0, column=3, padx=5, sticky="e")
    interval_options = ["5 seconds", "10 seconds", "15 seconds", "30 seconds", "60 seconds"]
    interval_var = tk.StringVar(value="10 seconds")
    interval_dropdown = ttk.Combobox(button_frame, textvariable=interval_var, values=interval_options, state="readonly", width=10)
    interval_dropdown.grid(row=0, column=4, padx=5, sticky="w")
    rssi_label = ttk.Label(button_frame, text="Signal Strength:")
    rssi_label.grid(row=0, column=5, padx=5, sticky="e")
    rssi_options = ["Very Close (> -50 dBm)", "Close (> -60 dBm)", "Medium (> -70 dBm)", "Far (> -80 dBm)", "Very Far (> -90 dBm)"]
    rssi_var = tk.StringVar(value="Medium (> -70 dBm)")
    rssi_dropdown = ttk.Combobox(button_frame, textvariable=rssi_var, values=rssi_options, state="readonly", width=18)
    rssi_dropdown.grid(row=0, column=6, padx=5, sticky="w")
    quit_button = ttk.Button(button_frame, text="Quit")
    quit_button.grid(row=0, column=9, padx=5, sticky="e")
    paned_window = ttk.PanedWindow(main_frame, orient="horizontal")
    paned_window.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
    present_frame_container = ttk.Frame(paned_window)
    absent_frame_container = ttk.Frame(paned_window)
    paned_window.add(present_frame_container, weight=1)
    paned_window.add(absent_frame_container, weight=1)
    present_label = ttk.Label(present_frame_container, text="Present")
    present_label.grid(row=0, column=0, pady=5)
    absent_label = ttk.Label(absent_frame_container, text="Absent")
    absent_label.grid(row=0, column=0, pady=5)
    return (
        button_frame,
        present_frame_container,
        absent_frame_container,
        add_student_button,
        scan_toggle_button,
        interval_var,
        rssi_var,
        quit_button,
        export_button
    )

def create_scrollable_frame(parent):
    """
    Creates a scrollable frame within a parent widget.
    """
    canvas = tk.Canvas(parent)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    return scrollable_frame

def bind_tab_dragging(notebook, on_press, on_motion, on_release):
    """
    Binds events to enable dragging of tabs within a Notebook.
    """
    notebook.bind("<ButtonPress-1>", on_press)
    notebook.bind("<B1-Motion>", on_motion)
    notebook.bind("<ButtonRelease-1>", on_release)

def change_theme(theme_name):
    """
    Changes the application theme using ttk.Style.
    """
    style = ttk.Style()
    try:
        style.theme_use(theme_name)
    except Exception as e:
        print(f"Error changing theme: {e}")
