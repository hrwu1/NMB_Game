// 游戏页面逻辑
document.addEventListener('DOMContentLoaded', () => {
    console.log('=== 页面加载完成，初始化游戏 ===');
    
    // 游戏常量
    const ACTUAL_BOARD_SIZE = 20;  // 实际的棋盘大小（20x20）
    const TILE_SIZE = 30;  // 每个格子的像素大小
    
    // 检查服务器提供的游戏ID
    console.log('游戏ID (从服务器):', GAME_ID);
    
    // 如果GAME_ID未定义，尝试从URL获取
    if (typeof GAME_ID === 'undefined' || !GAME_ID) {
        const urlParams = new URLSearchParams(window.location.search);
        const gameIdFromUrl = urlParams.get('game_id') || window.location.pathname.split('/').pop();
        
        if (gameIdFromUrl && gameIdFromUrl !== 'game') {
            console.log('游戏ID (从URL):', gameIdFromUrl);
            window.GAME_ID = gameIdFromUrl; // 全局存储
        } else {
            console.error('错误: 未找到有效的游戏ID!');
            alert('错误: 未找到有效的游戏ID');
            return;
        }
    }
    
    // 创建一个仅用于调试的全局变量
    window.debugGameState = {
        receivedEvents: {},
        socketConnected: false,
        lastDiceValue: 0,
        eventCount: {
            game_state: 0,
            dice_result: 0,
            success: 0,
            error: 0
        }
    };
    
    // 初始化Socket.io连接
    const socket = io({
        reconnectionAttempts: 5,
        timeout: 10000,
        transports: ['websocket', 'polling']
    });
    
    // 添加Socket.IO连接调试
    socket.on('connect', () => {
        console.log('Socket.IO 连接成功，Socket ID:', socket.id);
        window.debugGameState.socketConnected = true;
        
        // 测试: 列出所有注册的事件监听器
        console.log('当前Socket事件监听器:');
        console.log('- connect');
        console.log('- disconnect');
        console.log('- game_state');
        console.log('- dice_result');
        console.log('- success');
        console.log('- error');
        
        // 连接成功后立即加入游戏
        console.log(`准备加入游戏: ${GAME_ID}`);
        const storedPlayerId = localStorage.getItem('playerId') || 0;
        console.log(`使用存储的玩家ID: ${storedPlayerId}`);
        
        // 同时记录oldPlayerId，用于后续检测玩家ID变化
        localStorage.setItem('oldPlayerId', storedPlayerId.toString());
        console.log(`设置oldPlayerId为: ${storedPlayerId}`);
        
        socket.emit('join_game', {
            game_id: GAME_ID,
            player_id: storedPlayerId
        });
        
        console.log('join_game事件已发送');
        showStatusMessage('已连接到服务器，准备加入游戏...');
    });
    
    socket.on('disconnect', () => {
        console.log('Socket.IO 连接断开!');
        window.debugGameState.socketConnected = false;
    });
    
    socket.on('connect_error', (error) => {
        console.error('Socket.IO 连接错误:', error);
    });
    
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
    const BOARD_SIZE = 20;
    const REGION_SIZE = 4; // 每个区域包含的瓦片数量
    const PLAYER_COLORS = [
        '#ff0000', // 红色
        '#00ff00', // 绿色
        '#0000ff', // 蓝色
        '#ffff00', // 黄色
        '#ff00ff', // 紫色
        '#00ffff'  // 青色
    ];
    
    // 添加全局事件监听器，捕获所有Socket.IO事件
    const originalOnevent = socket.onevent;
    socket.onevent = function(packet) {
        const args = packet.data || [];
        console.log(`接收到Socket.IO事件: ${args[0]}`, args.slice(1));
        
        // 记录事件到调试对象
        if (args[0]) {
            window.debugGameState.receivedEvents[args[0]] = args.slice(1);
            
            if (window.debugGameState.eventCount[args[0]] !== undefined) {
                window.debugGameState.eventCount[args[0]]++;
            }
        }
        
        originalOnevent.call(this, packet);
    };
    
    // 重新定义Socket.IO事件处理函数
    
    // 游戏状态更新事件
    function handleGameState(state) {
        console.log('!!! game_state 事件触发 !!!');
        console.log('=== 收到游戏状态更新 ===');
        console.log('原始状态数据:', state);
        
        if (!state) {
            console.error('收到的游戏状态为空!');
            return;
        }
        
        // 检查关键数据
        console.log('状态数据检查:');
        console.log('- 骰子值:', state.dice_value, '类型:', typeof state.dice_value);
        console.log('- 初始位置选择:', state.selecting_start, '类型:', typeof state.selecting_start);
        console.log('- 当前玩家:', state.current_player, '类型:', typeof state.current_player);
        
        // 检查棋盘数据
        if (state.board && state.board.floors) {
            console.log('棋盘数据:');
            console.log('- 楼层数:', Object.keys(state.board.floors).length);
            for (const floorNum in state.board.floors) {
                const tiles = state.board.floors[floorNum];
                console.log(`- 楼层${floorNum}: ${tiles.length}个瓦片`);
                if (tiles.length > 0) {
                    console.log(`  样本瓦片:`, tiles[0]);
                }
            }
        } else {
            console.error('状态中没有棋盘数据!');
        }
        
        // 检查玩家数据
        if (state.players) {
            console.log('玩家数据:');
            console.log('- 玩家数:', state.players.length);
            state.players.forEach((player, idx) => {
                console.log(`- 玩家${idx+1}: id=${player.id}, name=${player.name}, position=${JSON.stringify(player.position)}, floor=${player.floor}`);
            });
            
            // 检查当前玩家ID，并保存到localStorage
            const currentPlayerIndex = parseInt(state.current_player);
            if (!isNaN(currentPlayerIndex) && state.players[currentPlayerIndex]) {
                // 保存玩家索引到localStorage，这是current_player的值
                console.log(`保存当前玩家索引到localStorage: ${currentPlayerIndex}`);
                localStorage.setItem('playerId', currentPlayerIndex.toString());
                
                // 检查是否需要更新服务器端session
                const oldPlayerId = parseInt(localStorage.getItem('oldPlayerId') || '-1');
                if (oldPlayerId !== currentPlayerIndex) {
                    console.log(`玩家索引已变更: ${oldPlayerId} -> ${currentPlayerIndex}，向服务器同步`);
                    // 发送加入游戏事件，更新服务器端session
                    socket.emit('join_game', {
                        game_id: GAME_ID,
                        player_id: currentPlayerIndex
                    });
                    // 记录已更新的ID，避免重复发送
                    localStorage.setItem('oldPlayerId', currentPlayerIndex.toString());
                }
            }
        } else {
            console.error('状态中没有玩家数据!');
        }
        
        const prevState = gameState;
        const prevDiceValue = gameState ? gameState.dice_value : 0;
        const prevMoved = gameState ? gameState.moved : false;
        
        console.log('更新前的状态:', {
            prevDiceValue: prevDiceValue,
            prevMoved: prevMoved,
            currentPlayer: prevState ? prevState.current_player : 'undefined'
        });
        
        // 检查玩家是否切换
        const isPlayerChanged = state.current_player !== undefined && 
                              prevState && 
                              state.current_player !== prevState.current_player;
        
        console.log('是否切换玩家:', isPlayerChanged);
        
        // 计算新的骰子值
        let newDiceValue;
        if (isPlayerChanged) {
            // 玩家切换时，使用新状态的骰子值
            newDiceValue = parseInt(state.dice_value || 0);
            console.log('玩家切换，使用新骰子值:', newDiceValue);
        } else {
            // 非玩家切换，优先使用之前的骰子值，除非之前为0且新值不为0
            newDiceValue = (parseInt(prevDiceValue) > 0) ? 
                parseInt(prevDiceValue) : 
                parseInt(state.dice_value || 0);
            console.log('非玩家切换，计算骰子值:', {
                prevValue: prevDiceValue,
                stateValue: state.dice_value,
                finalValue: newDiceValue
            });
        }
        
        // 保存原始gameState对象用于比较
        const originalGameState = gameState ? JSON.parse(JSON.stringify(gameState)) : null;
        
        // 更新游戏状态
        gameState = {
            ...state,
            dice_value: newDiceValue,
            moved: isPlayerChanged ? state.moved : prevMoved,
            selecting_start: Boolean(state.selecting_start)
        };
        
        // 记录到调试对象
        window.debugGameState.lastDiceValue = newDiceValue;
        
        console.log('更新后的gameState:', {
            dice_value: gameState.dice_value,
            moved: gameState.moved,
            current_player: gameState.current_player,
            selecting_start: gameState.selecting_start
        });
        
        // 检查游戏状态是否为第一次加载 (prevState 为 null)
        if (!prevState) {
            console.log('首次加载游戏状态!');
            
            // 立即初始化棋盘 - 这是关键步骤
            console.log('初始化棋盘...');
            try {
                drawBoard();
                console.log('棋盘初始化成功!');
            } catch (error) {
                console.error('棋盘初始化错误:', error);
            }
            
            // 检查是否处于选择初始位置阶段，显示提示
            if (gameState.selecting_start) {
                console.log('游戏处于初始位置选择阶段，显示提示');
                
                // 确保当前玩家存在
                if (gameState.players && gameState.current_player !== undefined) {
                    const currentPlayer = gameState.players[gameState.current_player];
                    if (currentPlayer) {
                        showStatusMessage(`请为${currentPlayer.name}选择初始位置，点击棋盘上的有效格子放置`);
                    }
                }
            }
        }
        
        // 同步玩家的骰子值
        if (gameState.players && gameState.current_player !== undefined) {
            const currentPlayer = gameState.players[gameState.current_player];
            if (currentPlayer) {
                const oldPlayerDiceValue = currentPlayer.dice_value;
                currentPlayer.dice_value = gameState.dice_value;
                console.log('同步当前玩家骰子值:', {
                    player_name: currentPlayer.name,
                    old_dice_value: oldPlayerDiceValue,
                    new_dice_value: currentPlayer.dice_value
                });
            }
        }
        
        // 强制更新骰子显示值
        if (diceResult) {
            if (gameState.dice_value > 0) {
                console.log(`强制更新骰子显示元素为: ${gameState.dice_value}`);
                diceResult.textContent = gameState.dice_value;
            } else {
                console.log('骰子值为0，重置骰子显示为0');
                diceResult.textContent = '0';
            }
        } else {
            console.error('找不到骰子显示元素!');
        }
        
        // 更新UI
        console.log('准备调用updateUI()');
        updateUI();
        console.log('updateUI()调用完成');
        
        // 如果有骰子值且未移动，重新计算可移动格子
        if (gameState.dice_value > 0 && !gameState.moved) {
            console.log('检测到有效的骰子值且未移动，重绘棋盘显示可移动格子');
            drawBoard();
            addMoveTip();
        }
        
        console.log('=== 游戏状态更新处理完成 ===');
    }
    
    // 掷骰子结果事件
    function handleDiceResult(data) {
        console.log('!!! dice_result 事件触发 !!!');
        console.log('收到掷骰子结果:', data);
        
        if (!data || !data.dice_value) {
            console.error('掷骰子结果数据无效!');
            return;
        }
        
        // 解析骰子值并立即更新显示
        const diceValue = parseInt(data.dice_value);
        
        // 立即更新显示骰子值
        if (diceResult) {
            console.log('直接更新骰子显示为:', diceValue);
            diceResult.textContent = diceValue;
        } else {
            console.error('找不到骰子显示元素!');
        }
        
        // 记录到调试对象
        window.debugGameState.lastDiceValue = diceValue;
        
        // 确保gameState存在
        if (!gameState) {
            gameState = {
                dice_value: 0,
                moved: false,
                players: []
            };
        }
        
        // 更新游戏状态中的骰子值
        gameState.dice_value = diceValue;
        gameState.moved = false;
        
        // 更新当前玩家的骰子值
        if (gameState.players && gameState.current_player !== undefined) {
            const currentPlayer = gameState.players[gameState.current_player];
            if (currentPlayer) {
                currentPlayer.dice_value = diceValue;
                
                console.log('更新玩家骰子值:', {
                    player_name: currentPlayer.name,
                    dice_value: currentPlayer.dice_value
                });
                
                // 显示移动提示
                showStatusMessage(`${currentPlayer.name}掷出了${diceValue}点，请选择高亮显示的格子进行移动`);
                
                // 重绘棋盘以显示可移动的格子
                drawBoard();
                addMoveTip();
                
                // 执行骰子动画（但不影响已经显示的值）
                animateDice(diceValue);
            }
        }
    }
    
    // 注册事件处理函数
    console.log('注册Socket.IO事件处理函数');
    socket.off('game_state').on('game_state', handleGameState);
    socket.off('dice_result').on('dice_result', handleDiceResult);
    
    socket.off('success').on('success', function(data) {
        console.log('!!! success 事件触发 !!!');
        console.log('收到成功消息:', data);
        
        if (data && data.message) {
            // 显示成功消息
            const isError = data.message.includes('错误') || data.message.includes('失败');
            showStatusMessage(data.message, isError);
            
            // 检查是否为加入游戏成功消息
            if (data.message.includes('已加入游戏')) {
                console.log('收到加入游戏成功消息');
                // 如果消息中包含player_id，则更新本地存储
                if (data.player_id !== undefined) {
                    const playerIdFromServer = parseInt(data.player_id);
                    console.log(`从服务器接收到玩家ID: ${playerIdFromServer}`);
                    
                    // 更新本地存储
                    localStorage.setItem('playerId', playerIdFromServer.toString());
                    localStorage.setItem('oldPlayerId', playerIdFromServer.toString());
                    console.log(`已更新本地存储的玩家ID: ${playerIdFromServer}`);
                }
            }
            
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
    
    socket.off('error').on('error', function(data) {
        console.log('!!! error 事件触发 !!!');
        console.error('错误:', data.message);
        showStatusMessage(`错误: ${data.message}`, true);
    });
    
    // 定时检查调试状态
    setInterval(() => {
        console.log('调试状态检查:', {
            socketConnected: window.debugGameState.socketConnected,
            eventCounts: window.debugGameState.eventCount,
            lastDiceValue: window.debugGameState.lastDiceValue,
            currentDiceDisplay: diceResult ? diceResult.textContent : 'element不存在'
        });
    }, 10000); // 每10秒检查一次
    
    // 绘制游戏板
    function drawBoard() {
        // 清空画布
        ctx.clearRect(0, 0, gameCanvas.width, gameCanvas.height);
        console.log('开始绘制棋盘...');
        
        // 计算实际的棋盘大小（20x20）
        const ACTUAL_BOARD_SIZE = 20;  // 新的棋盘大小为20x20
        
        // 计算新的偏移量，使棋盘居中
        const offsetX = (gameCanvas.width - ACTUAL_BOARD_SIZE * TILE_SIZE) / 2;
        const offsetY = (gameCanvas.height - ACTUAL_BOARD_SIZE * TILE_SIZE) / 2;
        
        // 绘制棋盘背景
        ctx.fillStyle = '#3f3f5a';
        ctx.fillRect(offsetX, offsetY, ACTUAL_BOARD_SIZE * TILE_SIZE, ACTUAL_BOARD_SIZE * TILE_SIZE);
        
        // 绘制网格线
        ctx.strokeStyle = '#2d2d42';
        ctx.lineWidth = 1;
        
        // 水平线
        for (let i = 0; i <= ACTUAL_BOARD_SIZE; i++) {
            ctx.beginPath();
            ctx.moveTo(offsetX, offsetY + i * TILE_SIZE);
            ctx.lineTo(offsetX + ACTUAL_BOARD_SIZE * TILE_SIZE, offsetY + i * TILE_SIZE);
            ctx.stroke();
        }
        
        // 垂直线
        for (let i = 0; i <= ACTUAL_BOARD_SIZE; i++) {
            ctx.beginPath();
            ctx.moveTo(offsetX + i * TILE_SIZE, offsetY);
            ctx.lineTo(offsetX + i * TILE_SIZE, offsetY + ACTUAL_BOARD_SIZE * TILE_SIZE);
            ctx.stroke();
        }
        
        if (!gameState) {
            console.log('绘制基本棋盘完成 (无游戏状态)');
            return;
        }
        
        // 如果没有棋盘数据，给出警告并返回
        if (!gameState.board || !gameState.board.floors) {
            console.error('警告: gameState中没有棋盘数据!');
            
            // 绘制一个简单的错误提示在棋盘中央
            ctx.fillStyle = 'red';
            ctx.font = '20px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('棋盘数据加载错误!', gameCanvas.width / 2, gameCanvas.height / 2);
            return;
        }
        
        console.log(`绘制棋盘内容 - 楼层: ${currentFloorValue}`);
        
        // 计算可移动的格子
        let movableTiles = [];
        
        // 骰子值大于0，不在初始位置选择阶段，且本回合未移动
        if (!gameState.selecting_start && gameState.dice_value > 0 && !gameState.moved) {
            const diceValue = parseInt(gameState.dice_value);
            
            console.log(`计算可移动格子 - 骰子值: ${diceValue}, 移动状态: ${gameState.moved}`);
            
            const currentPlayer = gameState.players[gameState.current_player];
            if (currentPlayer && currentPlayer.position) {
                let currentX, currentY;
                if (Array.isArray(currentPlayer.position)) {
                    [currentX, currentY] = currentPlayer.position;
                } else if (typeof currentPlayer.position === 'object' && currentPlayer.position !== null) {
                    currentX = currentPlayer.position[0];
                    currentY = currentPlayer.position[1];
                }
                
                if (currentX !== undefined && currentY !== undefined) {
                    console.log(`从位置(${currentX},${currentY})计算${diceValue}步可达的格子`);
                    
                    // 计算曼哈顿距离等于骰子值的所有格子
                    for (let x = Math.max(0, currentX - diceValue); x <= Math.min(BOARD_SIZE - 1, currentX + diceValue); x++) {
                        for (let y = Math.max(0, currentY - diceValue); y <= Math.min(BOARD_SIZE - 1, currentY + diceValue); y++) {
                            const manhattanDistance = Math.abs(x - currentX) + Math.abs(y - currentY);
                            if (manhattanDistance === diceValue) {
                                if (isValidTile(x, y) && !isOccupiedTile(x, y)) {
                                    movableTiles.push([x, y]);
                                }
                            }
                        }
                    }
                    
                    console.log(`找到${movableTiles.length}个可移动的格子:`, movableTiles);
                }
            }
        }
        
        // 获取当前楼层数据
        const floorData = gameState.board.floors[currentFloorValue];
        if (!floorData) {
            console.error(`当前楼层${currentFloorValue}没有数据!`);
            return;
        }
        
        // 首先绘制区域边界和背景
        const mapSize = gameState.board.map_size || 5;
        const regionSize = gameState.board.region_size || 4;
        
        // 绘制区域边界
        ctx.strokeStyle = '#6a6a8a';
        ctx.lineWidth = 2;
        for (let i = 0; i <= mapSize; i++) {
            // 垂直线
            ctx.beginPath();
            ctx.moveTo(offsetX + i * regionSize * TILE_SIZE, offsetY);
            ctx.lineTo(offsetX + i * regionSize * TILE_SIZE, offsetY + ACTUAL_BOARD_SIZE * TILE_SIZE);
            ctx.stroke();
            
            // 水平线
            ctx.beginPath();
            ctx.moveTo(offsetX, offsetY + i * regionSize * TILE_SIZE);
            ctx.lineTo(offsetX + ACTUAL_BOARD_SIZE * TILE_SIZE, offsetY + i * regionSize * TILE_SIZE);
            ctx.stroke();
        }
        
        // 检查新的数据格式
        const tiles = floorData.tiles || [];
        
        // 绘制未铺设但可放置的区域
        if (floorData.placeable_regions && floorData.placeable_regions.length > 0) {
            console.log(`绘制${floorData.placeable_regions.length}个可放置区域`);
            ctx.fillStyle = '#4a4a6a'; // 未铺设区域的颜色
            
            floorData.placeable_regions.forEach(region => {
                const regionX = region.x;
                const regionY = region.y;
                
                // 绘制区域背景 - 略淡一些表示未铺设
                ctx.globalAlpha = 0.6;
                ctx.fillRect(
                    offsetX + regionX * regionSize * TILE_SIZE,
                    offsetY + regionY * regionSize * TILE_SIZE,
                    regionSize * TILE_SIZE,
                    regionSize * TILE_SIZE
                );
                ctx.globalAlpha = 1.0;
                
                // 绘制"未铺设"标识
                ctx.fillStyle = '#ffffff';
                ctx.font = '14px Arial';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(
                    '未铺设',
                    offsetX + (regionX * regionSize + regionSize/2) * TILE_SIZE,
                    offsetY + (regionY * regionSize + regionSize/2) * TILE_SIZE
                );
                ctx.fillStyle = '#4a4a6a'; // 恢复未铺设区域的颜色
            });
        }
        
        // 绘制已放置区域
        if (floorData.placed_regions && floorData.placed_regions.length > 0) {
            console.log(`绘制${floorData.placed_regions.length}个已放置区域`);
            ctx.fillStyle = '#5a5a77'; // 已放置区域的颜色
            
            floorData.placed_regions.forEach(region => {
                const regionX = region.x;
                const regionY = region.y;
                
                // 绘制区域背景
                ctx.fillRect(
                    offsetX + regionX * regionSize * TILE_SIZE,
                    offsetY + regionY * regionSize * TILE_SIZE,
                    regionSize * TILE_SIZE,
                    regionSize * TILE_SIZE
                );
                
                // 绘制区域编号或标识
                ctx.fillStyle = '#ffffff';
                ctx.font = '12px Arial';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(
                    `区域(${regionX},${regionY})`,
                    offsetX + (regionX * regionSize + regionSize/2) * TILE_SIZE,
                    offsetY + (regionY * regionSize + regionSize/2) * TILE_SIZE - 10
                );
                ctx.fillStyle = '#5a5a77'; // 恢复已放置区域的颜色
            });
        }
        
        // 绘制具体的瓦片（白色可通行区域）
        console.log(`绘制${tiles.length}个瓦片`);
        tiles.forEach(tile => {
            const x = tile.x;
            const y = tile.y;
            
            // 根据瓦片状态设置颜色
            let tileColor;
            
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
            
            // 检查是否是特殊瓦片
            if (tile.special) {
                switch(tile.special) {
                    case 'stairs':
                        tileColor = '#00cccc'; // 青色为楼梯
                        break;
                    case 'elevator':
                        tileColor = '#cc00cc'; // 紫色为电梯
                        break;
                    default:
                        // 保持原色
                        break;
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
            
            // 绘制特殊瓦片图标
            if (tile.special) {
                const centerX = offsetX + (x + 0.5) * TILE_SIZE;
                const centerY = offsetY + (y + 0.5) * TILE_SIZE;
                
                if (tile.special === 'stairs') {
                    // 绘制楼梯图标
                    ctx.strokeStyle = '#ffffff';
                    ctx.lineWidth = 2;
                    for (let i = 0; i < 3; i++) {
                        // 绘制三条水平线表示楼梯
                        const lineY = centerY - TILE_SIZE/4 + i * TILE_SIZE/4;
                        ctx.beginPath();
                        ctx.moveTo(centerX - TILE_SIZE/3, lineY);
                        ctx.lineTo(centerX + TILE_SIZE/3, lineY);
                        ctx.stroke();
                    }
                } else if (tile.special === 'elevator') {
                    // 绘制电梯图标
                    ctx.strokeStyle = '#ffffff';
                    ctx.lineWidth = 2;
                    
                    // 电梯箱
                    ctx.strokeRect(
                        centerX - TILE_SIZE/3,
                        centerY - TILE_SIZE/3,
                        TILE_SIZE/1.5,
                        TILE_SIZE/1.5
                    );
                    
                    // 上下箭头
                    ctx.beginPath();
                    // 上箭头
                    ctx.moveTo(centerX, centerY - TILE_SIZE/6);
                    ctx.lineTo(centerX - TILE_SIZE/6, centerY);
                    ctx.moveTo(centerX, centerY - TILE_SIZE/6);
                    ctx.lineTo(centerX + TILE_SIZE/6, centerY);
                    // 下箭头
                    ctx.moveTo(centerX, centerY + TILE_SIZE/6);
                    ctx.lineTo(centerX - TILE_SIZE/6, centerY);
                    ctx.moveTo(centerX, centerY + TILE_SIZE/6);
                    ctx.lineTo(centerX + TILE_SIZE/6, centerY);
                    ctx.stroke();
                }
            }
            
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
            }
        });
        
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
        if (hoverTile) {
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
        if (gameState.players) {
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
        }
        
        // 请求下一帧绘制（让动画持续运行）
        if (!gameState.selecting_start && gameState.dice_value > 0 && movableTiles.length > 0) {
            requestAnimationFrame(drawBoard);
        }
        
        console.log('绘制棋盘完成');
    }
    
    // 检查格子是否有效（有路径）
    function isValidTile(x, y) {
        if (!gameState || !gameState.board || !gameState.board.floors) {
            return false;
        }
        
        const floorData = gameState.board.floors[currentFloorValue];
        if (!floorData) {
            return false;
        }
        
        // 检查新的数据格式
        if (floorData.tiles) {
            // 新格式：检查给定坐标是否在tiles数组中存在
            return floorData.tiles.some(tile => 
                tile.x === x && tile.y === y && tile.status > 0
            );
        } else {
            // 旧格式：直接检查floorData中是否有该坐标
            return floorData.some(tile => 
                tile.x === x && tile.y === y && tile.status > 0
            );
        }
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
            } else if (typeof player.position === 'string') {
                // 处理可能的字符串格式 "[x,y]"
                try {
                    const posArray = JSON.parse(player.position);
                    if (Array.isArray(posArray) && posArray.length === 2) {
                        [playerX, playerY] = posArray;
                    }
                } catch (e) {
                    console.error('解析玩家位置时出错:', e);
                    return false;
                }
            }
            
            // 检查位置是否匹配
            return playerX === x && playerY === y;
        });
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
            
            const currentPlayer = gameState.players[gameState.current_player];
            tipDiv.textContent = `${currentPlayer.name}请选择绿色高亮格子移动${gameState.dice_value}步`;
            
            document.body.appendChild(tipDiv);
        }
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
    
    // 骰子动画 - 修改为不会覆盖实际显示的值
    function animateDice(finalValue) {
        console.log(`开始骰子动画，最终值: ${finalValue}`);
        // 创建一个动画元素，不直接修改diceResult
        const animElement = document.createElement('div');
        animElement.style.position = 'absolute';
        animElement.style.top = '0';
        animElement.style.left = '0';
        animElement.style.width = '100%';
        animElement.style.height = '100%';
        animElement.style.display = 'flex';
        animElement.style.justifyContent = 'center';
        animElement.style.alignItems = 'center';
        animElement.style.fontSize = '24px';
        animElement.style.fontWeight = 'bold';
        animElement.style.color = 'white';
        animElement.style.zIndex = '999';
        animElement.style.pointerEvents = 'none'; // 不阻止点击
        
        // 将动画元素添加到body
        document.body.appendChild(animElement);
        
        let count = 0;
        const animValues = [];
        
        // 生成随机动画值
        for (let i = 0; i < 10; i++) {
            animValues.push(Math.floor(Math.random() * 6) + 1);
        }
        
        // 末尾添加最终值确保显示正确
        animValues.push(finalValue);
        
        const interval = setInterval(() => {
            if (count >= animValues.length) {
                clearInterval(interval);
                // 动画结束，移除元素
                animElement.remove();
                
                // 确认骰子值显示正确
                console.log(`确认diceResult显示值为${finalValue}`);
                diceResult.textContent = finalValue;
            } else {
                animElement.textContent = animValues[count];
                count++;
            }
        }, 100);
    }
    
    // 更新UI
    function updateUI() {
        if (!gameState) {
            console.log('updateUI: gameState不存在，退出');
            return;
        }
        
        // 更新当前玩家信息
        const currentPlayer = gameState.players[gameState.current_player];
        currentPlayerName.textContent = currentPlayer.name;
        currentPlayerName.style.color = PLAYER_COLORS[currentPlayer.id];
        
        // 设置当前玩家的ID
        gameState.current_turn = currentPlayer.id;
        
        // 调试输出当前骰子值
        console.log('updateUI中的骰子值:', gameState.dice_value, '类型:', typeof gameState.dice_value);
        
        // 确保当前楼层与游戏状态同步
        currentFloorValue = gameState.current_floor || 1;
        currentFloor.textContent = currentFloorValue;
        
        // 检查是否需要更新骰子显示
        if (gameState.dice_value === 0 || gameState.dice_value === undefined || gameState.dice_value === null) {
            console.log('重置骰子显示为0 (原值为:', diceResult.textContent, ')');
            diceResult.textContent = '0';
        } else if (parseInt(diceResult.textContent) !== gameState.dice_value) {
            console.log(`更新骰子显示从 ${diceResult.textContent} 到 ${gameState.dice_value}`);
            diceResult.textContent = gameState.dice_value;
        } else {
            console.log('骰子显示无需更新，当前值:', diceResult.textContent);
        }
        
        // 更新玩家列表
        updatePlayersList();
        
        // 根据游戏阶段设置UI状态
        if (gameState.selecting_start) {
            // 初始位置选择阶段
            showStatusMessage(`请为${currentPlayer.name}选择初始位置，点击棋盘上的有效格子放置`);
            
            // 禁用游戏按钮
            rollDiceBtn.disabled = true;
            rotateBtn.disabled = true;
            placeBtn.disabled = true;
            increaseDazeBtn.disabled = true;
            decreaseDazeBtn.disabled = true;
            endTurnBtn.disabled = true;
        } else {
            // 常规游戏阶段
            // 启用游戏按钮
            rollDiceBtn.disabled = false;
            rotateBtn.disabled = false;
            placeBtn.disabled = false;
            increaseDazeBtn.disabled = false;
            decreaseDazeBtn.disabled = false;
            endTurnBtn.disabled = false;
            
            // 根据是否已经掷骰子来显示提示
            if (gameState.dice_value > 0) {
                showStatusMessage(`${currentPlayer.name}掷出了${gameState.dice_value}点，请选择绿色高亮格子进行移动`);
            } else {
                showStatusMessage(`${currentPlayer.name}的回合，请掷骰子`);
            }
        }
        
        // 绘制游戏板
        drawBoard();
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
            
            // 显示玩家的位置信息和骰子值
            let posText = "未设置";
            if (player.position !== null && player.position !== undefined) {
                let x, y;
                if (Array.isArray(player.position)) {
                    [x, y] = player.position;
                    posText = `(${x},${y})`;
                } else if (typeof player.position === 'object' && player.position !== null) {
                    x = player.position[0];
                    y = player.position[1];
                    posText = `(${x},${y})`;
                } else if (typeof player.position === 'string') {
                    posText = player.position;
                }
            }
            
            statsSpan.textContent = `位置: ${posText} 楼层: ${player.floor} 迷惑: ${player.daze} 骰子值: ${player.dice_value || 0}`;
            
            playerItem.appendChild(nameContainer);
            playerItem.appendChild(statsSpan);
            playersContainer.appendChild(playerItem);
        });
    }
    
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

    // 获取鼠标在棋盘上的位置
    function getBoardPosition(e) {
        const rect = gameCanvas.getBoundingClientRect();
        const ACTUAL_BOARD_SIZE = 20;  // 使用实际的棋盘大小
        const offsetX = (gameCanvas.width - ACTUAL_BOARD_SIZE * TILE_SIZE) / 2;
        const offsetY = (gameCanvas.height - ACTUAL_BOARD_SIZE * TILE_SIZE) / 2;
        
        const x = Math.floor((e.clientX - rect.left - offsetX) / TILE_SIZE);
        const y = Math.floor((e.clientY - rect.top - offsetY) / TILE_SIZE);
        
        // 确保位置在棋盘内
        if (x >= 0 && x < ACTUAL_BOARD_SIZE && y >= 0 && y < ACTUAL_BOARD_SIZE) {
            return [x, y];
        }
        
        return null;
    }
    
    // 处理棋盘点击
    gameCanvas.addEventListener('click', (e) => {
        const position = getBoardPosition(e);
        if (!position) return;
        
        const [x, y] = position;
        
        if (gameState && gameState.selecting_start) {
            // 初始位置选择模式
            const currentPlayer = gameState.players[gameState.current_player];
            socket.emit('move_player', {
                position: position
            });
            showStatusMessage(`正在为玩家${currentPlayer.name}设置初始位置为(${x}, ${y})...`);
        } else if (gameState && gameState.players[gameState.current_player].dice_value > 0) {
            // 移动玩家模式 - 只有有剩余骰子值时才能移动
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
                    const manhattanDistance = Math.abs(x - currentX) + Math.abs(y - currentY);
                    
                    console.log('移动检查:', {
                        from: [currentX, currentY],
                        to: [x, y],
                        distance: manhattanDistance,
                        remaining_dice: currentPlayer.dice_value
                    });
                    
                    if (manhattanDistance === currentPlayer.dice_value) {
                        // 检查该格子是否有效（有路径）
                        const isValid = isValidTile(x, y);
                        if (isValid) {
                            // 检查该格子是否已被其他玩家占用
                            const isOccupied = isOccupiedTile(x, y);
                            if (!isOccupied) {
                                // 可以移动
                                console.log('发送移动请求:', {
                                    position: [x, y],
                                    distance: manhattanDistance
                                });
                                
                                socket.emit('move_player', {
                                    position: [x, y]
                                });
                                
                                // 更新本地状态
                                currentPlayer.dice_value = 0;
                                gameState.dice_value = 0;
                                gameState.moved = true;
                                selectedTile = position;
                                showStatusMessage(`移动到位置(${x}, ${y})`);
                                drawBoard();
                            } else {
                                showStatusMessage('该位置已被其他玩家占用', true);
                            }
                        } else {
                            showStatusMessage('无效的移动位置，该位置没有路径', true);
                        }
                    } else {
                        showStatusMessage(`移动距离必须等于骰子值${currentPlayer.dice_value}，当前距离为${manhattanDistance}`, true);
                    }
                }
            }
        } else {
            showStatusMessage('请先掷骰子', true);
        }
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
    
    // 掷骰子按钮点击事件 - 增加更多日志和错误捕获
    rollDiceBtn.addEventListener('click', () => {
        console.log('=== 点击掷骰子按钮 ===');
        console.log('当前游戏状态:', gameState);
        
        try {
            if (!gameState) {
                console.error('游戏状态未初始化，无法掷骰子');
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
            
            if (gameState.dice_value > 0) {
                showStatusMessage('已经掷过骰子，请先移动', true);
                return;
            }
            
            console.log('发送掷骰子请求');
            
            // 按钮点击后立即禁用，防止重复点击
            rollDiceBtn.disabled = true;
            
            // 显示掷骰子中的动画效果
            diceResult.textContent = '...';
            console.log('设置骰子显示为"..."，等待服务器响应');
            
            // 发送掷骰子请求
            console.log('发送 roll_dice 事件到服务器');
            socket.emit('roll_dice', {});
            showStatusMessage('掷骰子中...');
            
            // 添加请求超时处理
            setTimeout(() => {
                if (diceResult.textContent === '...') {
                    console.error('掷骰子请求超时!');
                    diceResult.textContent = '超时';
                    showStatusMessage('掷骰子请求超时，请重试', true);
                }
                // 2秒后重新启用按钮
                rollDiceBtn.disabled = false;
            }, 5000);
            
        } catch (error) {
            console.error('掷骰子按钮点击处理错误:', error);
            showStatusMessage('处理错误: ' + error.message, true);
            rollDiceBtn.disabled = false;
        }
    });

    // 向上按钮点击事件
    floorUpBtn.addEventListener('click', () => {
        console.log('点击向上按钮');
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
        console.log('点击向下按钮');
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
        console.log('点击旋转按钮');
        socket.emit('rotate_card');
        showStatusMessage('旋转卡片');
    });

    // 放置按钮点击事件
    placeBtn.addEventListener('click', () => {
        console.log('点击放置按钮');
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
        console.log('点击增加迷惑值按钮');
        socket.emit('change_daze', { change: 1 });
        showStatusMessage('增加迷惑值');
    });

    // 减少迷惑值按钮点击事件
    decreaseDazeBtn.addEventListener('click', () => {
        console.log('点击减少迷惑值按钮');
        socket.emit('change_daze', { change: -1 });
        showStatusMessage('减少迷惑值');
    });

    // 回合结束按钮
    endTurnBtn.addEventListener('click', () => {
        console.log('点击结束回合按钮');
        if (!gameState || gameState.selecting_start) {
            showStatusMessage('请先选择起始位置', true);
            return;
        }
        
        // 获取玩家ID，如果存储中有就使用，否则默认为0
        const storedPlayerId = localStorage.getItem('playerId');
        const playerId = parseInt(storedPlayerId || '0');
        
        console.log('检查回合: ', {
            当前玩家ID: gameState.current_player,
            当前玩家ID类型: typeof gameState.current_player,
            本地玩家ID: playerId,
            本地玩家ID原始值: storedPlayerId,
            localStorage状态: localStorage.length > 0 ? '有数据' : '空',
            玩家列表: gameState.players.map(p => `ID=${p.id}, 名称=${p.name}`)
        });
        
        // 重要：确保current_player和本地玩家ID类型匹配，统一使用整数进行比较
        const currentPlayerId = parseInt(gameState.current_player);
        
        console.log(`比较玩家ID: 当前玩家ID(${currentPlayerId}) vs 本地玩家ID(${playerId})`);
        
        // 如果当前玩家ID与本地存储不一致，先尝试同步
        if (currentPlayerId !== playerId) {
            console.warn(`玩家ID不匹配，尝试同步到服务器...`);
            // 更新本地存储
            localStorage.setItem('playerId', currentPlayerId.toString());
            // 同步到服务器
            socket.emit('join_game', {
                game_id: GAME_ID,
                player_id: currentPlayerId
            });
            
            // 显示同步提示，延迟后再自动点击结束回合按钮
            showStatusMessage('同步玩家ID中，请稍等...');
            
            // 一秒后重试
            setTimeout(() => {
                console.log('ID已同步，重新尝试结束回合');
                endTurnBtn.click();
            }, 1000);
            
            return;
        }
        
        if (gameState.dice_value > 0 && !gameState.moved) {
            showStatusMessage('掷骰子后必须移动', true);
            return;
        }
        
        console.log('发送end_turn事件到服务器');
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
        
        // 添加调试骰子按钮
        const debugDiceBtn = document.createElement('button');
        debugDiceBtn.id = 'debug-dice-btn';
        debugDiceBtn.textContent = '测试骰子(值=3)';
        debugDiceBtn.className = 'debug-btn';
        debugDiceBtn.style.backgroundColor = '#e91e63';
        debugDiceBtn.style.margin = '10px 0 10px 10px';
        debugDiceBtn.style.padding = '10px 20px';
        
        // 添加点击事件
        debugDiceBtn.addEventListener('click', () => {
            console.log('点击测试骰子按钮');
            
            // 手动设置骰子值
            const testDiceValue = 3;
            if (gameState) {
                gameState.dice_value = testDiceValue;
                gameState.moved = false;
                diceResult.textContent = testDiceValue;
                
                console.log('手动设置骰子值:', {
                    dice_value: gameState.dice_value,
                    moved: gameState.moved
                });
                
                // 显示移动提示
                const currentPlayer = gameState.players[gameState.current_player];
                showStatusMessage(`测试模式：${currentPlayer.name}掷出了${testDiceValue}点，请选择高亮显示的格子进行移动`);
                
                // 重绘棋盘以高亮显示可移动的格子
                drawBoard();
                
                // 添加移动提示
                addMoveTip();
            } else {
                showStatusMessage('游戏状态未初始化，无法测试', true);
            }
        });
        
        // 添加到控制面板
        gameControlPanel.appendChild(debugDiceBtn);
    }
}); 