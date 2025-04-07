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
                    return None, None  # 🚨 讀取失敗則返回 None
            else:
                print(f"❌ File not found: {selected_file}")
                return None, None  # 🚨 找不到檔案則返回 None
        else:
            print("❌ Invalid choice. Please select again.")

    if not test_config:  
        print("❌ Failed to load test configuration.")
        return None, None  # 🚨 避免後續 `NoneType` 錯誤

    # 🔹 **選擇 SSD 型號**
    print("\n📌 請選擇 SSD 型號（來自選擇的 JSON 檔案）:")
    ssd_models = [model for model in test_config.keys() if not model.startswith("_")]  # ✅ 過濾掉 _comments 之類的 key

    if not ssd_models:
        print("❌ No valid SSD models found in the test configuration.")
        return None, None  # 🚨 JSON 沒有 SSD 型號

    for idx, model in enumerate(ssd_models, 1):
        print(f"[{idx}] {model}")

    try:
        model_choice = int(input("輸入對應的型號編號: ").strip()) - 1
        if model_choice < 0 or model_choice >= len(ssd_models):
            raise ValueError("❌ 無效選擇")

        selected_model = ssd_models[model_choice]
        print(f"✅ 選擇的 SSD 型號: {selected_model}")

        # 🚨 **確保 test_config[selected_model] 是字典**
        model_config = test_config.get(selected_model, None)
        if not isinstance(model_config, dict):
            print(f"❌ Invalid test format for {selected_model}. Expected a dictionary, got {type(model_config)}")
            return None, None

    except ValueError as e:
        print(f"❌ 錯誤: {e}")
        return None, None  # 選擇錯誤則返回 None

    return model_config, selected_model  # ✅ 回傳測試案例 & SSD 型號


#FIO 測試
# 執行 FIO 測試（封裝單個裝置的所有測試）
def run_device_tests(device, tests, result_folder, runtime, market_name, form_factor, test_config, task_set=None, log_bandwidth=True):
    try:
        if not isinstance(tests, list):
            raise ValueError(f"Invalid tests format: {tests}")

        logging.info(f"\n🔧 Begin FIO test for device: {device}")
        logging.info(f"📝 Executing test sequence for {device}:")
        for i, test in enumerate(tests):
            logging.info(f"  {i+1:02d}. {test.get('name', 'Unnamed')} | RW: {test.get('rw')} | BS: {test.get('bs')}")

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
                test_config=test_config,
                precondition=test.get("precondition", False),
                rwmixread=test.get("rwmixread", None),
                log_bandwidth=log_bandwidth
            )

    except Exception as e:
        logging.error(f"❌ Error during tests for device {device}: {e}")
        raise


# **檢查 NVMe 總寫入量**
import re
import subprocess
import os
import logging

def check_nvme_write(device, result_folder, test_name):
    """
    檢查 NVMe SSD 的 Data Units Written 並記錄到 log 檔案 & 獨立 nvme_write_log.txt
    """
    is_nvme = device.startswith("nvme")  # ✅ 更準確判斷是否為 NVMe

    if not is_nvme:
        logging.info(f"Skipping smart-log for {device} (not NVMe).")
        return

    cmd = f"nvme smart-log /dev/{device} | grep 'Data Units Written'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    nvme_log_file = os.path.join(result_folder, "nvme_write_log.txt")

    with open(nvme_log_file, "a") as log_file:
        if result.returncode == 0:
            match = re.search(r"Data Units Written\s*:\s*([\d,]+)", result.stdout)
            if match:
                written_units = int(match.group(1).replace(",", ""))
                total_written_gb = written_units * 512 / 1024
                logging.info(f"Preconditioning [{test_name}] - NVMe {device} Total Data Written: {total_written_gb:.2f} GB")
                log_file.write(f"Preconditioning [{test_name}] - NVMe {device} Total Data Written: {total_written_gb:.2f} GB\n")
            else:
                logging.error(f"❌ Failed to extract Data Units Written for {device}. Raw output:\n{result.stdout}")
                log_file.write(f"❌ Failed to extract Data Units Written for {device}. Raw output:\n{result.stdout}\n")
        else:
            logging.error(f"❌ Error running smart-log for {device}")
            log_file.write(f"❌ Error running smart-log for {device}\n")


# FIO 測試  
# 讀取 JSON 測試設定

