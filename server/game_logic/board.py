"""
Board class for NMB Game.
Manages the multi-floor 3D map, path tiles, zones, and special locations.
"""

from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid
import random

from .constants import (
    FLOOR_COUNT, FLOOR_RANGE, STARTING_FLOOR, BOARD_SIZE, ZONES, ZONE_COUNT,
    PathTileType, SpecialSquareType, INITIAL_POSITION, ZONE_NAME_CARDS,
    MAP_CORRUPTION_LIMIT, calculate_corruption_percentage, is_game_lost
)

@dataclass
class TilePosition:
    """Represents a tile position on the board (for tile placement)"""
    x: int  # Tile grid X (0-9)
    y: int  # Tile grid Y (0-9) 
    floor: int
    
    def __post_init__(self):
        """Validate tile position bounds"""
        if not (0 <= self.x < BOARD_SIZE[0] and 0 <= self.y < BOARD_SIZE[1]):
            raise ValueError(f"Tile position ({self.x}, {self.y}) out of bounds")
        if self.floor not in range(*FLOOR_RANGE):
            raise ValueError(f"Floor {self.floor} out of range {FLOOR_RANGE}")
    
    def to_tuple(self) -> Tuple[int, int, int]:
        return (self.x, self.y, self.floor)
    
    def get_adjacent_positions(self, include_current_floor_only=False) -> List['TilePosition']:
        """Get adjacent tile positions for tile-level operations"""
        adjacent = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue  # Skip current position
                
                new_x, new_y = self.x + dx, self.y + dy
                
                # Check bounds
                if 0 <= new_x < BOARD_SIZE[0] and 0 <= new_y < BOARD_SIZE[1]:
                    try:
                        if include_current_floor_only:
                            adjacent.append(TilePosition(new_x, new_y, self.floor))
                        else:
                            # Include all floors for full adjacency
                            for floor in range(*FLOOR_RANGE):
                                adjacent.append(TilePosition(new_x, new_y, floor))
                    except ValueError:
                        continue  # Skip invalid positions
        
        return adjacent

@dataclass
class Position:
    """Represents a sub-position on the board (for player movement)"""
    tile_x: int    # Which tile (0-3)
    tile_y: int    # Which tile (0-3)
    sub_x: int     # Position within tile (0-3)
    sub_y: int     # Position within tile (0-3)
    floor: int
    
    def __post_init__(self):
        """Validate position bounds"""
        if not (0 <= self.tile_x < BOARD_SIZE[0] and 0 <= self.tile_y < BOARD_SIZE[1]):
            raise ValueError(f"Tile position ({self.tile_x}, {self.tile_y}) out of bounds")
        if not (0 <= self.sub_x < 4 and 0 <= self.sub_y < 4):
            raise ValueError(f"Sub-position ({self.sub_x}, {self.sub_y}) out of bounds (must be 0-3)")
        if self.floor not in range(*FLOOR_RANGE):
            raise ValueError(f"Floor {self.floor} out of range {FLOOR_RANGE}")
    
    def __hash__(self):
        return hash((self.tile_x, self.tile_y, self.sub_x, self.sub_y, self.floor))
    
    def __eq__(self, other):
        if isinstance(other, Position):
            return (self.tile_x == other.tile_x and self.tile_y == other.tile_y and 
                   self.sub_x == other.sub_x and self.sub_y == other.sub_y and 
                   self.floor == other.floor)
        return False
    
    def to_tuple(self) -> Tuple[int, int, int, int, int]:
        """Convert to tuple for easy comparison"""
        return (self.tile_x, self.tile_y, self.sub_x, self.sub_y, self.floor)
    
    def get_tile_position(self) -> TilePosition:
        """Get the tile position this sub-position belongs to"""
        return TilePosition(self.tile_x, self.tile_y, self.floor)
    
    def to_absolute_coords(self) -> Tuple[int, int]:
        """Convert to absolute board coordinates for display"""
        abs_x = self.tile_x * 4 + self.sub_x
        abs_y = self.tile_y * 4 + self.sub_y
        return (abs_x, abs_y)
    
    def get_adjacent_positions(self, include_current_floor_only=False) -> List['Position']:
        """Get all adjacent sub-positions (within same tile and adjacent tiles)"""
        adjacent = []
        
        # Adjacent positions within same tile and adjacent tiles
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue  # Skip current position
                
                new_sub_x = self.sub_x + dx
                new_sub_y = self.sub_y + dy
                new_tile_x = self.tile_x
                new_tile_y = self.tile_y
                
                # Handle crossing tile boundaries
                if new_sub_x < 0:
                    new_tile_x -= 1
                    new_sub_x = 3
                elif new_sub_x > 3:
                    new_tile_x += 1
                    new_sub_x = 0
                    
                if new_sub_y < 0:
                    new_tile_y -= 1
                    new_sub_y = 3
                elif new_sub_y > 3:
                    new_tile_y += 1
                    new_sub_y = 0
                
                # Check tile bounds
                if 0 <= new_tile_x < BOARD_SIZE[0] and 0 <= new_tile_y < BOARD_SIZE[1]:
                    try:
                        if include_current_floor_only:
                            adjacent.append(Position(new_tile_x, new_tile_y, new_sub_x, new_sub_y, self.floor))
                        else:
                            # Include all floors for full adjacency
                            for floor in range(*FLOOR_RANGE):
                                adjacent.append(Position(new_tile_x, new_tile_y, new_sub_x, new_sub_y, floor))
                    except ValueError:
                        continue  # Skip invalid positions
        
        return adjacent

