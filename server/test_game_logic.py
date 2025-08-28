#!/usr/bin/env python3
"""
Test script for NMB Game core logic components.
Run this to verify all classes work correctly before proceeding.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from game_logic.constants import *
from game_logic.player import Player, PlayerInventory
from game_logic.board import Board, Position, PathTile
from game_logic.cards import *

def test_constants():
    """Test constants module"""
    print("🧪 Testing Constants...")
    
    # Test disorder functions
    assert can_explore(3) == True
    assert can_explore(6) == False
    assert can_pass_walls(7) == True
    assert can_pass_walls(5) == False
    
    # Test phase calculation
    assert get_current_phase(25) == GamePhase.EXPLORATION
    assert get_current_phase(75) == GamePhase.MUTATION
    assert get_current_phase(150) == GamePhase.END_GAME
    
    print("✅ Constants tests passed!")

def test_player():
    """Test Player class"""
    print("🧪 Testing Player...")
    
    # Create player
    player = Player("TestPlayer", "socket123")
    assert player.name == "TestPlayer"
    assert player.disorder == 0
    assert player.floor == 2
    assert player.position == (0, 0)
    
    # Test disorder management
    player.update_disorder(3, "test increase")
    assert player.disorder == 3
    assert can_explore(player.disorder) == True
    
    player.update_disorder(4, "high disorder")
    assert player.disorder == 7
    assert can_explore(player.disorder) == False
    
    # Test inventory
    item = {"id": "test_item", "name": "Test Item"}
    assert player.inventory.add_item(item) == True
    assert len(player.inventory.items) == 1
    
    # Test turn management
    player.start_turn()
    assert player.turn_active == True
    player.set_movement_points(4)
    assert player.get_remaining_movement() == 4
    assert player.use_movement_points(2) == True
    assert player.get_remaining_movement() == 2
    
    # Test fall action
    fall_result = player.perform_fall()
    assert fall_result["success"] == True
    assert player.floor == 1
    assert player.disorder == 6  # Reduced by 1 after fall
    
    print("✅ Player tests passed!")

def test_board():
    """Test Board class"""
    print("🧪 Testing Board...")
    
    # Create board
    board = Board()
    
    # Check initial state
    initial_tiles = board.get_all_tiles()
    assert len(initial_tiles) == 1  # Should have initial tile
    assert initial_tiles[0].tile_id == "initial_tile"
    
    # Test position validation
    try:
        pos = Position(0, 0, 2)
        assert pos.floor == 2
    except ValueError:
        assert False, "Valid position should not raise error"
    
    # Test tile placement
    new_pos = Position(1, 0, 2)
    new_tile = PathTile("test_tile", PathTileType.BASIC, new_pos)
    assert board.place_tile(new_tile) == True
    
    # Test adjacency requirement
    far_pos = Position(5, 5, 2)
    far_tile = PathTile("far_tile", PathTileType.BASIC, far_pos)
    assert board.place_tile(far_tile) == False  # Should fail due to no adjacency
    
    # Test corruption
    board.corrupt_tile("test_tile")
    assert "test_tile" in board.corrupted_tiles
    assert board.get_corruption_percentage() > 0
    
    # Test zone assignment
    zone = board._assign_zone(new_pos)
    assert zone in ZONES
    
    print("✅ Board tests passed!")

def test_cards():
    """Test card system"""
    print("🧪 Testing Cards...")
    
    # Test PathTileCard
    path_card = PathTileCard(PathTileType.BASIC, name="Test Corridor")
    assert path_card.get_card_type() == CardType.PATH_TILE
    assert path_card.name == "Test Corridor"
    assert len(path_card.layout) == 16  # 4x4 grid
    
    # Test rotation
    old_layout = path_card.layout.copy()
    path_card.rotate(90)
    assert path_card.rotation == 90
    # Layout should have changed
    
    # Test ItemCard
    item_card = ItemCard(name="Test Item")
    assert item_card.get_card_type() == CardType.EFFECT
    assert item_card.effect_type == EffectCardType.SPECIAL_ITEM
    assert item_card.is_consumable == False  # Items are reusable
    
    # Test EventCard
    event_card = EventCard(name="Test Event")
    assert event_card.effect_type == EffectCardType.EVENT
    assert event_card.is_consumable == True
    
    # Test AnomalyCard
    anomaly_card = AnomalyCard(name="Test Anomaly")
    assert anomaly_card.effect_type == EffectCardType.ANOMALY
    assert anomaly_card.is_permanent == True
    
    # Test ButtonCard
    button_card = ButtonCard(available_floors=[2, 3, 4])
    assert button_card.get_card_type() == CardType.BUTTON
    assert button_card.can_access_floor(3) == True
    assert button_card.can_access_floor(5) == False
    
    # Test ZoneNameCard
    zone_card = ZoneNameCard("A", "Laboratory Wing")
    assert zone_card.get_card_type() == CardType.ZONE_NAME
    assert zone_card.is_revealed == False
    zone_name = zone_card.reveal()
    assert zone_card.is_revealed == True
    assert zone_name == "Laboratory Wing"
    
    print("✅ Card tests passed!")

def test_deck():
    """Test deck management"""
    print("🧪 Testing Decks...")
    
    # Create test deck
    cards = [PathTileCard(PathTileType.BASIC) for _ in range(10)]
    deck = Deck(CardType.PATH_TILE, cards)
    
    assert deck.cards_remaining() == 10
    assert deck.total_cards() == 10
    
    # Test drawing
    drawn_card = deck.draw()
    assert drawn_card is not None
    assert deck.cards_remaining() == 9
    
    # Test discarding
    deck.discard(drawn_card)
    assert len(deck.discarded) == 1
    
    # Test shuffling
    original_order = [card.card_id for card in deck.cards]
    deck.shuffle()
    new_order = [card.card_id for card in deck.cards]
    # Order should potentially be different (though might be same by chance)
    
    print("✅ Deck tests passed!")

def test_deck_creation():
    """Test starting deck creation"""
    print("🧪 Testing Deck Creation...")
    
    decks = create_starting_decks()
    
    # Check all deck types exist
    assert CardType.PATH_TILE in decks
    assert CardType.EFFECT in decks
    assert CardType.BUTTON in decks
    assert CardType.ZONE_NAME in decks
    
    # Check deck sizes
    assert decks[CardType.PATH_TILE].total_cards() == 60  # From create_starting_decks
    assert decks[CardType.EFFECT].total_cards() == 80
    assert decks[CardType.ZONE_NAME].total_cards() == 8
    
    # Test drawing from effect deck
    effect_card = decks[CardType.EFFECT].draw()
    assert effect_card is not None
    assert isinstance(effect_card, (ItemCard, EventCard, AnomalyCard))
    
    print("✅ Deck creation tests passed!")

def test_integration():
    """Test integration between components"""
    print("🧪 Testing Integration...")
    
    # Create game components
    board = Board()
    player1 = Player("Alice", "socket1")
    player2 = Player("Bob", "socket2")
    decks = create_starting_decks()
    
    # Test player interaction
    # Move players to same position
    player2.floor = player1.floor
    player2.position = player1.position
    
    # Test meeting (both have low disorder)
    meet_result = player1.meet_player(player2)
    assert meet_result["success"] == True
    assert player1.disorder == 0  # Should be reduced but was already 0
    
    # Test placing a path tile from deck
    path_card = decks[CardType.PATH_TILE].draw()
    assert path_card is not None
    
    # Create tile from card
    new_pos = Position(1, 0, 2)
    tile = PathTile(
        tile_id=path_card.card_id,
        tile_type=path_card.tile_type,
        position=new_pos,
        special_squares=path_card.layout
    )
    
    assert board.place_tile(tile) == True
    
    # Test player movement validation
    valid_moves = board.get_valid_moves_from_position(
        Position(0, 0, 2), 
        movement_points=3,
        player_disorder=player1.disorder
    )
    assert len(valid_moves) > 0
    
    print("✅ Integration tests passed!")

def main():
    """Run all tests"""
    print("🎮 NMB Game Core Logic Test Suite")
    print("=" * 50)
    
    try:
        test_constants()
        test_player()
        test_board()
        test_cards()
        test_deck()
        test_deck_creation()
        test_integration()
        
        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED!")
        print("✅ Core game logic is working correctly")
        print("🚀 Ready to proceed with Game engine implementation")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)