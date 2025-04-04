from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, rooms
import json
import random
import uuid
import os
import traceback
import sys

# 添加项目根目录到 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

# 现在可以正确导入 core 模块了
from core.game import Game
from web.game_adapter import GameAdapter
import time

# 获取当前文件所在目录的绝对路径
template_dir = os.path.join(current_dir, 'templates')
static_dir = os.path.join(current_dir, 'static')

app = Flask(__name__, 
            template_folder=template_dir,
            static_folder=static_dir)
app.config['SECRET_KEY'] = 'monopoly-game-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# 存储活跃游戏的字典 {game_id: GameAdapter对象}
games = {}

def get_game_id():
    """从会话或URL参数中获取游戏ID"""
    game_id = session.get('game_id')
    if not game_id:
        # 尝试从请求参数中获取
        game_id = request.args.get('game_id')
    
    # 验证游戏ID是否有效
    if not game_id or game_id not in games:
        return None
    
    return game_id

@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

@app.route('/game/<game_id>')
def game_page(game_id):
    """渲染游戏页面"""
    if game_id not in games:
        return "游戏不存在", 404
    return render_template('game.html', game_id=game_id)

@app.route('/api/create_game', methods=['POST'])
def create_game():
    """创建新游戏"""
    data = request.json
    num_players = data.get('num_players', 2)
    player_names = data.get('player_names', [])
    
    # 生成唯一游戏ID
    game_id = str(uuid.uuid4())
    
    # 创建游戏实例和适配器
    game = Game(num_players, player_names)
    games[game_id] = GameAdapter(game)
    
    return jsonify({
        'game_id': game_id,
        'num_players': num_players,
        'player_names': player_names
    })

# WebSocket事件
@socketio.on('connect')
def handle_connect():
    """处理WebSocket连接"""
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    """处理WebSocket断开连接"""
    print('Client disconnected')

