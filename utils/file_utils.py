import os
import sys
import glob
from datetime import datetime



#初始化
# 找出最新的結果資料夾
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

# 測試結果輸出            
# 取得測試結果 CSV 檔案名稱
def find_result_file_name(market_name, form_factor, base_folder):
    return os.path.join(base_folder, f"{market_name}_fio_summary_results.csv")
