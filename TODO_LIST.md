# NMB Game Implementation TODO List

## Backend Foundation
- [x] **backend_setup**: Set up Flask backend server with Flask-SocketIO for real-time communication
- [x] **project_structure**: Create complete directory structure for both server/ and client/ directories  
- [x] **backend_config**: Implement config.py and requirements.txt with all necessary Python dependencies
- [x] **game_constants**: Create constants.py with all game constants (max players, initial stats, floor limits, etc.)

## Core Game Logic
- [x] **player_class**: Implement Player class with Disorder value, floor tracking, position, and item/effect slots
- [x] **board_system**: Create Board class to manage multi-floor 3D map, path tiles, zones, and special locations
- [x] **card_system**: Implement card classes (Path tiles, Effect cards, Item cards, Anomaly cards, Button cards, Zone Name cards)
- [ ] **core_game_engine**: Build Game class with turn management, game phases, victory conditions, and state validation
- [ ] **game_actions**: Implement core game actions (Explore, Fall, Move, Meet, Rob, use stairs/elevators)

## Multiplayer Infrastructure
- [x] **game_manager**: Create GameManager to handle multiple concurrent game sessions and player routing
- [x] **websocket_routes**: Implement SocketIO event handlers (create_game, join_game, player_action, game_state_update)

## Frontend (React + Vite)
- [ ] **frontend_setup**: Set up React + Vite frontend with proper package.json and project structure
- [ ] **socket_service**: Create socketService.js to manage WebSocket connection and event handling
- [ ] **state_management**: Implement Zustand store (gameStore.js) for global game state management
- [ ] **game_board_ui**: Build GameBoard.jsx component to render 3D multi-floor board with tiles and player pawns
- [ ] **player_ui_components**: Create PlayerDashboard.jsx, PlayerHand.jsx, and Card.jsx components
- [ ] **navigation_pages**: Implement MainMenu.jsx, Lobby.jsx, and GamePage.jsx for app navigation

## Game Features
- [ ] **game_mechanics_ui**: Add UI for dice rolling, disorder tracking, floor navigation, and special actions
- [ ] **real_time_sync**: Ensure proper real-time synchronization of game state across all connected players
- [ ] **game_phases**: Implement the three game phases with escalating difficulty and map changes
- [ ] **victory_conditions**: Implement all victory/defeat conditions (escape items, experiment reports, corruption limit)

## Polish & Deployment
- [ ] **styling_assets**: Add CSS styling and game assets (tile images, card artwork, player tokens)
- [ ] **error_handling**: Implement comprehensive error handling and validation for invalid actions
- [ ] **testing_integration**: Add unit tests for game logic and integration tests for multiplayer functionality
- [ ] **deployment_prep**: Prepare deployment configuration and consider Redis integration for scaling

## Progress Tracking
- **In Progress**: None
- **Completed**: backend_setup, project_structure, backend_config, game_constants, player_class, board_system, card_system, game_manager, websocket_routes
- **Blocked**: None

## Latest Updates
- ✅ **Core Game Logic Complete**: All fundamental classes implemented (Player, Board, Cards)
- ✅ **Full Backend Infrastructure**: Server, WebSockets, session management
- ✅ **Comprehensive Card System**: All card types with effects and deck management
- 🧪 **Ready for Testing**: Core logic test suite created - run `python server/test_game_logic.py`
- 📋 **Next Phase**: Game engine and actions, then frontend development