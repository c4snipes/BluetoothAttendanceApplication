# widgets.py

import tkinter as tk
from tkinter import ttk
import platform

def create_notebook(master):
    """
    Create a Notebook widget for tabbed interfaces.
    """
    notebook = ttk.Notebook(master)
    notebook.pack(fill="both", expand=True)
    return notebook

def create_settings_tab(notebook, valid_class_codes, class_names):
    """
    Build a Settings tab for:
      - Delete DB
      - Change theme
      - Add new class
      - Add new class code
      - Import HTML
      - Export all
      - Delete a specific class
    """
    settings_frame = ttk.Frame(notebook)
    notebook.add(settings_frame, text="Settings")

    main_frame = ttk.Frame(settings_frame)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)
    main_frame.columnconfigure(1, weight=1)

    rowidx = 0

    # 1) Delete DB
    lbl_delete = ttk.Label(main_frame, text="Delete Student Database:")
    lbl_delete.grid(row=rowidx, column=0, sticky="w", pady=5)
    delete_button = ttk.Button(main_frame, text="Delete Database", style="Danger.TButton")
    delete_button.grid(row=rowidx, column=1, sticky="w", pady=5)
    style = ttk.Style()
    style.configure("Danger.TButton", foreground="red")
    rowidx += 1

    # 2) Change Theme
    lbl_theme = ttk.Label(main_frame, text="Change Application Theme:")
    lbl_theme.grid(row=rowidx, column=0, sticky="w", pady=5)
    theme_combo = ttk.Combobox(main_frame, values=sorted(style.theme_names()), state="readonly")
    current_theme = style.theme_use()
    theme_combo.set(current_theme)
    theme_combo.grid(row=rowidx, column=1, sticky="w", pady=5)
    rowidx += 1

    # 3) Add new class
    lbl_class = ttk.Label(main_frame, text="Add New Class:")
    lbl_class.grid(row=rowidx, column=0, sticky="w", pady=5)
    class_entry = ttk.Entry(main_frame)
    class_entry.grid(row=rowidx, column=1, sticky="ew", pady=5)
    add_class_button = ttk.Button(main_frame, text="Add Class")
    add_class_button.grid(row=rowidx, column=2, sticky="w", pady=5)
    rowidx += 1

    # 4) Display current class codes
    lbl_codes = ttk.Label(main_frame, text="Current Class Codes:")
    lbl_codes.grid(row=rowidx, column=0, sticky="w", pady=5)
    code_str = ", ".join([c for c in valid_class_codes if c.isalpha()])
    valid_class_codes_var = tk.StringVar(value=code_str)
    code_display = ttk.Label(main_frame, textvariable=valid_class_codes_var)
    code_display.grid(row=rowidx, column=1, sticky="w", pady=5)
    rowidx += 1

    # 5) Add new class code
    lbl_new_code = ttk.Label(main_frame, text="Add New Class Identifier:")
    lbl_new_code.grid(row=rowidx, column=0, sticky="w", pady=5)
    rowidx += 1
    lbl_new_code_help = ttk.Label(main_frame, text="(Used when importing HTML)", foreground="gray")
    lbl_new_code_help.grid(row=rowidx, column=0, columnspan=3, sticky="w", pady=5)
    rowidx += 1
    new_code_entry = ttk.Entry(main_frame)
    new_code_entry.grid(row=rowidx, column=1, sticky="ew", pady=5)
    add_code_button = ttk.Button(main_frame, text="Add Code")
    add_code_button.grid(row=rowidx, column=2, sticky="w", pady=5)
    rowidx += 1

    # 6) Import HTML
    lbl_import = ttk.Label(main_frame, text="Import Classes from HTML:")
    lbl_import.grid(row=rowidx, column=0, sticky="w", pady=5)
    import_html_button = ttk.Button(main_frame, text="Import HTML")
    import_html_button.grid(row=rowidx, column=1, sticky="w", pady=5)
    rowidx += 1

    # 7) Export all
    lbl_export_all = ttk.Label(main_frame, text="Export All Classes:")
    lbl_export_all.grid(row=rowidx, column=0, sticky="w", pady=5)
    export_all_button = ttk.Button(main_frame, text="Export All")
    export_all_button.grid(row=rowidx, column=1, sticky="w", pady=5)
    rowidx += 1

    # 8) Delete existing class
    lbl_delete_class = ttk.Label(main_frame, text="Delete Existing Class:")
    lbl_delete_class.grid(row=rowidx, column=0, sticky="w", pady=5)
    class_combo = ttk.Combobox(main_frame, values=class_names, state="readonly")
    class_combo.grid(row=rowidx, column=1, sticky="w", pady=5)
    delete_class_button = ttk.Button(main_frame, text="Delete Class")
    delete_class_button.grid(row=rowidx, column=2, sticky="w", pady=5)
    rowidx += 1

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
        'delete_class_button': delete_class_button
    }

