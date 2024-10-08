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

    # Row counter to avoid overlapping rows
    row_counter = 0

    # Delete Student Database Section
    delete_label = ttk.Label(settings_main_frame, text="Delete Student Database")
    delete_label.grid(row=row_counter, column=0, sticky='w', pady=5)

    delete_button = ttk.Button(settings_main_frame, text="Delete Database")
    delete_button.grid(row=row_counter, column=1, sticky='w', pady=5)

    row_counter += 1

    # Change Theme Section
    theme_label = ttk.Label(settings_main_frame, text="Change Application Theme")
    theme_label.grid(row=row_counter, column=0, sticky='w', pady=5)

    theme_combo = ttk.Combobox(settings_main_frame, values=sorted(ttk.Style().theme_names()), state='readonly')
    theme_combo.grid(row=row_counter, column=1, sticky='w', pady=5)
    if ttk.Style().theme_use():
        theme_combo.set(ttk.Style().theme_use())

    row_counter += 1

    # Class Management Section
    class_label = ttk.Label(settings_main_frame, text="Add New Class")
    class_label.grid(row=row_counter, column=0, sticky='w', pady=5)

    class_entry = ttk.Entry(settings_main_frame)
    class_entry.grid(row=row_counter, column=1, sticky='ew', pady=5)

    add_class_button = ttk.Button(settings_main_frame, text="Add Class")
    add_class_button.grid(row=row_counter, column=2, sticky='w', pady=5)

    row_counter += 1

    # Display Current Class Codes Section
    class_codes_label = ttk.Label(settings_main_frame, text="Current Class Codes:")
    class_codes_label.grid(row=row_counter, column=0, sticky='w', pady=5)

    class_codes_display = ttk.Label(settings_main_frame, text=", ".join(valid_class_codes))
    class_codes_display.grid(row=row_counter, column=1, sticky='w', pady=5)

    row_counter += 1

    # Add New Class Code Section
    new_code_label = ttk.Label(settings_main_frame, text="Add New Class Identifier for HTML Parsing:")
    new_code_label.grid(row=row_counter, column=0, sticky='w', pady=5)

    row_counter += 1

    new_code_help = ttk.Label(settings_main_frame, text="(Used to identify classes when importing from HTML files)", foreground="gray")
    new_code_help.grid(row=row_counter, column=0, columnspan=3, sticky='w', pady=5)

    row_counter += 1

    new_code_entry = ttk.Entry(settings_main_frame)
    new_code_entry.grid(row=row_counter, column=1, sticky='ew', pady=5)

    add_code_button = ttk.Button(settings_main_frame, text="Add Code")
    add_code_button.grid(row=row_counter, column=2, sticky='w', pady=5)

    row_counter += 1

    # Import HTML Section
    import_html_label = ttk.Label(settings_main_frame, text="Import Classes from HTML")
    import_html_label.grid(row=row_counter, column=0, sticky='w', pady=5)

    import_html_button = ttk.Button(settings_main_frame, text="Import HTML")
    import_html_button.grid(row=row_counter, column=1, sticky='w', pady=5)

    row_counter += 1

    # Export All Classes Section
    export_all_label = ttk.Label(settings_main_frame, text="Export Attendance for All Classes")
    export_all_label.grid(row=row_counter, column=0, sticky='w', pady=5)

    export_all_button = ttk.Button(settings_main_frame, text="Export All")
    export_all_button.grid(row=row_counter, column=1, sticky='w', pady=5)

    return (delete_button, theme_combo, add_class_button, class_entry,
            add_code_button, new_code_entry, class_codes_display,
            import_html_button, export_all_button)

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
    # Update columnconfigure to accommodate the new columns
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
    import_button.grid(row=0, column=0, padx=5, sticky='w')

    add_student_button = ttk.Button(button_frame, text="Add Student")
    add_student_button.grid(row=0, column=1, padx=5, sticky='w')

    stop_scan_button = ttk.Button(button_frame, text="Stop Scanning")
    stop_scan_button.grid(row=0, column=2, padx=5, sticky='w')

    export_button = ttk.Button(button_frame, text="Export Attendance")
    export_button.grid(row=0, column=3, padx=5, sticky='w')

    # Add Scan Interval Dropdown
    interval_label = ttk.Label(button_frame, text="Scan Interval:")
    interval_label.grid(row=0, column=4, padx=5, sticky='e')

    interval_options = ['5 seconds', '10 seconds', '15 seconds', '30 seconds', '60 seconds']
    interval_var = tk.StringVar(value='10 seconds')
    interval_dropdown = ttk.Combobox(button_frame, textvariable=interval_var, values=interval_options, state='readonly', width=10)
    interval_dropdown.grid(row=0, column=5, padx=5, sticky='w')

    # Add Signal Strength Dropdown
    rssi_label = ttk.Label(button_frame, text="Signal Strength:")
    rssi_label.grid(row=0, column=6, padx=5, sticky='e')

    rssi_options = [
        'Very Close (> -50 dBm)',
        'Close (> -60 dBm)',
        'Medium (> -70 dBm)',
        'Far (> -80 dBm)',
        'Very Far (> -90 dBm)'
    ]
    rssi_var = tk.StringVar(value='Medium (> -70 dBm)')
    rssi_dropdown = ttk.Combobox(button_frame, textvariable=rssi_var, values=rssi_options, state='readonly', width=18)
    rssi_dropdown.grid(row=0, column=7, padx=5, sticky='w')

    # Add the Quit Button
    quit_button = ttk.Button(button_frame, text="Quit")
    quit_button.grid(row=0, column=8, padx=5, sticky='e')

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

    return (button_frame, present_frame_container, absent_frame_container,
            import_button, add_student_button, stop_scan_button, log_text,
            interval_var, rssi_var, quit_button, export_button)

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

