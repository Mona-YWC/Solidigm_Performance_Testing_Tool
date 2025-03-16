import os
import json
import logging
import sys

def load_test_cases(json_file):
    """
    讀取測試案例 JSON 檔案，並回傳測試案例的字典。

    :param json_file: 測試案例 JSON 檔案的路徑
    :return: 讀取後的測試案例字典
    """
    if not os.path.exists(json_file):
        logging.error(f"❌ 錯誤: 找不到測試案例檔案 {json_file}，請確認檔案存在！")
        sys.exit(1)

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"❌ 錯誤: 解析 JSON 檔案時發生錯誤: {e}")
        sys.exit(1)

def select_ssd_model(json_file):
    """
    讓使用者從指定的 JSON 測試案例選擇 SSD 型號
    """
    test_cases = load_test_cases(json_file)  # ✅ 不再重新詢問 JSON 檔案
    ssd_models = list(test_cases.keys())

    if not ssd_models:
        print("❌ 錯誤: 測試案例清單為空，請確認測試案例 JSON 檔案內容！")
        sys.exit(1)

    print("\n📌 請選擇 SSD 型號（來自選擇的 JSON 檔案）:")
    for idx, model in enumerate(ssd_models, 1):
        print(f"[{idx}] {model}")

    try:
        selection = int(input("輸入對應的型號編號: ")) - 1
        if selection < 0 or selection >= len(ssd_models):
            print("❌ 無效選擇，請重新執行程式。")
            sys.exit(1)

        return ssd_models[selection]
    except ValueError:
        print("❌ 輸入錯誤，請輸入數字對應的型號。")
        sys.exit(1)
