# YOLO摸鱼后视镜项目

为了解决摸鱼时总担心后面有没有人的问题，找哈基米（gemini）开发了一个基于python的摸鱼后视镜项目，实时告诉你摄像头里看到几个人。

还能用桌面小浮窗看到具体人在哪里。让你做到摸鱼心里有底。2333333

## 🚀 快速开始（推荐新手）

### 一键启动简化版本
```powershell
# 安装依赖   我在python 3.13.3上可以运行，其他版本没试过
pip install -r requirements.txt

# 直接运行简化版
python single_yolo_mirror.py
```

**简化版特点：**
- ✅ 单文件运行，无需复杂配置
- ✅ CPU模式，兼容性好
- ✅ 即装即用，适合快速体验
- ⚠️ 性能较低，检测速度慢

**性能提升：** 如果追求更高性能，可以自行研究WSL环境配置或使用AI助手修改代码启用GPU加速，详见下方WSL+CUDA版本说明。

---

## 📁 文件结构

```
yolo后视镜/
├── WSL+win/              # GPU 加速版本（需要自行解决环境问题）
│   ├── api_server.py     # WSL 端 FastAPI 服务器
│   ├── windows_client.py # Windows 端摄像头采集和转发服务
│   ├── yolo.py          # 客户端程序（托盘 + 显示）
│   └── start_server.sh  # WSL 端启动脚本
├── simple_yolo_mirror.py # 简化版单文件程序（CPU模式，新手推荐）
├── requirements.txt      # Python 依赖包列表
├── yolov8n.pt           # YOLOv8 预训练模型文件
└── README.md            # 项目说明文档
```

## 🎮 程序说明

### 系统托盘功能

- **托盘图标** - 显示当前检测到的人数
- **右键菜单**：
  - 显示浮窗 - 显示可拖拽的人数浮窗
  - 隐藏浮窗 - 隐藏人数浮窗
  - 显示视频窗口 - 显示实时视频预览（带检测框）
  - 退出 - 关闭程序

### 浮窗操作

- **拖拽移动** - 点击并拖拽浮窗到任意位置
- **半透明显示** - 不影响其他应用的使用
- **实时更新** - 显示最新的人数统计

### 视频预览窗口

- **实时画面** - 显示摄像头采集的实时画面
- **检测框显示** - 红色矩形框标出检测到的人员
- **拖拽移动** - 可拖拽到任意位置
- **右键关闭** - 右键点击关闭窗口

## 🏗️ 系统架构

```
┌─────────────────┐    HTTP API    ┌─────────────────┐    TCP Socket    ┌─────────────────┐
│   WSL/Ubuntu    │ ◄──────────── │   Windows 端    │ ◄──────────────► │    客户端       │
│                 │               │                 │                  │                 │
│ • YOLOv8 模型   │               │ • 摄像头采集    │                  │ • 系统托盘      │
│ • FastAPI 服务  │               │ • 图像处理      │                  │ • 浮窗显示      │
│ • GPU 加速      │               │ • TCP 服务器    │                  │ • 视频预览      │
└─────────────────┘               └─────────────────┘                  └─────────────────┘
```
## ⚙️ 配置说明

### 1. WSL + CUDA 环境配置

**注意：** `WSL+win` 文件夹中的代码是为了使用 GPU 加速而设计的。WSL 环境下安装 CUDA 更加便捷，能够充分利用 GPU 性能进行 YOLO 推理加速。

- **推荐用户：** 熟悉 CUDA 环境配置的用户
- **安装建议：** 可以结合 AI 助手（如 ChatGPT、Claude 等）来协助安装和配置 WSL + CUDA 环境
- **性能优势：** GPU 加速可显著提升检测速度和响应性能

### 2. 网络配置

在 `WSL+win/windows_client.py` 中修改 WSL IP 地址：

```python
WSL_IP = "172.26.8.96"  # 替换为你的 WSL IP 地址
```

在 `WSL+win/yolo.py` 中修改服务器 IP 地址：

```python
SERVER_IP = "192.168.233.1"  # 替换为你的 Windows IP 地址
```


## 🚀 启动步骤

### 1. 启动 WSL 端 YOLO API 服务

```bash
cd WSL+win
chmod +x start_server.sh
./start_server.sh
```

### 2. 启动 Windows 端服务

```powershell
# 在 WSL+win 目录中执行
cd WSL+win
python windows_client.py
```

### 3. 启动客户端

```powershell
# 在 WSL+win 目录中执行
cd WSL+win
python yolo.py
```


