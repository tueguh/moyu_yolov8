import socket
import threading
import json
import time
import base64
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw, ImageFont, ImageTk
import tkinter as tk
from io import BytesIO

SERVER_IP = "192.168.233.1"  # 服务器 IP
PORT = 9999

# -------------------- 浮窗显示人数 --------------------
class FloatingWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.5)
        self.root.geometry("150x50+1700+950")
        self.label = tk.Label(self.root, text="0", font=("Arial", 24), bg="black", fg="white")
        self.label.pack(fill="both", expand=True)
        self.label.bind("<Button-1>", self.start_move)
        self.label.bind("<B1-Motion>", self.do_move)
        self.root.withdraw()

    def start_move(self, event):
        self.start_x = event.x
        self.start_y = event.y

    def do_move(self, event):
        x = self.root.winfo_x() + event.x - self.start_x
        y = self.root.winfo_y() + event.y - self.start_y
        self.root.geometry(f"+{x}+{y}")

    def update(self, count):
        self.label.config(text=str(count))

    def show(self):
        self.root.deiconify()

    def hide(self):
        self.root.withdraw()

# -------------------- 视频窗口 --------------------
class VideoWindow:
    def __init__(self, on_hide_callback=None):
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.width = 107
        self.height = 80
        self.root.geometry(f"{self.width}x{self.height}+1600+900")
        self.root.attributes("-alpha", 0.2)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.label = tk.Label(self.root)
        self.label.pack(fill="both", expand=True)
        self.root.withdraw()
        self.running = False
        self.boxes = []
        self.frame_size = (self.width, self.height)
        self.on_hide_callback = on_hide_callback

        # 拖动支持
        self.label.bind("<Button-1>", self.start_move)
        self.label.bind("<B1-Motion>", self.do_move)

        # 右键关闭窗口
        self.label.bind("<Button-3>", lambda e: self.hide())

    def start_move(self, event):
        self.start_x = event.x
        self.start_y = event.y

    def do_move(self, event):
        x = self.root.winfo_x() + event.x - self.start_x
        y = self.root.winfo_y() + event.y - self.start_y
        self.root.geometry(f"+{x}+{y}")

    def show(self):
        self.root.deiconify()
        self.running = True

    def hide(self):
        self.running = False
        self.root.withdraw()
        if self.on_hide_callback:
            self.on_hide_callback()  # 同步勾选状态

    def update_boxes(self, boxes):
        self.boxes = boxes or []

    def update_frame_from_server(self, frame_b64):
        if not self.running or not frame_b64:
            return
        try:
            frame_bytes = base64.b64decode(frame_b64)
            img = Image.open(BytesIO(frame_bytes))
            W_server, H_server = img.size
            W_client, H_client = self.frame_size
            img = img.resize(self.frame_size)
            draw = ImageDraw.Draw(img)

            for box in self.boxes:
                if isinstance(box, (list, tuple)) and len(box) >= 4:
                    x1, y1, x2, y2 = box[:4]
                elif isinstance(box, dict):
                    x1 = box.get("x1", 0)
                    y1 = box.get("y1", 0)
                    x2 = box.get("x2", 0)
                    y2 = box.get("y2", 0)
                else:
                    continue
                # 按比例缩放
                x1 = int(x1 * W_client / W_server)
                y1 = int(y1 * H_client / H_server)
                x2 = int(x2 * W_client / W_server)
                y2 = int(y2 * H_client / H_server)
                draw.rectangle([x1, y1, x2, y2], outline="red", width=2)

            img_tk = ImageTk.PhotoImage(img)
            self.label.imgtk = img_tk
            self.label.config(image=img_tk)
        except Exception as e:
            print("更新视频错误:", e)

