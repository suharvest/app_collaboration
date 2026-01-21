## 部署完成！

您的实时热力图系统现已运行。

### 访问入口

| 服务 | URL |
|------|-----|
| Grafana 仪表板 | http://localhost:3000 |
| 热力图页面 | http://localhost:8080/index.html |
| InfluxDB 界面 | http://localhost:8086 |

### Grafana 登录

- 用户名：`admin`
- 密码：`admin`（首次登录时更改）

### 下一步

1. **校准热力图** - 运行 Python 校准工具，将相机坐标映射到您的平面图
2. **自定义仪表板** - 添加或修改 Grafana 面板以满足您的需求
3. **调整热力图设置** - 在 index.html 中配置刷新间隔和累积模式

### 故障排除

- **Grafana 中没有数据**：检查 reCamera 是否已连接且 Node-RED 流程已部署
- **热力图无法加载**：验证 index.html 中的 InfluxDB 凭据
- **视频流断开**：这是正常的，由于 reCamera 资源限制；它会自动重新连接