def format_game_state(game_state):
    """格式化游戏状态，确保位置数据被正确序列化为JSON
    
    Args:
        game_state: 原始游戏状态字典
        
    Returns:
        格式化后的游戏状态字典
    """
    # 深度复制状态以避免修改原始数据
    state = dict(game_state)
    
    # 确保selecting_start是布尔类型
    if 'selecting_start' in state:
        # 强制转换为布尔值
        state['selecting_start'] = bool(state['selecting_start'])
        print(f"格式化selecting_start字段: {state['selecting_start']}, 类型: {type(state['selecting_start'])}")
    
    # 确保dice_value存在且为整数
    if 'dice_value' in state:
        state['dice_value'] = int(state['dice_value']) if state['dice_value'] is not None else 0
        print(f"格式化dice_value字段: {state['dice_value']}, 类型: {type(state['dice_value'])}")
    else:
        state['dice_value'] = 0
        print(f"添加缺失的dice_value字段，设为默认值0")
        
    # 确保moved字段存在
    if 'moved' not in state:
        state['moved'] = False
        print(f"添加缺失的moved字段，设为默认值False")
    else:
        state['moved'] = bool(state['moved'])
        
    # 修改位置数据格式，确保位置被正确传递
    if 'players' in state:
        for i, player in enumerate(state['players']):
            # 处理玩家位置
            if player['position'] is not None:
                print(f"处理玩家{player['id']+1}的位置: {player['position']}, 类型: {type(player['position'])}")
                if isinstance(player['position'], tuple):
                    player['position'] = list(player['position'])  # 转换元组为列表
                    print(f"转换后的位置: {player['position']}, 类型: {type(player['position'])}")
                    
            # 确保玩家骰子值存在且为整数
            if 'dice_value' in player:
                player['dice_value'] = int(player['dice_value']) if player['dice_value'] is not None else 0
                print(f"格式化玩家{player['id']+1}的骰子值: {player['dice_value']}, 类型: {type(player['dice_value'])}")
            else:
                player['dice_value'] = 0
                print(f"添加玩家{player['id']+1}缺失的dice_value字段，设为默认值0")
                
            # 确保当前玩家的骰子值与游戏状态一致
            if 'current_player' in state and state['current_player'] == i:
                if player['dice_value'] != state['dice_value']:
                    print(f"警告: 当前玩家{player['id']+1}的骰子值({player['dice_value']})与游戏状态中的值({state['dice_value']})不一致，同步为游戏状态值")
                    player['dice_value'] = state['dice_value']
    
    # 处理棋盘数据，确保格式兼容性
    if 'board' in state and 'floors' in state['board']:
        for floor_num, floor_data in state['board']['floors'].items():
            # 检查是否是新格式（字典形式）
            if isinstance(floor_data, dict) and 'tiles' in floor_data:
                # 新格式，已经是字典形式，确保tiles和placed_regions都是列表
                if not isinstance(floor_data['tiles'], list):
                    floor_data['tiles'] = list(floor_data['tiles'])
                
                if 'placed_regions' in floor_data and not isinstance(floor_data['placed_regions'], list):
                    floor_data['placed_regions'] = list(floor_data['placed_regions'])
                
                # 确保每个位置都是列表而不是元组
                for tile in floor_data['tiles']:
                    if 'x' in tile and 'y' in tile:
                        # 位置已经是x/y格式，不需要转换
                        pass
            else:
                # 旧格式，直接是瓦片列表，转换为新格式
                print(f"转换楼层 {floor_num} 的数据从旧格式到新格式")
                tiles = floor_data
                state['board']['floors'][floor_num] = {
                    'tiles': tiles,
                    'placed_regions': []  # 旧格式没有区域信息，提供空列表
                }
    
    # 打印最终格式化的状态摘要
    player_summary = []
    if 'players' in state:
        for player in state['players']:
            player_summary.append({
                'id': player['id'],
                'name': player['name'],
                'position': player['position'],
                'dice_value': player['dice_value']
            })
            
    print(f"格式化后的游戏状态摘要:")
    print(f"- selecting_start: {state.get('selecting_start')}")
    print(f"- dice_value: {state.get('dice_value')}")
    print(f"- current_player: {state.get('current_player')}")
    print(f"- moved: {state.get('moved')}")
    print(f"- 玩家状态: {player_summary}")
    
    return state

