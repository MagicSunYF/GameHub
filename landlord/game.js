const socket = io('http://localhost:5000');

let roomId = null;
let myPosition = null;
let myCards = [];
let selectedCards = [];
let isLandlord = false;
let currentTurn = null;
let gameStarted = false;

// 牌型定义
const CARD_VALUES = {
    '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
    'J': 11, 'Q': 12, 'K': 13, 'A': 14, '2': 15, 'joker': 16, 'JOKER': 17
};

const SUITS = ['♠', '♥', '♣', '♦'];

// ESC 隐藏功能
let isHidden = false;
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        isHidden = !isHidden;
        document.querySelectorAll('#title, #game-container, #hint')
            .forEach(el => el.classList.toggle('hidden', isHidden));
    }
});

// 菜单事件
document.getElementById('create-room-btn').addEventListener('click', () => {
    socket.emit('create_room', { game: 'landlord' });
});

document.getElementById('join-room-btn').addEventListener('click', () => {
    document.querySelector('.menu-buttons').classList.add('hidden');
    document.getElementById('join-input').classList.remove('hidden');
});

document.getElementById('join-confirm-btn').addEventListener('click', () => {
    const inputRoomId = document.getElementById('room-id-input').value.trim();
    if (inputRoomId) {
        socket.emit('join_room', { room_id: inputRoomId, game: 'landlord' });
    }
});

// Socket 事件
socket.on('room_created', (data) => {
    roomId = data.room_id;
    myPosition = data.position;
    document.getElementById('room-id-display').textContent = roomId;
    document.getElementById('room-panel').style.display = 'flex';
    document.querySelector('.menu-buttons').classList.add('hidden');
    updatePlayerSeats();
});

socket.on('room_joined', (data) => {
    roomId = data.room_id;
    myPosition = data.position;
    document.getElementById('room-id-display').textContent = roomId;
    document.getElementById('room-panel').style.display = 'flex';
    document.getElementById('join-input').classList.add('hidden');
    updatePlayerSeats();
});

socket.on('player_joined', (data) => {
    updatePlayerSeats(data.players);
});

socket.on('game_start', (data) => {
    gameStarted = true;
    document.getElementById('room-panel').classList.add('hidden');
    myCards = data.cards;
    renderMyCards();
    document.querySelector('.action-buttons').classList.remove('hidden');
});

function updatePlayerSeats(playerCount = 1) {
    const seats = [
        document.querySelector('#top-player .player-seat'),
        document.querySelector('#left-player .player-seat'),
        document.querySelector('#right-player .player-seat')
    ];
    
    // 右侧永远是自己
    seats[2].classList.remove('empty');
    seats[2].classList.add('ready');
    
    // 根据玩家数量更新其他座位
    if (playerCount >= 2) {
        seats[1].classList.remove('empty');
        seats[1].classList.add('ready');
        seats[1].querySelector('.player-name').textContent = '玩家2';
    }
    if (playerCount >= 3) {
        seats[0].classList.remove('empty');
        seats[0].classList.add('ready');
        seats[0].querySelector('.player-name').textContent = '玩家3';
    }
}

socket.on('bid_turn', (data) => {
    if (data.position === myPosition) {
        document.getElementById('bid-area').classList.remove('hidden');
    }
});

socket.on('landlord_decided', (data) => {
    document.getElementById('bid-area').classList.add('hidden');
    document.getElementById('landlord-cards').classList.remove('hidden');
    renderBottomCards(data.bottom_cards);
    
    const seats = [
        document.querySelector('#top-player .player-seat'),
        document.querySelector('#left-player .player-seat'),
        document.querySelector('#right-player .player-seat')
    ];
    
    seats[data.landlord].classList.add('landlord');
    const badge = document.createElement('div');
    badge.className = 'landlord-badge';
    badge.textContent = '地主';
    seats[data.landlord].appendChild(badge);
    
    if (data.landlord === myPosition) {
        isLandlord = true;
        myCards = myCards.concat(data.bottom_cards);
        renderMyCards();
        showEffect('地主', 'landlord');
    }
});

socket.on('play_turn', (data) => {
    currentTurn = data.position;
    if (data.position === myPosition) {
        document.getElementById('play-btn').disabled = false;
        document.getElementById('pass-btn').disabled = data.can_pass ? false : true;
    }
});

socket.on('cards_played', (data) => {
    document.getElementById('last-play').classList.remove('hidden');
    renderLastPlay(data.cards, data.position);
    updateCardCount(data.position, data.remaining);
    
    // 检查特殊牌型
    const cardType = analyzeCardType(data.cards);
    if (cardType.type === 'bomb') {
        showEffect('炸弹', 'bomb');
    } else if (cardType.type === 'rocket') {
        showEffect('火箭', 'rocket');
    } else if (cardType.type === 'plane') {
        showEffect('飞机', 'plane');
    }
});

socket.on('game_over', (data) => {
    const winner = data.winner === myPosition ? '你赢了！' : '你输了！';
    showEffect(winner, data.spring ? 'spring' : 'normal');
    
    setTimeout(() => {
        location.reload();
    }, 3000);
});

socket.on('error', (data) => {
    alert(data.msg);
});

// 叫地主按钮
document.querySelectorAll('.bid-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const bid = parseInt(btn.dataset.bid);
        socket.emit('bid', { room_id: roomId, bid });
        document.getElementById('bid-area').classList.add('hidden');
    });
});

