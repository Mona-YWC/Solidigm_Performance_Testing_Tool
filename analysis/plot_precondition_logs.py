#!/usr/bin/env python3

import os
import re
import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from matplotlib.ticker import FuncFormatter

# ========== SPEC 路徑設定 ==========
BASE_PATH = "/root/Solidigm_Performance_Testing_Tool"
SPEC_FOLDER = os.path.join(BASE_PATH, "spec_reference")
FAMILY_MAPPING_FILE = os.path.join(SPEC_FOLDER, "family_mapping.json")

def find_latest_test_folder(base_path=BASE_PATH):
    test_folders = [
        folder for folder in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, folder)) and
           re.match(r".+_TestResults_\d{8}_\d{6}$", folder)
    ]
    if not test_folders:
        print("❌ No valid test folders found.")
        return None
    test_folders.sort(
        key=lambda name: datetime.strptime(
            name.split("_")[-2] + name.split("_")[-1], "%Y%m%d%H%M%S"
        )
    )
    return os.path.join(base_path, test_folders[-1])

def get_spec_json_path_by_product(product_name):
    try:
        with open(FAMILY_MAPPING_FILE, "r") as f:
            mapping = json.load(f)
    except Exception as e:
        print(f"❌ 無法讀取 family_mapping.json: {e}")
        return None
    model_prefix = product_name.split("-")[0]
    return os.path.join(SPEC_FOLDER, mapping.get(model_prefix, ""))

def get_spec_value(spec_path, model_key, metric_name, capacity):
    if not os.path.exists(spec_path):
        return None
    with open(spec_path, "r") as f:
        spec_data = json.load(f)
    def parse_tb_string(tb_str):
        return float(tb_str.replace("TB", "").strip())
    if model_key not in spec_data:
        return None
    available_caps = spec_data[model_key]["Capacity"]
    cap_diffs = [abs(parse_tb_string(c) - parse_tb_string(capacity)) for c in available_caps]
    if not cap_diffs:
        return None
    min_diff = min(cap_diffs)
    if min_diff > 0.5:
        return None
    idx = cap_diffs.index(min_diff)
    return spec_data[model_key].get(metric_name, [])[idx]

def infer_metric_from_logname(log_path):
    name = os.path.basename(log_path).lower()
    if "128kb_seq_read" in name:
        return "128KB Seq Read (MB/s)"
    elif "128kb_seq_write" in name:
        return "128KB Seq Write (MB/s)"
    elif "16kb_randrw" in name or "70r_30w" in name:
        return "16KB Random Mixed 70/30 RR/RW (KIOPs)"
    elif "16kb_randr" in name:
        return "16KB Random Read (KIOPs)"
    elif "16kb_randw" in name:
        return "16KB Random Write (KIOPs)"
    elif "4kb_randrw" in name:
        return "4KB Random Mixed 70/30 RR/RW (KIOPs)"
    elif "4kb_randr" in name:
        return "4KB Random Read (KIOPs)"
    elif "4kb_randw" in name:
        return "4KB Random Write (KIOPs)"
    return None

