const socket = io(window.location.origin);

// 连接状态更新函数
function updateConnectionStatus(status, attempts) {
    if (status === 'connected') {
        console.log('已连接到服务器');
    } else if (status === 'reconnecting') {
        console.log(`正在重连... (尝试 ${attempts})`);
    } else if (status === 'disconnected') {
        console.log('连接已断开');
    }
}

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
            return {
                roomId,
                myPosition,
                isMultiplayer,
                isAIMode,
                isSpectator,
                opponentScore,
                score,
                gameRunning
            };
        },
        restore: (state) => {
            if (!state) return;
            
            roomId = state.roomId;
            myPosition = state.myPosition;
            isMultiplayer = state.isMultiplayer;
            isAIMode = state.isAIMode;
            isSpectator = state.isSpectator;
            opponentScore = state.opponentScore;
            score = state.score;
            
            if (roomId && !isAIMode) {
                socket.emit('rejoin_room', { room_id: roomId });
            }
            
            if (state.gameRunning) {
                menuScreen.classList.add('hidden');
                resizeCanvas();
                // 游戏会在重连后自然恢复
            }
        }
    }
});

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
    gravity: 0.8,  // 优化重力值，使跳跃更自然
    maxJumpSpeed: -15  // 最大跳跃速度
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
    gravity: 0.8,
    maxJumpSpeed: -15
};

const lanes = [100, 175, 250];
let currentLane = 1;
const obstacles = [];
const aiObstacles = [];
let baseObstacleSpeed = 5;  // 基础障碍物速度
let currentObstacleSpeed = 5;  // 当前障碍物速度（会随时间增加）
let obstacleTimer = 0;
let aiObstacleTimer = 0;
let speedIncreaseTimer = 0;  // 速度增加计时器
const SPEED_INCREASE_INTERVAL = 600;  // 每600帧（约10秒）增加速度
const MAX_SPEED = 12;  // 最大速度限制
let difficultyLevel = 1;  // 难度等级（1-5）
let obstacleSpawnInterval = 60;  // 障碍物生成间隔（帧数）

// 障碍物类型定义（多样化）
const OBSTACLE_TYPES = {
    GROUND: { type: 'ground', height: 80, yOffset: -80, color: ['#ff6666', '#cc0000'] },
    AIR: { type: 'air', height: 40, yOffset: -120, color: ['#ffcc00', '#ff8800'] },
    TALL: { type: 'tall', height: 120, yOffset: -120, color: ['#ff3333', '#990000'] },
    WIDE: { type: 'wide', height: 60, yOffset: -60, width: 75, color: ['#ff9966', '#cc6600'] },
    MOVING: { type: 'moving', height: 80, yOffset: -80, color: ['#9966ff', '#6633cc'], speed: 2 }
};

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
        // 切换所有主要元素的隐藏状态
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
        car.jumpSpeed = car.maxJumpSpeed;  // 使用最大跳跃速度
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
    currentObstacleSpeed = baseObstacleSpeed;  // 重置速度
    speedIncreaseTimer = 0;  // 重置速度增加计时器
    difficultyLevel = 1;  // 重置难度等级
    obstacleSpawnInterval = 60;  // 重置生成间隔
    gameOverEl.classList.add('hidden');
    menuScreen.classList.add('hidden');
    title.classList.add('hidden');
    hint.classList.add('hidden');
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
    title.classList.remove('hidden');
    hint.classList.remove('hidden');
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
    
    // 难度递增机制：速度增加 + 生成频率增加 + 难度等级提升（需求14.6）
    speedIncreaseTimer++;
    if (speedIncreaseTimer >= SPEED_INCREASE_INTERVAL) {
        // 增加速度
        if (currentObstacleSpeed < MAX_SPEED) {
            currentObstacleSpeed += 0.5;
        }
        
        // 增加难度等级（每10秒提升一级，最高5级）
        if (difficultyLevel < 5) {
            difficultyLevel++;
        }
        
        // 减少生成间隔（增加障碍物密度）
        if (obstacleSpawnInterval > 30) {
            obstacleSpawnInterval -= 5;
        }
        
        speedIncreaseTimer = 0;
    }
    
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
        car.jumpSpeed += car.gravity;  // 应用重力加速度
        car.jumpHeight += car.jumpSpeed;
        
        // 跳跃完成，回到地面
        if (car.jumpHeight >= 0) {
            car.jumpHeight = 0;
            car.jumpSpeed = 0;
            car.jumping = false;
        }
    }
}

