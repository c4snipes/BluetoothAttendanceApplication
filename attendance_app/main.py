# main.py

import tkinter as tk
from gui import AttendanceApp

if __name__ == "__main__":
    root = tk.Tk()
    app = AttendanceApp(root)
    root.mainloop()
