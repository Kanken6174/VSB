# main.py
import sys
import tkinter as tk
from tkinter import filedialog

from gui import run_gui

def main():
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        directory = filedialog.askdirectory(title="Select VHDL Project Directory")
        root.destroy()
    
    if not directory:
        print("No directory selected. Exiting.")
        sys.exit(1)
    
    run_gui(directory)

if __name__ == "__main__":
    main()
