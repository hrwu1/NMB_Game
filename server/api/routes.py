"""
SocketIO event handlers for the NMB Game server.
Handles client connections, game creation, and player actions.
"""

from flask_socketio import emit, join_room, leave_room, disconnect
from flask import request
import logging
import re
import time
from .game_manager import GameManager

# Initialize game manager
game_manager = GameManager()

# Input validation functions
def validate_player_name(name):
    """Validate player name input"""
    if not name or not isinstance(name, str):
        return False, "Player name is required"
    
    name = name.strip()
    if len(name) < 2:
        return False, "Player name must be at least 2 characters"
    if len(name) > 20:
        return False, "Player name must be 20 characters or less"
    if not re.match(r'^[a-zA-Z0-9\s_-]+$', name):
        return False, "Player name can only contain letters, numbers, spaces, hyphens, and underscores"
    
    return True, name

def validate_game_id(game_id):
    """Validate game ID format"""
    if not game_id or not isinstance(game_id, str):
        return False, "Game ID is required"
    
    game_id = game_id.strip().upper()
    if len(game_id) != 6:
        return False, "Game ID must be exactly 6 characters"
    if not re.match(r'^[A-Z0-9]+$', game_id):
        return False, "Game ID can only contain uppercase letters and numbers"
    
    return True, game_id

def emit_error(message, error_code=None):
    """Emit standardized error response"""
    error_data = {
        'message': message,
        'timestamp': time.time()
    }
    if error_code:
        error_data['code'] = error_code
    
    logging.error(f"Socket error ({request.sid}): {message}")
    emit('error', error_data)

