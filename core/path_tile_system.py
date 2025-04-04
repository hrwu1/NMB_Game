import random
from core.constants import BOARD_SIZE, REGION_SIZE, MAP_SIZE, FLOOR_NUM

class PathTileSystem:
    def __init__(self):
        """Initialize path tile system"""
        # Path cards pool
        self.card_pool = self.generate_card_pool()
        
        # Game grid - stores each tile's status (white/black)
        self.grid = [[[False for _ in range(MAP_SIZE * REGION_SIZE)] for _ in range(MAP_SIZE * REGION_SIZE)] for _ in range(FLOOR_NUM)]
        
        # Placed regions - tracks which regions have been placed
        self.placed_regions = [set() for _ in range(FLOOR_NUM)]
        
        # Special tiles
        self.special_tiles = [dict() for _ in range(FLOOR_NUM)]  # {(x,y): 'stairs'/'elevator'}
        self.special_pos = [set() for _ in range(FLOOR_NUM)]  # For easy access to all special positions
        
        # Initial setup
        self.initialize_center_region()
        
        # Debug info
        print("Initial path tile setup complete")
        print(f"Initial placed regions: {self.placed_regions[0]}")
        print(f"Initial special tiles: {self.special_tiles[0]}")
    
    def get_special_tile(self, x, y, floor):
        """Get special tile at position
        
        Args:
            x: X coordinate
            y: Y coordinate
            floor: Floor
            
        Returns:
            Special tile type or None
        """
        pos = (x, y)
        if pos in self.special_tiles[floor]:
            return self.special_tiles[floor][pos]
        return None
    
    def add_special_tile(self, pos, floor, tile_type):
        """Add special tile
        
        Args:
            pos: Position (x, y)
            floor: Floor
            tile_type: Type of special tile ('stairs'/'elevator')
        """
        self.special_tiles[floor][pos] = tile_type
        self.special_pos[floor].add(pos)
        print(f"Added special tile {tile_type} at position {pos} on floor {floor}")
    
    def get_tile_status(self, x, y, floor):
        """Check if tile is accessible (white)
        
        Args:
            x: X coordinate
            y: Y coordinate
            floor: Floor
            
        Returns:
            True if tile is white (accessible), False otherwise
        """
        if 0 <= x < MAP_SIZE * REGION_SIZE and 0 <= y < MAP_SIZE * REGION_SIZE:
            return self.grid[floor][y][x]
        return False
    
    def get_unplaced_regions(self, floor):
        """Get unplaced regions for a floor
        
        Args:
            floor: Floor
            
        Returns:
            Set of unplaced regions
        """
        unplaced = set()
        for rx in range(MAP_SIZE):
            for ry in range(MAP_SIZE):
                if (rx, ry) not in self.placed_regions[floor]:
                    unplaced.add((rx, ry))
        return unplaced
    
    def initialize_center_region(self):
        """初始化中央区域，只初始化地图中心的一个4×4区域"""
        # 计算中心区域的位置
        center_x, center_y = MAP_SIZE // 2, MAP_SIZE // 2
        
        # 使用全白色瓦片初始化中央区域（全1表示所有格子都是白色可通行的）
        card = 0xFFFF  # 16位全为1，表示4×4区域内所有格子都是白色
        
        # 在第1层（索引为1）的中央区域放置卡片
        self.place_card(card, center_x, center_y, 1, 0)
        
        # 确保该区域被标记为已放置
        self.placed_regions[1].add((center_x, center_y))
        
        # 不再初始化周围区域，只保留中央的一个4×4区域
        
        print(f"初始化中央区域完成：在楼层1的中心位置({center_x}, {center_y})放置了初始卡片")
        print(f"楼层1已放置区域: {self.placed_regions[1]}")
        print(f"楼层0已放置区域: {self.placed_regions[0]}")
    
    def place_card(self, card, region_x, region_y, floor, rotation=0):
        """Place a path card in a region
        
        Args:
            card: Card value
            region_x: Region X
            region_y: Region Y
            floor: Floor
            rotation: Rotation (0-3)
        """
        # Apply rotation
        rotated_card = self.rotate_card(card, rotation)
        
        # Calculate start position
        start_x = region_x * REGION_SIZE
        start_y = region_y * REGION_SIZE
        
        # Place the card
        for y in range(REGION_SIZE):
            for x in range(REGION_SIZE):
                # Get bit position based on x,y
                bit_pos = y * REGION_SIZE + x
                
                # Check if the bit is set (white tile)
                is_white = (rotated_card & (1 << bit_pos)) != 0
                
                # Set grid value
                self.grid[floor][start_y + y][start_x + x] = is_white
        
        # Mark region as placed
        self.placed_regions[floor].add((region_x, region_y))
    
    def rotate_card(self, card, rotation):
        """Rotate a card
        
        Args:
            card: Card value
            rotation: Rotation count (0-3)
            
        Returns:
            Rotated card value
        """
        # No rotation needed
        if rotation == 0:
            return card
        
        # Apply rotation
        rotated = 0
        for r in range(rotation):
            # Extract each bit and place it in rotated position
            for y in range(REGION_SIZE):
                for x in range(REGION_SIZE):
                    bit_pos = y * REGION_SIZE + x
                    if card & (1 << bit_pos):
                        # Calculate new position after 90-degree rotation
                        new_x = REGION_SIZE - 1 - y
                        new_y = x
                        new_pos = new_y * REGION_SIZE + new_x
                        rotated |= (1 << new_pos)
            
            # Update card for next rotation if needed
            card = rotated
            if r < rotation - 1:
                rotated = 0
        
        return rotated
    
    def generate_card_pool(self):
        """Generate card pool
        
        Returns:
            List of card values
        """
        # Define some sample path cards
        cards = [
            0x6996,  # Cross
            0xF999,  # T-junction
            0xCC66,  # Corner
            0xF0F0,  # Straight
            0xFFCC,  # Half-filled
            0xAAAA,  # Checkerboard
            0xFFFF,  # All white
            0x0FF0,  # Center filled
        ]
        
        # Create a larger pool with variations
        pool = []
        for card in cards:
            # Add the card and its rotations
            for r in range(4):
                rotated = self.rotate_card(card, r)
                if rotated not in pool:
                    pool.append(rotated)
        
        # Duplicate some cards to adjust probabilities
        full_pool = pool * 4
        
        # Shuffle the pool
        random.shuffle(full_pool)
        
        return full_pool
    
    def draw_card(self):
        """Draw a card from the pool
        
        Returns:
            Card value or None if pool is empty
        """
        if self.card_pool:
            return self.card_pool.pop()
        return None
    
    def find_legal_position(self, region_x=None, region_y=None, floor=None, all_floors=False):
        """Find a legal position for special tile or exit
        
        Args:
            region_x: Region X coordinate
            region_y: Region Y coordinate
            floor: Floor
            all_floors: Whether to search all floors
        
        Returns:
            Position (floor, (x, y)) or ((region_x, region_y), (x, y)) depending on call context
        """
        if all_floors:
            # Find a legal position on any floor
            for f in range(FLOOR_NUM):
                for rx, ry in self.placed_regions[f]:
                    legal_pos = self._find_position_in_region(rx, ry, f)
                    if legal_pos:
                        return (f, legal_pos)
            return (-1, (-1, -1))
        
        if region_x is not None and region_y is not None and floor is not None:
            # Find a legal position in a specific region
            return ((region_x, region_y), self._find_position_in_region(region_x, region_y, floor))
        
        return None

    def _find_position_in_region(self, region_x, region_y, floor):
        """Find a legal position within a region
        
        Args:
            region_x: Region X coordinate
            region_y: Region Y coordinate
            floor: Floor
        
        Returns:
            Position (x, y) or None if not found
        """
        # Check if region is placed
        if (region_x, region_y) not in self.placed_regions[floor]:
            return None
        
        # Check all tiles in the region
        for x in range(REGION_SIZE):
            for y in range(REGION_SIZE):
                abs_x = region_x * REGION_SIZE + x
                abs_y = region_y * REGION_SIZE + y
                
                # Check if tile is white (accessible)
                if self.get_tile_status(abs_x, abs_y, floor):
                    # Check if position is already used for a special tile
                    if (abs_x, abs_y) not in self.special_tiles[floor]:
                        return (abs_x, abs_y)
        
        return None

    def _hex_to_grid(self, card):
        """Convert a hexadecimal card value to a 2D grid
        
        Args:
            card: Card value in hexadecimal format
        
        Returns:
            2D grid of booleans (True for white, False for black)
        """
        grid = [[False for _ in range(REGION_SIZE)] for _ in range(REGION_SIZE)]
        
        for y in range(REGION_SIZE):
            for x in range(REGION_SIZE):
                bit_pos = y * REGION_SIZE + x
                grid[y][x] = (card & (1 << bit_pos)) != 0
        
        return grid 