def create_student_widget(self, parent_frame, student, student_id, class_name, present):
        frame = ttk.Frame(parent_frame, relief='raised', borderwidth=1)
        frame.pack(padx=5, pady=5, fill='both', expand=True)

        # Use grid layout inside the frame
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)  # For the device assignment column

        # Load student image
        image = self.get_student_image(student)
        image_label = ttk.Label(frame, image=image)
        image_label.image = image
        image_label.grid(row=0, column=0, rowspan=2, padx=5, pady=5)

        # Get assigned MAC addresses
        assigned_macs = self.attendance_manager.get_assigned_macs_for_student(class_name, student_id)
        if assigned_macs:
            # Display last four characters of the MAC addresses
            mac_display = ', '.join([mac[-4:] for mac in assigned_macs])
            name_text = f"{student['name']} (MAC: {mac_display})"
        else:
            name_text = student['name']

        # Student name label
        name_label = ttk.Label(frame, text=name_text)
        name_label.grid(row=0, column=1, sticky='w')

        # Attendance Toggle Button
        buttons_frame = ttk.Frame(frame)
        buttons_frame.grid(row=1, column=1, sticky='e')

        if present:
            action_button = ttk.Button(buttons_frame, text="Mark Absent",
                                    command=lambda: self.mark_student_absent(class_name, student_id))
        else:
            action_button = ttk.Button(buttons_frame, text="Mark Present",
                                    command=lambda: self.mark_student_present(class_name, student_id))

        action_button.pack(side='right', padx=5, pady=5)

        # Device assignment section
        # Get unassigned devices
        unassigned_devices = self.attendance_manager.get_unassigned_devices(self.found_devices)

        if unassigned_devices:
            # Create a variable to hold the selected device
            device_var = tk.StringVar()
            device_var.set("Select Device")

            # Create a list of device options
            device_options = []
            for addr, device_info in unassigned_devices.items():
                addr_short = addr[-4:]
                device_options.append(f"{device_info['name'] or 'Unknown'} ({addr_short})")

            # Create a Combobox for device selection
            device_combo = ttk.Combobox(frame, textvariable=device_var, values=device_options, state='readonly')
            device_combo.grid(row=0, column=2, padx=5, sticky='w')

            # Assign Device Button
            assign_button = ttk.Button(frame, text="Assign",
                                    command=lambda dv=device_var: self.assign_device_to_student_from_ui(class_name, student_id, dv.get()))
            assign_button.grid(row=1, column=2, padx=5, pady=5, sticky='w')
        else:
            # If no unassigned devices, show a label
            no_device_label = ttk.Label(frame, text="No unassigned devices")
            no_device_label.grid(row=0, column=2, padx=5, sticky='w')

        return frame