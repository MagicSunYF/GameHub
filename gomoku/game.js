const SIZE = 15;
const board = Array.from({ length: SIZE }, () => Array(SIZE).fill(0));
let current = 1;
let isOver = false;
let moves = [];
let myColor = 0;
let roomId = '';
let isSinglePlayer = false;
let isHidden = false;
let aiDifficulty = 'medium'; // 'easy', 'medium', 'hard'

const gameBoard = document.getElementById('game-board');
const gameInfo = document.getElementById('game-info');
const title = document.getElementById('title');
const hint = document.getElementById('hint');

gameBoard.style.width = `${SIZE * Math.min(40, window.innerWidth * 0.06)}px`;
gameBoard.style.height = `${SIZE * Math.min(40, window.innerWidth * 0.06)}px`;

const socket = io(window.location.origin);

// 初始化心跳管理器
const heartbeat = new HeartbeatManager(socket, {
    pingInterval: 30000,
    pongTimeout: 5000,
    maxReconnectAttempts: 3,
    onConnectionChange: (status, attempts) => {
        updateConnectionStatus(status, attempts);
    },
    stateRecovery: {
        save: () => {
            // 保存游戏状态
            return {
                board: board.map(row => [...row]),
                current,
                isOver,
                moves: [...moves],
                myColor,
                roomId,
                isSinglePlayer,
                aiDifficulty
            };
        },
        restore: (state) => {
            // 恢复游戏状态
            if (!state) return;
            
            for (let r = 0; r < SIZE; r++) {
                for (let c = 0; c < SIZE; c++) {
                    board[r][c] = state.board[r][c];
                }
            }
            current = state.current;
            isOver = state.isOver;
            moves = [...state.moves];
            myColor = state.myColor;
            roomId = state.roomId;
            isSinglePlayer = state.isSinglePlayer;
            aiDifficulty = state.aiDifficulty || 'medium';
            
            // 重新加入房间
            if (roomId && !isSinglePlayer) {
                socket.emit('rejoin_room', { room_id: roomId });
            }
            
            drawBoard();
            showInfo();
            menuPanel.classList.add('hidden');
        }
    }
});

function updateConnectionStatus(status, attempts) {
    if (status === 'connected') {
        console.log('已连接到服务器');
    } else if (status === 'reconnecting') {
        console.log(`正在重连... (尝试 ${attempts})`);
    } else if (status === 'disconnected') {
        console.log('连接已断开');
    }
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        isHidden = !isHidden;
        // 切换所有主要元素的隐藏状态
        [gameBoard, gameInfo, title, hint].forEach(el => {
            el.classList.toggle('hidden', isHidden);
        });
        // 菜单面板只在未开始游戏时显示
        if (!roomId && !isSinglePlayer) {
            menuPanel.classList.toggle('hidden', isHidden);
        }
    }
});

socket.on('room_created', (data) => {
    roomId = data.room_id;
    myColor = data.color;
    gameInfo.innerText = `房间号: ${roomId} (等待对手加入...)`;
    menuPanel.classList.add('hidden');
});

socket.on('room_joined', (data) => {
    roomId = data.room_id;
    myColor = data.color;
    menuPanel.classList.add('hidden');
});

socket.on('spectator_joined', (data) => {
    roomId = data.room_id;
    myColor = 0;
    for (let r = 0; r < SIZE; r++) {
        for (let c = 0; c < SIZE; c++) {
            board[r][c] = data.board[r][c];
        }
    }
    current = data.current;
    drawBoard();
    showInfo();
    menuPanel.classList.add('hidden');
});

socket.on('game_start', () => {
    drawBoard();
    showInfo();
    showStartEffect();
});

socket.on('move_made', (data) => {
    board[data.row][data.col] = data.color;
    current = 3 - data.color;
    drawBoard();
    showPieceEffect(data.row, data.col);
    showInfo();
});

