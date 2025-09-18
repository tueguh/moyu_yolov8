#!/bin/bash
echo "--- 正在啟動 YOLOv8 API 伺服器 ---"
echo "--- 作者: Gemini ---"

# 進入我們為 Python 3.10 建立的專案目錄
cd ~/headless_service_py310

# 啟動虛擬環境
source venv/bin/activate

# 執行 Python API 伺服器
# 注意: 我們在這裡直接執行 python api_server.py
# uvicorn 會在程式碼內部被呼叫
python ~/api_server.py
