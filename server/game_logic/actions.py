"""
Game actions for NMB Game.
Implements all player actions: Explore, Fall, Move, Meet, Rob, use stairs/elevators, etc.
"""

from typing import Dict, List, Optional, Tuple, Any
import random
import logging
from datetime import datetime

from .constants import *
from .player import Player
from .board import Board, Position, TilePosition, PathTile
from .cards import *

def validate_action(game, socket_id: str, action_type: str) -> Tuple[bool, str]:
    """Validate if a player can perform an action"""
    if socket_id not in game.players:
        return False, "Player not found"
    
    if game.state.value != "playing":
        return False, "Game is not in playing state"
    
    if not game.is_player_turn(socket_id):
        return False, "Not your turn"
    
    player = game.players[socket_id]
    
    # Check action-specific requirements
    if action_type == ActionType.EXPLORE.value:
        if not can_explore(player.disorder):
            return False, f"Disorder too high ({player.disorder} >= {DISORDER_FALL_THRESHOLD}), must Fall"
        if player.get_remaining_movement() <= 0:
            return False, "No movement points remaining"
    
    elif action_type == ActionType.FALL.value:
        if can_explore(player.disorder):
            return False, f"Disorder too low ({player.disorder} < {DISORDER_FALL_THRESHOLD}), can Explore"
        if player.floor <= 1:
            return False, "Already on bottom floor"
    
    elif action_type == ActionType.MOVE.value:
        if player.get_remaining_movement() <= 0:
            return False, "No movement points remaining"
    
    return True, ""

# =============================================================================
# MOVEMENT ACTIONS
# =============================================================================

