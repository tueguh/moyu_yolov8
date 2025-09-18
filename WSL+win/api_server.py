# api_server.py - 運行在 WSL (Ubuntu) 上
import uvicorn
from fastapi import FastAPI, File, UploadFile
from ultralytics import YOLO
import numpy as np
import cv2
from typing import List

print("正在啟動 FastAPI 伺服器...")

# 建立 FastAPI 應用
app = FastAPI(title="YOLOv8 Detection API", version="1.0")

# --- 全域載入模型 (效能最佳化) ---
# 模型只需要在伺服器啟動時載入一次
print("正在載入 YOLOv8 模型到 GPU...")
try:
    model = YOLO("yolov8n.pt")
    # 預熱模型，讓第一次請求速度更快
    model.predict(np.zeros((640, 480, 3)), device='cuda', verbose=False)
    print("模型載入並預熱成功！")
except Exception as e:
    print(f"模型載入失敗: {e}")
    model = None

# --- API 端點 (Endpoint) ---
@app.post("/detect/")
async def detect_image(image: UploadFile = File(...)):
    """
    接收上傳的圖片檔案，執行 YOLOv8 偵測，並回傳 JSON 結果。
    """
    if not model:
        return {"error": "模型未成功載入，無法進行偵測。"}

    # 1. 讀取並解碼圖片
    contents = await image.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        return {"error": "無法解碼圖片。"}

    # 2. 執行 YOLO 偵測
    results = model.predict(frame, conf=0.5, classes=[0], device='cuda', verbose=False)
    
    # 3. 處理並格式化結果
    boxes_data = []
    person_count = 0
    for box in results[0].boxes:
        person_count += 1
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        confidence = float(box.conf[0])
        boxes_data.append({
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "confidence": round(confidence, 2)
        })

    # 4. 回傳 JSON
    return {
        "person_count": person_count,
        "boxes": boxes_data
    }

# --- 啟動伺服器 ---
if __name__ == "__main__":
    # 監聽 0.0.0.0 可以讓 Windows 端的請求訪問到
    uvicorn.run("api_server:app", host="0.0.0.0", port=8888, reload=False)