# -------------------- 托盘客户端 --------------------
class TrayClient:
    def __init__(self, server_ip, port, floating_window):
        self.server_ip = server_ip
        self.port = port
        self.sock = None
        self.running = True
        self.person_count = 0
        self.floating = floating_window

        self.show_video = False
        self.video_window = VideoWindow(on_hide_callback=self.on_video_hidden)

        self.icon = pystray.Icon("YOLO", self.create_icon(0), "人數: 0")
        self.icon.menu = pystray.Menu(
            item("顯示浮窗", self.show_floating),
            item("隱藏浮窗", self.hide_floating),
            item("顯示視頻窗口", self.toggle_video, checked=lambda item: self.show_video),
            item("退出", self.exit_app)
        )

        # 启动线程
        self.tcp_thread = threading.Thread(target=self.client_thread, daemon=True)
        self.tcp_thread.start()
        self.video_thread = threading.Thread(target=self.video_loop, daemon=True)
        self.video_thread.start()
        threading.Thread(target=self.icon.run, daemon=True).start()

    def create_icon(self, number):
        size = 64
        img = Image.new("RGBA", (size, size), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        text = str(number)
        font_size = 64
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0,0), text, font=font)
        w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
        draw.text(((size-w)//2, (size-h)//2 - bbox[1]), text, font=font, fill=(255,0,0,255))
        return img

    def show_floating(self, icon=None, item=None):
        self.floating.root.after(0, self.floating.show)

    def hide_floating(self, icon=None, item=None):
        self.floating.root.after(0, self.floating.hide)

    def toggle_video(self, icon=None, item=None):
        self.show_video = not self.show_video
        if self.show_video:
            self.video_window.show()
        else:
            self.video_window.hide()
        self.icon.update_menu()  # 刷新菜单勾选

    def on_video_hidden(self):
        self.show_video = False
        self.icon.update_menu()  # 用户手动关闭窗口同步勾选

    def exit_app(self, icon=None, item=None):
        self.running = False
        try:
            if self.sock:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
        except:
            pass
        self.video_window.hide()
        self.floating.root.after(0, self.floating.root.destroy)
        self.icon.stop()

    def client_thread(self):
        buffer = b''
        while self.running:
            try:
                if not self.sock:
                    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.sock.settimeout(5)
                    self.sock.connect((self.server_ip, self.port))
                    print("已连接服务器")

                data = self.sock.recv(65536)
                if not self.running:
                    break
                if not data:
                    self.sock.close()
                    self.sock = None
                    time.sleep(3)
                    continue
                buffer += data

                while len(buffer) >= 4:
                    msg_len = int.from_bytes(buffer[:4], "big")
                    if len(buffer) < 4 + msg_len:
                        break
                    msg_data = buffer[4:4+msg_len]
                    buffer = buffer[4+msg_len:]
                    try:
                        json_data = json.loads(msg_data.decode("utf-8"))
                        self.person_count = int(json_data.get("person_count", 0))
                        boxes = json_data.get("boxes", [])
                        frame_b64 = json_data.get("frame", None)
                        self.video_window.update_boxes(boxes)
                        if frame_b64:
                            self.video_window.update_frame_from_server(frame_b64)
                    except Exception as e:
                        print("解析数据错误:", e)
                        continue

                    self.floating.root.after(0, self.floating.update, self.person_count)
                    self.icon.icon = self.create_icon(self.person_count)
                    self.icon.title = f"人數: {self.person_count}"

            except (socket.timeout, ConnectionRefusedError):
                print("无法连接服务器，3秒后重试...")
                if self.sock:
                    try:
                        self.sock.shutdown(socket.SHUT_RDWR)
                        self.sock.close()
                    except:
                        pass
                    self.sock = None
                time.sleep(3)
            except Exception as e:
                if self.running:
                    print("TCP线程错误:", e)
                time.sleep(3)

    def video_loop(self):
        while self.running:
            if self.show_video:
                try:
                    self.video_window.root.update_idletasks()
                    self.video_window.root.update()
                except:
                    pass
            time.sleep(0.03)

# -------------------- 主程序 --------------------
if __name__ == "__main__":
    floating_window = FloatingWindow()
    client = TrayClient(SERVER_IP, PORT, floating_window)
    floating_window.root.mainloop()
