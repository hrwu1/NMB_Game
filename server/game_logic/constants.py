"""
Game constants for NMB Game.
Contains all game rules, limits, and configuration values based on the game logic.
"""

from enum import Enum
from typing import Dict, List, Tuple

# =============================================================================
# GAME SETUP & LIMITS
# =============================================================================

# Player limits
MIN_PLAYERS = 2
MAX_PLAYERS = 4
RECOMMENDED_PLAYERS = (2, 4)

# Game start behavior
AUTO_START_ENABLED = True  # Whether to auto-start when min players join
REQUIRED_PLAYERS_FOR_AUTO_START = 2  # Number of players needed for auto-start

# Board dimensions
FLOOR_COUNT = 5
FLOOR_RANGE = (1, 6)  # Floors 1-5 (Python range excludes upper bound)
STARTING_FLOOR = 2
BOARD_SIZE = (5, 5)  # 5x5 tile grid per floor

# Initial player stats
INITIAL_DISORDER = 0
INITIAL_FLOOR = 2
INITIAL_POSITION = (2, 2)  # Starting tile position (center of 5x5 grid)
MAX_DISORDER = 10
DISORDER_FALL_THRESHOLD = 6

# =============================================================================
# GAME PHASES
# =============================================================================

class GamePhase(Enum):
    """Game phases with increasing difficulty"""
    EXPLORATION = 1
    MUTATION = 2
    END_GAME = 3

# Phase transition thresholds (based on total actions taken)
PHASE_THRESHOLDS = {
    GamePhase.EXPLORATION: 0,
    GamePhase.MUTATION: 50,
    GamePhase.END_GAME: 100
}

# =============================================================================
# VICTORY CONDITIONS
# =============================================================================

# Regular victory requirements
ESCAPE_ITEMS_REQUIRED = 3
ESCAPE_FLOOR = 5  # Top floor

# Special victory requirements
EXPERIMENT_REPORTS_REQUIRED = 7
ANOMALY_PURIFICATION_REQUIRED = "all"

# Defeat condition
MAP_CORRUPTION_LIMIT = 0.70  # 70% of map becomes corroded

# =============================================================================
# DICE MECHANICS
# =============================================================================

class DiceType(Enum):
    """Available dice types"""
    D4 = 4
    D6 = 6
    D8 = 8
    D12 = 12

# Movement mechanics
MOVEMENT_DIE = DiceType.D6
PLAYER_ORDER_DIE = DiceType.D12

# =============================================================================
# DISORDER MECHANICS
# =============================================================================

# Disorder effects
DISORDER_EFFECTS = {
    0: "Normal state",
    1: "Slightly unsettled",
    2: "Nervous",
    3: "Anxious", 
    4: "Disturbed",
    5: "Highly disturbed",
    6: "Cannot Explore - Forces Fall",
    7: "Can pass through walls",
    8: "Severe mental strain",
    9: "Near breaking point",
    10: "Complete breakdown"
}

# Disorder interaction ranges for Meet action
MEET_DISORDER_RANGE = 2  # Players can meet if disorder difference <= 2

# =============================================================================
# CARD TYPES & QUANTITIES
# =============================================================================

class CardType(Enum):
    """Types of cards in the game"""
    PATH_TILE = "path_tile"
    EFFECT = "effect"
    ITEM = "item"
    ANOMALY = "anomaly"
    BUTTON = "button"
    ZONE_NAME = "zone_name"

# Deck composition
DECK_SIZES = {
    CardType.PATH_TILE: 60,
    CardType.EFFECT: 80,  # Mixed deck of items, events, anomalies
    CardType.BUTTON: 20,
    CardType.ZONE_NAME: 8  # One per zone A-H
}

# Path tile types
class PathTileType(Enum):
    """Types of path tiles"""
    BASIC = "basic"
    DISORDERED = "disordered"
    CONSTRUCTION = "construction"
    ROTATING = "rotating"
    STAIRWELL = "stairwell"
    ELEVATOR = "elevator"
    INITIAL = "initial"

# Effect card subtypes
class EffectCardType(Enum):
    """Subtypes of effect cards"""
    SPECIAL_ITEM = "special_item"
    EVENT = "event"
    ANOMALY = "anomaly"

# =============================================================================
# SPECIAL SQUARES & LOCATIONS
# =============================================================================

class SpecialSquareType(Enum):
    """Types of special squares on tiles"""
    NORMAL = "normal"
    STAIRWELL = "stairwell"
    ELEVATOR_ROOM = "elevator_room"
    EVENT_SQUARE = "event_square"
    EMERGENCY_DOOR = "emergency_door"
    ITEM_SQUARE = "item_square"
    WALL = "wall"

# Special square effects
PASSING_EFFECTS = [
    SpecialSquareType.STAIRWELL,
    SpecialSquareType.ELEVATOR_ROOM,
    SpecialSquareType.EVENT_SQUARE
]

ENDING_EFFECTS = [
    SpecialSquareType.EMERGENCY_DOOR,
    SpecialSquareType.ITEM_SQUARE
]

