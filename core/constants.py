import pygame

# 屏幕和界面设置
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
TILE_SIZE = 20

# 游戏地图设置
BOARD_SIZE = 20  # 每层地图总大小 20x20
REGION_SIZE = 4  # 每个区域大小 4x4
MAP_SIZE = 5     # 区域地图大小 5x5
FLOOR_NUM = 11   # 楼层数

# 游戏阶段定义
PHASE_ROLL_DICE = 0    # Roll dice phase
PHASE_PLACE_CARD = 1   # Place card phase
PHASE_ROTATE_PATH = 2  # Rotate path phase
PHASE_MOVE = 3         # Move phase
PHASE_USE_TRANSPORT = 4 # Use transport phase
PHASE_SELECT_REGION = 5 # Select region phase
PHASE_SELECT_END = 6   # Select end phase

# 玩家颜色
PLAYER_COLORS = [
    (255, 0, 0),    # Red
    (0, 0, 255),    # Blue
    (0, 255, 0),    # Green
    (255, 255, 0),  # Yellow
    (255, 0, 255),  # Magenta
    (0, 255, 255)   # Cyan
]

# 游戏状态参数
MOVES_NUM = 0
LOOP_NUM = 0
EXIT = (-1, (-1, -1))  # 出口位置 (楼层, (x, y))
LOOP_NODES = [4, 8, 12]  # 循环节点
WINNER = -1  # 获胜玩家编号

# 每层特征 - 区域可放置配置
FLOOR_CONFIG = [
    # Each floor has a 5x5 grid of regions, represented by 0/1
    # 0 means region is blocked, 1 means region is allowed
    # First floor (0)
    [[1, 1, 1, 1, 1],
     [1, 1, 1, 1, 1],
     [1, 1, 1, 1, 1],
     [1, 1, 1, 1, 1],
     [1, 1, 1, 1, 1]],
    
    # Add configurations for other floors...
    # For simplicity, all other floors have the same configuration
    # In a real game, you might want to design different layouts for each floor
]

# Fill in the other floors with the same configuration
for i in range(1, FLOOR_NUM):
    FLOOR_CONFIG.append(FLOOR_CONFIG[0])

# 游戏阶段定义
PHASE_PREVIEW = 0       # 预览层数
PHASE_SELECT_REGION = 1 # 选择区域
PHASE_ROTATE_PATH = 2   # 旋转路径
PHASE_SELECT_END = 3    # 选择终点
PHASE_USE_TRANSPORT = 4 # 使用运输工具(楼梯、电梯) 