#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版YOLO后视镜 - 摸鱼神器
将所有功能整合到一个文件中，无需GPU加速
功能：实时人员检测、系统托盘显示、可拖拽浮窗、视频预览
"""

import cv2
import numpy as np
import threading
import time
import tkinter as tk
from tkinter import messagebox
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw, ImageFont, ImageTk
from ultralytics import YOLO
import queue
import sys
import os
from io import BytesIO
import base64

class SimpleYOLOMirror:
    def __init__(self):
        self.running = True
        self.person_count = 0
        self.model = None
        self.cap = None
        self.current_frame = None
        self.current_boxes = []
        self.quitting = False  # 添加退出标志，避免重复调用quit_app
        
        # 创建队列用于线程间通信
        self.result_queue = queue.Queue(maxsize=1)
        
        # 初始化组件
        self.init_model()
        self.init_camera()
        self.init_floating_window()
        self.init_video_window()
        self.init_tray()
        
    def init_model(self):
        """初始化YOLO模型"""
        try:
            print("正在加载YOLOv8模型...")
            self.model = YOLO("yolov8n.pt")  # 使用nano版本，速度更快
            print("模型加载成功！")
        except Exception as e:
            print(f"模型加载失败: {e}")
            messagebox.showerror("错误", f"YOLO模型加载失败: {e}")
            sys.exit(1)
    
    def init_camera(self):
        """初始化摄像头"""
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise Exception("无法打开摄像头")
            print("摄像头初始化成功！")
        except Exception as e:
            print(f"摄像头初始化失败: {e}")
            messagebox.showerror("错误", f"摄像头初始化失败: {e}")
            sys.exit(1)
    
    def init_floating_window(self):
        """初始化浮窗"""
        self.floating_window = FloatingWindow()
        
    def init_video_window(self):
        """初始化视频窗口"""
        self.show_video = False
        self.video_window = VideoWindow(on_hide_callback=self.on_video_hidden)
        
    def init_tray(self):
        """初始化系统托盘"""
        self.icon = pystray.Icon(
            "YOLO",
            self.create_icon(0),
            "人數: 0"
        )
        self.icon.menu = pystray.Menu(
            item("顯示浮窗", self.show_floating),
            item("隱藏浮窗", self.hide_floating),
            item("顯示視頻窗口", self.toggle_video, checked=lambda item: self.show_video),
            item("退出", self.quit_app)
        )
    
    def create_icon(self, number):
        """创建托盘图标"""
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
        """显示浮窗"""
        self.floating_window.root.after(0, self.floating_window.show)
    
    def hide_floating(self, icon=None, item=None):
        """隐藏浮窗"""
        self.floating_window.root.after(0, self.floating_window.hide)
        
    def toggle_video(self, icon=None, item=None):
        """切换视频窗口显示"""
        self.show_video = not self.show_video
        if self.show_video:
            self.video_window.show()
        else:
            self.video_window.hide()
        self.icon.update_menu()  # 刷新菜单勾选

    def on_video_hidden(self):
        """视频窗口被隐藏时的回调"""
        self.show_video = False
        self.icon.update_menu()  # 用户手动关闭窗口同步勾选
    
    def quit_app(self, icon=None, item=None):
        """退出应用"""
        if self.quitting:  # 避免重复调用
            return
        
        self.quitting = True
        print("正在退出...")
        self.running = False
        
        try:
            # 等待线程结束
            time.sleep(0.5)
            
            # 释放摄像头资源
            if self.cap:
                self.cap.release()
                print("摄像头资源已释放")
            
            # 安全关闭视频窗口
            if hasattr(self, 'video_window') and self.video_window:
                try:
                    self.video_window.hide()
                except:
                    pass
            
            # 安全关闭浮窗
            if hasattr(self, 'floating_window') and self.floating_window:
                try:
                    if self.floating_window.root.winfo_exists():
                        self.floating_window.root.quit()
                        self.floating_window.root.destroy()
                except:
                    pass
            
        except Exception as e:
            print(f"退出过程中出现错误: {e}")
        finally:
            # 最后停止托盘
            try:
                if hasattr(self, 'icon'):
                    self.icon.stop()
            except:
                pass
    
    def detect_persons(self, frame):
        """检测画面中的人员"""
        try:
            # 使用YOLO进行检测，只检测人员(class=0)
            results = self.model.predict(
                frame, 
                conf=0.5,  # 置信度阈值
                classes=[0],  # 只检测人员
                device='cpu',  # 使用CPU
                verbose=False
            )
            
            person_count = 0
            boxes = []
            if results and len(results) > 0 and results[0].boxes is not None:
                person_count = len(results[0].boxes)
                # 提取检测框坐标
                for box in results[0].boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    boxes.append([float(x1), float(y1), float(x2), float(y2)])
            
            return person_count, boxes
            
        except Exception as e:
            print(f"检测错误: {e}")
            return 0, []
    
    def camera_thread(self):
        """摄像头采集和检测线程"""
        print("摄像头线程启动")
        
        while self.running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    print("无法读取摄像头画面")
                    time.sleep(1)
                    continue
                
                # 保存当前帧
                self.current_frame = frame.copy()
                
                # 检测人员数量和位置
                person_count, boxes = self.detect_persons(frame)
                self.current_boxes = boxes
                
                # 更新结果队列
                if not self.result_queue.full():
                    try:
                        self.result_queue.put_nowait((person_count, boxes))
                    except queue.Full:
                        pass
                
                # 控制检测频率，避免CPU占用过高
                time.sleep(0.5)  # 每0.5秒检测一次
                
            except Exception as e:
                print(f"摄像头线程错误: {e}")
                time.sleep(1)
        
        print("摄像头线程结束")
    
    def update_display(self):
        """更新显示线程"""
        print("显示更新线程启动")
        
        while self.running:
            try:
                # 从队列获取最新结果
                try:
                    person_count, boxes = self.result_queue.get(timeout=1)
                    self.person_count = person_count
                    
                    # 更新托盘图标
                    if not self.quitting:
                        self.icon.icon = self.create_icon(person_count)
                        self.icon.title = f"人數: {person_count}"
                    
                    # 更新浮窗
                    if not self.quitting and hasattr(self, 'floating_window'):
                        try:
                            if self.floating_window.root.winfo_exists():
                                self.floating_window.root.after(0, self.floating_window.update, person_count)
                        except:
                            pass
                    
                    # 更新视频窗口
                    if self.show_video and self.current_frame is not None and not self.quitting:
                        try:
                            self.video_window.update_boxes(boxes)
                            self.video_window.update_frame(self.current_frame)
                        except:
                            pass
                    
                except queue.Empty:
                    continue
                    
            except Exception as e:
                if not self.quitting:
                    print(f"显示更新错误: {e}")
                time.sleep(1)
        
        print("显示更新线程结束")
    
    def run(self):
        """启动应用"""
        print("启动摸鱼后视镜...")
        
        # 启动摄像头线程
        camera_thread = threading.Thread(target=self.camera_thread, daemon=True)
        camera_thread.start()
        
        # 启动显示更新线程
        update_thread = threading.Thread(target=self.update_display, daemon=True)
        update_thread.start()
        
        # 启动视频更新线程
        video_thread = threading.Thread(target=self.video_loop, daemon=True)
        video_thread.start()
        
        # 启动托盘线程
        threading.Thread(target=self.icon.run, daemon=True).start()
        
        # 启动浮窗主循环（阻塞主线程）
        try:
            self.floating_window.root.protocol("WM_DELETE_WINDOW", self.quit_app)
            self.floating_window.root.mainloop()
        except KeyboardInterrupt:
            print("收到中断信号")
        except Exception as e:
            print(f"主循环错误: {e}")
        finally:
            if not self.quitting:
                self.quit_app()
            
    def video_loop(self):
        """视频窗口更新循环"""
        while self.running:
            if self.show_video and not self.quitting:
                try:
                    if self.video_window.root.winfo_exists():
                        self.video_window.root.update_idletasks()
                        self.video_window.root.update()
                except:
                    if not self.quitting:
                        break
            time.sleep(0.03)

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
        """更新人数显示"""
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

    def update_frame(self, frame):
        if not self.running or frame is None:
            return
        try:
            # 转换OpenCV图像为PIL图像
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
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

def main():
    """主函数"""
    print("="*50)
    print("    摸鱼后视镜 - 简化版")
    print("    实时监控后方人员数量")
    print("="*50)
    
    try:
        app = SimpleYOLOMirror()
        app.run()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行错误: {e}")
        messagebox.showerror("错误", f"程序运行错误: {e}")
    finally:
        print("程序结束")

if __name__ == "__main__":
    main()