@socketio.on('join_game')
def handle_join_game(data):
    """处理加入游戏请求"""
    if 'game_id' not in data:
        emit('error', {'message': '未指定游戏ID'})
        return

    game_id = data['game_id']
    player_id = int(data.get('player_id', 0))
    
    print(f"玩家 {player_id} 请求加入游戏 {game_id}, SID: {request.sid}")
    
    # 检查游戏是否存在
    if game_id not in games:
        emit('error', {'message': f'游戏 {game_id} 不存在'})
        print(f"错误: 游戏 {game_id} 不存在")
        return
    
    # 将游戏ID保存到会话
    session['game_id'] = game_id
    session['player_id'] = player_id
    print(f"已保存会话数据: game_id={game_id}, player_id={player_id}")
    
    # 加入房间
    join_room(game_id)
    print(f"玩家 {player_id} 已加入房间 {game_id}")
    
    # 发送格式化的当前游戏状态
    game_adapter = games[game_id]
    raw_state = game_adapter.get_game_state()
    print(f"原始游戏状态: {raw_state}")
    
    # 检查棋盘数据
    if 'board' in raw_state:
        print(f"棋盘数据: 楼层数={len(raw_state['board'].get('floors', {}))} 瓦片数={sum(len(floor) for floor in raw_state['board'].get('floors', {}).values())}")
    else:
        print(f"警告: 原始游戏状态中没有棋盘数据!")
    
    # 检查玩家数据
    if 'players' in raw_state:
        print(f"玩家数据: 玩家数={len(raw_state['players'])}")
        for i, p in enumerate(raw_state['players']):
            print(f"玩家{i+1}: id={p.get('id')}, name={p.get('name')}, position={p.get('position')}, floor={p.get('floor')}")
    else:
        print(f"警告: 原始游戏状态中没有玩家数据!")
    
    game_state = format_game_state(raw_state)
    
    print(f"向玩家 {player_id} 发送格式化的游戏状态")
    # 调试输出状态中的关键信息
    if 'board' in game_state and 'floors' in game_state['board']:
        print(f"游戏状态中的棋盘数据: {len(game_state['board']['floors'])}个楼层")
        for floor_num, tiles in game_state['board']['floors'].items():
            # 检查tiles是否为字典（新格式）或列表（旧格式）
            if isinstance(tiles, dict) and 'tiles' in tiles:
                tile_list = tiles['tiles']
                regions_list = tiles.get('placed_regions', [])
                print(f"  楼层{floor_num}: {len(tile_list)}个瓦片, {len(regions_list)}个放置区域")
                if len(tile_list) > 0:
                    print(f"  样本瓦片: {tile_list[0]}")
            else:
                # 旧格式：tiles直接是瓦片列表
                print(f"  楼层{floor_num}: {len(tiles)}个瓦片")
                if len(tiles) > 0:
                    print(f"  样本瓦片: {tiles[0]}")
    
    print(f"广播游戏状态到房间: {game_id}")
    emit('game_state', game_state)
    emit('success', {'message': f'已加入游戏 {game_id}', 'player_id': player_id})
    
    # 修复rooms()返回值的使用方式
    room_list = rooms()
    print(f"当前用户所在的房间: {room_list}")
    # 检查Flask-SocketIO的rooms()函数返回的是什么，并安全地获取玩家人数
    try:
        # 根据Flask-SocketIO文档，rooms()应该返回当前客户端所在的房间列表
        if isinstance(room_list, list):
            # 如果rooms()返回的是列表，检查game_id是否在列表中
            if game_id in room_list:
                print(f"房间 {game_id} 中包含当前客户端")
            else:
                print(f"当前客户端不在房间 {game_id} 中")
            # 这里无法获取房间中的客户端数量，只能知道当前客户端所在的房间
            print(f"无法通过rooms()获取房间内的客户端数量")
        elif isinstance(room_list, dict):
            # 如果rooms()返回的是字典，尝试获取game_id的值
            if game_id in room_list:
                print(f"房间 {game_id} 的连接数: {len(room_list[game_id])}")
            else:
                print(f"房间字典中没有 {game_id}")
        else:
            print(f"rooms()返回了未知类型: {type(room_list)}")
    except Exception as e:
        print(f"尝试获取房间信息时出错: {str(e)}")
        traceback.print_exc()

