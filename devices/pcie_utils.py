import re
import os
import subprocess
import logging

def get_pcie_bdf(devices):
    """取得 NVMe 裝置的 PCIe BDF"""
    device_bdf_map = {}
    for device in devices:
        try:
            bdf_path = f"/sys/block/{device}/device/address"
            if os.path.exists(bdf_path):
                with open(bdf_path, "r") as f:
                    bdf = f.read().strip()
                    device_bdf_map[device] = bdf
            else:
                print(f"⚠️ 找不到 {bdf_path}，請確認 {device} 是否為有效的 NVMe 裝置")
                device_bdf_map[device] = None

        except Exception as e:
            print(f"❌ 無法獲取 {device} 的 PCIe BDF，錯誤：{e}")
            device_bdf_map[device] = None

    return device_bdf_map


def setpci_for_devices(devices):
    """為 NVMe 設備設定 PCIe 參數"""
    for device in devices:
        try:
            bdf_path = f"/sys/block/{device}/device/address"
            with open(bdf_path, "r") as f:
                bdf = f.read().strip()

            if not bdf:
                logging.error(f"❌ 無法取得 {device} 的 BDF，跳過 PCIe 參數設定！")
                continue

            logging.info(f"✅ Found BDF {bdf} for {device}")

            # 設定 PCIe 參數
            cmd_power_limit = f"setpci -s {bdf} CAP_PM+10.b=00"
            subprocess.run(cmd_power_limit, shell=True, capture_output=True, text=True, check=True)
            logging.info(f"✅ Power limit adjusted for {device} ({bdf})")

        except FileNotFoundError:
            logging.error(f"❌ 找不到 {bdf_path}，無法獲取 {device} 的 BDF！")
        except subprocess.CalledProcessError as e:
            logging.error(f"❌ 無法為 {device} ({bdf}) 設定 PCIe 參數，錯誤：{e}")


def set_interrupt_Coalescing(devices, output_file="interrupt_coalescing.txt"):
    output_path = os.path.join(os.getcwd(), output_file)
    
    # 先詢問使用者是否要啟用 Interrupt Coalescing
    enable_ic = input("Do you want to enable Interrupt Coalescing? (y/n): ").strip().lower()
    if enable_ic != 'y':
        print("Skipping Interrupt Coalescing configuration.")
        return
    
    # 根據系統內的 NVMe 數量建議 threshold 值
    num_nvme = len(devices)
    if num_nvme == 8:
        recommended_threshold = 3
    elif num_nvme in [12, 16]:
        recommended_threshold = 5  # 或者 9，讓使用者選擇
    else:
        recommended_threshold = 9  # 超過這個數值可能不會帶來效益
    
    print(f"System detected {num_nvme} NVMe devices.")
    print(f"Recommended threshold value: {recommended_threshold}")
    
    # 讓使用者選擇 threshold 值
    threshold = input(f"Enter threshold value (default={recommended_threshold}): ").strip()
    if not threshold.isdigit():
        threshold = recommended_threshold  # 使用推薦值
    else:
        threshold = int(threshold)
    
    with open(output_path, "a") as log_file:
        for device in devices:
            try:
                # 去除設備名稱中的多餘空格或不可見字符
                device = device.strip()
                
                # 使用正則表達式提取基礎設備名稱（僅保留 nvmeX）
                match = re.match(r"^(nvme\d+)", device)
                if match:
                    device_base = match.group(1)
                else:
                    logging.error(f"Failed to extract base device name from: {device}")
                    continue
                
                # 設定 Interrupt Coalescing 參數
                set_feature_Interrupt_Coalescing = (
                    f"nvme set-feature /dev/{device_base} -feature-id 0x08 --value 0x01{threshold:02X}"
                )
                
                # 取得設定值來確認是否正確
                get_feature_Interrupt_Coalescing = (
                    f"nvme get-feature /dev/{device_base} -feature-id 0x08"
                )
                
                logging.info(f"Setting interrupt coalescing for /dev/{device_base} with threshold={threshold}")
                subprocess.run(set_feature_Interrupt_Coalescing, shell=True, capture_output=True, text=True, check=True)
                result = subprocess.run(get_feature_Interrupt_Coalescing, shell=True, capture_output=True, text=True, check=True)
                
                final_setting = result.stdout.strip()
                
                # 記錄結果到日誌與檔案
                logging.info(f"Interrupt coalescing set successfully for /dev/{device_base}: {final_setting}")
                log_file.write(f"{device_base}: {final_setting}\n")
                print(f"{device_base} interrupt coalescing setting: {final_setting}")
                
            except subprocess.CalledProcessError as e:
                logging.error(f"Failed to set interrupt coalescing for /dev/{device_base}: {e}")
                log_file.write(f"{device_base}: Failed to set interrupt coalescing\n")

