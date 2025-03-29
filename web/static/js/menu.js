// 菜单页面逻辑
document.addEventListener('DOMContentLoaded', () => {
    // 初始化变量
    let playerCount = 2;
    const playerNames = ['', '', '', '', '', ''];
    let activeInput = -1;
    
    // 获取DOM元素
    const playerCountDisplay = document.getElementById('player-count-display');
    const decreasePlayerBtn = document.getElementById('decrease-player');
    const increasePlayerBtn = document.getElementById('increase-player');
    const playerInputsContainer = document.getElementById('player-inputs-container');
    const startGameBtn = document.getElementById('start-game-btn');
    
    // 更新玩家输入框
    function updatePlayerInputs() {
        playerInputsContainer.innerHTML = '';
        
        for (let i = 0; i < playerCount; i++) {
            const playerInput = document.createElement('div');
            playerInput.className = 'player-input';
            
            const label = document.createElement('label');
            label.textContent = `玩家 ${i + 1}:`;
            
            const input = document.createElement('input');
            input.type = 'text';
            input.value = playerNames[i];
            input.dataset.index = i;
            
            // 添加输入事件
            input.addEventListener('input', (e) => {
                const index = parseInt(e.target.dataset.index);
                playerNames[index] = e.target.value;
            });
            
            // 添加焦点事件
            input.addEventListener('focus', (e) => {
                activeInput = parseInt(e.target.dataset.index);
            });
            
            input.addEventListener('blur', () => {
                activeInput = -1;
            });
            
            playerInput.appendChild(label);
            playerInput.appendChild(input);
            playerInputsContainer.appendChild(playerInput);
        }
    }
    
    // 减少玩家数量
    decreasePlayerBtn.addEventListener('click', () => {
        if (playerCount > 2) {
            playerCount--;
            playerCountDisplay.textContent = playerCount;
            updatePlayerInputs();
        }
    });
    
    // 增加玩家数量
    increasePlayerBtn.addEventListener('click', () => {
        if (playerCount < 6) {
            playerCount++;
            playerCountDisplay.textContent = playerCount;
            updatePlayerInputs();
        }
    });
    
    // 开始游戏
    startGameBtn.addEventListener('click', () => {
        // 验证玩家名称，如果为空则使用默认名称
        for (let i = 0; i < playerCount; i++) {
            if (!playerNames[i]) {
                playerNames[i] = `玩家${i+1}`;
            }
        }
        
        // 发送创建游戏请求
        fetch('/api/create_game', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                num_players: playerCount,
                player_names: playerNames.slice(0, playerCount)
            })
        })
        .then(response => response.json())
        .then(data => {
            // 重定向到游戏页面
            window.location.href = `/game/${data.game_id}`;
        })
        .catch(error => {
            console.error('创建游戏失败:', error);
            alert('创建游戏失败，请重试');
        });
    });
    
    // 初始化页面
    updatePlayerInputs();
}); 