@socketio.on('roll_dice')
def handle_roll_dice(data=None):
    """处理掷骰子事件"""
    game_id = get_game_id()
    if not game_id:
        emit('error', {'message': '未找到游戏ID'})
        return

    sid = request.sid
    print(f"收到掷骰子请求 - 连接ID: {sid}, 游戏ID: {game_id}")
    
    game_adapter = games[game_id]
    print(f"[DEBUG] 掷骰子前的游戏状态: {game_adapter.get_game_state()}")
    
    # 记录当前玩家
    current_player_id = game_adapter.game.current_player
    
    # 检查current_player_id的类型
    if hasattr(current_player_id, 'id'):
        # 如果current_player_id是Player对象，获取其id属性
        current_player_index = current_player_id.id
        current_player = current_player_id
        print(f"当前玩家是Player对象: id={current_player_index}, name={current_player.name}")
    else:
        # 如果current_player_id是索引值
        current_player_index = current_player_id
        current_player = game_adapter.game.players[current_player_index] if current_player_index is not None else None
        print(f"当前玩家索引: {current_player_index}, 玩家: {current_player.name if current_player else 'None'}")
    
    try:
        # 处理掷骰子事件
        result = game_adapter.handle_event('roll_dice', data or {})
        print(f"掷骰子结果: {result}")
        
        # 检查是否成功
        if not result['success']:
            print(f"掷骰子失败: {result['message']}")
            emit('error', {'message': result['message']})
            return
            
        # 获取骰子值
        dice_value = result['dice_value']
        
        # 检查玩家骰子值同步情况
        if current_player:
            if current_player.dice_value != dice_value:
                print(f"警告: 玩家骰子值不同步! 玩家: {current_player.dice_value}, 游戏: {dice_value}")
                # 尝试修复不同步
                current_player.set_dice_value(dice_value)
                
        # 先广播骰子结果
        print(f"广播骰子结果: {dice_value} 到房间: {game_id}")
        socketio.emit('dice_result', {'dice_value': dice_value}, room=game_id)
        
        # 然后广播格式化的游戏状态
        game_state = format_game_state(game_adapter.get_game_state())
        
        # 确保游戏状态中的骰子值与掷出的值一致
        if game_state['dice_value'] != dice_value:
            print(f"警告: 格式化后的游戏状态中骰子值仍不一致! 修复: {game_state['dice_value']} -> {dice_value}")
            game_state['dice_value'] = dice_value
            
        # 确保当前玩家的骰子值一致
        if 'players' in game_state and current_player_index is not None:
            if game_state['players'][current_player_index]['dice_value'] != dice_value:
                print(f"警告: 格式化后的玩家骰子值仍不一致! 修复: {game_state['players'][current_player_index]['dice_value']} -> {dice_value}")
                game_state['players'][current_player_index]['dice_value'] = dice_value
        
        print(f"广播游戏状态到房间: {game_id}")
        socketio.emit('game_state', game_state, room=game_id)
        
        print(f"广播成功消息")
        emit('success', {'message': f"掷出了 {dice_value} 点"})
        
        print(f"[DEBUG] 掷骰子后的游戏状态: {format_game_state(game_adapter.get_game_state())}")
        
    except Exception as e:
        print(f"掷骰子时发生错误: {str(e)}")
        traceback.print_exc()
        emit('error', {'message': f'掷骰子错误: {str(e)}'})

@socketio.on('move_player')
def handle_move_player(data):
    """处理玩家移动事件"""
    game_id = get_game_id()
    
    if not game_id:
        emit('error', {'message': '游戏不存在'})
        return
    
    game_adapter = games[game_id]
    
    # 获取移动前的游戏状态
    prev_state = format_game_state(game_adapter.get_game_state())
    print(f"移动前游戏状态: 选择起始={prev_state['selecting_start']}")
    
    # 处理移动事件
    result = game_adapter.handle_event('move_player', data)
    
    if result['success']:
        # 获取移动后的游戏状态
        post_state = format_game_state(game_adapter.get_game_state())
        print(f"移动后游戏状态: 选择起始={post_state['selecting_start']}")
        
        # 检查是否有初始位置选择阶段结束的标志
        phase_changed = prev_state['selecting_start'] and not post_state['selecting_start']
        if phase_changed:
            print("检测到游戏阶段已从初始位置选择转为正常游戏")
        
        # 检查是否有回合变更信息，比如初始位置选择完成或移动到下一个玩家
        if 'current_player' in result:
            print(f"玩家回合已变更为: {result['current_player']}")
        
        # 获取格式化的游戏状态
        game_state = format_game_state(game_adapter.get_game_state())
        
        # 广播更新后的游戏状态给所有玩家
        socketio.emit('game_state', game_state, room=game_id)
        
        # 如果位置设置成功，发送成功消息，将所有result内容都传递给客户端
        if 'message' in result:
            # 传递完整的结果信息给客户端
            success_data = {'message': result['message']}
            
            # 添加额外的位置设置数据
            if 'position_set' in result:
                for key in ['position_set', 'player_name', 'player_position', 'selecting_start', 'current_player']:
                    if key in result:
                        success_data[key] = result[key]
            
            # 如果游戏阶段刚刚转换，添加特殊标记
            if phase_changed:
                success_data['phase_changed'] = True
                        
            emit('success', success_data)
    else:
        emit('error', {'message': result.get('message', '移动失败')})

