import tkinter as tk
from tkinter import messagebox
import platform

# Audio alert support for Windows
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


def _play_sound(sound_type="alert"):
    if not HAS_WINSOUND:
        return
    try:
        if sound_type == "alert":
            winsound.MessageBeep(winsound.MB_ICONHAND)
        elif sound_type == "eject":
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        elif sound_type == "success":
            winsound.MessageBeep(winsound.MB_OK)
    except Exception:
        pass


def ask_allow_or_block(drive_letter, serial_number):
    """
    Top-most centered native popup window with audio alert when a new USB drive is detected.
    Returns: True if user chose ALLOW, False if user chose BLOCK.
    """
    _play_sound("alert")

    root = tk.Tk()
    root.title("USB-Sentinel — Security Alert")
    root.geometry("440x240")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.configure(bg="#0B0F17")

    # Center window on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"+{x}+{y}")

    result = {"allowed": False}

    def on_allow():
        result["allowed"] = True
        _play_sound("success")
        root.destroy()

    def on_block():
        result["allowed"] = False
        _play_sound("eject")
        root.destroy()

    # Header label
    hdr = tk.Label(
        root,
        text="🚨 NEW USB DRIVE DETECTED!",
        font=("Segoe UI", 13, "bold"),
        fg="#EF4444",
        bg="#0B0F17",
        pady=12
    )
    hdr.pack()

    # Information text
    info_text = f"Drive Letter:  {drive_letter}\nSerial Number: {serial_number}\n\nDo you trust and want to ALLOW access to this drive?"
    msg = tk.Label(
        root,
        text=info_text,
        font=("Segoe UI", 10),
        fg="#E2E8F0",
        bg="#0B0F17",
        justify="center"
    )
    msg.pack(padx=20, pady=5)

    # Button frame
    btn_frame = tk.Frame(root, bg="#0B0F17", pady=15)
    btn_frame.pack()

    allow_btn = tk.Button(
        btn_frame,
        text="  ALLOW DRIVE  ",
        font=("Segoe UI", 10, "bold"),
        bg="#10B981",
        fg="#FFFFFF",
        activebackground="#059669",
        activeforeground="#FFFFFF",
        bd=0,
        padx=15,
        pady=8,
        cursor="hand2",
        command=on_allow
    )
    allow_btn.pack(side=tk.LEFT, padx=10)

    block_btn = tk.Button(
        btn_frame,
        text="  BLOCK & EJECT  ",
        font=("Segoe UI", 10, "bold"),
        bg="#EF4444",
        fg="#FFFFFF",
        activebackground="#DC2626",
        activeforeground="#FFFFFF",
        bd=0,
        padx=15,
        pady=8,
        cursor="hand2",
        command=on_block
    )
    block_btn.pack(side=tk.LEFT, padx=10)

    # Protocol for closing window X -> treat as block for safety
    root.protocol("WM_DELETE_WINDOW", on_block)

    root.mainloop()
    return result["allowed"]


def ask_scan_now(drive_letter):
    """Prompt user after allowing a drive if they wish to launch an instant file scan."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    message = (
        f"Drive {drive_letter} has been ALLOWED and marked as trusted.\n\n"
        f"Do you want to run an instant security & file scan on {drive_letter} now?"
    )

    result = messagebox.askyesno("USB-Sentinel — Scan Drive?", message, parent=root)
    root.destroy()
    return result


def show_scan_result(result):
    """Show scan result popup notification."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    if "error" in result:
        messagebox.showerror("USB-Sentinel — Error", result["error"], parent=root)
    elif result.get("clean", True):
        _play_sound("success")
        messagebox.showinfo(
            "USB-Sentinel — Drive Clean",
            f"✅ Drive is clean!\n\nFiles analyzed: {result['files_scanned']}\nTime taken: {result['time_taken_seconds']}s",
            parent=root
        )
    else:
        _play_sound("alert")
        infected_list = "\n".join([f"- {i['file']} ({i['threat']})" for i in result["infected_files"]])
        messagebox.showwarning(
            "USB-Sentinel — THREATS FOUND",
            f"⚠️ {result['infected_count']} threat(s) detected!\n\n{infected_list}",
            parent=root
        )

    root.destroy()


def show_eject_notification(drive_letter):
    """Show ejection notification."""
    _play_sound("eject")
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    messagebox.showinfo(
        "USB-Sentinel — Drive Ejected",
        f"🛑 Drive {drive_letter} has been blocked and safely ejected from your system.",
        parent=root
    )
    root.destroy()


if __name__ == "__main__":
    answer = ask_allow_or_block("F:\\", "50E1BA2E")
    print("User choice:", "Allow" if answer else "Block")