def action_move(game, socket_id: str, move_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle player movement action"""
    is_valid, reason = validate_action(game, socket_id, ActionType.MOVE.value)
    if not is_valid:
        return {"success": False, "reason": reason}
    
    player = game.players[socket_id]
    target_position = move_data.get("target_position")
    path = move_data.get("path", [])
    
    if not target_position:
        return {"success": False, "reason": "Target position required"}
    
    # Validate target position
    try:
        if "sub_x" in target_position and "sub_y" in target_position:
            # New position format with tile and sub-coordinates
            target_pos = Position(
                tile_x=target_position["tile_x"],
                tile_y=target_position["tile_y"], 
                sub_x=target_position["sub_x"],
                sub_y=target_position["sub_y"],
                floor=target_position["floor"]
            )
        else:
            # Legacy format - convert absolute coordinates to tile+sub
            abs_x = target_position["x"]
            abs_y = target_position["y"]
            tile_x = abs_x // 4
            tile_y = abs_y // 4
            sub_x = abs_x % 4
            sub_y = abs_y % 4
            target_pos = Position(tile_x, tile_y, sub_x, sub_y, target_position["floor"])
    except (ValueError, KeyError) as e:
        return {"success": False, "reason": f"Invalid target position: {str(e)}"}
    
    # Current position (already a Position object)
    current_pos = player.position
    
    # Check if target position is movable
    if not game.board.is_position_movable(target_pos):
        return {"success": False, "reason": "Target position is not movable (blocked by walls or obstacles)"}
    
    # Calculate movement cost (simple distance for now)
    abs_current = current_pos.to_absolute_coords()
    abs_target = target_pos.to_absolute_coords()
    movement_cost = abs(abs_target[0] - abs_current[0]) + abs(abs_target[1] - abs_current[1])
    
    # For now, use simple movement cost calculation
    # Later we can implement proper pathfinding with the new position system
    if movement_cost == 0:
        return {"success": False, "reason": "Already at target position"}
    
    # Check movement points
    if movement_cost > player.get_remaining_movement():
        return {"success": False, "reason": f"Not enough movement points ({movement_cost} needed, {player.get_remaining_movement()} available)"}
    
    # Perform movement
    player.use_movement_points(movement_cost)
    player.update_position(target_pos)
    player.floor = target_pos.floor
    
    # Trigger any tile effects at destination
    tile = game.board.get_tile(target_pos)
    tile_effects = []
    if tile:
        player.current_tile_id = tile.tile_id
        tile_effects = _handle_tile_effects(game, player, tile, "movement_end")
    
    game.total_actions += 1
    game._log_event("player_moved", f"{player.name} moved to {target_pos.to_tuple()} (cost: {movement_cost})", socket_id)
    
    return {
        "success": True,
        "player": player.name,
        "new_position": target_pos.to_tuple(),
        "movement_cost": movement_cost,
        "remaining_movement": player.get_remaining_movement(),
        "path": path,
        "tile_effects": tile_effects
    }

def action_explore(game, socket_id: str, explore_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle explore action - draw and place new path tile"""
    print(f"[DEBUG] Explore action called! socket_id: {socket_id}, data: {explore_data}")
    
    is_valid, reason = validate_action(game, socket_id, ActionType.EXPLORE.value)
    if not is_valid:
        print(f"[ERROR] Explore action validation failed: {reason}")
        return {"success": False, "reason": reason}
    
    print("[OK] Explore action validation passed!")
    
    player = game.players[socket_id]
    placement_position = explore_data.get("placement_position")
    print(f"[DEBUG] Player: {player.name}, placement_position: {placement_position}")
    
    # If no placement position specified, find the best adjacent position automatically
    if not placement_position:
        # Get player's current tile position
        current_tile_pos = TilePosition(
            x=player.position.tile_x,
            y=player.position.tile_y, 
            floor=player.position.floor
        )
        
        # Try adjacent positions in order: East, West, South, North
        adjacent_offsets = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        place_pos = None
        
        for dx, dy in adjacent_offsets:
            test_x = current_tile_pos.x + dx
            test_y = current_tile_pos.y + dy
            
            # Check bounds
            if 0 <= test_x < BOARD_SIZE[0] and 0 <= test_y < BOARD_SIZE[1]:
                test_pos = TilePosition(test_x, test_y, current_tile_pos.floor)
                
                # Check if position is not occupied
                if not game.board.get_tile_at_tile_pos(test_pos):
                    place_pos = test_pos
                    break
        
        if not place_pos:
            return {"success": False, "reason": "No adjacent positions available for tile placement"}
    else:
        # Handle legacy frontend that still sends placement_position
        try:
            # For tile placement, we use tile coordinates (not sub-positions)
            if "tile_x" in placement_position:
                place_pos = TilePosition(
                    x=placement_position["tile_x"],
                    y=placement_position["tile_y"],
                    floor=placement_position["floor"]
                )
            else:
                # Legacy format - convert absolute to tile coordinates
                abs_x = placement_position["x"]
                abs_y = placement_position["y"]
                tile_x = abs_x // 4
                tile_y = abs_y // 4
                place_pos = TilePosition(tile_x, tile_y, placement_position["floor"])
        except (ValueError, KeyError) as e:
            return {"success": False, "reason": f"Invalid placement position: {str(e)}"}
    
    # Draw path tile from deck
    path_card = game.decks[CardType.PATH_TILE].draw()
    if not path_card:
        return {"success": False, "reason": "No path tiles remaining"}
    
    # Check if placement position is valid (adjacent to existing tiles)
    if not game.board._has_adjacent_tile(place_pos):
        # Return card to deck
        game.decks[CardType.PATH_TILE].add_card(path_card)
        return {"success": False, "reason": "Tile must be placed adjacent to existing tiles"}
    
    # Create tile from card
    new_tile = PathTile(
        tile_id=path_card.card_id,
        tile_type=path_card.tile_type,
        position=place_pos,
        special_squares=path_card.layout,
        rotation=path_card.rotation
    )
    
    # Place tile on board
    if not game.board.place_tile(new_tile):
        game.decks[CardType.PATH_TILE].add_card(path_card)
        return {"success": False, "reason": "Cannot place tile at this position"}
    
    # Handle disordered tiles
    disorder_increase = 0
    if new_tile.tile_type == PathTileType.DISORDERED:
        disorder_increase = 1
        player.update_disorder(disorder_increase, "placed disordered tile")
    
    # Use remaining movement to continue onto new tile
    remaining_movement = player.get_remaining_movement()
    if remaining_movement > 0:
        # Move to new tile - find a valid entrance point
        entrance_points = new_tile.get_entrance_points()
        if entrance_points:
            entrance_pos = entrance_points[0]  # Use first available entrance
            # Create proper Position with tile + sub coordinates
            new_position = Position(
                tile_x=place_pos.x,
                tile_y=place_pos.y,
                sub_x=entrance_pos[0],
                sub_y=entrance_pos[1],
                floor=place_pos.floor
            )
            player.use_movement_points(1)
            player.update_position(new_position)
            player.floor = place_pos.floor
            player.current_tile_id = new_tile.tile_id
    
    # Update statistics
    player.stats['tiles_explored'] += 1
    
    game.total_actions += 1
    game._log_event("tile_explored", 
                    f"{player.name} explored and placed {new_tile.tile_type.value} tile at {place_pos.to_tuple()}", 
                    socket_id)
    
    return {
        "success": True,
        "player": player.name,
        "tile_placed": new_tile.to_dict(),
        "disorder_increase": disorder_increase,
        "moved_to_tile": remaining_movement > 0,
        "remaining_movement": player.get_remaining_movement()
    }

def action_fall(game, socket_id: str, fall_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Handle fall action - drop to floor below"""
    is_valid, reason = validate_action(game, socket_id, ActionType.FALL.value)
    if not is_valid:
        return {"success": False, "reason": reason}
    
    player = game.players[socket_id]
    
    # Perform fall
    fall_result = player.perform_fall()
    if not fall_result["success"]:
        return fall_result
    
    # Draw and place new path tile on the floor below
    path_card = game.decks[CardType.PATH_TILE].draw()
    if path_card:
        # Place tile at player's position on new floor
        fall_pos = Position(player.position[0], player.position[1], player.floor)
        
        new_tile = PathTile(
            tile_id=path_card.card_id,
            tile_type=path_card.tile_type,
            position=fall_pos,
            special_squares=path_card.layout
        )
        
        if game.board.place_tile(new_tile):
            player.current_tile_id = new_tile.tile_id
            fall_result["tile_placed"] = new_tile.to_dict()
        else:
            # Return card to deck if can't place
            game.decks[CardType.PATH_TILE].add_card(path_card)
    
    game.total_actions += 1
    game._log_event("player_fell", f"{player.name} fell to floor {player.floor}", socket_id)
    
    return fall_result

# =============================================================================
# PLAYER INTERACTION ACTIONS
# =============================================================================

def action_meet(game, socket_id: str, meet_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle meet action with another player"""
    player = game.players[socket_id]
    target_socket_id = meet_data.get("target_player")
    
    if not target_socket_id or target_socket_id not in game.players:
        return {"success": False, "reason": "Target player not found"}
    
    target_player = game.players[target_socket_id]
    
    # Perform meet action
    meet_result = player.meet_player(target_player)
    
    if meet_result["success"]:
        game._log_event("players_met", meet_result["message"], socket_id)
    
    return meet_result

def action_rob(game, socket_id: str, rob_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle rob action - steal card from another player"""
    player = game.players[socket_id]
    target_socket_id = rob_data.get("target_player")
    
    if not target_socket_id or target_socket_id not in game.players:
        return {"success": False, "reason": "Target player not found"}
    
    target_player = game.players[target_socket_id]
    
    # Perform rob action
    rob_result = player.rob_player(target_player)
    
    if rob_result["success"]:
        game._log_event("player_robbed", rob_result["message"], socket_id)
    
    return rob_result

# =============================================================================
# SPECIAL ACTIONS
# =============================================================================

def action_use_stairs(game, socket_id: str, stairs_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle stairwell usage"""
    player = game.players[socket_id]
    target_floor = stairs_data.get("target_floor")
    
    if target_floor not in range(*FLOOR_RANGE):
        return {"success": False, "reason": "Invalid target floor"}
    
    # Check if player is on a stairwell tile
    current_pos = Position(player.position[0], player.position[1], player.floor)
    tile = game.board.get_tile(current_pos)
    
    if not tile or tile.tile_type != PathTileType.STAIRWELL:
        return {"success": False, "reason": "Must be on a stairwell tile"}
    
    # Check floor difference
    floor_diff = abs(target_floor - player.floor)
    if floor_diff != 1:
        return {"success": False, "reason": "Stairwells only allow movement to adjacent floors"}
    
    # Perform movement
    old_floor = player.floor
    player.change_floor(target_floor, "used stairwell")
    
    # Remove stairwell tile after use
    game.board.remove_tile(current_pos)
    
    # Find or create landing position on target floor
    target_pos = Position(player.position[0], player.position[1], target_floor)
    target_tile = game.board.get_tile(target_pos)
    
    if not target_tile:
        # Create basic tile at landing position
        path_card = game.decks[CardType.PATH_TILE].draw()
        if path_card and path_card.tile_type == PathTileType.BASIC:
            landing_tile = PathTile(
                tile_id=path_card.card_id,
                tile_type=path_card.tile_type,
                position=target_pos,
                special_squares=path_card.layout
            )
            game.board.place_tile(landing_tile)
            player.current_tile_id = landing_tile.tile_id
    else:
        player.current_tile_id = target_tile.tile_id
    
    game._log_event("used_stairs", f"{player.name} used stairs from floor {old_floor} to {target_floor}", socket_id)
    
    return {
        "success": True,
        "player": player.name,
        "old_floor": old_floor,
        "new_floor": target_floor,
        "stairwell_removed": True
    }

def action_use_elevator(game, socket_id: str, elevator_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle elevator usage"""
    player = game.players[socket_id]
    target_floor = elevator_data.get("target_floor")
    target_zone = elevator_data.get("target_zone")
    
    # Check if player is on an elevator tile
    current_pos = Position(player.position[0], player.position[1], player.floor)
    tile = game.board.get_tile(current_pos)
    
    if not tile or tile.tile_type != PathTileType.ELEVATOR:
        return {"success": False, "reason": "Must be on an elevator tile"}
    
    # Draw button card to determine available destinations
    button_card = game.decks[CardType.BUTTON].draw()
    if not button_card:
        return {"success": False, "reason": "No elevator buttons available"}
    
    # Check if target floor/zone is accessible
    if target_floor and not button_card.can_access_floor(target_floor):
        game.decks[CardType.BUTTON].discard(button_card)
        return {"success": False, "reason": f"Elevator button doesn't access floor {target_floor}"}
    
    if target_zone and not button_card.can_access_zone(target_zone):
        game.decks[CardType.BUTTON].discard(button_card)
        return {"success": False, "reason": f"Elevator button doesn't access zone {target_zone}"}
    
    # Check for malfunction in mutation+ phases
    if game.current_phase in [GamePhase.MUTATION, GamePhase.END_GAME]:
        if random.random() < ELEVATOR_MALFUNCTION_CHANCE:
            game.decks[CardType.BUTTON].discard(button_card)
            game._log_event("elevator_malfunction", f"Elevator malfunctioned for {player.name}", socket_id)
            return {"success": False, "reason": "Elevator malfunctioned!"}
    
    # Perform elevator travel
    old_floor = player.floor
    old_position = player.position
    
    if target_floor:
        player.change_floor(target_floor, "used elevator")
    
    # If targeting specific zone, try to place player there
    if target_zone:
        # Find a position in the target zone or create one
        zone_positions = [pos for pos, zone in game.board.zone_assignments.items() if zone == target_zone]
        
        if zone_positions:
            # Pick random position in zone
            new_pos_2d = random.choice(zone_positions)
            player.update_position(new_pos_2d)
        else:
            # Create new position in zone
            x, y = random.randint(0, BOARD_SIZE[0]-1), random.randint(0, BOARD_SIZE[1]-1)
            player.update_position((x, y))
            game.board.zone_assignments[(x, y)] = target_zone
    
    # Find or create elevator tile at destination
    dest_pos = Position(player.position[0], player.position[1], player.floor)
    dest_tile = game.board.get_tile(dest_pos)
    
    if not dest_tile:
        # Create elevator tile at destination
        elevator_tile = PathTile(
            tile_id=f"elevator_dest_{dest_pos.x}_{dest_pos.y}_{dest_pos.floor}",
            tile_type=PathTileType.ELEVATOR,
            position=dest_pos
        )
        game.board.place_tile(elevator_tile)
        player.current_tile_id = elevator_tile.tile_id
    
    game.decks[CardType.BUTTON].discard(button_card)
    
    game._log_event("used_elevator", 
                    f"{player.name} used elevator from floor {old_floor} to floor {player.floor}" + 
                    (f" zone {target_zone}" if target_zone else ""), 
                    socket_id)
    
    return {
        "success": True,
        "player": player.name,
        "old_floor": old_floor,
        "new_floor": player.floor,
        "old_position": old_position,
        "new_position": player.position,
        "target_zone": target_zone,
        "button_card": button_card.to_dict()
    }

def action_use_item(game, socket_id: str, item_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle item card usage"""
    player = game.players[socket_id]
    item_id = item_data.get("item_id")
    
    if not item_id:
        return {"success": False, "reason": "Item ID required"}
    
    # Find item in player's inventory
    item = player.inventory.remove_item(item_id)
    if not item:
        return {"success": False, "reason": "Item not found in inventory"}
    
    # Apply item effects (simplified - would need full effect system)
    effect_results = []
    item_name = item.get("name", "Unknown Item")
    
    # Basic item effects (expand based on actual item types)
    if "First Aid Kit" in item_name:
        player.update_disorder(-2, "used first aid kit")
        effect_results.append({"type": "disorder_heal", "value": -2})
    elif "Flashlight" in item_name:
        effect_results.append({"type": "vision_bonus", "duration": 3})
    elif "Emergency Radio" in item_name:
        # Share information with all players
        effect_results.append({"type": "share_info", "target": "all_players"})
    
    game._log_event("used_item", f"{player.name} used {item_name}", socket_id)
    
    return {
        "success": True,
        "player": player.name,
        "item_used": item,
        "effects": effect_results
    }

# =============================================================================
# BASIC ACTIONS
# =============================================================================

def action_pass(game, socket_id: str, pass_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Handle pass action - do nothing"""
    player = game.players[socket_id]
    
    game._log_event("player_passed", f"{player.name} passed their action", socket_id)
    
    return {
        "success": True,
        "player": player.name,
        "message": "Turn passed"
    }

def action_end_turn(game, socket_id: str, end_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Handle end turn action"""
    return game.end_turn(socket_id)

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _handle_tile_effects(game, player: Player, tile: PathTile, trigger: str) -> List[Dict[str, Any]]:
    """Handle special tile effects when triggered"""
    effects = []
    
    # Get player's local position on tile (simplified - assume center)
    local_pos = (1, 1)  # Center of 4x4 tile
    
    square_type = tile.special_squares.get(local_pos, SpecialSquareType.NORMAL)
    
    if square_type == SpecialSquareType.EVENT_SQUARE and trigger == "movement_end":
        # Draw event card
        event_card = game.decks[CardType.EFFECT].draw()
        if event_card and isinstance(event_card, EventCard):
            # Apply event effects
            event_result = event_card.apply_effects(player, game)
            effects.append({
                "type": "event_triggered",
                "card": event_card.to_dict(),
                "result": event_result
            })
            
            # Discard event card after use
            game.decks[CardType.EFFECT].discard(event_card)
    
    elif square_type == SpecialSquareType.ITEM_SQUARE and trigger == "movement_end":
        # Draw item card
        item_card = game.decks[CardType.EFFECT].draw()
        if item_card and isinstance(item_card, ItemCard):
            if player.inventory.add_item(item_card.to_dict()):
                effects.append({
                    "type": "item_found",
                    "card": item_card.to_dict()
                })
                player.stats['items_found'] += 1
            else:
                # Return to deck if inventory full
                game.decks[CardType.EFFECT].add_card(item_card)
                effects.append({
                    "type": "item_found_inventory_full",
                    "card": item_card.to_dict()
                })
    
    elif square_type == SpecialSquareType.EMERGENCY_DOOR and trigger == "movement_end":
        # Check if player has required escape items
        if player.escape_items_collected >= ESCAPE_ITEMS_REQUIRED:
            effects.append({
                "type": "escape_available",
                "message": "You can escape through this door!"
            })
        else:
            effects.append({
                "type": "escape_blocked",
                "message": f"Need {ESCAPE_ITEMS_REQUIRED - player.escape_items_collected} more escape items"
            })
    
    return effects

# Action mapping for easy dispatch
ACTION_HANDLERS = {
    ActionType.MOVE.value: action_move,
    ActionType.EXPLORE.value: action_explore,
    ActionType.FALL.value: action_fall,
    ActionType.MEET.value: action_meet,
    ActionType.ROB.value: action_rob,
    ActionType.USE_STAIRS.value: action_use_stairs,
    ActionType.USE_ELEVATOR.value: action_use_elevator,
    ActionType.USE_ITEM.value: action_use_item,
    ActionType.PASS.value: action_pass,
    "end_turn": action_end_turn
}

def execute_action(game, socket_id: str, action_type: str, action_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a player action"""
    if action_type not in ACTION_HANDLERS:
        return {"success": False, "reason": f"Unknown action type: {action_type}"}
    
    handler = ACTION_HANDLERS[action_type]
    
    try:
        result = handler(game, socket_id, action_data)
        
        # Update game state after action
        if result.get("success"):
            game.last_updated = datetime.now()
        
        return result
    
    except Exception as e:
        logging.error(f"Error executing action {action_type} for player {socket_id}: {e}")
        return {"success": False, "reason": f"Internal error: {str(e)}"}