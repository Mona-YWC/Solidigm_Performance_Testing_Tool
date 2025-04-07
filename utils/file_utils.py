import os
import sys
import re
import json
import glob
from datetime import datetime

# ---------- 自動設定根目錄 ----------
# 將 base_folder 設成「本檔案所在位置的上一層」（即專案根目錄）
base_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
spec_folder = os.path.join(base_folder, "spec_reference")
family_mapping_file = os.path.join(spec_folder, "family_mapping.json")

# ---------- 尋找最新測試資料夾 ----------
def find_latest_test_folder(base_path=base_folder):
    """
    根據 SSD 型號找到最新的測試結果資料夾，或選擇建立新資料夾。
    :param base_path: 測試結果的根目錄
    :return: 最新的資料夾路徑，或者創建的新資料夾路徑
    """
    test_folders = [
        folder for folder in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, folder)) and
           re.match(r".+_TestResults_\d{8}_\d{6}$", folder)
    ]

    if not test_folders:
        print("❌ No valid test folders found.")
        return None

    test_folders = [f for f in test_folders if not f.endswith(".zip")]
    test_folders.sort(
        key=lambda name: datetime.strptime(
            name.split("_")[-2] + name.split("_")[-1], "%Y%m%d%H%M%S"
        )
    )
    return os.path.join(base_path, test_folders[-1])

# ---------- 自動對應對應的 Spec JSON ----------
def get_spec_json_path_by_product(product_name):
    """
    根據 SSD 型號找到對應的 spec JSON 檔案路徑。
    :param product_name: SSD 型號（例如 "P5336-U2"）
    :return: Spec JSON 的路徑
    """
    try:
        with open(family_mapping_file, "r") as f:
            mapping = json.load(f)
    except Exception as e:
        print(f"❌ 無法讀取 family_mapping.json: {e}")
        return None

    model_prefix = product_name.split("-")[0]  # e.g., P5336
    if model_prefix in mapping:
        return os.path.join(spec_folder, mapping[model_prefix])
    else:
        print(f"❌ 找不到對應的 spec JSON for model: {model_prefix}")
        return None

# ---------- 找到測試結果資料夾並選擇是否創建新資料夾 ----------
def find_latest_result_folder(base_path, selected_model, output_folder_name):
    """
    根據 SSD 型號找到最新的測試結果資料夾，或選擇建立新資料夾。
    :param base_path: 測試結果的根目錄
    :param selected_model: 選擇的 SSD 型號（例如 "P5336-U2"）
    :param output_folder_name: 測試結果資料夾的名稱（例如 "TestResults"）
    :return: 最新或新建的資料夾路徑
    """
    folders = glob.glob(os.path.join(base_path, f"{selected_model}_{output_folder_name}_*"))
    latest_folder = max(folders, key=os.path.getmtime) if folders else None

    create_new = input("Do you want to create a new folder? (y/n): ").strip().lower()
    if create_new == 'y':
        new_folder = os.path.join(base_path, f"{selected_model}_{output_folder_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(new_folder)
        print(f"Created new folder: {new_folder}")
        return new_folder
    elif create_new == 'n':
        if latest_folder:
            print(f"Using the latest folder: {latest_folder}")
            return latest_folder
        else:
            print("No existing folders found. Exiting.")
            sys.exit(1)
    else:
        print("Invalid input. Exiting.")
        sys.exit(1)

# ---------- 取得測試結果 CSV 檔案名稱 ----------
def find_result_file_name(market_name, form_factor, base_folder):
    """
    根據市場名稱和形狀因子獲取測試結果 CSV 檔案路徑。
    :param market_name: 市場名稱（例如 "P5336-U2"）
    :param form_factor: SSD 形狀因子（例如 "U2"）
    :param base_folder: 根目錄
    :return: 完整的 CSV 檔案路徑
    """
    return os.path.join(base_folder, f"{market_name}_fio_summary_results.csv")
