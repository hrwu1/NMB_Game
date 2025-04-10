# 新主一隅 - Web版

这是一个使用Flask和HTML/JavaScript实现的新主一隅游戏Web版本。游戏后端使用Python和Pygame实现核心逻辑，前端使用HTML5、CSS和JavaScript实现用户界面。

## 功能特点

- 支持2-6名玩家
- 美观的Web界面
- 实时游戏更新（使用WebSocket）
- 保留了原始Pygame版本的所有游戏功能

## 技术栈

- **后端**：
  - Python 3.6+
  - Flask
  - Flask-SocketIO
  - Pygame (无窗口模式)

- **前端**：
  - HTML5
  - CSS3
  - JavaScript
  - Socket.IO客户端

## 项目结构

```
NMB_Game/
│
├── core/                 # 游戏核心逻辑
│   ├── constants.py      # 游戏常量定义
│   ├── game.py           # 主游戏类
│   ├── path_tile_system.py  # 路径系统
│   ├── player.py         # 玩家类
│   └── ui.py             # 用户界面组件
│
├── web/                  # Web应用代码
│   ├── app.py            # Flask应用主文件
│   ├── game_adapter.py   # 游戏适配器
│   ├── static/           # 静态资源
│   │   ├── css/          # 样式表
│   │   └── js/           # JavaScript文件
│   └── templates/        # HTML模板
│       ├── index.html    # 主页
│       └── game.html     # 游戏页
│
├── requirements.txt      # 项目依赖
├── run.py                # 启动脚本
└── README.md             # 项目说明
```

## 安装步骤

1. 确保安装了Python 3.6或更高版本

2. 克隆仓库：
   ```
   git clone <仓库URL>
   cd NMB_Game
   ```

3. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

4. 运行Web服务器：
   ```
   python run.py
   ```

5. 打开浏览器访问：
   ```
   http://localhost:5000
   ```

## 配置选项

可以通过环境变量设置以下配置：

- `DEBUG`: 是否启用调试模式 (True/False，默认True)
- `HOST`: 监听主机地址 (默认127.0.0.1，设为0.0.0.0允许公网访问)
- `PORT`: 监听端口 (默认5000)

示例：
```
# Windows
set HOST=0.0.0.0
python run.py

# Linux/Mac
HOST=0.0.0.0 python run.py
```

## 游戏说明

1. 在主页上选择玩家数量（2-6名）并输入每位玩家的名称
2. 点击"开始游戏"按钮创建新游戏
3. 游戏页面包含以下控制：
   - 掷骰子按钮
   - 楼层控制按钮（向上/向下）
   - 旋转和放置卡片按钮
   - 迷惑值控制按钮

## 架构说明

该项目使用了"适配器模式"将原始的Pygame游戏转换为Web应用：

1. **web/app.py**: Flask应用和WebSocket服务器
2. **web/game_adapter.py**: 适配器类，将Game类适配到Web环境
3. **web/templates/**: 包含HTML模板文件
4. **web/static/**: 包含CSS和JavaScript文件
5. **core/**: 包含原始游戏核心逻辑

## 扩展与改进

- 添加多房间支持
- 实现用户认证系统
- 添加游戏存档功能
- 完善移动设备支持
- 添加游戏声音效果

## 贡献

欢迎提交问题和拉取请求！

## 许可证

[指定许可证类型]
