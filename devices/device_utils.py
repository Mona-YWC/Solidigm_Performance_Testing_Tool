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
# **列出所有 NVMe & SATA裝置（排除 Boot Drive）**
def list_all_devices():
    """列出所有 NVMe 和 SATA 裝置，並排除 Boot Drive，同時顯示型號"""
    try:
        # 🔍 取得所有儲存裝置資訊
        result = subprocess.run(
            "lsblk -d -n -o NAME,SIZE,TYPE,MOUNTPOINT",
            shell=True, capture_output=True, text=True, check=True
        )
        device_lines = result.stdout.strip().split("\n")
        if not device_lines:
            print("⚠️ No storage devices found! Exiting.")
            sys.exit(1)

        all_devices = []
        display_idx = 0
        for line in device_lines:
            parts = line.split()
            name = parts[0]
            size = parts[1] if len(parts) > 1 else "Unknown"
            mountpoint = parts[3] if len(parts) > 3 else ""

            # ❌ 避免列出系統磁碟
            if mountpoint in ["/", "/boot", "/home", "[SWAP]"]:
                print(f"⛔ Skipping {name} (mounted as {mountpoint}) - Boot/System Drive")
                continue

            # 取得裝置型號
            model = "Unknown"
            model_path = f"/sys/block/{name}/device/model"
            if os.path.exists(model_path):
                try:
                    with open(model_path, "r") as f:
                        model = f.read().strip()
                except Exception:
                    pass
            elif name.startswith("nvme"):
                try:
                    nvme_res = subprocess.run(
                        f"nvme id-ctrl /dev/{name} | grep 'mn'",
                        shell=True, capture_output=True, text=True
                    )
                    if nvme_res.returncode == 0:
                        model_line = nvme_res.stdout.strip()
                        model = model_line.split(":")[-1].strip()
                except Exception:
                    pass

            all_devices.append({"name": name, "size": size})
            print(f"[{display_idx}] {name} | SIZE: {size} | MODEL: {model}")
            display_idx += 1

        if not all_devices:
            print("❌ No valid devices found (Boot Drive excluded). Exiting.")
            sys.exit(1)

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
# **裝置設定**
def run_security_erase(selected_devices):
    """執行安全清除（根據裝置類型區分 NVMe 和 SATA）"""
    for device in selected_devices:
        device_path = f"/dev/{device}"

        is_nvme = device.startswith("nvme")

        if is_nvme:
            logging.info(f"🔍 Checking device {device}: NVMe SSD")
            try:
                logging.info(f"🔹 Running blkdiscard on {device}...")
                subprocess.run(f"blkdiscard {device_path}", shell=True, check=True)
                logging.info(f"✅ blkdiscard completed on {device}.")
            except subprocess.CalledProcessError:
                logging.error(f"❌ blkdiscard failed for {device}, trying nvme format...")
                try:
                    subprocess.run(f"nvme format {device_path} -s 1 -n 1", shell=True, check=True)
                    logging.info(f"✅ nvme format completed on {device}.")
                except subprocess.CalledProcessError as e:
                    logging.error(f"❌ nvme format also failed for {device}: {e}")

        else:
            try:
                result = subprocess.run(f"lsblk -no ROTA {device_path}", shell=True, capture_output=True, text=True)
                is_rotational = result.stdout.strip()

                if is_rotational == "0":
                    logging.info(f"🔍 Checking device {device}: SATA SSD")
                    try:
                        logging.info(f"🔹 Running hdparm secure erase on {device}...")
                        subprocess.run(f"hdparm --user-master u --security-set-pass NULL {device_path}", shell=True, check=True)
                        subprocess.run(f"hdparm --user-master u --security-erase NULL {device_path}", shell=True, check=True)
                        logging.info(f"✅ hdparm secure erase completed on {device}.")
                    except subprocess.CalledProcessError as e:
                        logging.error(f"❌ hdparm secure erase failed for {device}: {e}")
                else:
                    logging.warning(f"⚠️ Device {device} is an HDD, skipping secure erase.")

            except subprocess.CalledProcessError as e:
                logging.error(f"❌ 無法判斷裝置 {device} 類型: {e}")

#裝置設定
# **設定中斷合併**

def get_taskset_commands():
    os.system('lscpu')

    from devices.device_utils import get_drives  # 保留原本依賴
    all_drives = get_drives()

    cpu_0_drives = []
    cpu_1_drives = []
    device_numa_map = {}  # ✅ 新增記錄 NUMA node

    for drive in all_drives:
        print(drive)
        drive_readlink = os.popen('readlink -e /sys/class/nvme/%s' % drive[0:-2]).read()
        bus_id = [x.strip() for x in drive_readlink.split('/')][-3]
        drive_numa = os.popen('lspci -vvv -s %s |grep -i numa' % bus_id).read()
        if 'node: 0' in drive_numa:
            cpu_0_drives.append(drive)
            device_numa_map[drive] = 0
        else:
            cpu_1_drives.append(drive)
            device_numa_map[drive] = 1

    print('CPU 0 : Drives :%s\nCPU 1 : Drives:%s' % (cpu_0_drives, cpu_1_drives))

    task_set = {}
    minimum_drives = min(len(cpu_0_drives), len(cpu_1_drives))

    cpu0_code_tatol = os.popen('''lscpu |grep "NUMA node0" |grep CPU|awk -F ":" '{print $NF}' ''').read().strip()
    cpu1_code_tatol = os.popen('''lscpu |grep "NUMA node1" |grep CPU|awk -F ":" '{print $NF}' ''').read().strip()
    cpu0_code_list = [x.strip() for x in cpu0_code_tatol.split(',')]
    cpu1_code_list = [x.strip() for x in cpu1_code_tatol.split(',')]

    def allocate_taskset(cpu_code_list, drives, start_idx, is_overclocking):
        start = int(cpu_code_list[start_idx].split('-')[0]) + 4
        drive_use_code = (int(cpu_code_list[0].split('-')[1]) - 3) // (minimum_drives // 2 + 1) if len(drives) % 2 == 1 else (int(cpu_code_list[0].split('-')[1]) - 3) // (minimum_drives // 2)
        for index, drive in enumerate(drives):
            if index < ((len(drives) + 1) // 2 if is_overclocking else len(drives) // 2):
                end = start + drive_use_code - 1
                task_set[drive] = f'taskset -c {start}-{end}'
                start = start + drive_use_code

    if len(cpu0_code_list) > 1:
        allocate_taskset(cpu0_code_list, cpu_0_drives, 0, False)
        allocate_taskset(cpu0_code_list, cpu_0_drives, 1, True)
        allocate_taskset(cpu1_code_list, cpu_1_drives, 0, False)
        allocate_taskset(cpu1_code_list, cpu_1_drives, 1, True)
    else:
        drive_use_code = (int(cpu0_code_list[0].split('-')[1]) - 3) // minimum_drives
        start_0 = int(cpu0_code_list[0].split('-')[0]) + 4
        start_1 = int(cpu1_code_list[0].split('-')[0]) + 4

        for drive in cpu_0_drives:
            task_set[drive] = f'taskset -c {start_0}-{start_0 + drive_use_code - 1}'
            start_0 += drive_use_code

        for drive in cpu_1_drives:
            task_set[drive] = f'taskset -c {start_1}-{start_1 + drive_use_code - 1}'
            start_1 += drive_use_code

    return task_set, device_numa_map  # ✅ 一起回傳 NUMA map




