const socket = io('http://localhost:5000');
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const scoreEl = document.getElementById('score');
const opponentScoreEl = document.getElementById('opponent-score');
const gameOverEl = document.getElementById('game-over');
const finalScoreEl = document.getElementById('final-score');
const resultTextEl = document.getElementById('result-text');
const title = document.getElementById('title');
const gameContainer = document.getElementById('game-container');
const controls = document.getElementById('controls');
const hint = document.getElementById('hint');
const menuScreen = document.getElementById('menu-screen');

let roomId = null;
let myPosition = null;
let isMultiplayer = false;
let isAIMode = false;
let isSpectator = false;
let opponentScore = 0;

function resizeCanvas() {
    if (isMultiplayer || isAIMode) {
        canvas.width = Math.min(window.innerWidth * 0.9, 900);
        canvas.height = Math.min(window.innerHeight * 0.75, 650);
    } else {
        canvas.width = Math.min(window.innerWidth * 0.9, 500);
        canvas.height = Math.min(window.innerHeight * 0.75, 700);
    }
}

resizeCanvas();
window.addEventListener('resize', resizeCanvas);

let isHidden = false;
let gameRunning = false;
let score = 0;
let aiScore = 0;
let animationId;

const car = {
    x: 175,
    y: 500,
    width: 50,
    height: 80,
    speed: 5,
    jumping: false,
    jumpHeight: 0,
    jumpSpeed: 0,
    gravity: 0.5
};

const aiCar = {
    x: 175,
    y: 500,
    width: 50,
    height: 80,
    lane: 1,
    jumping: false,
    jumpHeight: 0,
    jumpSpeed: 0,
    gravity: 0.5
};

const lanes = [100, 175, 250];
let currentLane = 1;
const obstacles = [];
const aiObstacles = [];
const obstacleSpeed = 5;
let obstacleTimer = 0;
let aiObstacleTimer = 0;

// 菜单事件
document.getElementById('single-mode-btn').addEventListener('click', () => {
    isMultiplayer = false;
    isAIMode = false;
    menuScreen.classList.add('hidden');
    resizeCanvas();
    startGame();
});

document.getElementById('ai-mode-btn').addEventListener('click', () => {
    isMultiplayer = false;
    isAIMode = true;
    menuScreen.classList.add('hidden');
    resizeCanvas();
    startGame();
});

document.getElementById('create-room-btn').addEventListener('click', () => {
    socket.emit('create_room', { game: 'racing' });
});

document.getElementById('join-room-btn').addEventListener('click', () => {
    document.getElementById('menu-panel').classList.add('hidden');
    document.getElementById('join-input').classList.remove('hidden');
});

document.getElementById('join-confirm-btn').addEventListener('click', () => {
    const inputRoomId = document.getElementById('room-id-input').value.trim();
    if (inputRoomId) {
        socket.emit('join_room', { room_id: inputRoomId, game: 'racing' });
    }
});

// Socket 事件
socket.on('room_created', (data) => {
    roomId = data.room_id;
    myPosition = data.position;
    isMultiplayer = true;
    document.getElementById('room-id-display').textContent = roomId;
    document.getElementById('room-info').classList.remove('hidden');
    document.getElementById('menu-panel').classList.add('hidden');
});

socket.on('room_joined', (data) => {
    roomId = data.room_id;
    myPosition = data.position;
    isMultiplayer = true;
    document.getElementById('room-id-display').textContent = roomId;
    document.getElementById('room-info').classList.remove('hidden');
    document.getElementById('join-input').classList.add('hidden');
});

socket.on('game_start', () => {
    menuScreen.classList.add('hidden');
    resizeCanvas();
    startGame();
});

socket.on('score_update', (data) => {
    if (data.position !== myPosition) {
        opponentScore = data.score;
        opponentScoreEl.textContent = `对手: ${Math.floor(opponentScore / 10)}`;
    }
});

socket.on('player_finished', (data) => {
    if (data.position !== myPosition && gameRunning) {
        opponentScore = data.score;
    }
});

socket.on('player_left', () => {
    alert('对手已离开');
    backToMenu();
});

socket.on('error', (data) => {
    alert(data.msg);
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        isHidden = !isHidden;
        [title, gameContainer, controls, hint, menuScreen].forEach(el => {
            el.classList.toggle('hidden', isHidden);
        });
    }
    
    if (!gameRunning || isSpectator) return;
    
    if (e.key === 'ArrowLeft' && currentLane > 0) {
        currentLane--;
        car.x = lanes[currentLane];
    }
    if (e.key === 'ArrowRight' && currentLane < 2) {
        currentLane++;
        car.x = lanes[currentLane];
    }
    if (e.key === ' ' && !car.jumping) {
        car.jumping = true;
        car.jumpSpeed = -12;
    }
});

