import os
import logging

def setup_logging(log_file):
    """
    設定日誌紀錄，確保所有日誌輸出到檔案並顯示在終端機。
    
    :param log_file: 要儲存日誌的檔案路徑
    """
    # 確保日誌目錄存在
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        filename=log_file,
        filemode="a",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger("").addHandler(console)
    
    logging.info("✅ Logging setup complete.")
