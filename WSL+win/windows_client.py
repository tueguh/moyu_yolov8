import requests
import cv2
import time
import socket
import json
import threading
import queue
import base64

# --- YOLO API 配置 ---
WSL_IP = "172.26.8.96"
API_URL = f"http://{WSL_IP}:8888/detect/"

# --- TCP 配置 ---
HOST = "0.0.0.0"
PORT = 9999

# --- 共享队列 ---
result_queue = queue.Queue(maxsize=1)  # 存最新结果

def capture_thread():
    """采集 + YOLO 检测线程"""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("無法打開攝影機！")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 压缩成 JPEG
        _, img_encoded = cv2.imencode('.jpg', frame)
        files = {'image': ('image.jpg', img_encoded.tobytes(), 'image/jpeg')}

        data = {"person_count": 0, "boxes": [], "frame": None}
        try:
            response = requests.post(API_URL, files=files, timeout=5)
            if response.status_code == 200:
                data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"YOLO 連線錯誤: {e}")

        # 保存原始帧，用 Base64 编码
        _, jpeg_frame = cv2.imencode('.jpg', frame)
        frame_b64 = base64.b64encode(jpeg_frame.tobytes()).decode('utf-8')
        data["frame"] = frame_b64

        # 放进队列（覆盖旧数据）
        if result_queue.full():
            result_queue.get_nowait()
        result_queue.put_nowait(data)

        time.sleep(1/5)  # 控制频率

    cap.release()

def client_handler(conn, addr):
    """处理单个客户端连接"""
    print(f"客戶端已連線: {addr}")
    try:
        while True:
            try:
                data = result_queue.get(timeout=1)
            except queue.Empty:
                continue

            msg = json.dumps(data).encode("utf-8")
            conn.sendall(len(msg).to_bytes(4, "big") + msg)

    except Exception as e:
        print(f"客戶端斷開 {addr}: {e}")
    finally:
        conn.close()

def tcp_server_thread():
    """TCP 服务器线程，支持多个客户端"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"TCP 服務啟動，監聽 {PORT}")

    while True:
        conn, addr = server.accept()
        t = threading.Thread(target=client_handler, args=(conn, addr), daemon=True)
        t.start()

def main():
    threading.Thread(target=capture_thread, daemon=True).start()
    tcp_server_thread()

if __name__ == "__main__":
    main()
