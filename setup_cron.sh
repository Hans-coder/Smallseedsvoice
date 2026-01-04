#!/bin/bash
# 設置定時任務腳本

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_PATH="$SCRIPT_DIR/venv/bin/python"
MAIN_SCRIPT="$SCRIPT_DIR/main.py"

# 檢查虛擬環境是否存在
if [ ! -f "$PYTHON_PATH" ]; then
    echo "錯誤：未找到虛擬環境，請先運行 'python3 -m venv venv'"
    exit 1
fi

# 獲取當前用戶的crontab
CRON_FILE=$(mktemp)
crontab -l > "$CRON_FILE" 2>/dev/null || touch "$CRON_FILE"

# 檢查是否已經存在相同的任務
if grep -q "$MAIN_SCRIPT" "$CRON_FILE"; then
    echo "⚠️  定時任務已存在"
    echo "現有的定時任務："
    grep "$MAIN_SCRIPT" "$CRON_FILE"
    echo ""
    read -p "是否要替換現有任務？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        rm "$CRON_FILE"
        exit 0
    fi
    # 移除舊任務
    sed -i.bak "\|$MAIN_SCRIPT|d" "$CRON_FILE"
fi

# 顯示選項
echo "請選擇定時任務頻率："
echo "1) 每週一上午9點（推薦）"
echo "2) 每天上午9點"
echo "3) 每週一、三、五上午9點"
echo "4) 自定義"
read -p "請選擇 (1-4): " choice

case $choice in
    1)
        CRON_SCHEDULE="0 9 * * 1"
        DESCRIPTION="每週一上午9點"
        ;;
    2)
        CRON_SCHEDULE="0 9 * * *"
        DESCRIPTION="每天上午9點"
        ;;
    3)
        CRON_SCHEDULE="0 9 * * 1,3,5"
        DESCRIPTION="每週一、三、五上午9點"
        ;;
    4)
        read -p "請輸入cron表達式（例如：0 9 * * 1）: " CRON_SCHEDULE
        DESCRIPTION="自定義：$CRON_SCHEDULE"
        ;;
    *)
        echo "無效選擇"
        rm "$CRON_FILE"
        exit 1
        ;;
esac

# 添加新任務
CRON_LINE="$CRON_SCHEDULE cd $SCRIPT_DIR && $PYTHON_PATH $MAIN_SCRIPT >> $SCRIPT_DIR/logs/cron.log 2>&1"
echo "$CRON_LINE" >> "$CRON_FILE"

# 安裝crontab
crontab "$CRON_FILE"
rm "$CRON_FILE"

echo ""
echo "✅ 定時任務設置成功！"
echo "   頻率：$DESCRIPTION"
echo "   命令：$PYTHON_PATH $MAIN_SCRIPT"
echo ""
echo "查看定時任務：crontab -l"
echo "編輯定時任務：crontab -e"
echo "刪除定時任務：crontab -r"
echo ""
echo "日誌文件：$SCRIPT_DIR/logs/cron.log"

