import tkinter as tk

def main():
    root = tk.Tk()
    root.title("Tkinter Test")
    label = tk.Label(root, text="Tkinter is working!")
    label.pack(padx=20, pady=20)
    root.mainloop()

if __name__ == "__main__":
    main()