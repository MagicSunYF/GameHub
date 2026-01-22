# 设计文档 - 小游戏集平台

## 概述

小游戏集平台是一个基于插件化架构的多游戏集合系统，采用苹果风格UI设计。平台支持三种游戏模式：人机对战、本地双人对战和联网对战。前端使用原生HTML/CSS/JavaScript，后端使用Python Flask + SocketIO实现实时通信。

## 架构

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                         前端层                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  主页    │  │  五子棋  │  │  斗地主  │  │ 极速狂飙 │   │
│  │index.html│  │  插件    │  │  插件    │  │  插件    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                    HTTP / WebSocket
                            │
┌─────────────────────────────────────────────────────────────┐
│                         后端层                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Flask Application                        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐    │  │
│  │  │ 静态文件   │  │   CORS     │  │  SocketIO  │    │  │
│  │  │   服务     │  │   配置     │  │   服务     │    │  │
│  │  └────────────┘  └────────────┘  └────────────┘    │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Game Manager (房间管理)                     │  │
│  │  - 创建/删除房间                                      │  │
│  │  - 玩家加入/离开                                      │  │
│  │  - 游戏状态管理                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              游戏插件层                               │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │  │
│  │  │ 五子棋   │  │ 斗地主   │  │ 极速狂飙 │          │  │
│  │  │ Plugin   │  │ Plugin   │  │ Plugin   │          │  │
│  │  └──────────┘  └──────────┘  └──────────┘          │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          Database (可选)                              │  │
│  │  - 游戏记录                                           │  │
│  │  - 玩家统计                                           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

- **前端**: HTML5, CSS3, JavaScript (ES6+)
- **后端**: Python 3.8+, Flask, Flask-SocketIO, Flask-CORS
- **通信**: HTTP (REST), WebSocket (Socket.IO)
- **数据库**: MySQL 8.0+ (可选)
- **部署**: 支持本地开发和生产部署

## 组件和接口

### 1. 主页组件 (index.html)

**职责**: 展示游戏列表，提供导航入口

**接口**:
```javascript
// 自动扫描游戏插件
function loadGamePlugins() {
    // 扫描所有包含 game.json 的文件夹
    // 生成游戏卡片
}

// 游戏卡片数据结构
interface GameCard {
    name: string;        // 游戏名称
    id: string;          // 游戏ID
    icon: string;        // 图标（emoji或路径）
    description: string; // 简介
    entry: string;       // 入口文件
}
```

### 2. 游戏插件接口

**game.json 配置**:
```json
{
    "name": "游戏名称",
    "id": "game-id",
    "icon": "🎮",
    "description": "特性1 · 特性2 · 特性3",
    "entry": "index.html",
    "version": "1.0.0",
    "author": "作者",
    "server": {
        "enabled": true,
        "file": "server.py",
        "port": 5000
    }
}
```

**必需文件**:
- `index.html`: 游戏入口页面
- `game.js`: 游戏逻辑
- `style.css`: 游戏样式
- `game.json`: 配置文件

**必需元素**:
```html
<h1 id="title">游戏标题</h1>
<div id="game-container">游戏主体</div>
<div id="hint">按 ESC 隐藏</div>
```

**必需功能**:
```javascript
// ESC 隐藏功能
let isHidden = false;
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        isHidden = !isHidden;
        document.querySelectorAll('#title, #game-container, #hint')
            .forEach(el => el.classList.toggle('hidden', isHidden));
    }
});
```

### 3. 后端 Flask 应用 (app.py)

**职责**: 提供HTTP服务和WebSocket服务

**接口**:
```python
def create_app(config):
    """创建Flask应用"""
    app = Flask(__name__, static_folder='..')
    
    # 配置CORS
    cors_origins = config.ALLOWED_ORIGINS if config.ALLOWED_ORIGINS else "*"
    
    # 配置SocketIO
    socketio = SocketIO(app, cors_allowed_origins=cors_origins)
    
    return app, socketio

# 路由
@app.route('/')
def index():
    """主页"""
    
@app.route('/<game>/<path:path>')
def game_files(game, path):
    """游戏文件"""
    
@app.route('/<path:path>')
def static_files(path):
    """静态文件"""
```

### 4. 游戏管理器 (game_manager.py)

**职责**: 管理所有游戏房间和玩家

