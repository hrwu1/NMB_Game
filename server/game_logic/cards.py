"""
Card classes for NMB Game.
Handles all card types: Path tiles, Effect cards, Items, Anomalies, Button cards, Zone Name cards.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import uuid
import random

from .constants import (
    CardType, PathTileType, EffectCardType, SpecialSquareType,
    DECK_SIZES, ZONES, ZONE_NAME_CARDS, ActionType
)

class CardRarity(Enum):
    """Card rarity levels"""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    LEGENDARY = "legendary"

@dataclass
class CardEffect:
    """Represents a card effect that can be applied"""
    effect_type: str
    target: str  # "self", "all_players", "board", "game"
    value: Any = None
    duration: Optional[int] = None  # Turns, None = permanent
    condition: Optional[str] = None
    description: str = ""

class BaseCard(ABC):
    """Abstract base class for all cards"""
    
    def __init__(self, card_id: str = None, name: str = "", description: str = ""):
        self.card_id = card_id or str(uuid.uuid4())[:8]
        self.name = name
        self.description = description
        self.created_at = None
    
    @abstractmethod
    def get_card_type(self) -> CardType:
        """Return the type of this card"""
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert card to dictionary for serialization"""
        pass
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

# =============================================================================
# PATH TILE CARDS
# =============================================================================

class PathTileCard(BaseCard):
    """Path tile cards used to expand the map"""
    
    def __init__(self, tile_type: PathTileType = PathTileType.BASIC, 
                 layout: Dict[tuple, SpecialSquareType] = None, 
                 connections: List[tuple] = None, **kwargs):
        super().__init__(**kwargs)
        self.tile_type = tile_type
        self.layout = layout or self._generate_default_layout()
        self.connections = connections or []
        self.rotation = 0
        self.is_disordered = tile_type == PathTileType.DISORDERED
        
        # Set default name if not provided
        if not self.name:
            self.name = self._generate_tile_name()
    
    def get_card_type(self) -> CardType:
        return CardType.PATH_TILE
    
    def _generate_default_layout(self) -> Dict[tuple, SpecialSquareType]:
        """Generate a random 4x4 tile layout"""
        layout = {}
        
        # Fill with normal squares
        for x in range(4):
            for y in range(4):
                layout[(x, y)] = SpecialSquareType.NORMAL
        
        # Add special features based on tile type
        if self.tile_type == PathTileType.STAIRWELL:
            layout[(1, 1)] = SpecialSquareType.STAIRWELL
            layout[(2, 2)] = SpecialSquareType.STAIRWELL
        elif self.tile_type == PathTileType.ELEVATOR:
            # 2x2 elevator room in center
            for x in range(1, 3):
                for y in range(1, 3):
                    layout[(x, y)] = SpecialSquareType.ELEVATOR_ROOM
        elif self.tile_type == PathTileType.BASIC:
            # Random special squares
            special_count = random.randint(0, 2)
            special_types = [SpecialSquareType.EVENT_SQUARE, SpecialSquareType.ITEM_SQUARE, 
                           SpecialSquareType.EMERGENCY_DOOR]
            
            for _ in range(special_count):
                x, y = random.randint(0, 3), random.randint(0, 3)
                if layout.get((x, y)) == SpecialSquareType.NORMAL:
                    layout[(x, y)] = random.choice(special_types)
        elif self.tile_type == PathTileType.DISORDERED:
            # Add some walls to make it more dangerous
            wall_count = random.randint(2, 4)
            for _ in range(wall_count):
                x, y = random.randint(0, 3), random.randint(0, 3)
                layout[(x, y)] = SpecialSquareType.WALL
        
        return layout
    
    def _generate_tile_name(self) -> str:
        """Generate a name for the tile based on its type"""
        names_by_type = {
            PathTileType.BASIC: ["Corridor", "Hallway", "Room", "Chamber", "Passage"],
            PathTileType.DISORDERED: ["Twisted Hall", "Corrupted Room", "Nightmare Chamber", "Warped Passage"],
            PathTileType.STAIRWELL: ["Stairwell", "Stairs", "Staircase"],
            PathTileType.ELEVATOR: ["Elevator", "Lift", "Elevator Shaft"],
            PathTileType.CONSTRUCTION: ["Construction Zone", "Under Repair", "Blocked Passage"],
            PathTileType.ROTATING: ["Rotating Room", "Shifting Chamber", "Moving Platform"],
            PathTileType.INITIAL: ["Starting Area", "Entrance Hall"]
        }
        
        return random.choice(names_by_type.get(self.tile_type, ["Unknown Room"]))
    
    def rotate(self, degrees: int = 90) -> None:
        """Rotate the tile layout"""
        self.rotation = (self.rotation + degrees) % 360
        
        if degrees % 90 == 0:  # Only rotate in 90-degree increments
            # Rotate the layout dictionary
            rotated_layout = {}
            for (x, y), square_type in self.layout.items():
                # Rotate coordinates
                if degrees == 90:
                    new_x, new_y = 3 - y, x
                elif degrees == 180:
                    new_x, new_y = 3 - x, 3 - y
                elif degrees == 270:
                    new_x, new_y = y, 3 - x
                else:
                    new_x, new_y = x, y
                
                rotated_layout[(new_x, new_y)] = square_type
            
            self.layout = rotated_layout
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_id": self.card_id,
            "name": self.name,
            "description": self.description,
            "type": "path_tile",
            "tile_type": self.tile_type.value,
            "layout": {f"{k[0]},{k[1]}": v.value for k, v in self.layout.items()},
            "connections": self.connections,
            "rotation": self.rotation,
            "is_disordered": self.is_disordered
        }

