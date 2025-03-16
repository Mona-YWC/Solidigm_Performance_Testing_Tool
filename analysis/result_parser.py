import re
import os 
import csv

# 測試結果輸出            
# 取得測試結果 CSV 檔案名稱
def find_result_file_name(market_name, form_factor, base_folder):
    return os.path.join(base_folder, f"{market_name}_fio_summary_results.csv")


# 測試結果輸出   
# 解析輸出結果並寫入 CSV
def parse_fio_output(output):
    # 提取 read 和 write 部分的 IOPS 和 BW
    def extract_iops_bw(match_iops, match_bw):
        iops = 0
        bw = 0
        
        if match_iops:
            iops_value = match_iops.group(1).lower()
            if iops_value.endswith("k"):
                iops = int(float(iops_value[:-1]) * 1_000)
            elif iops_value.endswith("m"):
                iops = int(float(iops_value[:-1]) * 1_000_000)
            else:
                iops = int(float(iops_value))
        
        if match_bw:
            bw_value = float(match_bw.group(1))
            bw_unit = match_bw.group(2)
            if "MiB/s" in bw_unit:
                bw_value *= 1.048576  # MiB -> MB
            elif "GiB/s" in bw_unit:
                bw_value *= 1024  # GiB -> MB
            bw = bw_value
        
        return iops, bw

    read_iops_match = re.search(r'read:.*IOPS=([0-9\.]+[kKmM]?)', output)
    read_bw_match = re.search(r'read:.*BW=([0-9\.]+)([KMG]?i?B/s)', output)
    write_iops_match = re.search(r'write:.*IOPS=([0-9\.]+[kKmM]?)', output)
    write_bw_match = re.search(r'write:.*BW=([0-9\.]+)([KMG]?i?B/s)', output)
    
    read_iops, read_bw = extract_iops_bw(read_iops_match, read_bw_match)
    write_iops, write_bw = extract_iops_bw(write_iops_match, write_bw_match)
    
    # 計算總 IOPS 和 BW
    total_iops = read_iops + write_iops
    total_bw = read_bw + write_bw
    
    # 提取 runtime
    runtime_match = re.search(r'run=([0-9]+)-[0-9]+msec', output)
    runtime = str(int(runtime_match.group(1)) // 1000) if runtime_match else "N/A"
    
    return f"{total_bw:.2f}MB/s", total_iops, runtime


# 測試結果輸出   
# 寫入結果到 CSV
def write_to_csv(csv_file, data):
    headers = ["Device", "Test Name", "Bandwidth", "IOPS", "IO Depth", "Num Jobs", "IO Engine", "Runtime"]
    write_header = not os.path.exists(csv_file)
    with open(csv_file, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(headers)
        writer.writerow(data)