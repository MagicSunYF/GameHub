# 小游戏插件接入规范 v1.0

## 目录结构
```
game-name/
├── game.json          # 游戏配置文件（必需）
├── index.html         # 游戏入口页面（必需）
├── game.js            # 游戏逻辑（必需）
├── style.css          # 游戏样式（必需）
├── server.py          # 后端服务（可选）
└── assets/            # 资源文件夹（可选）
```

## game.json 配置规范

```json
{
  "name": "游戏名称",
  "id": "game-id",
  "icon": "🎮",
  "description": "游戏简介",
  "entry": "index.html",
  "version": "1.0.0",
  "author": "作者名",
  "server": {
    "enabled": false,
    "file": "server.py",
    "port": 5000
  }
}
```

### 字段说明
- `name`: 游戏显示名称
- `id`: 游戏唯一标识符（小写字母+连字符）
- `icon`: 游戏图标（emoji或图片路径）
- `description`: 游戏简介（建议3个特性用 · 分隔）
- `entry`: 入口HTML文件名
- `version`: 版本号
- `author`: 作者信息
- `server`: 后端服务配置（可选）
  - `enabled`: 是否需要后端服务
  - `file`: 服务文件名
  - `port`: 服务端口

## 样式规范

### 必需元素
```html
<h1 id="title">游戏标题</h1>
<div id="game-container">游戏主体</div>
<div id="hint">按 ESC 隐藏</div>
```

### 样式要求
- 背景: `linear-gradient(135deg, #1d1d1f 0%, #000 100%)`
- 主色调: `#f5f5f7` (浅色文字)
- 次要色: `#86868b` (灰色文字)
- 按钮样式: 半透明背景 + 圆角 + 毛玻璃效果
- 字体: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`

### 必需CSS类
```css
.hidden {
    opacity: 0;
    pointer-events: none;
}
```

## 交互规范

### 键盘事件
- `ESC`: 隐藏/显示游戏界面
- 游戏控制键由各游戏自定义

### 隐藏功能实现
```javascript
let isHidden = false;
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        isHidden = !isHidden;
        document.querySelectorAll('#title, #game-container, #hint')
            .forEach(el => el.classList.toggle('hidden', isHidden));
    }
});
```

## 接入流程

1. 创建游戏文件夹（使用游戏ID命名）
2. 按规范创建必需文件
3. 编写 game.json 配置
4. 实现游戏逻辑和样式
5. 测试隐藏功能和样式一致性
6. 将文件夹放入项目根目录

## 自动发现机制

主页会自动扫描所有包含 `game.json` 的文件夹，并根据配置生成游戏卡片。

## 示例参考

- 五子棋: `gomoku/`
- 极速狂飙: `racing/`