function updateAICar() {
    if (aiCar.jumping) {
        aiCar.jumpSpeed += aiCar.gravity;  // 应用重力加速度
        aiCar.jumpHeight += aiCar.jumpSpeed;
        
        // 跳跃完成，回到地面
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
        
        // 处理不同类型的障碍物
        if ((nearestObstacle.type === 'air' || nearestObstacle.type === 'tall') && !aiCar.jumping) {
            aiCar.jumping = true;
            aiCar.jumpSpeed = aiCar.maxJumpSpeed;
        } else if ((nearestObstacle.type === 'ground' || nearestObstacle.type === 'wide' || nearestObstacle.type === 'moving') && obsLane === aiCar.lane) {
            // 躲避地面障碍物
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
    const isPlayerObstacles = obstacleArray === obstacles;
    
    if (isPlayerObstacles) {
        obstacleTimer++;
        if (obstacleTimer > obstacleSpawnInterval) {
            generateObstacle(obstacleArray);
            obstacleTimer = 0;
        }
    } else {
        aiObstacleTimer++;
        if (aiObstacleTimer > obstacleSpawnInterval) {
            generateObstacle(obstacleArray);
            aiObstacleTimer = 0;
        }
    }
    
    // 使用当前速度更新障碍物位置
    for (let i = obstacleArray.length - 1; i >= 0; i--) {
        const obs = obstacleArray[i];
        obs.y += currentObstacleSpeed;
        
        // 移动型障碍物左右移动
        if (obs.type === 'moving') {
            obs.moveTimer = (obs.moveTimer || 0) + 1;
            if (obs.moveTimer % 30 === 0) {
                const currentLaneIdx = lanes.indexOf(obs.x);
                if (obs.moveDirection === undefined) {
                    obs.moveDirection = Math.random() > 0.5 ? 1 : -1;
                }
                
                const nextLane = currentLaneIdx + obs.moveDirection;
                if (nextLane >= 0 && nextLane < lanes.length) {
                    obs.x = lanes[nextLane];
                } else {
                    obs.moveDirection *= -1;
                }
            }
        }
        
        if (obs.y > canvas.height) {
            obstacleArray.splice(i, 1);
        }
    }
}

// 增强的随机生成算法（需求14.3）
function generateObstacle(obstacleArray) {
    // 根据难度等级选择障碍物类型
    let obstacleType;
    const rand = Math.random();
    
    if (difficultyLevel === 1) {
        // 难度1：只有基础障碍物
        obstacleType = rand > 0.5 ? OBSTACLE_TYPES.GROUND : OBSTACLE_TYPES.AIR;
    } else if (difficultyLevel === 2) {
        // 难度2：添加高障碍物
        if (rand < 0.4) obstacleType = OBSTACLE_TYPES.GROUND;
        else if (rand < 0.7) obstacleType = OBSTACLE_TYPES.AIR;
        else obstacleType = OBSTACLE_TYPES.TALL;
    } else if (difficultyLevel === 3) {
        // 难度3：添加宽障碍物
        if (rand < 0.3) obstacleType = OBSTACLE_TYPES.GROUND;
        else if (rand < 0.5) obstacleType = OBSTACLE_TYPES.AIR;
        else if (rand < 0.7) obstacleType = OBSTACLE_TYPES.TALL;
        else obstacleType = OBSTACLE_TYPES.WIDE;
    } else if (difficultyLevel === 4) {
        // 难度4：添加移动障碍物
        if (rand < 0.25) obstacleType = OBSTACLE_TYPES.GROUND;
        else if (rand < 0.45) obstacleType = OBSTACLE_TYPES.AIR;
        else if (rand < 0.65) obstacleType = OBSTACLE_TYPES.TALL;
        else if (rand < 0.8) obstacleType = OBSTACLE_TYPES.WIDE;
        else obstacleType = OBSTACLE_TYPES.MOVING;
    } else {
        // 难度5：所有类型均衡分布
        if (rand < 0.2) obstacleType = OBSTACLE_TYPES.GROUND;
        else if (rand < 0.4) obstacleType = OBSTACLE_TYPES.AIR;
        else if (rand < 0.6) obstacleType = OBSTACLE_TYPES.TALL;
        else if (rand < 0.8) obstacleType = OBSTACLE_TYPES.WIDE;
        else obstacleType = OBSTACLE_TYPES.MOVING;
    }
    
    // 智能车道选择：避免连续在同一车道生成
    let lane;
    const recentObstacles = obstacleArray.slice(-3);
    const recentLanes = recentObstacles.map(obs => lanes.indexOf(obs.x));
    
    // 如果最近3个障碍物都在同一车道，强制选择其他车道
    if (recentLanes.length >= 3 && recentLanes.every(l => l === recentLanes[0])) {
        const availableLanes = [0, 1, 2].filter(l => l !== recentLanes[0]);
        lane = availableLanes[Math.floor(Math.random() * availableLanes.length)];
    } else {
        lane = Math.floor(Math.random() * 3);
    }
    
    // 创建障碍物
    const obstacle = {
        x: lanes[lane],
        y: obstacleType.yOffset,
        width: obstacleType.width || 50,
        height: obstacleType.height,
        type: obstacleType.type,
        color: obstacleType.color
    };
    
    // 高难度下可能生成组合障碍物（多个障碍物同时出现）
    if (difficultyLevel >= 4 && Math.random() < 0.2) {
        obstacleArray.push(obstacle);
        
        // 在不同车道生成第二个障碍物
        const otherLanes = [0, 1, 2].filter(l => l !== lane);
        const secondLane = otherLanes[Math.floor(Math.random() * otherLanes.length)];
        const secondType = Math.random() > 0.5 ? OBSTACLE_TYPES.GROUND : OBSTACLE_TYPES.AIR;
        
        obstacleArray.push({
            x: lanes[secondLane],
            y: secondType.yOffset,
            width: secondType.width || 50,
            height: secondType.height,
            type: secondType.type,
            color: secondType.color
        });
    } else {
        obstacleArray.push(obstacle);
    }
}

function drawObstacles(obstacleArray, offsetX) {
    const scale = (isMultiplayer || isAIMode ? canvas.width / 2 : canvas.width) / 400;
    obstacleArray.forEach(obs => {
        // 根据障碍物类型计算Y位置
        let obsY = obs.y;
        if (obs.type === 'air') {
            obsY = obs.y + 100;
        } else if (obs.type === 'tall') {
            obsY = obs.y + 50;
        }
        
        ctx.save();
        ctx.shadowBlur = 15 * scale;
        
        // 使用障碍物自带的颜色
        const colors = obs.color || ['#ff6666', '#cc0000'];
        ctx.shadowColor = `rgba(${parseInt(colors[0].slice(1, 3), 16)}, ${parseInt(colors[0].slice(3, 5), 16)}, ${parseInt(colors[0].slice(5, 7), 16)}, 0.6)`;
        
        const gradient = ctx.createLinearGradient(
            offsetX + obs.x * scale, obsY * scale,
            offsetX + obs.x * scale, (obsY + obs.height) * scale
        );
        gradient.addColorStop(0, colors[0]);
        gradient.addColorStop(1, colors[1]);
        ctx.fillStyle = gradient;
        
        ctx.fillRect(offsetX + obs.x * scale, obsY * scale, obs.width * scale, obs.height * scale);
        
        // 为移动型障碍物添加视觉标识
        if (obs.type === 'moving') {
            ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
            ctx.fillRect(
                offsetX + (obs.x + 5) * scale, 
                (obsY + 5) * scale, 
                (obs.width - 10) * scale, 
                (obs.height - 10) * scale
            );
        }
        
        // 为高障碍物添加警告标识
        if (obs.type === 'tall') {
            ctx.fillStyle = 'rgba(255, 255, 0, 0.5)';
            ctx.fillRect(
                offsetX + (obs.x + obs.width / 2 - 5) * scale,
                (obsY + 10) * scale,
                10 * scale,
                10 * scale
            );
        }
        
        ctx.restore();
    });
}

function checkCollision(carObj, obstacleArray, isAI = false) {
    const carY = carObj.y + carObj.jumpHeight;
    
    // 优化碰撞检测：添加碰撞容差，使检测更精确（需求14.2）
    const collisionTolerance = 5;  // 5像素的容差，避免边缘误判
    
    for (let i = 0; i < obstacleArray.length; i++) {
        const obs = obstacleArray[i];
        
        // 根据障碍物类型计算Y位置
        let obsY = obs.y;
        if (obs.type === 'air') {
            obsY = obs.y + 100;
        } else if (obs.type === 'tall') {
            obsY = obs.y + 50;
        }
        
        // AABB碰撞检测算法，带容差优化
        const carLeft = carObj.x + collisionTolerance;
        const carRight = carObj.x + carObj.width - collisionTolerance;
        const carTop = carY + collisionTolerance;
        const carBottom = carY + carObj.height - collisionTolerance;
        
        const obsLeft = obs.x + collisionTolerance;
        const obsRight = obs.x + obs.width - collisionTolerance;
        const obsTop = obsY + collisionTolerance;
        const obsBottom = obsY + obs.height - collisionTolerance;
        
        // 检测矩形重叠
        if (carLeft < obsRight &&
            carRight > obsLeft &&
            carTop < obsBottom &&
            carBottom > obsTop) {
            if (isAI) {
                gameOverAI();
            } else {
                gameOver();
            }
            return;  // 碰撞后立即返回
        }
    }
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
