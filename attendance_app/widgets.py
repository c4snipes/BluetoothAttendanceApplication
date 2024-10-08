# widgets.py

import tkinter as tk
from tkinter import ttk

def create_notebook(master):
    notebook = ttk.Notebook(master)
    notebook.pack(fill='both', expand=True)
    return notebook

def create_settings_tab(notebook, valid_class_codes):
    settings_frame = ttk.Frame(notebook)
    notebook.add(settings_frame, text='Settings')

    settings_main_frame = ttk.Frame(settings_frame)
    settings_main_frame.pack(fill='both', expand=True, padx=10, pady=10)

    # Configure settings_main_frame to expand
    settings_main_frame.columnconfigure(1, weight=1)

    # Delete Student Database Section
    delete_label = ttk.Label(settings_main_frame, text="Delete Student Database")
    delete_label.grid(row=0, column=0, sticky='w', pady=5)

    delete_button = ttk.Button(settings_main_frame, text="Delete Database")
    delete_button.grid(row=0, column=1, sticky='w', pady=5)

    # Change Theme Section
    theme_label = ttk.Label(settings_main_frame, text="Change Application Theme")
    theme_label.grid(row=1, column=0, sticky='w', pady=5)

    theme_combo = ttk.Combobox(settings_main_frame, values=sorted(ttk.Style().theme_names()), state='readonly')
    theme_combo.grid(row=1, column=1, sticky='w', pady=5)
    if ttk.Style().theme_use():
        theme_combo.set(ttk.Style().theme_use())

    # Class Management Section
    class_label = ttk.Label(settings_main_frame, text="Add New Class")
    class_label.grid(row=2, column=0, sticky='w', pady=5)

    class_entry = ttk.Entry(settings_main_frame)
    class_entry.grid(row=2, column=1, sticky='ew', pady=5)
    settings_main_frame.columnconfigure(1, weight=1)

    add_class_button = ttk.Button(settings_main_frame, text="Add Class")
    add_class_button.grid(row=2, column=2, sticky='w', pady=5)

    # Display Current Class Codes Section
    class_codes_label = ttk.Label(settings_main_frame, text="Current Class Codes:")
    class_codes_label.grid(row=3, column=0, sticky='w', pady=5)

    class_codes_display = ttk.Label(settings_main_frame, text=", ".join(valid_class_codes))
    class_codes_display.grid(row=3, column=1, sticky='w', pady=5)

    # Add New Class Code Section
    new_code_label = ttk.Label(settings_main_frame, text="Add New Class Code:")
    new_code_label.grid(row=4, column=0, sticky='w', pady=5)

    new_code_entry = ttk.Entry(settings_main_frame)
    new_code_entry.grid(row=4, column=1, sticky='ew', pady=5)

    add_code_button = ttk.Button(settings_main_frame, text="Add Code")
    add_code_button.grid(row=4, column=2, sticky='w', pady=5)

    # Import HTML Section (This part ensures the Import HTML button is displayed)
    import_html_label = ttk.Label(settings_main_frame, text="Import Classes from HTML")
    import_html_label.grid(row=5, column=0, sticky='w', pady=5)

    import_html_button = ttk.Button(settings_main_frame, text="Import HTML")
    import_html_button.grid(row=5, column=1, sticky='w', pady=5)

    return delete_button, theme_combo, add_class_button, class_entry, add_code_button, new_code_entry, class_codes_display, import_html_button