**数据结构**:
```python
class GameManager:
    def __init__(self):
        self.rooms = {}  # {room_id: RoomData}

# 房间数据结构
RoomData = {
    'game_type': str,      # 游戏类型
    'players': [str],      # 玩家SID列表
    'state': dict,         # 游戏状态
    'spectators': [str]    # 观战者SID列表
}
```

**接口**:
```python
def create_room(game_type, initial_state) -> str:
    """创建房间，返回房间ID"""
    
def get_room(room_id) -> dict:
    """获取房间信息"""
    
def delete_room(room_id):
    """删除房间"""
    
def add_player(room_id, player_id) -> bool:
    """添加玩家"""
    
def remove_player(room_id, player_id) -> bool:
    """移除玩家"""
    
def add_spectator(room_id, spectator_id) -> bool:
    """添加观战者"""
```

### 5. 游戏插件基类

**职责**: 定义游戏插件的标准接口

**接口**:
```python
class GamePlugin:
    def __init__(self, app, socketio, db, game_manager):
        self.app = app
        self.socketio = socketio
        self.db = db
        self.game_manager = game_manager
        self.register_routes()
        self.register_events()
        if db:
            self.init_db()
    
    def register_routes(self):
        """注册HTTP路由"""
        pass
    
    def register_events(self):
        """注册WebSocket事件"""
        pass
    
    def init_db(self):
        """初始化数据库表"""
        pass
```

### 6. WebSocket 事件协议

**通用事件**:
```javascript
// 客户端 -> 服务器
emit('create_room', {game: 'game-id'})
emit('join_room', {room_id: string, spectator: boolean})
emit('disconnect')

// 服务器 -> 客户端
on('room_created', {room_id: string, position: number})
on('room_joined', {room_id: string, position: number})
on('spectator_joined', {room_id: string})
on('error', {msg: string})
on('player_left', {})
```

**游戏特定事件** (以五子棋为例):
```javascript
// 客户端 -> 服务器
emit('make_move', {room_id: string, row: number, col: number})
emit('send_comment', {room_id: string, comment: string})

// 服务器 -> 客户端
on('game_start', {})
on('move_made', {row: number, col: number, color: number})
on('game_over', {winner: number})
on('new_comment', {comment: string})
```

## 数据模型

### 房间模型

```typescript
interface Room {
    game_type: string;           // 游戏类型: 'gomoku' | 'landlord' | 'racing'
    players: string[];           // 玩家Socket ID列表
    state: GameState;            // 游戏状态（各游戏不同）
    spectators: string[];        // 观战者Socket ID列表
}
```

### 五子棋游戏状态

```typescript
interface GomokuState {
    board: number[][];           // 15x15棋盘，0=空 1=黑 2=白
    current: number;             // 当前回合: 1=黑 2=白
    moves: Move[];               // 历史走法
}

interface Move {
    row: number;
    col: number;
    color: 'black' | 'white';
}
```

### 斗地主游戏状态

```typescript
interface LandlordState {
    players_ready: number;       // 准备玩家数
    cards: {[position: number]: Card[]};  // 各玩家手牌
    bottom_cards: Card[];        // 底牌
    landlord: number | null;     // 地主位置
    current_turn: number;        // 当前回合
    last_play: Card[];           // 上次出的牌
    bids: {[position: number]: number};   // 叫牌记录
}

interface Card {
    suit: string;                // 花色: '♠' | '♥' | '♣' | '♦' | ''
    value: string;               // 点数: '3'-'10' | 'J' | 'Q' | 'K' | 'A' | '2' | 'joker' | 'JOKER'
}
```

### 极速狂飙游戏状态

```typescript
interface RacingState {
    players_ready: number;       // 准备玩家数
    scores: {[position: number]: number};  // 各玩家分数
    game_started: boolean;       // 游戏是否开始
}
```

### 数据库模型 (可选)

```sql
-- 游戏记录表
CREATE TABLE game_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    game_type VARCHAR(32) NOT NULL,
    moves TEXT NOT NULL,
    winner VARCHAR(32),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_game_type (game_type),
    INDEX idx_created_at (created_at)
) CHARSET=utf8mb4 ENGINE=InnoDB;
```

## 正确性属性

*属性是一个特征或行为，应该在系统的所有有效执行中保持为真。属性是人类可读规范和机器可验证正确性保证之间的桥梁。*

### 属性 1: 房间ID唯一性

