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
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        print(f"Client disconnected: {request.sid}")
        # TODO: Handle player leaving game
        
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
    
    @socketio.on('player_action')
    def handle_player_action(data):
        """Handle player game actions"""
        try:
            game_id = data.get('game_id')
            action_data = data.get('action_data', {})
            
            print(f"Player action received for game {game_id}: {action_data}")
            
            # Process the action (placeholder for now)
            # TODO: Implement game logic processing
            
            # For now, just echo the action back to all players
            socketio.emit('game_state_update', {
                'game_id': game_id,
                'action': action_data,
                'message': 'Action processed (placeholder)'
            }, room=game_id)
            
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