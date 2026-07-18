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

def ask_scan_now(drive_letter):
    root = tk.Tk()
    root.withdraw()

    message = (
        f"Drive {drive_letter} has been allowed.\n\n"
        f"Do you want to scan it for viruses now?\n"
        f"(This may take several minutes for large drives)"
    )

    result = messagebox.askyesno("USB-Sentinel — Scan Drive?", message)
    root.destroy()
    return result


def show_scan_result(result):
    root = tk.Tk()
    root.withdraw()

    if "error" in result:
        messagebox.showerror("USB-Sentinel — Scan Error", result["error"])
    elif result["clean"]:
        messagebox.showinfo(
            "USB-Sentinel — Scan Complete",
            f"✅ No threats found.\n\nFiles scanned: {result['files_scanned']}\nTime taken: {result['time_taken_seconds']}s"
        )
    else:
        infected_list = "\n".join([f"- {i['file']} ({i['threat']})" for i in result["infected_files"]])
        messagebox.showwarning(
            "USB-Sentinel — THREATS FOUND",
            f"⚠️ {result['infected_count']} infected file(s) found!\n\n{infected_list}"
        )

    root.destroy()