# 迁移指南

## 从旧版本迁移

### 主要变更

1. **服务器文件位置变更**
   - 旧: `gomoku/server.py`
   - 新: `server/main.py`

2. **配置方式变更**
   - 旧: 硬编码配置
   - 新: 环境变量配置

3. **安全增强**
   - 强制设置数据库密码
   - CORS 限制
   - 输入验证
   - 路径遍历防护

### 迁移步骤

1. 停止旧服务器
```bash
# 停止运行中的 gomoku/server.py
```

2. 安装依赖
```bash
cd server
pip install -r requirements.txt
```

3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，设置：
# - DB_PASSWORD: 强密码
# - ALLOWED_ORIGINS: 允许的域名
```

4. 启动新服务器
```bash
python main.py
```

### 配置对照表

| 旧配置 | 新配置 | 说明 |
|--------|--------|------|
| 硬编码密码 '123456' | DB_PASSWORD 环境变量 | 必须设置强密码 |
| CORS 允许所有 | ALLOWED_ORIGINS | 生产环境必须配置 |
| 无输入验证 | validators.py | 自动验证所有输入 |

### 数据库兼容性

数据库表结构保持不变，无需迁移数据。

### 客户端兼容性

前端代码无需修改，API 接口保持兼容。

### 常见问题

**Q: 启动时提示 "必须设置 DB_PASSWORD"**
A: 在 .env 文件中设置 DB_PASSWORD 环境变量

**Q: 生产环境启动失败**
A: 确保设置了 ALLOWED_ORIGINS 并禁用 DEBUG 模式

**Q: 旧的 gomoku/server.py 还能用吗？**
A: 已删除，请使用新的 server/main.py
