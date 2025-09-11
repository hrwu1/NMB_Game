// Game state variables
let socket = null;
let gameState = null;
let currentGameId = null;
// Note: We track current player through socket.id directly, not this variable
// let currentPlayerId = null; // Removed - using socket.id directly instead
let selectedFloor = 2;
let gameConfig = null; // Store game configuration from server

// Initialize the game
async function initGame() {
    try {
        // Fetch game configuration first
        await loadGameConfig();
        connectToServer();
    } catch (error) {
        console.error('Failed to load game configuration:', error);
        addLog('Failed to load game configuration. Using defaults.', 'warning');
        // Use fallback config
        gameConfig = {
            board: {
                size: [5, 5],
                grid_size: 20,
                tile_size: 4
            }
        };
        connectToServer();
    }
}

// Load game configuration from server
async function loadGameConfig() {
    try {
        console.log('Attempting to fetch game configuration from server...');
        
        const response = await fetch('http://localhost:5000/api/config');
        
        console.log('Response received:', response.status, response.statusText);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        gameConfig = await response.json();
        console.log('Game configuration loaded successfully:', gameConfig);
        
        // Validate configuration structure
        if (!gameConfig.board || !gameConfig.board.size) {
            throw new Error('Invalid configuration structure received');
        }
        
        // Set CSS custom properties for dynamic grid sizing
        const root = document.documentElement;
        const gridSize = gameConfig.board.grid_size;
        root.style.setProperty('--board-grid-size', gridSize);
        root.style.setProperty('--tile-size', '24px');
        
        addLog(`Configuration loaded: ${gameConfig.board.size[0]}x${gameConfig.board.size[1]} board`, 'system');
        
    } catch (error) {
        console.error('Detailed error loading game config:', error);
        console.error('Error name:', error.name);
        console.error('Error message:', error.message);
        throw error;
    }
}

// Socket connection management
function connectToServer() {
    socket = io('http://localhost:5000');
    
    socket.on('connect', function() {
        updateConnectionStatus(true);
        addLog('Connected to NMB Game server', 'system');
    });
    
    socket.on('disconnect', function() {
        updateConnectionStatus(false);
        addLog('Disconnected from server', 'error');
    });
    
    // Game event handlers
    socket.on('connected', function(data) {
        addLog(data.message, 'system');
    });
    
    socket.on('game_created', function(data) {
        addLog(`Game created: ${data.game_id}`, 'action');
        currentGameId = data.game_id;
        document.getElementById('gameId').value = data.game_id;
        document.getElementById('startGameBtn').style.display = 'block';
        updateGameControls('host');
        showLobbyStatus(data.game_id, 1, 4, true, data.auto_start_enabled);
    });
    
    socket.on('game_joined', function(data) {
        addLog(`Joined game: ${data.game_id}`, 'action');
        currentGameId = data.game_id;
        updateGameControls('player');
        showLobbyStatus(data.game_id, data.player_count, data.max_players, false, data.auto_start_enabled);
    });
    
    socket.on('player_joined', function(data) {
        addLog(data.message, 'system');
        updateLobbyPlayerCount(data.player_count, data.max_players, data.auto_start_enabled);
    });
    
    socket.on('game_started', function(data) {
        const message = data.auto_started ? 'Game auto-started!' : 'Game started!';
        addLog(message, 'action');
        gameState = data.game_state;
        document.getElementById('startGameBtn').style.display = 'none';
        hideLobbyStatus(); // Hide lobby status when game starts
        updateGameDisplay();
        updateActionButtons();
    });
    
    socket.on('game_state_update', function(data) {
        const oldState = gameState ? gameState.state : null;
        gameState = data.game_state;
        
        if (data.action_result) {
            addLog(`Action: ${JSON.stringify(data.action_result)}`, 'action');
        }
        
        // Check for state transitions
        if (oldState === 'pawn_placement' && gameState.state === 'playing') {
            addLog('🎮 All pawns placed! Normal gameplay begins!', 'success');
            showToast('All pawns placed! Game started!', 'success');
        }
        
        // Hide start button if game moves beyond waiting state
        if (gameState.state !== 'waiting') {
            const startBtn = document.getElementById('startGameBtn');
            if (startBtn) {
                startBtn.style.display = 'none';
            }
        }
        
        updateGameDisplay();
        updateActionButtons();
    });
    
    // Enhanced dice roll event handler
    socket.on('dice_roll', function(data) {
        console.log('🎲 Dice roll event received:', data);
        
        if (data.purpose === 'player_order' && data.all_player_rolls) {
            // This is a player order determination roll
            showDiceRoll('d12', 'player_order', data.result, data.all_player_rolls);
            addLog(`🎯 Turn order determined! ${Object.values(data.all_player_rolls).map(p => `${p.name}(${p.roll})`).join(', ')}`, 'action');
        } else if (data.purpose === 'movement') {
            // This is a movement roll
            showDiceRoll('d6', 'movement', data.result);
            addLog(`🚶 ${data.player_name} rolled ${data.result} for movement`, 'action');
        } else {
            // Generic dice roll
            showDiceRoll(data.dice_type || 'd6', data.purpose || 'generic', data.result);
            addLog(`🎲 ${data.player_name || 'Someone'} rolled ${data.result}`, 'action');
        }
    });
    
    // Enhanced turn start event
    socket.on('turn_started', function(data) {
        addLog(`🎯 ${data.player_name}'s turn started`, 'action');
        
        if (data.movement_roll && data.player_id === socket.id) {
            // This player just started their turn and got a movement roll
            setTimeout(() => {
                showDiceRoll('d6', 'movement', data.movement_roll);
            }, 500); // Small delay to let other UI updates complete
        }
    });
    
    socket.on('action_result', function(data) {
        if (data.success) {
            addLog(`Action successful: ${data.message || 'Action completed'}`, 'action');
        } else {
            addLog(`Action failed: ${data.reason}`, 'error');
        }
    });
    
    socket.on('error', function(data) {
        const errorMessage = data.message || data.reason || 'Unknown server error';
        addLog(`Server Error: ${errorMessage}`, 'error');
        console.error('Socket error:', data);
    });
    
    // Enhanced connection event handlers
    socket.on('connect_error', function(error) {
        console.error('Connection error:', error);
        handleNetworkError(error);
    });
    
    socket.on('disconnect', function(reason) {
        console.log('Disconnected:', reason);
        updateConnectionStatus(false);
        addLog(`Disconnected: ${reason}`, 'warning');
        
        if (reason === 'io server disconnect') {
            // Server disconnected us, don't try to reconnect automatically
            addLog('Server disconnected the connection. Please refresh the page.', 'error');
        } else {
            // Client-side disconnect, try to reconnect
            addLog('Attempting to reconnect...', 'system');
        }
    });
    
    socket.on('reconnect', function(attemptNumber) {
        console.log('Reconnected after', attemptNumber, 'attempts');
        updateConnectionStatus(true);
        addLog(`Reconnected successfully!`, 'success');
        
        // Re-join game if we were in one
        if (currentGameId) {
            const playerName = document.getElementById('playerName').value.trim();
            if (playerName) {
                socket.emit('join_game', { game_id: currentGameId, player_name: playerName });
                addLog('Rejoining game...', 'system');
            }
        }
    });
    
    socket.on('reconnect_error', function(error) {
        console.error('Reconnection failed:', error);
        addLog('Failed to reconnect. Please refresh the page.', 'error');
    });
}