def run_fio_test(result_folder, device, test_name, rw, bs, iodepth, numjobs, runtime, 
                 market_name, form_factor, test_config, precondition=False, rwmixread=None, log_bandwidth=True):
    """
    根據 JSON 設定執行 FIO 測試，包含 preconditioning，並自動將結果寫入 CSV。
    """
    fio_result_file = os.path.join(result_folder, f"fio_{test_name}_{device}.txt")
    csv_filename = os.path.join(result_folder, f"{market_name}_fio_summary_results.csv")

    is_nvme = device.startswith("nvme")

    try:
        if test_config is None:
            logging.error(f"❌ test_config is None in run_fio_test for {device}. Skipping test.")
            return

        test_case_info = next((t for t in test_config.get("test_cases", []) if t.get("name") == test_name), {})
        ioengine = test_case_info.get("ioengine", "libaio")

        precondition_settings = test_config.get("precondition", {}).get(rw, {})
        precondition_ioengine = precondition_settings.get("ioengine", "libaio")

        detailed_log_path = os.path.join(result_folder, f"{device}_precondition_log", test_name)
        os.makedirs(detailed_log_path, exist_ok=True)
        pre_log_file = os.path.join(detailed_log_path, "precondition_bw.1.log")
        test_log_file = os.path.join(detailed_log_path, "test_bw.1.log")

        # ---------- Preconditioning ----------
        if precondition and precondition_settings:
            logging.info(f"⚙️ Running preconditioning for {test_name} on {device}...")

            if is_nvme:
                try:
                    subprocess.run(f"blkdiscard /dev/{device}", shell=True, check=True)
                    logging.info(f"✅ Discarded all blocks on {device} before preconditioning.")
                except subprocess.CalledProcessError as e:
                    logging.warning(f"⚠️ blkdiscard failed on {device}, trying 'nvme format'...")
                    try:
                        subprocess.run(f"nvme format /dev/{device} -s 1 -n 1", shell=True, check=True)
                        logging.info(f"✅ Fallback to 'nvme format' succeeded on {device}.")
                    except subprocess.CalledProcessError as e2:
                        logging.error(f"❌ nvme format also failed on {device}: {e2}")
                        precondition = False
            else:
                logging.info(f"Skipping blkdiscard on {device} (not NVMe).")

            if precondition:
                precondition_command = (
                    f"fio --name=Preconditioning --filename=/dev/{device} --ioengine={precondition_ioengine} --direct=1 "
                    f"--bs={precondition_settings['bs']} --rw={precondition_settings['rw']} "
                    f"--iodepth={precondition_settings['iodepth']} --numjobs={precondition_settings['numjobs']} "
                    f"--randrepeat=0 --norandommap --group_reporting "
                    f"--write_bw_log={os.path.splitext(pre_log_file)[0]}"
                )

                if log_bandwidth:
                    precondition_command += " --log_avg_msec=1000"

                if precondition_settings.get("mode") == "runtime":
                    precondition_command += f" --runtime={precondition_settings['value']} --time_based"
                elif precondition_settings.get("mode") == "loop":
                    precondition_command += f" --loops={precondition_settings['value']}"

                if precondition_settings.get("fill_device"):
                    precondition_command += " --size=100% --fill_device=1"

                if "cpus_allowed" in precondition_settings:
                    precondition_command += f" --cpus_allowed={precondition_settings['cpus_allowed']}"

                subprocess.run(precondition_command, shell=True, check=True)
                logging.info(f"✅ Preconditioning completed for {device}")

                if is_nvme:
                    check_nvme_write(device, result_folder, test_name)

        # ---------- 正式 FIO 測試 ----------
        logging.info(f"🚀 Running FIO test: {test_name} on {device}...")

        fio_command = (
            f"fio --name={test_name} --filename=/dev/{device} --rw={rw} --bs={bs} "
            f"--iodepth={iodepth} --numjobs={numjobs} --ioengine={ioengine} --runtime={runtime} "
            f"--direct=1 --group_reporting --norandommap --log_hist_msec=1000 --cpus_allowed_policy=split "
            f"--write_bw_log={os.path.splitext(test_log_file)[0]}"
        )

        if log_bandwidth:
            fio_command += " --log_avg_msec=1000"

        if rw == "randrw" and rwmixread is not None:
            fio_command += f" --rwmixread={rwmixread}"

        logging.info(f"FIO command: {fio_command}")

        result = subprocess.run(fio_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            logging.info(f"✅ FIO test {test_name} completed successfully on {device}")

            total_bw, total_iops, test_runtime = parse_fio_output(result.stdout)
            write_to_csv(csv_filename, [
                device, test_name, total_bw, total_iops, iodepth, numjobs, ioengine, test_runtime
            ])
            logging.info(f"✅ FIO result saved to {csv_filename}")
        else:
            logging.error(f"❌ FIO test {test_name} failed on {device}:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")

    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Error during {test_name} on {device}: {e}")
