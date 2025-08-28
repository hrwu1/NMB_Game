# Game Logic Summary

This document outlines the core game logic for "NMB Game", a cooperative horror-themed board game.

## 1. Objective

The primary goal is for players to escape the ever-changing "New Main Building". This can be achieved through several means:

*   **Regular Victory:** Be the first player to collect 3 specific escape items and reach the designated escape exit on the top floor.
*   **Special Victory:** Uncover the building's secrets by collecting 7 "Experiment Report" pages or by purifying all "Anomaly" sources using specific item combinations.
*   **Shared Victory:** Players on the same path tile can share hand cards and escape together.
*   **Collective Failure:** All players lose if 70% of the map becomes "corroded" before anyone escapes.

## 2. Game Components

*   **"Memory Blueprint" Game Board:** A multi-story, 3D map representing the building. Players lay path tiles on this board.
*   **Player Status Monitor:** A personal board for each player to track:
    *   **Disorder Value (迷乱值):** A key stat representing the player's sanity. Starts at 0.
    *   **Current Floor:** The player's current floor level. Starts at 2.
    *   **Location:** The player's position on the map grid.
    *   **Item & Effect Slots:** For holding item and persistent effect cards.
*   **Path Tiles:** 4x4 grid tiles that form the playable map.
    *   **Basic Tiles:** Standard paths.
    *   **Disordered Tiles:** Introduced by "Anomaly" effects; placing them increases the player's Disorder.
    *   **Special Tiles:** Including temporary "Construction" tiles and "Rotating" tiles.
*   **Effect Cards:** A single deck containing:
    *   **Special Item Cards:** Generally beneficial items.
    *   **Event Cards:** Immediate effects that can be good or bad.
    *   **"Anomaly" Cards:** Usually detrimental effects impacting all players or the game state.
*   **Other Components:** Button Cards (for elevators), Zone Name Cards, Dice (D4, D6, D8, D12).

## 3. Game Setup

1.  Player order is determined by a D12 roll.
2.  Each player receives a Status Monitor, sets Disorder to 0 and Floor to 2.
3.  An "Initial Path Tile" is placed on the 2nd-floor platform of the game board.
4.  Players place their pawns on the initial tile.
5.  A deck of basic Path Tiles is created.
6.  All Effect Cards are shuffled into a single deck.

## 4. Gameplay Flow (Player's Turn)

On their turn, a player performs the following actions in order:

1.  **Movement Roll:** Roll a D6 to determine movement points.
2.  **Move:** Move the player pawn along the connected path tiles.
3.  **Path End Action:** If the player's movement path ends before using all movement points:
    *   If **Disorder is less than 6**, perform an **Explore** action: draw a new Path Tile and place it adjacent to the current tile to extend the path. Then, complete the move.
    *   If **Disorder is 6 or more**, a **Fall** occurs: the player's floor level decreases by 1, Disorder decreases by 1, and a new Path Tile is drawn and placed on the floor below the player.
4.  **Tile Effects:**
    *   **Passing through special squares** (Stairwell, Elevator Room, Event Square) triggers their effects.
    *   **Ending movement on special squares** (Emergency Door, Item Square) triggers their effects.
5.  **Player Interaction:** When passing another player, a player can choose to:
    *   **Meet (会合):** If Disorder values are close, players can trade cards and reduce their Disorder.
    *   **Rob (抢夺):** Steal a card from the other player, increasing their Disorder.

## 5. Core Mechanics

### Disorder Value (迷乱值)

*   This is a measure of a player's sanity. It is increased by game effects, like placing Disordered Path Tiles or triggering certain cards.
*   A player's Disorder level affects game events, skill checks, and victory conditions.
*   At high Disorder levels, players can traverse normally impassable "wall" squares. However, a high Disorder level also prevents them from performing the "Explore" action, forcing a "Fall".

### Multi-Floor Navigation

*   **Stairwells (楼梯间):** Allow moving up or down one floor. The stairwell tile is removed from the board after use.
*   **Elevator Rooms (电梯间):** Allow movement between non-adjacent floors and across different building zones. To use an elevator, a player draws a "Button Card" which dictates the available floors/zones. Elevators are permanent "anchor" tiles.

### Zones & Zone Names

*   The building is divided into zones (A-H). When a player first enters a zone, a random "Zone Name Card" is placed face-down for that zone.
*   Certain effects allow players to peek at a zone's name. If a duplicate zone name is revealed, all placed Zone Name Cards are reshuffled, changing the layout.
*   Zone names are critical for locating the escape route in the final phase of the game.

## 6. Game Phases

The game progresses through three distinct phases based on the number of rounds/actions taken:

1.  **Phase 1: Exploration:** The initial phase where players explore the map and acquire basic items.
2.  **Phase 2: Mutation:** The building becomes more dangerous. Elevators may malfunction, Anomaly events become more frequent, and the map begins to be covered by an impassable "blood-colored蔓延".
3.  **Phase 3: End Game:** The map begins to collapse. An escape exit appears randomly on the top floor. Players must have collected the required escape items to win.