socket.on('game_over', (data) => {
    isOver = true;
    drawBoard();
    gameInfo.innerText = `玩家 ${data.winner === 1 ? '黑子' : '白子'} 获胜！`;
    showWinEffect();
});

socket.on('player_left', () => {
    gameInfo.innerText = '对手已离开';
    isOver = true;
});

socket.on('new_comment', (data) => {
    showBarrage(data.comment);
});

socket.on('error', (data) => {
    alert(data.msg);
});

function createRoom() {
    socket.emit('create_room');
}

function joinRoom() {
    const id = prompt('请输入房间号:');
    if (id) {
        socket.emit('join_room', { room_id: id });
    }
}

function spectateRoom() {
    const id = prompt('请输入房间号:');
    if (id) {
        socket.emit('join_room', { room_id: id, spectator: true });
    }
}

function startSinglePlayer(difficulty = 'medium') {
    isSinglePlayer = true;
    aiDifficulty = difficulty;
    myColor = 1;
    current = 1;
    isOver = false;
    for (let r = 0; r < SIZE; r++) {
        for (let c = 0; c < SIZE; c++) {
            board[r][c] = 0;
        }
    }
    moves = [];
    drawBoard();
    showInfo();
    showStartEffect();
    menuPanel.classList.add('hidden');
}

function showDifficultyMenu() {
    const difficultyPanel = document.getElementById('difficulty-panel');
    if (difficultyPanel) {
        difficultyPanel.classList.remove('hidden');
        menuPanel.classList.add('hidden');
    }
}

function selectDifficulty(difficulty) {
    const difficultyPanel = document.getElementById('difficulty-panel');
    if (difficultyPanel) {
        difficultyPanel.classList.add('hidden');
    }
    startSinglePlayer(difficulty);
}

drawBoard();
const menuPanel = document.getElementById('menu-panel');

function drawBoard() {
    gameBoard.innerHTML = '';
    for (let r = 0; r < SIZE; r++) {
        for (let c = 0; c < SIZE; c++) {
            const cell = document.createElement('div');
            cell.className = 'cell';
            cell.dataset.row = r;
            cell.dataset.col = c;
            if (board[r][c] === 1) {
                const piece = document.createElement('div');
                piece.className = 'piece-black';
                cell.appendChild(piece);
            } else if (board[r][c] === 2) {
                const piece = document.createElement('div');
                piece.className = 'piece-white';
                cell.appendChild(piece);
            }
            cell.onclick = onCellClick;
            gameBoard.appendChild(cell);
        }
    }
}

function onCellClick(e) {
    if (isOver) return;
    
    if (isSinglePlayer) {
        if (current !== myColor) return;
        const r = +this.dataset.row;
        const c = +this.dataset.col;
        if (board[r][c] !== 0) return;
        
        board[r][c] = current;
        moves.push({ row: r, col: c, color: current === 1 ? 'black' : 'white' });
        drawBoard();
        showPieceEffect(r, c);
        
        if (checkWin(r, c, current)) {
            isOver = true;
            gameInfo.innerText = `玩家 ${current === 1 ? '黑子' : '白子'} 获胜！`;
            showWinEffect();
            return;
        }
        
        current = 3 - current;
        showInfo();
        
        setTimeout(() => aiMove(), 500);
        return;
    }
    
    if (myColor === 0 || current !== myColor) return;
    const r = +this.dataset.row;
    const c = +this.dataset.col;
    if (board[r][c] !== 0) return;
    socket.emit('make_move', { room_id: roomId, row: r, col: c });
}