def create_class_tab_widgets_with_photos(parent_frame, attendance_manager):
    """
    1) Build a top row of controls (Add Student, Start/Stop Scanning, etc.)
    2) Replace the PanedWindow with two side-by-side frames for Present/Absent (improvement #6)
    3) Color-code those frames for clarity (improvement #7)
    4) Add a short help text next to Scan Interval (improvement #10)
    """
    # -- Create or configure a Style for color-coded frames --
    style = ttk.Style()
    style.configure("Present.TFrame", background="#d4fdd4")  # light green
    style.configure("Absent.TFrame", background="#ffecec")   # light red

    main_frame = ttk.Frame(parent_frame)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # top button row
    button_frame = ttk.Frame(main_frame)
    button_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

    # If you have multiple columns, configure them
    for i in range(10):
        button_frame.columnconfigure(i, weight=0)
    # Let the far-right column stretch if you want spacing
    button_frame.columnconfigure(9, weight=1)

    add_student_button = ttk.Button(button_frame, text="Add Student")
    add_student_button.grid(row=0, column=0, padx=5, sticky="w")

    scan_toggle_button = ttk.Button(button_frame, text="Start Scanning")
    scan_toggle_button.grid(row=0, column=1, padx=5, sticky="w")

    export_button = ttk.Button(button_frame, text="Export Attendance")
    export_button.grid(row=0, column=2, padx=5, sticky="w")

    # Scan Interval Label
    lbl_interval = ttk.Label(button_frame, text="Scan Interval:")
    lbl_interval.grid(row=0, column=3, padx=5, sticky="e")

    # Combobox for interval
    interval_options = ["5 seconds","10 seconds","15 seconds","30 seconds","60 seconds"]
    interval_var = tk.StringVar(value="10 seconds")
    interval_dropdown = ttk.Combobox(button_frame, textvariable=interval_var,
                                     values=interval_options, state="readonly", width=10)
    interval_dropdown.grid(row=0, column=4, padx=5, sticky="w")

    # (improvement #10) Brief help text about intervals
    help_interval = ttk.Label(button_frame, text="(Shorter = faster detection, more CPU usage)", foreground="gray")
    help_interval.grid(row=1, column=3, columnspan=2, sticky="w", padx=5)

    # RSSI
    lbl_rssi = ttk.Label(button_frame, text="Signal Strength:")
    lbl_rssi.grid(row=0, column=5, padx=5, sticky="e")
    rssi_options = [
        "Very Close (> -50 dBm)",
        "Close (> -60 dBm)",
        "Medium (> -70 dBm)",
        "Far (> -80 dBm)",
        "Very Far (> -90 dBm)"
    ]
    rssi_var = tk.StringVar(value="Medium (> -70 dBm)")
    rssi_dropdown = ttk.Combobox(button_frame, textvariable=rssi_var,
                                 values=rssi_options, state="readonly", width=18)
    rssi_dropdown.grid(row=0, column=6, padx=5, sticky="w")

    # Quit button
    quit_button = ttk.Button(button_frame, text="Quit")
    quit_button.grid(row=0, column=9, padx=5, sticky="e")

   
    present_frame_container = ttk.Frame(main_frame, style="Present.TFrame")
    absent_frame_container = ttk.Frame(main_frame, style="Absent.TFrame")

    # Place them side by side in columns 0 and 1
    present_frame_container.grid(row=1, column=0, sticky="nsew", padx=(10,5), pady=10)
    absent_frame_container.grid(row=1, column=1, sticky="nsew", padx=(5,10), pady=10)

    # Let these two columns expand
    main_frame.columnconfigure(0, weight=1)
    main_frame.columnconfigure(1, weight=1)
    main_frame.rowconfigure(1, weight=1)

    # Add top labels for each section
    lbl_present = ttk.Label(present_frame_container, text="Present", background="#d4fdd4")
    lbl_present.pack(pady=5)

    lbl_absent = ttk.Label(absent_frame_container, text="Absent", background="#ffecec")
    lbl_absent.pack(pady=5)

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
    Create a Canvas + Scrollbars + an internal Frame that can be scrolled.
    """
    outer_frame = ttk.Frame(parent)
    # Adjusted to pack or use grid; here's an example with pack:
    outer_frame.pack(fill="both", expand=True)

    canvas = tk.Canvas(outer_frame)
    vbar = ttk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
    hbar = ttk.Scrollbar(outer_frame, orient="horizontal", command=canvas.xview)
    scroll_frame = ttk.Frame(canvas)

    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

    # Layout
    canvas.pack(side="left", fill="both", expand=True)
    vbar.pack(side="right", fill="y")
    hbar.pack(side="bottom", fill="x")

    # MouseWheel
    def _on_mousewheel(event):
        if platform.system() == "Windows":
            if event.state & 0x1:  # SHIFT pressed
                canvas.xview_scroll(int(-1*(event.delta/120)), "units")
            else:
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        elif platform.system() == "Darwin":
            # macOS
            if event.state & 0x1:  # SHIFT
                canvas.xview_scroll(int(-1*event.delta), "units")
            else:
                canvas.yview_scroll(int(-1*event.delta), "units")
        else:
            # Linux
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

    def _on_shift_mousewheel(event):
        if platform.system() == "Windows":
            canvas.xview_scroll(int(-1*(event.delta/120)), "units")
        elif platform.system() == "Darwin":
            canvas.xview_scroll(int(-1*event.delta), "units")

    canvas.bind("<Enter>", lambda e: canvas.focus_set())
    canvas.bind("<Leave>", lambda e: canvas.focus_set())
    canvas.bind("<MouseWheel>", _on_mousewheel)
    canvas.bind("<Shift-MouseWheel>", _on_shift_mousewheel)
    canvas.bind("<Button-4>", _on_mousewheel)
    canvas.bind("<Button-5>", _on_mousewheel)

    return scroll_frame

def change_theme(theme_name):
    """
    Helper to switch theme if needed.
    """
    style = ttk.Style()
    try:
        style.theme_use(theme_name)
    except Exception as e:
        pass

def bind_tab_dragging(notebook, on_tab_press, on_tab_motion, on_tab_release):
    """
    Enable drag-and-drop reordering of ttk.Notebook tabs.
    """
    notebook.bind("<ButtonPress-1>", on_tab_press, True)
    notebook.bind("<ButtonRelease-1>", on_tab_release, True)
    notebook.bind("<B1-Motion>", on_tab_motion, True)
    
