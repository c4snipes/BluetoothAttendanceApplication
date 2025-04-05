# widgets.py

import tkinter as tk
from tkinter import ttk
import platform

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
        self.widget.bind("<Destroy>", self.hide_tooltip)  # Ensure tooltip is hidden

    def show_tooltip(self, event=None):
        try:
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
            self.tooltip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)  # Remove window decorations
            tw.wm_geometry(f"+{x}+{y}")
            label = tk.Label(
                tw,
                text=self.text,
                background="#FFFFE0",  # Light yellow background
                relief="solid",
                borderwidth=1,
                font=("Arial", 10),
            )
            label.pack()
        except Exception as e:
            pass  # Handle exceptions silently

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

def create_notebook(master):
    """
    Create a Notebook widget for tabbed interfaces.

    :param master: Parent Tkinter widget.
    :return: ttk.Notebook instance.
    """
    notebook = ttk.Notebook(master)
    notebook.pack(fill="both", expand=True)
    return notebook

def create_settings_tab(notebook, valid_class_codes, class_names):
    """
    Create the Settings tab within the Notebook.

    :param notebook: The ttk.Notebook instance.
    :param valid_class_codes: List of valid class codes.
    :param class_names: List of existing class names.
    :return: A dictionary containing widgets that need to be connected to actions.
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

    delete_button = ttk.Button(settings_main_frame, text="Delete Database")
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

    row_counter += 1

    # Class Management Section
    class_label = ttk.Label(settings_main_frame, text="Add New Class")
    class_label.grid(row=row_counter, column=0, sticky="w", pady=5)

    class_entry = ttk.Entry(settings_main_frame)
    class_entry.grid(row=row_counter, column=1, sticky="ew", pady=5)

    add_class_button = ttk.Button(settings_main_frame, text="Add Class")
    add_class_button.grid(row=row_counter, column=2, sticky="w", pady=5)

    row_counter += 1

    # Display Current Class Codes Section
    class_codes_label = ttk.Label(settings_main_frame, text="Current Class Codes:")
    class_codes_label.grid(row=row_counter, column=0, sticky="w", pady=5)

    # Use StringVar for dynamic updates
    valid_class_codes_display = [code for code in valid_class_codes if code.isalpha()]
    valid_class_codes_var = tk.StringVar(value=", ".join(valid_class_codes_display))
    class_codes_display = ttk.Label(
        settings_main_frame, textvariable=valid_class_codes_var
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

    add_code_button = ttk.Button(settings_main_frame, text="Add Code")
    add_code_button.grid(row=row_counter, column=2, sticky="w", pady=5)

    row_counter += 1

    # Import HTML Section
    import_html_label = ttk.Label(settings_main_frame, text="Import Classes from HTML")
    import_html_label.grid(row=row_counter, column=0, sticky="w", pady=5)

    import_html_button = ttk.Button(settings_main_frame, text="Import HTML")
    import_html_button.grid(row=row_counter, column=1, sticky="w", pady=5)

    row_counter += 1

    # Export All Classes Section
    export_all_label = ttk.Label(
        settings_main_frame, text="Export Attendance for All Classes"
    )
    export_all_label.grid(row=row_counter, column=0, sticky="w", pady=5)

    export_all_button = ttk.Button(settings_main_frame, text="Export All")
    export_all_button.grid(row=row_counter, column=1, sticky="w", pady=5)

    row_counter += 1

    # Delete Class Section
    delete_class_label = ttk.Label(settings_main_frame, text="Delete Existing Class")
    delete_class_label.grid(row=row_counter, column=0, sticky="w", pady=5)

    class_combo = ttk.Combobox(settings_main_frame, values=class_names, state="readonly")
    class_combo.grid(row=row_counter, column=1, sticky="w", pady=5)

    delete_class_button = ttk.Button(settings_main_frame, text="Delete Class")
    delete_class_button.grid(row=row_counter, column=2, sticky="w", pady=5)

    # Return the widgets as a dictionary
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
    Create widgets for the Class tab, including configurations to allow resizing
    of the "Absent" and "Present" student lists when the window is resized.
    """
    # Main frame inside the attendance tab
    main_frame = ttk.Frame(parent_frame)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Configure grid to allow resizing
    main_frame.columnconfigure(0, weight=1)
    main_frame.rowconfigure(1, weight=1)  # Allow row 1 (list_frame) to expand
    main_frame.rowconfigure(2, weight=0)

    button_frame = ttk.Frame(main_frame)
    button_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

    # Configure columns to expand appropriately
    for i in range(9):  # Adjusted number of columns
        button_frame.columnconfigure(i, weight=1 if i == 8 else 0)
    button_frame.rowconfigure(0, weight=0)

    # Place buttons using grid
    add_student_button = ttk.Button(button_frame, text="Add Student")
    add_student_button.grid(row=0, column=0, padx=5, sticky="w")

    scan_toggle_button = ttk.Button(button_frame, text="Start Scanning")
    scan_toggle_button.grid(row=0, column=1, padx=5, sticky="w")

    export_button = ttk.Button(button_frame, text="Export Attendance")
    export_button.grid(row=0, column=2, padx=5, sticky="w")

    # Add Scan Interval Dropdown
    interval_label = ttk.Label(button_frame, text="Scan Interval:")
    interval_label.grid(row=0, column=3, padx=5, sticky="e")

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
    interval_dropdown.grid(row=0, column=4, padx=5, sticky="w")

    # Add Signal Strength Dropdown
    rssi_label = ttk.Label(button_frame, text="Signal Strength:")
    rssi_label.grid(row=0, column=5, padx=5, sticky="e")

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
    rssi_dropdown.grid(row=0, column=6, padx=5, sticky="w")
    
    quit_button = ttk.Button(button_frame, text="Quit")
    quit_button.grid(row=0, column=9, padx=5, sticky="e")

    
    # List frame for present and absent students
    paned_window = ttk.PanedWindow(main_frame, orient="horizontal")
    paned_window.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    # Configure main_frame to allow expansion
    main_frame.columnconfigure(0, weight=1)
    main_frame.rowconfigure(1, weight=1)

    # Create frames for Present and Absent students
    present_frame_container = ttk.Frame(paned_window)
    absent_frame_container = ttk.Frame(paned_window)

    # Add the frames to the PanedWindow
    paned_window.add(present_frame_container, weight=1)
    paned_window.add(absent_frame_container, weight=1)

    # Configure frames to expand
    present_frame_container.columnconfigure(0, weight=1)
    present_frame_container.rowconfigure(1, weight=1)
    absent_frame_container.columnconfigure(0, weight=1)
    absent_frame_container.rowconfigure(1, weight=1)

    # Labels for Present and Absent
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
        export_button,
    )

