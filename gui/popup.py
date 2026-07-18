import tkinter as tk
from tkinter import messagebox

def ask_allow_or_block(drive_letter, serial_number):
    root = tk.Tk()
    root.withdraw()  # hide the empty main window, we only want the popup

    message = (
        f"New USB drive detected!\n\n"
        f"Drive: {drive_letter}\n"
        f"Serial: {serial_number}\n\n"
        f"Do you want to ALLOW this drive?"
    )

    result = messagebox.askyesno("USB-Sentinel — New Drive Detected", message)

    root.destroy()
    return result  # True = Allow, False = Block

if __name__ == "__main__":
    answer = ask_allow_or_block("F:\\", "50E1BA2E")
    print("User chose:", "Allow" if answer else "Block")