@socketio.on('change_floor')
def handle_change_floor(data):
    """处理更改楼层的请求"""
    print(f"处理更改楼层事件: {data}")
    
    # 获取当前会话信息
    session_id = request.sid
    game_id = session.get('game_id')
    
    if not game_id:
        emit('error', {'message': '未加入游戏'})
        return
    
    # 检查请求中是否包含楼层信息
    if 'floor' not in data:
        emit('error', {'message': '缺少楼层信息'})
        return
    
    floor = data['floor']
    if not isinstance(floor, int) or floor < 1 or floor > 5:
        emit('error', {'message': '无效的楼层值，楼层应为1-5之间的整数'})
        return
    
    emit('success', {'message': f'已切换到第{floor}层'})
    
    # 向所有玩家广播楼层变化
    socketio.emit('floor_change', {'floor': floor}, room=game_id)

@socketio.on('rotate_card')
def handle_rotate_card():
    """处理旋转卡片的请求"""
    print("处理旋转卡片事件")
    
    # 获取当前会话信息
    session_id = request.sid
    game_id = session.get('game_id')
    player_id = session.get('player_id')
    
    if not game_id:
        emit('error', {'message': '未加入游戏'})
        return
    
    if player_id is None:
        emit('error', {'message': '玩家ID未设置'})
        return
    
    try:
        # 获取游戏适配器
        game_adapter = games.get(game_id)
        if not game_adapter:
            emit('error', {'message': '游戏不存在'})
            return
        
        # 检查是否是当前玩家的回合
        current_player_id = game_adapter.game.current_player
        
        # 检查current_player_id的类型
        if hasattr(current_player_id, 'id'):
            # 如果current_player_id是Player对象，获取其id属性
            current_player_index = current_player_id.id
        else:
            # 如果current_player_id是索引值
            current_player_index = current_player_id
            
        if current_player_index != player_id:
            emit('error', {'message': '不是你的回合'})
            return
        
        # 执行旋转卡片的逻辑
        # 注意：这里只是模拟旋转卡片，实际实现需要根据游戏规则进行调整
        result = {'success': True, 'message': '卡片已旋转'}
        
        emit('success', {'message': '卡片已旋转'})
        
        # 向所有玩家广播卡片旋转事件
        socketio.emit('card_rotated', {
            'player_id': player_id,
            'player_name': game_adapter.game.players[player_id].name,
            'timestamp': time.time()
        }, room=game_id)
        
    except Exception as e:
        print(f"旋转卡片时出错: {e}")
        emit('error', {'message': f'旋转卡片时出错: {str(e)}'})

@socketio.on('place_card')
def handle_place_card(data):
    """处理放置卡片事件"""
    game_id = get_game_id()
    
    if not game_id:
        emit('error', {'message': '游戏不存在'})
        return
    
    game_adapter = games[game_id]
    result = game_adapter.handle_event('place_card', data)
    
    if result['success']:
        # 广播更新后的游戏状态
        game_state = format_game_state(game_adapter.get_game_state())
        socketio.emit('game_state', game_state, room=game_id)
    else:
        emit('error', {'message': result.get('message', '放置失败')})

