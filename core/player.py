import pygame
from core.constants import TILE_SIZE

class Player:
    def __init__(self, id, color, name=None):
        """Initialize player
        
        Args:
            id: Player ID
            color: Player color
            name: Player name, if None defaults to "Player{id+1}"
        """
        self.id = id
        self.name = name if name else f"Player{id+1}"
        self.color = color
        
        # Position related
        self.pos = None  # Initial position to be selected
        self.floor = 1   # Initial floor is 1
        
        # Status
        self.daze = 0    # Confusion value
        
        # Drawing related
        self.rect = pygame.Rect(0, 0, TILE_SIZE // 2, TILE_SIZE // 2)
    
    def set_position(self, x, y):
        """Set player position
        
        Args:
            x: x coordinate
            y: y coordinate
        """
        self.pos = (x, y)
    
    def set_floor(self, floor):
        """Set player floor
        
        Args:
            floor: Floor
        """
        self.floor = floor
    
    def add_daze(self, value):
        """Add confusion value
        
        Args:
            value: Confusion value to add
        """
        self.daze += value
    
    def draw(self, screen, board_offset, current=False):
        """Draw player
        
        Args:
            screen: Screen object
            board_offset: Board offset
            current: Whether this is the current player
        """
        if self.pos:
            x, y = self.pos
            self.rect.topleft = (
                board_offset[0] + x * TILE_SIZE + TILE_SIZE // 4,
                board_offset[1] + y * TILE_SIZE + TILE_SIZE // 4
            )
            pygame.draw.rect(screen, self.color, self.rect)
            
            # If this is the current player, add yellow marker
            if current:
                pygame.draw.circle(screen, (255, 255, 0), self.rect.center, TILE_SIZE // 6)
    
    def get_info_text(self, font, is_current=False):
        """Get player info text
        
        Args:
            font: Font object
            is_current: Whether this is the current player
            
        Returns:
            Rendered player info text
        """
        color = self.color if not is_current else (255, 255, 0)
        return font.render(f"{self.name} (F{self.floor+1}), Confusion: {self.daze}", True, color) 