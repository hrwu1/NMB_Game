"""
Core Game class for NMB Game.
Orchestrates all game components: players, board, cards, turns, phases, and victory conditions.
"""

from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime
import random
import uuid
import logging

from .constants import *
from .player import Player
from .board import Board, Position, PathTile
from .cards import *

class GameState(Enum):
    """Game state enumeration"""
    WAITING = "waiting"
    STARTING = "starting"
    PAWN_PLACEMENT = "pawn_placement"  # New phase for initial pawn placement
    PLAYING = "playing"
    PAUSED = "paused"
    FINISHED = "finished"

class Game:
    """Core game engine managing the complete game state and logic"""
    
    def __init__(self, game_id: str = None, max_players: int = MAX_PLAYERS):
        # Basic game info
        self.game_id = game_id or str(uuid.uuid4())[:6].upper()
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        
        # Game state
        self.state = GameState.WAITING
        self.current_phase = GamePhase.EXPLORATION
        self.round_number = 0
        self.turn_number = 0
        self.total_actions = 0
        
        # Players
        self.players: Dict[str, Player] = {}  # socket_id -> Player
        self.player_numbers: Dict[str, int] = {}  # socket_id -> player_number (1-4)
        self.player_order: List[str] = []  # Turn order by socket_id
        self.current_player_index = 0
        self.max_players = max_players
        self.host_socket_id: Optional[str] = None
        self.next_player_number = 1  # Track next available player number
        
        # Game components
        self.board = Board()
        self.decks = create_starting_decks()
        
        # Game mechanics
        self.dice_results: Dict[str, int] = {}  # Recent dice rolls
        self.pending_actions: List[Dict[str, Any]] = []
        self.game_log: List[Dict[str, Any]] = []
        
        # Victory tracking
        self.victory_condition_met = False
        self.victory_type: Optional[str] = None
        self.winning_players: List[str] = []
        self.defeat_reason: Optional[str] = None
        
        # Phase-specific state
        self.corruption_events = []
        self.active_anomalies: List[AnomalyCard] = []
        self.escape_exits_revealed = False
        
        # Pawn placement tracking
        self.players_placed_pawns: set = set()  # Track which players have placed pawns
        
        self._log_event("game_created", f"Game {self.game_id} created")
    
    # =============================================================================
    # PLAYER MANAGEMENT
    # =============================================================================
    
    def add_player(self, player: Player) -> bool:
        """Add a player to the game"""
        if len(self.players) >= self.max_players:
            return False
        
        if self.state != GameState.WAITING:
            return False
        
        # Assign stable player number
        self.player_numbers[player.socket_id] = self.next_player_number
        self.next_player_number += 1
        
        self.players[player.socket_id] = player
        
        # First player becomes host
        if not self.host_socket_id:
            self.host_socket_id = player.socket_id
            player.is_host = True
        
        self._log_event("player_joined", f"{player.name} joined the game as Player {self.player_numbers[player.socket_id]}")
        self.last_updated = datetime.now()
        return True
    
    def remove_player(self, socket_id: str) -> Optional[Player]:
        """Remove a player from the game"""
        if socket_id not in self.players:
            return None
        
        player = self.players.pop(socket_id)
        
        # Remove player number mapping
        if socket_id in self.player_numbers:
            self.player_numbers.pop(socket_id)
        
        # Remove from turn order
        if socket_id in self.player_order:
            old_index = self.player_order.index(socket_id)
            self.player_order.remove(socket_id)
            
            # Adjust current player index if needed
            if self.current_player_index >= old_index and self.current_player_index > 0:
                self.current_player_index -= 1
        
        # Assign new host if needed
        if socket_id == self.host_socket_id and self.players:
            new_host_id = next(iter(self.players.keys()))
            self.host_socket_id = new_host_id
            self.players[new_host_id].is_host = True
        
        self._log_event("player_left", f"{player.name} left the game")
        
        # End game if no players left
        if not self.players:
            self.state = GameState.FINISHED
            self.defeat_reason = "All players left"
        
        self.last_updated = datetime.now()
        return player
    
    def get_current_player(self) -> Optional[Player]:
        """Get the player whose turn it is"""
        # Allow turns during both pawn placement and normal gameplay
        if not self.player_order or self.state not in [GameState.PAWN_PLACEMENT, GameState.PLAYING]:
            return None
        
        current_socket_id = self.player_order[self.current_player_index]
        return self.players.get(current_socket_id)
    
    def get_player_by_id(self, socket_id: str) -> Optional[Player]:
        """Get player by socket ID"""
        return self.players.get(socket_id)
    
    # =============================================================================
    # GAME FLOW MANAGEMENT
    # =============================================================================
    
    def start_game(self) -> Dict[str, Any]:
        """Start the game"""
        if self.state == GameState.PAWN_PLACEMENT:
            return {"success": False, "reason": "Game has already started - players are placing pawns"}
        elif self.state == GameState.PLAYING:
            return {"success": False, "reason": "Game is already in progress"}
        elif self.state == GameState.FINISHED:
            return {"success": False, "reason": "Game has already finished"}
        elif self.state != GameState.WAITING:
            return {"success": False, "reason": f"Game is not in waiting state (current state: {self.state.value})"}
        
        if len(self.players) < MIN_PLAYERS:
            return {"success": False, "reason": f"Need at least {MIN_PLAYERS} players"}
        
        # Determine player order
        self._determine_player_order()
        
        # Initialize game state to pawn placement phase
        self.state = GameState.PAWN_PLACEMENT
        self.round_number = 0  # Start at 0 during placement phase
        self.turn_number = 1
        self.current_phase = GamePhase.EXPLORATION
        
        # Give each player starting hand (but NOT position)
        for player in self.players.values():
            self._deal_starting_hand(player)
        
        # Start first player's turn for pawn placement
        self._start_next_turn()
        
        self._log_event("game_started", f"Game started with {len(self.players)} players - pawn placement phase")
        return {"success": True, "message": "Game started - place your pawns!"}
    
    def _determine_player_order(self) -> None:
        """Determine turn order by rolling D12"""
        rolls = {}
        
        for socket_id, player in self.players.items():
            roll = random.randint(1, PLAYER_ORDER_DIE.value)
            rolls[socket_id] = roll
            self.dice_results[f"order_{socket_id}"] = roll
        
        # Sort by roll result (highest first)
        self.player_order = sorted(rolls.keys(), key=lambda x: rolls[x], reverse=True)
        
        order_message = ", ".join([
            f"{self.players[sid].name}({rolls[sid]})" 
            for sid in self.player_order
        ])
        self._log_event("turn_order", f"Turn order: {order_message}")
    
    def _deal_starting_hand(self, player: Player) -> None:
        """Deal starting cards to a player"""
        # Draw 3 effect cards
        for _ in range(3):
            card = self.decks[CardType.EFFECT].draw()
            if card:
                player.inventory.add_to_hand(card.to_dict())
    
    def _set_player_initial_position(self, player: Player) -> None:
        """Set player's initial position on the starting tile"""
        from .board import Position  # Import at runtime to avoid circular imports
        player.position = Position(
            tile_x=INITIAL_POSITION[0],  # Tile at (2,2)
            tile_y=INITIAL_POSITION[1],
            sub_x=1,  # Center of tile
            sub_y=1,
            floor=INITIAL_FLOOR
        )
        player.floor = INITIAL_FLOOR
    
    def place_player_pawn(self, socket_id: str, placement_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle player pawn placement during initial phase"""
        if self.state != GameState.PAWN_PLACEMENT:
            return {"success": False, "reason": "Not in pawn placement phase"}
        
        if socket_id not in self.players:
            return {"success": False, "reason": "Player not found"}
        
        if not self.is_player_turn(socket_id):
            return {"success": False, "reason": "Not your turn"}
        
        if socket_id in self.players_placed_pawns:
            return {"success": False, "reason": "You have already placed your pawn"}
        
        player = self.players[socket_id]
        
        # Get target position from placement_data
        target_position = placement_data.get("target_position")
        if not target_position:
            return {"success": False, "reason": "Target position is required"}
        
        try:
            # Validate and create position
            from .board import Position
            target_pos = Position(
                tile_x=target_position["tile_x"],
                tile_y=target_position["tile_y"],
                sub_x=target_position["sub_x"],
                sub_y=target_position["sub_y"],
                floor=target_position.get("floor", INITIAL_FLOOR)
            )
        except (KeyError, ValueError) as e:
            return {"success": False, "reason": f"Invalid target position: {str(e)}"}
        
        # Validate placement position (must be on initial tile and movable)
        if (target_pos.tile_x != INITIAL_POSITION[0] or 
            target_pos.tile_y != INITIAL_POSITION[1] or 
            target_pos.floor != INITIAL_FLOOR):
            return {"success": False, "reason": "Can only place pawn on the starting tile"}
        
        # Check if position is movable
        if not self.board.is_position_movable(target_pos):
            return {"success": False, "reason": "Cannot place pawn on walls or blocked areas"}
        
        # Check if position is already occupied by another player
        for other_player in self.players.values():
            if (other_player.socket_id != socket_id and 
                other_player.position and
                other_player.position.tile_x == target_pos.tile_x and
                other_player.position.tile_y == target_pos.tile_y and
                other_player.position.sub_x == target_pos.sub_x and
                other_player.position.sub_y == target_pos.sub_y and
                other_player.floor == target_pos.floor):
                return {"success": False, "reason": "Position already occupied by another player"}
        
        # Place the pawn
        player.position = target_pos
        player.floor = target_pos.floor
        
        # Mark player as having placed their pawn
        self.players_placed_pawns.add(socket_id)
        
        self._log_event("pawn_placed", f"{player.name} placed their pawn at ({target_pos.tile_x},{target_pos.tile_y}) sub-pos ({target_pos.sub_x},{target_pos.sub_y})")
        
        # Automatically end turn after placing pawn
        self._advance_pawn_placement_turn()
        
        return {
            "success": True, 
            "message": f"Pawn placed at selected position!",
            "position": {
                "tile_x": target_pos.tile_x,
                "tile_y": target_pos.tile_y, 
                "sub_x": target_pos.sub_x,
                "sub_y": target_pos.sub_y,
                "floor": target_pos.floor
            },
            "players_placed": len(self.players_placed_pawns),
            "total_players": len(self.players)
        }
    
    def _advance_pawn_placement_turn(self) -> None:
        """Advance turn during pawn placement phase"""
        # Move to next player
        self.current_player_index = (self.current_player_index + 1) % len(self.player_order)
        self.turn_number += 1
        
        # Check if all players have placed pawns
        if len(self.players_placed_pawns) >= len(self.players):
            self._transition_to_normal_gameplay()
        else:
            # Start next player's turn
            self._start_next_turn()
    
    def _transition_to_normal_gameplay(self) -> None:
        """Transition from pawn placement to normal gameplay"""
        self.state = GameState.PLAYING
        self.round_number = 1
        self.turn_number = 1
        self.current_player_index = 0  # Reset to first player
        
        # Start normal gameplay
        self._start_next_turn()
        
        self._log_event("gameplay_started", "All pawns placed - normal gameplay begins!")
        
        # Clear placement tracking
        self.players_placed_pawns.clear()
    
    def _start_next_turn(self) -> None:
        """Start the next player's turn"""
        current_player = self.get_current_player()
        if not current_player:
            return
        
        # End previous player's turn
        for player in self.players.values():
            if player.turn_active:
                player.end_turn()
        
        # Start current player's turn
        current_player.start_turn()
        
        # During pawn placement, don't roll dice or set movement points
        if self.state == GameState.PAWN_PLACEMENT:
            self._log_event("turn_started", f"{current_player.name}'s turn - place your pawn!")
        else:
            # Roll movement dice only during normal gameplay
            movement_roll = self._roll_dice(MOVEMENT_DIE)
            current_player.set_movement_points(movement_roll)
            self.dice_results[f"movement_{current_player.socket_id}"] = movement_roll
            
            self._log_event("turn_started", 
                           f"{current_player.name}'s turn started (Movement: {movement_roll})")
    
    def end_turn(self, socket_id: str) -> Dict[str, Any]:
        """End current player's turn"""
        if socket_id not in self.players:
            return {"success": False, "reason": "Player not found"}
        
        current_player = self.get_current_player()
        if not current_player or current_player.socket_id != socket_id:
            return {"success": False, "reason": "Not your turn"}
        
        # End current turn
        current_player.end_turn()
        
        # Advance to next player
        self.current_player_index = (self.current_player_index + 1) % len(self.player_order)
        self.turn_number += 1
        
        # Check if round is complete
        if self.current_player_index == 0:
            self._end_round()
        
        # Start next turn
        self._start_next_turn()
        
        # Check game phase progression
        self._check_phase_progression()
        
        # Check victory/defeat conditions
        self._check_game_end_conditions()
        
        return {"success": True, "next_player": self.get_current_player().name}
    
    def _end_round(self) -> None:
        """Handle end of round effects"""
        self.round_number += 1
        
        # Phase-specific effects
        if self.current_phase == GamePhase.MUTATION:
            # Spread corruption
            newly_corrupted = self.board.spread_corruption(CORRUPTION_SPREAD_RATE)
            if newly_corrupted:
                self._log_event("corruption_spread", 
                               f"Corruption spread to {len(newly_corrupted)} tiles")
        
        elif self.current_phase == GamePhase.END_GAME:
            # More aggressive corruption
            newly_corrupted = self.board.spread_corruption(CORRUPTION_SPREAD_RATE * 2)
            if newly_corrupted:
                self._log_event("corruption_accelerated", 
                               f"Corruption accelerated! {len(newly_corrupted)} tiles corrupted")
        
        self._log_event("round_ended", f"Round {self.round_number - 1} completed")
    
    # =============================================================================
    # GAME PHASES
    # =============================================================================
    
    def _check_phase_progression(self) -> None:
        """Check if game should advance to next phase"""
        old_phase = self.current_phase
        new_phase = get_current_phase(self.total_actions)
        
        if new_phase != old_phase:
            self.current_phase = new_phase
            self._handle_phase_transition(old_phase, new_phase)
    
    def _handle_phase_transition(self, old_phase: GamePhase, new_phase: GamePhase) -> None:
        """Handle transition between game phases"""
        phase_names = {
            GamePhase.EXPLORATION: "Exploration",
            GamePhase.MUTATION: "Mutation", 
            GamePhase.END_GAME: "End Game"
        }
        
        self._log_event("phase_transition", 
                       f"Phase changed: {phase_names[old_phase]} → {phase_names[new_phase]}")
        
        if new_phase == GamePhase.MUTATION:
            self._start_mutation_phase()
        elif new_phase == GamePhase.END_GAME:
            self._start_endgame_phase()
    
    def _start_mutation_phase(self) -> None:
        """Initialize mutation phase effects"""
        self._log_event("mutation_phase", "The building becomes more dangerous...")
        
        # Start corruption spread
        self.board.corruption_spread_rate = CORRUPTION_SPREAD_RATE
        
        # Increase anomaly frequency (handled in card drawing)
        
    def _start_endgame_phase(self) -> None:
        """Initialize end game phase effects"""
        self._log_event("endgame_phase", "The building begins to collapse! Find the exit!")
        
        # Reveal escape exits on top floor
        if not self.escape_exits_revealed:
            self._reveal_escape_exits()
        
        # Accelerate corruption
        self.board.corruption_spread_rate = CORRUPTION_SPREAD_RATE * 2
    
    def _reveal_escape_exits(self) -> None:
        """Reveal escape exits on the top floor"""
        # Add random escape exits on floor 5
        for _ in range(2):  # 2 escape exits
            x, y = random.randint(0, BOARD_SIZE[0]-1), random.randint(0, BOARD_SIZE[1]-1)
            exit_pos = Position(x, y, ESCAPE_FLOOR)
            
            # Create escape tile if position is empty
            if not self.board.get_tile(exit_pos):
                escape_tile = PathTile(
                    tile_id=f"escape_exit_{x}_{y}",
                    tile_type=PathTileType.BASIC,
                    position=exit_pos
                )
                # Add emergency door
                escape_tile.special_squares[(1, 1)] = SpecialSquareType.EMERGENCY_DOOR
                self.board.place_tile(escape_tile)
                self.board.escape_exits.append(exit_pos)
        
        self.escape_exits_revealed = True
        self._log_event("exits_revealed", "Escape exits appeared on the top floor!")
    
    # =============================================================================
    # DICE ROLLING
    # =============================================================================
    
    def _roll_dice(self, dice_type: DiceType) -> int:
        """Roll a die and return result"""
        result = random.randint(1, dice_type.value)
        return result
    
    def roll_dice_for_player(self, socket_id: str, dice_type: DiceType, 
                            purpose: str = "") -> Dict[str, Any]:
        """Roll dice for a specific player"""
        if socket_id not in self.players:
            return {"success": False, "reason": "Player not found"}
        
        result = self._roll_dice(dice_type)
        self.dice_results[f"{purpose}_{socket_id}"] = result
        
        player_name = self.players[socket_id].name
        self._log_event("dice_roll", f"{player_name} rolled {dice_type.name}: {result} ({purpose})")
        
        return {
            "success": True,
            "player": player_name,
            "dice_type": dice_type.name,
            "result": result,
            "purpose": purpose
        }
    
    # =============================================================================
    # VICTORY AND DEFEAT CONDITIONS
    # =============================================================================
    
    def _check_game_end_conditions(self) -> None:
        """Check for victory or defeat conditions"""
        # Check defeat conditions first
        if self._check_defeat_conditions():
            return
        
        # Check victory conditions
        self._check_victory_conditions()
    
    def _check_defeat_conditions(self) -> bool:
        """Check for game defeat conditions"""
        # Corruption defeat
        if self.board.is_game_lost_to_corruption():
            self._end_game_defeat("corruption", "70% of the map became corrupted")
            return True
        
        # All players dead/disconnected
        active_players = [p for p in self.players.values() if p.is_connected]
        if not active_players:
            self._end_game_defeat("no_players", "All players disconnected")
            return True
        
        return False
    
    def _check_victory_conditions(self) -> None:
        """Check for victory conditions"""
        for socket_id, player in self.players.items():
            # Regular victory: 3 escape items + reach exit
            if (player.escape_items_collected >= ESCAPE_ITEMS_REQUIRED and 
                player.floor == ESCAPE_FLOOR and
                any(exit_pos.x == player.position[0] and exit_pos.y == player.position[1] 
                    for exit_pos in self.board.escape_exits)):
                
                self._end_game_victory("escape", [socket_id], 
                                     f"{player.name} escaped with required items!")
                return
            
            # Special victory: 7 experiment reports
            if player.experiment_reports_collected >= EXPERIMENT_REPORTS_REQUIRED:
                self._end_game_victory("research", [socket_id],
                                     f"{player.name} uncovered the building's secrets!")
                return
        
        # Collective victory: All anomalies purified
        if not self.active_anomalies and len(self.active_anomalies) > 0:
            all_players = list(self.players.keys())
            self._end_game_victory("purification", all_players,
                                 "All anomalies have been purified!")
            return
    
    def _end_game_victory(self, victory_type: str, winning_players: List[str], message: str) -> None:
        """End game with victory"""
        self.state = GameState.FINISHED
        self.victory_condition_met = True
        self.victory_type = victory_type
        self.winning_players = winning_players
        
        winner_names = [self.players[sid].name for sid in winning_players]
        self._log_event("victory", f"VICTORY! {message} Winners: {', '.join(winner_names)}")
    
    def _end_game_defeat(self, defeat_type: str, message: str) -> None:
        """End game with defeat"""
        self.state = GameState.FINISHED
        self.victory_condition_met = False
        self.defeat_reason = f"{defeat_type}: {message}"
        
        self._log_event("defeat", f"DEFEAT! {message}")
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def _log_event(self, event_type: str, message: str, player_id: str = None) -> None:
        """Log a game event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "message": message,
            "player_id": player_id,
            "turn": self.turn_number,
            "round": self.round_number,
            "phase": self.current_phase.name
        }
        
        self.game_log.append(event)
        logging.info(f"Game {self.game_id}: {message}")
    
    def get_game_state(self) -> Dict[str, Any]:
        """Get complete game state for serialization"""
        current_player = self.get_current_player()
        
        return {
            "game_id": self.game_id,
            "state": self.state.value,
            "phase": self.current_phase.name,
            "round": self.round_number,
            "turn": self.turn_number,
            "total_actions": self.total_actions,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            
            # Players
            "players": {sid: {**player.to_dict(), "player_number": self.player_numbers.get(sid, 1)} 
                       for sid, player in self.players.items()},
            "player_numbers": self.player_numbers,
            "player_order": self.player_order,
            "current_player": current_player.socket_id if current_player else None,
            "host": self.host_socket_id,
            
            # Board state
            "board": self.board.get_board_state(),
            
            # Decks
            "decks": {deck_type.value: deck.to_dict() for deck_type, deck in self.decks.items()},
            
            # Recent dice rolls
            "dice_results": self.dice_results,
            
            # Game progress
            "victory_condition_met": self.victory_condition_met,
            "victory_type": self.victory_type,
            "winning_players": self.winning_players,
            "defeat_reason": self.defeat_reason,
            
            # Recent events
            "recent_events": self.game_log[-10:] if self.game_log else [],
            
            # Phase-specific info
            "corruption_percentage": self.board.get_corruption_percentage(),
            "active_anomalies": len(self.active_anomalies),
            "escape_exits_revealed": self.escape_exits_revealed,
            
            # Pawn placement info
            "pawn_placement": {
                "players_placed": list(self.players_placed_pawns),
                "total_players": len(self.players),
                "placement_complete": len(self.players_placed_pawns) >= len(self.players)
            }
        }
    
    def is_player_turn(self, socket_id: str) -> bool:
        """Check if it's a specific player's turn"""
        current_player = self.get_current_player()
        return current_player is not None and current_player.socket_id == socket_id
    
    def can_start_game(self) -> Tuple[bool, str]:
        """Check if game can be started"""
        if self.state != GameState.WAITING:
            return False, "Game is not in waiting state"
        
        if len(self.players) < MIN_PLAYERS:
            return False, f"Need at least {MIN_PLAYERS} players"
        
        return True, "Game can be started"
    
    def get_valid_actions(self, socket_id: str) -> List[str]:
        """Get list of valid actions for a player"""
        if socket_id not in self.players:
            return []
        
        player = self.players[socket_id]
        
        if not self.is_player_turn(socket_id):
            return ["wait"]  # Can only wait if not their turn
        
        # During pawn placement phase, only allow pawn placement
        if self.state == GameState.PAWN_PLACEMENT:
            if socket_id in self.players_placed_pawns:
                return ["wait"]  # Already placed pawn, can only wait
            else:
                return ["place_pawn"]  # Can only place pawn
        
        actions = []
        
        # Basic actions (only during normal gameplay)
        if player.get_remaining_movement() > 0:
            actions.extend(["move", "explore" if can_explore(player.disorder) else "fall"])
        
        # Interaction actions (if other players on same tile)
        same_tile_players = [
            p for p in self.players.values() 
            if p != player and p.floor == player.floor and p.position == player.position
        ]
        
        if same_tile_players:
            actions.extend(["meet", "rob"])
        
        # Item usage
        if player.inventory.items:
            actions.append("use_item")
        
        # Always available
        actions.extend(["pass", "end_turn"])
        
        return actions
    
    def __str__(self) -> str:
        return (f"Game({self.game_id}, {self.state.value}, "
               f"{len(self.players)} players, {self.current_phase.name})")
    
    def __repr__(self) -> str:
        return (f"Game(id='{self.game_id}', state='{self.state.value}', "
               f"players={len(self.players)}, phase='{self.current_phase.name}', "
               f"round={self.round_number}, turn={self.turn_number})")