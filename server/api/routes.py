"""
SocketIO event handlers for the NMB Game server.
Handles client connections, game creation, and player actions.
"""

from flask_socketio import emit, join_room, leave_room, disconnect
from flask import request
import logging
from .game_manager import GameManager

# Initialize game manager
game_manager = GameManager()

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
            player_name = data.get('player_name', 'Anonymous')
            print(f"Creating game for player: {player_name}")
            
            # Create new game
            game_id = game_manager.create_game(player_name, request.sid)
            
            # Join the game room
            join_room(game_id)
            
            # Send response to client
            emit('game_created', {
                'game_id': game_id,
                'player_name': player_name,
                'message': f'Game {game_id} created successfully'
            })
            
            print(f"Game {game_id} created for player {player_name}")
            
        except Exception as e:
            print(f"Error creating game: {e}")
            emit('error', {'message': f'Failed to create game: {str(e)}'})
    
    @socketio.on('join_game')
    def handle_join_game(data):
        """Handle join game request"""
        try:
            game_id = data.get('game_id')
            player_name = data.get('player_name', 'Anonymous')
            
            print(f"Player {player_name} attempting to join game {game_id}")
            
            # Join the game
            success = game_manager.join_game(game_id, player_name, request.sid)
            
            if success:
                # Join the game room
                join_room(game_id)
                
                # Notify all players in the game
                socketio.emit('player_joined', {
                    'player_name': player_name,
                    'message': f'{player_name} joined the game'
                }, room=game_id)
                
                # Send success response to joining player
                emit('game_joined', {
                    'game_id': game_id,
                    'player_name': player_name,
                    'message': 'Successfully joined the game'
                })
                
                print(f"Player {player_name} joined game {game_id}")
                
            else:
                emit('error', {'message': 'Failed to join game. Game may be full or not exist.'})
                
        except Exception as e:
            print(f"Error joining game: {e}")
            emit('error', {'message': f'Failed to join game: {str(e)}'})
    
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