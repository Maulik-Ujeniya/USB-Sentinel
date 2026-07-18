import subprocess
import platform

def get_drive_serial(device_id):
    os_name = platform.system()  # "Windows", "Darwin" (Mac), or "Linux"

    if os_name == "Windows":
        return _get_serial_windows(device_id)
    elif os_name == "Darwin":
        return _get_serial_mac(device_id)
    elif os_name == "Linux":
        return _get_serial_linux(device_id)
    else:
        return None


def _get_serial_windows(drive_letter):
    drive_letter = drive_letter.replace("\\", "").replace(":", "").strip().upper()
    cmd = [
        "powershell",
        "-Command",
        f"Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='{drive_letter}:'\" | Select-Object -ExpandProperty VolumeSerialNumber"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    serial = result.stdout.strip()
    return serial if serial else None


def _get_serial_mac(device_path):
    # device_path example: "/dev/disk2s1"
    cmd = ["diskutil", "info", device_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    for line in result.stdout.split("\n"):
        if "Volume UUID" in line:
            return line.split(":", 1)[1].strip()
    return None


def _get_serial_linux(device_path):
    # device_path example: "/dev/sdb1"
    cmd = ["udevadm", "info", "--query=property", "--name=" + device_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    for line in result.stdout.split("\n"):
        if line.startswith("ID_SERIAL="):
            return line.split("=", 1)[1].strip()
    return None


if __name__ == "__main__":
    if platform.system() == "Windows":
        device_input = input("Enter drive letter (example: F): ")
    else:
        device_input = input("Enter device path (example: /dev/disk2s1): ")

    serial = get_drive_serial(device_input)
    print(f"Serial Number: {serial}")

def eject_drive(drive_letter):
    os_name = platform.system()
    drive_letter = drive_letter.replace("\\", "").replace(":", "").strip().upper()

    if os_name == "Windows":
        cmd = [
            "powershell",
            "-Command",
            f"(New-Object -comObject Shell.Application).Namespace(17).ParseName('{drive_letter}:').InvokeVerb('Eject')"
        ]
        subprocess.run(cmd, capture_output=True, text=True)
        return True
    else:
        # Mac and Linux eject commands come later once we can test on those OS
        return False