// UI Update functions
function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connection-status');
    if (connected) {
        statusElement.textContent = 'Connected ✅';
        statusElement.className = 'connection-status connected';
    } else {
        statusElement.textContent = 'Disconnected ❌';
        statusElement.className = 'connection-status disconnected';
    }
}

function updateGameControls(role) {
    const createBtn = document.getElementById('createGameBtn');
    const joinBtn = document.getElementById('joinGameBtn');
    const startBtn = document.getElementById('startGameBtn');
    
    createBtn.disabled = true;
    joinBtn.disabled = true;
    
    if (role === 'host') {
        startBtn.style.display = 'block';
    }
}

function updateGameDisplay() {
    if (!gameState) return;
    
    // Update game info
    document.getElementById('game-phase').textContent = gameState.phase;
    document.getElementById('game-round').textContent = gameState.round;
    
    // Find current player
    const currentPlayer = getCurrentPlayer();
    if (currentPlayer) {
        updatePlayerStatus(currentPlayer);
        updatePlayerHand(currentPlayer);
    }
    
    // Update board
    updateGameBoard();
}

function getCurrentPlayer() {
    if (!gameState || !gameState.players) return null;
    
    // Find the player that matches this client's socket ID
    return gameState.players[socket.id] || null;
}

function updatePlayerStatus(player) {
    document.getElementById('player-status').style.display = 'block';
    document.getElementById('player-name').textContent = player.name;
    document.getElementById('disorder-value').textContent = player.disorder;
    document.getElementById('floor-value').textContent = player.floor;
    
    // Display both tile and sub-position
    const pos = player.position;
    if (pos && pos.tile_x !== undefined) {
        document.getElementById('position-value').textContent = `T(${pos.tile_x},${pos.tile_y}) S(${pos.sub_x},${pos.sub_y})`;
    } else if (pos && Array.isArray(pos)) {
        // Legacy format
        document.getElementById('position-value').textContent = `(${pos[0]}, ${pos[1]})`;
    } else {
        // No position yet (game hasn't started)
        document.getElementById('position-value').textContent = 'Not positioned';
    }
    
    const movementUsed = player.movement_used || 0;
    const movementPoints = player.movement_points || 0;
    document.getElementById('movement-value').textContent = `${movementUsed}/${movementPoints}`;
    
    // Update disorder styling
    const disorderStat = document.querySelector('#disorder-value').parentElement;
    if (player.disorder >= 6) {
        disorderStat.classList.add('disorder-high');
    } else {
        disorderStat.classList.remove('disorder-high');
    }
    
    // Update turn indicator
    const isCurrentTurn = gameState.current_player === socket.id;
    const turnIndicator = document.getElementById('turn-indicator');
    turnIndicator.textContent = isCurrentTurn ? '🎯 Your Turn' : '⏳ Waiting';
}

