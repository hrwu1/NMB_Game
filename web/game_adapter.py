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
        state = {
            'current_player': self.game.current_player_index,
            'dice_value': self.game.dice_value,
            'phase': self.game.move_phase,
            'current_floor': self.game.current_floor,
            'selecting_start': self.game.selecting_start,
            'moved': getattr(self.game, 'player_moved', False),
            'players': []
        }
        
        # 添加玩家信息
        for i, player in enumerate(self.game.players):
            # 打印每个玩家的位置信息，帮助调试
            print(f"玩家{i+1} {player.name} 的位置: {player.pos}, 楼层: {player.floor}")
            
            # 将Python的None转换为null，以便在前端能够正确处理
            position = player.pos if player.pos is not None else None
            
            state['players'].append({
                'id': player.id,
                'name': player.name,
                'color': player.color,
                'position': position,
                'floor': player.floor,
                'daze': player.daze
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
        
        # 获取所有楼层的棋盘状态
        for floor in range(1, 6):  # 假设有5个楼层
            tiles = []
            
            # 获取该楼层的所有有效区块
            for x in range(20):  # 假设棋盘大小为20x20
                for y in range(20):
                    status = self.game.tile_system.get_tile_status(x, y, floor)
                    if status:
                        tiles.append({
                            'x': x,
                            'y': y,
                            'status': status
                        })
            
            board['floors'][floor] = tiles
        
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
            
            # 如果已经掷过骰子但还没移动，不允许再次掷骰子
            if self.game.dice_value > 0:
                result['message'] = '本回合已经掷过骰子，请先移动棋子'
                return result
            
            # 如果检查通过，掷骰子
            dice_value = random.randint(1, 6)
            self.game.dice_value = dice_value
            print(f"掷骰子成功，点数为: {dice_value}")
            
            # 如果在这里有物品效果需要修改骰子点数，可以在这里处理
            
            result['success'] = True
            result['message'] = f'掷出了{dice_value}点'
            result['dice_value'] = dice_value
            result['player_index'] = self.game.current_player_index
            
            # 将当前骰子值存储在游戏状态中，确保其他部分能访问
            self.game.dice_value = dice_value
            print(f"游戏状态已更新，当前骰子值: {self.game.dice_value}")
            
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
            # 另外，如果没有掷骰子，也不能移动
            if self.game.dice_value == 0:
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
                    old_pos = self.game.current_player.pos
                    if old_pos:
                        old_x, old_y = old_pos
                        manhattan_distance = abs(x - old_x) + abs(y - old_y)
                        dice_value = self.game.dice_value
                        
                        print(f"移动距离检查: 从({old_x},{old_y})到({x},{y})的曼哈顿距离为{manhattan_distance}, 骰子点数为{dice_value}")
                        
                        if manhattan_distance != dice_value:
                            result['message'] = f'移动距离必须等于骰子点数{dice_value}，当前移动距离为{manhattan_distance}'
                            return result
                    
                    # 检查目标位置是否已被其他玩家占用
                    for player in self.game.players:
                        if player.id != self.game.current_player.id and player.pos == position:
                            result['message'] = '该位置已被其他玩家占用'
                            return result
                    
                    # 设置玩家位置
                    old_pos = self.game.current_player.pos
                    print(f"移动玩家 {self.game.current_player.name} 从 {old_pos} 到 ({x},{y})")
                    
                    # 使用Player类的set_position方法而不是直接赋值
                    self.game.current_player.set_position(x, y)
                    
                    # 标记玩家已移动，为了支持回合结束检查
                    self.game.player_moved = True
                    
                    result['success'] = True
                    result['message'] = '移动成功'
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

            # 如果掷了骰子但还没移动，不允许结束回合
            if self.game.dice_value > 0 and not getattr(self.game, 'player_moved', True):
                result['message'] = '请先移动棋子后再结束回合'
                return result
            
            # 更新到下一个玩家
            current_player_name = self.game.current_player.name
            self.game.current_player_index = (self.game.current_player_index + 1) % self.game.num_players
            self.game.dice_value = 0  # 重置骰子值
            
            # 重置移动状态
            self.game.player_moved = False
            
            result['success'] = True
            result['message'] = f'玩家{current_player_name}的回合结束，轮到玩家{self.game.current_player.name}的回合'
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