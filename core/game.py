import pygame
import random
import sys
from pygame.locals import *

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BOARD_SIZE, REGION_SIZE, FLOOR_NUM, 
    PLAYER_COLORS, FLOOR_CONFIG, PHASE_PREVIEW, PHASE_SELECT_REGION, 
    PHASE_ROTATE_PATH, PHASE_SELECT_END, PHASE_USE_TRANSPORT,
    PHASE_ROLL_DICE, PHASE_PLACE_CARD, PHASE_MOVE,
    MOVES_NUM, LOOP_NUM, EXIT, LOOP_NODES, WINNER, TILE_SIZE, MAP_SIZE
)
from core.player import Player
from core.path_tile_system import PathTileSystem
from core.ui import Button, InfoPanel, CardPreview, GameBoard, PlayerToken

class Game:
    def __init__(self, num_players, player_names=None):
        """Initialize the game
        
        Args:
            num_players: Number of players
            player_names: List of player names, if None use default names
        """
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("NMB Game - Board Game")  # English title
        self.font = pygame.font.Font(None, 36)
        self.clock = pygame.time.Clock()
        
        # Game state
        self.num_players = num_players
        self.tile_system = PathTileSystem()
        self.current_player_index = 0
        self.dice_value = 0
        self.current_floor = 1  # Start at floor 1 where the initial tile is placed
        
        # Initialize players
        self.players = []
        for i in range(num_players):
            name = player_names[i] if player_names and i < len(player_names) else None
            self.players.append(Player(i, PLAYER_COLORS[i], name))
        
        # Game phase
        self.selecting_start = True  # Whether in the initial position selection phase
        self.move_phase = PHASE_PREVIEW
        
        # Game data
        self.valid_tiles = set()  # Valid move tiles
        self.inner_tiles = set()  # Reachable tiles
        self.current_card = None  # Current path card
        self.card_rotation = 0    # Path card rotation
        self.target_region = None # Target region
        
        # Dice animation
        self.dice_anim = [random.randint(1, 6) for _ in range(10)]
        
        # UI components
        self.board_offset = (50, 50)
        self.game_board = GameBoard(self.board_offset)
        self.info_panel = InfoPanel(pygame.Rect(900, 50, 400, 600))
        self.card_preview = CardPreview(pygame.Rect(920, 320, 200, 200))
        
        # Reposition buttons to avoid overlap
        self.rotate_btn = Button(pygame.Rect(920, 580, 100, 40), "Rotate", (0, 150, 0))
        self.place_btn = Button(pygame.Rect(1040, 580, 100, 40), "Place", (150, 0, 0))
        self.up_btn = Button(pygame.Rect(920, 580, 100, 40), "Up", (0, 150, 0))
        self.down_btn = Button(pygame.Rect(1040, 580, 100, 40), "Down", (150, 0, 0))
        
        # Floor navigation buttons
        self.floor_up_btn = Button(pygame.Rect(1170, 70, 40, 30), "^", (0, 100, 0))
        self.floor_down_btn = Button(pygame.Rect(1170, 110, 40, 30), "v", (100, 0, 0))
        
        # Elevator floor buttons - reposition to avoid overlap
        self.floor_btns = []
        for i in range(FLOOR_NUM):
            self.floor_btns.append(Button(
                pygame.Rect(920 + (i % 3) * 70, 630 + (i // 3) * 50, 60, 40),
                f"F{i + 1}", (200, 200, 200)
            ))
            
        # Confusion value buttons - reposition to avoid overlap
        self.increase_daze_btn = Button(pygame.Rect(920, 530, 100, 40), "+Daze", (200, 0, 0))
        self.decrease_daze_btn = Button(pygame.Rect(1040, 530, 100, 40), "-Daze", (0, 200, 0))
        
        # Initialize player tokens with different offsets
        self.player_tokens = []
        token_offsets = [
            (-TILE_SIZE // 4, -TILE_SIZE // 4),   # Top-left
            (TILE_SIZE // 4, -TILE_SIZE // 4),    # Top-right
            (-TILE_SIZE // 4, TILE_SIZE // 4),    # Bottom-left
            (TILE_SIZE // 4, TILE_SIZE // 4)      # Bottom-right
        ]
        
        for i in range(num_players):
            self.player_tokens.append(
                PlayerToken(i, self.players[i].name, token_offsets[i])
            )
            
            # Set current player token as selected
            if i == self.current_player_index:
                self.player_tokens[i].set_selected(True)
        
        # Initialize game state
        self.state = 'setup'  # Initial state
        self.active_region = None  # Active region being placed
        self.player_moved = False  # Whether player has moved in this turn
        self.special_used = False  # Whether player has used special action
        self.move_history = []  # For undo functionality
        
        # Debug flags
        self.debug_mode = False
        
        print(f"Game initialized with {num_players} players, starting at floor {self.current_floor}")
        print("Please select starting positions for all players")
    
    @property
    def current_player(self):
        """Get current player"""
        return self.players[self.current_player_index]
    
    def roll_dice(self):
        """Roll dice and play animation
        
        Returns:
            Dice value
        """
        # Play dice animation
        for val in self.dice_anim:
            self.dice_value = val
            self.draw_all()
            pygame.display.update()
            pygame.time.wait(80)
        
        # Generate final value
        self.dice_value = random.randint(1, 6)
        return self.dice_value
    
    def get_valid_moves(self, start_pos, steps, use=1):
        """Get valid move tiles
        
        Args:
            start_pos: Starting position (x, y)
            steps: Number of steps
            use: Use mode 0: Only check reachability 1: Check legal end
            
        Returns:
            Valid tiles set
        """
        # Handle None start_pos
        if start_pos is None:
            return set()
        
        valid = set()
        queue = [(start_pos[0], start_pos[1], 0)]
        visited = set()
        
        floor = self.current_player.floor
        daze_level = self.current_player.daze  # Get current player's confusion value
        
        while queue:
            x, y, d = queue.pop(0)
            if (x, y) in visited:
                continue
            visited.add((x, y))
            
            if use == 0:  # Check reachability, allow passing through unplaced regions
                if d == steps and (self.tile_system.get_tile_status(x, y, floor) or \
                        (x // REGION_SIZE, y // REGION_SIZE) in self.tile_system.get_unplaced_regions(floor)):
                    valid.add((x, y))
                
                if d < steps:
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = (x + dx) % BOARD_SIZE, (y + dy) % BOARD_SIZE
                        if self.tile_system.get_tile_status(nx, ny, floor) or \
                                (nx // REGION_SIZE, ny // REGION_SIZE) in self.tile_system.get_unplaced_regions(floor):
                            queue.append((nx, ny, d + 1))
            
            else:  # Check legal end, can only reach valid tiles based on confusion level
                is_valid_destination = False
                
                # Basic rule: White tiles are always passable
                if self.tile_system.get_tile_status(x, y, floor):
                    is_valid_destination = True
                # Confusion rule: When confusion value reaches certain level, can pass through special tiles
                elif daze_level >= 6:
                    # When confusion level reaches 6, any tile can be passed
                    is_valid_destination = True
                elif daze_level >= 3:
                    # When confusion level reaches 3, can pass through certain special marked tiles
                    # Here you can add other special case checks as needed
                    # For example: Check if the position is a special "confusion tile"
                    is_valid_destination = False  # Need to modify based on specific implementation
                
                if d == steps and is_valid_destination:
                    valid.add((x, y))
                
                if d < steps:
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = (x + dx) % BOARD_SIZE, (y + dy) % BOARD_SIZE
                        # Similarly decide whether to cross the tile based on confusion value
                        can_pass = False
                        
                        # Basic rule: White tiles are always passable
                        if self.tile_system.get_tile_status(nx, ny, floor):
                            can_pass = True
                        # Confusion rule: When confusion value reaches certain level, can cross special tiles
                        elif daze_level >= 6:
                            # When confusion level reaches 6, any tile can be crossed
                            can_pass = True
                        elif daze_level >= 3:
                            # When confusion level reaches 3, can cross certain special marked tiles
                            can_pass = False  # Need to modify based on specific implementation
                        
                        if can_pass:
                            queue.append((nx, ny, d + 1))
        
        return valid
    
    def get_reachable_regions(self, current_pos, steps):
        """Get reachable unplaced regions
        
        Args:
            current_pos: Current position (x, y)
            steps: Number of steps
            
        Returns:
            Reachable regions list [(rx, ry), ...]
        """
        # Handle None current_pos
        if current_pos is None:
            return []
        
        current_region = (current_pos[0] // REGION_SIZE, current_pos[1] // REGION_SIZE)
        unplaced = self.tile_system.get_unplaced_regions(self.current_player.floor)
        reachable = []
        
        # Check each unplaced region
        for rx, ry in unplaced:
            # Check if it can be placed
            if not FLOOR_CONFIG[self.current_player.floor][rx][ry]:
                continue
            
            # Check if the region is reachable within the current tile steps
            region_valid = False
            for x in range(REGION_SIZE):
                for y in range(REGION_SIZE):
                    abs_x = rx * REGION_SIZE + x
                    abs_y = ry * REGION_SIZE + y
                    
                    # Calculate Manhattan distance
                    dx = abs(abs_x - current_pos[0])
                    dy = abs(abs_y - current_pos[1])
                    
                    # Manhattan distance between region and current region
                    region_dx = abs(rx - current_region[0])
                    region_dy = abs(ry - current_region[1])
                    
                    # Satisfy conditions: within reachable steps and adjacent regions
                    if (dx + dy) <= steps and (region_dx + region_dy) <= 1 \
                            and (abs_x, abs_y) in self.get_valid_moves(current_pos, steps, use=0):
                        reachable.append((rx, ry))
                        region_valid = True
                        break
                if region_valid:
                    break
        
        return reachable
    
    def handle_region_placement(self):
        """Handle region placement logic
        
        Returns:
            Whether a path card is successfully drawn
        """
        self.current_card = self.tile_system.draw_card()
        if self.current_card:
            self.card_rotation = 0
            return True
        return False
    
    def create_special_tiles(self, region_x, region_y):
        """Create special tiles in the newly placed region (stairs and elevator)
        
        Args:
            region_x: Region x coordinate
            region_y: Region y coordinate
        """
        floor = self.current_player.floor
        
        # Try to generate stairs
        if random.random() < 0.3:
            legal_pos = self.tile_system.find_legal_position(region_x, region_y, floor)
            if legal_pos:
                self.tile_system.add_special_tile(legal_pos[1], floor, 'stairs')
        
        # Try to generate elevator
        if random.random() < 0.2:
            legal_pos = self.tile_system.find_legal_position(region_x, region_y, floor)
            if legal_pos:
                self.tile_system.add_special_tile(legal_pos[1], floor, 'elevator')
    
    def next_player(self):
        """Switch to the next player"""
        global MOVES_NUM, LOOP_NUM, EXIT
        
        self.current_player_index = (self.current_player_index + 1) % self.num_players
        self.current_floor = self.current_player.floor
        self.move_phase = PHASE_ROLL_DICE  # 确保设置为掷骰子阶段
        self.valid_tiles = set()
        self.inner_tiles = set()
        self.current_card = None  # 确保清除卡牌状态
        self.card_rotation = 0
        self.target_region = None
        
        # Update game statistics
        MOVES_NUM += 1
        LOOP_NUM = MOVES_NUM // self.num_players
        
        # Generate exit after certain rounds
        if EXIT[0] == -1 and MOVES_NUM >= LOOP_NODES[2] * self.num_players:
            EXIT = self.tile_system.find_legal_position(all_floors=True)
    
    def check_win_condition(self):
        """Check if any player wins"""
        global WINNER
        
        player_pos = self.current_player.pos
        player_floor = self.current_player.floor
        
        # Check if player reaches exit
        if EXIT[0] != -1 and player_floor == EXIT[0] and player_pos == EXIT[1]:
            WINNER = self.current_player_index
            return True
        
        return False
    
    def draw_all(self):
        """Draw all game elements"""
        # Clear screen
        self.screen.fill((20, 30, 40))
        
        # Draw game board and special tiles
        self.game_board.draw(self.screen, self.tile_system, self.current_floor, FLOOR_CONFIG)
        
        # 如果实现了特殊绘制方法，使用它
        if hasattr(self.game_board, 'draw_special_tiles'):
            self.game_board.draw_special_tiles(self.screen, self.tile_system, self.current_floor, EXIT)
        
        # Draw info panel
        self.draw_info_panel()
        
        # Draw buttons
        self.draw_buttons()
        
        # Draw highlighted tiles
        self.draw_highlights()
        
        # Draw players
        self.draw_players()
        
        # Update display
        pygame.display.flip()
    
    def draw_players(self):
        """Draw players on the game board
        
        Args:
            screen: Screen object
        """
        # Draw player tokens at their positions on the board
        for i, player in enumerate(self.players):
            # Skip players on different floors
            if player.floor != self.current_floor:
                continue
                
            # Skip players with no position yet
            if player.pos is None:
                continue

            # Get pixel position of the player
            pos_x = self.board_offset[0] + player.pos[0] * TILE_SIZE + TILE_SIZE // 2
            pos_y = self.board_offset[1] + player.pos[1] * TILE_SIZE + TILE_SIZE // 2

            # Draw player using PlayerToken
            self.player_tokens[i].draw(self.screen, (pos_x, pos_y))
    
    def draw_info_panel(self):
        """Draw game information panel"""
        # Background panel
        pygame.draw.rect(self.screen, (50, 50, 70), self.info_panel.rect)
        pygame.draw.rect(self.screen, (100, 100, 120), self.info_panel.rect, 2)
        
        # Game status info
        title_text = self.font.render(f"Floor {self.current_floor + 1}", True, (255, 255, 255))
        self.screen.blit(title_text, (self.info_panel.rect.x + 20, self.info_panel.rect.y + 20))
        
        # Phase information
        phase_names = {
            PHASE_PREVIEW: "Preview",
            PHASE_SELECT_REGION: "Select Region",
            PHASE_ROTATE_PATH: "Rotate Path",
            PHASE_SELECT_END: "Select Destination",
            PHASE_USE_TRANSPORT: "Use Transport"
        }
        
        phase_name = phase_names.get(self.move_phase, "Unknown")
        phase_text = self.font.render(f"Phase: {phase_name}", True, (255, 255, 255))
        self.screen.blit(phase_text, (self.info_panel.rect.x + 20, self.info_panel.rect.y + 60))
        
        # Dice value
        if self.dice_value > 0:
            dice_text = self.font.render(f"Dice: {self.dice_value}", True, (255, 255, 255))
            self.screen.blit(dice_text, (self.info_panel.rect.x + 20, self.info_panel.rect.y + 100))
        
        # Player information
        player_y = self.info_panel.rect.y + 150
        for i, player in enumerate(self.players):
            # Player text
            player_text = player.get_info_text(self.font, i == self.current_player_index)
            self.screen.blit(player_text, (self.info_panel.rect.x + 20, player_y))
            
            # Display Confusion level (previously labeled as "迷乱值")
            daze_text = self.font.render(f"Daze: {player.daze}", True, 
                                       (255, 200, 200) if player.daze > 3 else (200, 255, 200))
            self.screen.blit(daze_text, (self.info_panel.rect.x + 20, player_y + 30))
            
            # Player status indicators
            color_rect = pygame.Rect(self.info_panel.rect.x + 10, player_y + 60, 20, 20)
            pygame.draw.rect(self.screen, player.color, color_rect)
            
            player_y += 90  # 增加垂直间距，避免玩家信息重叠
        
        # Card preview - only show if we have a card AND we're in ROTATE_PATH phase
        if self.current_card is not None and self.move_phase == PHASE_ROTATE_PATH:
            preview_text = self.font.render("Card Preview:", True, (255, 255, 255))
            self.screen.blit(preview_text, (self.card_preview.rect.x, self.card_preview.rect.y - 30))
            
            # Draw the card preview
            try:
                self.card_preview.draw(self.screen, self.current_card, self.card_rotation, self.tile_system)
            except TypeError:
                # Fallback if old method signature
                self.card_preview.draw(self.screen, self.current_card, self.card_rotation)
    
    def draw_buttons(self):
        """Draw game buttons"""
        # Floor navigation
        self.floor_up_btn.draw(self.screen)
        self.floor_down_btn.draw(self.screen)
        
        # Rotation & placement - only show if we have a card AND we're in ROTATE_PATH phase
        if self.move_phase == PHASE_ROTATE_PATH and self.current_card is not None:
            self.rotate_btn.draw(self.screen)
            self.place_btn.draw(self.screen)
        
        # Transportation buttons
        elif self.move_phase == PHASE_USE_TRANSPORT:
            special_type = self.tile_system.get_special_tile(
                self.current_player.pos[0], 
                self.current_player.pos[1],
                self.current_player.floor
            )
            
            # Stairs buttons
            if special_type == 'stairs':
                self.up_btn.draw(self.screen)
                self.down_btn.draw(self.screen)
            
            # Elevator buttons
            elif special_type == 'elevator':
                for btn in self.floor_btns:
                    btn.draw(self.screen)
        
        # Always show confusion control buttons
        self.increase_daze_btn.draw(self.screen)
        self.decrease_daze_btn.draw(self.screen)
    
    def draw_highlights(self):
        """Draw highlighted areas and tiles"""
        # Initial position selection phase
        if self.selecting_start:
            # Highlight center region where initial path tile is placed
            center_region_x = center_region_y = MAP_SIZE // 2
            start_area = []
            
            # Check each position in the center region
            for x in range(center_region_x * REGION_SIZE, (center_region_x + 1) * REGION_SIZE):
                for y in range(center_region_y * REGION_SIZE, (center_region_y + 1) * REGION_SIZE):
                    if self.tile_system.get_tile_status(x, y, self.current_floor):
                        # Check if already occupied by a player
                        occupied = False
                        for player in self.players:
                            if player.pos == (x, y) and player.floor == self.current_floor:
                                occupied = True
                                break
                        if not occupied:
                            start_area.append((x, y))
            
            # Highlight available positions
            if start_area:
                self.game_board.highlight_tiles(self.screen, start_area, (0, 200, 0))
                print(f"Found {len(start_area)} valid starting positions in center region")
            else:
                print("Warning: No valid starting positions found!")
        
        # Region selection phase
        elif self.move_phase == PHASE_SELECT_REGION:
            # Highlight reachable regions
            current_pos = self.current_player.pos
            reachable = self.get_reachable_regions(current_pos, self.dice_value)
            # Check if game_board has highlight_regions method
            if hasattr(self.game_board, 'highlight_regions'):
                self.game_board.highlight_regions(self.screen, reachable, (0, 0, 255))
            else:
                # Fallback to highlighting tiles
                region_tiles = []
                for rx, ry in reachable:
                    for dx in range(REGION_SIZE):
                        for dy in range(REGION_SIZE):
                            region_tiles.append((rx * REGION_SIZE + dx, ry * REGION_SIZE + dy))
                self.game_board.highlight_tiles(self.screen, region_tiles, (0, 0, 255))
        
        # Endpoint selection phase
        elif self.move_phase == PHASE_SELECT_END:
            # Highlight reachable endpoints
            if self.valid_tiles:
                self.game_board.highlight_tiles(self.screen, self.valid_tiles, (0, 255, 0))
            
            # Highlight special tiles
            if hasattr(self.tile_system, 'special_pos'):
                special_tiles = []
                # Get special tiles for current floor
                if 0 <= self.current_player.floor < len(self.tile_system.special_pos):
                    for pos in self.tile_system.special_pos[self.current_player.floor]:
                        if self.inner_tiles and pos in self.inner_tiles:
                            special_tiles.append(pos)
                self.game_board.highlight_tiles(self.screen, special_tiles, (255, 0, 0))
    
    def handle_start_selection(self, event):
        """Handle initial position selection
        
        Args:
            event: Mouse event
            
        Returns:
            Whether the event was handled
        """
        # Get tile coordinates from mouse position
        mouse_x, mouse_y = event.pos
        tile_x = (mouse_x - self.board_offset[0]) // TILE_SIZE
        tile_y = (mouse_y - self.board_offset[1]) // TILE_SIZE
        
        print(f"Clicked at tile coordinates: ({tile_x}, {tile_y}) on floor {self.current_floor}")
        
        # Check if coordinates are valid
        if 0 <= tile_x < BOARD_SIZE and 0 <= tile_y < BOARD_SIZE:
            # Check if tile is a valid white tile
            if self.tile_system.get_tile_status(tile_x, tile_y, self.current_floor):
                print(f"Valid white tile found at ({tile_x}, {tile_y})")
                
                # Check if already occupied
                occupied = False
                for player in self.players:
                    if player.pos == (tile_x, tile_y) and player.floor == self.current_floor:
                        occupied = True
                        print(f"Position already occupied by player {player.name}")
                        break
                        
                if not occupied:
                    # Set player position
                    self.current_player.set_position(tile_x, tile_y)
                    self.current_player.set_floor(self.current_floor)
                    print(f"Player {self.current_player.name} placed at position ({tile_x}, {tile_y}) on floor {self.current_floor}")
                    
                    # Move to next player or start game
                    self.current_player_index += 1
                    if self.current_player_index >= self.num_players:
                        self.current_player_index = 0
                        self.selecting_start = False
                        self.move_phase = PHASE_ROLL_DICE
                        print("Starting main game phase")
                    else:
                        print(f"Player {self.current_player.name} selecting position")
                    
                    return True
            else:
                print(f"Not a valid white tile at ({tile_x}, {tile_y})")
        else:
            print(f"Coordinates ({tile_x}, {tile_y}) are outside the board")
        
        return False
        
    def handle_region_selection(self, pos):
        """Handle region selection
        
        Args:
            pos: Mouse position
            
        Returns:
            Whether the event was handled
        """
        # Get region coordinates from mouse position
        region_x = (pos[0] - self.board_offset[0]) // (REGION_SIZE * TILE_SIZE)
        region_y = (pos[1] - self.board_offset[1]) // (REGION_SIZE * TILE_SIZE)
        
        print(f"Clicked on region: ({region_x}, {region_y}) on floor {self.current_floor}")
        
        # Verify region is in valid range
        if 0 <= region_x < MAP_SIZE and 0 <= region_y < MAP_SIZE:
            # Verify region is reachable
            if (region_x, region_y) in self.valid_tiles:
                # Generate random card for that region
                self.current_card = self.tile_system.draw_card()
                self.card_rotation = 0
                self.target_region = (region_x, region_y)
                self.move_phase = PHASE_ROTATE_PATH
                return True
            else:
                print(f"Region ({region_x}, {region_y}) not in valid regions: {self.valid_tiles}")
        else:
            print(f"Region coordinates ({region_x}, {region_y}) are outside the map")
        
        return False
    
    def handle_endpoint_selection(self, pos):
        """Handle endpoint selection
        
        Args:
            pos: Mouse position
            
        Returns:
            Whether the event was handled
        """
        # Convert mouse position to tile coordinates
        mouse_x, mouse_y = pos
        tile_x = (mouse_x - self.board_offset[0]) // TILE_SIZE
        tile_y = (mouse_y - self.board_offset[1]) // TILE_SIZE
        
        print(f"Endpoint selection: clicked at tile ({tile_x}, {tile_y})")
        
        # Check if tile is in valid tiles
        if (tile_x, tile_y) in self.valid_tiles:
            print(f"Valid endpoint selected: ({tile_x}, {tile_y})")
            
            # Move player
            self.current_player.set_position(tile_x, tile_y)
            
            # Check special tiles
            tile_type = self.tile_system.get_special_tile(tile_x, tile_y, self.current_player.floor)
            if tile_type == 'stairs':
                print(f"Player reached stairs, entering transport phase")
                self.move_phase = PHASE_USE_TRANSPORT
            elif tile_type == 'elevator':
                print(f"Player reached elevator, entering transport phase")
                self.move_phase = PHASE_USE_TRANSPORT
            else:
                # Next player
                self.move_phase = PHASE_ROLL_DICE
                self.check_win_condition()
                self.next_player()
                print(f"Moving to next player: {self.current_player.name}")
            
            # Clear valid tiles
            self.valid_tiles = set()
            self.inner_tiles = set()
            
            return True
        else:
            print(f"Invalid endpoint ({tile_x}, {tile_y}), valid endpoints are: {self.valid_tiles}")
        
        return False
        
    def handle_button_click(self, pos):
        """Handle button clicks
        
        Args:
            pos: Mouse position
            
        Returns:
            Whether the event was handled
        """
        # Path card rotation buttons - only allow rotation if we have a card and are in ROTATE_PATH phase
        if self.move_phase == PHASE_ROTATE_PATH and self.current_card is not None and self.rotate_btn.rect.collidepoint(pos):
            # Rotate card clockwise
            self.card_rotation = (self.card_rotation + 1) % 4
            return True
        
        # Path card placement button - only allow placement if we have a card and are in ROTATE_PATH phase
        if self.move_phase == PHASE_ROTATE_PATH and self.current_card is not None and self.place_btn.rect.collidepoint(pos):
            # Place the card
            success = self.place_region(self.target_region[0], self.target_region[1])
            
            if success:
                # Check if it's a chaotic card (for now, consider cards with less than 8 white tiles as chaotic)
                white_count = bin(self.current_card).count('1')
                if white_count < 8:
                    # Add confusion value
                    self.add_player_daze(1)
                    print(f"Chaotic card placed! Confusion +1 (now: {self.current_player.daze})")
                
                # Get valid moves after placing the card
                self.valid_tiles = self.get_valid_moves(self.current_player.pos, self.dice_value)
                self.inner_tiles = self.valid_tiles
                
                if not self.valid_tiles:
                    # No valid moves available, move to next player
                    self.move_phase = PHASE_ROLL_DICE  # 确保设置正确的阶段
                    self.next_player()
                else:
                    # Move to endpoint selection phase
                    self.move_phase = PHASE_SELECT_END  # 确保设置正确的阶段
                    print("Moving to endpoint selection phase")
            
            return True
        
        # Using stairs
        if self.move_phase == PHASE_USE_TRANSPORT:
            # Using stairs to move up
            if self.up_btn.rect.collidepoint(pos):
                self.current_player.set_floor(self.current_player.floor + 1)
                self.current_floor = self.current_player.floor
                # Reset phase
                self.move_phase = PHASE_PREVIEW
                self.next_player()
                return True
            
            # Using stairs to move down
            if self.down_btn.rect.collidepoint(pos):
                self.current_player.set_floor(self.current_player.floor - 1)
                self.current_floor = self.current_player.floor
                # Reset phase
                self.move_phase = PHASE_PREVIEW
                self.next_player()
                return True
        
        # Using elevator
        if self.move_phase == PHASE_USE_TRANSPORT:
            # Check elevator floor buttons
            for i, btn in enumerate(self.floor_btns):
                if btn.rect.collidepoint(pos):
                    # Move to that floor
                    self.current_player.set_floor(i)
                    self.current_floor = i
                    # Reset phase
                    self.move_phase = PHASE_PREVIEW
                    self.next_player()
                    return True
        
        # 处理迷乱值按钮
        if self.increase_daze_btn.rect.collidepoint(pos):
            self.add_player_daze(1)
            return True
        
        if self.decrease_daze_btn.rect.collidepoint(pos):
            self.decrease_player_daze(1)
            return True
        
        return False
    
    def handle_floor_navigation(self, event):
        """Handle floor navigation
        
        Args:
            event: Mouse event
            
        Returns:
            Whether the event was handled
        """
        # Floor up button
        if self.floor_up_btn.rect.collidepoint(event.pos) and self.current_floor < FLOOR_NUM - 1:
            self.current_floor += 1
            print(f"Changing to floor {self.current_floor + 1}")
            return True
        
        # Floor down button
        if self.floor_down_btn.rect.collidepoint(event.pos) and self.current_floor > 0:
            self.current_floor -= 1
            print(f"Changing to floor {self.current_floor + 1}")
            return True
        
        return False
    
    def handle_event(self, event):
        """Handle game events
        
        Args:
            event: Pygame event
            
        Returns:
            Whether the event was handled
        """
        global EXIT
        
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        
        # Floor navigation - always active
        if event.type == MOUSEBUTTONDOWN:
            if self.handle_floor_navigation(event):
                return True
        
        # Initial position selection phase
        if self.selecting_start and event.type == MOUSEBUTTONDOWN:
            return self.handle_start_selection(event)
            
        # Handle keyboard events
        elif event.type == KEYDOWN:
            # Space key to roll dice
            if event.key == K_SPACE and self.move_phase == PHASE_ROLL_DICE:
                dice_value = self.roll_dice()
                
                # Make sure player has a position
                if self.current_player.pos is None:
                    print("Warning: Player has no position yet")
                    return True
                
                # Check if there are unplaced regions within movement range
                regions = self.get_reachable_regions(self.current_player.pos, dice_value)
                if regions:
                    self.valid_tiles = set(regions)
                    self.move_phase = PHASE_SELECT_REGION
                    print(f"Found {len(regions)} reachable regions: {regions}")
                else:
                    # Get valid moves
                    self.valid_tiles = self.get_valid_moves(self.current_player.pos, dice_value)
                    self.inner_tiles = self.valid_tiles
                    # Check if empty (no valid moves)
                    if not self.valid_tiles:
                        self.move_phase = PHASE_ROLL_DICE
                        self.next_player()
                    else:
                        self.move_phase = PHASE_SELECT_END
                        print(f"Found {len(self.valid_tiles)} valid move destinations")
                
                return True
                
        # Handle mouse events
        elif event.type == MOUSEBUTTONDOWN:            
            # Selecting region
            if self.move_phase == PHASE_SELECT_REGION:
                return self.handle_region_selection(event.pos)
            
            # Selecting end point
            elif self.move_phase == PHASE_SELECT_END:
                return self.handle_endpoint_selection(event.pos)
            
            # Handling button clicks
            else:
                return self.handle_button_click(event.pos)
        
        return False
    
    def run(self):
        """Run game main loop"""
        clock = pygame.time.Clock()
        
        print("\n--- GAME STARTING ---")
        print(f"Current floor: {self.current_floor}")
        print(f"Initial tile should be at center of floor {self.current_floor}")
        print("Checking initial tile status:")
        
        # Debug: Check the initial tile status
        center_region_x = center_region_y = MAP_SIZE // 2
        white_tiles = 0
        for x in range(center_region_x * REGION_SIZE, (center_region_x + 1) * REGION_SIZE):
            for y in range(center_region_y * REGION_SIZE, (center_region_y + 1) * REGION_SIZE):
                if self.tile_system.get_tile_status(x, y, self.current_floor):
                    white_tiles += 1
        
        print(f"Found {white_tiles} white tiles in center region of floor {self.current_floor}")
        
        # Make sure we are in selecting start phase
        self.selecting_start = True
        self.move_phase = PHASE_PREVIEW

        while True:
            for event in pygame.event.get():
                if self.handle_event(event):
                    continue
            
            # Draw game elements
            self.draw_all()
            
            # Check for win condition
            if WINNER != -1:
                self.draw_winning_screen()
            
            # Limit frame rate
            clock.tick(60)

    def draw_winning_screen(self):
        """Draw winning screen"""
        self.screen.fill((0, 0, 0))
        winner_text = self.font.render(f"{self.players[WINNER].name} Wins!", True, (255, 255, 0))
        text_rect = winner_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(winner_text, text_rect)
        
        pygame.display.flip()
        
        # Wait for player to close the game
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == KEYDOWN:
                    waiting = False

    def add_player_daze(self, value):
        """Increase current player's confusion value
        
        Args:
            value: Confusion value to increase
        """
        self.current_player.add_daze(value)
        
    def decrease_player_daze(self, value):
        """Decrease current player's confusion value
        
        Args:
            value: Confusion value to decrease
        """
        self.current_player.add_daze(-value)  # Use negative value to decrease confusion 

    def next_turn(self):
        """Advance to the next player's turn"""
        if self.state != 'game_end':
            # Unselect current player token
            self.player_tokens[self.current_player_index].set_selected(False)
            
            # Move to the next player
            self.current_player_index = (self.current_player_index + 1) % self.num_players
            self.current_player = self.players[self.current_player_index]
            
            # Reset turn state
            self.player_moved = False
            self.special_used = False
            self.state = 'play'  # Reset to play state
            self.active_region = None
            
            # Select new current player token
            self.player_tokens[self.current_player_index].set_selected(True)
            
            # Set current floor to player's floor
            self.current_floor = self.current_player.floor
            
            # Update UI elements for new player
            self.update_ui()
            
            print(f"Next turn: Player {self.current_player_index + 1}")

    def update_ui(self):
        """Update UI elements for the current player"""
        # Implement any necessary updates to the UI for the current player
        pass

    def place_region(self, region_x, region_y):
        """Place path region
        
        Args:
            region_x: Region X coordinate
            region_y: Region Y coordinate
            
        Returns:
            Whether the operation succeeded
        """
        # Place region using tile system
        if self.current_card is None:
            print("No card to place")
            return False
        
        success = self.tile_system.place_card(
            self.current_card, 
            region_x, region_y, 
            self.current_floor,
            self.card_rotation
        )
        
        if success:
            # Completely reset card-related state
            self.current_card = None
            self.card_rotation = 0
            self.target_region = None
            print("Card placed successfully, all card states reset")
            return True
        else:
            print("Failed to place region")
            return False