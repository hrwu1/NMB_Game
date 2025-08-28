"""
Game Manager for handling multiple concurrent game sessions.
Manages game creation, player joining, and routing actions to correct games.
"""

import uuid
from typing import Dict, Optional, Any
from datetime import datetime
import logging

class GameManager:
    """Manages multiple concurrent game sessions"""
    
    def __init__(self):
        self.games: Dict[str, Dict[str, Any]] = {}  # game_id -> game_data
        self.player_to_game: Dict[str, str] = {}    # socket_id -> game_id
        self.max_players = 4
        
    def create_game(self, player_name: str, socket_id: str) -> str:
        """Create a new game session"""
        game_id = str(uuid.uuid4())[:8]  # Short game ID
        
        # Initialize game data
        game_data = {
            'id': game_id,
            'created_at': datetime.now(),
            'players': {
                socket_id: {
                    'name': player_name,
                    'socket_id': socket_id,
                    'disorder': 0,
                    'floor': 2,
                    'position': {'x': 0, 'y': 0},
                    'items': [],
                    'effects': [],
                    'is_host': True
                }
            },
            'status': 'waiting',  # waiting, playing, finished
            'current_turn': 0,
            'game_phase': 1,
            'board_state': self._initialize_board(),
            'deck_state': self._initialize_decks()
        }
        
        self.games[game_id] = game_data
        self.player_to_game[socket_id] = game_id
        
        logging.info(f"Game {game_id} created by {player_name}")
        return game_id
    
    def join_game(self, game_id: str, player_name: str, socket_id: str) -> bool:
        """Join an existing game session"""
        if game_id not in self.games:
            return False
            
        game_data = self.games[game_id]
        
        # Check if game is full
        if len(game_data['players']) >= self.max_players:
            return False
            
        # Check if game has started
        if game_data['status'] != 'waiting':
            return False
            
        # Add player to game
        game_data['players'][socket_id] = {
            'name': player_name,
            'socket_id': socket_id,
            'disorder': 0,
            'floor': 2,
            'position': {'x': 0, 'y': 0},
            'items': [],
            'effects': [],
            'is_host': False
        }
        
        self.player_to_game[socket_id] = game_id
        
        logging.info(f"Player {player_name} joined game {game_id}")
        return True
    
    def leave_game(self, socket_id: str) -> Optional[str]:
        """Remove a player from their current game"""
        if socket_id not in self.player_to_game:
            return None
            
        game_id = self.player_to_game[socket_id]
        
        if game_id in self.games:
            # Remove player from game
            if socket_id in self.games[game_id]['players']:
                player_name = self.games[game_id]['players'][socket_id]['name']
                del self.games[game_id]['players'][socket_id]
                
                # If no players left, delete the game
                if not self.games[game_id]['players']:
                    del self.games[game_id]
                    logging.info(f"Game {game_id} deleted (no players remaining)")
                else:
                    # If host left, assign new host
                    remaining_players = self.games[game_id]['players']
                    if not any(p['is_host'] for p in remaining_players.values()):
                        # Make first remaining player the host
                        first_player_id = next(iter(remaining_players.keys()))
                        remaining_players[first_player_id]['is_host'] = True
                        
                logging.info(f"Player {player_name} left game {game_id}")
        
        del self.player_to_game[socket_id]
        return game_id
    
    def get_game_state(self, game_id: str) -> Optional[Dict[str, Any]]:
        """Get current state of a game"""
        if game_id not in self.games:
            return None
            
        # Make a copy of the game state and convert datetime to string for JSON serialization
        game_state = self.games[game_id].copy()
        if 'created_at' in game_state:
            game_state['created_at'] = game_state['created_at'].isoformat()
        
        return game_state
    
    def get_player_game(self, socket_id: str) -> Optional[str]:
        """Get the game ID that a player is currently in"""
        return self.player_to_game.get(socket_id)
    
    def start_game(self, game_id: str) -> bool:
        """Start a game (change status from waiting to playing)"""
        if game_id not in self.games:
            return False
            
        game_data = self.games[game_id]
        
        # Need at least 1 player to start (though game is designed for 2-4)
        if len(game_data['players']) < 1:
            return False
            
        game_data['status'] = 'playing'
        logging.info(f"Game {game_id} started with {len(game_data['players'])} players")
        return True
    
    def _initialize_board(self) -> Dict[str, Any]:
        """Initialize empty board state"""
        return {
            'floors': {
                '1': {'tiles': {}, 'zones': {}},
                '2': {'tiles': {'0,0': 'initial_tile'}, 'zones': {}},
                '3': {'tiles': {}, 'zones': {}},
                '4': {'tiles': {}, 'zones': {}},
                '5': {'tiles': {}, 'zones': {}}
            },
            'corruption_level': 0
        }
    
    def _initialize_decks(self) -> Dict[str, Any]:
        """Initialize game decks"""
        return {
            'path_tiles': {'remaining': 50, 'discarded': []},
            'effect_cards': {'remaining': 80, 'discarded': []},
            'zone_cards': {'remaining': 8, 'placed': {}}
        }
    
    def get_game_list(self) -> Dict[str, Any]:
        """Get list of available games for lobby"""
        games_info = {}
        for game_id, game_data in self.games.items():
            if game_data['status'] == 'waiting':
                games_info[game_id] = {
                    'id': game_id,
                    'players': len(game_data['players']),
                    'max_players': self.max_players,
                    'created_at': game_data['created_at'].isoformat(),
                    'player_names': [p['name'] for p in game_data['players'].values()]
                }
        return games_info