function updateGameBoard() {
    const boardElement = document.getElementById('game-board');
    const currentFloorData = gameState?.board?.floors?.[selectedFloor];
    
    if (!currentFloorData) {
        boardElement.innerHTML = '<div class="board-message">No tiles on this floor</div>';
        return;
    }
    
    if (!gameConfig) {
        boardElement.innerHTML = '<div class="board-message">Loading board configuration...</div>';
        return;
    }
    
    // Use dynamic board configuration
    const gridSize = gameConfig.board.grid_size;
    const tileSize = gameConfig.board.tile_size;
    const boardSize = gameConfig.board.size;
    
    // Create board grid dynamically based on configuration
    const gridDiv = document.createElement('div');
    gridDiv.className = 'board-grid';
    
    // Create dynamic sub-position grid
    for (let abs_y = 0; abs_y < gridSize; abs_y++) {
        for (let abs_x = 0; abs_x < gridSize; abs_x++) {
            const subDiv = document.createElement('div');
            subDiv.className = 'board-tile';
            
            // Calculate which tile this sub-position belongs to
            const tile_x = Math.floor(abs_x / tileSize);
            const tile_y = Math.floor(abs_y / tileSize);
            const sub_x = abs_x % tileSize;
            const sub_y = abs_y % tileSize;
            
            subDiv.dataset.tileX = tile_x;
            subDiv.dataset.tileY = tile_y;
            subDiv.dataset.subX = sub_x;
            subDiv.dataset.subY = sub_y;
            subDiv.dataset.absX = abs_x;
            subDiv.dataset.absY = abs_y;
            
            // Add tile boundary styling for edges
            if (sub_x === 0 || sub_x === 3 || sub_y === 0 || sub_y === 3) {
                subDiv.classList.add('tile-boundary');
            }
            
            // Check if there's a tile at this position
            const tileKey = `${tile_x},${tile_y}`;
            const tileData = currentFloorData[tileKey];
            
            if (tileData) {
                // Check if this sub-position is movable
                const isMovable = tileData.movable_positions?.some(pos => 
                    pos.x === sub_x && pos.y === sub_y);
                
                if (isMovable) {
                    // Add tile styling based on type
                    subDiv.classList.add(`tile-${tileData.tile_type}`);
                    
                    // Add special styling during pawn placement phase
                    if (gameState && gameState.state === 'pawn_placement' && 
                        gameState.current_player === socket.id) {
                        // Highlight clickable positions on the starting tile
                        if (tile_x === 2 && tile_y === 2 && selectedFloor === 2) {
                            subDiv.classList.add('pawn-placement-available');
                        }
                    }
                } else {
                    // Non-movable position (wall/blocked)
                    subDiv.classList.add('tile-wall');
                }
                
                if (tileData.is_corrupted) {
                    subDiv.classList.add('tile-corrupted');
                }
                
                // Add players on this sub-position
                const playersOnSubPos = getPlayersOnSubPosition(tile_x, tile_y, sub_x, sub_y, selectedFloor);
                playersOnSubPos.forEach((player) => {
                    const pawnDiv = document.createElement('div');
                    // Use stable player number instead of array index
                    const playerNumber = player.player_number || 1;
                    pawnDiv.className = `player-pawn player-${playerNumber}`;
                    pawnDiv.textContent = player.name.charAt(0);
                    pawnDiv.title = `${player.name} (Player ${playerNumber})`;
                    subDiv.appendChild(pawnDiv);
                });
                
                // Add click handler for both movement and pawn placement
                if (isMovable) {
                    subDiv.addEventListener('click', () => handleSubPositionClick(tile_x, tile_y, sub_x, sub_y));
                }
            }
            
            gridDiv.appendChild(subDiv);
        }
    }
    
    boardElement.innerHTML = '';
    boardElement.appendChild(gridDiv);
}

function getPlayersOnSubPosition(tile_x, tile_y, sub_x, sub_y, floor) {
    if (!gameState?.players) return [];
    
    return Object.values(gameState.players).filter(player => {
        const pos = player.position;
        // Check if player has a position (game has started) and position matches
        return pos && 
               pos.tile_x === tile_x && 
               pos.tile_y === tile_y &&
               pos.sub_x === sub_x &&
               pos.sub_y === sub_y &&
               player.floor === floor;
    });
}

function updateActionButtons() {
    const actionsDiv = document.getElementById('action-buttons');
    
    if (!gameState) {
        actionsDiv.innerHTML = '<p style="color: #888; text-align: center;">Game not started</p>';
        return;
    }
    
    // Handle pawn placement phase
    if (gameState.state === 'pawn_placement') {
        const isMyTurn = gameState.current_player === socket.id;
        const currentPlayer = getCurrentPlayer();
        const pawnPlacement = gameState.pawn_placement || {};
        
        if (!isMyTurn) {
            actionsDiv.innerHTML = `
                <div class="pawn-placement-info">
                    <h4>🎯 Pawn Placement Phase</h4>
                    <p>Players placed: ${pawnPlacement.players_placed?.length || 0}/${pawnPlacement.total_players || 0}</p>
                    <p style="color: #888; text-align: center;">Wait for your turn</p>
                </div>
            `;
            return;
        }
        
        // Check if current player has already placed their pawn
        const hasPlaced = pawnPlacement.players_placed?.includes(socket.id);
        
        if (hasPlaced) {
            actionsDiv.innerHTML = `
                <div class="pawn-placement-info">
                    <h4>🎯 Pawn Placement Phase</h4>
                    <p>Players placed: ${pawnPlacement.players_placed?.length || 0}/${pawnPlacement.total_players || 0}</p>
                    <p style="color: #4CAF50; text-align: center;">✅ Pawn placed! Waiting for others...</p>
                </div>
            `;
            return;
        }
        
        // Player can place pawn
        actionsDiv.innerHTML = `
            <div class="pawn-placement-info">
                <h4>🎯 Pawn Placement Phase</h4>
                <p>Players placed: ${pawnPlacement.players_placed?.length || 0}/${pawnPlacement.total_players || 0}</p>
                <div class="placement-instructions">
                    <p style="color: #ff9800; margin-bottom: 10px;">🖱️ <strong>Click on the board to place your pawn!</strong></p>
                    <p style="color: #888; font-size: 0.9em; margin: 0;">Click on any green square on the starting tile</p>
                </div>
            </div>
        `;
        return;
    }
    
    // Normal gameplay phase
    if (gameState.state !== 'playing') {
        actionsDiv.innerHTML = '<p style="color: #888; text-align: center;">Game not started</p>';
        return;
    }
    
    const isMyTurn = gameState.current_player === socket.id;
    const currentPlayer = getCurrentPlayer();
    
    if (!isMyTurn) {
        actionsDiv.innerHTML = '<p style="color: #888; text-align: center;">Wait for your turn</p>';
        return;
    }
    
    // Generate action buttons based on current game state
    const actions = [];
    
    if (currentPlayer.movement_points > currentPlayer.movement_used) {
        actions.push({ 
            name: 'Move', 
            action: 'move', 
            class: 'primary',
            disabled: false 
        });
        
        if (currentPlayer.disorder < 6) {
            actions.push({ 
                name: 'Explore', 
                action: 'explore', 
                class: 'primary',
                disabled: false 
            });
        } else {
            actions.push({ 
                name: 'Fall', 
                action: 'fall', 
                class: 'danger',
                disabled: false 
            });
        }
    }
    
    actions.push({ 
        name: 'Pass', 
        action: 'pass', 
        class: '',
        disabled: false 
    });
    
    actions.push({ 
        name: 'End Turn', 
        action: 'end_turn', 
        class: 'danger',
        disabled: false 
    });
    
    // Render action buttons
    actionsDiv.innerHTML = actions.map(action => `
        <button class="action-btn ${action.class}" 
                onclick="performAction('${action.action}')" 
                ${action.disabled ? 'disabled' : ''}>
            ${action.name}
        </button>
    `).join('');
}

