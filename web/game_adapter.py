import pygame
from pygame.locals import *
import sys
import os
import random

# 添加core目录到Python模块搜索路径
core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core')
if core_path not in sys.path:
    sys.path.append(core_path)

from core.game import Game

class GameAdapter:
    """游戏适配器，用于将Pygame游戏适配到Web环境"""
    
    def __init__(self, game):
        """初始化适配器
        
        Args:
            game: Game对象
        """
        self.game = game
        self.initialized = False
        
        # 确保当前楼层设置为1
        self.game.current_floor = 1
        print(f"当前楼层已设置为: {self.game.current_floor}")
        
        # 初始化Pygame (无窗口模式)
        if not pygame.get_init():
            pygame.init()
        pygame.display.set_mode((1, 1), pygame.NOFRAME)
    
    def get_game_state(self):
        """获取游戏状态以JSON格式返回
        
        Returns:
            游戏状态字典
        """
        # 确保Game对象和当前玩家的骰子值同步
        current_player = self.game.players[self.game.current_player_index]
        if self.game.dice_value != current_player.dice_value:
            print(f"警告: 游戏骰子值与玩家骰子值不一致，强制同步 - 游戏: {self.game.dice_value}, 玩家: {current_player.dice_value}")
            # 优先使用玩家的骰子值
            if current_player.dice_value > 0:
                self.game.dice_value = current_player.dice_value
            else:
                current_player.set_dice_value(self.game.dice_value)
        
        # 确保使用正确的骰子值
        dice_value = current_player.dice_value if current_player.dice_value > 0 else self.game.dice_value
        
        state = {
            'current_player': self.game.current_player_index,
            'dice_value': dice_value,  # 使用同步后的骰子值
            'phase': self.game.move_phase,
            'current_floor': self.game.current_floor,
            'selecting_start': self.game.selecting_start,
            'moved': getattr(self.game, 'player_moved', False),
            'players': []
        }
        
        # 添加玩家信息
        for i, player in enumerate(self.game.players):
            # 打印每个玩家的位置信息，帮助调试
            print(f"玩家{i+1} {player.name} 的位置: {player.pos}, 楼层: {player.floor}, 骰子值: {player.dice_value}")
            
            # 将Python的None转换为null，以便在前端能够正确处理
            position = player.pos if player.pos is not None else None
            
            # 获取玩家骰子值，确保数值类型
            player_dice_value = int(player.dice_value) if player.dice_value is not None else 0
            
            state['players'].append({
                'id': player.id,
                'name': player.name,
                'color': player.color,
                'position': position,
                'floor': player.floor,
                'daze': player.daze,
                'dice_value': player_dice_value  # 确保骰子值为整数
            })
        
        # 添加棋盘信息
        state['board'] = self.get_board_state()
        
        return state
    
    def get_board_state(self):
        """获取棋盘状态
        
        Returns:
            棋盘状态字典
        """
        board = {
            'floors': {}
        }
        
        try:
            print("开始获取棋盘状态...")
            
            # 检查tile_system是否存在并初始化
            if not hasattr(self.game, 'tile_system') or self.game.tile_system is None:
                print("警告: 游戏的tile_system不存在或为空")
                # 尝试初始化tile_system
                self.game.initialize_board()
                if not hasattr(self.game, 'tile_system') or self.game.tile_system is None:
                    print("错误: 无法初始化游戏的tile_system，返回空棋盘")
                    # 如果仍然不存在，创建一个带有简单测试瓦片的棋盘
                    for floor in range(1, 6):
                        test_tiles = []
                        # 创建一个10x10的简单测试棋盘在中央
                        for x in range(5, 15):
                            for y in range(5, 15):
                                # 添加一个简单的格子图案
                                if (x + y) % 2 == 0:
                                    test_tiles.append({
                                        'x': x,
                                        'y': y,
                                        'status': 1
                                    })
                        board['floors'][floor] = test_tiles
                    return board
            
            # 获取所有楼层的棋盘状态
            for floor in range(1, 6):  # 假设有5个楼层
                tiles = []
                tile_count = 0
                
                # 获取该楼层的所有有效区块
                for x in range(20):  # 假设棋盘大小为20x20
                    for y in range(20):
                        try:
                            status = self.game.tile_system.get_tile_status(x, y, floor)
                            if status:
                                tiles.append({
                                    'x': x,
                                    'y': y,
                                    'status': status
                                })
                                tile_count += 1
                        except Exception as e:
                            print(f"获取瓦片状态时出错 - x={x}, y={y}, floor={floor}: {str(e)}")
                
                print(f"楼层 {floor} 包含 {tile_count} 个有效瓦片")
                board['floors'][floor] = tiles
                
            total_tiles = sum(len(tiles) for tiles in board['floors'].values())
            print(f"获取棋盘状态完成 - 总共 {len(board['floors'])} 个楼层, {total_tiles} 个瓦片")
            
        except Exception as e:
            print(f"获取棋盘状态时发生异常: {str(e)}")
            # 返回一个最小的有效棋盘
            for floor in range(1, 6):
                board['floors'][floor] = [
                    {'x': 10, 'y': 10, 'status': 1}, 
                    {'x': 11, 'y': 10, 'status': 1},
                    {'x': 10, 'y': 11, 'status': 1}
                ]
        
        return board
    
    def handle_event(self, event_type, data=None):
        """处理前端事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            
        Returns:
            处理结果
        """
        result = {
            'success': False,
            'message': '',
        }
        
        if event_type == 'roll_dice':
            # 处理掷骰子事件
            print(f"收到掷骰子请求，当前游戏状态: selecting_start={self.game.selecting_start}, dice_value={self.game.dice_value}")
            
            # 获取强制开始参数（前端处理选择初始位置完成但后端未更新的情况）
            force_start = False
            if data and 'force_start' in data:
                force_start = data['force_start']
            
            if self.game.selecting_start and not force_start:
                result['message'] = '所有玩家必须先选择初始位置'
                return result
            
            # 如果强制开始，则结束初始位置选择
            if force_start and self.game.selecting_start:
                # 检查是否所有玩家都有位置，如果有玩家没有位置，则强制设置一个随机位置
                all_positioned = True
                for player in self.game.players:
                    if player.pos is None:
                        all_positioned = False
                        # 设置随机位置
                        placed = False
                        attempts = 0
                        while not placed and attempts < 100:
                            x, y = random.randint(0, 19), random.randint(0, 19)
                            if self.game.tile_system.get_tile_status(x, y, self.game.current_floor):
                                # 检查是否有其他玩家在这个位置
                                position_taken = False
                                for other_player in self.game.players:
                                    if other_player.pos and other_player.pos == (x, y):
                                        position_taken = True
                                        break
                                
                                if not position_taken:
                                    player.set_position(x, y)
                                    placed = True
                                    print(f"强制为玩家 {player.name} 设置随机初始位置 ({x},{y})")
                            attempts += 1
                
                self.game.selecting_start = False
                self.game.move_phase = 'roll_dice'
                result['message'] = '已强制结束初始位置选择阶段，游戏正式开始！'
                print("强制结束初始位置选择阶段，游戏开始")
            
            # 检查当前玩家是否还有剩余骰子值
            current_player = self.game.players[self.game.current_player_index]
            if current_player.dice_value > 0:
                result['message'] = '本回合已经掷过骰子，请先完成移动'
                return result
            
            # 生成一个新的骰子值
            dice_value = random.randint(1, 6)
            
            # 同步更新当前玩家和游戏的骰子值
            current_player.set_dice_value(dice_value)  # 设置玩家的骰子值
            self.game.dice_value = dice_value  # 保持Game对象状态一致
            
            print(f"掷骰子成功，点数为: {dice_value}, 玩家骰子值为: {current_player.dice_value}, 游戏骰子值为: {self.game.dice_value}")
            
            result['success'] = True
            result['message'] = f'掷出了{dice_value}点'
            result['dice_value'] = dice_value
            result['player_index'] = self.game.current_player_index
            
            return result
        
        elif event_type == 'select_start_position':
            # 检查是否处于起始位置选择阶段
            if not self.game.selecting_start:
                result['message'] = '游戏已经开始，不能再选择初始位置'
                return result
                
            # 验证数据
            if not data or 'position' not in data:
                result['message'] = '缺少位置信息'
                return result
                
            position = data['position']
            # 确保位置是元组
            if isinstance(position, list) and len(position) == 2:
                position = tuple(position)
                
            x, y = position
            # 验证位置是否在棋盘范围内
            if 0 <= x < 20 and 0 <= y < 20:
                # 检查位置是否是白色瓦片（初始位置只能选择白色瓦片）
                tile_status = self.game.tile_system.get_tile_status(x, y, self.game.current_floor)
                
                if tile_status:
                    # 检查位置是否已被其他玩家占用
                    position_taken = False
                    for player in self.game.players:
                        if player.pos and player.pos == (x, y):
                            position_taken = True
                            break
                            
                    if not position_taken:
                        # 设置当前玩家的初始位置
                        current_player = self.game.current_player
                        player_name = current_player.name
                        print(f"设置玩家 {player_name} 的初始位置为 ({x},{y})")
                        
                        # 使用Player类的set_position方法而不是直接赋值
                        current_player.set_position(x, y)
                        
                        # 保存当前玩家索引
                        current_idx = self.game.current_player_index
                        
                        # 移动到下一个玩家或开始游戏
                        current_player_name = self.game.current_player.name
                        self.game.current_player_index = (self.game.current_player_index + 1) % self.game.num_players
                        
                        # 检查是否所有玩家都已选择初始位置
                        all_positioned = True
                        for player in self.game.players:
                            if player.pos is None:
                                all_positioned = False
                                break
                        
                        # 如果所有玩家都已选择位置，则结束初始化阶段
                        if all_positioned:
                            self.game.selecting_start = False
                            self.game.move_phase = 'roll_dice'
                            first_player = self.game.players[self.game.current_player_index]
                            result['message'] = f'所有玩家已选择初始位置，游戏正式开始！请{first_player.name}掷骰子开始游戏！'
                            print("所有玩家已选择初始位置，游戏正式开始")
                        else:
                            next_player = self.game.players[self.game.current_player_index]
                            result['message'] = f'玩家{current_player_name}的初始位置已设置为({x},{y})，请为玩家{next_player.name}选择初始位置'
                            print(f"轮到玩家 {next_player.name} 选择初始位置")
                        
                        result['success'] = True
                        # 不再覆盖上面设置的详细message
                        result['selecting_start'] = self.game.selecting_start
                        result['current_player'] = self.game.current_player_index
                        result['previous_player'] = current_idx
                        result['position_set'] = True
                        result['player_name'] = player_name
                        result['player_position'] = [x, y]  # 使用列表形式，避免JSON序列化问题
                    else:
                        result['message'] = '该位置已被其他玩家占用'
                else:
                    result['message'] = '该位置不是有效的白色瓦片'
            else:
                result['message'] = '位置超出棋盘范围'
        
        elif event_type == 'move_player':
            # 如果没有骰子点数，这是选择初始位置
            if self.game.selecting_start:
                # 注意这部分逻辑和select_start_position事件重复，可以后续重构
                result = self.handle_event('select_start_position', data)
                
                # 额外检查是否所有玩家都设置了初始位置
                all_positioned = True
                for player in self.game.players:
                    if player.pos is None:
                        all_positioned = False
                        break
                
                # 如果所有玩家都选择了初始位置，确保我们结束选择初始位置阶段
                if all_positioned and self.game.selecting_start:
                    self.game.selecting_start = False
                    self.game.move_phase = 'roll_dice'
                    print("检测到所有玩家已有位置，自动结束初始位置选择阶段")
                    
                    # 更新结果消息
                    result['selecting_start'] = False
                    result['message'] = '所有玩家已选择初始位置，游戏正式开始！'
                
                return result
            
            # 如果游戏已经开始，检查是否是当前玩家的回合
            # 另外，如果没有骰子值，也不能移动
            current_player = self.game.players[self.game.current_player_index]
            if current_player.dice_value == 0:
                result['message'] = '请先掷骰子'
                return result
            
            # 处理正常移动
            if not data or 'position' not in data:
                result['message'] = '缺少位置信息'
                return result
                
            position = data['position']
            if isinstance(position, list) and len(position) == 2:
                position = tuple(position)
                
            x, y = position
            # 检查位置是否有效
            if 0 <= x < 20 and 0 <= y < 20:
                # 检查是否是可移动的位置 (这里需要添加路径检查逻辑)
                is_valid_move = self.game.tile_system.get_tile_status(x, y, self.game.current_floor)
                
                if is_valid_move:
                    # 检查移动距离是否符合骰子点数（曼哈顿距离）
                    old_pos = current_player.pos
                    if old_pos:
                        old_x, old_y = old_pos
                        manhattan_distance = abs(x - old_x) + abs(y - old_y)
                        
                        print(f"移动距离检查: 从({old_x},{old_y})到({x},{y})的曼哈顿距离为{manhattan_distance}, 剩余骰子值为{current_player.dice_value}")
                        
                        if manhattan_distance != current_player.dice_value:
                            result['message'] = f'移动距离必须等于剩余骰子值{current_player.dice_value}，当前移动距离为{manhattan_distance}'
                            return result
                    
                    # 检查目标位置是否已被其他玩家占用
                    for player in self.game.players:
                        if player.id != current_player.id and player.pos == position:
                            result['message'] = '该位置已被其他玩家占用'
                            return result
                    
                    # 设置玩家位置
                    old_pos = current_player.pos
                    print(f"移动玩家 {current_player.name} 从 {old_pos} 到 ({x},{y})")
                    
                    # 使用Player类的set_position方法而不是直接赋值
                    current_player.set_position(x, y)
                    
                    # 减少玩家的骰子值
                    current_player.reduce_dice_value(manhattan_distance)
                    
                    # 标记玩家已移动，为了支持回合结束检查
                    self.game.player_moved = True
                    
                    result['success'] = True
                    result['message'] = '移动成功'
                    
                    # 如果玩家还有剩余骰子值，提示可以继续移动
                    if current_player.dice_value > 0:
                        result['message'] = f'移动成功，还可以移动{current_player.dice_value}步'
                else:
                    result['message'] = '无效的移动位置，该位置不可移动'
            else:
                result['message'] = '移动位置超出了棋盘范围'
        
        elif event_type == 'change_floor':
            # 处理改变楼层
            if not data or 'floor' not in data:
                result['message'] = '缺少楼层信息'
                return result
                
            floor = data['floor']
            if 1 <= floor <= 5:  # 假设有5个楼层
                self.game.current_floor = floor
                result['success'] = True
            else:
                result['message'] = '无效的楼层'
        
        elif event_type == 'rotate_card':
            # 处理旋转路径卡片
            self.game.card_rotation = (self.game.card_rotation + 1) % 4
            result['success'] = True
        
        elif event_type == 'place_card':
            # 处理放置路径卡片
            if not data or 'position' not in data:
                result['message'] = '缺少位置信息'
                return result
                
            position = data['position']
            # 将位置数组转换为元组
            if isinstance(position, list) and len(position) == 2:
                position = tuple(position)
                
            x, y = position
            if 0 <= x < 20 and 0 <= y < 20:
                # 放置卡片
                self.game.tile_system.place_path_card(
                    x, y, 
                    self.game.current_floor,
                    self.game.current_card,
                    self.game.card_rotation
                )
                result['success'] = True
            else:
                result['message'] = '无效的放置位置'
        
        elif event_type == 'change_daze':
            # 处理改变迷惑值
            if not data or 'change' not in data:
                result['message'] = '缺少变化值'
                return result
            
            change = data['change']
            player = self.game.current_player
            player.daze = max(0, min(10, player.daze + change))  # 限制在0-10之间
            result['success'] = True

        elif event_type == 'end_turn':
            # 处理结束回合
            # 确保不在初始位置选择阶段
            if self.game.selecting_start:
                result['message'] = '请先为所有玩家选择初始位置'
                return result

            # 如果有剩余骰子值且未移动完，不允许结束回合
            current_player = self.game.players[self.game.current_player_index]
            if current_player.dice_value > 0:
                result['message'] = '请先完成所有移动后再结束回合'
                return result
            
            # 获取当前玩家名称，用于结果消息
            current_player_name = current_player.name
            
            # 切换到下一个玩家
            old_index = self.game.current_player_index
            self.game.current_player_index = (self.game.current_player_index + 1) % self.game.num_players
            
            # 重置当前回合玩家的骰子值
            current_player.set_dice_value(0)
            
            # 重置游戏对象的骰子值
            self.game.dice_value = 0
            
            # 重置移动状态
            self.game.player_moved = False
            
            # 获取新的当前玩家
            new_player = self.game.players[self.game.current_player_index]
            print(f"玩家回合结束: 从 {current_player_name}(idx={old_index}) 切换到 {new_player.name}(idx={self.game.current_player_index})")
            print(f"重置骰子值: 游戏={self.game.dice_value}, 旧玩家={current_player.dice_value}, 新玩家={new_player.dice_value}")
            
            result['success'] = True
            result['message'] = f'玩家{current_player_name}的回合结束，轮到玩家{new_player.name}的回合'
            result['current_player'] = self.game.current_player_index
        
        return result
    
    def simulate_pygame_event(self, event_type, pos=None):
        """模拟Pygame事件
        
        Args:
            event_type: Pygame事件类型
            pos: 鼠标位置
            
        Returns:
            事件处理结果
        """
        # 创建Pygame事件
        if event_type == MOUSEBUTTONDOWN:
            event = pygame.event.Event(MOUSEBUTTONDOWN, {'pos': pos, 'button': 1})
        else:
            event = pygame.event.Event(event_type)
        
        # 发送到Pygame事件队列
        pygame.event.post(event)
        
        # 处理事件
        for event in pygame.event.get():
            if event.type == event_type:
                # 这里我们需要调用Game类中处理该事件的方法
                # 由于原始Game类设计不是为了API调用，这里可能需要改造
                pass
        
        return {'success': True}
    
    def cleanup(self):
        """清理资源"""
        pygame.quit() 