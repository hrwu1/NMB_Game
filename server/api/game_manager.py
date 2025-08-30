"""
Game Manager for handling multiple concurrent game sessions.
Manages game creation, player joining, and routing actions to correct games.
"""

import uuid
from typing import Dict, Optional, Any, List
from datetime import datetime
import logging
import sys
import os

# Add game_logic to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game_logic.game import Game, GameState
from game_logic.player import Player
from game_logic.actions import execute_action

class GameManager:
    """Manages multiple concurrent game sessions"""
    
    def __init__(self):
        self.games: Dict[str, Game] = {}  # game_id -> Game instance
        self.player_to_game: Dict[str, str] = {}    # socket_id -> game_id
        self.max_players = 4
        
    def create_game(self, player_name: str, socket_id: str) -> str:
        """Create a new game session"""
        game_id = str(uuid.uuid4())[:8]  # Short game ID
        
        # Create new Game instance
        game = Game(game_id, self.max_players)
        
        # Create and add player
        player = Player(player_name, socket_id)
        game.add_player(player)
        
        # Store game and player mapping
        self.games[game_id] = game
        self.player_to_game[socket_id] = game_id
        
        logging.info(f"Game {game_id} created by {player_name}")
        return game_id
    
    def game_exists(self, game_id: str) -> bool:
        """Check if a game with the given ID exists"""
        return game_id in self.games
    
    def join_game(self, game_id: str, player_name: str, socket_id: str) -> bool:
        """Join an existing game session"""
        if game_id not in self.games:
            return False
            
        game = self.games[game_id]
        
        # Check if game can accept new players
        if game.state != GameState.WAITING:
            return False
            
        # Create and add player
        player = Player(player_name, socket_id)
        success = game.add_player(player)
        
        if success:
            self.player_to_game[socket_id] = game_id
            logging.info(f"Player {player_name} joined game {game_id}")
        
        return success
    
    def leave_game(self, socket_id: str) -> Optional[str]:
        """Remove a player from their current game"""
        if socket_id not in self.player_to_game:
            return None
            
        game_id = self.player_to_game[socket_id]
        
        if game_id in self.games:
            game = self.games[game_id]
            removed_player = game.remove_player(socket_id)
            
            if removed_player:
                logging.info(f"Player {removed_player.name} left game {game_id}")
                
                # If no players left, delete the game
                if not game.players:
                    del self.games[game_id]
                    logging.info(f"Game {game_id} deleted (no players remaining)")
        
        del self.player_to_game[socket_id]
        return game_id
    
    def get_game_state(self, game_id: str) -> Optional[Dict[str, Any]]:
        """Get current state of a game"""
        if game_id not in self.games:
            return None
            
        game = self.games[game_id]
        return game.get_game_state()
    
    def get_player_game(self, socket_id: str) -> Optional[str]:
        """Get the game ID that a player is currently in"""
        return self.player_to_game.get(socket_id)
    
    def start_game(self, game_id: str, socket_id: str) -> Dict[str, Any]:
        """Start a game (only host can start)"""
        if game_id not in self.games:
            return {"success": False, "reason": "Game not found"}
            
        game = self.games[game_id]
        
        # Check if player is host
        if game.host_socket_id != socket_id:
            return {"success": False, "reason": "Only host can start game"}
        
        # Start the game
        result = game.start_game()
        if result["success"]:
            logging.info(f"Game {game_id} started with {len(game.players)} players")
        
        return result
    
    def handle_player_action(self, socket_id: str, action_type: str, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a player action"""
        if socket_id not in self.player_to_game:
            return {"success": False, "reason": "Player not in any game"}
        
        game_id = self.player_to_game[socket_id]
        if game_id not in self.games:
            return {"success": False, "reason": "Game not found"}
        
        game = self.games[game_id]
        
        # Execute the action
        result = execute_action(game, socket_id, action_type, action_data)
        
        if result.get("success"):
            logging.info(f"Player action in game {game_id}: {action_type} by {socket_id}")
        
        return result
    
    def get_valid_actions(self, socket_id: str) -> List[str]:
        """Get valid actions for a player"""
        if socket_id not in self.player_to_game:
            return []
        
        game_id = self.player_to_game[socket_id]
        if game_id not in self.games:
            return []
        
        game = self.games[game_id]
        return game.get_valid_actions(socket_id)
    
    def get_game_list(self) -> Dict[str, Any]:
        """Get list of available games for lobby"""
        games_info = {}
        for game_id, game in self.games.items():
            if game.state == GameState.WAITING:
                games_info[game_id] = {
                    'id': game_id,
                    'players': len(game.players),
                    'max_players': self.max_players,
                    'created_at': game.created_at.isoformat(),
                    'player_names': [p.name for p in game.players.values()],
                    'host': game.players[game.host_socket_id].name if game.host_socket_id else None
                }
        return games_info
    
    def get_game(self, game_id: str) -> Optional[Game]:
        """Get game instance by ID"""
        return self.games.get(game_id)