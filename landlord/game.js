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
                myCards: [...myCards],
                selectedCards: [...selectedCards],
                isLandlord,
                currentTurn,
                gameStarted,
                isSingleMode,
                lastPlayPosition,
                lastPlayCards: [...lastPlayCards],
                bidMultiplier,
                passCount,
                bombCount
            };
        },
        restore: (state) => {
            if (!state) return;
            
            roomId = state.roomId;
            myPosition = state.myPosition;
            myCards = [...state.myCards];
            selectedCards = [...state.selectedCards];
            isLandlord = state.isLandlord;
            currentTurn = state.currentTurn;
            gameStarted = state.gameStarted;
            isSingleMode = state.isSingleMode;
            lastPlayPosition = state.lastPlayPosition;
            lastPlayCards = [...state.lastPlayCards];
            bidMultiplier = state.bidMultiplier;
            passCount = state.passCount;
            bombCount = state.bombCount;
            
            if (roomId && !isSingleMode) {
                socket.emit('rejoin_room', { room_id: roomId });
            }
            
            if (gameStarted) {
                document.getElementById('menu-screen').classList.add('hidden');
                document.getElementById('room-panel').classList.add('hidden');
                renderMyCards();
            }
        }
    }
});

let roomId = null;
let myPosition = null;
let myCards = [];
let selectedCards = [];
let isLandlord = false;
let currentTurn = null;
let gameStarted = false;
let isSingleMode = false;
let aiCards = { left: [], top: [] };
let lastPlayPosition = null;
let lastPlayCards = [];
let bidMultiplier = 1;
let currentBidder = null;
let passCount = 0;
let bombCount = 0;

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
        document.getElementById('title').classList.toggle('hidden', isHidden);
        document.getElementById('game-container').classList.toggle('hidden', isHidden);
        document.getElementById('hint').classList.toggle('hidden', isHidden);
    }
});

// 菜单事件
document.getElementById('single-mode-btn').addEventListener('click', () => {
    isSingleMode = true;
    startSingleMode();
});

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
    document.getElementById('bid-area').classList.add('hidden');
    updatePlayerSeats();
});

socket.on('room_joined', (data) => {
    roomId = data.room_id;
    myPosition = data.position;
    document.getElementById('room-id-display').textContent = roomId;
    document.getElementById('room-panel').style.display = 'flex';
    document.getElementById('join-input').classList.add('hidden');
    document.getElementById('bid-area').classList.add('hidden');
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
    
    bidMultiplier = data.bid_multiplier || 1;
    document.getElementById('bid-multiplier').textContent = bidMultiplier;
    
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
        showEffect('你是地主', 'landlord');
    }
});

socket.on('update_cards', (data) => {
    myCards = data.cards;
    renderMyCards();
});

socket.on('player_bid', (data) => {
    showEffect(`玩家${data.position + 1}叫${data.bid}分`, 'normal');
});

socket.on('no_landlord', () => {
    showEffect('无人叫地主，重新开始', 'normal');
    setTimeout(() => location.reload(), 2000);
});

socket.on('player_passed', (data) => {
    showEffect(`玩家${data.position + 1}不出`, 'normal');
});

socket.on('play_turn', (data) => {
    currentTurn = data.position;
    if (data.position === myPosition) {
        document.getElementById('play-btn').disabled = false;
        document.getElementById('pass-btn').disabled = data.can_pass === false;
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
    const multiplier = data.multiplier || 1;
    const msg = data.spring ? `${winner} (春天 ${multiplier}倍)` : `${winner} (${multiplier}倍)`;
    showEffect(msg, data.spring ? 'spring' : 'normal');
    
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
        
        if (isSingleMode) {
            handleSingleModeBid(bid);
        } else {
            // 联机模式直接发送叫牌
            socket.emit('bid', { room_id: roomId, bid: bid });
            document.getElementById('bid-area').classList.add('hidden');
        }
    });
});