function showInfo() {
    if (isSinglePlayer) {
        const difficultyText = {
            'easy': '简单',
            'medium': '中等',
            'hard': '困难'
        }[aiDifficulty] || '中等';
        
        gameInfo.innerHTML = isOver ? '' : `
            <span>当前轮到：${current === 1 ? '黑子(你)' : '白子(AI)'} | 难度：${difficultyText}</span>
        `;
        return;
    }
    if (myColor === 0) {
        gameInfo.innerHTML = `
            <span>观战模式</span>
            <button onclick="sendComment()">发送弹幕</button>
        `;
        return;
    }
    const turnText = current === myColor ? '你的回合' : '对手回合';
    gameInfo.innerHTML = isOver ? '' : `
        <span>你是${myColor === 1 ? '黑子' : '白子'} | ${turnText}</span>
        ${roomId ? '<button onclick="sendComment()">发送弹幕</button>' : ''}
    `;
}

function checkWin(r, c, color) {
    const directions = [
        [0, 1], [1, 0], [1, 1], [1, -1]
    ];
    for (const [dr, dc] of directions) {
        let cnt = 1;
        for (let i = 1; i < 5; i++) {
            const nr = r + dr * i, nc = c + dc * i;
            if (nr >= 0 && nc >= 0 && nr < SIZE && nc < SIZE && board[nr][nc] === color) cnt++; else break;
        }
        for (let i = 1; i < 5; i++) {
            const nr = r - dr * i, nc = c - dc * i;
            if (nr >= 0 && nc >= 0 && nr < SIZE && nc < SIZE && board[nr][nc] === color) cnt++; else break;
        }
        if (cnt >= 5) return true;
    }
    return false;
}

function aiMove() {
    if (isOver) return;
    
    const startTime = performance.now();
    let bestMove = null;
    
    // 根据难度选择策略
    if (aiDifficulty === 'easy') {
        bestMove = getEasyMove();
    } else if (aiDifficulty === 'medium') {
        bestMove = getMediumMove();
    } else {
        bestMove = getHardMove();
    }
    
    // 优化响应时间：确保AI至少思考200ms，最多500ms
    const elapsed = performance.now() - startTime;
    const delay = Math.max(200, Math.min(500, 300 + Math.random() * 200));
    const waitTime = Math.max(0, delay - elapsed);
    
    setTimeout(() => {
        if (bestMove) {
            board[bestMove.r][bestMove.c] = 2;
            moves.push({ row: bestMove.r, col: bestMove.c, color: 'white' });
            drawBoard();
            showPieceEffect(bestMove.r, bestMove.c);
            
            if (checkWin(bestMove.r, bestMove.c, 2)) {
                isOver = true;
                gameInfo.innerText = 'AI 获胜！';
                showWinEffect();
                return;
            }
            
            current = 1;
            showInfo();
        }
    }, waitTime);
}

// 简单难度：随机选择附近的位置
function getEasyMove() {
    const candidates = [];
    
    // 找到所有已有棋子附近的空位
    for (let r = 0; r < SIZE; r++) {
        for (let c = 0; c < SIZE; c++) {
            if (board[r][c] === 0 && hasNeighbor(r, c, 2)) {
                candidates.push({ r, c });
            }
        }
    }
    
    // 如果没有附近的位置，随机选择
    if (candidates.length === 0) {
        for (let r = 0; r < SIZE; r++) {
            for (let c = 0; c < SIZE; c++) {
                if (board[r][c] === 0) {
                    candidates.push({ r, c });
                }
            }
        }
    }
    
    return candidates.length > 0 ? candidates[Math.floor(Math.random() * candidates.length)] : null;
}

// 中等难度：基础评估函数
function getMediumMove() {
    let bestScore = -Infinity;
    let bestMove = null;
    
    for (let r = 0; r < SIZE; r++) {
        for (let c = 0; c < SIZE; c++) {
            if (board[r][c] === 0 && hasNeighbor(r, c, 2)) {
                let score = evaluatePosition(r, c, 2) * 1.0;
                score += evaluatePosition(r, c, 1) * 0.9;
                
                if (score > bestScore) {
                    bestScore = score;
                    bestMove = { r, c };
                }
            }
        }
    }
    
    return bestMove || getEasyMove();
}

