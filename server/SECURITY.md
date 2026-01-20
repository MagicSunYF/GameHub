# 安全配置指南

## 环境变量配置

### 必需配置

1. **数据库密码** (DB_PASSWORD)
   - 必须设置强密码
   - 至少12位，包含大小写字母、数字和特殊字符
   - 不要使用默认密码或弱密码

2. **CORS 配置** (ALLOWED_ORIGINS)
   - 生产环境必须设置允许的域名
   - 多个域名用逗号分隔
   - 示例: `https://example.com,https://app.example.com`

### 配置示例

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
DB_PASSWORD=your_strong_password_here
ALLOWED_ORIGINS=https://yourdomain.com
```

## 安全特性

### 1. 输入验证
- 游戏ID: 只允许字母数字和连字符
- 房间ID: 防止路径遍历攻击
- 坐标验证: 防止越界访问
- 评论清理: 防止XSS攻击

### 2. CORS 保护
- 生产环境强制配置允许的源
- 开发环境显示警告
- 防止未授权的跨域访问

### 3. 数据库安全
- 强制要求设置密码
- 使用参数化查询防止SQL注入
- 连接池管理和错误处理

## 部署检查清单

- [ ] 设置强数据库密码
- [ ] 配置 ALLOWED_ORIGINS
- [ ] 禁用 DEBUG 模式
- [ ] 使用 HTTPS
- [ ] 定期更新依赖包
- [ ] 监控异常访问日志

## 漏洞报告

如发现安全问题，请通过私密渠道报告，不要公开披露。