def plot_bw_log(log_path, output_folder, product_name, prefix):
    txt_files = sorted([
        f for f in os.listdir(log_path)
        if f.startswith(prefix) and f.endswith(".log")
    ])
    if not txt_files:
        print(f"⚠️ No folders found with prefix '{prefix}' under {log_path}")
        return

    model_key = "-".join(product_name.split("-")[:2])
    capacity = next((part for part in product_name.split("-") if re.match(r"\d+\.\d+TB", part)), None)
    if not capacity:
        capacity = product_name.split("-")[-1].replace("TB", "") + "TB"
    print(f"🎯 使用容量為: {capacity}")

    spec_path = get_spec_json_path_by_product(product_name)
    subfolder_name = os.path.basename(log_path).lower()
    plt.figure(figsize=(16, 6))
    ax = plt.gca()
    ax.set_facecolor('white')
    ax.figure.set_facecolor('white')
    ax.ticklabel_format(style='plain', axis='y')  # 👈 關掉 y 軸科學記號

    all_times, all_bws_mb = [], []
    available_threads = set()
    for txt in txt_files:
        with open(os.path.join(log_path, txt), "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 3:
                    try:
                        available_threads.add(int(parts[2]))
                    except:
                        continue

    if not available_threads:
        print(f"❌ No valid thread info found in {log_path}")
        return

    selected_thread = 0 if 0 in available_threads else min(available_threads)
    print(f"🔍 Using thread {selected_thread} in {log_path}")

    global_start = None
    for txt in txt_files:
        with open(os.path.join(log_path, txt), "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) < 3 or int(parts[2]) != selected_thread:
                    continue
                t = int(parts[0])
                if global_start is None or t < global_start:
                    global_start = t

    for txt in txt_files:
        filepath = os.path.join(log_path, txt)
        times, bws_mb = [], []
        with open(filepath, "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) < 3 or int(parts[2]) != selected_thread:
                    continue
                t = int(parts[0]) - global_start
                bw = int(parts[1])
                times.append(t)
                bws_mb.append(bw)
        if times:
            all_times.extend(times)
            all_bws_mb.extend(bws_mb)
            plt.plot(times, bws_mb, label=txt, linewidth=0.8)

    if not all_times:
        print(f"⚠️ No valid data found for merged plot in {log_path}")
        return

    metric = infer_metric_from_logname(log_path)
    if metric:
        spec_val = get_spec_value(spec_path, model_key, metric, capacity)
        print(f"📌 spec_val: {spec_val}")
        if spec_val:
            plt.axhline(spec_val, color='blue', linestyle='-', linewidth=1,
                        label=f'SPEC: {spec_val} MB/s')
            if "rand" in subfolder_name:
                lower, upper = spec_val * 0.9, spec_val * 1.1
                plt.axhspan(lower, upper, color='green', alpha=0.2, label="SPEC ±10% Range")
                avg_bw = np.mean(all_bws_mb)
                plt.axhline(avg_bw, color='red', linestyle='--', linewidth=1,
                            label=f'Avg Bandwidth: {avg_bw:.2f} MB/s')

    max_time = max(all_times)
    tick_count = 20
    tick_interval = max(max_time // tick_count, 1)
    tick_values = np.arange(0, max_time + 1, tick_interval)
    plt.xticks(tick_values)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x)}"))
    ax.set_xlim(left=0)  # ✅ 加上這行解決 X 軸 0 空格問題
    plt.xticks(rotation=45)

    plt.title(f"{prefix.capitalize()} Bandwidth - {os.path.basename(log_path)}")
    plt.xlabel("Time (Seconds)")
    plt.ylabel("Bandwidth (MB/s)")
    plt.grid(True, linestyle='--', linewidth=0.5)
    plt.legend()
    plt.tight_layout()
    out_file = os.path.join(output_folder, f"{os.path.basename(log_path)}_{prefix.lower()}merged_plot.png")
    plt.savefig(out_file)
    print(f"✅ Merged plot saved: {out_file}")
    plt.close()

def main():
    latest_folder = find_latest_test_folder()
    if not latest_folder:
        return
    product_name = os.path.basename(latest_folder).replace("_TestResults_", "")
    for device_folder in os.listdir(latest_folder):
        device_path = os.path.join(latest_folder, device_folder)
        if os.path.isdir(device_path) and device_folder.endswith("_precondition_log"):
            for test_type_folder in os.listdir(device_path):
                log_path = os.path.join(device_path, test_type_folder)
                if os.path.isdir(log_path):
                    print(f"📊 Plotting precondition + test logs in: {log_path}")
                    plot_bw_log(log_path, log_path, product_name, "precondition")
                    plot_bw_log(log_path, log_path, product_name, "test")

if __name__ == "__main__":
    main()
