#!/bin/bash

# 需求的 Python 版本
REQUIRED_PYTHON="3.10"
REQUIRED_MAJOR=$(echo "$REQUIRED_PYTHON" | cut -d. -f1)
REQUIRED_MINOR=$(echo "$REQUIRED_PYTHON" | cut -d. -f2)

# 獲取當前 Python 版本
if command -v python3 &>/dev/null; then
    CURRENT_PYTHON=$(python3 --version 2>/dev/null | awk '{print $2}')
    CURRENT_MAJOR=$(echo "$CURRENT_PYTHON" | cut -d. -f1)
    CURRENT_MINOR=$(echo "$CURRENT_PYTHON" | cut -d. -f2)
else
    CURRENT_MAJOR=0
    CURRENT_MINOR=0
fi

# 比較版本
if [ "$CURRENT_MAJOR" -lt "$REQUIRED_MAJOR" ] || \
   { [ "$CURRENT_MAJOR" -eq "$REQUIRED_MAJOR" ] && [ "$CURRENT_MINOR" -lt "$REQUIRED_MINOR" ]; }; then
    echo "Current Python version is too low ($CURRENT_PYTHON). Upgrading to Python $REQUIRED_PYTHON..."
    sudo apt update
    sudo apt install -y python3.$REQUIRED_MINOR python3-pip
    sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.$REQUIRED_MINOR 1
    sudo update-alternatives --config python3
else
    echo "Python $CURRENT_PYTHON is sufficient."
fi

# 確保 pip 是最新版本
echo "Upgrading pip..."
pip3 install --upgrade pip

# 安裝 requirements.txt 中的套件
if [ -f "requirements.txt" ]; then
    echo "Installing packages from requirements.txt..."
    pip3 install -r requirements.txt
else
    echo "requirements.txt not found. Skipping package installation."
fi

echo "Setup completed."