# =============================================================================
# ZONES & BUILDING LAYOUT
# =============================================================================

# Building zones
ZONES = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
ZONE_COUNT = len(ZONES)

# Zone name cards (face-down until revealed)
ZONE_NAME_CARDS = [
    "Laboratory Wing",
    "Administrative Office",
    "Research Facility", 
    "Patient Ward",
    "Storage Area",
    "Maintenance Tunnel",
    "Observation Deck",
    "Emergency Exit"
]

# =============================================================================
# PLAYER ACTIONS
# =============================================================================

class ActionType(Enum):
    """Types of actions players can take"""
    MOVE = "move"
    EXPLORE = "explore" 
    FALL = "fall"
    MEET = "meet"
    ROB = "rob"
    USE_STAIRS = "use_stairs"
    USE_ELEVATOR = "use_elevator"
    USE_ITEM = "use_item"
    PASS = "pass"

# Action requirements
EXPLORE_REQUIREMENTS = {
    "max_disorder": DISORDER_FALL_THRESHOLD - 1,
    "movement_remaining": True
}

# =============================================================================
# INVENTORY & SLOTS
# =============================================================================

# Player inventory limits
MAX_ITEM_SLOTS = 6
MAX_EFFECT_SLOTS = 4
HAND_SIZE_LIMIT = 7

# =============================================================================
# TURN STRUCTURE
# =============================================================================

# Turn phases
class TurnPhase(Enum):
    """Phases within a single player turn"""
    MOVEMENT_ROLL = "movement_roll"
    MOVEMENT = "movement"
    PATH_END_ACTION = "path_end_action"
    TILE_EFFECTS = "tile_effects"
    PLAYER_INTERACTION = "player_interaction"
    END_TURN = "end_turn"

# =============================================================================
# CORRUPTION & MAP CHANGES
# =============================================================================

# Corruption mechanics (Phase 2+)
CORRUPTION_SPREAD_RATE = 0.05  # 5% per turn in mutation phase
BLOOD_CORRUPTION_COLOR = "#8B0000"  # Dark red for corrupted areas

# Elevator malfunction chance in Phase 2+
ELEVATOR_MALFUNCTION_CHANCE = 0.3  # 30%

# =============================================================================
# VALIDATION RULES
# =============================================================================

# Movement validation
MAX_MOVEMENT_PER_TURN = 6  # Based on D6
MIN_MOVEMENT_PER_TURN = 1

# Tile placement rules
TILE_PLACEMENT_ADJACENCY = True  # Must be adjacent to existing tiles
MAX_TILES_PER_FLOOR = 25  # Reasonable limit

# Player interaction distances
INTERACTION_DISTANCE = 0  # Must be on same tile
ROB_DISORDER_PENALTY = 1  # Disorder increase for robbing
MEET_DISORDER_REDUCTION = 1  # Disorder decrease for meeting

# =============================================================================
# GAME TIMING
# =============================================================================

# Session limits
MAX_GAME_DURATION_MINUTES = 120  # 2 hours
TURN_TIME_LIMIT_SECONDS = 60  # 1 minute per turn
IDLE_TIMEOUT_MINUTES = 10  # Auto-kick idle players

# =============================================================================
# ERROR MESSAGES
# =============================================================================

ERROR_MESSAGES = {
    "invalid_move": "Invalid movement path",
    "insufficient_movement": "Not enough movement points",
    "disorder_too_high": f"Disorder >= {DISORDER_FALL_THRESHOLD}, must Fall instead of Explore",
    "tile_placement_invalid": "Cannot place tile at this location",
    "player_not_found": "Player not found in game",
    "game_not_found": "Game session not found",
    "action_not_allowed": "Action not allowed in current game state",
    "inventory_full": "Inventory is full",
    "out_of_bounds": "Position is out of bounds"
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_disorder_description(disorder_level: int) -> str:
    """Get description for disorder level"""
    return DISORDER_EFFECTS.get(disorder_level, "Unknown disorder level")

def can_explore(disorder_level: int) -> bool:
    """Check if player can perform Explore action"""
    return disorder_level < DISORDER_FALL_THRESHOLD

def can_pass_walls(disorder_level: int) -> bool:
    """Check if player can pass through walls"""
    return disorder_level >= 7

def calculate_corruption_percentage(corrupted_tiles: int, total_tiles: int) -> float:
    """Calculate current corruption percentage"""
    if total_tiles == 0:
        return 0.0
    return corrupted_tiles / total_tiles

def is_game_lost(corruption_percentage: float) -> bool:
    """Check if game is lost due to corruption"""
    return corruption_percentage >= MAP_CORRUPTION_LIMIT

def get_current_phase(total_actions: int) -> GamePhase:
    """Determine current game phase based on actions taken"""
    if total_actions >= PHASE_THRESHOLDS[GamePhase.END_GAME]:
        return GamePhase.END_GAME
    elif total_actions >= PHASE_THRESHOLDS[GamePhase.MUTATION]:
        return GamePhase.MUTATION
    else:
        return GamePhase.EXPLORATION