function startGame() {
    gameRunning = true;
    score = 0;
    aiScore = 0;
    opponentScore = 0;
    obstacles.length = 0;
    aiObstacles.length = 0;
    car.x = lanes[1];
    car.y = 500;
    aiCar.x = lanes[1];
    aiCar.y = 500;
    aiCar.lane = 1;
    currentLane = 1;
    car.jumping = false;
    car.jumpHeight = 0;
    aiCar.jumping = false;
    aiCar.jumpHeight = 0;
    gameOverEl.classList.add('hidden');
    gameContainer.classList.remove('hidden');
    controls.classList.remove('hidden');
    
    if (isMultiplayer || isAIMode) {
        opponentScoreEl.classList.remove('hidden');
        opponentScoreEl.textContent = isAIMode ? 'AI: 0' : '对手: 0';
    }
    
    gameLoop();
}

function backToMenu() {
    gameContainer.classList.add('hidden');
    controls.classList.add('hidden');
    menuScreen.classList.remove('hidden');
    document.getElementById('menu-panel').classList.remove('hidden');
    document.getElementById('join-input').classList.add('hidden');
    document.getElementById('room-info').classList.add('hidden');
    opponentScoreEl.classList.add('hidden');
    isMultiplayer = false;
    isAIMode = false;
    isSpectator = false;
    roomId = null;
}

function gameLoop() {
    if (!gameRunning) return;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    if (isMultiplayer || isAIMode) {
        drawSplitScreen();
    } else {
        drawRoad(0, canvas.width);
        updateCar();
        drawCar(0);
        updateObstacles(obstacles);
        drawObstacles(obstacles, 0);
        checkCollision(car, obstacles);
    }
    
    score++;
    scoreEl.textContent = `得分: ${Math.floor(score / 10)}`;
    
    if (isAIMode) {
        aiScore++;
        opponentScoreEl.textContent = `AI: ${Math.floor(aiScore / 10)}`;
        updateAI();
    }
    
    if (isMultiplayer && !isAIMode && score % 30 === 0) {
        socket.emit('update_score', { room_id: roomId, score });
    }
    
    animationId = requestAnimationFrame(gameLoop);
}

function drawSplitScreen() {
    const halfWidth = canvas.width / 2;
    
    // 左侧玩家
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, halfWidth, canvas.height);
    ctx.clip();
    drawRoad(0, halfWidth);
    updateCar();
    drawCar(0);
    updateObstacles(obstacles);
    drawObstacles(obstacles, 0);
    checkCollision(car, obstacles);
    ctx.restore();
    
    // 分割线
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(halfWidth, 0);
    ctx.lineTo(halfWidth, canvas.height);
    ctx.stroke();
    
    // 右侧AI/对手
    ctx.save();
    ctx.beginPath();
    ctx.rect(halfWidth, 0, halfWidth, canvas.height);
    ctx.clip();
    drawRoad(halfWidth, halfWidth);
    updateAICar();
    drawAICar(halfWidth);
    updateObstacles(aiObstacles);
    drawObstacles(aiObstacles, halfWidth);
    checkCollision(aiCar, aiObstacles, true);
    ctx.restore();
}

function drawRoad(offsetX, width) {
    const gradient = ctx.createLinearGradient(offsetX, 0, offsetX, canvas.height);
    gradient.addColorStop(0, '#1a1a1a');
    gradient.addColorStop(1, '#0a0a0a');
    ctx.fillStyle = gradient;
    ctx.fillRect(offsetX, 0, width, canvas.height);
    
    const scale = width / 400;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
    ctx.lineWidth = 3 * scale;
    ctx.setLineDash([20 * scale, 20 * scale]);
    
    for (let i = 1; i < 3; i++) {
        ctx.beginPath();
        ctx.moveTo(offsetX + (lanes[i] - 12.5) * scale, 0);
        ctx.lineTo(offsetX + (lanes[i] - 12.5) * scale, canvas.height);
        ctx.stroke();
    }
    
    ctx.setLineDash([]);
}

function updateCar() {
    if (car.jumping) {
        car.jumpSpeed += car.gravity;
        car.jumpHeight += car.jumpSpeed;
        
        if (car.jumpHeight >= 0) {
            car.jumpHeight = 0;
            car.jumpSpeed = 0;
            car.jumping = false;
        }
    }
}

function updateAICar() {
    if (aiCar.jumping) {
        aiCar.jumpSpeed += aiCar.gravity;
        aiCar.jumpHeight += aiCar.jumpSpeed;
        
        if (aiCar.jumpHeight >= 0) {
            aiCar.jumpHeight = 0;
            aiCar.jumpSpeed = 0;
            aiCar.jumping = false;
        }
    }
}