# =============================================================================
# EFFECT CARDS (Items, Events, Anomalies)
# =============================================================================

class EffectCard(BaseCard):
    """Base class for effect cards (items, events, anomalies)"""
    
    def __init__(self, effect_type: EffectCardType, rarity: CardRarity = CardRarity.COMMON,
                 effects: List[CardEffect] = None, cost: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.effect_type = effect_type
        self.rarity = rarity
        self.effects = effects or []
        self.cost = cost  # Cost to use (if applicable)
        self.is_permanent = False
        self.is_consumable = True
    
    def get_card_type(self) -> CardType:
        return CardType.EFFECT
    
    def can_use(self, player=None, game_state=None) -> tuple[bool, str]:
        """Check if card can be used in current context"""
        # Override in subclasses for specific requirements
        return True, ""
    
    def apply_effects(self, player=None, game_state=None) -> Dict[str, Any]:
        """Apply the card's effects"""
        results = []
        
        for effect in self.effects:
            result = self._apply_single_effect(effect, player, game_state)
            results.append(result)
        
        return {
            "success": True,
            "results": results,
            "card_consumed": self.is_consumable
        }
    
    def _apply_single_effect(self, effect: CardEffect, player=None, game_state=None) -> Dict[str, Any]:
        """Apply a single effect (override in subclasses)"""
        return {"effect_type": effect.effect_type, "applied": True}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_id": self.card_id,
            "name": self.name,
            "description": self.description,
            "type": "effect",
            "effect_type": self.effect_type.value,
            "rarity": self.rarity.value,
            "cost": self.cost,
            "is_permanent": self.is_permanent,
            "is_consumable": self.is_consumable,
            "effects": [
                {
                    "effect_type": e.effect_type,
                    "target": e.target,
                    "value": e.value,
                    "duration": e.duration,
                    "description": e.description
                }
                for e in self.effects
            ]
        }

class ItemCard(EffectCard):
    """Special item cards - generally beneficial"""
    
    def __init__(self, **kwargs):
        super().__init__(effect_type=EffectCardType.SPECIAL_ITEM, **kwargs)
        self.is_consumable = False  # Items are typically reusable
        
        # Set default name and effects if not provided
        if not self.name:
            self.name, self.effects = self._generate_random_item()
    
    def _generate_random_item(self) -> tuple[str, List[CardEffect]]:
        """Generate a random beneficial item"""
        items = [
            ("Flashlight", [CardEffect("vision_bonus", "self", 2, description="See further in dark areas")]),
            ("First Aid Kit", [CardEffect("heal_disorder", "self", -2, description="Reduce Disorder by 2")]),
            ("Master Key", [CardEffect("unlock_doors", "self", description="Can open locked doors")]),
            ("Escape Rope", [CardEffect("emergency_escape", "self", description="Instantly move to adjacent floor")]),
            ("Calming Pills", [CardEffect("disorder_immunity", "self", 3, description="Immune to disorder for 3 turns")]),
            ("Map Fragment", [CardEffect("reveal_zones", "board", 2, description="Reveal 2 random zone names")]),
            ("Emergency Radio", [CardEffect("communicate", "all_players", description="Share information with all players")]),
            ("Lockpicks", [CardEffect("bypass_locks", "self", description="Ignore locked door restrictions")]),
            ("Holy Water", [CardEffect("purify_anomaly", "board", description="Purify one Anomaly source")]),
            ("Research Notes", [CardEffect("experiment_report", "self", 1, description="Gain 1 Experiment Report")]),
            ("Night Vision Goggles", [CardEffect("see_in_dark", "self", description="Ignore darkness effects")]),
            ("Crowbar", [CardEffect("force_doors", "self", description="Force open emergency doors")])
        ]
        
        name, effects = random.choice(items)
        return name, effects

