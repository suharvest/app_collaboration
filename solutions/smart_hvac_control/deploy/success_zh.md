## 部署成功！

暖通自动化控制系统已开始运行。

### 下一步操作

1. **打开控制面板** - 点击下方"访问 Web 界面"按钮
2. **连接设备** - 配置 OPC-UA 服务器地址（没有实际设备可用内置模拟器测试）
3. **上传历史数据** - 导入过去的运行数据，让系统学习最佳参数
4. **开始使用** - 设置好参数映射后，系统就能给出调参建议了

### 运维命令

查看运行状态：
```bash
docker ps | grep missionpack_knn
```

查看运行日志：
```bash
docker logs missionpack_knn
```

重启服务：
```bash
docker restart missionpack_knn
```

### Kiosk 模式（可选）

如果需要让设备开机自动全屏显示控制面板，可以在设备管理页面配置 Kiosk 模式。
