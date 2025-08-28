# Full Stack Game Architecture for "NMB Game"

This document outlines a proposed full-stack architecture for developing a web-based version of the "NMB Game". The architecture is designed to be modular, scalable, and provide a real-time, interactive experience for players.

## 1. High-Level Overview

The architecture is composed of two main parts:

1.  **Backend (Server-side):** A Python-based server responsible for managing the core game logic, player states, and real-time communication.
2.  **Frontend (Client-side):** A modern JavaScript framework-based application that renders the game board and user interface, capturing player input and communicating with the backend.

Communication between the frontend and backend will be handled primarily through **WebSockets** to ensure low-latency, real-time updates for all players in a game session.

---

## 2. Backend Architecture (Python)

The backend will handle all the authoritative game state and logic.

*   **Framework:** **Flask** with the **Flask-SocketIO** extension.
    *   **Why Flask?** It's a lightweight and flexible framework, making it ideal for building a custom game server and API without unnecessary overhead.
    *   **Why Flask-SocketIO?** It provides seamless WebSocket integration, which is essential for broadcasting game state changes to all connected clients in real time.

*   **Directory Structure (`/server`):**

    ```
    server/
    |-- run.py              # Main entry point to start the Flask server
    |-- config.py           # Configuration (e.g., secret keys, environment settings)
    |-- requirements.txt    # Python dependencies
    |
    |-- api/
    |   |-- __init__.py
    |   |-- routes.py       # Defines SocketIO event handlers (e.g., 'create_game', 'player_action')
    |   |-- game_manager.py # Manages active game sessions (creating, finding, storing games)
    |
    |-- game_logic/
        |-- __init__.py
        |-- game.py         # Core Game class, manages game loop, phases, and state
        |-- player.py       # Player class (Disorder, hand, position, etc.)
        |-- board.py        # Board class (manages tiles, floors, zones)
        |-- cards.py        # Classes for all card types (Path, Effect, Item, Anomaly)
        |-- actions.py      # Functions for specific game actions (Explore, Fall, etc.)
        |-- constants.py    # Game constants (max players, initial stats)
    ```

*   **Key Components:**
    *   `game_manager.py`: A singleton or global object that holds a dictionary of all active game instances, indexed by a unique `game_id`. It handles creating new games and routing player actions to the correct game instance.
    *   `game.py`: The "engine" of the game. An instance of this class represents a single game session. It will contain the main game loop (`next_turn()`), manage the board, decks, and players, and validate player actions.
    *   `routes.py`: This is the communication layer. It defines listeners for WebSocket events from clients. When a player sends an action (e.g., `'move'`), the handler in this file will call the appropriate method on the correct `Game` instance and then broadcast the updated game state to all players in that game's "room".

*   **Communication (SocketIO Events):**
    *   **Client to Server:**
        *   `create_game(player_name)`: Asks the server to create a new game.
        *   `join_game(game_id, player_name)`: Asks to join an existing game.
        *   `player_action(game_id, action_data)`: A player performs an action (e.g., `{ "type": "MOVE", "path": [...] }`).
    *   **Server to Client:**
        *   `game_state_update(game_state_json)`: The server broadcasts the entire updated game state to all players in a game room whenever any action occurs. This keeps all clients perfectly in sync.
        *   `error(message)`: Sent to a specific player if they attempt an invalid action.

---

## 3. Frontend Architecture (React)

The frontend is responsible for rendering the game state received from the server and providing an intuitive interface for players to interact with.

*   **Framework:** **React** with **Vite** as a build tool.
    *   **Why React?** Its component-based architecture is perfect for building a complex UI like a game board. The large ecosystem provides excellent libraries for state management and effects.
    *   **Why Vite?** It provides a much faster and more modern development experience than traditional setups like Create React App.

*   **Directory Structure (`/client`):**

    ```
    client/
    |-- index.html          # Main HTML file
    |-- package.json        # Node.js dependencies (React, etc.)
    |
    |-- src/
        |-- main.jsx        # App entry point
        |-- App.jsx         # Main component, handles routing and layout
        |
        |-- components/     # Reusable UI components
        |   |-- GameBoard.jsx
        |   |-- PlayerDashboard.jsx
        |   |-- Card.jsx
        |   |-- PlayerHand.jsx
        |   |-- GameLog.jsx
        |
        |-- pages/          # Top-level page components
        |   |-- MainMenu.jsx
        |   |-- Lobby.jsx
        |   |-- GamePage.jsx
        |
        |-- state/          # Global state management
        |   |-- gameStore.js # Zustand or Redux Toolkit store for game state
        |
        |-- services/
        |   |-- socketService.js # Manages WebSocket connection and event handling
        |
        |-- assets/         # Images, fonts, etc.
        |-- styles/         # CSS files or modules
    ```

*   **Key Components:**
    *   `socketService.js`: A crucial module that establishes and maintains the WebSocket connection using the `socket.io-client` library. It will listen for the `game_state_update` event from the server and update the global state store. It also provides functions that components can call to send actions to the server (e.g., `socketService.sendAction(...)`).
    *   `gameStore.js`: A global state store (using **Zustand** for simplicity and performance). This store will hold the entire game state object received from the server. React components will subscribe to this store, and they will automatically re-render whenever the state changes.
    *   `GameBoard.jsx`: A complex component that takes the board layout from the `gameStore` and renders it. It will handle logic for displaying tiles, player pawns, and highlighting valid moves.
    *   `GamePage.jsx`: The main container for the game screen, which combines the `GameBoard`, `PlayerDashboard`, `PlayerHand`, and other UI elements. It orchestrates the flow of data from the store to the various display components.

---

## 4. Database & State

*   **Initial Phase:** The `game_manager` on the backend can store all active game states in memory (e.g., in a Python dictionary). This is simple and fast, and perfectly suitable for development and small-scale deployment.
*   **Scaling Up (Optional):** If the game needs to support a large number of concurrent sessions or persist games across server restarts, a fast in-memory database like **Redis** could be integrated. The `game_manager` would then save and retrieve game state objects from Redis instead of a local dictionary.