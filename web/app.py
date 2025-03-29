from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import json
import random
import uuid
import os
from core.game import Game
from web.game_adapter import GameAdapter

# 获取当前文件所在目录的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(current_dir, 'templates')
static_dir = os.path.join(current_dir, 'static')

app = Flask(__name__, 
            template_folder=template_dir,
            static_folder=static_dir)
app.config['SECRET_KEY'] = 'monopoly-game-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# 存储活跃游戏的字典 {game_id: GameAdapter对象}
games = {}

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
    
    # 修改位置数据格式，确保位置被正确传递
    if 'players' in state:
        for player in state['players']:
            if player['position'] is not None:
                print(f"处理玩家{player['id']+1}的位置: {player['position']}, 类型: {type(player['position'])}")
                if isinstance(player['position'], tuple):
                    player['position'] = list(player['position'])  # 转换元组为列表
                    print(f"转换后的位置: {player['position']}, 类型: {type(player['position'])}")
    
    return state

@socketio.on('join_game')
def handle_join_game(data):
    """处理玩家加入游戏"""
    game_id = data.get('game_id')
    player_id = data.get('player_id', 0)
    
    print(f"玩家请求加入游戏{game_id}，玩家ID={player_id}")
    
    if game_id not in games:
        print(f"游戏{game_id}不存在")
        emit('error', {'message': '游戏不存在'})
        return
    
    # 将用户添加到游戏房间
    session['game_id'] = game_id
    session['player_id'] = player_id
    print(f"玩家已加入游戏: game_id={game_id}, player_id={player_id}")
    
    # 获取并格式化游戏状态
    game_state = format_game_state(games[game_id].get_game_state())
    
    # 发送游戏初始状态
    emit('game_state', game_state)
    print(f"已发送游戏状态给玩家")

@socketio.on('roll_dice')
def handle_roll_dice(data=None):
    """处理掷骰子事件"""
    game_id = session.get('game_id')
    print(f"收到掷骰子请求, 游戏ID: {game_id}, 数据: {data}")
    
    if not game_id or game_id not in games:
        print(f"错误: 游戏 {game_id} 不存在")
        emit('error', {'message': '游戏不存在'})
        return
    
    game_adapter = games[game_id]
    # 获取游戏当前状态，用于调试
    current_state = format_game_state(game_adapter.get_game_state())
    print(f"掷骰子前游戏状态: 当前玩家={current_state['current_player']}, 选择起始={current_state['selecting_start']}, 骰子值={current_state['dice_value']}")
    
    # 检查是否需要强制开始游戏
    force_start = False
    if data and 'force_start' in data:
        force_start = data['force_start']
        print(f"检测到强制开始请求: force_start={force_start}")
    
    # 使用参数调用handle_event
    result = game_adapter.handle_event('roll_dice', {'force_start': force_start} if force_start else None)
    print(f"掷骰子处理结果: {result}")
    
    if result.get('success', False):
        # 确保有骰子值
        if 'dice_value' not in result:
            print("警告: 处理结果中没有骰子值")
            emit('error', {'message': '服务器处理出错，骰子结果丢失'})
            return
        
        dice_value = result['dice_value']
        print(f"成功掷出了 {dice_value} 点")
        
        # 广播掷骰子结果
        dice_data = {
            'player_index': game_adapter.game.current_player_index,
            'dice_value': dice_value
        }
        print(f"广播掷骰子结果: {dice_data}")
        socketio.emit('dice_result', dice_data, room=game_id)
        
        # 更新游戏状态
        game_state = format_game_state(game_adapter.get_game_state())
        print(f"掷骰子后游戏状态: 当前玩家={game_state['current_player']}, 选择起始={game_state['selecting_start']}, 骰子值={game_state['dice_value']}")
        socketio.emit('game_state', game_state, room=game_id)
        
        # 发送成功消息
        emit('success', {'message': f"掷出了 {dice_value} 点"})
    else:
        print(f"掷骰子失败: {result.get('message', '未知错误')}")
        emit('error', {'message': result.get('message', '掷骰子失败')})