function handleSingleModeBid(bid) {
    if (bid === 0) {
        // 不叫/不抢
        passCount++;
        if (currentBidder === null) {
            // 第一轮叫地主，没人叫则下一位
            nextBidTurn();
        } else {
            // 抢地主阶段
            if (passCount >= 2) {
                // 连续两人不抢，确定地主
                finalizeLandlord();
            } else {
                nextBidTurn();
            }
        }
    } else if (bid === 1) {
        // 叫地主
        if (currentBidder === null) {
            currentBidder = myPosition;
            bidMultiplier = 2;
            passCount = 0;
            document.getElementById('bid-multiplier').textContent = bidMultiplier;
            nextBidTurn();
        }
    } else if (bid === 2) {
        // 抢地主
        if (currentBidder !== null) {
            currentBidder = myPosition;
            bidMultiplier = Math.min(bidMultiplier + 1, 5);
            passCount = 0;
            document.getElementById('bid-multiplier').textContent = bidMultiplier;
            nextBidTurn();
        }
    } else if (bid === 3) {
        // 加倍
        if (currentBidder !== null) {
            currentBidder = myPosition;
            bidMultiplier = Math.min(bidMultiplier * 2, 8);
            passCount = 0;
            document.getElementById('bid-multiplier').textContent = bidMultiplier;
            nextBidTurn();
        }
    }
    
    document.getElementById('bid-area').classList.add('hidden');
}

function nextBidTurn() {
    currentTurn = (currentTurn + 1) % 3;
    
    if (currentTurn === myPosition) {
        showBidButtons();
    } else {
        setTimeout(aiBid, 1500);
    }
}

function showBidButtons() {
    if (!gameStarted || !isSingleMode) return;
    
    document.getElementById('bid-area').classList.remove('hidden');
    
    const callBtn = document.querySelector('.bid-btn.call');
    const grabBtn = document.querySelector('.bid-btn.grab');
    
    if (currentBidder === null) {
        // 第一轮叫地主
        callBtn.disabled = false;
        grabBtn.disabled = true;
        callBtn.textContent = '叫地主';
    } else {
        // 抢地主阶段
        callBtn.disabled = true;
        grabBtn.disabled = false;
        grabBtn.textContent = `抢地主(${bidMultiplier + 1}倍)`;
    }
}

function aiBid() {
    const random = Math.random();
    
    if (currentBidder === null) {
        // AI叫地主概率50%
        if (random > 0.5) {
            currentBidder = currentTurn;
            bidMultiplier = 2;
            passCount = 0;
            document.getElementById('bid-multiplier').textContent = bidMultiplier;
            showEffect(`AI${currentTurn + 1}叫1分`, 'normal');
        } else {
            passCount++;
            showEffect(`AI${currentTurn + 1}不叫`, 'normal');
        }
    } else {
        // AI抢地主概率30%，加倍概率10%
        if (random > 0.9 && bidMultiplier < 8) {
            // 加倍
            currentBidder = currentTurn;
            bidMultiplier = Math.min(bidMultiplier * 2, 8);
            passCount = 0;
            document.getElementById('bid-multiplier').textContent = bidMultiplier;
            showEffect(`AI${currentTurn + 1}加倍`, 'normal');
        } else if (random > 0.7 && bidMultiplier < 5) {
            // 抢地主
            currentBidder = currentTurn;
            bidMultiplier++;
            passCount = 0;
            document.getElementById('bid-multiplier').textContent = bidMultiplier;
            showEffect(`AI${currentTurn + 1}抢地主`, 'normal');
        } else {
            passCount++;
            showEffect(`AI${currentTurn + 1}不抢`, 'normal');
            
            if (passCount >= 2) {
                setTimeout(finalizeLandlord, 1000);
                return;
            }
        }
    }
    
    setTimeout(nextBidTurn, 1000);
}

function finalizeLandlord() {
    if (currentBidder === null) {
        // 无人叫地主，重新发牌
        showEffect('无人叫地主，重新开始', 'normal');
        setTimeout(() => location.reload(), 2000);
        return;
    }
    
    decideLandlord(currentBidder, aiCards.top.concat(aiCards.left).slice(0, 3));
}