@socketio.on('change_daze')
def handle_change_daze(data):
    """处理更改迷惑值的请求"""
    print(f"处理更改迷惑值事件: {data}")
    
    # 获取当前会话信息
    session_id = request.sid
    game_id = session.get('game_id')
    player_id = session.get('player_id')
    
    if not game_id:
        emit('error', {'message': '未加入游戏'})
        return
    
    if player_id is None:
        emit('error', {'message': '玩家ID未设置'})
        return
    
    # 检查请求中是否包含迷惑值变化
    if 'change' not in data:
        emit('error', {'message': '缺少迷惑值变化信息'})
        return
    
    change = data['change']
    if not isinstance(change, int):
        emit('error', {'message': '迷惑值变化必须是整数'})
        return
    
    try:
        # 获取游戏适配器
        game_adapter = games.get(game_id)
        if not game_adapter:
            emit('error', {'message': '游戏不存在'})
            return
        
        # 检查是否是当前玩家的回合
        current_player_id = game_adapter.game.current_player
        
        # 检查current_player_id的类型
        if hasattr(current_player_id, 'id'):
            # 如果current_player_id是Player对象，获取其id属性
            current_player_index = current_player_id.id
        else:
            # 如果current_player_id是索引值
            current_player_index = current_player_id
            
        if current_player_index != player_id:
            emit('error', {'message': '不是你的回合'})
            return
        
        # 获取当前玩家
        current_player = game_adapter.game.players[player_id]
        
        # 更新迷惑值（假设Player类有一个daze属性）
        if not hasattr(current_player, 'daze'):
            current_player.daze = 0
        
        current_player.daze = max(0, current_player.daze + change)
        max_daze = 10  # 假设最大迷惑值为10
        current_player.daze = min(max_daze, current_player.daze)
        
        daze_message = '增加' if change > 0 else '减少'
        emit('success', {'message': f'迷惑值{daze_message}至{current_player.daze}'})
        
        # 更新游戏状态并广播
        game_state = format_game_state(game_adapter.get_game_state())
        socketio.emit('game_state', game_state, room=game_id)
        
        # 向所有玩家广播迷惑值变化事件
        socketio.emit('daze_changed', {
            'player_id': player_id,
            'player_name': current_player.name,
            'daze': current_player.daze,
            'change': change,
            'timestamp': time.time()
        }, room=game_id)
        
    except Exception as e:
        print(f"更改迷惑值时出错: {e}")
        emit('error', {'message': f'更改迷惑值时出错: {str(e)}'})

@socketio.on('end_turn')
def handle_end_turn(data=None):
    """处理结束回合事件"""
    game_id = get_game_id()
    player_id = session.get('player_id')
    
    if not game_id:
        emit('error', {'message': '游戏不存在'})
        return
    
    if player_id is None:
        emit('error', {'message': '玩家ID未设置'})
        return
    
    # 确保player_id是整数类型
    player_id = int(player_id)
    print(f"玩家 {player_id} 尝试结束回合")
    
    game_adapter = games[game_id]
    
    # 详细打印游戏状态信息用于调试
    game_state = game_adapter.get_game_state()
    print(f"当前游戏状态: current_player_index={game_state.get('current_player_index', 'unknown')}, current_player={game_state.get('current_player', 'unknown')}")
    
    # 获取当前玩家ID - 确保从游戏状态中获取current_player字段，并将其转换为整数
    current_player_id = int(game_state.get('current_player', 0))
    print(f"当前玩家ID (从游戏状态): {current_player_id}, 类型: {type(current_player_id)}")
    print(f"请求玩家ID: {player_id}, 类型: {type(player_id)}")
    
    # 直接使用游戏状态中的current_player与请求玩家ID比较
    if current_player_id != player_id:
        # 打印所有玩家信息用于调试
        for i, player in enumerate(game_adapter.game.players):
            print(f"玩家{i}: id={player.id}, name={player.name}")
            
        emit('error', {'message': f'不是你的回合，当前回合玩家ID: {current_player_id}'})
        print(f"玩家 {player_id} 尝试结束玩家 {current_player_id} 的回合，操作被拒绝")
        return
    
    print(f"验证通过，玩家 {player_id} 正在结束自己的回合")
    result = game_adapter.handle_event('end_turn', data)
    
    if result['success']:
        # 广播更新后的游戏状态
        game_state = format_game_state(game_adapter.get_game_state())
        print(f"回合结束后的游戏状态: current_player={game_state.get('current_player')}")
        socketio.emit('game_state', game_state, room=game_id)
        
        if 'message' in result:
            emit('success', {'message': result['message']})
    else:
        emit('error', {'message': result.get('message', '结束回合失败')})

