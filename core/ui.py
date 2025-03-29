import pygame
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, BOARD_SIZE, REGION_SIZE, MAP_SIZE, FLOOR_NUM
import math

class Button:
    def __init__(self, rect, text, color=(100, 100, 200), hover_color=None, text_color=(255, 255, 255)):
        """Initialize button
        
        Args:
            rect: Button rectangle
            text: Button text
            color: Button color
            hover_color: Color when mouse hovers over button (defaults to lighter version of color)
            text_color: Color of the button text
        """
        self.rect = rect
        self.text = text
        self.color = color
        self.hover_color = hover_color or self._get_lighter_color(color)
        self.text_color = text_color
        self.font = pygame.font.Font(None, 30)
        self.is_hovered = False
        self.border_radius = 8  # Rounded corners
    
    def _get_lighter_color(self, color):
        """Get a lighter version of the color
        
        Args:
            color: Base color
            
        Returns:
            Lighter color
        """
        return tuple(min(c + 40, 255) for c in color)
    
    def draw(self, screen):
        """Draw the button
        
        Args:
            screen: Screen to draw on
        """
        # Check if mouse is hovering over button
        mouse_pos = pygame.mouse.get_pos()
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        
        # Draw button background with rounded corners
        pygame.draw.rect(
            screen, 
            self.hover_color if self.is_hovered else self.color, 
            self.rect,
            border_radius=self.border_radius
        )
        
        # Draw border (slightly darker than button color)
        border_color = tuple(max(c - 30, 0) for c in self.color)
        pygame.draw.rect(
            screen, 
            border_color, 
            self.rect, 
            width=2,
            border_radius=self.border_radius
        )
        
        # Draw text with slight shadow for better visibility
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        
        # Draw shadow
        shadow_surf = self.font.render(self.text, True, (30, 30, 30))
        shadow_rect = shadow_surf.get_rect(center=(text_rect.centerx + 1, text_rect.centery + 1))
        screen.blit(shadow_surf, shadow_rect)
        
        # Draw text
        screen.blit(text_surf, text_rect)
    
    def is_clicked(self, pos):
        """Check if button is clicked
        
        Args:
            pos: Mouse position
            
        Returns:
            Whether button is clicked
        """
        return self.rect.collidepoint(pos)


class InfoPanel:
    def __init__(self, rect, color=(40, 40, 60), border_color=(80, 80, 100)):
        """Initialize info panel
        
        Args:
            rect: Panel rectangle
            color: Panel color
            border_color: Panel border color
        """
        self.rect = rect
        self.color = color
        self.border_color = border_color
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 42)
        self.border_radius = 10  # Rounded corners
        
        # Section separators
        self.section_margin = 15
    
    def draw(self, screen):
        """Draw panel background
        
        Args:
            screen: Screen object
        """
        # Draw main panel with rounded corners
        pygame.draw.rect(
            screen, 
            self.color, 
            self.rect,
            border_radius=self.border_radius
        )
        
        # Draw panel border
        pygame.draw.rect(
            screen, 
            self.border_color, 
            self.rect, 
            width=2,
            border_radius=self.border_radius
        )
    
    def draw_text(self, screen, text, pos, color=(255, 255, 255), small=False, is_title=False):
        """Draw text
        
        Args:
            screen: Screen object
            text: Text content
            pos: Position
            color: Text color
            small: Whether to use small font
            is_title: Whether text is a title
        """
        if is_title:
            font = self.title_font
        else:
            font = self.small_font if small else self.font
            
        # Draw text with shadow for better visibility
        shadow_surf = font.render(text, True, (30, 30, 30))
        screen.blit(shadow_surf, (pos[0] + 1, pos[1] + 1))
        
        # Draw main text
        text_surf = font.render(text, True, color)
        screen.blit(text_surf, pos)
        
        # Return the size of the text for layout calculations
        return text_surf.get_width(), text_surf.get_height()
    
    def draw_section_separator(self, screen, y_pos):
        """Draw a horizontal separator line
        
        Args:
            screen: Screen object
            y_pos: Y position
        """
        margin = 20
        pygame.draw.line(
            screen,
            self.border_color,
            (self.rect.x + margin, y_pos),
            (self.rect.x + self.rect.width - margin, y_pos),
            1
        )
    
    def draw_dice(self, screen, value, pos):
        """Draw dice
        
        Args:
            screen: Screen object
            value: Dice value
            pos: Position
        """
        # Draw dice background with rounded corners
        dice_rect = pygame.Rect(pos[0], pos[1], 80, 80)
        pygame.draw.rect(screen, (230, 230, 230), dice_rect, border_radius=10)
        pygame.draw.rect(screen, (150, 150, 150), dice_rect, width=2, border_radius=10)
        
        # Draw dots based on value
        if value:
            dots = {
                1: [(40, 40)],
                2: [(20, 20), (60, 60)],
                3: [(20, 20), (40, 40), (60, 60)],
                4: [(20, 20), (60, 20), (20, 60), (60, 60)],
                5: [(20, 20), (60, 20), (40, 40), (20, 60), (60, 60)],
                6: [(20, 20), (60, 20), (20, 40), (60, 40), (20, 60), (60, 60)]
            }
            
            dot_color = (50, 50, 50)
            for dot_pos in dots.get(value, []):
                pygame.draw.circle(
                    screen, 
                    dot_color, 
                    (pos[0] + dot_pos[0], pos[1] + dot_pos[1]), 
                    8
                )
                # Add highlight to dots for 3D effect
                pygame.draw.circle(
                    screen, 
                    (100, 100, 100), 
                    (pos[0] + dot_pos[0] - 2, pos[1] + dot_pos[1] - 2), 
                    3
                )


