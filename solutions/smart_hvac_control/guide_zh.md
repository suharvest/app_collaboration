基于 KNN 预测模型的暖通空调能源优化系统，支持 OPC-UA 集成。

## 前提条件

- **Docker** 已安装并运行（版本 20.0+）
- **网络连接** 可访问镜像仓库
- **可用端口**：8280（Web 界面），4841（OPC-UA 模拟器）

## 套餐: 标准部署 {#default}

部署一套基于 KNN 算法的暖通优化系统，从历史数据中学习并给出最优参数建议。

| 设备 | 用途 |
|------|------|
| reComputer R1100 | 边缘计算设备，内置 Docker |

**部署完成后你可以：**
- 获得 AI 根据历史数据给出的温度调节建议
- 通过 OPC-UA 对接工业暖通控制器
- 通过 Web 面板监控和调参

**前提条件：** Docker 已安装 · OPC-UA 控制器（或用内置模拟器测试）

## 步骤 1: 暖通控制系统 {#hvac type=docker_deploy required=true}

### 部署目标: 本机部署 {#hvac_local type=local config=devices/local.yaml default=true}

点击下方"部署"按钮，系统将自动在本机启动暖通控制服务。

![接线图](gallery/architecture.svg)

1. 确保 Docker 已安装并运行
2. 点击部署启动容器
3. 通过 localhost:8280 访问 Web 界面

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| Docker 未运行 | 启动 Docker Desktop 应用 |
| 端口 8280 被占用 | 关闭占用该端口的程序，或修改配置使用其他端口 |
| 容器启动后停止 | 执行 `docker logs missionpack_knn` 查看错误日志 |
| 网页打不开 | 等待 30 秒让服务完全启动 |

### 部署目标: 远程部署 {#hvac_remote type=remote config=devices/remote.yaml}

点击下方"部署"按钮，系统将自动把暖通控制服务部署到远程设备。

![接线图](gallery/recomputer.svg)

1. 通过 SSH 连接远程设备
2. 远程部署 Docker 容器
3. 通过设备 IP:8280 访问 Web 界面

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | 检查 IP 地址和用户名密码是否正确 |
| 远程设备无 Docker | 先在远程设备上安装 Docker |
| 部署超时 | 检查远程设备网络，确保能访问镜像仓库 |
| 网页打不开 | 检查防火墙是否开放 8280 端口 |

---

# 部署完成

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