def create_class_tab_widgets_with_photos(parent_frame):
    # Main frame inside the attendance tab
    main_frame = ttk.Frame(parent_frame)
    main_frame.pack(fill='both', expand=True, padx=10, pady=10)

    # Configure grid to allow resizing
    main_frame.columnconfigure(0, weight=1)
    main_frame.rowconfigure(1, weight=1)
    main_frame.rowconfigure(2, weight=0)

    button_frame = ttk.Frame(main_frame)
    button_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

    # Use grid layout for button_frame
    button_frame.columnconfigure(0, weight=0)
    button_frame.columnconfigure(1, weight=0)
    button_frame.columnconfigure(2, weight=0)
    button_frame.columnconfigure(3, weight=0)
    button_frame.columnconfigure(4, weight=0)
    button_frame.columnconfigure(5, weight=0)
    button_frame.columnconfigure(6, weight=0)
    button_frame.columnconfigure(7, weight=1)
    button_frame.rowconfigure(0, weight=0)

    # Place buttons using grid
    import_button = ttk.Button(button_frame, text="Import Students")
    import_button.grid(row=0, column=0, padx=5, sticky='w')

    add_student_button = ttk.Button(button_frame, text="Add Student")
    add_student_button.grid(row=0, column=1, padx=5, sticky='w')

    stop_scan_button = ttk.Button(button_frame, text="Stop Scanning")
    stop_scan_button.grid(row=0, column=2, padx=5, sticky='w')

    # Add Scan Interval Dropdown
    interval_label = ttk.Label(button_frame, text="Scan Interval:")
    interval_label.grid(row=0, column=3, padx=5, sticky='e')

    interval_options = ['5 seconds', '10 seconds', '15 seconds', '30 seconds', '60 seconds']
    interval_var = tk.StringVar(value='10 seconds')
    interval_dropdown = ttk.Combobox(button_frame, textvariable=interval_var, values=interval_options, state='readonly', width=10)
    interval_dropdown.grid(row=0, column=4, padx=5, sticky='w')

    # Add Signal Strength Dropdown
    rssi_label = ttk.Label(button_frame, text="Signal Strength:")
    rssi_label.grid(row=0, column=5, padx=5, sticky='e')

    rssi_options = [
        'Very Close (> -50 dBm)',
        'Close (> -60 dBm)',
        'Medium (> -70 dBm)',
        'Far (> -80 dBm)',
        'Very Far (> -90 dBm)'
    ]
    rssi_var = tk.StringVar(value='Medium (> -70 dBm)')
    rssi_dropdown = ttk.Combobox(button_frame, textvariable=rssi_var, values=rssi_options, state='readonly', width=18)
    rssi_dropdown.grid(row=0, column=6, padx=5, sticky='w')

    # Add the Quit Button
    quit_button = ttk.Button(button_frame, text="Quit")
    quit_button.grid(row=0, column=7, padx=5, sticky='e')

    list_frame = ttk.Frame(main_frame)
    list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    # Configure list_frame to expand
    list_frame.columnconfigure(0, weight=1)
    list_frame.columnconfigure(1, weight=1)
    list_frame.rowconfigure(0, weight=1)

    present_frame_container = ttk.Frame(list_frame)
    present_frame_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    absent_frame_container = ttk.Frame(list_frame)
    absent_frame_container.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

    # Configure frames to expand
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

    log_text = tk.Text(log_frame, height=5, state='disabled', wrap='word')
    log_text.grid(row=0, column=0, sticky="nsew")

    return button_frame, present_frame_container, absent_frame_container, \
           import_button, add_student_button, stop_scan_button, log_text, \
           interval_var, rssi_var, quit_button

def create_device_assignment_tab(parent_frame):
    # Create the main frame inside the device assignment tab
    main_frame = ttk.Frame(parent_frame)
    main_frame.pack(fill='both', expand=True, padx=10, pady=10)

    # Configure grid to allow resizing
    main_frame.columnconfigure(0, weight=1)
    main_frame.rowconfigure(1, weight=1)

    # Devices Label
    devices_label = ttk.Label(main_frame, text="Detected Devices")
    devices_label.grid(row=0, column=0, pady=5)

    # Devices Listbox (increase width to handle longer text with "First Seen" time)
    devices_listbox = tk.Listbox(main_frame, selectmode=tk.SINGLE, width=60)
    devices_listbox.grid(row=1, column=0, sticky="nsew")
    devices_scrollbar = ttk.Scrollbar(main_frame, orient='vertical', command=devices_listbox.yview)
    devices_scrollbar.grid(row=1, column=1, sticky="ns")
    devices_listbox.config(yscrollcommand=devices_scrollbar.set)

    # Assign Device Button
    assign_device_button = ttk.Button(main_frame, text="Assign Device")
    assign_device_button.grid(row=2, column=0, pady=5)

    return {
        'devices_listbox': devices_listbox,
        'assign_device_button': assign_device_button
    }


def create_scrollable_frame(parent):
    canvas = tk.Canvas(parent)
    scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        '<Configure>',
        lambda e: canvas.configure(
            scrollregion=canvas.bbox('all')
        )
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
    canvas.configure(yscrollcommand=scrollbar.set)

    # Use grid instead of pack
    canvas.grid(row=0, column=0, sticky='nsew')
    scrollbar.grid(row=0, column=1, sticky='ns')

    # Configure grid weights for proper resizing
    parent.grid_rowconfigure(0, weight=1)
    parent.grid_columnconfigure(0, weight=1)

    return scrollable_frame
