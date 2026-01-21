## 部署语音服务

此步骤将自动部署三个 Docker 容器到 reRouter：

| 服务 | 说明 |
|------|------|
| sensecraft-asr-server | 本地 ASR（自动语音识别）引擎 |
| sensecraft-voice-client | 语音采集和 Web 界面 |
| watchtower | 自动容器更新 |

### 前置条件

继续之前，请确保：

- reSpeaker XVF3800 已连接到 reRouter USB 口
- reRouter 可以访问互联网（在 SSH 中验证 `ping google.com` 或 `ping openwrt.org`）

### 自动部署

在下方输入 SSH 凭据。部署将：

1. 通过 SSH 连接到 reRouter
2. 创建必要的数据目录
3. 下载 ASR 模型（约 500MB）
4. 拉取 Docker 镜像
5. 启动所有服务

### 模型下载

ASR 模型包约为 500MB。下载时间取决于网络速度。

### 验证部署

部署后，通过 SSH 检查容器状态：

```bash
docker ps
```

三个容器都应显示 `Status: Up`。

### 访问 Web 界面

访问 http://192.168.49.1:8090 进入边缘客户端界面，功能包括：

- 实时 ASR 转录
- 声纹识别
- 设备配置