class CardPreview:
    def __init__(self, rect, color=(60, 60, 80), border_color=(100, 100, 130)):
        """Initialize card preview
        
        Args:
            rect: Preview area rectangle
            color: Background color
            border_color: Border color
        """
        self.rect = rect
        self.color = color
        self.border_color = border_color
        self.border_radius = 10  # Rounded corners
        self.tile_colors = {
            'white': (230, 230, 230),  # White tiles
            'black': (60, 60, 60),      # Black tiles
            'white_hover': (200, 255, 200),  # Highlighted white tiles
            'black_hover': (100, 100, 100)   # Highlighted black tiles
        }
    
    def draw(self, screen, hex_code, rotation, tile_system=None):
        """Draw card preview
        
        Args:
            screen: Screen object
            hex_code: Path card code
            rotation: Rotation angle
            tile_system: Path tile system (optional)
        """
        # Draw background
        pygame.draw.rect(
            screen, 
            self.color, 
            self.rect,
            border_radius=self.border_radius
        )
        
        # Draw border
        pygame.draw.rect(
            screen, 
            self.border_color, 
            self.rect, 
            width=2,
            border_radius=self.border_radius
        )
        
        if hex_code is None:
            # Draw placeholder text if no card
            font = pygame.font.Font(None, 24)
            text = font.render("No Card", True, (200, 200, 200))
            text_rect = text.get_rect(center=(self.rect.x + self.rect.width // 2, 
                                             self.rect.y + self.rect.height // 2))
            screen.blit(text, text_rect)
            return
        
        try:
            # Get rotated card grid
            if tile_system:
                rotated_card = tile_system.rotate_card(hex_code, rotation)
                if hasattr(tile_system, '_hex_to_grid'):
                    grid = tile_system._hex_to_grid(rotated_card)
                else:
                    # Fallback if _hex_to_grid not available
                    grid = self._hex_to_grid(rotated_card)
            else:
                # Simple fallback if tile_system not provided
                rotated_card = hex_code
                grid = self._hex_to_grid(rotated_card)
            
            # Calculate cell size
            cell_size = min(self.rect.width // 4 - 8, self.rect.height // 4 - 8)
            
            # Draw rotation indicator
            self._draw_rotation_indicator(screen, rotation)
            
            # Draw cells
            for x in range(4):
                for y in range(4):
                    # Determine cell color
                    color = self.tile_colors['white'] if grid[y][x] else self.tile_colors['black']
                    
                    # Calculate cell position with margin
                    cell_x = self.rect.x + 15 + x * (cell_size + 4)
                    cell_y = self.rect.y + 15 + y * (cell_size + 4)
                    
                    # Draw cell with rounded corners
                    cell_rect = pygame.Rect(cell_x, cell_y, cell_size, cell_size)
                    pygame.draw.rect(screen, color, cell_rect, border_radius=3)
                    
                    # Draw cell border
                    border_color = (150, 150, 150) if grid[y][x] else (40, 40, 40)
                    pygame.draw.rect(screen, border_color, cell_rect, width=1, border_radius=3)
                    
                    # Add highlight for 3D effect if white
                    if grid[y][x]:
                        highlight_rect = pygame.Rect(cell_x, cell_y, cell_size // 2, 3)
                        pygame.draw.rect(screen, (255, 255, 255, 128), highlight_rect, border_radius=1)
        
        except Exception as e:
            # If there's an error, display a message
            font = pygame.font.Font(None, 20)
            text = font.render(f"Preview Error: {str(e)[:20]}", True, (255, 100, 100))
            text_rect = text.get_rect(center=(self.rect.x + self.rect.width // 2, 
                                             self.rect.y + self.rect.height // 2))
            screen.blit(text, text_rect)
            print(f"Error in card preview: {e}")
    
    def _draw_rotation_indicator(self, screen, rotation):
        """Draw an indicator for the current rotation
        
        Args:
            screen: Screen object
            rotation: Current rotation (0-3)
        """
        # Draw rotation text
        font = pygame.font.Font(None, 24)
        rot_text = font.render(f"Rotation: {rotation*90}°", True, (200, 200, 200))
        screen.blit(rot_text, (self.rect.x + 10, self.rect.y + self.rect.height - 30))
        
        # Draw a small arrow
        center_x = self.rect.x + self.rect.width - 30
        center_y = self.rect.y + self.rect.height - 20
        arrow_length = 12
        
        # Calculate arrow endpoint based on rotation
        if rotation == 0:  # Up
            end_x, end_y = center_x, center_y - arrow_length
        elif rotation == 1:  # Right
            end_x, end_y = center_x + arrow_length, center_y
        elif rotation == 2:  # Down
            end_x, end_y = center_x, center_y + arrow_length
        else:  # Left
            end_x, end_y = center_x - arrow_length, center_y
        
        # Draw arrow line
        pygame.draw.line(screen, (200, 200, 200), (center_x, center_y), (end_x, end_y), 2)
        
        # Draw arrow head
        arrow_head_length = 6
        if rotation == 0:  # Up
            points = [(end_x, end_y), (end_x - 4, end_y + arrow_head_length), 
                     (end_x + 4, end_y + arrow_head_length)]
        elif rotation == 1:  # Right
            points = [(end_x, end_y), (end_x - arrow_head_length, end_y - 4), 
                     (end_x - arrow_head_length, end_y + 4)]
        elif rotation == 2:  # Down
            points = [(end_x, end_y), (end_x - 4, end_y - arrow_head_length), 
                     (end_x + 4, end_y - arrow_head_length)]
        else:  # Left
            points = [(end_x, end_y), (end_x + arrow_head_length, end_y - 4), 
                     (end_x + arrow_head_length, end_y + 4)]
        
        pygame.draw.polygon(screen, (200, 200, 200), points)
    
    def _hex_to_grid(self, card):
        """Convert a hexadecimal card value to a 2D grid
        
        Args:
            card: Card value in hexadecimal format
        
        Returns:
            2D grid of booleans (True for white, False for black)
        """
        grid = [[False for _ in range(4)] for _ in range(4)]
        
        for y in range(4):
            for x in range(4):
                bit_pos = y * 4 + x
                grid[y][x] = (card & (1 << bit_pos)) != 0
        
        return grid


class GameBoard:
    def __init__(self, offset):
        """Initialize game board
        
        Args:
            offset: Board offset (x, y)
        """
        self.offset = offset
        self.rect = pygame.Rect(
            offset[0], 
            offset[1],
            BOARD_SIZE * TILE_SIZE,  # Use BOARD_SIZE instead of MAP_SIZE
            BOARD_SIZE * TILE_SIZE   # Use BOARD_SIZE instead of MAP_SIZE
        )
        
        # Tile colors
        self.colors = {
            'white': (250, 250, 250),         # White (walkable) tiles
            'black': (50, 50, 50),            # Black (wall) tiles
            'unplaced': (100, 100, 150),      # Unplaced but placeable region
            'not_placeable': (80, 30, 30),    # Not placeable region
            'background': (30, 30, 45),       # Board background
            'grid': (70, 70, 90),             # Grid lines
            'region': (200, 200, 220),        # Region borders
            'highlight': {
                'valid': (0, 255, 0, 180),    # Valid move highlight
                'region': (0, 0, 255, 180),   # Valid region highlight
                'special': (255, 0, 0, 180)   # Special tile highlight
            },
            'special': {
                'stairs': (0, 200, 200),      # Stairs color
                'elevator': (200, 0, 200)     # Elevator color
            }
        }
    
    def draw(self, screen, tile_system, current_floor, floor_config):
        """Draw game board
        
        Args:
            screen: Screen object
            tile_system: Path tile system
            current_floor: Current floor
            floor_config: Floor configuration
        """
        # Draw background
        board_width = BOARD_SIZE * TILE_SIZE
        board_height = BOARD_SIZE * TILE_SIZE
        pygame.draw.rect(screen, self.colors['background'], (self.offset[0], self.offset[1], board_width, board_height))
        
        # Draw grid lines (lighter)
        for i in range(BOARD_SIZE + 1):
            # Vertical lines
            pygame.draw.line(
                screen, 
                self.colors['grid'], 
                (self.offset[0] + i * TILE_SIZE, self.offset[1]), 
                (self.offset[0] + i * TILE_SIZE, self.offset[1] + board_height), 
                1
            )
            # Horizontal lines
            pygame.draw.line(
                screen, 
                self.colors['grid'], 
                (self.offset[0], self.offset[1] + i * TILE_SIZE), 
                (self.offset[0] + board_width, self.offset[1] + i * TILE_SIZE), 
                1
            )
        
        # Draw tiles
        for y in range(BOARD_SIZE):
            for x in range(BOARD_SIZE):
                # Calculate pixel position
                pixel_x = self.offset[0] + x * TILE_SIZE
                pixel_y = self.offset[1] + y * TILE_SIZE
                
                # Draw tile
                region_x, region_y = x // REGION_SIZE, y // REGION_SIZE
                
                # Check if index is valid
                if (current_floor < len(floor_config) and 
                    region_y < len(floor_config[current_floor]) and 
                    region_x < len(floor_config[current_floor][region_y])):
                    # Safely get config value
                    is_placeable = floor_config[current_floor][region_y][region_x]
                else:
                    # Default to placeable
                    is_placeable = True
                
                # Get tile status
                is_white = tile_system.get_tile_status(x, y, current_floor)
                
                # Determine tile color
                if is_white:
                    # White tile (accessible)
                    tile_color = self.colors['white']
                else:
                    # Black tile or unplaced region
                    region_placed = (region_x, region_y) in tile_system.placed_regions[current_floor]
                    if region_placed:
                        # Black tile (wall)
                        tile_color = self.colors['black']
                    elif is_placeable:
                        # Unplaced but placeable
                        tile_color = self.colors['unplaced']
                    else:
                        # Not placeable
                        tile_color = self.colors['not_placeable']
                
                # Draw tile with a slight margin for visual separation
                margin = 1
                tile_rect = pygame.Rect(
                    pixel_x + margin, 
                    pixel_y + margin, 
                    TILE_SIZE - margin * 2, 
                    TILE_SIZE - margin * 2
                )
                pygame.draw.rect(screen, tile_color, tile_rect)
        
        # Draw region boundaries
        for i in range(MAP_SIZE + 1):
            line_width = 2
            # Vertical lines
            pygame.draw.line(screen, self.colors['region'], 
                           (self.offset[0] + i * REGION_SIZE * TILE_SIZE, self.offset[1]), 
                           (self.offset[0] + i * REGION_SIZE * TILE_SIZE, self.offset[1] + board_height), 
                           line_width)
            # Horizontal lines
            pygame.draw.line(screen, self.colors['region'], 
                           (self.offset[0], self.offset[1] + i * REGION_SIZE * TILE_SIZE), 
                           (self.offset[0] + board_width, self.offset[1] + i * REGION_SIZE * TILE_SIZE), 
                           line_width)
    
    def draw_special_tiles(self, screen, tile_system, current_floor, exit_pos):
        """Draw special tiles
        
        Args:
            screen: Screen object
            tile_system: Path tile system
            current_floor: Current floor
            exit_pos: Exit position (floor, (x, y))
        """
        # Draw special tiles
        for y in range(BOARD_SIZE):
            for x in range(BOARD_SIZE):
                # Calculate pixel position
                pixel_x = self.offset[0] + x * TILE_SIZE
                pixel_y = self.offset[1] + y * TILE_SIZE
                
                # Get special tile type
                special_type = tile_system.get_special_tile(x, y, current_floor)
                
                # Draw special tile
                if special_type == 'stairs':
                    # Draw stairs - triangle shape
                    color = self.colors['special']['stairs']
                    points = [
                        (pixel_x + 5, pixel_y + TILE_SIZE - 5),
                        (pixel_x + TILE_SIZE - 5, pixel_y + 5),
                        (pixel_x + TILE_SIZE - 5, pixel_y + TILE_SIZE - 5)
                    ]
                    pygame.draw.polygon(screen, color, points)
                    
                    # Draw stairs icon
                    for i in range(3):
                        stair_y = pixel_y + 8 + i * 5
                        pygame.draw.line(
                            screen, 
                            (255, 255, 255), 
                            (pixel_x + 7, stair_y), 
                            (pixel_x + TILE_SIZE - 7, stair_y), 
                            2
                        )
                
                elif special_type == 'elevator':
                    # Draw elevator - rectangle shape
                    color = self.colors['special']['elevator']
                    elevator_rect = pygame.Rect(
                        pixel_x + 5, 
                        pixel_y + 5, 
                        TILE_SIZE - 10, 
                        TILE_SIZE - 10
                    )
                    pygame.draw.rect(screen, color, elevator_rect, border_radius=3)
                    
                    # Draw elevator icon (up/down arrows)
                    center_x = pixel_x + TILE_SIZE // 2
                    # Up arrow
                    arrow_top = pixel_y + 8
                    points_up = [
                        (center_x, arrow_top),
                        (center_x - 5, arrow_top + 5),
                        (center_x + 5, arrow_top + 5)
                    ]
                    pygame.draw.polygon(screen, (255, 255, 255), points_up)
                    
                    # Down arrow
                    arrow_bottom = pixel_y + TILE_SIZE - 8
                    points_down = [
                        (center_x, arrow_bottom),
                        (center_x - 5, arrow_bottom - 5),
                        (center_x + 5, arrow_bottom - 5)
                    ]
                    pygame.draw.polygon(screen, (255, 255, 255), points_down)
                
                # Draw exit if on current floor
                if exit_pos[0] == current_floor and exit_pos[1] == (x, y):
                    # Draw exit - pulsing circle
                    pulse = (pygame.time.get_ticks() % 1000) / 1000.0  # 0.0 to 1.0
                    pulse_size = 3 + pulse * 3  # Pulsing size between 3 and 6
                    
                    # Draw exit marker
                    pygame.draw.circle(
                        screen, 
                        (200, 0, 0), 
                        (pixel_x + TILE_SIZE // 2, pixel_y + TILE_SIZE // 2), 
                        TILE_SIZE // 2 - pulse_size
                    )
                    
                    # Draw exit text
                    font = pygame.font.Font(None, 18)
                    text = font.render("EXIT", True, (255, 255, 255))
                    text_rect = text.get_rect(center=(pixel_x + TILE_SIZE // 2, pixel_y + TILE_SIZE // 2))
                    screen.blit(text, text_rect)
    
    def highlight_tiles(self, screen, tiles, color):
        """Highlight tiles
        
        Args:
            screen: Screen to draw on
            tiles: List of tile positions (x, y)
            color: Highlight color
        """
        # Set up highlight colors based on the provided color
        if color == (0, 255, 0):  # Green (valid move)
            highlight_color = self.colors['highlight']['valid']
        elif color == (0, 0, 255):  # Blue (region)
            highlight_color = self.colors['highlight']['region']
        elif color == (255, 0, 0):  # Red (special)
            highlight_color = self.colors['highlight']['special']
        else:
            highlight_color = color
        
        # Create a surface with alpha for the highlight
        if len(highlight_color) == 3:
            highlight_color = (*highlight_color, 180)  # Add alpha if not provided
            
        for x, y in tiles:
            # Calculate pixel position
            pixel_x = self.offset[0] + x * TILE_SIZE
            pixel_y = self.offset[1] + y * TILE_SIZE
            
            # Draw highlight square with rounded corners
            highlight_rect = pygame.Rect(
                pixel_x + 2, 
                pixel_y + 2, 
                TILE_SIZE - 4, 
                TILE_SIZE - 4
            )
            
            # Draw a pulsing highlight effect
            pulse = (pygame.time.get_ticks() % 1000) / 1000.0  # 0.0 to 1.0
            pulse_alpha = int(128 + 64 * pulse)  # Alpha varies between 128 and 192
            
            # Create surface with per-pixel alpha
            s = pygame.Surface((TILE_SIZE - 4, TILE_SIZE - 4), pygame.SRCALPHA)
            s.fill((*highlight_color[:3], pulse_alpha))
            screen.blit(s, highlight_rect)
            
            # Draw border
            pygame.draw.rect(
                screen, 
                highlight_color[:3],  # Use RGB without alpha
                highlight_rect, 
                width=2,
                border_radius=3
            )
    
    def highlight_regions(self, screen, regions, color):
        """Highlight regions
        
        Args:
            screen: Screen to draw on
            regions: List of region positions (rx, ry)
            color: Highlight color
        """
        # Set color for region highlighting
        if len(color) == 3:
            highlight_color = (*color, 120)  # Add alpha if not provided
        else:
            highlight_color = color
            
        for rx, ry in regions:
            # Calculate pixel position
            pixel_x = self.offset[0] + rx * REGION_SIZE * TILE_SIZE
            pixel_y = self.offset[1] + ry * REGION_SIZE * TILE_SIZE
            
            # Create highlight surface with alpha
            s = pygame.Surface((REGION_SIZE * TILE_SIZE, REGION_SIZE * TILE_SIZE), pygame.SRCALPHA)
            s.fill(highlight_color)
            screen.blit(s, (pixel_x, pixel_y))
            
            # Draw border with pulsing effect
            pulse = (pygame.time.get_ticks() % 1000) / 1000.0  # 0.0 to 1.0
            border_width = 2 + int(pulse * 2)  # Width varies between 2 and 4
            
            pygame.draw.rect(
                screen, 
                color,  # Use RGB without alpha
                (pixel_x, pixel_y, REGION_SIZE * TILE_SIZE, REGION_SIZE * TILE_SIZE), 
                width=border_width,
                border_radius=4
            )
    
    def get_tile_coordinates(self, screen_pos):
        """Convert screen position to tile coordinates
        
        Args:
            screen_pos: Screen position (x, y)
            
        Returns:
            (x, y) tile coordinates or None if outside board
        """
        # Check if position is within board
        if not self.rect.collidepoint(screen_pos):
            return None
        
        # Calculate tile coordinates
        tile_x = (screen_pos[0] - self.offset[0]) // TILE_SIZE
        tile_y = (screen_pos[1] - self.offset[1]) // TILE_SIZE
        
        return (tile_x, tile_y)
    
    def get_region_coordinates(self, screen_pos):
        """Convert screen position to region coordinates
        
        Args:
            screen_pos: Screen position (x, y)
            
        Returns:
            (x, y) region coordinates or None if outside board
        """
        # Get tile coordinates
        tile_coords = self.get_tile_coordinates(screen_pos)
        if not tile_coords:
            return None
        
        # Calculate region coordinates
        region_x = tile_coords[0] // REGION_SIZE
        region_y = tile_coords[1] // REGION_SIZE
        
        return (region_x, region_y)


class PlayerToken:
    def __init__(self, player_id, player_name, token_offset):
        """Initialize player token
        
        Args:
            player_id: Player ID
            player_name: Player name
            token_offset: Token offset from center (x, y)
        """
        self.player_id = player_id
        self.player_name = player_name
        self.token_offset = token_offset
        
        # Player colors
        self.colors = {
            0: (220, 50, 50),     # Red
            1: (50, 50, 220),     # Blue
            2: (50, 180, 50),     # Green
            3: (220, 180, 30),    # Yellow
            'shadow': (20, 20, 30)
        }
        
        # Animation parameters
        self.animation = {
            'pulse': 0,           # Pulse effect (0-1)
            'hover': 0,           # Hover effect (pixels)
            'rotation': 0,        # Rotation angle
            'selected': False     # Is token selected
        }
        
        # Token design
        self.size = TILE_SIZE // 2
        self.inner_size = int(self.size * 0.65)
        self.border_width = 2
        
        # Font for player info
        self.font = pygame.font.Font(None, 16)

    def update_animation(self):
        """Update animation effects"""
        # Update pulse effect (0-1 range)
        time_ms = pygame.time.get_ticks()
        self.animation['pulse'] = (math.sin(time_ms / 200) + 1) / 2
        
        # Update hover effect (pixels up/down)
        self.animation['hover'] = math.sin(time_ms / 350) * 2
        
        # Update rotation for selected tokens
        if self.animation['selected']:
            self.animation['rotation'] = (time_ms / 20) % 360
        else:
            # Gradually reset rotation when not selected
            target = 0
            current = self.animation['rotation'] % 360
            if current > 180:
                current -= 360
            
            # Move toward 0 rotation
            if abs(current) < 5:
                self.animation['rotation'] = 0
            else:
                self.animation['rotation'] = current * 0.9
    
    def set_selected(self, selected):
        """Set whether token is selected
        
        Args:
            selected: Is token selected
        """
        self.animation['selected'] = selected
    
    def draw(self, screen, position):
        """Draw player token
        
        Args:
            screen: Screen to draw on
            position: Position (x, y) 
        """
        # Update animation values
        self.update_animation()
        
        # Calculate center position with animation
        center_x = position[0] + self.token_offset[0]
        center_y = position[1] + self.token_offset[1] - self.animation['hover']
        
        # Draw shadow
        shadow_offset = 2
        pygame.draw.circle(
            screen, 
            self.colors['shadow'], 
            (center_x + shadow_offset, center_y + shadow_offset), 
            self.size
        )
        
        # Get player color with pulse effect for selected tokens
        color = self.colors[self.player_id]
        if self.animation['selected']:
            # Make color pulse brighter when selected
            pulse_factor = 0.2 * self.animation['pulse']
            pulsed_color = (
                min(255, int(color[0] * (1 + pulse_factor))),
                min(255, int(color[1] * (1 + pulse_factor))),
                min(255, int(color[2] * (1 + pulse_factor)))
            )
            color = pulsed_color
        
        # Draw outer circle
        pygame.draw.circle(
            screen, 
            color, 
            (center_x, center_y), 
            self.size
        )
        
        # Draw inner circle (white)
        pygame.draw.circle(
            screen, 
            (255, 255, 255), 
            (center_x, center_y), 
            self.inner_size
        )
        
        # Draw player ID in center
        text = self.font.render(str(self.player_id + 1), True, (0, 0, 0))
        text_rect = text.get_rect(center=(center_x, center_y))
        screen.blit(text, text_rect)
        
        # Draw player name above token
        name_text = self.font.render(self.player_name, True, color)
        name_rect = name_text.get_rect(center=(center_x, center_y - self.size - 5))
        
        # Add background to make text more readable
        bg_rect = name_rect.inflate(10, 6)
        pygame.draw.rect(screen, (40, 40, 50, 200), bg_rect, border_radius=4)
        
        screen.blit(name_text, name_rect) 