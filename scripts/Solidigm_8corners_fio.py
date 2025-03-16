#!/usr/bin/env python3

import os
import logging
import subprocess
import csv
import re
import json

# 從其他模組 import 相關功能
from utils.file_utils import find_result_file_name  # 取得測試結果 CSV 檔名
from analysis.result_parser import parse_fio_output, write_to_csv  # 解析 FIO 輸出 & 寫入 CSV
from devices.device_utils import get_drives  # 取得可用的儲存裝置

# 🔹 設定 Device 對應的 Product Family
product_families = {
    "1": "D3_family_test_cases.json",
    "2": "D5_family_test_cases.json",
    "3": "D7_family_test_cases.json"
}

def select_product_family():
    """
    讓使用者選擇 Product Family，並返回測試案例的 JSON 設定。
    """
    test_config = None
    selected_file = None

    while True:
        print("\n📂 Select a Product Family:")
        for index, name in product_families.items():
            print(f"{index}. {name}")

        choice = input("Enter the index of the Product Family: ").strip()

        if choice in product_families:
            selected_file = os.path.join(os.getcwd(), "test_cases", product_families[choice])
            print(f"🔍 Checking file: {selected_file}")

            if os.path.exists(selected_file):
                try:
                    with open(selected_file, "r") as f:
                        test_config = json.load(f)  # ✅ 存成變數返回
                    print(f"✅ Loaded test config from {selected_file}")
                    break
                except Exception as e:
                    print(f"❌ Error loading {selected_file}: {e}")
            else:
                print(f"❌ File not found: {selected_file}")
        else:
            print("❌ Invalid choice. Please select again.")

    # 🔹 **選擇 SSD 型號**
    print("\n📌 請選擇 SSD 型號（來自選擇的 JSON 檔案）:")
    ssd_models = [model for model in test_config.keys() if not model.startswith("_")]  # ✅ 過濾掉 _comments 之類的 key

    for idx, model in enumerate(ssd_models, 1):
        print(f"[{idx}] {model}")

    try:
        model_choice = int(input("輸入對應的型號編號: ").strip()) - 1
        if model_choice < 0 or model_choice >= len(ssd_models):
            raise ValueError("❌ 無效選擇")

        selected_model = ssd_models[model_choice]
        print(f"✅ 選擇的 SSD 型號: {selected_model}")

    except ValueError as e:
        print(f"❌ 錯誤: {e}")
        return None, None  # 選擇錯誤則返回 None

    return test_config[selected_model], selected_model  # ✅ 回傳測試案例 & SSD 型號



#FIO 測試
# 執行 FIO 測試（封裝單個裝置的所有測試）
def run_device_tests(device, tests, result_folder, runtime, market_name, form_factor, test_config, task_set=None):
    try:
        # **確保 tests 是 list**
        if not isinstance(tests, list):
            raise ValueError(f"Invalid tests format: {tests}")  # 🚀 這段錯誤應該不會再發生

        for test in tests:
            run_fio_test(
                result_folder=result_folder,
                device=device,
                test_name=test["name"],
                rw=test["rw"],
                bs=test["bs"],
                iodepth=test["iodepth"],
                numjobs=test["numjobs"],
                runtime=runtime,
                market_name=market_name,
                form_factor=form_factor,
                test_config=test_config,  # ✅ 傳入 test_config
                precondition=test.get("precondition", False),
                rwmixread=test.get("rwmixread")
            )

    except Exception as e:
        logging.error(f"❌ Error during tests for device {device}: {e}")
        raise


  
# **檢查 NVMe 總寫入量**
def check_nvme_write(device, result_folder, test_name):
    """
    檢查 NVMe SSD 的 Data Units Written 並記錄到 log 檔案 & 獨立 nvme_write_log.txt
    """
    cmd = f"nvme smart-log /dev/{device} | grep 'Data Units Written'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    # 設定 log 檔案路徑
    nvme_log_file = os.path.join(result_folder, "nvme_write_log.txt")

    with open(nvme_log_file, "a") as log_file:
        if result.returncode == 0:
            # **修正這行，使用正則表達式來擷取數字**
            match = re.search(r"Data Units Written:\s+([\d,]+)", result.stdout)
            if match:
                written_units = int(match.group(1).replace(",", ""))  # 去除千分位逗號
                total_written_gb = written_units * 512 / 1024  # 換算成 GB

                # 記錄到 `fio_tests.log`
                logging.info(f"Preconditioning [{test_name}] - NVMe {device} Total Data Written: {total_written_gb:.2f} GB")

                # 記錄到 `nvme_write_log.txt`
                log_file.write(f"Preconditioning [{test_name}] - NVMe {device} Total Data Written: {total_written_gb:.2f} GB\n")
            else:
                logging.error(f"❌ Failed to extract Data Units Written for {device}: {result.stdout.strip()}")
                log_file.write(f"❌ Failed to extract Data Units Written for {device}: {result.stdout.strip()}\n")
        else:
            logging.error(f"❌ Error running smart-log for {device}")
            log_file.write(f"❌ Error running smart-log for {device}\n")