def create_scrollable_frame(parent):
    """
    Create a scrollable frame within a given parent frame.

    :param parent: The parent Tkinter widget.
    :return: The scrollable frame (ttk.Frame).
    """
    canvas = tk.Canvas(parent)
    v_scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    h_scrollbar = ttk.Scrollbar(parent, orient="horizontal", command=canvas.xview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(
        yscrollcommand=v_scrollbar.set,
        xscrollcommand=h_scrollbar.set,
    )

    # Add scrollbars to the grid layout
    canvas.grid(row=1, column=0, sticky="nsew")
    v_scrollbar.grid(row=1, column=1, sticky="ns")
    h_scrollbar.grid(row=2, column=0, sticky="ew")

    # Configure the parent frame to expand
    parent.rowconfigure(1, weight=1)
    parent.columnconfigure(0, weight=1)

    # Bind scroll events
    def _on_mousewheel(event):
        if platform.system() == "Windows":
            if event.state & 0x1:  # Shift key is held down
                canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif platform.system() == "Darwin":
            if event.state & 0x1:  # Shift key is held down
                canvas.xview_scroll(int(-1 * event.delta), "units")
            else:
                canvas.yview_scroll(int(-1 * event.delta), "units")
        else:  # Linux and other platforms
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

    def _on_shift_mousewheel(event):
        if platform.system() == "Windows":
            canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        elif platform.system() == "Darwin":
            canvas.xview_scroll(int(-1 * event.delta), "units")

    # Bind scroll events to the canvas
    canvas.bind("<Enter>", lambda e: canvas.focus_set())
    canvas.bind("<Leave>", lambda e: canvas.focus_set())

    # Windows and macOS
    canvas.bind("<MouseWheel>", _on_mousewheel)
    canvas.bind("<Shift-MouseWheel>", _on_shift_mousewheel)
    # Linux
    canvas.bind("<Button-4>", _on_mousewheel)
    canvas.bind("<Button-5>", _on_mousewheel)

    return scrollable_frame

def change_theme(theme_name):
    """
    Change the application theme.

    :param theme_name: The name of the theme to apply.
    """
    style = ttk.Style()
    try:
        style.theme_use(theme_name)
        # Reconfigure custom styles if necessary
    except Exception as e:
        pass  # Handle exceptions silently

def bind_tab_dragging(notebook, on_tab_press, on_tab_motion, on_tab_release):
    """
    Bind events for tab drag-and-drop functionality.

    :param notebook: The ttk.Notebook instance.
    :param on_tab_press: Function to handle tab press event.
    :param on_tab_motion: Function to handle tab motion event.
    :param on_tab_release: Function to handle tab release event.
    """
    notebook.bind("<ButtonPress-1>", on_tab_press, True)
    notebook.bind("<ButtonRelease-1>", on_tab_release, True)
    notebook.bind("<B1-Motion>", on_tab_motion, True)