*对于任意*两个不同的房间创建操作，生成的房间ID应该不同

**验证: 需求 4.1**

### 属性 2: 玩家加入房间的幂等性

*对于任意*房间和玩家，多次添加同一玩家到同一房间应该只保留一个实例

**验证: 需求 4.3**

### 属性 3: 房间人数限制

*对于任意*游戏房间，玩家数量不应超过该游戏类型定义的最大人数

**验证: 需求 4.5**

### 属性 4: 游戏状态同步

*对于任意*房间内的所有玩家，在任何时刻接收到的游戏状态应该一致

**验证: 需求 5.3, 5.4**

### 属性 5: 输入验证完整性

*对于任意*客户端输入，如果包含无效数据，系统应该拒绝并返回错误而不是崩溃

**验证: 需求 11.5**

### 属性 6: 五子棋胜利条件

*对于任意*棋盘状态，如果存在五个连续的相同颜色棋子（横/竖/斜），系统应该判定该颜色获胜

**验证: 需求 12.5, 12.6**

### 属性 7: 斗地主牌型验证

*对于任意*牌组合，系统应该正确识别其是否为合法牌型（单/对/三/顺/炸/火箭）

**验证: 需求 13.6**

### 属性 8: WebSocket消息顺序

*对于任意*房间内的消息序列，所有客户端接收到的消息顺序应该一致

**验证: 需求 5.2, 5.3**

### 属性 9: 断线重连状态恢复

*对于任意*玩家断线后重连，系统应该能恢复到断线前的游戏状态

**验证: 需求 5.6**

### 属性 10: 观战者权限隔离

*对于任意*观战者，其不应该能够执行任何影响游戏状态的操作

**验证: 需求 6.4**

## 错误处理

### 网络错误

- **连接失败**: 显示"无法连接到服务器"提示，提供重试按钮
- **连接超时**: 3秒无响应显示"连接超时"，自动尝试重连
- **断线**: 显示"连接已断开"，自动重连最多3次

### 输入验证错误

- **无效房间ID**: 返回 `{msg: '房间不存在'}`
- **房间已满**: 返回 `{msg: '房间已满'}`
- **无效坐标**: 返回 `{msg: '无效的坐标'}`
- **弹幕过长**: 截断到200字符

### 游戏逻辑错误

- **非法走法**: 显示"无效操作"提示，不更新状态
- **不是你的回合**: 忽略操作，不发送到服务器
- **重复落子**: 显示"该位置已有棋子"

### 数据库错误

- **连接失败**: 打印警告，跳过数据库功能，游戏继续运行
- **查询失败**: 记录错误日志，返回空结果
- **写入失败**: 记录错误日志，不影响游戏进行

## 测试策略

### 单元测试

**后端组件**:
- `GameManager`: 测试房间创建、玩家管理、状态更新
- `InputValidator`: 测试各种输入验证规则
- 游戏插件: 测试游戏逻辑（胜利判定、牌型识别等）

**前端组件**:
- 游戏逻辑: 测试AI算法、牌型判断、碰撞检测
- UI交互: 测试按钮点击、键盘输入、动画触发

### 集成测试

- **WebSocket通信**: 测试客户端-服务器消息传递
- **房间流程**: 测试创建房间→加入→游戏→结束完整流程
- **多人同步**: 测试多个客户端状态同步
- **观战功能**: 测试观战者加入和接收更新

### 属性测试

使用 `hypothesis` (Python) 和 `fast-check` (JavaScript) 进行属性测试：

- **房间ID生成**: 生成大量房间，验证ID唯一性
- **输入验证**: 生成随机输入，验证所有无效输入被拒绝
- **游戏状态**: 生成随机操作序列，验证状态一致性
- **牌型识别**: 生成随机牌组合，验证识别正确性

每个属性测试运行至少100次迭代。

### 端到端测试

- **完整游戏流程**: 模拟真实玩家完成一局游戏
- **断线重连**: 模拟网络中断和恢复
- **并发压力**: 模拟多个房间同时运行
- **跨浏览器**: 测试Chrome、Firefox、Safari兼容性

### 性能测试

- **并发连接**: 测试100个同时在线玩家
- **消息延迟**: 测试WebSocket消息往返时间 < 100ms
- **内存泄漏**: 长时间运行检测内存增长
- **数据库查询**: 测试查询响应时间 < 50ms