def register_socket_handlers(socketio):
    """Register all SocketIO event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        print(f"Client connected: {request.sid}")
        emit('connected', {'message': 'Connected to NMB Game server'})
    
    @socketio.on('get_valid_actions')
    def handle_get_valid_actions(data):
        """Handle request for valid actions"""
        try:
            valid_actions = game_manager.get_valid_actions(request.sid)
            emit('valid_actions', {'actions': valid_actions})
            
        except Exception as e:
            print(f"Error getting valid actions: {e}")
            emit('error', {'message': f'Failed to get valid actions: {str(e)}'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        print(f"Client disconnected: {request.sid}")
        
        # Remove player from their game
        game_id = game_manager.leave_game(request.sid)
        if game_id:
            # Notify other players in the game
            socketio.emit('player_disconnected', {
                'message': 'A player has disconnected',
                'game_id': game_id
            }, room=game_id)
            
            print(f"Player {request.sid} removed from game {game_id}")
        
    @socketio.on('create_game')
    def handle_create_game(data):
        """Handle game creation request"""
        try:
            # Validate input data
            if not data or not isinstance(data, dict):
                emit_error("Invalid request data", "INVALID_DATA")
                return
            
            player_name = data.get('player_name')
            
            # Validate player name
            is_valid, validated_name = validate_player_name(player_name)
            if not is_valid:
                emit_error(validated_name, "INVALID_PLAYER_NAME")
                return
            
            print(f"Creating game for player: {validated_name}")
            
            # Create new game
            game_id = game_manager.create_game(validated_name, request.sid)
            
            if not game_id:
                emit_error("Failed to create game. Server may be at capacity.", "GAME_CREATION_FAILED")
                return
            
            # Join the game room
            join_room(game_id)
            
            # Send response to client
            emit('game_created', {
                'game_id': game_id,
                'player_name': validated_name,
                'message': f'Game {game_id} created successfully',
                'success': True
            })
            
            print(f"Game {game_id} created for player {validated_name}")
            
        except Exception as e:
            print(f"Error creating game: {e}")
            emit_error(f"Server error while creating game: {str(e)}", "SERVER_ERROR")
    
    @socketio.on('join_game')
    def handle_join_game(data):
        """Handle join game request"""
        try:
            # Validate input data
            if not data or not isinstance(data, dict):
                emit_error("Invalid request data", "INVALID_DATA")
                return
            
            game_id = data.get('game_id')
            player_name = data.get('player_name')
            
            # Validate game ID
            is_valid_id, validated_game_id = validate_game_id(game_id)
            if not is_valid_id:
                emit_error(validated_game_id, "INVALID_GAME_ID")
                return
            
            # Validate player name
            is_valid_name, validated_name = validate_player_name(player_name)
            if not is_valid_name:
                emit_error(validated_name, "INVALID_PLAYER_NAME")
                return
            
            print(f"Player {validated_name} attempting to join game {validated_game_id}")
            
            # Check if game exists
            if not game_manager.game_exists(validated_game_id):
                emit_error(f"Game {validated_game_id} does not exist", "GAME_NOT_FOUND")
                return
            
            # Join the game
            success = game_manager.join_game(validated_game_id, validated_name, request.sid)
            
            if success:
                # Join the game room
                join_room(validated_game_id)
                
                # Notify all players in the game
                socketio.emit('player_joined', {
                    'player_name': validated_name,
                    'message': f'{validated_name} joined the game'
                }, room=validated_game_id)
                
                # Send success response to joining player
                emit('game_joined', {
                    'game_id': validated_game_id,
                    'player_name': validated_name,
                    'message': 'Successfully joined the game',
                    'success': True
                })
                
                print(f"Player {validated_name} joined game {validated_game_id}")
                
            else:
                emit_error('Failed to join game. Game may be full or you may already be in it.', "JOIN_FAILED")
                
        except Exception as e:
            print(f"Error joining game: {e}")
            emit_error(f"Server error while joining game: {str(e)}", "SERVER_ERROR")
    
    @socketio.on('start_game')
    def handle_start_game(data):
        """Handle game start request"""
        try:
            game_id = data.get('game_id')
            
            print(f"Start game request for game {game_id} from {request.sid}")
            
            # Start the game
            result = game_manager.start_game(game_id, request.sid)
            
            if result["success"]:
                # Notify all players in the game that it started
                game_state = game_manager.get_game_state(game_id)
                socketio.emit('game_started', {
                    'game_id': game_id,
                    'message': 'Game started!',
                    'game_state': game_state
                }, room=game_id)
                
                print(f"Game {game_id} started successfully")
            else:
                emit('error', {'message': result.get("reason", "Failed to start game")})
                
        except Exception as e:
            print(f"Error starting game: {e}")
            emit('error', {'message': f'Failed to start game: {str(e)}'})
    
    @socketio.on('player_action')
    def handle_player_action(data):
        """Handle player game actions"""
        try:
            action_type = data.get('action_type')
            action_data = data.get('action_data', {})
            
            print(f"Player action received: {action_type} from {request.sid}")
            
            # Process the action through GameManager
            result = game_manager.handle_player_action(request.sid, action_type, action_data)
            
            if result["success"]:
                # Get updated game state
                game_id = game_manager.get_player_game(request.sid)
                if game_id:
                    game_state = game_manager.get_game_state(game_id)
                    
                    # Broadcast updated game state to all players
                    socketio.emit('game_state_update', {
                        'game_id': game_id,
                        'action_result': result,
                        'game_state': game_state
                    }, room=game_id)
                    
                    print(f"Action {action_type} processed successfully for {request.sid}")
                
                # Send success response to acting player
                emit('action_result', result)
            else:
                emit('error', {'message': result.get("reason", "Action failed")})
                
        except Exception as e:
            print(f"Error processing player action: {e}")
            emit('error', {'message': f'Failed to process action: {str(e)}'})
    
    @socketio.on('get_game_state')
    def handle_get_game_state(data):
        """Handle request for current game state"""
        try:
            game_id = data.get('game_id')
            
            # Get game state from manager
            game_state = game_manager.get_game_state(game_id)
            
            if game_state:
                emit('game_state_update', game_state)
            else:
                emit('error', {'message': 'Game not found'})
                
        except Exception as e:
            print(f"Error getting game state: {e}")
            emit('error', {'message': f'Failed to get game state: {str(e)}'})
    
    print("✅ SocketIO event handlers registered successfully")