// 困难难度：深度搜索和高级评估
function getHardMove() {
    let bestScore = -Infinity;
    let bestMove = null;
    
    // 优先检查必胜和必防
    for (let r = 0; r < SIZE; r++) {
        for (let c = 0; c < SIZE; c++) {
            if (board[r][c] === 0) {
                // 检查AI是否能赢
                board[r][c] = 2;
                if (checkWin(r, c, 2)) {
                    board[r][c] = 0;
                    return { r, c };
                }
                board[r][c] = 0;
                
                // 检查是否需要防守
                board[r][c] = 1;
                if (checkWin(r, c, 1)) {
                    board[r][c] = 0;
                    return { r, c };
                }
                board[r][c] = 0;
            }
        }
    }
    
    // 高级评估：考虑多个方向和模式
    for (let r = 0; r < SIZE; r++) {
        for (let c = 0; c < SIZE; c++) {
            if (board[r][c] === 0 && hasNeighbor(r, c, 2)) {
                let score = evaluatePositionAdvanced(r, c, 2) * 1.1;
                score += evaluatePositionAdvanced(r, c, 1) * 1.0;
                
                // 中心位置加分
                const centerDist = Math.abs(r - 7) + Math.abs(c - 7);
                score += (14 - centerDist) * 2;
                
                if (score > bestScore) {
                    bestScore = score;
                    bestMove = { r, c };
                }
            }
        }
    }
    
    return bestMove || getMediumMove();
}

// 检查是否有邻居
function hasNeighbor(r, c, range = 2) {
    for (let dr = -range; dr <= range; dr++) {
        for (let dc = -range; dc <= range; dc++) {
            if (dr === 0 && dc === 0) continue;
            const nr = r + dr, nc = c + dc;
            if (nr >= 0 && nc >= 0 && nr < SIZE && nc < SIZE && board[nr][nc] !== 0) {
                return true;
            }
        }
    }
    return false;
}

function evaluatePosition(r, c, color) {
    let score = 0;
    const directions = [[0, 1], [1, 0], [1, 1], [1, -1]];
    
    for (const [dr, dc] of directions) {
        let count = 1;
        let empty = 0;
        
        for (let i = 1; i < 5; i++) {
            const nr = r + dr * i, nc = c + dc * i;
            if (nr < 0 || nc < 0 || nr >= SIZE || nc >= SIZE) break;
            if (board[nr][nc] === color) count++;
            else if (board[nr][nc] === 0) { empty++; break; }
            else break;
        }
        
        for (let i = 1; i < 5; i++) {
            const nr = r - dr * i, nc = c - dc * i;
            if (nr < 0 || nc < 0 || nr >= SIZE || nc >= SIZE) break;
            if (board[nr][nc] === color) count++;
            else if (board[nr][nc] === 0) { empty++; break; }
            else break;
        }
        
        if (count >= 5) score += 100000;
        else if (count === 4 && empty > 0) score += 10000;
        else if (count === 3 && empty > 0) score += 1000;
        else if (count === 2 && empty > 0) score += 100;
    }
    
    return score;
}

// 高级评估函数：考虑更多模式
function evaluatePositionAdvanced(r, c, color) {
    let score = 0;
    const directions = [[0, 1], [1, 0], [1, 1], [1, -1]];
    
    for (const [dr, dc] of directions) {
        const pattern = getPattern(r, c, dr, dc, color);
        score += evaluatePattern(pattern);
    }
    
    return score;
}