@socketio.on('custom_event')
def handle_custom_event(data):
    """处理自定义事件，例如强制开始游戏"""
    print(f"收到自定义事件: {data}")
    
    # 获取当前会话信息
    session_id = request.sid
    game_id = session.get('game_id')
    
    if not game_id:
        emit('error', {'message': '未加入游戏'})
        return
    
    # 检查事件类型
    if 'type' not in data:
        emit('error', {'message': '缺少事件类型'})
        return
    
    event_type = data['type']
    
    try:
        # 获取游戏适配器
        game_adapter = games.get(game_id)
        if not game_adapter:
            emit('error', {'message': '游戏不存在'})
            return
        
        # 处理特定类型的自定义事件
        if event_type == 'all_positions_set':
            # 强制设置所有玩家已选择起始位置
            game_adapter.game.selecting_start = False
            message = data.get('message', '所有玩家已设置起始位置')
            
            emit('success', {'message': message})
            
            # 更新游戏状态并广播
            game_state = format_game_state(game_adapter.get_game_state())
            socketio.emit('game_state', game_state, room=game_id)
            
            socketio.emit('notification', {
                'message': message,
                'type': 'info',
                'timestamp': time.time()
            }, room=game_id)
        else:
            emit('error', {'message': f'未知的事件类型: {event_type}'})
    
    except Exception as e:
        print(f"处理自定义事件时出错: {e}")
        emit('error', {'message': f'处理自定义事件时出错: {str(e)}'})

@app.route('/test')
def test_page():
    """渲染测试页面"""
    return render_template('test.html')

@app.route('/test/<game_id>')
def test_game_page(game_id):
    """渲染带游戏ID的测试页面"""
    if game_id not in games:
        return "游戏不存在", 404
    return render_template('test.html', game_id=game_id)

@app.route('/api/game/<game_id>/status')
def get_game_status(game_id):
    """获取游戏状态信息"""
    if game_id not in games:
        return jsonify({
            'error': '游戏不存在',
            'game_id': game_id,
            'exists': False,
            'active_games': list(games.keys())
        }), 404
    
    game_adapter = games[game_id]
    raw_state = game_adapter.get_game_state()
    
    # 准备轻量级状态摘要
    status = {
        'exists': True,
        'game_id': game_id,
        'selecting_start': raw_state.get('selecting_start', False),
        'current_player': raw_state.get('current_player', 0),
        'num_players': len(raw_state.get('players', [])),
        'has_board': 'board' in raw_state and 'floors' in raw_state['board'],
        'current_floor': raw_state.get('current_floor', 1)
    }
    
    # 如果有棋盘数据，添加摘要
    if status['has_board']:
        floors_data = {}
        for floor_num, tiles in raw_state['board']['floors'].items():
            floors_data[floor_num] = len(tiles)
        status['floors'] = floors_data
    
    # 添加玩家摘要信息
    if 'players' in raw_state:
        players_summary = []
        for player in raw_state['players']:
            players_summary.append({
                'id': player.get('id'),
                'name': player.get('name'),
                'has_position': player.get('position') is not None,
                'floor': player.get('floor', 1)
            })
        status['players'] = players_summary
    
    return jsonify(status)

@app.route('/api/health')
def health_check():
    """API健康检查"""
    return jsonify({
        'status': 'ok',
        'active_games': len(games),
        'game_ids': list(games.keys())
    })

if __name__ == '__main__':
    socketio.run(app, debug=True, host='127.0.0.1', port=5000) 