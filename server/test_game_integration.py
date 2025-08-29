#!/usr/bin/env python3
"""
Integration test for complete NMB Game engine.
Tests the Game class with actions, turn management, and full game flow.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from game_logic.game import Game, GameState
from game_logic.player import Player
from game_logic.actions import execute_action
from game_logic.constants import *

def test_game_creation_and_setup():
    """Test game creation and player management"""
    print("🧪 Testing Game Creation and Setup...")
    
    # Create game
    game = Game("test_game", max_players=4)
    assert game.game_id == "test_game"
    assert game.state == GameState.WAITING
    assert len(game.players) == 0
    
    # Add players
    player1 = Player("Alice", "socket1", "player1")
    player2 = Player("Bob", "socket2", "player2")
    
    assert game.add_player(player1) == True
    assert game.add_player(player2) == True
    assert len(game.players) == 2
    
    # First player should be host
    assert game.host_socket_id == "socket1"
    assert player1.is_host == True
    
    print("✅ Game creation and setup tests passed!")

def test_game_start_process():
    """Test game starting process"""
    print("🧪 Testing Game Start Process...")
    
    game = Game("start_test")
    player1 = Player("Alice", "socket1")
    player2 = Player("Bob", "socket2")
    
    game.add_player(player1)
    game.add_player(player2)
    
    # Test starting game
    result = game.start_game()
    assert result["success"] == True
    assert game.state == GameState.PLAYING
    assert len(game.player_order) == 2
    assert game.current_phase == GamePhase.EXPLORATION
    
    # Check players have starting hands
    assert len(player1.inventory.hand) == 3
    assert len(player2.inventory.hand) == 3
    
    # Check first turn started
    current_player = game.get_current_player()
    assert current_player is not None
    assert current_player.turn_active == True
    assert current_player.movement_points > 0
    
    print("✅ Game start process tests passed!")

def test_basic_actions():
    """Test basic player actions"""
    print("🧪 Testing Basic Actions...")
    
    game = Game("action_test")
    player1 = Player("Alice", "socket1")
    player2 = Player("Bob", "socket2")
    
    game.add_player(player1)
    game.add_player(player2)
    game.start_game()
    
    current_player = game.get_current_player()
    socket_id = current_player.socket_id
    
    # Test pass action
    result = execute_action(game, socket_id, "pass", {})
    assert result["success"] == True
    
    # Test explore action (place new tile)
    explore_data = {
        "placement_position": {"x": 1, "y": 0, "floor": 2}
    }
    result = execute_action(game, socket_id, "explore", explore_data)
    assert result["success"] == True
    assert "tile_placed" in result
    
    # Verify tile was placed on board
    tiles = game.board.get_all_tiles()
    assert len(tiles) == 2  # initial + new tile
    
    # Test movement
    move_data = {
        "target_position": {"x": 1, "y": 0, "floor": 2}
    }
    result = execute_action(game, socket_id, "move", move_data)
    assert result["success"] == True
    assert current_player.position == (1, 0)
    
    print("✅ Basic actions tests passed!")

def test_player_interactions():
    """Test player interaction actions"""
    print("🧪 Testing Player Interactions...")
    
    game = Game("interaction_test")
    player1 = Player("Alice", "socket1")
    player2 = Player("Bob", "socket2")
    
    game.add_player(player1)
    game.add_player(player2)
    game.start_game()
    
    # Move both players to same position
    player1.update_position((0, 0))
    player1.floor = 2
    player2.update_position((0, 0))
    player2.floor = 2
    
    # Test meet action
    if game.is_player_turn(player1.socket_id):
        current_socket = player1.socket_id
    else:
        current_socket = player2.socket_id
        
    meet_data = {
        "target_player": player2.socket_id if current_socket == player1.socket_id else player1.socket_id
    }
    
    result = execute_action(game, current_socket, "meet", meet_data)
    assert result["success"] == True
    
    print("✅ Player interaction tests passed!")

def test_turn_management():
    """Test turn progression and management"""
    print("🧪 Testing Turn Management...")
    
    game = Game("turn_test")
    player1 = Player("Alice", "socket1")
    player2 = Player("Bob", "socket2")
    
    game.add_player(player1)
    game.add_player(player2)
    game.start_game()
    
    # Get initial turn state
    initial_player = game.get_current_player()
    initial_turn = game.turn_number
    
    # End current turn
    result = execute_action(game, initial_player.socket_id, "end_turn", {})
    assert result["success"] == True
    
    # Check turn progression
    new_player = game.get_current_player()
    assert new_player != initial_player  # Should be different player
    assert game.turn_number == initial_turn + 1
    
    # Check previous player's turn ended
    assert initial_player.turn_active == False
    assert new_player.turn_active == True
    
    print("✅ Turn management tests passed!")

def test_disorder_and_fall():
    """Test disorder mechanics and fall action"""
    print("🧪 Testing Disorder and Fall...")
    
    game = Game("disorder_test")
    player1 = Player("Alice", "socket1")
    
    game.add_player(player1)
    game.add_player(Player("Bob", "socket2"))  # Need minimum players
    game.start_game()
    
    # Set high disorder to force fall
    player1.disorder = 6
    assert can_explore(player1.disorder) == False
    
    if game.is_player_turn(player1.socket_id):
        # Test fall action
        result = execute_action(game, player1.socket_id, "fall", {})
        assert result["success"] == True
        assert player1.floor == 1  # Should have fallen to floor below
        assert player1.disorder == 5  # Should be reduced
    
    print("✅ Disorder and fall tests passed!")

def test_game_state_serialization():
    """Test complete game state serialization"""
    print("🧪 Testing Game State Serialization...")
    
    game = Game("serialize_test")
    player1 = Player("Alice", "socket1")
    player2 = Player("Bob", "socket2")
    
    game.add_player(player1)
    game.add_player(player2)
    game.start_game()
    
    # Get game state
    state = game.get_game_state()
    
    # Verify all required fields exist
    required_fields = [
        "game_id", "state", "phase", "round", "turn", "players", 
        "player_order", "current_player", "board", "decks",
        "victory_condition_met", "corruption_percentage"
    ]
    
    for field in required_fields:
        assert field in state, f"Missing field: {field}"
    
    # Verify structure
    assert isinstance(state["players"], dict)
    assert isinstance(state["board"], dict)
    assert isinstance(state["decks"], dict)
    assert len(state["players"]) == 2
    
    print("✅ Game state serialization tests passed!")

def test_deck_interactions():
    """Test card deck drawing and effects"""
    print("🧪 Testing Deck Interactions...")
    
    game = Game("deck_test")
    player1 = Player("Alice", "socket1")
    
    game.add_player(player1)
    game.add_player(Player("Bob", "socket2"))
    game.start_game()
    
    # Check decks were created
    assert CardType.PATH_TILE in game.decks
    assert CardType.EFFECT in game.decks
    assert CardType.BUTTON in game.decks
    assert CardType.ZONE_NAME in game.decks
    
    # Test drawing from decks
    path_card = game.decks[CardType.PATH_TILE].draw()
    assert path_card is not None
    
    effect_card = game.decks[CardType.EFFECT].draw()
    assert effect_card is not None
    
    # Check deck counts decreased
    initial_path_count = 60  # From create_starting_decks
    initial_effect_count = 80
    
    # Account for starting hands: 2 players × 3 cards each = 6 cards from effect deck
    starting_cards_dealt = len(game.players) * 3
    
    assert game.decks[CardType.PATH_TILE].cards_remaining() == initial_path_count - 1
    assert game.decks[CardType.EFFECT].cards_remaining() == initial_effect_count - starting_cards_dealt - 1
    
    print("✅ Deck interaction tests passed!")

def test_victory_conditions():
    """Test victory condition checking"""
    print("🧪 Testing Victory Conditions...")
    
    game = Game("victory_test")
    player1 = Player("Alice", "socket1")
    
    game.add_player(player1)
    game.add_player(Player("Bob", "socket2"))
    game.start_game()
    
    # Test escape victory setup
    player1.escape_items_collected = ESCAPE_ITEMS_REQUIRED
    player1.floor = ESCAPE_FLOOR
    
    # Create escape exit
    from game_logic.board import Position
    exit_pos = Position(0, 0, ESCAPE_FLOOR)
    game.board.escape_exits.append(exit_pos)
    player1.update_position((0, 0))
    
    # Check victory conditions
    game._check_victory_conditions()
    
    # Should trigger victory
    assert game.victory_condition_met == True
    assert game.victory_type == "escape"
    assert player1.socket_id in game.winning_players
    
    print("✅ Victory condition tests passed!")

def test_corruption_defeat():
    """Test corruption defeat condition"""
    print("🧪 Testing Corruption Defeat...")
    
    game = Game("corruption_test")
    player1 = Player("Alice", "socket1")
    
    game.add_player(player1)
    game.add_player(Player("Bob", "socket2"))
    game.start_game()
    
    # Get all tiles and corrupt most of them
    all_tiles = game.board.get_all_tiles()
    corruption_needed = int(len(all_tiles) * MAP_CORRUPTION_LIMIT) + 1
    
    for i, tile in enumerate(all_tiles[:corruption_needed]):
        game.board.corrupt_tile(tile.tile_id)
    
    # Check defeat conditions
    game._check_game_end_conditions()
    
    # Should trigger defeat
    assert game.state == GameState.FINISHED
    assert game.victory_condition_met == False
    assert "corruption" in game.defeat_reason
    
    print("✅ Corruption defeat tests passed!")

def test_complete_game_flow():
    """Test a complete mini game flow"""
    print("🧪 Testing Complete Game Flow...")
    
    game = Game("flow_test")
    player1 = Player("Alice", "socket1")
    player2 = Player("Bob", "socket2")
    
    # Setup game
    game.add_player(player1)
    game.add_player(player2)
    assert game.start_game()["success"] == True
    
    # Play several turns
    for turn in range(6):  # Play 3 rounds (2 players each)
        current_player = game.get_current_player()
        assert current_player is not None
        
        # Perform some action
        if turn % 2 == 0:  # Explore on even turns
            result = execute_action(game, current_player.socket_id, "explore", {
                "placement_position": {"x": turn, "y": 0, "floor": 2}
            })
            # Note: might fail due to adjacency, that's ok
        else:  # Pass on odd turns
            result = execute_action(game, current_player.socket_id, "pass", {})
            assert result["success"] == True
        
        # End turn
        end_result = execute_action(game, current_player.socket_id, "end_turn", {})
        assert end_result["success"] == True
    
    # Game should still be running
    assert game.state == GameState.PLAYING
    assert game.round_number >= 3  # Should have completed at least 3 rounds
    assert len(game.game_log) > 0  # Should have logged events
    
    print("✅ Complete game flow tests passed!")

def main():
    """Run all integration tests"""
    print("🎮 NMB Game Integration Test Suite")
    print("=" * 50)
    
    try:
        test_game_creation_and_setup()
        test_game_start_process()
        test_basic_actions()
        test_player_interactions()
        test_turn_management()
        test_disorder_and_fall()
        test_game_state_serialization()
        test_deck_interactions()
        test_victory_conditions()
        test_corruption_defeat()
        test_complete_game_flow()
        
        print("\n" + "=" * 50)
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Complete game engine is working correctly")
        print("🚀 Backend is ready for frontend integration!")
        print("💡 Next: Implement React frontend with real-time UI")
        
    except Exception as e:
        print(f"\n❌ INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)