// 出牌按钮
document.getElementById('play-btn').addEventListener('click', () => {
    if (selectedCards.length === 0) return;
    
    const cardType = analyzeCardType(selectedCards);
    if (!cardType.valid) {
        alert('牌型不合法');
        return;
    }
    
    if (isSingleMode) {
        // 检查是否能压过上家
        if (lastPlayCards.length > 0 && lastPlayPosition !== 2) {
            if (!canBeat(selectedCards, lastPlayCards)) {
                alert('牌型不符或牌力不够');
                return;
            }
        }
        
        // 单人模式
        selectedCards.forEach(card => {
            const index = myCards.findIndex(c => c.value === card.value && c.suit === card.suit);
            if (index > -1) myCards.splice(index, 1);
        });
        
        document.getElementById('last-play').classList.remove('hidden');
        renderLastPlay(selectedCards, 2);
        lastPlayCards = [...selectedCards];
        lastPlayPosition = 2;
        
        if (cardType.type === 'bomb') showEffect('炸弹', 'bomb');
        else if (cardType.type === 'rocket') showEffect('火箭', 'rocket');
        
        if (cardType.type === 'bomb' || cardType.type === 'rocket') {
            bombCount++;
            bidMultiplier *= 2;
        }
        
        if (myCards.length === 0) {
            const isSpring = aiCards.left.length === 17 && aiCards.top.length === 17;
            const finalMultiplier = isSpring ? bidMultiplier * 2 : bidMultiplier;
            showEffect(`你赢了！${finalMultiplier}倍`, 'spring');
            setTimeout(() => location.reload(), 2000);
            return;
        }
        
        updateCardCount(2, myCards.length);
        selectedCards = [];
        renderMyCards();
        document.getElementById('play-btn').disabled = true;
        
        currentTurn = 0;
        setTimeout(aiPlay, 1500);
    } else {
        // 联机模式
        socket.emit('play_cards', { room_id: roomId, cards: selectedCards });
        
        selectedCards.forEach(card => {
            const index = myCards.findIndex(c => c.value === card.value && c.suit === card.suit);
            if (index > -1) myCards.splice(index, 1);
        });
        
        selectedCards = [];
        renderMyCards();
        document.getElementById('play-btn').disabled = true;
    }
});