function updateAI() {
    const nearestObstacle = aiObstacles.find(obs => obs.y > 300 && obs.y < 550);
    
    if (nearestObstacle) {
        const obsLane = lanes.indexOf(nearestObstacle.x);
        
        if (nearestObstacle.type === 'air' && !aiCar.jumping) {
            aiCar.jumping = true;
            aiCar.jumpSpeed = -12;
        } else if (nearestObstacle.type === 'ground' && obsLane === aiCar.lane) {
            if (aiCar.lane < 2 && Math.random() > 0.5) {
                aiCar.lane++;
            } else if (aiCar.lane > 0) {
                aiCar.lane--;
            }
            aiCar.x = lanes[aiCar.lane];
        }
    }
}

function drawCar(offsetX) {
    const y = car.y + car.jumpHeight;
    const scale = (isMultiplayer || isAIMode ? canvas.width / 2 : canvas.width) / 400;
    
    ctx.save();
    ctx.shadowBlur = 20 * scale;
    ctx.shadowColor = 'rgba(0, 150, 255, 0.8)';
    
    const gradient = ctx.createLinearGradient(
        offsetX + car.x * scale, y * scale,
        offsetX + car.x * scale, (y + car.height) * scale
    );
    gradient.addColorStop(0, '#00aaff');
    gradient.addColorStop(1, '#0066cc');
    ctx.fillStyle = gradient;
    ctx.fillRect(offsetX + car.x * scale, y * scale, car.width * scale, car.height * scale);
    
    ctx.fillStyle = '#003d7a';
    ctx.fillRect(offsetX + (car.x + 5) * scale, (y + 5) * scale, (car.width - 10) * scale, 25 * scale);
    
    ctx.fillStyle = 'rgba(200, 230, 255, 0.8)';
    ctx.fillRect(offsetX + (car.x + 8) * scale, (y + 8) * scale, (car.width - 16) * scale, 18 * scale);
    
    ctx.fillStyle = '#ffff00';
    ctx.shadowBlur = 10 * scale;
    ctx.shadowColor = '#ffff00';
    ctx.fillRect(offsetX + (car.x + 5) * scale, (y + car.height - 10) * scale, 12 * scale, 8 * scale);
    ctx.fillRect(offsetX + (car.x + car.width - 17) * scale, (y + car.height - 10) * scale, 12 * scale, 8 * scale);
    
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(offsetX + (car.x - 3) * scale, (y + 20) * scale, 8 * scale, 15 * scale);
    ctx.fillRect(offsetX + (car.x + car.width - 5) * scale, (y + 20) * scale, 8 * scale, 15 * scale);
    ctx.fillRect(offsetX + (car.x - 3) * scale, (y + 50) * scale, 8 * scale, 15 * scale);
    ctx.fillRect(offsetX + (car.x + car.width - 5) * scale, (y + 50) * scale, 8 * scale, 15 * scale);
    
    ctx.restore();
}

function drawAICar(offsetX) {
    const y = aiCar.y + aiCar.jumpHeight;
    const scale = canvas.width / 2 / 400;
    
    ctx.save();
    ctx.shadowBlur = 20 * scale;
    ctx.shadowColor = 'rgba(255, 100, 0, 0.8)';
    
    const gradient = ctx.createLinearGradient(
        offsetX + aiCar.x * scale, y * scale,
        offsetX + aiCar.x * scale, (y + aiCar.height) * scale
    );
    gradient.addColorStop(0, '#ff6600');
    gradient.addColorStop(1, '#cc3300');
    ctx.fillStyle = gradient;
    ctx.fillRect(offsetX + aiCar.x * scale, y * scale, aiCar.width * scale, aiCar.height * scale);
    
    ctx.fillStyle = '#990000';
    ctx.fillRect(offsetX + (aiCar.x + 5) * scale, (y + 5) * scale, (aiCar.width - 10) * scale, 25 * scale);
    
    ctx.fillStyle = 'rgba(255, 200, 150, 0.8)';
    ctx.fillRect(offsetX + (aiCar.x + 8) * scale, (y + 8) * scale, (aiCar.width - 16) * scale, 18 * scale);
    
    ctx.fillStyle = '#ffff00';
    ctx.shadowBlur = 10 * scale;
    ctx.shadowColor = '#ffff00';
    ctx.fillRect(offsetX + (aiCar.x + 5) * scale, (y + aiCar.height - 10) * scale, 12 * scale, 8 * scale);
    ctx.fillRect(offsetX + (aiCar.x + aiCar.width - 17) * scale, (y + aiCar.height - 10) * scale, 12 * scale, 8 * scale);
    
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(offsetX + (aiCar.x - 3) * scale, (y + 20) * scale, 8 * scale, 15 * scale);
    ctx.fillRect(offsetX + (aiCar.x + aiCar.width - 5) * scale, (y + 20) * scale, 8 * scale, 15 * scale);
    ctx.fillRect(offsetX + (aiCar.x - 3) * scale, (y + 50) * scale, 8 * scale, 15 * scale);
    ctx.fillRect(offsetX + (aiCar.x + aiCar.width - 5) * scale, (y + 50) * scale, 8 * scale, 15 * scale);
    
    ctx.restore();
}