function updatePlayerHand(player) {
    const handDiv = document.getElementById('player-hand');
    const handCount = document.getElementById('hand-count');
    
    const cards = player.inventory?.hand || [];
    handCount.textContent = cards.length;
    
    if (cards.length === 0) {
        handDiv.innerHTML = '<p style="color: #888; text-align: center;">No cards</p>';
        return;
    }
    
    handDiv.innerHTML = cards.map(card => `
        <div class="card card-${card.effect_type || 'item'}" onclick="useCard('${card.card_id}')">
            <div class="card-name">${card.name}</div>
            <div class="card-description">${card.description || 'No description'}</div>
        </div>
    `).join('');
}

// Game action functions with enhanced validation
function createGame() {
    const playerName = document.getElementById('playerName').value.trim();
    
    // Validate player name
    const validation = validatePlayerName(playerName);
    if (!validation.valid) {
        addLog(validation.message, 'error');
        return;
    }
    
    // Check connection
    if (!socket || !socket.connected) {
        addLog('Not connected to server. Please wait for connection.', 'error');
        return;
    }
    
    // Disable button to prevent multiple clicks
    const createBtn = document.getElementById('createGameBtn');
    createBtn.disabled = true;
    createBtn.textContent = 'Creating...';
    
    socket.emit('create_game', { player_name: playerName });
    addLog(`Creating game for player: ${playerName}`, 'system');
    
    // Re-enable button after timeout
    setTimeout(() => {
        createBtn.disabled = false;
        createBtn.textContent = 'Create New Game';
    }, 3000);
}

function joinGame() {
    const playerName = document.getElementById('playerName').value.trim();
    const gameId = document.getElementById('gameId').value.trim().toUpperCase();
    
    // Validate player name
    const nameValidation = validatePlayerName(playerName);
    if (!nameValidation.valid) {
        addLog(nameValidation.message, 'error');
        return;
    }
    
    // Validate game ID
    const gameIdValidation = validateGameId(gameId);
    if (!gameIdValidation.valid) {
        addLog(gameIdValidation.message, 'error');
        return;
    }
    
    // Check connection
    if (!socket || !socket.connected) {
        addLog('Not connected to server. Please wait for connection.', 'error');
        return;
    }
    
    // Disable button to prevent multiple clicks
    const joinBtn = document.getElementById('joinGameBtn');
    joinBtn.disabled = true;
    joinBtn.textContent = 'Joining...';
    
    socket.emit('join_game', { game_id: gameId, player_name: playerName });
    addLog(`Joining game ${gameId} as ${playerName}`, 'system');
    
    // Re-enable button after timeout
    setTimeout(() => {
        joinBtn.disabled = false;
        joinBtn.textContent = 'Join Game';
    }, 3000);
}

function startGame() {
    if (!currentGameId) {
        addLog('No active game to start', 'error');
        return;
    }
    
    // Check if we have enough players (basic client-side check)
    const playerCountDisplay = document.getElementById('player-count-display');
    if (playerCountDisplay) {
        const text = playerCountDisplay.textContent;
        const playerCount = parseInt(text.split('/')[0]);
        
        if (playerCount < 2) {
            addLog('Cannot start game: Need at least 2 players to start', 'warning');
            showToast('Need at least 2 players to start the game', 'warning');
            return;
        }
    }
    
    socket.emit('start_game', { game_id: currentGameId });
    addLog('Starting game...', 'system');
    
    // Update lobby status to show starting state
    const lobbyStatusText = document.getElementById('lobby-status-text');
    if (lobbyStatusText) {
        lobbyStatusText.textContent = 'Starting game...';
        lobbyStatusText.className = 'status-starting';
    }
}

function performAction(actionType) {
    console.log(`🔍 DEBUG: performAction called with actionType: ${actionType}`);
    
    // Check connection first
    if (!socket || !socket.connected) {
        addLog('Not connected to server. Please reconnect.', 'error');
        return;
    }
    
    if (!currentGameId || !gameState) {
        addLog('No active game session', 'error');
        console.log('❌ DEBUG: No active game or game state');
        return;
    }
    
    console.log('✅ DEBUG: Game state exists, proceeding...');
    let actionData = {};
    
    // Handle different action types
    if (actionType === 'move') {
        // For now, just use current position + 1 as target (simplified)
        const currentPlayer = getCurrentPlayer();
        const pos = currentPlayer.position;
        
        if (pos.tile_x !== undefined) {
            // New position format - move within tile or to adjacent tile
            let newTileX = pos.tile_x;
            let newSubX = pos.sub_x + 1;
            
            // Handle movement across tile boundary
            if (newSubX > 3) {
                newTileX = Math.min(pos.tile_x + 1, gameConfig.board.size[0] - 1);
                newSubX = 0;
            }
            
            actionData.target_position = { 
                tile_x: newTileX,
                tile_y: pos.tile_y,
                sub_x: newSubX,
                sub_y: pos.sub_y,
                floor: pos.floor || currentPlayer.floor
            };
        } else {
            // Legacy format fallback
            const newX = Math.min(pos[0] + 1, gameConfig.board.size[0] - 1);  // Dynamic board range
            actionData.target_position = { 
                x: newX, 
                y: pos[1], 
                floor: currentPlayer.floor 
            };
        }
    } else if (actionType === 'explore') {
        // Let the backend determine the best placement position
        // Frontend just sends the explore action without specifying position
        // Backend will find the best adjacent position automatically
        // actionData is already {} so no need to reassign
    }
    
    // Validate action before sending
    const validation = validateAction(actionType, actionData);
    if (!validation.valid) {
        addLog(validation.message, 'warning');
        return;
    }
    
    console.log(`🔍 DEBUG: About to emit action - type: ${actionType}, data:`, actionData);
    
    // Disable action buttons temporarily to prevent spam
    const actionButtons = document.querySelectorAll('.action-btn');
    actionButtons.forEach(btn => {
        btn.disabled = true;
        btn.style.opacity = '0.6';
    });
    
    socket.emit('player_action', {
        action_type: actionType,
        action_data: actionData
    });
    
    console.log('✅ DEBUG: Action emitted successfully');
    addLog(`Performing action: ${actionType}`, 'action');
    
    // Re-enable action buttons after a short delay
    setTimeout(() => {
        actionButtons.forEach(btn => {
            btn.disabled = false;
            btn.style.opacity = '1';
        });
    }, 1000);
}