// 出牌按钮
document.getElementById('play-btn').addEventListener('click', () => {
    if (selectedCards.length === 0) return;
    
    const cardType = analyzeCardType(selectedCards);
    if (!cardType.valid) {
        alert('牌型不合法');
        return;
    }
    
    socket.emit('play_cards', { room_id: roomId, cards: selectedCards });
    
    // 移除已出的牌
    selectedCards.forEach(card => {
        const index = myCards.findIndex(c => c.value === card.value && c.suit === card.suit);
        if (index > -1) myCards.splice(index, 1);
    });
    
    selectedCards = [];
    renderMyCards();
    document.getElementById('play-btn').disabled = true;
});

document.getElementById('pass-btn').addEventListener('click', () => {
    socket.emit('pass', { room_id: roomId });
    selectedCards = [];
    renderMyCards();
    document.getElementById('pass-btn').disabled = true;
});

// 渲染手牌
function renderMyCards() {
    const container = document.getElementById('hand-cards');
    container.innerHTML = '';
    
    myCards.sort((a, b) => {
        const valA = CARD_VALUES[a.value];
        const valB = CARD_VALUES[b.value];
        if (valA !== valB) return valA - valB;
        return SUITS.indexOf(a.suit) - SUITS.indexOf(b.suit);
    });
    
    myCards.forEach((card, index) => {
        const cardEl = createCardElement(card);
        cardEl.addEventListener('click', () => toggleCardSelection(card, cardEl));
        container.appendChild(cardEl);
    });
}

function createCardElement(card) {
    const div = document.createElement('div');
    div.className = 'card';
    
    if (card.value === 'joker') {
        div.classList.add('joker');
        div.innerHTML = '<div class="card-value">小王</div>';
    } else if (card.value === 'JOKER') {
        div.classList.add('big-joker');
        div.innerHTML = '<div class="card-value">大王</div>';
    } else {
        div.classList.add(card.suit === '♥' || card.suit === '♦' ? 'red' : 'black');
        div.innerHTML = `
            <div class="card-value">${card.value}</div>
            <div class="card-suit">${card.suit}</div>
        `;
    }
    
    return div;
}

function toggleCardSelection(card, element) {
    const index = selectedCards.findIndex(c => c.value === card.value && c.suit === card.suit);
    
    if (index > -1) {
        selectedCards.splice(index, 1);
        element.classList.remove('selected');
    } else {
        selectedCards.push(card);
        element.classList.add('selected');
    }
}

function renderBottomCards(cards) {
    const container = document.getElementById('bottom-cards');
    container.innerHTML = '';
    cards.forEach(card => {
        container.appendChild(createCardElement(card));
    });
}

function renderLastPlay(cards, position) {
    const container = document.getElementById('last-cards');
    container.innerHTML = '';
    cards.forEach(card => {
        container.appendChild(createCardElement(card));
    });
}

function updateCardCount(position, count) {
    const seats = [
        document.querySelector('#top-player .player-seat'),
        document.querySelector('#left-player .player-seat'),
        document.querySelector('#right-player .player-seat')
    ];
    
    let countEl = seats[position].querySelector('.card-count');
    if (!countEl) {
        countEl = document.createElement('div');
        countEl.className = 'card-count';
        seats[position].appendChild(countEl);
    }
    countEl.textContent = `${count}张`;
}

function updatePlayerInfo(landlordPos) {
    // 已在 landlord_decided 中处理
}

// 牌型分析
function analyzeCardType(cards) {
    if (cards.length === 0) return { valid: false };
    
    const values = cards.map(c => CARD_VALUES[c.value]).sort((a, b) => a - b);
    const counts = {};
    values.forEach(v => counts[v] = (counts[v] || 0) + 1);
    const countArr = Object.values(counts).sort((a, b) => b - a);
    
    // 火箭
    if (cards.length === 2 && values[0] === 16 && values[1] === 17) {
        return { valid: true, type: 'rocket' };
    }
    
    // 炸弹
    if (cards.length === 4 && countArr[0] === 4) {
        return { valid: true, type: 'bomb' };
    }
    
    // 单张
    if (cards.length === 1) {
        return { valid: true, type: 'single' };
    }
    
    // 对子
    if (cards.length === 2 && countArr[0] === 2) {
        return { valid: true, type: 'pair' };
    }
    
    // 三张
    if (cards.length === 3 && countArr[0] === 3) {
        return { valid: true, type: 'triple' };
    }
    
    // 三带一
    if (cards.length === 4 && countArr[0] === 3 && countArr[1] === 1) {
        return { valid: true, type: 'triple_single' };
    }
    
    // 三带一对
    if (cards.length === 5 && countArr[0] === 3 && countArr[1] === 2) {
        return { valid: true, type: 'triple_pair' };
    }
    
    // 飞机（两个三张）
    if (cards.length >= 6 && countArr[0] === 3 && countArr[1] === 3) {
        return { valid: true, type: 'plane' };
    }
    
    // 顺子
    if (cards.length >= 5 && countArr[0] === 1 && isSequence(values)) {
        return { valid: true, type: 'straight' };
    }
    
    return { valid: false };
}

function isSequence(values) {
    for (let i = 1; i < values.length; i++) {
        if (values[i] !== values[i-1] + 1) return false;
    }
    return true;
}

// 特效显示
function showEffect(text, type) {
    const container = document.getElementById('effect-container');
    const effect = document.createElement('div');
    effect.className = `effect ${type}`;
    effect.textContent = text;
    container.appendChild(effect);
    
    setTimeout(() => {
        effect.remove();
    }, 2000);
}