document.getElementById('pass-btn').addEventListener('click', () => {
    if (isSingleMode) {
        selectedCards = [];
        renderMyCards();
        document.getElementById('pass-btn').disabled = true;
        document.getElementById('play-btn').disabled = true;
        currentTurn = 0;
        setTimeout(aiPlay, 1000);
    } else {
        socket.emit('pass', { room_id: roomId });
        selectedCards = [];
        renderMyCards();
        document.getElementById('pass-btn').disabled = true;
    }
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
        div.innerHTML = `
            <div class="card-value">小王</div>
            <div class="card-suit">🃏</div>
        `;
    } else if (card.value === 'JOKER') {
        div.classList.add('big-joker');
        div.innerHTML = `
            <div class="card-value">大王</div>
            <div class="card-suit">🃏</div>
        `;
    } else {
        div.classList.add(card.suit === '♥' || card.suit === '♦' ? 'red' : 'black');
        div.innerHTML = `
            <div class="card-corner top-left">
                <span>${card.value}</span>
                <span>${card.suit}</span>
            </div>
            <div class="card-value">${card.value}</div>
            <div class="card-suit">${card.suit}</div>
            <div class="card-corner bottom-right">
                <span>${card.value}</span>
                <span>${card.suit}</span>
            </div>
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
    const uniqueValues = Object.keys(counts).map(Number).sort((a, b) => a - b);
    const countArr = Object.values(counts).sort((a, b) => b - a);
    
    // 火箭 (Rocket): 小王+大王
    if (cards.length === 2 && values[0] === 16 && values[1] === 17) {
        return { valid: true, type: 'rocket', value: 17 };
    }
    
    // 炸弹 (Bomb): 四张相同
    if (cards.length === 4 && countArr[0] === 4) {
        return { valid: true, type: 'bomb', value: uniqueValues[0] };
    }
    
    // 单张 (Single)
    if (cards.length === 1) {
        return { valid: true, type: 'single', value: values[0] };
    }
    
    // 对子 (Pair)
    if (cards.length === 2 && countArr[0] === 2) {
        return { valid: true, type: 'pair', value: uniqueValues[0] };
    }
    
    // 三张 (Triple)
    if (cards.length === 3 && countArr[0] === 3) {
        return { valid: true, type: 'triple', value: uniqueValues[0] };
    }
    
    // 三带一 (Triple with Single)
    if (cards.length === 4 && countArr[0] === 3 && countArr[1] === 1) {
        const tripleValue = uniqueValues.find(v => counts[v] === 3);
        return { valid: true, type: 'triple_single', value: tripleValue };
    }
    
    // 三带一对 (Triple with Pair)
    if (cards.length === 5 && countArr[0] === 3 && countArr[1] === 2) {
        const tripleValue = uniqueValues.find(v => counts[v] === 3);
        return { valid: true, type: 'triple_pair', value: tripleValue };
    }
    
    // 顺子 (Straight): 至少5张连续单牌，不能包含2和王
    if (cards.length >= 5 && countArr[0] === 1) {
        const maxValue = Math.max(...uniqueValues);
        // 顺子不能包含2(15)和王(16,17)
        if (maxValue <= 14 && isSequence(uniqueValues)) {
            return { valid: true, type: 'straight', value: uniqueValues[0], length: cards.length };
        }
    }
    
    // 连对 (Consecutive Pairs): 至少3对连续对子
    if (cards.length >= 6 && cards.length % 2 === 0) {
        const pairCount = cards.length / 2;
        if (pairCount >= 3 && countArr[0] === 2 && uniqueValues.length === pairCount) {
            const maxValue = Math.max(...uniqueValues);
            // 连对不能包含2(15)和王(16,17)
            if (maxValue <= 14 && isSequence(uniqueValues)) {
                return { valid: true, type: 'consecutive_pairs', value: uniqueValues[0], length: pairCount };
            }
        }
    }
    
    // 飞机 (Plane): 至少2个连续三张
    if (cards.length >= 6) {
        const tripleValues = uniqueValues.filter(v => counts[v] === 3);
        if (tripleValues.length >= 2 && isSequence(tripleValues)) {
            const maxValue = Math.max(...tripleValues);
            // 飞机不能包含2(15)和王(16,17)
            if (maxValue <= 14) {
                // 纯飞机（只有三张）
                if (cards.length === tripleValues.length * 3) {
                    return { valid: true, type: 'plane', value: tripleValues[0], length: tripleValues.length };
                }
                // 飞机带单牌
                if (cards.length === tripleValues.length * 4 && uniqueValues.length === tripleValues.length * 2) {
                    return { valid: true, type: 'plane_single', value: tripleValues[0], length: tripleValues.length };
                }
                // 飞机带对子
                if (cards.length === tripleValues.length * 5) {
                    const pairValues = uniqueValues.filter(v => counts[v] === 2);
                    if (pairValues.length === tripleValues.length) {
                        return { valid: true, type: 'plane_pair', value: tripleValues[0], length: tripleValues.length };
                    }
                }
            }
        }
    }
    
    // 四带二 (Four with Two): 四张+两张单牌或两对
    if (cards.length === 6 && countArr[0] === 4) {
        const quadValue = uniqueValues.find(v => counts[v] === 4);
        return { valid: true, type: 'four_two_single', value: quadValue };
    }
    
    if (cards.length === 8 && countArr[0] === 4 && countArr[1] === 2 && countArr[2] === 2) {
        const quadValue = uniqueValues.find(v => counts[v] === 4);
        return { valid: true, type: 'four_two_pair', value: quadValue };
    }
    
    return { valid: false };
}

function isSequence(values) {
    if (values.length < 2) return false;
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


// 单人模式
function startSingleMode() {
    document.getElementById('room-panel').style.display = 'none';
    document.getElementById('bid-area').classList.add('hidden');
    gameStarted = true;
    myPosition = 2;
    
    // 初始化AI玩家
    const seats = [
        document.querySelector('#top-player .player-seat'),
        document.querySelector('#left-player .player-seat')
    ];
    seats.forEach((seat, idx) => {
        seat.classList.remove('empty');
        seat.classList.add('ready');
        seat.querySelector('.player-name').textContent = `AI${idx + 1}`;
    });
    
    // 发牌
    const deck = createDeck();
    shuffleArray(deck);
    
    const bottomCards = deck.slice(0, 3);
    aiCards.left = deck.slice(3, 20);
    aiCards.top = deck.slice(20, 37);
    myCards = deck.slice(37, 54);
    
    renderMyCards();
    document.querySelector('.action-buttons').classList.remove('hidden');
    
    // 随机首发玩家
    currentTurn = Math.floor(Math.random() * 3);
    currentBidder = null;
    bidMultiplier = 1;
    passCount = 0;
    
    setTimeout(() => {
        if (currentTurn === myPosition) {
            showBidButtons();
        } else {
            aiBid();
        }
    }, 1000);
}

function decideLandlord(position, bottomCards) {
    document.getElementById('landlord-cards').classList.remove('hidden');
    renderBottomCards(bottomCards);
    
    const seats = [
        document.querySelector('#top-player .player-seat'),
        document.querySelector('#left-player .player-seat'),
        document.querySelector('#right-player .player-seat')
    ];
    
    seats[position].classList.add('landlord');
    const badge = document.createElement('div');
    badge.className = 'landlord-badge';
    badge.textContent = '地主';
    seats[position].appendChild(badge);
    
    if (position === 2) {
        isLandlord = true;
        myCards = myCards.concat(bottomCards);
        renderMyCards();
        showEffect('你是地主', 'landlord');
        currentTurn = 2;
        enablePlay();
    } else if (position === 1) {
        aiCards.left = aiCards.left.concat(bottomCards);
        showEffect('AI1是地主', 'landlord');
        currentTurn = 1;
        setTimeout(aiPlay, 1500);
    } else {
        aiCards.top = aiCards.top.concat(bottomCards);
        showEffect('AI2是地主', 'landlord');
        currentTurn = 0;
        setTimeout(aiPlay, 1500);
    }
    
    updateCardCount(0, aiCards.top.length);
    updateCardCount(1, aiCards.left.length);
    updateCardCount(2, myCards.length);
}

function aiPlay() {
    if (!isSingleMode || currentTurn === 2) return;
    
    const aiCardSet = currentTurn === 1 ? aiCards.left : aiCards.top;
    
    // AI出牌逻辑
    let playCards = [];
    
    if (lastPlayCards.length === 0 || lastPlayPosition === currentTurn) {
        // 主动出牌，出最小的单张
        playCards = selectAICards(aiCardSet);
    } else {
        // 跟牌，尝试压过上家
        playCards = aiTryBeat(aiCardSet, lastPlayCards);
    }
    
    if (playCards.length > 0) {
        playCards.forEach(card => {
            const idx = aiCardSet.findIndex(c => c.value === card.value && c.suit === card.suit);
            if (idx > -1) aiCardSet.splice(idx, 1);
        });
        
        document.getElementById('last-play').classList.remove('hidden');
        renderLastPlay(playCards, currentTurn);
        lastPlayCards = [...playCards];
        lastPlayPosition = currentTurn;
        
        const cardType = analyzeCardType(playCards);
        if (cardType.type === 'bomb') showEffect('炸弹', 'bomb');
        else if (cardType.type === 'rocket') showEffect('火箭', 'rocket');
        
        if (aiCardSet.length === 0) {
            setTimeout(() => {
                showEffect('AI获胜', 'normal');
                setTimeout(() => location.reload(), 2000);
            }, 500);
            return;
        }
    } else {
        // 不出，清空上家出牌
        if (lastPlayPosition !== currentTurn) {
            const nextTurn = (currentTurn + 1) % 3;
            if (nextTurn === lastPlayPosition) {
                lastPlayCards = [];
                lastPlayPosition = null;
            }
        }
    }
    
    updateCardCount(currentTurn, aiCardSet.length);
    currentTurn = (currentTurn + 1) % 3;
    
    if (currentTurn === 2) {
        enablePlay();
    } else {
        setTimeout(aiPlay, 1500);
    }
}

function aiTryBeat(cards, lastCards) {
    const lastType = analyzeCardType(lastCards);
    
    // 简单策略：找最小能压过的牌
    if (lastType.type === 'single') {
        const sorted = cards.sort((a, b) => CARD_VALUES[a.value] - CARD_VALUES[b.value]);
        for (const card of sorted) {
            if (CARD_VALUES[card.value] > CARD_VALUES[lastCards[0].value]) {
                return [card];
            }
        }
    } else if (lastType.type === 'pair') {
        const pairs = findPairs(cards);
        for (const pair of pairs) {
            if (CARD_VALUES[pair[0].value] > CARD_VALUES[lastCards[0].value]) {
                return pair;
            }
        }
    }
    
    return []; // 不出
}

function findPairs(cards) {
    const counts = {};
    cards.forEach(c => {
        counts[c.value] = counts[c.value] || [];
        counts[c.value].push(c);
    });
    
    const pairs = [];
    for (const value in counts) {
        if (counts[value].length >= 2) {
            pairs.push(counts[value].slice(0, 2));
        }
    }
    
    return pairs.sort((a, b) => CARD_VALUES[a[0].value] - CARD_VALUES[b[0].value]);
}

function selectAICards(cards) {
    // 简单策略：出最小的单张
    if (cards.length === 0) return [];
    
    const sorted = cards.sort((a, b) => CARD_VALUES[a.value] - CARD_VALUES[b.value]);
    return [sorted[0]];
}

function enablePlay() {
    document.getElementById('play-btn').disabled = false;
    document.getElementById('pass-btn').disabled = (lastPlayCards.length === 0 || lastPlayPosition === 2) ? true : false;
}

function createDeck() {
    const suits = ['♠', '♥', '♣', '♦'];
    const values = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2'];
    const deck = [];
    for (const s of suits) {
        for (const v of values) {
            deck.push({ suit: s, value: v });
        }
    }
    deck.push({ suit: '', value: 'joker' });
    deck.push({ suit: '', value: 'JOKER' });
    return deck;
}

function shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
}


// 判断能否压过上家
function canBeat(myCards, lastCards) {
    const myType = analyzeCardType(myCards);
    const lastType = analyzeCardType(lastCards);
    
    if (!myType.valid) return false;
    
    // 火箭最大，可以压任何牌
    if (myType.type === 'rocket') return true;
    
    // 炸弹可以压任何非炸弹和火箭
    if (myType.type === 'bomb') {
        if (lastType.type === 'rocket') return false;
        if (lastType.type === 'bomb') {
            return myType.value > lastType.value;
        }
        return true;
    }
    
    // 如果上家是炸弹或火箭，只能用更大的炸弹或火箭压
    if (lastType.type === 'bomb' || lastType.type === 'rocket') {
        return false;
    }
    
    // 其他牌型必须类型相同
    if (myType.type !== lastType.type) {
        return false;
    }
    
    // 对于有长度的牌型（顺子、连对、飞机），长度必须相同
    if (myType.length !== undefined && myType.length !== lastType.length) {
        return false;
    }
    
    // 比较牌力（使用value字段）
    return myType.value > lastType.value;
}

function getCardValue(card) {
    return CARD_VALUES[card.value];
}