# FIO 測試  
# 讀取 JSON 測試設定

def run_fio_test(result_folder, device, test_name, rw, bs, iodepth, numjobs, runtime, market_name, form_factor, test_config, precondition=False, rwmixread=None):
    """
    根據 JSON 設定執行 FIO 測試，包含 preconditioning，並自動將結果寫入 CSV。
    """
    fio_result_file = os.path.join(result_folder, f"fio_{test_name}_{device}.txt")
    csv_filename = os.path.join(result_folder, f"{market_name}_fio_summary_results.csv")  # ✅ 確保結果寫入 CSV

    try:
        # **讀取 JSON 設定**
        precondition_settings = test_config.get("precondition", {}).get(rw, {})

        if precondition and precondition_settings:
            logging.info(f"Running preconditioning for {test_name} on {device}...")

            # **清除 LBA 空間**
            subprocess.run(f"blkdiscard /dev/{device}", shell=True, check=True)
            logging.info(f"Discarded all blocks on {device} before preconditioning.")

            # **組裝 preconditioning 指令**
            precondition_command = (
                f"fio --name=Preconditioning --filename=/dev/{device} --ioengine=libaio --direct=1 "
                f"--bs={precondition_settings['bs']} --rw={precondition_settings['rw']} "
                f"--iodepth={precondition_settings['iodepth']} --numjobs={precondition_settings['numjobs']} "
                f"--randrepeat=0 --norandommap --group_reporting "
                f"--verify=meta --verify_pattern=0xdeadbeef"
            )

            # **根據 mode 決定 runtime 或 loops**
            if precondition_settings.get("mode") == "runtime":
                precondition_command += f" --runtime={precondition_settings['value']} --time_based"
            elif precondition_settings.get("mode") == "loop":
                precondition_command += f" --loops={precondition_settings['value']}"

            # **如果需要填滿 SSD**
            if precondition_settings.get("fill_device"):
                precondition_command += " --size=100% --fill_device=1"

            # **NUMA 優化**
            if "cpus_allowed" in precondition_settings:
                precondition_command += f" --cpus_allowed={precondition_settings['cpus_allowed']}"

            # **執行 preconditioning**
            subprocess.run(precondition_command, shell=True, check=True)
            logging.info(f"✅ Preconditioning completed for {device}")

        # **正式 FIO 測試**
        logging.info(f"Running FIO test: {test_name} on {device}...")

        fio_command = (
            f"fio --name={test_name} --filename=/dev/{device} --rw={rw} --bs={bs} "
            f"--iodepth={iodepth} --numjobs={numjobs} --ioengine=libaio --runtime={runtime} "
            f"--direct=1 --group_reporting --norandommap --log_hist_msec=1000 --cpus_allowed_policy=split"
        )

        # **randrw 測試加入 rwmixread**
        if rw == "randrw" and rwmixread is not None:
            fio_command += f" --rwmixread={rwmixread}"

        # **執行測試**
        result = subprocess.run(fio_command, shell=True, capture_output=True, text=True)
        logging.info(f"✅ FIO test {test_name} completed for {device}")

        # **解析 FIO 結果並存入 CSV**
        if result.returncode == 0:
            total_bw, total_iops, test_runtime = parse_fio_output(result.stdout)
            write_to_csv(csv_filename, [
                device, test_name, total_bw, total_iops, iodepth, numjobs, "libaio", test_runtime
            ])
            logging.info(f"✅ FIO result saved to {csv_filename}")
        else:
            logging.error(f"❌ FIO test {test_name} failed on {device}: {result.stderr}")

    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Error during {test_name} on {device}: {e}")
        

  
