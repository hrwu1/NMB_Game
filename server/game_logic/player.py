"""
Player class for NMB Game.
Manages individual player state, inventory, position, and actions.
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid

# Position import will be done at runtime to avoid circular imports

from .constants import (
    INITIAL_DISORDER, INITIAL_FLOOR, INITIAL_POSITION, MAX_DISORDER,
    MAX_ITEM_SLOTS, MAX_EFFECT_SLOTS, HAND_SIZE_LIMIT,
    DISORDER_FALL_THRESHOLD, ActionType, get_disorder_description,
    can_explore, can_pass_walls, ROB_DISORDER_PENALTY, MEET_DISORDER_REDUCTION,
    MEET_DISORDER_RANGE
)

@dataclass
class PlayerInventory:
    """Player inventory management"""
    items: List[Dict[str, Any]] = field(default_factory=list)
    effects: List[Dict[str, Any]] = field(default_factory=list)
    hand: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_item(self, item: Dict[str, Any]) -> bool:
        """Add item to inventory if space available"""
        if len(self.items) < MAX_ITEM_SLOTS:
            self.items.append(item)
            return True
        return False
    
    def add_effect(self, effect: Dict[str, Any]) -> bool:
        """Add effect to inventory if space available"""
        if len(self.effects) < MAX_EFFECT_SLOTS:
            self.effects.append(effect)
            return True
        return False
    
    def add_to_hand(self, card: Dict[str, Any]) -> bool:
        """Add card to hand if space available"""
        if len(self.hand) < HAND_SIZE_LIMIT:
            self.hand.append(card)
            return True
        return False
    
    def remove_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Remove and return item by ID"""
        for i, item in enumerate(self.items):
            if item.get('id') == item_id:
                return self.items.pop(i)
        return None
    
    def remove_effect(self, effect_id: str) -> Optional[Dict[str, Any]]:
        """Remove and return effect by ID"""
        for i, effect in enumerate(self.effects):
            if effect.get('id') == effect_id:
                return self.effects.pop(i)
        return None
    
    def remove_from_hand(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Remove and return card from hand by ID"""
        for i, card in enumerate(self.hand):
            if card.get('id') == card_id:
                return self.hand.pop(i)
        return None
    
    def is_inventory_full(self) -> bool:
        """Check if inventory is completely full"""
        return (len(self.items) >= MAX_ITEM_SLOTS and 
                len(self.effects) >= MAX_EFFECT_SLOTS)
    
    def get_available_slots(self) -> Dict[str, int]:
        """Get available slots in inventory"""
        return {
            'items': MAX_ITEM_SLOTS - len(self.items),
            'effects': MAX_EFFECT_SLOTS - len(self.effects),
            'hand': HAND_SIZE_LIMIT - len(self.hand)
        }

class Player:
    """Represents a player in the NMB Game"""
    
    def __init__(self, name: str, socket_id: str, player_id: str = None):
        # Basic player info
        self.name = name
        self.socket_id = socket_id
        self.player_id = player_id or str(uuid.uuid4())[:8]
        self.created_at = datetime.now()
        
        # Game state  
        self.disorder = INITIAL_DISORDER
        self.floor = INITIAL_FLOOR
        # Position - not set until game starts
        self.position = None  # Will be set when game starts
        self.current_tile_id: Optional[str] = None
        
        # Movement and actions
        self.movement_points = 0
        self.movement_used = 0
        self.actions_taken = 0
        self.last_action: Optional[str] = None
        self.turn_active = False
        
        # Inventory and cards
        self.inventory = PlayerInventory()
        
        # Game mechanics
        self.is_host = False
        self.is_connected = True
        self.last_seen = datetime.now()
        
        # Victory progress
        self.escape_items_collected = 0
        self.experiment_reports_collected = 0
        
        # Statistics
        self.stats = {
            'turns_taken': 0,
            'tiles_explored': 0,
            'items_found': 0,
            'players_met': 0,
            'players_robbed': 0,
            'falls_taken': 0,
            'max_disorder_reached': INITIAL_DISORDER
        }
    
    # =============================================================================
    # CORE STATE MANAGEMENT
    # =============================================================================
    
    def update_disorder(self, change: int, reason: str = "") -> bool:
        """Update player's disorder level"""
        old_disorder = self.disorder
        self.disorder = max(0, min(MAX_DISORDER, self.disorder + change))
        
        # Update statistics
        if self.disorder > self.stats['max_disorder_reached']:
            self.stats['max_disorder_reached'] = self.disorder
        
        print(f"Player {self.name}: Disorder {old_disorder} → {self.disorder} ({reason})")
        return self.disorder != old_disorder
    
    def change_floor(self, new_floor: int, reason: str = "") -> bool:
        """Move player to a different floor"""
        if new_floor < 1 or new_floor > 5:
            return False
            
        old_floor = self.floor
        self.floor = new_floor
        
        print(f"Player {self.name}: Floor {old_floor} → {self.floor} ({reason})")
        return True
    
    def update_position(self, new_position, tile_id: str = None) -> None:
        """Update player's position on current floor"""
        from .board import Position  # Import at runtime to avoid circular imports
        
        if isinstance(new_position, tuple):
            # Legacy tuple format - convert to new Position system
            if len(new_position) == 2:
                # Assume it's (x, y) and player stays in same tile
                self.position = Position(
                    tile_x=self.position.tile_x,
                    tile_y=self.position.tile_y,
                    sub_x=new_position[0] % 4,
                    sub_y=new_position[1] % 4,
                    floor=self.position.floor
                )
            elif len(new_position) == 5:
                # Full position tuple
                self.position = Position(*new_position)
        else:
            # New Position object
            self.position = new_position
            
        if tile_id:
            self.current_tile_id = tile_id
        
        print(f"Player {self.name}: Moved to tile ({self.position.tile_x},{self.position.tile_y}) sub-position ({self.position.sub_x},{self.position.sub_y})")
    
    def set_movement_points(self, points: int) -> None:
        """Set movement points for the current turn"""
        self.movement_points = points
        self.movement_used = 0
    
    def use_movement_points(self, points: int) -> bool:
        """Use movement points if available"""
        if self.movement_used + points <= self.movement_points:
            self.movement_used += points
            return True
        return False
    
    def get_remaining_movement(self) -> int:
        """Get remaining movement points"""
        return self.movement_points - self.movement_used
    
    # =============================================================================
    # GAME ACTION VALIDATION
    # =============================================================================
    
    def can_perform_action(self, action_type: ActionType) -> Tuple[bool, str]:
        """Check if player can perform the specified action"""
        if action_type == ActionType.EXPLORE:
            if not can_explore(self.disorder):
                return False, f"Disorder too high ({self.disorder} >= {DISORDER_FALL_THRESHOLD}), must Fall"
            if self.get_remaining_movement() <= 0:
                return False, "No movement points remaining"
            return True, ""
        
        elif action_type == ActionType.FALL:
            if self.disorder < DISORDER_FALL_THRESHOLD:
                return False, f"Disorder too low ({self.disorder} < {DISORDER_FALL_THRESHOLD}), can Explore instead"
            if self.floor <= 1:
                return False, "Already on bottom floor, cannot fall further"
            return True, ""
        
        elif action_type == ActionType.MOVE:
            if self.get_remaining_movement() <= 0:
                return False, "No movement points remaining"
            return True, ""
        
        elif action_type == ActionType.USE_STAIRS:
            # Can use stairs if on a stairwell tile
            return True, ""
        
        elif action_type == ActionType.USE_ELEVATOR:
            # Can use elevator if on an elevator tile
            return True, ""
        
        else:
            return True, ""  # Most actions are always available
    
    def can_interact_with_player(self, other_player: 'Player', action_type: str) -> Tuple[bool, str]:
        """Check if this player can interact with another player"""
        # Must be on same tile
        if (self.floor != other_player.floor or 
            self.position != other_player.position):
            return False, "Players must be on the same tile"
        
        if action_type == "meet":
            disorder_diff = abs(self.disorder - other_player.disorder)
            if disorder_diff > MEET_DISORDER_RANGE:
                return False, f"Disorder levels too different ({disorder_diff} > {MEET_DISORDER_RANGE})"
        
        elif action_type == "rob":
            if not other_player.inventory.hand:
                return False, "Target player has no cards to rob"
        
        return True, ""
    
    # =============================================================================
    # PLAYER INTERACTIONS
    # =============================================================================
    
    def meet_player(self, other_player: 'Player') -> Dict[str, Any]:
        """Perform meet action with another player"""
        can_meet, reason = self.can_interact_with_player(other_player, "meet")
        if not can_meet:
            return {"success": False, "reason": reason}
        
        # Both players reduce disorder
        self.update_disorder(-MEET_DISORDER_REDUCTION, f"met with {other_player.name}")
        other_player.update_disorder(-MEET_DISORDER_REDUCTION, f"met with {self.name}")
        
        # Update statistics
        self.stats['players_met'] += 1
        other_player.stats['players_met'] += 1
        
        return {
            "success": True,
            "message": f"{self.name} and {other_player.name} met peacefully",
            "disorder_change": -MEET_DISORDER_REDUCTION
        }
    
    def rob_player(self, other_player: 'Player') -> Dict[str, Any]:
        """Perform rob action on another player"""
        can_rob, reason = self.can_interact_with_player(other_player, "rob")
        if not can_rob:
            return {"success": False, "reason": reason}
        
        # Random card from target's hand
        if not other_player.inventory.hand:
            return {"success": False, "reason": "Target has no cards"}
        
        import random
        stolen_card = random.choice(other_player.inventory.hand)
        other_player.inventory.remove_from_hand(stolen_card['id'])
        
        # Add to robber's hand if space
        if self.inventory.add_to_hand(stolen_card):
            # Increase robber's disorder
            self.update_disorder(ROB_DISORDER_PENALTY, f"robbed {other_player.name}")
            
            # Update statistics
            self.stats['players_robbed'] += 1
            
            return {
                "success": True,
                "message": f"{self.name} robbed {stolen_card['name']} from {other_player.name}",
                "stolen_card": stolen_card,
                "disorder_change": ROB_DISORDER_PENALTY
            }
        else:
            # Put card back if robber's hand is full
            other_player.inventory.add_to_hand(stolen_card)
            return {"success": False, "reason": "Robber's hand is full"}
    
    # =============================================================================
    # TURN MANAGEMENT
    # =============================================================================
    
    def start_turn(self) -> None:
        """Initialize player's turn"""
        self.turn_active = True
        self.movement_points = 0
        self.movement_used = 0
        self.stats['turns_taken'] += 1
        print(f"Turn started for {self.name}")
    
    def end_turn(self) -> None:
        """End player's turn"""
        self.turn_active = False
        self.movement_points = 0
        self.movement_used = 0
        self.last_seen = datetime.now()
        print(f"Turn ended for {self.name}")
    
    def perform_fall(self) -> Dict[str, Any]:
        """Perform fall action (disorder >= 6)"""
        if self.floor <= 1:
            return {"success": False, "reason": "Already on bottom floor"}
        
        # Move to floor below
        old_floor = self.floor
        self.change_floor(self.floor - 1, "fell due to high disorder")
        
        # Reduce disorder
        self.update_disorder(-1, "disorder reduced after fall")
        
        # Update statistics
        self.stats['falls_taken'] += 1
        
        return {
            "success": True,
            "message": f"{self.name} fell from floor {old_floor} to {self.floor}",
            "floor_change": self.floor - old_floor,
            "disorder_change": -1
        }
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get current player status"""
        return {
            "name": self.name,
            "disorder": self.disorder,
            "disorder_description": get_disorder_description(self.disorder),
            "floor": self.floor,
            "position": self.position,
            "movement_remaining": self.get_remaining_movement(),
            "can_explore": can_explore(self.disorder),
            "can_pass_walls": can_pass_walls(self.disorder),
            "inventory_slots": self.inventory.get_available_slots(),
            "escape_progress": {
                "items": self.escape_items_collected,
                "reports": self.experiment_reports_collected
            },
            "is_turn_active": self.turn_active,
            "is_connected": self.is_connected,
            "stats": self.stats
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert player to dictionary for JSON serialization"""
        return {
            "player_id": self.player_id,
            "name": self.name,
            "socket_id": self.socket_id,
            "disorder": self.disorder,
            "floor": self.floor,
            "position": {
                "tile_x": self.position.tile_x,
                "tile_y": self.position.tile_y,
                "sub_x": self.position.sub_x,
                "sub_y": self.position.sub_y,
                "absolute_coords": self.position.to_absolute_coords()
            },
            "current_tile_id": self.current_tile_id,
            "movement_points": self.movement_points,
            "movement_used": self.movement_used,
            "inventory": {
                "items": self.inventory.items,
                "effects": self.inventory.effects,
                "hand": self.inventory.hand,
                "slots_available": self.inventory.get_available_slots()
            },
            "is_host": self.is_host,
            "is_connected": self.is_connected,
            "turn_active": self.turn_active,
            "escape_progress": {
                "items": self.escape_items_collected,
                "reports": self.experiment_reports_collected
            },
            "stats": self.stats,
            "created_at": self.created_at.isoformat(),
            "last_seen": self.last_seen.isoformat()
        }
    
    def update_connection_status(self, is_connected: bool) -> None:
        """Update player's connection status"""
        self.is_connected = is_connected
        if is_connected:
            self.last_seen = datetime.now()
    
    def __str__(self) -> str:
        return f"Player({self.name}, Floor {self.floor}, Disorder {self.disorder})"
    
    def __repr__(self) -> str:
        return f"Player(name='{self.name}', disorder={self.disorder}, floor={self.floor}, position={self.position})"