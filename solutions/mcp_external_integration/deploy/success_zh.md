# 部署完成！

恭喜！所有组件已成功部署，您现在可以使用语音控制仓库管理系统了。

## 快速验证

### 测试语音命令

对您的 SenseCAP Watcher 说：

- "查询小智标准版的库存"
- "帮我入库 5 台 Watcher 小智标准版"
- "今天的库存汇总是什么？"

### 验证 Web 界面

访问 http://localhost:2125 查看：

- 仪表盘上的实时统计数据
- 库存列表中的产品信息
- 操作日志中的语音命令记录

## 常用链接

| 资源 | 地址 |
|------|------|
| 前端界面 | http://localhost:2125 |
| API 文档 | http://localhost:2124/docs |
| Wiki 文档 | https://wiki.seeedstudio.com/cn/mcp_external_system_integration/ |
| GitHub | https://github.com/suharvest/warehouse_system |

## 故障排除

如果遇到问题：

1. **MCP 桥接器断开**：检查终端是否仍在运行 `./start_mcp.sh`
2. **语音无响应**：确保 Watcher 已连接到 SenseCraft AI 平台
3. **API 调用失败**：检查 Docker 容器状态：`docker-compose -f docker-compose.prod.yml ps`

## 扩展使用

想要自定义语音命令或集成其他业务系统？

1. 参考 [Wiki 文档](https://wiki.seeedstudio.com/cn/mcp_external_system_integration/) 中的"为您的系统定制"章节
2. 修改 `mcp/warehouse_mcp.py` 添加新的工具函数
3. 更新 `mcp/config.yml` 指向您的 API 端点

感谢使用 MCP 外部系统集成方案！