// 获取某个方向的模式
function getPattern(r, c, dr, dc, color) {
    const pattern = { count: 1, empty: 0, blocked: 0 };
    
    // 正方向
    for (let i = 1; i < 5; i++) {
        const nr = r + dr * i, nc = c + dc * i;
        if (nr < 0 || nc < 0 || nr >= SIZE || nc >= SIZE) {
            pattern.blocked++;
            break;
        }
        if (board[nr][nc] === color) {
            pattern.count++;
        } else if (board[nr][nc] === 0) {
            pattern.empty++;
            break;
        } else {
            pattern.blocked++;
            break;
        }
    }
    
    // 反方向
    for (let i = 1; i < 5; i++) {
        const nr = r - dr * i, nc = c - dc * i;
        if (nr < 0 || nc < 0 || nr >= SIZE || nc >= SIZE) {
            pattern.blocked++;
            break;
        }
        if (board[nr][nc] === color) {
            pattern.count++;
        } else if (board[nr][nc] === 0) {
            pattern.empty++;
            break;
        } else {
            pattern.blocked++;
            break;
        }
    }
    
    return pattern;
}

// 评估模式得分
function evaluatePattern(pattern) {
    const { count, empty, blocked } = pattern;
    
    // 五连
    if (count >= 5) return 100000;
    
    // 活四（两端都空）
    if (count === 4 && blocked === 0) return 50000;
    
    // 冲四（一端被堵）
    if (count === 4 && blocked === 1) return 10000;
    
    // 活三
    if (count === 3 && blocked === 0 && empty >= 2) return 5000;
    
    // 眠三
    if (count === 3 && blocked === 1 && empty >= 1) return 1000;
    
    // 活二
    if (count === 2 && blocked === 0 && empty >= 2) return 500;
    
    // 眠二
    if (count === 2 && blocked === 1 && empty >= 1) return 100;
    
    return 10;
}

function saveGameRecord(winner) {
    fetch('http://localhost:5000/save_game', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ moves, winner })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'ok') {
            console.log('本局记录已保存到服务器！');
        } else {
            alert('保存对局记录失败：' + data.reason);
        }
    })
    .catch(err => {
        alert('保存对局记录失败: ' + err);
    });
}

function showPieceEffect(r, c) {
    const cells = document.querySelectorAll('.cell');
    const index = r * SIZE + c;
    const cell = cells[index];
    cell.classList.add('piece-drop');
    setTimeout(() => cell.classList.remove('piece-drop'), 800);
    
    const ripple = document.createElement('div');
    ripple.className = 'water-ripple';
    ripple.style.left = (c * 40 + 30) + 'px';
    ripple.style.top = (r * 40 + 30) + 'px';
    gameBoard.appendChild(ripple);
    setTimeout(() => ripple.remove(), 1000);
}

function showStartEffect() {
    const overlay = document.createElement('div');
    overlay.className = 'start-overlay';
    overlay.innerText = '对战开始！';
    document.body.appendChild(overlay);
    setTimeout(() => overlay.remove(), 2000);
}

function showWinEffect() {
    const overlay = document.createElement('div');
    overlay.className = 'win-overlay';
    overlay.innerHTML = `
        <div class="win-title">Victory</div>
        <div class="win-subtitle">绝杀！</div>
    `;
    document.body.appendChild(overlay);
    
    const allPieces = document.querySelectorAll('.piece-black, .piece-white');
    allPieces.forEach((piece, i) => {
        setTimeout(() => {
            piece.classList.add('piece-shake');
            setTimeout(() => piece.classList.remove('piece-shake'), 500);
        }, i * 20);
    });
    
    document.addEventListener('keydown', function hideWin(e) {
        if (e.key === 'Escape') {
            overlay.classList.add('hidden');
            document.removeEventListener('keydown', hideWin);
        }
    });
    
    setTimeout(() => overlay.remove(), 3000);
}

function showBarrage(text) {
    const barrage = document.createElement('div');
    barrage.className = 'barrage';
    barrage.innerText = text;
    barrage.style.top = Math.random() * 60 + 20 + '%';
    document.body.appendChild(barrage);
    setTimeout(() => barrage.remove(), 5000);
}

function sendComment() {
    if (!roomId) return;
    const comment = prompt('输入弹幕:');
    if (comment) {
        socket.emit('send_comment', { room_id: roomId, comment });
    }
}
