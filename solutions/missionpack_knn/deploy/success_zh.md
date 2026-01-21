## 部署成功！

您的暖通自动化控制系统已开始运行。

### 下一步操作

1. **访问 Web 界面** - 打开浏览器并导航到应用 URL
2. **连接 OPC-UA 服务器** - 配置 OPC-UA 服务器连接或使用内置模拟器
3. **上传训练数据** - 导入历史暖通数据用于模型训练
4. **配置参数** - 设置输入/输出参数映射

### 常用命令

查看容器状态：
```bash
docker ps | grep missionpack_knn
```

查看应用日志：
```bash
docker logs missionpack_knn
```

重启应用：
```bash
docker restart missionpack_knn
```

### Kiosk 模式（可选）

您可以在设备管理页面配置 Kiosk 模式，使应用在开机时自动全屏启动。