class EventCard(EffectCard):
    """Event cards - immediate effects that can be good or bad"""
    
    def __init__(self, **kwargs):
        super().__init__(effect_type=EffectCardType.EVENT, **kwargs)
        
        if not self.name:
            self.name, self.effects = self._generate_random_event()
    
    def _generate_random_event(self) -> tuple[str, List[CardEffect]]:
        """Generate a random event"""
        events = [
            ("Power Surge", [CardEffect("elevator_malfunction", "board", description="All elevators malfunction this turn")]),
            ("Strange Noise", [CardEffect("disorder_increase", "all_players", 1, description="All players gain 1 Disorder")]),
            ("Lucky Find", [CardEffect("gain_item", "self", description="Draw an additional item card")]),
            ("Building Shift", [CardEffect("rotate_tiles", "board", description="Randomly rotate 2 tiles")]),
            ("Emergency Broadcast", [CardEffect("reveal_exit", "board", description="Reveal escape exit location")]),
            ("Structural Damage", [CardEffect("corrupt_tiles", "board", 1, description="1 random tile becomes corrupted")]),
            ("Team Spirit", [CardEffect("heal_all", "all_players", -1, description="All players reduce Disorder by 1")]),
            ("False Alarm", [CardEffect("no_effect", "game", description="Nothing happens")]),
            ("Security Breach", [CardEffect("unlock_all", "board", description="All locked doors open")]),
            ("Psychological Pressure", [CardEffect("disorder_test", "self", description="Roll D6: 1-3 gain 2 Disorder")])
        ]
        
        name, effects = random.choice(events)
        return name, effects

class AnomalyCard(EffectCard):
    """Anomaly cards - usually detrimental effects"""
    
    def __init__(self, **kwargs):
        super().__init__(effect_type=EffectCardType.ANOMALY, **kwargs)
        self.is_permanent = True  # Anomalies persist until purified
        
        if not self.name:
            self.name, self.effects = self._generate_random_anomaly()
    
    def _generate_random_anomaly(self) -> tuple[str, List[CardEffect]]:
        """Generate a random detrimental anomaly"""
        anomalies = [
            ("Temporal Distortion", [CardEffect("time_loop", "game", description="Repeat last turn for all players")]),
            ("Gravity Anomaly", [CardEffect("forced_fall", "all_players", description="All players with Disorder ≥ 4 must Fall")]),
            ("Shadow Infestation", [CardEffect("darkness", "board", 5, description="All tiles become dark for 5 turns")]),
            ("Memory Loss", [CardEffect("forget_cards", "all_players", 2, description="All players discard 2 cards")]),
            ("Corruption Spread", [CardEffect("accelerate_corruption", "board", description="Double corruption spread rate")]),
            ("Phantom Walls", [CardEffect("block_passages", "board", 3, description="Random passages blocked for 3 turns")]),
            ("Disorder Amplification", [CardEffect("double_disorder", "all_players", 3, description="Double all Disorder gains for 3 turns")]),
            ("Reality Fracture", [CardEffect("shuffle_zones", "board", description="Reshuffle all zone name cards")]),
            ("Nightmare Vision", [CardEffect("hallucination", "all_players", description="Players see false tile layouts")]),
            ("Chaos Field", [CardEffect("random_teleport", "all_players", description="Randomly teleport all players")])
        ]
        
        name, effects = random.choice(anomalies)
        return name, effects
    
    def can_be_purified(self, items: List[str]) -> bool:
        """Check if anomaly can be purified with given items"""
        # Example purification requirements
        purification_items = {
            "Temporal Distortion": ["Holy Water", "Research Notes"],
            "Gravity Anomaly": ["Emergency Rope", "First Aid Kit"],
            "Shadow Infestation": ["Flashlight", "Night Vision Goggles"],
            # Add more as needed
        }
        
        required = purification_items.get(self.name, ["Holy Water"])  # Default requirement
        return any(item in items for item in required)

# =============================================================================
# BUTTON CARDS (Elevator Controls)
# =============================================================================

