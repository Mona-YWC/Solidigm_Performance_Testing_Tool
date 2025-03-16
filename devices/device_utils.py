import os
import subprocess
import logging
import re
import sys

      
#初始化
def get_drives():
    drive_list = []
    
    # 抓取所有的 disk 裝置（包含 NVMe 和 SATA）
    lsblk_list = os.popen("lsblk -d -n -o NAME,TYPE | awk '$2 == \"disk\"'").read()
    lines = [x.strip().split()[0] for x in lsblk_list.strip().split("\n") if x.strip()]
    
    for drive in lines:
        # 過濾掉 OS 使用的磁碟
        os_drive = os.popen(f'lsblk /dev/{drive}').read()
        if 'root' in os_drive or 'home' in os_drive:
            continue
        
        drive_list.append(drive)

    return list(set(drive_list))
        

#裝置設定
# **列出所有 NVMe & SATA裝置**
def list_all_devices():
    """列出所有 NVMe 和 SATA 裝置"""
    try:
        result = subprocess.run(
            "lsblk -d -n -o NAME,SIZE,TYPE | awk '$3 == \"disk\"'",
            shell=True, capture_output=True, text=True, check=True
        )
        device_lines = result.stdout.strip().split("\n")
        if not device_lines:
            print("⚠️ No storage devices found! Exiting.")
            sys.exit(1)

        all_devices = []
        for idx, line in enumerate(device_lines):
            parts = line.split()
            name = parts[0]  # 裝置名稱
            size = parts[1] if len(parts) > 1 else "Unknown"

            all_devices.append({"name": name, "size": size})
            print(f"[{idx}] {name} | SIZE: {size}")

        return all_devices

    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing lsblk: {e}")
        sys.exit(1)


#裝置設定
# **讓使用者手動選擇 NVMe & SATA 裝置**
def select_storage_devices(devices):
    print("\n🔍 Enter the indices of the devices to test (comma-separated, e.g., 0,2):")
    indices = input("Your selection: ").split(",")

    selected_devices = []
    try:
        for idx in indices:
            idx = int(idx.strip())
            if 0 <= idx < len(devices):
                selected_devices.append(devices[idx]["name"])
            else:
                print(f"⚠️ Index {idx} is out of range. Skipping.")

        if not selected_devices:
            print("❌ No valid devices selected. Exiting.")
            sys.exit(1)

        return selected_devices

    except ValueError:
        print("❌ Invalid input. Exiting.")
        sys.exit(1)


#裝置設定        
def run_security_erase(devices):
    for device in devices:
        try:
            security_command = f"nvme format /dev/{device} --ses=1"
            logging.info(f"Security erase start for /dev/{device}")
            security_erase_result = subprocess.run(security_command, shell=True, capture_output=True, text=True, check=True)
            logging.info(f"Security erase completed for /dev/{device}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Security erase failed for /dev/{device}: {e}")
