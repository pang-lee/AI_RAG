#!/bin/bash

# 刪除 log/ 目錄及其內容
if [ -d "logs" ]; then
    sudo rm -rf logs/
    if [ $? -eq 0 ]; then
        echo "已成功刪除 logs/ 目錄"
    else
        echo "刪除 logs/ 目錄失敗，可能權限不足或檔案被鎖定"
        exit 1
    fi
else
    echo "logs/ 目錄不存在"
fi