class ButtonCard(BaseCard):
    """Button cards for elevator operation"""
    
    def __init__(self, available_floors: List[int] = None, 
                 available_zones: List[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.available_floors = available_floors or [1, 2, 3, 4, 5]
        self.available_zones = available_zones or random.sample(ZONES, random.randint(2, 4))
        
        if not self.name:
            self.name = f"Elevator Button {self.card_id[:4].upper()}"
        
        if not self.description:
            floors_str = ", ".join(map(str, self.available_floors))
            zones_str = ", ".join(self.available_zones)
            self.description = f"Access floors: {floors_str}. Zones: {zones_str}"
    
    def get_card_type(self) -> CardType:
        return CardType.BUTTON
    
    def can_access_floor(self, floor: int) -> bool:
        """Check if this button allows access to a floor"""
        return floor in self.available_floors
    
    def can_access_zone(self, zone: str) -> bool:
        """Check if this button allows access to a zone"""
        return zone in self.available_zones
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_id": self.card_id,
            "name": self.name,
            "description": self.description,
            "type": "button",
            "available_floors": self.available_floors,
            "available_zones": self.available_zones
        }

# =============================================================================
# ZONE NAME CARDS
# =============================================================================

class ZoneNameCard(BaseCard):
    """Zone name cards for building layout"""
    
    def __init__(self, zone_letter: str, zone_name: str = None, **kwargs):
        super().__init__(**kwargs)
        self.zone_letter = zone_letter
        self.zone_name = zone_name or random.choice(ZONE_NAME_CARDS)
        self.is_revealed = False
        
        self.name = f"Zone {zone_letter}"
        self.description = f"Zone {zone_letter}: {self.zone_name if self.is_revealed else '???'}"
    
    def get_card_type(self) -> CardType:
        return CardType.ZONE_NAME
    
    def reveal(self) -> str:
        """Reveal the zone name"""
        self.is_revealed = True
        self.description = f"Zone {self.zone_letter}: {self.zone_name}"
        return self.zone_name
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_id": self.card_id,
            "name": self.name,
            "description": self.description,
            "type": "zone_name",
            "zone_letter": self.zone_letter,
            "zone_name": self.zone_name if self.is_revealed else None,
            "is_revealed": self.is_revealed
        }

# =============================================================================
# DECK MANAGEMENT
# =============================================================================

class Deck:
    """Manages a deck of cards with shuffling and drawing"""
    
    def __init__(self, deck_type: CardType, cards: List[BaseCard] = None):
        self.deck_type = deck_type
        self.cards = cards or []
        self.discarded = []
        self.drawn_count = 0
    
    def shuffle(self) -> None:
        """Shuffle the deck"""
        random.shuffle(self.cards)
    
    def draw(self) -> Optional[BaseCard]:
        """Draw a card from the top of the deck"""
        if not self.cards:
            if self.discarded:
                # Reshuffle discarded cards
                self.cards = self.discarded.copy()
                self.discarded.clear()
                self.shuffle()
            else:
                return None
        
        if self.cards:
            card = self.cards.pop(0)
            self.drawn_count += 1
            return card
        
        return None
    
    def discard(self, card: BaseCard) -> None:
        """Add card to discard pile"""
        self.discarded.append(card)
    
    def add_card(self, card: BaseCard) -> None:
        """Add card to deck"""
        self.cards.append(card)
    
    def peek(self, count: int = 1) -> List[BaseCard]:
        """Peek at top cards without drawing"""
        return self.cards[:count]
    
    def cards_remaining(self) -> int:
        """Get number of cards remaining"""
        return len(self.cards)
    
    def total_cards(self) -> int:
        """Get total cards in deck + discard"""
        return len(self.cards) + len(self.discarded)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "deck_type": self.deck_type.value,
            "cards_remaining": self.cards_remaining(),
            "discarded_count": len(self.discarded),
            "total_drawn": self.drawn_count,
            "total_cards": self.total_cards()
        }

def create_starting_decks() -> Dict[CardType, Deck]:
    """Create all starting decks with appropriate card distributions"""
    decks = {}
    
    # Path Tile Deck
    path_cards = []
    # Basic tiles (majority)
    for _ in range(35):
        path_cards.append(PathTileCard(PathTileType.BASIC))
    # Disordered tiles
    for _ in range(10):
        path_cards.append(PathTileCard(PathTileType.DISORDERED))
    # Special tiles
    for _ in range(8):
        path_cards.append(PathTileCard(PathTileType.STAIRWELL))
    for _ in range(5):
        path_cards.append(PathTileCard(PathTileType.ELEVATOR))
    for _ in range(2):
        path_cards.append(PathTileCard(PathTileType.ROTATING))
    
    decks[CardType.PATH_TILE] = Deck(CardType.PATH_TILE, path_cards)
    
    # Effect Card Deck (mixed)
    effect_cards = []
    # Items (beneficial)
    for _ in range(25):
        effect_cards.append(ItemCard())
    # Events (mixed)
    for _ in range(35):
        effect_cards.append(EventCard())
    # Anomalies (detrimental)
    for _ in range(20):
        effect_cards.append(AnomalyCard())
    
    decks[CardType.EFFECT] = Deck(CardType.EFFECT, effect_cards)
    
    # Button Cards
    button_cards = []
    for _ in range(DECK_SIZES[CardType.BUTTON]):
        button_cards.append(ButtonCard())
    
    decks[CardType.BUTTON] = Deck(CardType.BUTTON, button_cards)
    
    # Zone Name Cards
    zone_cards = []
    for zone in ZONES:
        zone_cards.append(ZoneNameCard(zone))
    
    decks[CardType.ZONE_NAME] = Deck(CardType.ZONE_NAME, zone_cards)
    
    # Shuffle all decks
    for deck in decks.values():
        deck.shuffle()
    
    return decks