#裝置設定
# 這一段是有問題的  因為他邏輯是要抓bdf 但是下面自己的都能抓 所以或許可以刪掉 3/23
def get_pcie_bdf(devices):
    """
    取得 NVMe 裝置的 PCIe BDF（Bus-Device-Function）並回傳字典
    :param devices: NVMe 裝置名稱清單，例如 ["nvme0n1", "nvme1n1"]
    :return: 字典 { "nvme0n1": "0000:02:00.0", "nvme1n1": "0000:03:00.0" }
    """
    device_bdf_map = {}

    for device in devices:
        try:
            # 使用正確的路徑來獲取 BDF
            bdf_path = f"/sys/block/{device}/device/address"
            if os.path.exists(bdf_path):
                with open(bdf_path, "r") as f:
                    bdf = f.read().strip()
                    device_bdf_map[device] = bdf
            else:
                print(f"⚠️ 找不到 {bdf_path}，請確認 {device} 是否為有效的 NVMe 裝置")
                device_bdf_map[device] = None

        except Exception as e:
            print(f"❌ 無法獲取 {device} 的 PCIe BDF，錯誤：{e}")
            device_bdf_map[device] = None

    return device_bdf_map



#裝置設定
# **設定 PCIe 參數**
def setpci_for_devices(devices):
    """
    為指定的 NVMe 設備調整 PCIe 參數，例如提高功耗限制或啟用 ASPM。
    :param devices: NVMe 裝置名稱清單，例如 ["nvme0n1", "nvme1n1"]
    設定DUT device to D0 stage
    """
    for device in devices:
        try:
            # 先取得 BDF
            bdf_path = f"/sys/block/{device}/device/address"
            with open(bdf_path, "r") as f:
                bdf = f.read().strip()  # 讀取 BDF，例如 '0000:02:00.0'

            if not bdf:
                logging.error(f"❌ 無法取得 {device} 的 BDF，跳過 PCIe 參數設定！")
                continue

            logging.info(f"✅ Found BDF {bdf} for {device}")

            # 修改 PCIe 配置以提高功耗限制
            cmd_power_limit = f"setpci -s {bdf} CAP_PM+10.b=00"
            subprocess.run(cmd_power_limit, shell=True, capture_output=True, text=True, check=True)
            logging.info(f"✅ Power limit adjusted for {device} ({bdf})")

            # 啟用 ASPM（Active State Power Management）
            cmd_aspm_enable = f"setpci -s {bdf} CAP_PM+F.b=02"
            subprocess.run(cmd_aspm_enable, shell=True, capture_output=True, text=True, check=True)
            logging.info(f"✅ ASPM enabled for {device} ({bdf})")

        except FileNotFoundError:
            logging.error(f"❌ 找不到 {bdf_path}，無法獲取 {device} 的 BDF！")
        except subprocess.CalledProcessError as e:
            logging.error(f"❌ 無法為 {device} ({bdf}) 設定 PCIe 參數，錯誤：{e}")

            
#裝置設定
def save_before_lspci_output(devices, output_dir="./lspci_outputs"):
    """
    儲存 lspci -vvvs <BDF> 的輸出結果
    :param devices: NVMe 裝置名稱清單，例如 ["nvme0n1", "nvme1n1"]
    """
    os.makedirs(output_dir, exist_ok=True)

    for device in devices:
        try:
            # 使用正確的路徑來獲取 BDF
            bdf_path = f"/sys/block/{device}/device/address"
            if os.path.exists(bdf_path):
                with open(bdf_path, "r") as f:
                    bdf = f.read().strip()
            else:
                logging.error(f"⚠️ 找不到 {bdf_path}，請確認 {device} 是否為有效的 NVMe 裝置")
                continue

            if not bdf:
                logging.error(f"❌ 無法取得 {device} 的 BDF，跳過 lspci 設定！")
                continue

            logging.info(f"✅ Found BDF {bdf} for {device}")

            # 執行 lspci -vvvs <BDF>
            cmd = f"lspci -vvvs {bdf}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)

            # 儲存輸出到檔案
            output_file = os.path.join(output_dir, f"{device}_before.txt")
            with open(output_file, "w") as f:
                f.write(result.stdout)

            logging.info(f"✅ 已儲存 {device} ({bdf}) 的 lspci 結果到 {output_file}")

        except FileNotFoundError:
            logging.error(f"❌ 找不到 {bdf_path}，無法獲取 {device} 的 BDF！")
        except subprocess.CalledProcessError as e:
            logging.error(f"❌ 無法執行 lspci，錯誤：{e}")

         
