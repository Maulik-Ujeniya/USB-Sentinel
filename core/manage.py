from db import list_all_drives, forget_drive

def show_drives():
    drives = list_all_drives()
    if not drives:
        print("No drives saved yet.")
        return

    print("\nSaved Drives:")
    print("-" * 60)
    for serial, letter, count, trusted in drives:
        status = "Trusted" if trusted == 1 else "Not Trusted"
        print(f"Serial: {serial} | Letter: {letter} | Connected: {count}x | Status: {status}")
    print("-" * 60)

def main():
    show_drives()
    serial_to_forget = input("\nEnter Serial Number to FORGET (or press Enter to skip): ").strip()
    if serial_to_forget:
        forget_drive(serial_to_forget)
        print(f"Drive {serial_to_forget} forgotten. It will be treated as unknown next time.")

if __name__ == "__main__":
    main()