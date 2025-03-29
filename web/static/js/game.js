// 游戏页面逻辑
document.addEventListener('DOMContentLoaded', () => {
    // 初始化Socket.io连接
    const socket = io();
    
    // 获取DOM元素
    const gameCanvas = document.getElementById('game-canvas');
    const ctx = gameCanvas.getContext('2d');
    const currentPlayerName = document.getElementById('current-player-name');
    const diceResult = document.getElementById('dice-result');
    const rollDiceBtn = document.getElementById('roll-dice-btn');
    const floorUpBtn = document.getElementById('floor-up-btn');
    const floorDownBtn = document.getElementById('floor-down-btn');
    const currentFloor = document.getElementById('current-floor');
    const rotateBtn = document.getElementById('rotate-btn');
    const placeBtn = document.getElementById('place-btn');
    const increaseDazeBtn = document.getElementById('increase-daze-btn');
    const decreaseDazeBtn = document.getElementById('decrease-daze-btn');
    const endTurnBtn = document.getElementById('end-turn-btn');
    const playersContainer = document.getElementById('players-container');
    const statusMessage = document.getElementById('status-message');
    
    // 游戏状态
    let gameState = null;
    let currentFloorValue = 1;
    let selectedTile = null;
    let hoverTile = null; // 鼠标悬停的瓦片
    let isPlaceMode = false; // 是否处于放置模式
    const playerTokens = []; // 玩家标记
    
    // 常量
    const TILE_SIZE = 40;
    const BOARD_SIZE = 20;
    const PLAYER_COLORS = [
        '#ff0000', // 红色
        '#00ff00', // 绿色
        '#0000ff', // 蓝色
        '#ffff00', // 黄色
        '#ff00ff', // 紫色
        '#00ffff'  // 青色
    ];
    
    // 连接到游戏
    socket.on('connect', () => {
        console.log('已连接到服务器，Socket ID:', socket.id);
        showStatusMessage('已连接到服务器，准备游戏中...');
        
        // 加入游戏
        console.log('尝试加入游戏:', GAME_ID);
        socket.emit('join_game', {
            game_id: GAME_ID,
            player_id: localStorage.getItem('playerId') || 0 // 从本地存储获取玩家ID
        });
    });
    
    // 连接错误处理
    socket.on('connect_error', (err) => {
        console.error('连接错误:', err);
        showStatusMessage('连接错误: ' + err.message, true);
    });
    
    socket.on('disconnect', () => {
        console.log('与服务器断开连接');
        showStatusMessage('与服务器断开连接，请刷新页面', true);
    });
    
    // 添加初始化游戏的帮助信息
    function showInitialHelp() {
        if (gameState && gameState.selecting_start) {
            const currentPlayer = gameState.players[gameState.current_player];
            showStatusMessage(`游戏初始化：请为玩家${currentPlayer.name}选择初始位置，点击棋盘上的有效格子放置棋子`, false, 8000);
        }
    }
    
    // 监听游戏状态更新
    socket.on('game_state', (state) => {
        console.log('收到游戏状态更新:', state);
        console.log('选择初始位置模式:', state.selecting_start, typeof state.selecting_start);
        
        // 调试玩家位置信息
        if (state.players) {
            state.players.forEach((player, index) => {
                console.log(`玩家${player.name}位置: ${JSON.stringify(player.position)}, 类型: ${typeof player.position}`);
            });
        }
        
        // 保存上一次的状态
        const prevState = gameState;
        const isFirstState = !prevState;
        
        // 更新游戏状态
        gameState = state;
        
        // 确保选择初始位置模式的值是布尔类型
        if (typeof gameState.selecting_start === 'string') {
            console.log("选择初始位置模式值是字符串，转换为布尔值:", gameState.selecting_start);
            gameState.selecting_start = gameState.selecting_start === 'true' || gameState.selecting_start === '1';
            console.log("转换后的选择初始位置模式:", gameState.selecting_start, typeof gameState.selecting_start);
        }
        
        // 确保前端的当前楼层与游戏状态同步
        currentFloorValue = state.current_floor;
        
        // 检查是否所有玩家都有位置信息
        let allPlayersHavePositions = true;
        if (gameState.players) {
            for (const player of gameState.players) {
                if (!player.position) {
                    allPlayersHavePositions = false;
                    break;
                }
            }
        }
        
        // 如果所有玩家都有位置但selecting_start仍为true，则强制设为false并发送一个后端请求
        if (allPlayersHavePositions && gameState.selecting_start) {
            console.log("所有玩家都有位置，但选择初始位置模式仍为true，强制设为false");
            gameState.selecting_start = false;
            
            // 向服务器发送一个自定义事件，通知所有玩家已选择初始位置
            socket.emit('custom_event', {
                type: 'all_positions_set',
                message: '所有玩家已选择初始位置，强制开始游戏'
            });
            
            // 通知服务器重置selecting_start状态
            socket.emit('roll_dice', {
                force_start: true
            });
        }
        
        // 如果是第一次接收状态，保存玩家ID
        if (localStorage.getItem('playerId') === null && state.players && state.players.length > 0) {
            // 这里暂时注释掉自动设置玩家ID的逻辑，让玩家可以手动选择角色
            // const playerId = state.players[0].id;
            // localStorage.setItem('playerId', playerId);
            // console.log('设置玩家ID:', playerId);
        }
        
        // 检测玩家是否已移动
        if (prevState && prevState.players && gameState.players) {
            // 获取当前玩家
            const currentPlayerIndex = gameState.current_player;
            const currentPlayer = gameState.players[currentPlayerIndex];
            const prevPlayer = prevState.players[currentPlayerIndex];
            
            // 判断是否移动了位置
            if (currentPlayer && prevPlayer && 
                JSON.stringify(currentPlayer.position) !== JSON.stringify(prevPlayer.position)) {
                gameState.moved = true;
            } else if (prevState.current_player !== gameState.current_player) {
                // 如果玩家切换了，重置moved状态
                gameState.moved = false;
            }
        }
        
        updateUI();
        
        // 如果是首次加载状态并且正在选择初始位置，显示帮助信息
        if (isFirstState) {
            setTimeout(showInitialHelp, 1000);
        }
    });
    
    // 监听掷骰子结果
    socket.on('dice_result', (data) => {
        console.log('掷骰子结果:', data);
        
        // 更新游戏状态中的骰子值
        if (gameState) {
            // 更新骰子值显示
            diceResult.textContent = data.dice_value;
            
            // 更新游戏状态中的骰子值
            gameState.dice_value = data.dice_value;
            gameState.moved = false; // 重置移动状态
            
            // 显示移动提示
            const currentPlayer = gameState.players[gameState.current_player];
            showStatusMessage(`${currentPlayer.name}掷出了${data.dice_value}点，请选择高亮显示的格子进行移动`);
            
            // 重绘棋盘以高亮显示可移动的格子
            drawBoard();
            
            // 添加移动提示
            addMoveTip();
            
            // 强制更新UI显示
            requestAnimationFrame(() => {
                diceResult.textContent = data.dice_value;
            });
        } else {
            diceResult.textContent = data.dice_value;
            showStatusMessage(`玩家${data.player_index + 1}掷出了${data.dice_value}点`);
        }
        
        // 动画效果
        animateDice(data.dice_value);
    });
    
    // 监听错误消息
    socket.on('error', (data) => {
        console.error('错误:', data.message);
        showStatusMessage(`错误: ${data.message}`, true);
    });
    
    // 监听成功消息
    socket.on('success', (data) => {
        console.log('收到成功消息:', data);
        
        if (data.message) {
            // 显示成功消息
            const isError = data.message.includes('错误') || data.message.includes('失败');
            showStatusMessage(data.message, isError);
            
            // 如果检测到游戏阶段变更（从初始位置选择阶段转为正常游戏）
            if (data.phase_changed || data.message.includes('游戏正式开始')) {
                console.log("检测到游戏阶段变更，从选择初始位置转为正常游戏");
                
                // 如果gameState还没有更新，先本地更新
                if (gameState && gameState.selecting_start) {
                    console.log("本地更新gameState.selecting_start = false");
                    gameState.selecting_start = false;
                    updateUI(); // 立即更新UI，不等待服务器的game_state事件
                }
                
                // 播放游戏开始的特效
                playGameStartEffect();
            }
            
            // 如果是初始位置设置成功的消息，播放一个简单的视觉效果
            else if (data.message.includes('初始位置已设置')) {
                // 简单闪烁效果
                const flashCount = 3;
                let count = 0;
                const interval = setInterval(() => {
                    count++;
                    if (count > flashCount * 2) {
                        clearInterval(interval);
                        return;
                    }
                    
                    if (count % 2 === 1) {
                        gameCanvas.style.boxShadow = '0 0 20px rgba(0, 255, 0, 0.7)';
                    } else {
                        gameCanvas.style.boxShadow = 'none';
                    }
                }, 150);
                
                // 恢复正常显示
                setTimeout(() => {
                    gameCanvas.style.boxShadow = 'none';
                }, (flashCount * 2 + 1) * 150);
            }
            
            // 如果有位置设置信息，检查玩家列表更新
            if (data.position_set && data.player_name && data.player_position) {
                console.log(`收到玩家${data.player_name}的位置设置成功消息，位置: ${data.player_position}`);
                
                // 当收到位置设置成功的消息时，立即更新画布，不等待game_state更新
                if (gameState && gameState.players) {
                    // 查找对应的玩家
                    const playerIdx = gameState.players.findIndex(p => p.name === data.player_name);
                    if (playerIdx >= 0) {
                        console.log(`找到玩家${data.player_name}，更新位置为${data.player_position}`);
                        gameState.players[playerIdx].position = data.player_position;
                        updatePlayersList(); // 更新玩家列表
                        drawBoard(); // 重绘游戏板
                    }
                }
                
                // 如果selecting_start字段存在，立即更新游戏阶段
                if ('selecting_start' in data && gameState) {
                    console.log(`收到selecting_start更新: ${data.selecting_start}`);
                    gameState.selecting_start = data.selecting_start;
                    
                    // 如果初始位置选择阶段已结束，更新UI
                    if (!data.selecting_start) {
                        console.log("初始位置选择已完成，更新UI");
                        updateUI();
                    }
                }
            }
        }
    });
    
    // 播放游戏开始特效
    function playGameStartEffect() {
        console.log("播放游戏开始特效");
        
        // 添加游戏开始动画覆盖层
        const overlay = document.createElement('div');
        overlay.style.position = 'fixed';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
        overlay.style.display = 'flex';
        overlay.style.justifyContent = 'center';
        overlay.style.alignItems = 'center';
        overlay.style.zIndex = '9999';
        overlay.style.opacity = '0';
        overlay.style.transition = 'opacity 0.5s';
        
        const message = document.createElement('div');
        message.textContent = '游戏正式开始！';
        message.style.color = '#fff';
        message.style.fontSize = '36px';
        message.style.fontWeight = 'bold';
        message.style.textShadow = '0 0 10px #00ff00';
        
        overlay.appendChild(message);
        document.body.appendChild(overlay);
        
        // 显示动画
        setTimeout(() => {
            overlay.style.opacity = '1';
        }, 10);
        
        // 3秒后移除动画
        setTimeout(() => {
            overlay.style.opacity = '0';
            setTimeout(() => {
                overlay.remove();
            }, 500);
        }, 3000);
    }
    
    // 添加移动提示文本到UI
    function addMoveTip() {
        // 移除旧的提示（如果有）
        const oldTip = document.getElementById('move-tip');
        if (oldTip) {
            oldTip.remove();
        }
        
        // 只有在掷骰子后且不在初始位置选择阶段时显示提示
        if (gameState && !gameState.selecting_start && gameState.dice_value > 0 && !gameState.moved) {
            const tipDiv = document.createElement('div');
            tipDiv.id = 'move-tip';
            tipDiv.style.position = 'fixed';
            tipDiv.style.bottom = '10px';
            tipDiv.style.left = '50%';
            tipDiv.style.transform = 'translateX(-50%)';
            tipDiv.style.background = 'rgba(0, 0, 0, 0.7)';
            tipDiv.style.color = '#ffffff';
            tipDiv.style.padding = '10px 20px';
            tipDiv.style.borderRadius = '5px';
            tipDiv.style.zIndex = '1000';
            tipDiv.style.fontSize = '16px';
            tipDiv.style.fontWeight = 'bold';
            tipDiv.style.boxShadow = '0 0 10px rgba(0, 255, 0, 0.7)';
            tipDiv.style.animation = 'pulse 2s infinite';
            
            // 添加CSS动画
            const style = document.createElement('style');
            style.textContent = `
                @keyframes pulse {
                    0% { box-shadow: 0 0 10px rgba(0, 255, 0, 0.7); }
                    50% { box-shadow: 0 0 20px rgba(0, 255, 0, 1); }
                    100% { box-shadow: 0 0 10px rgba(0, 255, 0, 0.7); }
                }
            `;
            document.head.appendChild(style);
            
            const currentPlayer = gameState.players[gameState.current_player];
            tipDiv.textContent = `${currentPlayer.name}请选择绿色高亮格子移动${gameState.dice_value}步`;
            
            document.body.appendChild(tipDiv);
        }
    }
    
    // 更新UI
    function updateUI() {
        if (!gameState) return;
        
        // 更新当前玩家信息
        const currentPlayer = gameState.players[gameState.current_player];
        currentPlayerName.textContent = currentPlayer.name;
        currentPlayerName.style.color = PLAYER_COLORS[currentPlayer.id];
        
        // 设置当前玩家的ID
        gameState.current_turn = currentPlayer.id;
        
        // 更新骰子结果（只在没有值的时候显示0）
        if (!gameState.dice_value && gameState.dice_value !== 0) {
            diceResult.textContent = '0';
        }
        
        // 更新玩家列表
        updatePlayersList();
        
        // 检查所有玩家是否都有位置
        let allPlayersHavePositions = true;
        for (const player of gameState.players) {
            if (!player.position) {
                allPlayersHavePositions = false;
                break;
            }
        }
        console.log("所有玩家都有位置:", allPlayersHavePositions);
        
        // 显示调试信息
        const debugInfo = document.createElement('div');
        debugInfo.style.position = 'fixed';
        debugInfo.style.top = '10px';
        debugInfo.style.left = '10px';
        debugInfo.style.background = 'rgba(0,0,0,0.7)';
        debugInfo.style.color = 'white';
        debugInfo.style.padding = '10px';
        debugInfo.style.borderRadius = '5px';
        debugInfo.style.zIndex = '1000';
        debugInfo.style.fontSize = '12px';
        
        // 收集调试信息
        const diceValueType = typeof gameState.dice_value;
        const diceValueDisplay = gameState.dice_value || 0;
        
        debugInfo.innerHTML = `
            <div>初始位置模式: ${gameState.selecting_start} (类型: ${typeof gameState.selecting_start})</div>
            <div>骰子值: ${diceValueDisplay} (类型: ${diceValueType})</div>
            <div>当前玩家: ${gameState.current_player} (${currentPlayer.name})</div>
            <div>玩家位置: ${JSON.stringify(currentPlayer.position)}</div>
            <div>楼层: ${currentFloorValue}</div>
        `;
        
        // 移除旧的调试信息
        const oldDebug = document.getElementById('debug-info');
        if (oldDebug) {
            oldDebug.remove();
        }
        
        // 添加新的调试信息
        debugInfo.id = 'debug-info';
        document.body.appendChild(debugInfo);
        
        // 更新游戏容器的类，标识初始位置选择状态
        const gameContainer = document.querySelector('.game-container');
        if (gameState.selecting_start) {
            gameContainer.classList.add('selecting-start');
        } else {
            gameContainer.classList.remove('selecting-start');
        }
        
        console.log("UI更新 - 状态检查:", {
            selecting_start: gameState.selecting_start,
            dice_value: gameState.dice_value,
            current_player: gameState.current_player,
            current_turn: gameState.current_turn
        });
        
        // 绘制游戏板
        drawBoard();
        
        // 更新当前楼层显示
        currentFloor.textContent = currentFloorValue;
        
        // 强制转换selecting_start为布尔值
        const isSelectingStart = Boolean(gameState.selecting_start);
        console.log("转换后的选择初始位置状态:", isSelectingStart);
        
        // 根据游戏阶段设置UI状态 - 使用转换后的布尔值
        if (isSelectingStart) {
            // 初始位置选择阶段
            showStatusMessage(`请为${currentPlayer.name}选择初始位置，点击棋盘上的有效格子放置`);
            
            // 禁用游戏按钮
            rollDiceBtn.disabled = true;
            rotateBtn.disabled = true;
            placeBtn.disabled = true;
            increaseDazeBtn.disabled = true;
            decreaseDazeBtn.disabled = true;
            endTurnBtn.disabled = true;
            
            rollDiceBtn.style.opacity = '0.5';
            rotateBtn.style.opacity = '0.5';
            placeBtn.style.opacity = '0.5';
            increaseDazeBtn.style.opacity = '0.5';
            decreaseDazeBtn.style.opacity = '0.5';
            endTurnBtn.style.opacity = '0.5';
            
            console.log("初始位置阶段 - 按钮已禁用", {
                rollDice: rollDiceBtn.disabled,
                rotate: rotateBtn.disabled,
                place: placeBtn.disabled,
                increaseDaze: increaseDazeBtn.disabled,
                decreaseDaze: decreaseDazeBtn.disabled,
                endTurn: endTurnBtn.disabled
            });
        } else {
            // 常规游戏阶段
            // 启用游戏按钮
            rollDiceBtn.disabled = false;
            rotateBtn.disabled = false;
            placeBtn.disabled = false;
            increaseDazeBtn.disabled = false;
            decreaseDazeBtn.disabled = false;
            endTurnBtn.disabled = false;
            
            rollDiceBtn.style.opacity = '1';
            rotateBtn.style.opacity = '1';
            placeBtn.style.opacity = '1';
            increaseDazeBtn.style.opacity = '1';
            decreaseDazeBtn.style.opacity = '1';
            endTurnBtn.style.opacity = '1';
            
            console.log("游戏阶段 - 按钮已启用", {
                rollDice: !rollDiceBtn.disabled,
                rotate: !rotateBtn.disabled,
                place: !placeBtn.disabled,
                increaseDaze: !increaseDazeBtn.disabled,
                decreaseDaze: !decreaseDazeBtn.disabled,
                endTurn: !endTurnBtn.disabled
            });
            
            // 根据是否已经掷骰子来显示提示
            if (gameState.dice_value > 0) {
                showStatusMessage(`${currentPlayer.name}掷出了${gameState.dice_value}点，请选择绿色高亮格子进行移动`);
            } else {
                showStatusMessage(`${currentPlayer.name}的回合，请掷骰子`);
            }
        }
        
        // 添加移动提示
        addMoveTip();
    }
    
    // 更新玩家列表
    function updatePlayersList() {
        playersContainer.innerHTML = '';
        
        gameState.players.forEach((player, index) => {
            const playerItem = document.createElement('li');
            playerItem.className = 'player-item';
            if (index === gameState.current_player) {
                playerItem.classList.add('current');
            }
            
            const nameContainer = document.createElement('div');
            nameContainer.className = 'player-name-container';
            
            const colorSpan = document.createElement('span');
            colorSpan.className = 'player-color';
            colorSpan.style.backgroundColor = PLAYER_COLORS[player.id];
            
            const nameSpan = document.createElement('span');
            nameSpan.textContent = player.name;
            
            nameContainer.appendChild(colorSpan);
            nameContainer.appendChild(nameSpan);
            
            const statsSpan = document.createElement('span');
            statsSpan.className = 'player-stats';
            
            // 显示玩家的位置信息
            let posText = "未设置";
            if (player.position !== null && player.position !== undefined) {
                console.log(`处理玩家${player.name}的位置显示, 原始数据:`, player.position);
                
                let x, y;
                if (Array.isArray(player.position)) {
                    [x, y] = player.position;
                    posText = `(${x},${y})`;
                    console.log(`数组形式位置: (${x},${y})`);
                } else if (typeof player.position === 'object' && player.position !== null) {
                    // 如果是tuple形式的对象 {0: x, 1: y}
                    x = player.position[0];
                    y = player.position[1];
                    posText = `(${x},${y})`;
                    console.log(`对象形式位置: (${x},${y})`);
                } else if (typeof player.position === 'string') {
                    // 如果是字符串表示的坐标，例如 "(x,y)"
                    posText = player.position;
                    console.log(`字符串形式位置: ${player.position}`);
                } else {
                    // 未知形式，显示原始值
                    posText = `${player.position}`;
                    console.log(`未知形式位置: ${player.position}, 类型: ${typeof player.position}`);
                }
            } else {
                console.log(`玩家${player.name}没有位置信息`);
            }
            
            statsSpan.textContent = `位置: ${posText} 楼层: ${player.floor} 迷惑: ${player.daze}`;
            
            playerItem.appendChild(nameContainer);
            playerItem.appendChild(statsSpan);
            playersContainer.appendChild(playerItem);
        });
    }
    
    // 绘制游戏板
    function drawBoard() {
        // 清空画布
        ctx.clearRect(0, 0, gameCanvas.width, gameCanvas.height);
        
        // 绘制网格
        const offsetX = (gameCanvas.width - BOARD_SIZE * TILE_SIZE) / 2;
        const offsetY = (gameCanvas.height - BOARD_SIZE * TILE_SIZE) / 2;
        
        // 绘制棋盘背景
        ctx.fillStyle = '#3f3f5a';
        ctx.fillRect(offsetX, offsetY, BOARD_SIZE * TILE_SIZE, BOARD_SIZE * TILE_SIZE);
        
        // 绘制网格线
        ctx.strokeStyle = '#2d2d42';
        ctx.lineWidth = 1;
        
        // 水平线
        for (let i = 0; i <= BOARD_SIZE; i++) {
            ctx.beginPath();
            ctx.moveTo(offsetX, offsetY + i * TILE_SIZE);
            ctx.lineTo(offsetX + BOARD_SIZE * TILE_SIZE, offsetY + i * TILE_SIZE);
            ctx.stroke();
        }
        
        // 垂直线
        for (let i = 0; i <= BOARD_SIZE; i++) {
            ctx.beginPath();
            ctx.moveTo(offsetX + i * TILE_SIZE, offsetY);
            ctx.lineTo(offsetX + i * TILE_SIZE, offsetY + BOARD_SIZE * TILE_SIZE);
            ctx.stroke();
        }
        
        // 检查当前玩家位置和骰子值，打印调试信息
        if (gameState) {
            console.log("当前游戏状态:", {
                selecting_start: gameState.selecting_start,
                dice_value: gameState.dice_value,
                current_player: gameState.current_player
            });
            
            const currentPlayer = gameState.players[gameState.current_player];
            if (currentPlayer && currentPlayer.position) {
                console.log(`当前玩家 ${currentPlayer.name} 位置:`, currentPlayer.position);
            }
        }
        
        // 计算可移动的格子（如果掷了骰子且不在初始位置选择阶段）
        let movableTiles = [];
        if (gameState && !gameState.selecting_start && gameState.dice_value > 0) {
            console.log("检测到骰子值 > 0，计算可移动格子");
            const currentPlayer = gameState.players[gameState.current_player];
            if (currentPlayer && currentPlayer.position) {
                // 获取当前玩家位置
                let currentX, currentY;
                if (Array.isArray(currentPlayer.position)) {
                    [currentX, currentY] = currentPlayer.position;
                } else if (typeof currentPlayer.position === 'object' && currentPlayer.position !== null) {
                    currentX = currentPlayer.position[0];
                    currentY = currentPlayer.position[1];
                }
                
                if (currentX !== undefined && currentY !== undefined) {
                    const diceValue = gameState.dice_value;
                    console.log(`计算从(${currentX},${currentY})可移动${diceValue}步的格子`);
                    
                    // 计算曼哈顿距离恰好等于骰子点数的所有可能格子
                    for (let x = Math.max(0, currentX - diceValue); x <= Math.min(BOARD_SIZE - 1, currentX + diceValue); x++) {
                        for (let y = Math.max(0, currentY - diceValue); y <= Math.min(BOARD_SIZE - 1, currentY + diceValue); y++) {
                            const manhattanDistance = Math.abs(x - currentX) + Math.abs(y - currentY);
                            if (manhattanDistance === diceValue) {
                                // 检查该格子是否有效（有路径）
                                const isValid = isValidTile(x, y);
                                if (isValid) {
                                    // 检查该格子是否已被其他玩家占用
                                    const isOccupied = isOccupiedTile(x, y);
                                    if (!isOccupied) {
                                        movableTiles.push([x, y]);
                                    }
                                }
                            }
                        }
                    }
                    
                    console.log(`找到${movableTiles.length}个可移动的格子:`, movableTiles);
                }
            }
        }
        
        // 绘制棋盘瓦片
        if (gameState && gameState.board && gameState.board.floors) {
            const floorTiles = gameState.board.floors[currentFloorValue];
            if (floorTiles) {
                floorTiles.forEach(tile => {
                    const x = tile.x;
                    const y = tile.y;
                    
                    // 根据瓦片状态设置颜色
                    let tileColor;
                    
                    // 简化UI，使用固定颜色，不再使用动画效果
                    if (gameState.selecting_start && tile.status) {
                        // 初始位置选择阶段的白色瓦片
                        tileColor = '#ffffff';  // 纯白色
                    } else {
                        switch (tile.status) {
                            case 1: // 普通路径
                                tileColor = '#8a8aa5';
                                break;
                            case 2: // 特殊路径
                                tileColor = '#c4c4e0';
                                break;
                            case 3: // 可购买地块
                                tileColor = '#ffd700'; // 金色
                                break;
                            default:
                                tileColor = '#5a5a77';
                        }
                    }
                    
                    // 检查是否是可移动的格子
                    const isMovable = movableTiles.some(pos => pos[0] === x && pos[1] === y);
                    if (isMovable) {
                        // 高亮显示可移动的格子
                        tileColor = '#66ff66'; // 亮绿色
                    }
                    
                    // 绘制瓦片
                    ctx.fillStyle = tileColor;
                    ctx.fillRect(
                        offsetX + x * TILE_SIZE + 1, 
                        offsetY + y * TILE_SIZE + 1, 
                        TILE_SIZE - 2, 
                        TILE_SIZE - 2
                    );
                    
                    // 如果是可移动的格子，添加特殊标记
                    if (isMovable) {
                        // 绘制一个圆形标记
                        ctx.fillStyle = '#33cc33';  // 深绿色
                        ctx.beginPath();
                        ctx.arc(
                            offsetX + (x + 0.5) * TILE_SIZE,
                            offsetY + (y + 0.5) * TILE_SIZE,
                            TILE_SIZE / 4,
                            0,
                            Math.PI * 2
                        );
                        ctx.fill();
                        
                        // 添加脉动动画效果
                        const animPhase = (Date.now() % 2000) / 2000;  // 0到1之间的值，循环
                        const pulseSize = TILE_SIZE / 3 + Math.sin(animPhase * Math.PI * 2) * TILE_SIZE / 10;
                        
                        // 绘制闪烁的外环
                        ctx.strokeStyle = '#4caf50';
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        ctx.arc(
                            offsetX + (x + 0.5) * TILE_SIZE,
                            offsetY + (y + 0.5) * TILE_SIZE,
                            pulseSize,
                            0,
                            Math.PI * 2
                        );
                        ctx.stroke();
                    }
                });
            }
        }
        
        // 绘制选中的瓦片
        if (selectedTile) {
            const [x, y] = selectedTile;
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 3;
            ctx.strokeRect(
                offsetX + x * TILE_SIZE + 2,
                offsetY + y * TILE_SIZE + 2,
                TILE_SIZE - 4,
                TILE_SIZE - 4
            );
        }
        
        // 绘制鼠标悬停的瓦片
        if (hoverTile && gameState) {
            const [x, y] = hoverTile;
            
            // 检查是否是可移动的格子
            const isMovable = movableTiles.some(pos => pos[0] === x && pos[1] === y);
            
            // 如果是可移动的格子，使用绿色高亮；否则使用蓝色
            ctx.strokeStyle = isMovable ? '#00ff00' : '#00ffff';
            ctx.lineWidth = isMovable ? 3 : 2;
            ctx.strokeRect(
                offsetX + x * TILE_SIZE + 1,
                offsetY + y * TILE_SIZE + 1,
                TILE_SIZE - 2,
                TILE_SIZE - 2
            );
        }
        
        // 绘制玩家标记
        gameState.players.forEach(player => {
            // 检查玩家位置是否有效
            if (player.position !== null && player.position !== undefined && player.floor === currentFloorValue) {
                // 确保位置是数组形式
                let x, y;
                if (Array.isArray(player.position)) {
                    [x, y] = player.position;
                } else if (typeof player.position === 'object' && player.position !== null) {
                    // 如果是tuple形式的对象 {0: x, 1: y}
                    x = player.position[0];
                    y = player.position[1];
                }
                
                // 如果坐标有效，则绘制玩家标记
                if (x !== undefined && y !== undefined) {
                    // 打印调试信息
                    console.log(`绘制玩家${player.id+1}的标记，位置: (${x},${y}), 楼层: ${player.floor}`);
                    
                    // 判断是否是当前玩家
                    const isCurrentPlayer = player.id === gameState.players[gameState.current_player].id;
                    
                    // 如果是当前玩家，绘制一个闪烁的光环
                    if (isCurrentPlayer) {
                        const animPhase = (Date.now() % 1500) / 1500;  // 0到1之间的值，循环
                        const haloSize = TILE_SIZE / 2 + Math.sin(animPhase * Math.PI * 2) * TILE_SIZE / 10;
                        
                        ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
                        ctx.beginPath();
                        ctx.arc(
                            offsetX + (x + 0.5) * TILE_SIZE,
                            offsetY + (y + 0.5) * TILE_SIZE,
                            haloSize,
                            0,
                            Math.PI * 2
                        );
                        ctx.fill();
                    }
                    
                    ctx.fillStyle = PLAYER_COLORS[player.id];
                    ctx.beginPath();
                    ctx.arc(
                        offsetX + (x + 0.5) * TILE_SIZE, 
                        offsetY + (y + 0.5) * TILE_SIZE, 
                        TILE_SIZE / 3, 0, Math.PI * 2
                    );
                    ctx.fill();
                    
                    // 玩家ID
                    ctx.fillStyle = '#ffffff';
                    ctx.font = '12px Arial';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(
                        player.id + 1,
                        offsetX + (x + 0.5) * TILE_SIZE,
                        offsetY + (y + 0.5) * TILE_SIZE
                    );
                }
            }
        });
        
        // 请求下一帧绘制（让动画持续运行）
        if (!gameState.selecting_start && gameState.dice_value > 0 && movableTiles.length > 0) {
            requestAnimationFrame(drawBoard);
        }
    }
    
    // 检查格子是否有效（有路径）
    function isValidTile(x, y) {
        if (!gameState || !gameState.board || !gameState.board.floors) {
            return false;
        }
        
        const floorTiles = gameState.board.floors[currentFloorValue];
        if (!floorTiles) {
            return false;
        }
        
        // 检查该坐标是否在地图上有有效的瓦片
        return floorTiles.some(tile => 
            tile.x === x && tile.y === y && tile.status > 0
        );
    }
    
    // 检查格子是否被其他玩家占用
    function isOccupiedTile(x, y) {
        if (!gameState || !gameState.players) {
            return false;
        }
        
        // 检查是否有其他玩家在这个位置
        return gameState.players.some(player => {
            if (player.floor !== currentFloorValue) {
                return false;
            }
            
            // 获取玩家位置
            let playerX, playerY;
            if (Array.isArray(player.position)) {
                [playerX, playerY] = player.position;
            } else if (typeof player.position === 'object' && player.position !== null) {
                playerX = player.position[0];
                playerY = player.position[1];
            }
            
            // 检查位置是否匹配
            return playerX === x && playerY === y;
        });
    }
    
    // 骰子动画
    function animateDice(finalValue) {
        let count = 0;
        const animValues = [];
        
        // 生成随机动画值
        for (let i = 0; i < 10; i++) {
            animValues.push(Math.floor(Math.random() * 6) + 1);
        }
        
        // 末尾添加最终值
        animValues.push(finalValue);
        
        const interval = setInterval(() => {
            diceResult.textContent = animValues[count];
            count++;
            
            if (count >= animValues.length) {
                clearInterval(interval);
            }
        }, 100);
    }
    
    // 显示状态提示
    function showStatusMessage(message, isError = false, duration = 3000) {
        statusMessage.textContent = message;
        statusMessage.className = 'status-message visible';
        
        if (isError) {
            statusMessage.style.backgroundColor = 'rgba(255, 0, 0, 0.7)';
        } else {
            statusMessage.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
        }
        
        // 指定时间后自动隐藏
        setTimeout(() => {
            statusMessage.className = 'status-message';
        }, duration);
    }
    
    // 获取鼠标在棋盘上的位置
    function getBoardPosition(e) {
        const rect = gameCanvas.getBoundingClientRect();
        const offsetX = (gameCanvas.width - BOARD_SIZE * TILE_SIZE) / 2;
        const offsetY = (gameCanvas.height - BOARD_SIZE * TILE_SIZE) / 2;
        
        const x = Math.floor((e.clientX - rect.left - offsetX) / TILE_SIZE);
        const y = Math.floor((e.clientY - rect.top - offsetY) / TILE_SIZE);
        
        // 确保位置在棋盘内
        if (x >= 0 && x < BOARD_SIZE && y >= 0 && y < BOARD_SIZE) {
            return [x, y];
        }
        
        return null;
    }
    
    // 处理棋盘点击
    gameCanvas.addEventListener('click', (e) => {
        const position = getBoardPosition(e);
        if (!position) return;
        
        const [x, y] = position;
        console.log(`点击位置: (${x}, ${y})`);
        
        if (gameState && gameState.selecting_start) {
            // 初始位置选择模式
            const currentPlayer = gameState.players[gameState.current_player];
            socket.emit('move_player', {
                position: position
            });
            showStatusMessage(`正在为玩家${currentPlayer.name}设置初始位置为(${x}, ${y})...`);
        } else if (isPlaceMode) {
            // 放置卡片模式
            socket.emit('place_card', {
                position: position
            });
            showStatusMessage(`尝试在位置(${x}, ${y})放置卡片`);
            isPlaceMode = false; // 重置模式
            placeBtn.classList.remove('active');
        } else if (gameState && gameState.dice_value > 0) {
            // 移动玩家模式 - 只有掷骰子后才能移动
            // 检查是否是可移动的格子（曼哈顿距离等于骰子点数的格子）
            const currentPlayer = gameState.players[gameState.current_player];
            if (currentPlayer && currentPlayer.position) {
                // 获取当前玩家位置
                let currentX, currentY;
                if (Array.isArray(currentPlayer.position)) {
                    [currentX, currentY] = currentPlayer.position;
                } else if (typeof currentPlayer.position === 'object' && currentPlayer.position !== null) {
                    currentX = currentPlayer.position[0];
                    currentY = currentPlayer.position[1];
                }
                
                if (currentX !== undefined && currentY !== undefined) {
                    const diceValue = gameState.dice_value;
                    const manhattanDistance = Math.abs(x - currentX) + Math.abs(y - currentY);
                    
                    console.log(`当前位置(${currentX},${currentY})到目标位置(${x},${y})的曼哈顿距离: ${manhattanDistance}, 骰子点数: ${diceValue}`);
                    
                    if (manhattanDistance === diceValue) {
                        // 检查该格子是否有效（有路径）
                        const isValid = isValidTile(x, y);
                        if (isValid) {
                            // 检查该格子是否已被其他玩家占用
                            const isOccupied = isOccupiedTile(x, y);
                            if (!isOccupied) {
                                // 可以移动
                                selectedTile = position;
                                socket.emit('move_player', {
                                    position: position
                                });
                                showStatusMessage(`尝试移动到位置(${x}, ${y})`);
                                drawBoard(); // 重绘以显示选中效果
                            } else {
                                showStatusMessage('该位置已被其他玩家占用，不能移动到此处', true);
                            }
                        } else {
                            showStatusMessage('该位置不是有效的瓦片，不能移动到此处', true);
                        }
                    } else {
                        showStatusMessage(`移动距离必须等于骰子点数${diceValue}，当前选择的移动距离为${manhattanDistance}`, true);
                    }
                }
            }
        } else {
            // 没有掷骰子，不能移动
            showStatusMessage('请先掷骰子', true);
        }
    });
    
    // 掷骰子按钮点击事件
    rollDiceBtn.addEventListener('click', () => {
        console.log('点击掷骰子按钮, 游戏状态:', gameState);
        
        if (!gameState) {
            showStatusMessage('游戏状态未初始化', true);
            return;
        }
        
        // 如果处于选择初始位置阶段，检查剩余玩家并提示
        if (gameState.selecting_start) {
            const remainingPlayers = gameState.players.filter(player => !player.position).map(p => p.name).join('、');
            
            // 检查是否所有玩家都有位置
            let allPlayersHavePositions = true;
            for (const player of gameState.players) {
                if (!player.position) {
                    allPlayersHavePositions = false;
                    break;
                }
            }
            
            if (allPlayersHavePositions) {
                console.log("检测到所有玩家都有位置，尝试强制开始游戏");
                showStatusMessage('检测到所有玩家都有位置，尝试强制开始游戏...');
                
                // 如果所有玩家都有位置，强制开始游戏
                socket.emit('roll_dice', {
                    force_start: true
                });
                console.log('发送强制开始游戏请求');
                
                // 为防止多次点击，暂时禁用按钮
                rollDiceBtn.disabled = true;
                setTimeout(() => {
                    rollDiceBtn.disabled = false;
                }, 3000);
                
                return;
            }
            
            showStatusMessage(`游戏处于初始位置选择阶段，请先为以下玩家选择起始位置: ${remainingPlayers}`, true);
            console.log('仍需选择初始位置的玩家:', remainingPlayers);
            return;
        }
        
        // 获取玩家ID，如果存储中有就使用，否则默认为0
        const playerId = parseInt(localStorage.getItem('playerId') || '0');
        console.log(`当前玩家ID: ${playerId}, 当前回合玩家ID: ${gameState.current_turn}, 当前玩家索引: ${gameState.current_player}`);
        
        // 注释掉玩家ID检查，暂时允许任何人掷骰子
        /*
        if (gameState.current_turn !== playerId) {
            showStatusMessage('不是你的回合', true);
            return;
        }
        */
        
        if (gameState.dice_value > 0) {
            showStatusMessage('已经掷过骰子，请先移动', true);
            return;
        }
        
        console.log('发送掷骰子请求');
        socket.emit('roll_dice', {});
        showStatusMessage('掷骰子中...');
    });
    
    // 向上按钮点击事件
    floorUpBtn.addEventListener('click', () => {
        if (currentFloorValue < 5) { // 假设最大楼层为5
            currentFloorValue++;
            currentFloor.textContent = currentFloorValue;
            socket.emit('change_floor', { floor: currentFloorValue });
            showStatusMessage(`切换到第${currentFloorValue}层`);
            drawBoard();
        }
    });
    
    // 向下按钮点击事件
    floorDownBtn.addEventListener('click', () => {
        if (currentFloorValue > 1) {
            currentFloorValue--;
            currentFloor.textContent = currentFloorValue;
            socket.emit('change_floor', { floor: currentFloorValue });
            showStatusMessage(`切换到第${currentFloorValue}层`);
            drawBoard();
        }
    });
    
    // 旋转按钮点击事件
    rotateBtn.addEventListener('click', () => {
        socket.emit('rotate_card');
        showStatusMessage('旋转卡片');
    });
    
    // 放置按钮点击事件
    placeBtn.addEventListener('click', () => {
        isPlaceMode = !isPlaceMode;
        
        if (isPlaceMode) {
            placeBtn.classList.add('active');
            showStatusMessage('请点击棋盘上的位置放置卡片');
        } else {
            placeBtn.classList.remove('active');
            showStatusMessage('已取消放置模式');
        }
    });
    
    // 增加迷惑值按钮点击事件
    increaseDazeBtn.addEventListener('click', () => {
        socket.emit('change_daze', { change: 1 });
        showStatusMessage('增加迷惑值');
    });
    
    // 减少迷惑值按钮点击事件
    decreaseDazeBtn.addEventListener('click', () => {
        socket.emit('change_daze', { change: -1 });
        showStatusMessage('减少迷惑值');
    });
    
    // 鼠标移动事件处理
    gameCanvas.addEventListener('mousemove', (e) => {
        // 获取鼠标所在的瓦片位置
        const position = getBoardPosition(e);
        if (position) {
            // 如果位置发生变化，则更新悬停瓦片并重绘
            if (!hoverTile || hoverTile[0] !== position[0] || hoverTile[1] !== position[1]) {
                hoverTile = position;
                drawBoard(); // 重绘以显示悬停效果
            }
        } else if (hoverTile) {
            // 如果鼠标移出棋盘，清除悬停效果
            hoverTile = null;
            drawBoard();
        }
    });
    
    // 鼠标离开画布事件处理
    gameCanvas.addEventListener('mouseleave', () => {
        // 清除悬停效果
        hoverTile = null;
        drawBoard();
    });
    
    // 回合结束按钮
    endTurnBtn.addEventListener('click', () => {
        if (!gameState || gameState.selecting_start) {
            showStatusMessage('请先选择起始位置', true);
            return;
        }
        
        // 获取玩家ID，如果存储中有就使用，否则默认为0
        const playerId = parseInt(localStorage.getItem('playerId') || '0');
        
        if (gameState.current_turn !== playerId) {
            showStatusMessage('不是你的回合', true);
            return;
        }
        
        if (gameState.dice_value > 0 && !gameState.moved) {
            showStatusMessage('掷骰子后必须移动', true);
            return;
        }
        
        socket.emit('end_turn', {});
        showStatusMessage('回合结束');
    });
    
    // 添加强制开始游戏按钮
    const gameControlPanel = document.querySelector('.game-controls');
    if (gameControlPanel) {
        const forceStartBtn = document.createElement('button');
        forceStartBtn.id = 'force-start-btn';
        forceStartBtn.textContent = '强制开始游戏';
        forceStartBtn.className = 'force-start-btn';
        forceStartBtn.style.backgroundColor = '#ff9800';
        forceStartBtn.style.margin = '10px 0';
        forceStartBtn.style.padding = '10px 20px';
        
        // 添加点击事件
        forceStartBtn.addEventListener('click', () => {
            console.log('点击强制开始游戏按钮');
            showStatusMessage('正在强制开始游戏...');
            
            // 发送强制开始游戏请求
            socket.emit('roll_dice', {
                force_start: true
            });
            
            // 同时发送自定义事件通知
            socket.emit('custom_event', {
                type: 'all_positions_set',
                message: '手动强制开始游戏'
            });
            
            // 本地更新状态
            if (gameState) {
                gameState.selecting_start = false;
                updateUI();
            }
        });
        
        // 添加到控制面板
        gameControlPanel.appendChild(forceStartBtn);
    }
}); 