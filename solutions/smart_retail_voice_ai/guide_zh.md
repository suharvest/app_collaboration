## 套餐: 标准部署 {#default}

为你的门店部署一套边缘语音采集分析系统。

| 设备 | 用途 |
|------|------|
| reRouter CM4 | 边缘计算设备，运行语音服务 |
| reSpeaker XVF3800 | 4麦克风阵列，采集门店对话 |

**部署完成后你可以：**
- 实时转录门店内的顾客对话
- 声纹识别——自动分辨不同说话人
- 对接 [SenseCraft Voice](https://voice.sensecraft.seeed.cc/) 云平台，多门店数据汇总分析
- 隐私优先——音频在本地处理，不上传原始录音

**前提条件：** USB-C 数据线 · 网线

## 步骤 1: 刷写 OpenWrt 固件 {#firmware type=manual required=false}

将操作系统写入 reRouter，然后连接到网络。**2025 年 11 月之后购买的新品可跳过此步骤**——已预装正确固件。

| 设备 | 连接方式 | 注意事项 |
|------|---------|---------|
| reRouter CM4 | 取出 SD 卡或 eMMC 模块 | 用于刷写固件 |
| SD 卡/eMMC | 插入读卡器连接电脑 | 建议使用 USB 3.0 读卡器 |

**刷写步骤**：

1. 下载固件：[全球版](https://files.seeedstudio.com/wiki/solution/ai-sound/reRouter-firmware-backup/OpenWRT-24.10.3-RPi-4-Factory.img.gz) | [中国版](https://files.seeedstudio.com/wiki/solution/ai-sound/reRouter-firmware-backup/OpenWRT-24.10.3-RPi-4-Factory-Chinese.img.gz)
2. 下载 [Raspberry Pi Imager](https://www.raspberrypi.com/software/) 刷机工具
3. 选择"自定义镜像"，选择下载的固件文件
4. 选择目标存储设备（SD 卡或 eMMC）
5. 点击"写入"，等待完成
6. 将存储设备装回 reRouter，接线上电

**首次连接**：

1. 用网线将电脑连接到 reRouter 的 **LAN 口**
2. 用另一根网线将 **WAN 口** 连接到路由器
3. 等待 1-2 分钟启动完成
4. 浏览器访问 `http://192.168.49.1`
5. 登录：用户名 `root`，密码留空

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 无法访问 192.168.49.1 | 确认网线插在 LAN 口而非 WAN 口 |
| 页面加载缓慢 | 等待 2 分钟让系统完全启动 |
| 刷机失败 | 格式化存储设备后重试 |
| 登录失败 | 密码为空，直接点登录 |

---

## 步骤 2: 部署语音服务 {#voice_services type=docker_deploy required=true config=devices/rerouter.yaml}

在设备上启动语音识别和分析服务。

### 部署目标: 本机部署 {#voice_services_local type=local config=devices/voice_local.yaml}

在本地电脑上部署语音服务。

### 接线

| 设备 | 连接方式 | 注意事项 |
|------|---------|---------|
| reSpeaker XVF3800 | USB 连接到电脑 | 确保使用数据线，不是充电线 |
| 电脑 | 需安装 Docker Desktop | Windows/Mac 需下载安装 |

1. 确保 Docker Desktop 已安装并运行
2. 确认 reSpeaker XVF3800 已通过 USB 连接
3. 确认至少 2GB 可用磁盘空间，端口 8090 未被占用
4. 验证 reSpeaker 被识别：**Windows** 设备管理器 > 声音控制器；**Mac** 系统偏好设置 > 声音 > 输入；**Linux** 执行 `arecord -l`

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| Docker 未运行 | 启动 Docker Desktop 应用 |
| 端口 8090 被占用 | 关闭占用该端口的程序，或修改配置使用其他端口 |
| 找不到麦克风设备 | 重新插拔 USB，确认设备管理器中有显示 |
| 容器启动失败 | 检查 Docker 日志：`docker logs sensecraft-voice-client` |

### 部署目标: 远程部署 {#voice_services_remote type=remote config=devices/rerouter.yaml default=true}

将语音服务部署到远程设备（reRouter、树莓派等）。

### 接线

![接线图](gallery/wan_lan.png)

| 设备 | 连接方式 | 注意事项 |
|------|---------|---------|
| reSpeaker XVF3800 | USB 连接到 reRouter | 部署时会自动配置音频参数 |
| reRouter CM4 | WAN 口接路由器 | 需要联网下载容器镜像 |
| reRouter CM4 | LAN 口接电脑 | 用于 SSH 访问和部署操作 |
| 电脑 | 与 reRouter 在同一网络 | 用于执行远程部署 |

1. 确认 reRouter WAN 口已连接路由器且能上网
2. 电脑网线接 reRouter LAN 口
3. 默认 SSH：IP `192.168.49.1`，用户 `root`，无密码
4. 将 reSpeaker XVF3800 插入 reRouter USB 口

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| SSH 连接被拒绝 | 确认网线插在 LAN 口，IP 是否正确 |
| 认证失败 | OpenWrt 默认密码为空，直接回车 |
| 镜像下载超时 | 检查 WAN 口网络连接，确认能访问互联网 |
| 容器启动失败 | SSH 登录后执行 `docker logs sensecraft-voice-client` 查看错误信息 |
| 找不到麦克风 | 执行 `arecord -l`，确认 reSpeaker 被识别 |
| 日志中出现 "Health check failed" | 启动时正常现象——语音客户端先于 ASR 服务就绪，等待 30 秒后自动恢复 |

---

# 部署完成

语音 AI 系统已就绪！

## 服务访问

部署完成后，可访问以下服务：

| 服务 | 访问地址 | 用途 |
|------|---------|------|
| 边缘客户端 | http://\<设备IP\>:8090 | 实时转录、声纹管理、设备配置 |
| OpenWrt 管理 | http://\<设备IP\> | 网络配置、系统管理 |
| SenseCraft Voice 云平台 | https://voice.sensecraft.seeed.cc/ | 多门店分析、AI 分析、数据导出 |

## 初始设置

1. **重启设备** — SSH 执行 `reboot` 命令，等待 2 分钟
2. **打开边缘客户端** — 浏览器访问 `http://<设备IP>:8090`
3. **测试语音识别** — 在 reSpeaker 附近说话，观察实时转录结果

## 边缘客户端 (http://\<设备IP\>:8090)

边缘客户端提供本地语音处理和设备管理功能：

![边缘客户端](gallery/edge-client-asr.png)

| 功能 | 说明 |
|------|------|
| 实时语音对话 | 实时语音转文字——验证音频输入和识别准确性 |
| 说话人管理 | 注册声纹，自动识别不同说话人 |
| 设备配置 | 修改网络设置（WiFi）和上游服务器地址，用于云端同步 |

## 云端管理平台 (https://voice.sensecraft.seeed.cc/)

将边缘设备连接到 SenseCraft Voice 云平台，获取高级分析功能：

| 模块 | 说明 |
|------|------|
| **仪表板** | 数据总览，支持门店筛选、每日采集趋势、关键词热点分析 |
| **记录管理** | 搜索、筛选和导出语音记录，支持对话模式和时间线模式（含音频回放） |
| **AI 分析** | 将语音记录提交给 AI 进行自定义处理，基于你设定的提示词 |
| **门店管理** | 按门店、位置、设备名称组织设备，支持层级管理 |
| **后端配置** | 配置关键词和同义词进行事件检测，管理 AI 提示词和用户权限 |

**连接云平台的方法：**
1. 打开边缘客户端 > 设备状态页面
2. 上游服务器地址已预先配置
3. 设备会自动注册并出现在云平台中

## 快速验证

- 在 reSpeaker 麦克风附近说话
- 查看边缘客户端的实时转录
- 确认文字出现在网页看板上
- 检查声纹识别是否能区分不同说话人

## 后续步骤

- [查看 Wiki 文档](https://wiki.seeedstudio.com/cn/solutions/smart-retail-voice-ai-solution-1/)
- [SenseCraft Voice 平台](https://voice.sensecraft.seeed.cc/)
- [购买硬件](https://www.seeedstudio.com.cn/solutions/voicecollectionanalysis-zh-hans)
