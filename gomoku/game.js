const SIZE = 15;
const board = Array.from({ length: SIZE }, () => Array(SIZE).fill(0));
let current = 1;
let isOver = false;
let moves = [];
let myColor = 0;
let roomId = '';
let isSinglePlayer = false;
let isHidden = false;

const gameBoard = document.getElementById('game-board');
const gameInfo = document.getElementById('game-info');
const title = document.getElementById('title');
const hint = document.getElementById('hint');

gameBoard.style.width = `${SIZE * Math.min(40, window.innerWidth * 0.06)}px`;
gameBoard.style.height = `${SIZE * Math.min(40, window.innerWidth * 0.06)}px`;

const socket = io('http://192.168.132.58:5000');

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        isHidden = !isHidden;
        if (isHidden) {
            gameBoard.classList.add('hidden');
            gameInfo.classList.add('hidden');
            title.classList.add('hidden');
            hint.classList.add('hidden');
        } else {
            gameBoard.classList.remove('hidden');
            gameInfo.classList.remove('hidden');
            title.classList.remove('hidden');
            hint.classList.remove('hidden');
        }
    }
});

socket.on('room_created', (data) => {
    roomId = data.room_id;
    myColor = data.color;
    gameInfo.innerText = `房间号: ${roomId} (等待对手加入...)`;
});

socket.on('room_joined', (data) => {
    roomId = data.room_id;
    myColor = data.color;
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

function startSinglePlayer() {
    isSinglePlayer = true;
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
}

drawBoard();
gameInfo.innerHTML = `
    <button onclick="startSinglePlayer()">单人模式</button>
    <button onclick="createRoom()">创建房间</button>
    <button onclick="joinRoom()">加入房间</button>
    <button onclick="spectateRoom()">观战</button>
`;

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
        gameInfo.innerHTML = isOver ? '' : `
            <span>当前轮到：${current === 1 ? '黑子(你)' : '白子(AI)'}</span>
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
    
    let bestScore = -Infinity;
    let bestMove = null;
    
    for (let r = 0; r < SIZE; r++) {
        for (let c = 0; c < SIZE; c++) {
            if (board[r][c] === 0) {
                let score = evaluatePosition(r, c, 2);
                score += evaluatePosition(r, c, 1) * 0.9;
                
                if (score > bestScore) {
                    bestScore = score;
                    bestMove = { r, c };
                }
            }
        }
    }
    
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