@socketio.on('move_player')
def handle_move_player(data):
    """处理玩家移动事件"""
    game_id = session.get('game_id')
    
    if not game_id or game_id not in games:
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
    """处理楼层变更事件"""
    game_id = session.get('game_id')
    
    if not game_id or game_id not in games:
        emit('error', {'message': '游戏不存在'})
        return
    
    game_adapter = games[game_id]
    result = game_adapter.handle_event('change_floor', data)
    
    # 不需要广播状态，因为这只是UI状态变化

@socketio.on('rotate_card')
def handle_rotate_card():
    """处理旋转卡片事件"""
    game_id = session.get('game_id')
    
    if not game_id or game_id not in games:
        emit('error', {'message': '游戏不存在'})
        return
    
    game_adapter = games[game_id]
    result = game_adapter.handle_event('rotate_card')
    
    if result['success']:
        # 广播更新后的游戏状态
        game_state = format_game_state(game_adapter.get_game_state())
        socketio.emit('game_state', game_state, room=game_id)
    else:
        emit('error', {'message': result.get('message', '旋转失败')})

@socketio.on('place_card')
def handle_place_card(data):
    """处理放置卡片事件"""
    game_id = session.get('game_id')
    
    if not game_id or game_id not in games:
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
    """处理迷惑值变更事件"""
    game_id = session.get('game_id')
    
    if not game_id or game_id not in games:
        emit('error', {'message': '游戏不存在'})
        return
    
    game_adapter = games[game_id]
    result = game_adapter.handle_event('change_daze', data)
    
    if result['success']:
        # 广播更新后的游戏状态
        game_state = format_game_state(game_adapter.get_game_state())
        socketio.emit('game_state', game_state, room=game_id)
    else:
        emit('error', {'message': result.get('message', '迷惑值变更失败')})

@socketio.on('end_turn')
def handle_end_turn():
    """处理结束回合事件"""
    game_id = session.get('game_id')
    
    if not game_id or game_id not in games:
        emit('error', {'message': '游戏不存在'})
        return
    
    game_adapter = games[game_id]
    result = game_adapter.handle_event('end_turn')
    
    if result['success']:
        # 广播更新后的游戏状态
        game_state = format_game_state(game_adapter.get_game_state())
        socketio.emit('game_state', game_state, room=game_id)
        
        if 'message' in result:
            emit('success', {'message': result['message']})
    else:
        emit('error', {'message': result.get('message', '结束回合失败')})

@socketio.on('custom_event')
def handle_custom_event(data):
    """处理自定义事件
    
    Args:
        data: 事件数据
    """
    print(f"收到自定义事件: {data}")
    
    event_type = data.get('type')
    session_id = request.sid
    game_id = session.get('game_id')
    
    if event_type == 'all_positions_set':
        # 处理所有玩家已设置初始位置的事件
        print("收到所有玩家已设置初始位置的通知，同步游戏状态")
        
        # 获取游戏实例
        if not game_id or game_id not in games:
            emit('error', {'message': '游戏未初始化'})
            return
            
        game_adapter = games[game_id]
        
        # 更新游戏状态
        if game_adapter.game.selecting_start:
            game_adapter.game.selecting_start = False
            print("强制更新游戏状态：结束初始位置选择阶段")
            
            # 广播更新的游戏状态
            emit('success', {
                'message': '所有玩家已选择初始位置，游戏正式开始！',
                'selecting_start': False
            }, broadcast=True)
            
            # 广播更新的游戏状态
            updated_state = format_game_state(game_adapter.get_game_state())
            socketio.emit('game_state', updated_state, room=game_id)
    
    # 返回确认信息
    emit('success', {'message': f'自定义事件 {event_type} 已处理'})

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

if __name__ == '__main__':
    socketio.run(app, debug=True, host='127.0.0.1', port=5000) 