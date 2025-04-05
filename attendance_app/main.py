# main.py

"""
Main entry point for the Bluetooth-Based Attendance Application.
Initializes the GUI and starts the application with profiling.
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
logging.basicConfig(level=logging.DEBUG, filename='application.log',
                    format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    try:
        root = tk.Tk()
        attendance_manager = AttendanceManager()
        app = AttendanceApp(root) # Assuming AttendanceApp has a start method
        root.mainloop()
    except Exception as e:
        logging.exception("An unexpected error occurred:")
        messagebox.showerror("Application Error", f"An unexpected error occurred:\n{e}")
        root.destroy()

if __name__ == "__main__":
    # Create a profiler object
    profiler = cProfile.Profile()
    # Start profiling
    profiler.enable()

    # Run the main function
    main()

    # Stop profiling
    profiler.disable()

    # Create a stream to hold the profiling results
    s = io.StringIO()
    # Create a Stats object and sort the results by cumulative time
    sortby = pstats.SortKey.CUMULATIVE
    ps = pstats.Stats(profiler, stream=s).sort_stats(sortby)
    # Print the profiling results
    ps.print_stats()

    # Write the profiling results to a file
    with open('profiling_results.txt', 'w') as f:
        f.write(s.getvalue())

    print("Profiling complete. Results written to 'profiling_results.txt'.")