function handleSubPositionClick(tile_x, tile_y, sub_x, sub_y) {
    if (!gameState || gameState.current_player !== socket.id) {
        return;
    }
    
    const currentPlayer = getCurrentPlayer();
    
    // Handle pawn placement phase
    if (gameState.state === 'pawn_placement') {
        // Check if player has already placed their pawn
        const pawnPlacement = gameState.pawn_placement || {};
        const hasPlaced = pawnPlacement.players_placed?.includes(socket.id);
        
        if (hasPlaced) {
            addLog('You have already placed your pawn!', 'warning');
            return;
        }
        
        // Place pawn at clicked position
        const actionData = {
            target_position: { 
                tile_x: tile_x, 
                tile_y: tile_y,
                sub_x: sub_x,
                sub_y: sub_y,
                floor: selectedFloor 
            }
        };
        
        socket.emit('player_action', {
            action_type: 'place_pawn',
            action_data: actionData
        });
        
        addLog(`Placing pawn at tile (${tile_x},${tile_y}) sub-position (${sub_x},${sub_y})`, 'action');
        return;
    }
    
    // Handle normal gameplay movement
    if (gameState.state === 'playing') {
        // Check if this is a move action
        if (currentPlayer.movement_points > currentPlayer.movement_used) {
            const actionData = {
                target_position: { 
                    tile_x: tile_x, 
                    tile_y: tile_y,
                    sub_x: sub_x,
                    sub_y: sub_y,
                    floor: selectedFloor 
                }
            };
            
            socket.emit('player_action', {
                action_type: 'move',
                action_data: actionData
            });
            
            addLog(`Moving to tile (${tile_x},${tile_y}) sub-position (${sub_x},${sub_y})`, 'action');
        }
    }
}

function useCard(cardId) {
    if (!currentGameId || !gameState) {
        addLog('No active game', 'error');
        return;
    }
    
    socket.emit('player_action', {
        action_type: 'use_item',
        action_data: { item_id: cardId }
    });
    
    addLog(`Using card: ${cardId}`, 'action');
}

function changeFloor(direction) {
    const newFloor = selectedFloor + direction;
    if (newFloor >= 1 && newFloor <= 5) {
        selectedFloor = newFloor;
        document.getElementById('current-floor').textContent = `Floor ${selectedFloor}`;
        updateGameBoard();
    }
}

