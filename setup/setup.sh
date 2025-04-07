#!/bin/bash

# 顯示開始訊息
echo "==========================================="
echo "    Solidigm Performance Testing Tool"
echo "         系統環境安裝腳本"
echo "==========================================="

# 需求的 Python 版本
REQUIRED_PYTHON="3.10"
REQUIRED_MAJOR=$(echo "$REQUIRED_PYTHON" | cut -d. -f1)
REQUIRED_MINOR=$(echo "$REQUIRED_PYTHON" | cut -d. -f2)

# 檢測作業系統類型
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "無法確定作業系統類型！"
    exit 1
fi

echo "檢測到操作系統: $OS"

# 獲取當前 Python 版本
if command -v python3 &>/dev/null; then
    CURRENT_PYTHON=$(python3 --version 2>/dev/null | awk '{print $2}')
    CURRENT_MAJOR=$(echo "$CURRENT_PYTHON" | cut -d. -f1)
    CURRENT_MINOR=$(echo "$CURRENT_PYTHON" | cut -d. -f2)
    echo "當前 Python 版本: $CURRENT_PYTHON"
else
    CURRENT_MAJOR=0
    CURRENT_MINOR=0
    echo "未檢測到 Python3"
fi

# 比較版本並安裝/升級 Python (根據不同的系統)
if [ "$CURRENT_MAJOR" -lt "$REQUIRED_MAJOR" ] || \
   { [ "$CURRENT_MAJOR" -eq "$REQUIRED_MAJOR" ] && [ "$CURRENT_MINOR" -lt "$REQUIRED_MINOR" ]; }; then
    echo "當前 Python 版本過低 ($CURRENT_PYTHON)。正在升級到 Python $REQUIRED_PYTHON..."
    
    if [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
        # CentOS/RHEL 系統
        echo "在 CentOS/RHEL 上安裝 Python $REQUIRED_PYTHON..."
        sudo yum install -y epel-release
        sudo yum install -y python${REQUIRED_MAJOR}${REQUIRED_MINOR} python${REQUIRED_MAJOR}-pip
        sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python${REQUIRED_MAJOR}.${REQUIRED_MINOR} 1
        sudo alternatives --set python3 /usr/bin/python${REQUIRED_MAJOR}.${REQUIRED_MINOR}
    elif [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        # Ubuntu/Debian 系統
        echo "在 Ubuntu/Debian 上安裝 Python $REQUIRED_PYTHON..."
        sudo apt update
        sudo apt install -y python3.$REQUIRED_MINOR python3-pip
        sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.$REQUIRED_MINOR 1
        sudo update-alternatives --config python3
    else
        echo "不支持的操作系統: $OS"
        exit 1
    fi
else
    echo "Python $CURRENT_PYTHON 版本符合要求。"
fi

# 安裝系統依賴項 (根據不同的系統)
echo "安裝系統依賴項..."
if [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
    # CentOS/RHEL 系統
    sudo yum groupinstall "Development Tools" -y
    sudo yum install -y gcc python3-devel fio
    
    # 禁用系統自動睡眠
    echo "禁用系統自動睡眠..."
    sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
    sudo mkdir -p /etc/systemd/logind.conf.d/
    echo "[Login]
HandleLidSwitch=ignore
HandleSuspendKey=ignore
HandleHibernateKey=ignore
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore
IdleAction=ignore" | sudo tee /etc/systemd/logind.conf.d/no-sleep.conf
    sudo systemctl restart systemd-logind
    
elif [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    # Ubuntu/Debian 系統
    sudo apt update
    sudo apt install -y build-essential gcc python3-dev fio
    
    # 禁用系統自動睡眠
    echo "禁用系統自動睡眠..."
    sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
    sudo mkdir -p /etc/systemd/logind.conf.d/
    echo "[Login]
HandleLidSwitch=ignore
HandleSuspendKey=ignore
HandleHibernateKey=ignore
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore
IdleAction=ignore" | sudo tee /etc/systemd/logind.conf.d/no-sleep.conf
    sudo systemctl restart systemd-logind
else
    echo "不支持的操作系統: $OS"
    exit 1
fi

# 確保 pip 是最新版本
echo "升級 pip..."
python3 -m pip install --upgrade pip

# 創建 requirements.txt 文件 (如果不存在)
if [ ! -f "requirements.txt" ]; then
    echo "創建 requirements.txt 檔案..."
    cat > requirements.txt << EOF
numpy>=1.21.0,<2.0.0                      # Supports newer features and avoids breaking changes
openpyxl>=3.0.0,<4.0.0                    # Supports modern Excel formats
requests>=2.25.0,<3.0.0                   # Stable and widely-used version
psutil>=5.8.0,<6.0.0                      # Supports the latest system performance features
watchdog>=2.0.0,<3.0.0                    # Provides stable file monitoring
pandas>=1.5.0,<1.6.0                      # Data manipulation and analysis
pyodbc>=4.0.35                            # ODBC database connectivity
Jinja2>=3.0.0,<4.0.0                      # Templating engine for rendering
dash>=2.0.0,<3.0.0                        # Web application framework for dashboards
dash-bootstrap-components>=1.0.0,<2.0.0   # Bootstrap components for Dash
fio                                       # Flexible I/O Tester Python binding
EOF
fi

# 安裝 requirements.txt 中的套件
echo "安裝 Python 套件..."
python3 -m pip install -r requirements.txt

# 完成設置
echo "==========================================="
echo "安裝完成！"
echo "Python 版本："
python3 --version
echo "PIP 版本："
pip3 --version
echo "==========================================="