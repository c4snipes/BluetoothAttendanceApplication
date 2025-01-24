"""
Main entry point for the Bluetooth-Based Attendance Application.
Initializes the GUI, starts the application, and includes performance profiling.
"""

import tkinter as tk
from tkinter import messagebox
import cProfile
import pstats
import io
import logging
from gui import AttendanceApp
from attendance import AttendanceManager

# Configure basic logging settings
logging.basicConfig(
    level=logging.DEBUG,
    filename='application.log',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    """
    Create the Tk root, instantiate AttendanceManager & AttendanceApp, then start mainloop.
    If an error occurs, log and show a message.
    """
    try:
        root = tk.Tk()
        attendance_manager = AttendanceManager()
        app = AttendanceApp(root)
        root.mainloop()
    except Exception as e:
        logging.exception("An unexpected error occurred:")
        messagebox.showerror("Application Error", f"An unexpected error occurred:\n{e}")
        root.destroy()

if __name__ == "__main__":
    # Profiling block
    profiler = cProfile.Profile()
    profiler.enable()

    main()

    profiler.disable()

    # Dump profiling info
    s = io.StringIO()
    sortby = pstats.SortKey.CUMULATIVE
    ps = pstats.Stats(profiler, stream=s).sort_stats(sortby)
    ps.print_stats()

    with open('profiling_results.txt', 'w') as f:
        f.write(s.getvalue())

    print("Profiling complete. Results written to 'profiling_results.txt'.")