// Enhanced error handling and utility functions
function addLog(message, type = 'system') {
    const logDiv = document.getElementById('game-log');
    const timestamp = new Date().toLocaleTimeString();
    
    // Truncate extremely long messages to prevent layout issues
    let displayMessage = message;
    if (message.length > 500) {
        displayMessage = message.substring(0, 480) + '... (truncated)';
    }
    
    // Add appropriate icons for different log types
    const icons = {
        'info': 'ℹ️',
        'action': '⚡',
        'error': '❌',
        'system': '🔧',
        'success': '✅',
        'warning': '⚠️'
    };
    
    const icon = icons[type] || 'ℹ️';
    
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${type}`;
    
    // Escape HTML to prevent XSS and layout issues
    const escapedMessage = displayMessage
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    
    logEntry.innerHTML = `
        <div class="log-timestamp">${icon} ${timestamp}</div>
        <div class="log-message">${escapedMessage}</div>
    `;
    
    // Add title attribute for full message if truncated
    if (message.length > 500) {
        logEntry.title = message;
    }
    
    // Remove old entries if too many
    while (logDiv.children.length > 100) {
        logDiv.removeChild(logDiv.firstChild);
    }
    
    logDiv.appendChild(logEntry);
    logDiv.scrollTop = logDiv.scrollHeight;
    
    // Show toast notification for errors and important messages
    if (type === 'error' || type === 'warning') {
        showToast(message, type);
    }
}

// Toast notification system
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    // Truncate toast messages too
    let displayMessage = message;
    if (message.length > 200) {
        displayMessage = message.substring(0, 180) + '...';
    }
    
    toast.textContent = displayMessage;
    
    // Style the toast
    Object.assign(toast.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        padding: '12px 20px',
        borderRadius: '8px',
        color: 'white',
        fontWeight: 'bold',
        zIndex: '1000',
        transform: 'translateX(100%)',
        transition: 'transform 0.3s ease',
        maxWidth: '300px',
        minWidth: '200px',
        wordWrap: 'break-word',
        overflowWrap: 'break-word',
        wordBreak: 'break-word',
        boxSizing: 'border-box'
    });
    
    // Set background based on type
    const backgrounds = {
        'error': 'linear-gradient(135deg, #ef4444, #dc2626)',
        'warning': 'linear-gradient(135deg, #f59e0b, #d97706)',
        'success': 'linear-gradient(135deg, #10b981, #059669)',
        'info': 'linear-gradient(135deg, #3b82f6, #2563eb)'
    };
    
    toast.style.background = backgrounds[type] || backgrounds.info;
    toast.style.boxShadow = '0 8px 20px rgba(0, 0, 0, 0.3)';
    
    document.body.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
        toast.style.transform = 'translateX(0)';
    }, 100);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (toast.parentNode) {
                document.body.removeChild(toast);
            }
        }, 300);
    }, 5000);
}

// Enhanced input validation
function validatePlayerName(name) {
    if (!name || name.trim().length === 0) {
        return { valid: false, message: 'Player name cannot be empty' };
    }
    if (name.trim().length < 2) {
        return { valid: false, message: 'Player name must be at least 2 characters' };
    }
    if (name.trim().length > 20) {
        return { valid: false, message: 'Player name must be 20 characters or less' };
    }
    if (!/^[a-zA-Z0-9\s_-]+$/.test(name.trim())) {
        return { valid: false, message: 'Player name can only contain letters, numbers, spaces, hyphens, and underscores' };
    }
    return { valid: true, message: '' };
}

function validateGameId(gameId) {
    if (!gameId || gameId.trim().length === 0) {
        return { valid: false, message: 'Game ID cannot be empty' };
    }
    if (gameId.trim().length !== 6) {
        return { valid: false, message: 'Game ID must be exactly 6 characters' };
    }
    if (!/^[A-Z0-9]+$/.test(gameId.trim())) {
        return { valid: false, message: 'Game ID can only contain uppercase letters and numbers' };
    }
    return { valid: true, message: '' };
}

// Network error handling
function handleNetworkError(error) {
    console.error('Network error:', error);
    addLog('Connection lost. Attempting to reconnect...', 'error');
    showToast('Connection lost. Please check your internet connection.', 'error');
    
    // Update connection status
    const status = document.getElementById('connection-status');
    status.textContent = 'Reconnecting...';
    status.className = 'connection-status disconnected';
    
    // Try to reconnect after a delay
    setTimeout(() => {
        if (socket && !socket.connected) {
            socket.connect();
        }
    }, 2000);
}

// Action validation before sending to server
function validateAction(actionType, actionData) {
    if (!currentGameId || !gameState) {
        return { valid: false, message: 'No active game session' };
    }
    
    const currentPlayer = getCurrentPlayer();
    if (!currentPlayer) {
        return { valid: false, message: 'Player not found in game' };
    }
    
    // Check if it's the player's turn
    if (gameState.current_player !== socket.id) {
        return { valid: false, message: 'It is not your turn' };
    }
    
    // Validate specific actions
    switch (actionType) {
        case 'move':
            if (!actionData.target_position) {
                return { valid: false, message: 'Move action requires a target position' };
            }
            break;
            
        case 'explore':
            if (currentPlayer.movement_points <= 0) {
                return { valid: false, message: 'No movement points remaining' };
            }
            break;
            
        case 'meet':
        case 'rob':
            // Check if there are other players in the same position
            const samePositionPlayers = Object.values(gameState.players).filter(p => 
                p.id !== currentPlayer.id &&
                p.position.tile_x === currentPlayer.position.tile_x &&
                p.position.tile_y === currentPlayer.position.tile_y &&
                p.position.sub_x === currentPlayer.position.sub_x &&
                p.position.sub_y === currentPlayer.position.sub_y &&
                p.position.floor === currentPlayer.position.floor
            );
            
            if (samePositionPlayers.length === 0) {
                return { valid: false, message: `No other players at your position for ${actionType} action` };
            }
            break;
    }
    
    return { valid: true, message: '' };
}

// Test function for debugging configuration loading
window.testConfigEndpoint = async function() {
    console.log('=== Testing Configuration Endpoint ===');
    try {
        console.log('1. Attempting fetch...');
        const response = await fetch('http://localhost:5000/api/config');
        
        console.log('2. Response object:', response);
        console.log('3. Response status:', response.status);
        console.log('4. Response ok:', response.ok);
        console.log('5. Response headers:');
        for (let [key, value] of response.headers.entries()) {
            console.log(`   ${key}: ${value}`);
        }
        
        console.log('6. Getting response text...');
        const text = await response.text();
        console.log('7. Raw response text:', text);
        
        if (!text) {
            console.error('8. Empty response!');
            return null;
        }
        
        console.log('8. Parsing JSON...');
        const config = JSON.parse(text);
        console.log('9. Parsed configuration:', config);
        
        return config;
    } catch (error) {
        console.error('Test failed at step:', error.message);
        console.error('Full error:', error);
        return null;
    }
};

// Simple test without fetch API
window.testConfigSimple = function() {
    console.log('=== Simple XMLHttpRequest Test ===');
    
    const xhr = new XMLHttpRequest();
    xhr.open('GET', 'http://localhost:5000/api/config', true);
    
    xhr.onreadystatechange = function() {
        console.log('ReadyState:', xhr.readyState, 'Status:', xhr.status);
        
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                console.log('Success! Response:', xhr.responseText);
                try {
                    const config = JSON.parse(xhr.responseText);
                    console.log('Parsed config:', config);
                } catch (e) {
                    console.error('JSON parse error:', e);
                }
            } else {
                console.error('Request failed:', xhr.status, xhr.statusText);
            }
        }
    };
    
    xhr.onerror = function() {
        console.error('Network error occurred');
    };
    
    xhr.send();
};

// Lobby Status Functions
function showLobbyStatus(gameId, playerCount, maxPlayers, isHost, autoStartEnabled = true) {
    const lobbyStatus = document.getElementById('lobbyStatus');
    const lobbyGameId = document.getElementById('lobby-game-id');
    const playerCountDisplay = document.getElementById('player-count-display');
    const lobbyStatusText = document.getElementById('lobby-status-text');
    const requirementText = document.querySelector('.requirement-text');
    
    // Show the lobby status panel
    lobbyStatus.style.display = 'block';
    
    // Update game ID
    lobbyGameId.textContent = `Game ID: ${gameId}`;
    
    // Update player count
    playerCountDisplay.textContent = `${playerCount}/${maxPlayers} players`;
    
    // Update status text based on auto-start setting
    if (playerCount >= 2) {
        if (autoStartEnabled) {
            // Auto-start is enabled
            lobbyStatusText.textContent = 'Auto-starting game...';
            lobbyStatusText.className = 'status-starting';
            requirementText.textContent = 'Game will start automatically!';
            
            // Hide the start button since auto-start will happen
            const startBtn = document.getElementById('startGameBtn');
            if (startBtn) {
                startBtn.style.display = 'none';
            }
        } else {
            // Manual start mode
            if (isHost) {
                lobbyStatusText.textContent = 'Ready to start! Click "Start Game"';
                lobbyStatusText.className = 'status-ready';
                requirementText.textContent = 'Game is ready to start!';
                
                // Show the start button for the host
                const startBtn = document.getElementById('startGameBtn');
                if (startBtn) {
                    startBtn.style.display = 'block';
                }
            } else {
                lobbyStatusText.textContent = 'Ready to start! Waiting for host...';
                lobbyStatusText.className = 'status-ready';
                requirementText.textContent = 'Waiting for host to start the game';
            }
        }
    } else {
        lobbyStatusText.textContent = 'Waiting for more players...';
        lobbyStatusText.className = 'status-waiting';
        requirementText.textContent = 'Need at least 2 players to start';
    }
    
    // Update player list (for now, just show count - we'll enhance this later)
    updatePlayerList(playerCount, isHost);
}

function updateLobbyPlayerCount(playerCount, maxPlayers, autoStartEnabled = true) {
    const playerCountDisplay = document.getElementById('player-count-display');
    const lobbyStatusText = document.getElementById('lobby-status-text');
    const requirementText = document.querySelector('.requirement-text');
    
    if (playerCountDisplay) {
        playerCountDisplay.textContent = `${playerCount}/${maxPlayers} players`;
    }
    
    if (lobbyStatusText) {
        if (playerCount >= 2) {
            if (autoStartEnabled) {
                // Auto-start is enabled
                lobbyStatusText.textContent = 'Auto-starting game...';
                lobbyStatusText.className = 'status-starting';
                requirementText.textContent = 'Game will start automatically!';
                
                // Hide the start button since auto-start will happen
                const startBtn = document.getElementById('startGameBtn');
                if (startBtn) {
                    startBtn.style.display = 'none';
                }
            } else {
                // Manual start mode - determine if user is host
                // We'll assume host status is maintained from the initial lobby setup
                const startBtn = document.getElementById('startGameBtn');
                const isHost = startBtn && startBtn.style.display !== 'none';
                
                if (isHost) {
                    lobbyStatusText.textContent = 'Ready to start! Click "Start Game"';
                    lobbyStatusText.className = 'status-ready';
                    requirementText.textContent = 'Game is ready to start!';
                    startBtn.style.display = 'block';
                } else {
                    lobbyStatusText.textContent = 'Ready to start! Waiting for host...';
                    lobbyStatusText.className = 'status-ready';
                    requirementText.textContent = 'Waiting for host to start the game';
                }
            }
        } else {
            lobbyStatusText.textContent = 'Waiting for more players...';
            lobbyStatusText.className = 'status-waiting';
            requirementText.textContent = 'Need at least 2 players to start';
        }
    }
    
    // Update player list
    updatePlayerList(playerCount, false);
}

function updatePlayerList(playerCount, isHost) {
    const playerList = document.getElementById('player-list');
    playerList.innerHTML = '';
    
    // For now, just show generic player entries
    // In a full implementation, we'd get actual player names from the server
    for (let i = 0; i < playerCount; i++) {
        const li = document.createElement('li');
        if (i === 0 && isHost) {
            li.textContent = 'Player ' + (i + 1) + ' (You - Host)';
            li.className = 'player-host';
        } else if (i === 0 && !isHost) {
            li.textContent = 'Player ' + (i + 1) + ' (Host)';
            li.className = 'player-host';
        } else {
            li.textContent = 'Player ' + (i + 1);
        }
        playerList.appendChild(li);
    }
}

function hideLobbyStatus() {
    const lobbyStatus = document.getElementById('lobbyStatus');
    lobbyStatus.style.display = 'none';
}

// =============================================================================
// DICE ANIMATION SYSTEM
// =============================================================================

function showDiceRoll(diceType, purpose, result, playerData = null) {
    const container = document.getElementById('dice-container');
    const diceDisplay = document.getElementById('dice-display');
    const resultTitle = document.getElementById('dice-result-title');
    const resultValue = document.getElementById('dice-result-value');
    const closeBtn = document.getElementById('dice-close-btn');
    const playerOrderDisplay = document.getElementById('player-order-display');
    
    // Clear previous dice
    diceDisplay.innerHTML = '';
    
    // Create the dice element
    const dice = createDiceElement(diceType, result);
    diceDisplay.appendChild(dice);
    
    // Set up title based on purpose
    let title = '';
    switch (purpose) {
        case 'player_order':
            title = '🎯 Rolling for Turn Order';
            break;
        case 'movement':
            title = '🚶 Movement Roll';
            break;
        default:
            title = '🎲 Rolling Dice';
    }
    
    resultTitle.textContent = title;
    resultValue.textContent = '?';
    
    // Hide player order display and close button initially
    playerOrderDisplay.style.display = 'none';
    closeBtn.style.display = 'none';
    
    // Show the container
    container.classList.add('active');
    
    // Start the dice rolling animation
    dice.classList.add('rolling');
    
    // After animation completes, show the result
    setTimeout(() => {
        dice.classList.remove('rolling');
        resultValue.textContent = result;
        
        // Special handling for player order determination
        if (purpose === 'player_order' && playerData) {
            setTimeout(() => {
                showPlayerOrderResults(playerData);
            }, 1000);
        } else {
            // For regular rolls, show close button after a moment
            setTimeout(() => {
                closeBtn.style.display = 'block';
            }, 1500);
        }
        
        // Update in-game dice panel for movement rolls
        if (purpose === 'movement') {
            updateInGameDiceDisplay(result);
        }
        
    }, 2000); // Match the animation duration
}

function createDiceElement(diceType, finalResult) {
    const dice = document.createElement('div');
    dice.className = `dice ${diceType}`;
    
    // Create 6 faces (simplified for both d6 and d12)
    const faces = ['front', 'back', 'right', 'left', 'top', 'bottom'];
    
    faces.forEach((faceClass, index) => {
        const face = document.createElement('div');
        face.className = `dice-face ${faceClass}`;
        
        if (diceType === 'd6') {
            // For D6, show dots or numbers
            if (faceClass === 'front') {
                // The front face will show the final result
                face.innerHTML = createDiceDots(finalResult);
            } else {
                // Other faces show random numbers
                const randomNum = Math.floor(Math.random() * 6) + 1;
                face.innerHTML = createDiceDots(randomNum);
            }
        } else {
            // For D12, just show numbers
            if (faceClass === 'front') {
                face.textContent = finalResult;
            } else {
                face.textContent = Math.floor(Math.random() * 12) + 1;
            }
        }
        
        dice.appendChild(face);
    });
    
    return dice;
}

function createDiceDots(number) {
    if (number < 1 || number > 6) {
        return number.toString();
    }
    
    const dotsContainer = document.createElement('div');
    dotsContainer.className = 'dice-dots';
    
    const dotPositions = {
        1: [4], // center
        2: [0, 8], // opposite corners
        3: [0, 4, 8], // diagonal
        4: [0, 2, 6, 8], // four corners
        5: [0, 2, 4, 6, 8], // four corners + center
        6: [0, 2, 3, 5, 6, 8] // two columns
    };
    
    // Create 9 positions (3x3 grid)
    for (let i = 0; i < 9; i++) {
        const dotSlot = document.createElement('div');
        if (dotPositions[number].includes(i)) {
            const dot = document.createElement('div');
            dot.className = 'dice-dot';
            dotSlot.appendChild(dot);
        }
        dotsContainer.appendChild(dotSlot);
    }
    
    return dotsContainer.outerHTML;
}

function showPlayerOrderResults(playerOrderData) {
    const playerOrderDisplay = document.getElementById('player-order-display');
    const playerOrderList = document.getElementById('player-order-list');
    const closeBtn = document.getElementById('dice-close-btn');
    
    // Clear previous results
    playerOrderList.innerHTML = '';
    
    // Sort players by their rolls (highest first)
    const sortedPlayers = Object.entries(playerOrderData)
        .sort((a, b) => b[1].roll - a[1].roll);
    
    // Create the ordered list
    sortedPlayers.forEach(([socketId, playerInfo], index) => {
        const listItem = document.createElement('li');
        listItem.className = 'player-order-item';
        
        const rank = document.createElement('span');
        rank.className = 'player-order-rank';
        rank.textContent = `#${index + 1}`;
        
        const name = document.createElement('span');
        name.className = 'player-order-name';
        name.textContent = playerInfo.name;
        
        const roll = document.createElement('span');
        roll.className = 'player-order-roll';
        roll.textContent = playerInfo.roll;
        
        listItem.appendChild(rank);
        listItem.appendChild(name);
        listItem.appendChild(roll);
        
        playerOrderList.appendChild(listItem);
    });
    
    // Show the player order display
    playerOrderDisplay.style.display = 'block';
    
    // Show close button
    setTimeout(() => {
        closeBtn.style.display = 'block';
    }, 1000);
}