function updateObstacles(obstacleArray) {
    if (obstacleArray === obstacles) {
        obstacleTimer++;
        if (obstacleTimer > 60) {
            const lane = Math.floor(Math.random() * 3);
            const type = Math.random() > 0.5 ? 'ground' : 'air';
            obstacleArray.push({
                x: lanes[lane],
                y: type === 'ground' ? -80 : -120,
                width: 50,
                height: type === 'ground' ? 80 : 40,
                type: type
            });
            obstacleTimer = 0;
        }
    } else {
        aiObstacleTimer++;
        if (aiObstacleTimer > 60) {
            const lane = Math.floor(Math.random() * 3);
            const type = Math.random() > 0.5 ? 'ground' : 'air';
            obstacleArray.push({
                x: lanes[lane],
                y: type === 'ground' ? -80 : -120,
                width: 50,
                height: type === 'ground' ? 80 : 40,
                type: type
            });
            aiObstacleTimer = 0;
        }
    }
    
    for (let i = obstacleArray.length - 1; i >= 0; i--) {
        obstacleArray[i].y += obstacleSpeed;
        
        if (obstacleArray[i].y > canvas.height) {
            obstacleArray.splice(i, 1);
        }
    }
}

function drawObstacles(obstacleArray, offsetX) {
    const scale = (isMultiplayer || isAIMode ? canvas.width / 2 : canvas.width) / 400;
    obstacleArray.forEach(obs => {
        const obsY = obs.type === 'ground' ? obs.y : obs.y + 100;
        
        ctx.save();
        ctx.shadowBlur = 15 * scale;
        
        if (obs.type === 'ground') {
            ctx.shadowColor = 'rgba(255, 68, 68, 0.6)';
            const gradient = ctx.createLinearGradient(
                offsetX + obs.x * scale, obsY * scale,
                offsetX + obs.x * scale, (obsY + obs.height) * scale
            );
            gradient.addColorStop(0, '#ff6666');
            gradient.addColorStop(1, '#cc0000');
            ctx.fillStyle = gradient;
        } else {
            ctx.shadowColor = 'rgba(255, 170, 0, 0.6)';
            const gradient = ctx.createLinearGradient(
                offsetX + obs.x * scale, obsY * scale,
                offsetX + obs.x * scale, (obsY + obs.height) * scale
            );
            gradient.addColorStop(0, '#ffcc00');
            gradient.addColorStop(1, '#ff8800');
            ctx.fillStyle = gradient;
        }
        
        ctx.fillRect(offsetX + obs.x * scale, obsY * scale, obs.width * scale, obs.height * scale);
        ctx.restore();
    });
}

function checkCollision(carObj, obstacleArray, isAI = false) {
    const carY = carObj.y + carObj.jumpHeight;
    
    obstacleArray.forEach(obs => {
        const obsY = obs.type === 'ground' ? obs.y : obs.y + 100;
        
        if (carObj.x < obs.x + obs.width &&
            carObj.x + carObj.width > obs.x &&
            carY < obsY + obs.height &&
            carY + carObj.height > obsY) {
            if (isAI) {
                gameOverAI();
            } else {
                gameOver();
            }
        }
    });
}

function gameOver() {
    gameRunning = false;
    cancelAnimationFrame(animationId);
    finalScoreEl.textContent = Math.floor(score / 10);
    
    if (isMultiplayer && !isAIMode) {
        socket.emit('game_over', { room_id: roomId, score });
        
        if (Math.floor(score / 10) > Math.floor(opponentScore / 10)) {
            resultTextEl.textContent = '你赢了！';
        } else if (Math.floor(score / 10) < Math.floor(opponentScore / 10)) {
            resultTextEl.textContent = '对手获胜';
        } else {
            resultTextEl.textContent = '平局';
        }
    } else if (isAIMode) {
        if (Math.floor(score / 10) > Math.floor(aiScore / 10)) {
            resultTextEl.textContent = '你赢了！';
        } else {
            resultTextEl.textContent = 'AI获胜';
        }
    } else {
        resultTextEl.textContent = '';
    }
    
    gameOverEl.classList.remove('hidden');
}

function gameOverAI() {
    if (!isAIMode) return;
    
    gameRunning = false;
    cancelAnimationFrame(animationId);
    finalScoreEl.textContent = Math.floor(score / 10);
    resultTextEl.textContent = '你赢了！';
    gameOverEl.classList.remove('hidden');
}