#裝置設定
def save_after_lspci_output(device_bdf_map, output_dir="./lspci_outputs"):
    """
    對每個設備執行 lspci -vvvs <BDF>，並將輸出存成 .txt 檔案。

    :param device_bdf_map: 字典，鍵為設備名稱（如 nvme2n1），值為對應的 BDF 值（如 0000:02:00.0）
    :param output_dir: 儲存 lspci 輸出檔案的目錄，預設為 "./lspci_outputs"
    """
    # 確保輸出目錄存在
    os.makedirs(output_dir, exist_ok=True)

    for device, bdf in device_bdf_map.items():
        # if bdf is None or not validate_bdf_format(bdf):
        #     logging.error(f"Skipping device {device} due to invalid or missing BDF: {bdf}")
        #     continue

        try:
            # 構建 lspci 命令
            cmd = f"lspci -vvvs {bdf}"

            # 執行 lspci 命令
            logging.info(f"Executing: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)

            # 將輸出寫入檔案
            output_file = os.path.join(output_dir, f"{device}_after.txt")
            with open(output_file, "w") as f:
                f.write(result.stdout)

            logging.info(f"Saved lspci output for {device} ({bdf}) to {output_file}")

        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to execute lspci for device {device} ({bdf}): {e}")
        except Exception as e:
            logging.error(f"Unexpected error for device {device} ({bdf}): {e}")



#裝置設定  
# 設定 Interrupt Coalescing (適用於 Intel 平台)

def set_interrupt_Coalescing(devices, output_file="interrupt_coalescing.txt"):
    output_path = os.path.join(os.getcwd(), output_file)
    
    # 先詢問使用者是否要啟用 Interrupt Coalescing
    enable_ic = input("Do you want to enable Interrupt Coalescing? (y/n): ").strip().lower()
    if enable_ic != 'y':
        print("Skipping Interrupt Coalescing configuration.")
        return
    
    # 根據系統內的 NVMe 數量建議 threshold 值
    num_nvme = len(devices)
    if num_nvme == 8:
        recommended_threshold = 3
    elif num_nvme in [12, 16]:
        recommended_threshold = 5  # 或者 9，讓使用者選擇
    else:
        recommended_threshold = 9  # 超過這個數值可能不會帶來效益
    
    print(f"System detected {num_nvme} NVMe devices.")
    print(f"Recommended threshold value: {recommended_threshold}")
    
    # 讓使用者選擇 threshold 值
    threshold = input(f"Enter threshold value (default={recommended_threshold}): ").strip()
    if not threshold.isdigit():
        threshold = recommended_threshold  # 使用推薦值
    else:
        threshold = int(threshold)
    
    with open(output_path, "a") as log_file:
        for device in devices:
            try:
                # 去除設備名稱中的多餘空格或不可見字符
                device = device.strip()
                
                # 使用正則表達式提取基礎設備名稱（僅保留 nvmeX）
                match = re.match(r"^(nvme\d+)", device)
                if match:
                    device_base = match.group(1)
                else:
                    logging.error(f"Failed to extract base device name from: {device}")
                    continue
                
                # 設定 Interrupt Coalescing 參數
                set_feature_Interrupt_Coalescing = (
                    f"nvme set-feature /dev/{device_base} -feature-id 0x08 --value 0x01{threshold:02X}"
                )
                
                # 取得設定值來確認是否正確
                get_feature_Interrupt_Coalescing = (
                    f"nvme get-feature /dev/{device_base} -feature-id 0x08"
                )
                
                logging.info(f"Setting interrupt coalescing for /dev/{device_base} with threshold={threshold}")
                subprocess.run(set_feature_Interrupt_Coalescing, shell=True, capture_output=True, text=True, check=True)
                result = subprocess.run(get_feature_Interrupt_Coalescing, shell=True, capture_output=True, text=True, check=True)
                
                final_setting = result.stdout.strip()
                
                # 記錄結果到日誌與檔案
                logging.info(f"Interrupt coalescing set successfully for /dev/{device_base}: {final_setting}")
                log_file.write(f"{device_base}: {final_setting}\n")
                print(f"{device_base} interrupt coalescing setting: {final_setting}")
                
            except subprocess.CalledProcessError as e:
                logging.error(f"Failed to set interrupt coalescing for /dev/{device_base}: {e}")
                log_file.write(f"{device_base}: Failed to set interrupt coalescing\n")