function updateInGameDiceDisplay(rollValue) {
    const panel = document.getElementById('in-game-dice-panel');
    const miniDice = document.getElementById('current-mini-dice');
    const rollValueSpan = document.getElementById('current-roll-value');
    
    // Update the values
    miniDice.textContent = rollValue;
    rollValueSpan.textContent = rollValue;
    
    // Show the panel
    panel.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        panel.style.display = 'none';
    }, 5000);
}

function closeDiceDisplay() {
    const container = document.getElementById('dice-container');
    container.classList.remove('active');
    
    // Also hide in-game dice panel
    const inGamePanel = document.getElementById('in-game-dice-panel');
    inGamePanel.style.display = 'none';
}

// Function to trigger dice animation for testing
window.testDiceRoll = function(diceType = 'd6', result = null) {
    const actualResult = result || Math.floor(Math.random() * (diceType === 'd6' ? 6 : 12)) + 1;
    showDiceRoll(diceType, 'movement', actualResult);
};

// Function to test player order dice
window.testPlayerOrderDice = function() {
    const mockPlayerData = {
        'player1': { name: 'Alice', roll: Math.floor(Math.random() * 12) + 1 },
        'player2': { name: 'Bob', roll: Math.floor(Math.random() * 12) + 1 },
        'player3': { name: 'Charlie', roll: Math.floor(Math.random() * 12) + 1 }
    };
    
    // Show highest roll for animation
    const highestRoll = Math.max(...Object.values(mockPlayerData).map(p => p.roll));
    showDiceRoll('d12', 'player_order', highestRoll, mockPlayerData);
};

// =============================================================================
// ENHANCED GAME EVENT HANDLERS
// =============================================================================

// Initialize the game when page loads
window.addEventListener('load', function() {
    initGame();
    addLog('Welcome to NMB Game!', 'system');
    addLog('Create a new game or join an existing one to start playing.', 'system');
});