@dataclass 
class PathTile:
    """Represents a path tile on the board"""
    tile_id: str
    tile_type: PathTileType
    position: TilePosition  # Tile grid position
    rotation: int = 0  # 0, 90, 180, 270 degrees
    special_squares: Dict[Tuple[int, int], SpecialSquareType] = field(default_factory=dict)
    zone: Optional[str] = None  # A-H
    is_corrupted: bool = False
    is_removed: bool = False  # For stairwells that are removed after use
    connections: List[Tuple[int, int]] = field(default_factory=list)  # Valid paths within tile
    movable_positions: Set[Tuple[int, int]] = field(default_factory=set)  # Which sub-positions can be moved to
    
    def __post_init__(self):
        """Initialize tile with default layout"""
        if not self.tile_id:
            self.tile_id = str(uuid.uuid4())[:8]
        
        # Set up default 4x4 tile layout if not specified
        if not self.special_squares:
            self.special_squares = self._generate_default_layout()
        
        # Set up connections if not specified
        if not self.connections:
            self.connections = self._generate_default_connections()
        
        # Generate movable positions based on special squares
        if not self.movable_positions:
            self.movable_positions = self._generate_movable_positions()
    
    def _generate_default_layout(self) -> Dict[Tuple[int, int], SpecialSquareType]:
        """Generate default 4x4 tile layout"""
        layout = {}
        
        # Fill with normal squares
        for x in range(4):
            for y in range(4):
                layout[(x, y)] = SpecialSquareType.NORMAL
        
        # Add special squares based on tile type
        if self.tile_type == PathTileType.STAIRWELL:
            layout[(1, 1)] = SpecialSquareType.STAIRWELL
            layout[(2, 2)] = SpecialSquareType.STAIRWELL
        elif self.tile_type == PathTileType.ELEVATOR:
            layout[(1, 1)] = SpecialSquareType.ELEVATOR_ROOM
            layout[(2, 1)] = SpecialSquareType.ELEVATOR_ROOM
            layout[(1, 2)] = SpecialSquareType.ELEVATOR_ROOM
            layout[(2, 2)] = SpecialSquareType.ELEVATOR_ROOM
        elif self.tile_type == PathTileType.BASIC:
            # Add some random special squares
            if random.random() < 0.3:  # 30% chance
                layout[(random.randint(0, 3), random.randint(0, 3))] = SpecialSquareType.EVENT_SQUARE
            if random.random() < 0.2:  # 20% chance
                layout[(random.randint(0, 3), random.randint(0, 3))] = SpecialSquareType.ITEM_SQUARE
        
        return layout
    
    def _generate_default_connections(self) -> List[Tuple[int, int]]:
        """Generate default path connections within tile"""
        connections = []
        
        # Create basic cross pattern for normal tiles
        for x in range(4):
            for y in range(4):
                # Connect to adjacent squares
                for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < 4 and 0 <= ny < 4:
                        connections.append(((x, y), (nx, ny)))
        
        return connections
    
    def _generate_movable_positions(self) -> Set[Tuple[int, int]]:
        """Generate which sub-positions within this tile can be moved to"""
        movable = set()
        
        for x in range(4):
            for y in range(4):
                square_type = self.special_squares.get((x, y), SpecialSquareType.NORMAL)
                
                # For now, randomly make some positions movable (later we can define this manually)
                if square_type == SpecialSquareType.WALL:
                    # Walls are never movable (except with high disorder)
                    continue
                elif square_type in [SpecialSquareType.NORMAL, SpecialSquareType.EVENT_SQUARE, 
                                   SpecialSquareType.ITEM_SQUARE, SpecialSquareType.EMERGENCY_DOOR,
                                   SpecialSquareType.STAIRWELL, SpecialSquareType.ELEVATOR_ROOM]:
                    # These are always movable
                    movable.add((x, y))
                else:
                    # For other types, randomly decide (70% chance movable)
                    if random.random() < 0.7:
                        movable.add((x, y))
        
        # Ensure at least some positions are movable
        if not movable:
            # If no positions are movable, make corners movable
            movable.update([(0, 0), (0, 3), (3, 0), (3, 3)])
        
        return movable
    
    def can_enter_square(self, local_pos: Tuple[int, int], player_disorder: int = 0) -> bool:
        """Check if a sub-position within this tile can be entered"""
        # First check if it's a movable position
        if local_pos not in self.movable_positions:
            # Check if it's a wall that high disorder can pass through
            square_type = self.special_squares.get(local_pos, SpecialSquareType.NORMAL)
            if square_type == SpecialSquareType.WALL:
                from .constants import can_pass_walls
                return can_pass_walls(player_disorder)
            return False
        
        return True
    
    def is_position_movable(self, local_pos: Tuple[int, int]) -> bool:
        """Check if a sub-position within this tile is movable"""
        return local_pos in self.movable_positions
    
    def get_entrance_points(self) -> List[Tuple[int, int]]:
        """Get valid entrance points to this tile"""
        # Return all movable positions on the edges of the tile
        entrance_points = []
        
        # Check edges - prioritize edge positions for entrances
        for x in range(4):
            for y in [0, 3]:  # Top and bottom edges
                if (x, y) in self.movable_positions:
                    entrance_points.append((x, y))
        
        for y in range(1, 3):  # Middle rows (avoid corners we already checked)
            for x in [0, 3]:  # Left and right edges
                if (x, y) in self.movable_positions:
                    entrance_points.append((x, y))
        
        # If no edge positions are movable, return any movable position
        if not entrance_points and self.movable_positions:
            entrance_points = list(self.movable_positions)[:4]  # Take first few
        
        return entrance_points if entrance_points else [(1, 1)]  # Fallback to center
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tile to dictionary for serialization"""
        return {
            "tile_id": self.tile_id,
            "tile_type": self.tile_type.value,
            "position": {
                "x": self.position.x,
                "y": self.position.y,
                "floor": self.position.floor
            },
            "rotation": self.rotation,
            "special_squares": {f"{k[0]},{k[1]}": v.value for k, v in self.special_squares.items()},
            "zone": self.zone,
            "is_corrupted": self.is_corrupted,
            "is_removed": self.is_removed,
            "connections": self.connections,
            "entrance_points": self.get_entrance_points(),
            "movable_positions": [{"x": pos[0], "y": pos[1]} for pos in self.movable_positions]
        }

class Board:
    """Manages the game board state"""
    
    def __init__(self):
        # Multi-floor tile storage: floor -> (x,y) -> PathTile
        self.floors: Dict[int, Dict[Tuple[int, int], PathTile]] = {}
        
        # Initialize empty floors
        for floor in range(*FLOOR_RANGE):
            self.floors[floor] = {}
        
        # Zone management
        self.zone_assignments: Dict[Tuple[int, int], str] = {}  # (x,y) -> zone letter
        self.zone_names: Dict[str, Optional[str]] = {zone: None for zone in ZONES}
        self.available_zone_names = ZONE_NAME_CARDS.copy()
        random.shuffle(self.available_zone_names)
        
        # Corruption tracking
        self.corrupted_tiles: Set[str] = set()  # tile_ids
        self.corruption_spread_rate = 0.0
        
        # Special locations
        self.stairwells: Dict[int, List[Position]] = {}  # floor -> list of stairwell positions
        self.elevators: Dict[int, List[Position]] = {}   # floor -> list of elevator positions
        self.escape_exits: List[Position] = []  # Available escape points
        
        # Initialize with starting tile
        self._create_initial_tile()
    
    def _create_initial_tile(self) -> None:
        """Create the initial path tile on floor 2"""
        initial_tile_pos = TilePosition(INITIAL_POSITION[0], INITIAL_POSITION[1], STARTING_FLOOR)
        initial_tile = PathTile(
            tile_id="initial_tile",
            tile_type=PathTileType.INITIAL,
            position=initial_tile_pos,
            zone="B"  # Starting zone
        )
        
        self.place_tile(initial_tile)
        self.zone_assignments[(INITIAL_POSITION[0], INITIAL_POSITION[1])] = "B"
    
    # =============================================================================
    # TILE MANAGEMENT
    # =============================================================================
    
    def place_tile(self, tile: PathTile) -> bool:
        """Place a tile on the board"""
        floor = tile.position.floor
        pos_key = (tile.position.x, tile.position.y)
        
        # Check if position is already occupied
        if pos_key in self.floors[floor]:
            return False
        
        # For non-initial tiles, check adjacency
        if tile.tile_type != PathTileType.INITIAL:
            if not self._has_adjacent_tile(tile.position):
                return False
        
        # Place the tile
        self.floors[floor][pos_key] = tile
        
        # Assign zone if needed
        if not tile.zone:
            tile.zone = self._assign_zone(tile.position)
        
        # Update special location tracking
        self._update_special_locations(tile)
        
        print(f"Placed {tile.tile_type.value} tile at {tile.position.to_tuple()}")
        return True
    
    def remove_tile(self, position: Position) -> Optional[PathTile]:
        """Remove a tile from the board (used for stairwells)"""
        floor = position.floor
        pos_key = (position.x, position.y)
        
        if pos_key in self.floors[floor]:
            tile = self.floors[floor].pop(pos_key)
            tile.is_removed = True
            
            # Remove from special locations
            if tile.tile_type == PathTileType.STAIRWELL:
                if floor in self.stairwells:
                    self.stairwells[floor] = [p for p in self.stairwells[floor] if p != position]
            
            print(f"Removed tile from {position.to_tuple()}")
            return tile
        
        return None
    
    def get_tile_at_tile_pos(self, tile_position: TilePosition) -> Optional[PathTile]:
        """Get tile at specific tile position"""
        floor = tile_position.floor
        pos_key = (tile_position.x, tile_position.y)
        return self.floors[floor].get(pos_key)
    
    def get_tile_at_position(self, position: Position) -> Optional[PathTile]:
        """Get tile that contains the specified sub-position"""
        tile_pos = TilePosition(position.tile_x, position.tile_y, position.floor)
        return self.get_tile_at_tile_pos(tile_pos)
    
    def get_tile(self, position) -> Optional[PathTile]:
        """Get tile at position (supports both TilePosition and Position)"""
        if isinstance(position, TilePosition):
            return self.get_tile_at_tile_pos(position)
        elif isinstance(position, Position):
            return self.get_tile_at_position(position)
        else:
            # Legacy support - assume it's a Position-like object with x, y, floor
            floor = position.floor
            pos_key = (position.x, position.y)
            return self.floors[floor].get(pos_key)
    
    def is_position_movable(self, position: Position) -> bool:
        """Check if a sub-position can be moved to"""
        tile = self.get_tile_at_position(position)
        if not tile:
            return False
        
        if tile.is_corrupted or tile.is_removed:
            return False
        
        return tile.is_position_movable((position.sub_x, position.sub_y))
    
    def _has_adjacent_tile(self, position) -> bool:
        """Check if position has at least one adjacent tile"""
        if isinstance(position, TilePosition):
            # For tile placement, check adjacent tile positions
            adjacent_tile_positions = position.get_adjacent_positions(include_current_floor_only=True)
            
            for adj_tile_pos in adjacent_tile_positions:
                if self.get_tile_at_tile_pos(adj_tile_pos) is not None:
                    return True
        else:
            # For sub-position checks, check adjacent sub-positions
            adjacent_positions = position.get_adjacent_positions(include_current_floor_only=True)
            
            for adj_pos in adjacent_positions:
                if self.get_tile(adj_pos) is not None:
                    return True
        
        return False
    
    def _update_special_locations(self, tile: PathTile) -> None:
        """Update tracking of special locations"""
        floor = tile.position.floor
        
        if tile.tile_type == PathTileType.STAIRWELL:
            if floor not in self.stairwells:
                self.stairwells[floor] = []
            self.stairwells[floor].append(tile.position)
        
        elif tile.tile_type == PathTileType.ELEVATOR:
            if floor not in self.elevators:
                self.elevators[floor] = []
            self.elevators[floor].append(tile.position)
    
    # =============================================================================
    # ZONE MANAGEMENT
    # =============================================================================
    
    def _assign_zone(self, position) -> str:
        """Assign a zone to a tile position"""
        if isinstance(position, TilePosition):
            pos_key = (position.x, position.y)
        else:
            # Handle legacy Position objects
            pos_key = (position.tile_x, position.tile_y)
        
        # Check if already assigned
        if pos_key in self.zone_assignments:
            return self.zone_assignments[pos_key]
        
        # Check adjacent tiles for zone continuity
        adjacent_positions = position.get_adjacent_positions(include_current_floor_only=True)
        adjacent_zones = set()
        
        for adj_pos in adjacent_positions:
            if isinstance(adj_pos, TilePosition):
                adj_key = (adj_pos.x, adj_pos.y)
            else:
                adj_key = (adj_pos.tile_x, adj_pos.tile_y)
            
            if adj_key in self.zone_assignments:
                adjacent_zones.add(self.zone_assignments[adj_key])
        
        # If adjacent to existing zones, use one of them
        if adjacent_zones:
            chosen_zone = random.choice(list(adjacent_zones))
        else:
            # Assign new zone
            unassigned_zones = [zone for zone in ZONES 
                              if zone not in self.zone_assignments.values()]
            chosen_zone = random.choice(unassigned_zones) if unassigned_zones else random.choice(ZONES)
        
        self.zone_assignments[pos_key] = chosen_zone
        return chosen_zone
    
    def reveal_zone_name(self, zone_letter: str) -> Optional[str]:
        """Reveal the name of a zone"""
        if zone_letter not in ZONES:
            return None
        
        if self.zone_names[zone_letter] is not None:
            return self.zone_names[zone_letter]
        
        if not self.available_zone_names:
            return None
        
        # Assign random name
        zone_name = self.available_zone_names.pop(0)
        self.zone_names[zone_letter] = zone_name
        
        # Check for duplicates (causes reshuffle in actual game)
        existing_names = [name for name in self.zone_names.values() if name is not None]
        if existing_names.count(zone_name) > 1:
            # Reshuffle all zone names
            self._reshuffle_zone_names()
        
        return self.zone_names[zone_letter]
    
    def _reshuffle_zone_names(self) -> None:
        """Reshuffle all zone names when duplicate is found"""
        # Collect all assigned names back
        assigned_names = [name for name in self.zone_names.values() if name is not None]
        self.available_zone_names.extend(assigned_names)
        
        # Clear assignments
        for zone in ZONES:
            self.zone_names[zone] = None
        
        # Shuffle and reassign
        random.shuffle(self.available_zone_names)
        print("Zone names reshuffled due to duplicate!")
    
    # =============================================================================
    # CORRUPTION SYSTEM
    # =============================================================================
    
    def corrupt_tile(self, tile_id: str) -> bool:
        """Mark a tile as corrupted"""
        if tile_id not in self.corrupted_tiles:
            self.corrupted_tiles.add(tile_id)
            print(f"Tile {tile_id} became corrupted")
            return True
        return False
    
    def spread_corruption(self, spread_rate: float = 0.05) -> List[str]:
        """Spread corruption to adjacent tiles"""
        newly_corrupted = []
        all_tiles = self.get_all_tiles()
        
        # Find tiles adjacent to corrupted ones
        corruption_candidates = set()
        for tile_id in self.corrupted_tiles:
            tile = self._find_tile_by_id(tile_id)
            if tile:
                adjacent_positions = tile.position.get_adjacent_positions(include_current_floor_only=True)
                for adj_pos in adjacent_positions:
                    adj_tile = self.get_tile(adj_pos)
                    if adj_tile and adj_tile.tile_id not in self.corrupted_tiles:
                        corruption_candidates.add(adj_tile.tile_id)
        
        # Randomly corrupt some candidates
        for candidate_id in corruption_candidates:
            if random.random() < spread_rate:
                if self.corrupt_tile(candidate_id):
                    newly_corrupted.append(candidate_id)
        
        return newly_corrupted
    
    def get_corruption_percentage(self) -> float:
        """Calculate current corruption percentage"""
        total_tiles = sum(len(floor_tiles) for floor_tiles in self.floors.values())
        return calculate_corruption_percentage(len(self.corrupted_tiles), total_tiles)
    
    def is_game_lost_to_corruption(self) -> bool:
        """Check if game is lost due to corruption"""
        return is_game_lost(self.get_corruption_percentage())
    
    # =============================================================================
    # PATHFINDING & MOVEMENT
    # =============================================================================
    
    def get_valid_moves_from_position(self, position: Position, movement_points: int, 
                                     player_disorder: int = 0) -> List[Position]:
        """Get all valid positions reachable with given movement points"""
        valid_positions = set()
        to_check = [(position, 0)]  # (position, movement_used)
        checked = set()
        
        while to_check:
            current_pos, movement_used = to_check.pop(0)
            
            if movement_used > movement_points:
                continue
            
            pos_key = current_pos.to_tuple()
            if pos_key in checked:
                continue
            checked.add(pos_key)
            
            if movement_used > 0:  # Don't include starting position
                valid_positions.add(current_pos)
            
            # Get adjacent positions
            adjacent = current_pos.get_adjacent_positions(include_current_floor_only=True)
            for adj_pos in adjacent:
                tile = self.get_tile(adj_pos)
                if tile and not tile.is_corrupted and not tile.is_removed:
                    # Check if player can enter this tile
                    entrance_points = tile.get_entrance_points()
                    if entrance_points:  # If there are valid entrance points
                        to_check.append((adj_pos, movement_used + 1))
        
        return list(valid_positions)
    
    def find_path(self, start: Position, end: Position, player_disorder: int = 0) -> Optional[List[Position]]:
        """Find path between two positions using A* algorithm"""
        from heapq import heappush, heappop
        
        def heuristic(pos1: Position, pos2: Position) -> float:
            return abs(pos1.x - pos2.x) + abs(pos1.y - pos2.y) + abs(pos1.floor - pos2.floor) * 2
        
        open_set = [(0, start)]
        came_from = {}
        g_score = {start: 0}
        f_score = {start: heuristic(start, end)}
        
        while open_set:
            current = heappop(open_set)[1]
            
            if current == end:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return list(reversed(path))
            
            # Check neighbors
            adjacent = current.get_adjacent_positions()
            for neighbor in adjacent:
                tile = self.get_tile(neighbor)
                if not tile or tile.is_corrupted or tile.is_removed:
                    continue
                
                tentative_g = g_score[current] + 1
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + heuristic(neighbor, end)
                    heappush(open_set, (f_score[neighbor], neighbor))
        
        return None  # No path found
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def get_all_tiles(self) -> List[PathTile]:
        """Get all tiles on the board"""
        tiles = []
        for floor_tiles in self.floors.values():
            tiles.extend(floor_tiles.values())
        return [tile for tile in tiles if not tile.is_removed]
    
    def get_tiles_on_floor(self, floor: int) -> List[PathTile]:
        """Get all tiles on a specific floor"""
        if floor in self.floors:
            return [tile for tile in self.floors[floor].values() if not tile.is_removed]
        return []
    
    def get_players_on_tile(self, position: Position, players: List) -> List:
        """Get all players on a specific tile"""
        return [player for player in players 
                if player.floor == position.floor and 
                   player.position == (position.x, position.y)]
    
    def _find_tile_by_id(self, tile_id: str) -> Optional[PathTile]:
        """Find tile by its ID"""
        for floor_tiles in self.floors.values():
            for tile in floor_tiles.values():
                if tile.tile_id == tile_id:
                    return tile
        return None
    
    def get_board_state(self) -> Dict[str, Any]:
        """Get current board state for serialization"""
        return {
            "floors": {
                str(floor): {
                    f"{pos[0]},{pos[1]}": tile.to_dict()
                    for pos, tile in floor_tiles.items()
                    if not tile.is_removed
                }
                for floor, floor_tiles in self.floors.items()
            },
            "zone_assignments": {
                f"{pos[0]},{pos[1]}": zone 
                for pos, zone in self.zone_assignments.items()
            },
            "zone_names": {
                zone: name for zone, name in self.zone_names.items() 
                if name is not None
            },
            "corruption": {
                "corrupted_tiles": list(self.corrupted_tiles),
                "corruption_percentage": self.get_corruption_percentage(),
                "game_lost": self.is_game_lost_to_corruption()
            },
            "special_locations": {
                "stairwells": {
                    str(floor): [pos.to_tuple() for pos in positions]
                    for floor, positions in self.stairwells.items()
                },
                "elevators": {
                    str(floor): [pos.to_tuple() for pos in positions]
                    for floor, positions in self.elevators.items()
                },
                "escape_exits": [pos.to_tuple() for pos in self.escape_exits]
            }
        }
    
    def __str__(self) -> str:
        tile_count = sum(len(floor) for floor in self.floors.values())
        return f"Board({tile_count} tiles, {len(self.corrupted_tiles)} corrupted, {self.get_corruption_percentage():.1%} corruption)"