#!/usr/bin/env python3

import os
import logging
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback 
import time

# Import modules from different categories
from devices.device_utils import list_all_devices, select_storage_devices, run_security_erase
from devices.pcie_utils import get_pcie_bdf, setpci_for_devices, set_interrupt_Coalescing
from utils.logging_utils import setup_logging
from utils.file_utils import find_latest_result_folder
from devices.pcie_utils import save_before_lspci_output, save_after_lspci_output
from scripts.Solidigm_8corners_fio import start as fio_start, run_device_tests, select_product_family

# **主函式**
def main():
    start_time = time.time()  # 記錄開始時間
    base_path = "/root/Solidigm_Performance_Testing_Tool"

    # ✅ **改為由 `8corners_fio.py` 負責選擇 Product Family & 測試 JSON**
    tests, selected_model = select_product_family()
    if tests is None or selected_model is None:
        print("❌ 測試案例選擇失敗，退出程序。")
        sys.exit(1)

    # ✅ **解析 Form Factor**
    form_factor = selected_model.split("-")[-1]  # 假設型號格式為 "P1010-U2"，則提取 "U2"

    # ✅ **確保測試案例是 list**
    if not isinstance(tests.get("test_cases", []), list):
        logging.error(f"❌ Invalid test format for {selected_model}. Expected a list, got {type(tests)}")
        sys.exit(1)

    # ✅ **取出 test_cases 陣列**
    tests = tests["test_cases"]

    # **建立測試結果資料夾**
    latest_folder = find_latest_result_folder(base_path, selected_model, "TestResults")
    log_file = os.path.join(latest_folder, "fio_tests.log")
    setup_logging(log_file)

    # **列出可用 SATA & NVMe 裝置**
    all_devices = list_all_devices()

    # **讓使用者選擇測試裝置**
    selected_devices = select_storage_devices(all_devices)

    # **執行安全清除**
    run_security_erase(selected_devices)

    # **設定中斷合併**
    set_interrupt_Coalescing(selected_devices)

    # **獲取 NVMe PCIe BDF**
    device_bdf_map = get_pcie_bdf(selected_devices)

    # **執行 lspci 之前的狀態保存**
    save_before_lspci_output(device_bdf_map, f"{latest_folder}/lspci_outputs")

    # **設定 PCIe 參數**
    setpci_for_devices(device_bdf_map)

    # **輸入 FIO 測試的 Runtime**
    runtime = input("Enter the runtime for FIO tests (in seconds): ").strip()
    if not runtime.isdigit() or int(runtime) <= 0:
        print("❌ Invalid runtime. Please enter a positive integer.")
        sys.exit(1)
    runtime = int(runtime)

    # **如果選擇多個 SSD，則啟用 task_set**
    task_set = None
    if len(selected_devices) > 1:
        task_set = fio_start()
        cpu_core_binding_file = os.path.join(latest_folder, "CPU_Core_Binding.txt")
        with open(cpu_core_binding_file, "a") as log_file:
            log_file.write(f"Task Set: {task_set}\n")

    # **使用 ThreadPoolExecutor 執行測試**
    with ThreadPoolExecutor(max_workers=len(selected_devices)) as executor:
        futures = {
            executor.submit(run_device_tests, device, tests, latest_folder, runtime, selected_model, form_factor, task_set): device
            for device in selected_devices
        }

        # **等待所有裝置測試完成**
        for future in as_completed(futures):
            device = futures[future]
            try:
                future.result()
                logging.info(f"✅ Tests completed for device: {device}")
            except Exception as e:
                logging.error(f"❌ Error during tests for device {device}: {e}\n{traceback.format_exc()}")

    print("✅ All tests completed. Results saved in:", latest_folder)

    # **執行 lspci 之後的狀態保存**
    save_after_lspci_output(device_bdf_map, f"{latest_folder}/lspci_outputs")

    end_time = time.time()  # 記錄結束時間
    elapsed_time = end_time - start_time
    logging.info(f"⏳ 測試總執行時間: {elapsed_time:.2f} 秒")
    print(f"⏳ 測試總執行時間: {elapsed_time:.2f} 秒")

if __name__ == "__main__":
    main()
