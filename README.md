# 小游戏集

简单、优雅、有趣的小游戏合集

## 游戏列表

- **五子棋**: 联机对战 · 单人模式 · 观战弹幕
- **极速狂飙**: 躲避障碍 · 跳跃闯关 · 挑战极限

## 快速开始

1. 安装依赖:
```bash
cd server
pip install -r requirements.txt
```

2. 配置环境变量（可选）:
```bash
cp .env.example .env
# 编辑 .env 修改数据库配置
```

3. 启动服务器:
```bash
python main.py
```

4. 访问 http://localhost:5000 开始游戏

## 插件开发

查看 `GAME_PLUGIN_SPEC.md` 了解如何开发新游戏插件

## 特性

- 🎮 插件化架构，轻松扩展
- 📱 响应式设计，支持多种分辨率
- 🎨 统一的苹果风格界面
- ⌨️ 按 ESC 快速隐藏（摸鱼神器）
