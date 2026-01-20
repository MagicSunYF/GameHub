const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const scoreEl = document.getElementById('score');
const gameOverEl = document.getElementById('game-over');
const finalScoreEl = document.getElementById('final-score');
const title = document.getElementById('title');
const gameContainer = document.getElementById('game-container');
const controls = document.getElementById('controls');
const hint = document.getElementById('hint');

function resizeCanvas() {
    const maxWidth = Math.min(window.innerWidth * 0.9, 400);
    const maxHeight = Math.min(window.innerHeight * 0.8, 600);
    const ratio = Math.min(maxWidth / 400, maxHeight / 600);
    canvas.width = 400 * ratio;
    canvas.height = 600 * ratio;
    canvas.style.width = canvas.width + 'px';
    canvas.style.height = canvas.height + 'px';
}

resizeCanvas();
window.addEventListener('resize', resizeCanvas);

let isHidden = false;
let gameRunning = false;
let score = 0;
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

const lanes = [100, 175, 250];
let currentLane = 1;

const obstacles = [];
const obstacleSpeed = 5;
let obstacleTimer = 0;

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        isHidden = !isHidden;
        [title, gameContainer, controls, hint].forEach(el => {
            el.classList.toggle('hidden', isHidden);
        });
    }
    
    if (!gameRunning) return;
    
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
    obstacles.length = 0;
    car.x = lanes[1];
    car.y = 500;
    currentLane = 1;
    car.jumping = false;
    car.jumpHeight = 0;
    gameOverEl.classList.add('hidden');
    controls.classList.add('hidden');
    gameLoop();
}

function restartGame() {
    startGame();
}

function gameLoop() {
    if (!gameRunning) return;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    drawRoad();
    updateCar();
    drawCar();
    updateObstacles();
    drawObstacles();
    checkCollision();
    
    score++;
    scoreEl.textContent = `得分: ${Math.floor(score / 10)}`;
    
    animationId = requestAnimationFrame(gameLoop);
}

function drawRoad() {
    ctx.fillStyle = '#2a2a2a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    const scale = canvas.width / 400;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 3 * scale;
    ctx.setLineDash([20 * scale, 20 * scale]);
    
    for (let i = 1; i < 3; i++) {
        ctx.beginPath();
        ctx.moveTo((lanes[i] - 12.5) * scale, 0);
        ctx.lineTo((lanes[i] - 12.5) * scale, canvas.height);
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

function drawCar() {
    const y = car.y + car.jumpHeight;
    const scale = canvas.width / 400;
    
    ctx.save();
    ctx.shadowBlur = 15;
    ctx.shadowColor = 'rgba(0, 150, 255, 0.6)';
    
    // 车身主体
    const gradient = ctx.createLinearGradient(car.x * scale, y * scale, car.x * scale, (y + car.height) * scale);
    gradient.addColorStop(0, '#0099ff');
    gradient.addColorStop(1, '#0066cc');
    ctx.fillStyle = gradient;
    ctx.fillRect(car.x * scale, y * scale, car.width * scale, car.height * scale);
    
    // 车顶
    ctx.fillStyle = '#004d99';
    ctx.fillRect((car.x + 5) * scale, (y + 5) * scale, (car.width - 10) * scale, 25 * scale);
    
    // 前窗
    ctx.fillStyle = 'rgba(200, 230, 255, 0.7)';
    ctx.fillRect((car.x + 8) * scale, (y + 8) * scale, (car.width - 16) * scale, 18 * scale);
    
    // 车灯
    ctx.fillStyle = '#ffff00';
    ctx.fillRect((car.x + 5) * scale, (y + car.height - 10) * scale, 12 * scale, 8 * scale);
    ctx.fillRect((car.x + car.width - 17) * scale, (y + car.height - 10) * scale, 12 * scale, 8 * scale);
    
    // 车轮
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect((car.x - 3) * scale, (y + 20) * scale, 8 * scale, 15 * scale);
    ctx.fillRect((car.x + car.width - 5) * scale, (y + 20) * scale, 8 * scale, 15 * scale);
    ctx.fillRect((car.x - 3) * scale, (y + 50) * scale, 8 * scale, 15 * scale);
    ctx.fillRect((car.x + car.width - 5) * scale, (y + 50) * scale, 8 * scale, 15 * scale);
    
    // 车轮细节
    ctx.fillStyle = '#666';
    ctx.fillRect((car.x - 1) * scale, (y + 23) * scale, 4 * scale, 9 * scale);
    ctx.fillRect((car.x + car.width - 3) * scale, (y + 23) * scale, 4 * scale, 9 * scale);
    ctx.fillRect((car.x - 1) * scale, (y + 53) * scale, 4 * scale, 9 * scale);
    ctx.fillRect((car.x + car.width - 3) * scale, (y + 53) * scale, 4 * scale, 9 * scale);
    
    ctx.shadowBlur = 0;
    ctx.restore();
}

function updateObstacles() {
    obstacleTimer++;
    
    if (obstacleTimer > 60) {
        const lane = Math.floor(Math.random() * 3);
        const type = Math.random() > 0.5 ? 'ground' : 'air';
        obstacles.push({
            x: lanes[lane],
            y: type === 'ground' ? -80 : -120,
            width: 50,
            height: type === 'ground' ? 80 : 40,
            type: type
        });
        obstacleTimer = 0;
    }
    
    for (let i = obstacles.length - 1; i >= 0; i--) {
        obstacles[i].y += obstacleSpeed;
        
        if (obstacles[i].y > canvas.height) {
            obstacles.splice(i, 1);
        }
    }
}

function drawObstacles() {
    const scale = canvas.width / 400;
    obstacles.forEach(obs => {
        const obsY = obs.type === 'ground' ? obs.y : obs.y + 100;
        
        if (obs.type === 'ground') {
            ctx.fillStyle = '#ff4444';
            ctx.fillRect(obs.x * scale, obsY * scale, obs.width * scale, obs.height * scale);
        } else {
            ctx.fillStyle = '#ffaa00';
            ctx.fillRect(obs.x * scale, obsY * scale, obs.width * scale, obs.height * scale);
        }
        
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 2 * scale;
        ctx.strokeRect(obs.x * scale, obsY * scale, obs.width * scale, obs.height * scale);
    });
}

function checkCollision() {
    const carY = car.y + car.jumpHeight;
    
    obstacles.forEach(obs => {
        const obsY = obs.type === 'ground' ? obs.y : obs.y + 100;
        
        if (car.x < obs.x + obs.width &&
            car.x + car.width > obs.x &&
            carY < obsY + obs.height &&
            carY + car.height > obsY) {
            gameOver();
        }
    });
}

function gameOver() {
    gameRunning = false;
    cancelAnimationFrame(animationId);
    finalScoreEl.textContent = Math.floor(score / 10);
    gameOverEl.classList.remove('hidden');
    controls.classList.remove('hidden');
}
