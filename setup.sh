#!/bin/bash

# 設定所需的 Python 版本
REQUIRED_PYTHON="3.10"
REQUIRED_MAJOR=$(echo "$REQUIRED_PYTHON" | cut -d. -f1)
REQUIRED_MINOR=$(echo "$REQUIRED_PYTHON" | cut -d. -f2)

# 檢查系統中現有的 Python 版本
if command -v python3 &>/dev/null; then
    CURRENT_PYTHON=$(python3 --version 2>/dev/null | awk '{print $2}')
    CURRENT_MAJOR=$(echo "$CURRENT_PYTHON" | cut -d. -f1)
    CURRENT_MINOR=$(echo "$CURRENT_PYTHON" | cut -d. -f2)
else
    CURRENT_MAJOR=0
    CURRENT_MINOR=0
fi

# 判斷 Python 版本並執行對應操作
if [ "$CURRENT_MAJOR" -lt 3 ]; then
    echo "Current Python version ($CURRENT_MAJOR.$CURRENT_MINOR) is too low. Installing Python $REQUIRED_PYTHON..."
    sudo yum remove -y python2 python
    sudo yum install -y python3.$REQUIRED_MINOR
    sudo ln -sf /usr/bin/python3.$REQUIRED_MINOR /usr/bin/python3
    sudo ln -sf /usr/bin/python3 /usr/bin/python
elif [ "$CURRENT_MAJOR" -eq 3 ] && [ "$CURRENT_MINOR" -lt "$REQUIRED_MINOR" ]; then
    echo "Python version is $CURRENT_PYTHON, which is lower than $REQUIRED_PYTHON."
    read -p "Do you want to upgrade to Python $REQUIRED_PYTHON? [y/N]: " UPGRADE
    if [[ "$UPGRADE" =~ ^[Yy]$ ]]; then
        echo "Upgrading Python to $REQUIRED_PYTHON..."
        sudo yum remove -y python3
        sudo yum install -y python3.$REQUIRED_MINOR
        sudo ln -sf /usr/bin/python3.$REQUIRED_MINOR /usr/bin/python3
        sudo ln -sf /usr/bin/python3 /usr/bin/python
    else
        echo "Keeping the current Python version ($CURRENT_PYTHON)."
    fi
else
    echo "Python $CURRENT_PYTHON is up-to-date or newer than $REQUIRED_PYTHON. No changes made."
fi

# 確保 pip 是最新版本
echo "Upgrading pip..."
python3 -m ensurepip --upgrade
python3 -m pip install --upgrade pip

# 安裝 requirements.txt 中的套件
if [ -f "requirements.txt" ]; then
    echo "Installing packages from requirements.txt..."
    python3 -m pip install -r requirements.txt || {
        echo "Some packages could not be installed. Please check their Python version requirements."
        exit 1
    }
else
    echo "requirements.txt not found. Skipping package installation."
fi

echo "Setup completed."