#FIO 測試  
def start():
    # print cpu info
    os.system('lscpu')
    # Get all test drives
    all_drives = get_drives()
    # for spec_id in spec_list:
       # drive_list = [x.strip() for x in (test_config['%s'% spec_id]).split('-') if x.strip()]
       # for drive in drive_list:
           # all_drives.append(drive)
            
    # Get distribution of test drives
    cpu_0_drives = []
    cpu_1_drives = []
    for drive in all_drives:
        print (drive)
        drive_readlink = os.popen('readlink -e /sys/class/nvme/%s' % drive[0:-2]).read()
        bus_id = [x.strip() for x in drive_readlink.split('/')][-3]
        drive_numa = os.popen('lspci -vvv -s %s |grep -i numa'% bus_id).read()
        if 'node: 0' in drive_numa:
            cpu_0_drives.append(drive)
        else:
            cpu_1_drives.append(drive)
            
    print('CPU 0 : Drives :%s\nCPU 1 : Drives:%s' % (cpu_0_drives, cpu_1_drives))
    # Save cpu code for drive
    task_set = {}
    #Minimum allocation value
    if len(cpu_0_drives) > len(cpu_1_drives):
        minimum_drives = len(cpu_0_drives)
    else:
        minimum_drives = len(cpu_1_drives)
    
    # Get cpu total code
    cpu0_code_tatol = os.popen('''lscpu |grep "NUMA node0" |grep CPU|awk -F ":" '{print $NF}' ''').read().strip()
    cpu1_code_tatol = os.popen('''lscpu |grep "NUMA node1" |grep CPU|awk -F ":" '{print $NF}' ''').read().strip()
    cpu0_code_list = [x.strip() for x in cpu0_code_tatol.split(',')]
    cpu1_code_list = [x.strip() for x in cpu1_code_tatol.split(',')]
    print(cpu0_code_list, cpu1_code_list)
    
    # check overclocking
    if len(cpu0_code_list) > 1:
        # get drive use code
        if len(cpu_0_drives) % 2 == 1:
            drive_use_code = (int([x.strip() for x in cpu0_code_list[0].split('-')][1]) - 3) // (minimum_drives // 2 + 1)
        else:
            drive_use_code = (int([x.strip() for x in cpu0_code_list[0].split('-')][1]) - 3) // (minimum_drives // 2)
    
        # code start
        cpu0_dominant_frequency_code_use_start = int([x.strip() for x in cpu0_code_list[0].split('-')][0]) + 4
        cpu0_overclocking_code_use_start = int([x.strip() for x in cpu0_code_list[1].split('-')][0]) + 4
        cpu1_dominant_frequency_code_use_start = int([x.strip() for x in cpu1_code_list[0].split('-')][0]) + 4
        cpu1_overclocking_code_use_start = int([x.strip() for x in cpu1_code_list[1].split('-')][0]) + 4

        for index, drive in enumerate(cpu_0_drives):
            if index < ((len(cpu_0_drives) + 1) // 2):
                command = 'taskset -c %s-%s'% (cpu0_dominant_frequency_code_use_start, cpu0_dominant_frequency_code_use_start + drive_use_code - 1)
                task_set.update({drive: command})
                cpu0_dominant_frequency_code_use_start = cpu0_dominant_frequency_code_use_start + int(drive_use_code)
            else:
                command = 'taskset -c %s-%s'% (cpu0_overclocking_code_use_start, cpu0_overclocking_code_use_start + drive_use_code - 1)
                task_set.update({drive: command})
                cpu0_overclocking_code_use_start = cpu0_overclocking_code_use_start + int(drive_use_code)
                
        for index, drive in enumerate(cpu_1_drives):
            if index < ((len(cpu_1_drives) + 1) // 2):
                command = 'taskset -c %s-%s'% (cpu1_dominant_frequency_code_use_start, cpu1_dominant_frequency_code_use_start + drive_use_code - 1)
                task_set.update({drive: command})
                cpu1_dominant_frequency_code_use_start = cpu1_dominant_frequency_code_use_start + int(drive_use_code)
            else:
                command = 'taskset -c %s-%s'% (cpu1_overclocking_code_use_start, cpu1_overclocking_code_use_start + drive_use_code - 1)
                task_set.update({drive: command})
                cpu1_overclocking_code_use_start = cpu1_overclocking_code_use_start + int(drive_use_code)
         
    else:
        if len(cpu_0_drives) % 2 == 1:
            drive_use_code = (int([x.strip() for x in cpu0_code_list[0].split('-')][1]) - 3) // (minimum_drives)
        else:
            drive_use_code = (int([x.strip() for x in cpu0_code_list[0].split('-')][1]) - 3) // (minimum_drives)
        
        cpu0_dominant_frequency_code_use_start = int([x.strip() for x in cpu0_code_list[0].split('-')][0]) + 4
        cpu1_dominant_frequency_code_use_start = int([x.strip() for x in cpu1_code_list[0].split('-')][0]) + 4
        
        for index,drive in enumerate(cpu_0_drives):
            command = 'taskset -c %s-%s'% (cpu0_dominant_frequency_code_use_start, cpu0_dominant_frequency_code_use_start + drive_use_code - 1)
            task_set.update({drive: command})
            cpu0_dominant_frequency_code_use_start = cpu0_dominant_frequency_code_use_start + int(drive_use_code)

        
        for index,drive in enumerate(cpu_1_drives):
            command = 'taskset -c %s-%s'% (cpu1_dominant_frequency_code_use_start, cpu1_dominant_frequency_code_use_start + drive_use_code - 1)
            task_set.update({drive: command})
            cpu1_dominant_frequency_code_use_start = cpu1_dominant_frequency_code_use_start + int(drive_use_code)
    return task_set