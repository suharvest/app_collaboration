# MCP 桥接服务

将 AI 的意图转换为仓库系统 API 调用，是连接语音助手和业务系统的关键组件。

## 工作原理

```
Watcher → SenseCraft 云 → MCP 端点 → 桥接器 → 仓库 API
```

## 配置信息

部署时需要填写：

| 字段 | 说明 | 来源 |
|------|------|------|
| MCP 端点 | WebSocket 地址 | SenseCraft AI → Watcher Agent → Configuration |
| API 密钥 | 仓库系统访问密钥 | 仓库系统 → User Management → API Key |

## 故障排除

| 问题 | 解决方案 |
|------|---------|
| 连接超时 | 检查 MCP 端点地址是否正确 |
| 网络被阻止 | 用手机热点测试，排除办公网络防火墙问题 |
| 401 未授权 | 检查 API 密钥是否正确 |
