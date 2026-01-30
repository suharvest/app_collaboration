本方案部署一套完整的边缘语音采集分析系统，专为零售环境设计。

## 硬件连接总览

| 设备 | 连接到 | 接口 | 用途 |
|------|--------|------|------|
| reRouter CM4 | 路由器 | WAN 口（网线） | 联网上传数据 |
| reRouter CM4 | 电脑 | LAN 口（网线） | 配置和访问管理界面 |
| reSpeaker XVF3800 | 电脑 | USB-C | 初次配置麦克风参数 |
| reSpeaker XVF3800 | reRouter CM4 | USB-A | 正式使用时的连接方式 |

## 连接示意图

```
┌─────────────┐                    ┌─────────────┐
│   路由器    │ ───── WAN 口 ───── │  reRouter   │
│  (互联网)   │                    │    CM4      │
└─────────────┘                    └──────┬──────┘
                                          │
                                     LAN 口 / USB 口
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
              ┌─────┴─────┐         ┌─────┴─────┐         ┌─────┴─────┐
              │   电脑    │         │ reSpeaker │         │  其他设备  │
              │(配置管理) │         │ XVF3800   │         │  (可选)   │
              └───────────┘         └───────────┘         └───────────┘
```

## 前置条件

| 物品 | 说明 |
|------|------|
| reRouter CM4 | 至少 4GB 内存和 32GB 存储 |
| reSpeaker XVF3800 | 四麦克风阵列 |
| USB-C 数据线 | 用于配置 reSpeaker（步骤二） |
| 网线 x2 | 一根接 WAN 口联网，一根接 LAN 口连电脑 |
| 电脑 | Windows/Mac/Linux，用于刷固件和配置 |

## 部署步骤概览

1. **刷写固件** - 给 reRouter 刷入 OpenWrt 系统
2. **配置麦克风** - 设置 reSpeaker 的音频参数
3. **部署服务** - 一键部署语音采集和分析容器

## 套餐: 标准部署 {#default}

## 步骤 1: 刷写 OpenWrt 固件 {#firmware type=manual required=true config=devices/firmware.yaml}

### 硬件连接

| 设备 | 连接方式 | 注意事项 |
|------|---------|---------|
| reRouter CM4 | 取出 SD 卡或 eMMC 模块 | 用于刷写固件 |
| SD 卡/eMMC | 插入读卡器连接电脑 | 建议使用 USB 3.0 读卡器 |

### 刷写步骤

