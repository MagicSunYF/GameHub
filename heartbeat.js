/**
 * WebSocket心跳检测模块
 * 用于监控连接健康状态并处理超时断线
 */

class HeartbeatManager {
    constructor(socket, options = {}) {
        this.socket = socket;
        this.pingInterval = options.pingInterval || 30000; // 30秒发送一次心跳
        this.pongTimeout = options.pongTimeout || 5000; // 5秒未收到响应视为超时
        this.maxReconnectAttempts = options.maxReconnectAttempts || 3;
        
        this.pingTimer = null;
        this.pongTimer = null;
        this.reconnectAttempts = 0;
        this.isConnected = false;
        this.onConnectionChange = options.onConnectionChange || (() => {});
        
        // 状态恢复相关
        this.stateRecovery = options.stateRecovery || null; // {save: fn, restore: fn}
        this.savedState = null;
        this.reconnectTimer = null;
        this.reconnectDelay = 1000; // 初始重连延迟1秒
        this.maxReconnectDelay = 30000; // 最大重连延迟30秒
        
        this.init();
    }
    
    init() {
        // 监听连接事件
        this.socket.on('connect', () => {
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000; // 重置重连延迟
            this.onConnectionChange('connected');
            this.startHeartbeat();
            
            // 恢复状态
            if (this.savedState && this.stateRecovery && this.stateRecovery.restore) {
                console.log('恢复游戏状态...');
                this.stateRecovery.restore(this.savedState);
                this.savedState = null;
            }
        });
        
        // 监听断开事件
        this.socket.on('disconnect', (reason) => {
            this.isConnected = false;
            this.onConnectionChange('disconnected');
            this.stopHeartbeat();
            
            // 保存状态
            if (this.stateRecovery && this.stateRecovery.save) {
                this.savedState = this.stateRecovery.save();
                console.log('已保存游戏状态');
            }
            
            // 自动重连（如果不是主动断开）
            if (reason !== 'io client disconnect') {
                this.scheduleReconnect();
            }
        });
        
        // 监听心跳响应
        this.socket.on('pong', () => {
            this.clearPongTimer();
        });
        
        // 监听重连事件
        this.socket.on('reconnect_attempt', (attemptNumber) => {
            this.reconnectAttempts = attemptNumber;
            this.onConnectionChange('reconnecting', this.reconnectAttempts);
        });
        
        this.socket.on('reconnect_failed', () => {
            this.onConnectionChange('failed');
        });
        
        // 监听连接错误
        this.socket.on('connect_error', (error) => {
            console.error('连接错误:', error.message);
            this.onConnectionChange('error', this.reconnectAttempts);
        });
    }
    
    startHeartbeat() {
        this.stopHeartbeat();
        
        this.pingTimer = setInterval(() => {
            if (this.isConnected) {
                this.sendPing();
            }
        }, this.pingInterval);
    }
    
    stopHeartbeat() {
        if (this.pingTimer) {
            clearInterval(this.pingTimer);
            this.pingTimer = null;
        }
        this.clearPongTimer();
    }
    
    sendPing() {
        this.socket.emit('ping', { timestamp: Date.now() });
        
        // 设置超时定时器
        this.pongTimer = setTimeout(() => {
            this.handleTimeout();
        }, this.pongTimeout);
    }
    
    clearPongTimer() {
        if (this.pongTimer) {
            clearTimeout(this.pongTimer);
            this.pongTimer = null;
        }
    }
    
    handleTimeout() {
        console.warn('心跳超时，连接可能已断开');
        this.onConnectionChange('timeout');
        
        // 保存状态
        if (this.stateRecovery && this.stateRecovery.save) {
            this.savedState = this.stateRecovery.save();
        }
        
        // 强制断开并重连
        this.socket.disconnect();
        this.scheduleReconnect();
    }
    
    scheduleReconnect() {
        // 清除之前的重连定时器
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
        }
        
        // 检查重连次数限制
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('已达到最大重连次数');
            this.onConnectionChange('failed');
            return;
        }
        
        // 使用指数退避策略
        const delay = Math.min(
            this.reconnectDelay * Math.pow(2, this.reconnectAttempts),
            this.maxReconnectDelay
        );
        
        console.log(`将在 ${delay}ms 后尝试重连 (第 ${this.reconnectAttempts + 1} 次)`);
        
        this.reconnectTimer = setTimeout(() => {
            this.reconnectAttempts++;
            this.onConnectionChange('reconnecting', this.reconnectAttempts);
            this.socket.connect();
        }, delay);
    }
    
    manualReconnect() {
        // 手动重连，重置计数器
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
        }
        
        this.onConnectionChange('reconnecting', 0);
        this.socket.connect();
    }
    
    destroy() {
        this.stopHeartbeat();
        
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
        }
        
        this.socket.off('connect');
        this.socket.off('disconnect');
        this.socket.off('pong');
        this.socket.off('reconnect_attempt');
        this.socket.off('reconnect_failed');
        this.socket.off('connect_error');
    }
}

// 创建连接状态指示器
function createConnectionIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'connection-indicator';
    indicator.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: 500;
        z-index: 10000;
        transition: all 0.3s ease;
        display: none;
    `;
    document.body.appendChild(indicator);
    return indicator;
}

// 更新连接状态显示
function updateConnectionStatus(status, attempts = 0) {
    let indicator = document.getElementById('connection-indicator');
    if (!indicator) {
        indicator = createConnectionIndicator();
    }
    
    const statusConfig = {
        connected: {
            text: '已连接',
            color: '#34c759',
            show: false
        },
        disconnected: {
            text: '连接已断开',
            color: '#ff3b30',
            show: true
        },
        reconnecting: {
            text: `重连中... (${attempts}/${3})`,
            color: '#ff9500',
            show: true
        },
        timeout: {
            text: '连接超时',
            color: '#ff9500',
            show: true
        },
        error: {
            text: `连接错误 (${attempts}/${3})`,
            color: '#ff3b30',
            show: true
        },
        failed: {
            text: '连接失败，请刷新页面',
            color: '#ff3b30',
            show: true
        }
    };
    
    const config = statusConfig[status];
    if (config) {
        indicator.textContent = config.text;
        indicator.style.backgroundColor = config.color;
        indicator.style.color = '#fff';
        indicator.style.display = config.show ? 'block' : 'none';
    }
}