1. 下载固件：[全球版](https://files.seeedstudio.com/wiki/solution/ai-sound/reRouter-firmware-backup/openwrt-bcm27xx-bcm2711-rpi-4-ext4-factory-global.img.gz) | [中国版](https://files.seeedstudio.com/wiki/solution/ai-sound/reRouter-firmware-backup/openwrt-bcm27xx-bcm2711-rpi-4-ext4-factory-cn.img.gz)
2. 下载 [Raspberry Pi Imager](https://www.raspberrypi.com/software/) 刷机工具
3. 选择"自定义镜像"，选择下载的固件文件
4. 选择目标存储设备（SD 卡或 eMMC）
5. 点击"写入"，等待完成
6. 将存储设备装回 reRouter，接线上电

### 首次连接

1. 用网线将电脑连接到 reRouter 的 **LAN 口**
2. 用另一根网线将 **WAN 口** 连接到路由器
3. 等待 1-2 分钟启动完成
4. 浏览器访问 `http://192.168.49.1`
5. 登录：用户名 `root`，密码留空

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| 无法访问 192.168.49.1 | 确认网线插在 LAN 口而非 WAN 口 |
| 页面加载缓慢 | 等待 2 分钟让系统完全启动 |
| 刷机失败 | 格式化存储设备后重试 |
| 登录失败 | 密码为空，直接点登录 |

---

## 步骤 2: 配置 reSpeaker 麦克风 {#respeaker type=manual required=true config=devices/respeaker.yaml}

### 硬件连接

| 设备 | 连接方式 | 注意事项 |
|------|---------|---------|
| reSpeaker XVF3800 | USB-C 连接**电脑** | 配置阶段必须连电脑，不要连 reRouter |
| 电脑 | 需要终端/命令行 | Windows 用 PowerShell，Mac/Linux 用终端 |

### 为什么要配置

reSpeaker 出厂默认启用了回声消除功能，会影响本方案的录音效果。需要关闭这个功能。

### 配置步骤

1. 用 USB-C 线将 reSpeaker 连接到**电脑**（注意：不是 reRouter）
2. 确认电脑识别到设备（Windows 设备管理器 / Mac 系统信息）
3. 下载配置工具：
   ```bash
   git clone https://github.com/respeaker/reSpeaker_XVF3800_USB_4MIC_ARRAY.git
   cd reSpeaker_XVF3800_USB_4MIC_ARRAY
   ```
4. 进入对应系统目录（`windows` / `macos` / `linux`）
5. 执行配置命令：
   ```bash
   # Mac/Linux 需要加 sudo
   sudo ./xvf_host clear_configuration 1
   sudo ./xvf_host audio_mgr_op_r 8 0
   sudo ./xvf_host save_configuration 1
   ```
6. 配置完成后，**断开电脑**，将 reSpeaker 连接到 **reRouter 的 USB 口**

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| 电脑未识别设备 | 换一根 USB 线，确保是数据线不是充电线 |
| 命令执行报错 | 确认进入了正确的系统目录 |
| Permission denied | Mac/Linux 需要加 sudo，Windows 用管理员运行 |
| 配置后没效果 | 断电重插 reSpeaker 让配置生效 |

---

## 步骤 3: 部署语音服务 {#voice_services type=docker_deploy required=true config=devices/rerouter.yaml}

### 部署目标: 本机部署 {#voice_services_local config=devices/voice_local.yaml}

### 硬件连接

| 设备 | 连接方式 | 注意事项 |
|------|---------|---------|
| reSpeaker XVF3800 | USB 连接到电脑 | 确保已完成步骤二的配置 |
| 电脑 | 需安装 Docker Desktop | Windows/Mac 需下载安装 |

### 前提条件

- Docker Desktop 已安装并运行
- reSpeaker XVF3800 已通过 USB 连接
- 至少 2GB 可用磁盘空间
- 端口 8090 未被占用

### 验证连接

部署前，确认 reSpeaker 被识别：
- **Windows**: 设备管理器 > 声音、视频和游戏控制器
- **Mac**: 系统偏好设置 > 声音 > 输入，选择 XVF3800
- **Linux**: 执行 `arecord -l` 查看录音设备

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| Docker 未运行 | 启动 Docker Desktop 应用 |
| 端口 8090 被占用 | 关闭占用该端口的程序，或修改配置使用其他端口 |
| 找不到麦克风设备 | 重新插拔 USB，确认设备管理器中有显示 |
| 容器启动失败 | 检查 Docker 日志：`docker logs <容器名>` |

### 部署目标: 远程部署 {#voice_services_remote config=devices/rerouter.yaml default=true}

### 硬件连接

| 设备 | 连接方式 | 注意事项 |
|------|---------|---------|
| reSpeaker XVF3800 | USB 连接到 reRouter | 确保已完成步骤二的配置 |
| reRouter CM4 | WAN 口接路由器 | 需要联网下载容器镜像 |
| reRouter CM4 | LAN 口接电脑 | 用于 SSH 访问和部署操作 |
| 电脑 | 与 reRouter 在同一网络 | 用于执行远程部署 |

### 开始之前

1. **确认设备联网**
   - reRouter WAN 口已连接路由器
   - 在 reRouter 管理界面确认有互联网连接

2. **记录连接信息**

| 字段 | 默认值 | 说明 |
|------|--------|------|
| 设备 IP | 192.168.49.1 | 从 LAN 口访问的地址 |
| SSH 用户名 | root | OpenWrt 默认用户 |
| SSH 密码 | （空） | 默认无密码 |

### 连接示意

```
┌────────┐     WAN      ┌──────────┐     LAN      ┌────────┐
│ 路由器 │ ──────────── │ reRouter │ ──────────── │  电脑  │
└────────┘              └────┬─────┘              └────────┘
                             │ USB
                        ┌────┴─────┐
                        │ reSpeaker│
                        └──────────┘
```

![接线图](intro/gallery/wan_lan.png)

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| SSH 连接被拒绝 | 确认网线插在 LAN 口，IP 是否正确 |
| 认证失败 | OpenWrt 默认密码为空，直接回车 |
| 镜像下载超时 | 检查 WAN 口网络连接，确认能访问互联网 |
| 容器启动失败 | SSH 登录后执行 `docker logs` 查看错误信息 |
| 找不到麦克风 | 执行 `arecord -l`，确认 reSpeaker 被识别 |

---

# 部署完成

## 部署成功！

智能零售语音 AI 方案已成功部署。

### 后续步骤

1. **重启设备** - 强烈建议重启以确保所有设置生效：
   ```bash
   reboot
   ```

2. **访问语音客户端** - 重启后访问：
   - http://192.168.49.1:8090

3. **测试语音识别** - 在 reSpeaker 附近说话，验证实时转录是否出现

4. **配置云平台**（可选）- 连接到 SenseCraft Voice 云平台以使用：
   - 多门店管理
   - AI 驱动分析
   - 关键词热点分析

### 故障排除

如果服务未正常运行：

```bash
# 检查容器状态
docker ps

# 查看语音客户端日志
docker logs sensecraft-voice-client

# 检查音频设备
ls -l /dev/snd/
```
