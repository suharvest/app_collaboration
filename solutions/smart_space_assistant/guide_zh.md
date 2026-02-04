## 套餐: 人脸识别 {#face_recognition}

给小智装上"眼睛"，让它认识家人朋友，进门自动打招呼。

| 设备 | 用途 |
|------|------|
| SenseCAP Watcher | 带摄像头的 AI 语音助手 |
| USB-C 数据线 | 烧录固件 |

**部署完成后你可以：**
- 进门自动打招呼（识别到熟人会主动问候）
- 语音录入人脸（说"记住我的脸，我叫小明"）
- 最多存储 20 个人

**前提条件：** WiFi 网络 · [小智 App](https://github.com/78/xiaozhi-esp32) 用于绑定设备

## 步骤 1: 烧录小智固件 {#face_esp32 type=esp32_usb required=true config=devices/watcher_esp32.yaml}

### 接线

![连接设备](gallery/watcher.svg)

1. 用 USB-C 线连接 Watcher 到电脑
2. 在上方选择串口（选 wchusbserial 开头的）
3. 点击烧录按钮

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 找不到串口 | 换一条 USB 线或换个 USB 口 |
| 收不到串口数据 | 按住 BOOT 按钮，按一下 RESET，松开 BOOT，然后重试 |
| 烧录失败 | 重新插拔设备再试 |

---

## 步骤 2: 烧录人脸识别固件 {#face_himax type=himax_usb required=true config=devices/watcher_himax.yaml}

### 接线

![连接设备](gallery/watcher.svg)

1. 确保 Watcher 已连接到电脑
2. 在上方选择串口（选 usbmodem 开头的）
3. 点击烧录按钮
4. 点击烧录后，按一下设备的重启按钮进入烧录模式

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 设备无响应 | 重新插拔 USB 线 |
| 烧录卡住或失败 | 按重启按钮重试 |
| 反复烧录失败 | 换一条 USB 线或换个 USB 口 |
| 烧录到 99% 失败或中途重启 | 关闭其他占用串口的程序，重新插拔 USB 后重试 |

---

## 步骤 3: 配置小智 {#face_configure type=manual required=false}

### 连接 WiFi

设备开机后会提示配网，按语音指引完成 WiFi 连接。

### 绑定小智账号

1. 打开小智 App
2. 扫描设备上显示的二维码
3. 完成绑定

### 测试功能

说"小智小智"唤醒设备，然后说"记住我的脸，我叫小明"测试人脸录入。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| WiFi 连接失败 | 确保使用 2.4GHz 网络，检查密码 |
| 二维码不显示 | 重启设备，等待完全启动 |

---

## 步骤 4: 人脸录入指南 {#face_enrollment type=manual required=false}

### 录入人脸

1. 唤醒小智："小智小智"
2. 说："记住我的脸，我叫**你的名字**"
3. 正对摄像头，保持光线充足
4. 听到"录入成功"即完成

### 测试识别

1. 离开摄像头画面
2. 再次出现在摄像头前
3. 设备会说"检测到**你的名字**"

### 管理人脸

| 操作 | 语音命令 |
|------|----------|
| 查看已录入的人 | "你认识谁" |
| 删除某人 | "删除小明的人脸" |

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 录入失败 | 确保光线充足，正对摄像头 |
| 识别不工作 | 在更好的光线条件下重新录入 |

### 部署完成

人脸识别已就绪！

**测试方法：**
- 说「记住我的脸，我叫小明」录入人脸
- 下次进入镜头范围时，小智会主动打招呼

**语音命令：** 「你认识谁」、「删除小明的人脸」

---

## 套餐: 大屏投屏 {#display_cast}

把小智对话投射到电视或大屏幕，适合展厅、会议室等场景。

| 设备 | 用途 |
|------|------|
| SenseCAP Watcher | AI 语音助手 |
| reComputer R1100 | 运行投屏服务 |
| HDMI 显示器 | 显示投屏内容 |

**部署完成后你可以：**
- 大屏实时显示对话内容
- 按 F 进入全屏演示模式
- mDNS 自动发现 - 语音控制连接

**前提条件：** 所有设备在同一网络

## 步骤 1: 烧录 Watcher 固件 {#display_watcher type=esp32_usb required=true config=devices/display_watcher.yaml}

### 接线

![连接设备](gallery/watcher.svg)

1. 使用 USB-C 数据线连接 Watcher 到电脑
2. 在上方选择对应的串口
3. 如未检测到，请尝试其他 USB 口或更换数据线

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 找不到串口 | 换一条 USB 线或换个 USB 口 |
| 烧录失败 | 重新插拔设备再试 |

---

## 步骤 2: 部署投屏服务 {#display_service type=docker_deploy required=true config=devices/display_local.yaml}

### 部署目标: 本机部署 {#display_service_local type=local config=devices/display_local.yaml}

将投屏服务部署到您的本地电脑。

### 接线

![架构图](gallery/architecture.svg)

1. 确保 Docker 已安装并运行
2. 设置显示名称（如"客厅显示器"）用于 mDNS 发现
3. 点击部署按钮启动服务

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 找不到 Docker | 安装 Docker Desktop |
| 端口 8765 被占用 | 停止占用该端口的其他服务 |

### 部署目标: 远程部署 {#display_service_remote type=remote config=devices/recomputer.yaml default=true}

将投屏服务部署到 reComputer R1100。

### 接线

![架构图](gallery/architecture.svg)

1. 将 reComputer 连接到网络和 HDMI 显示器
2. 输入 IP 地址和 SSH 凭据
3. 设置显示名称（如"会议室显示器"）用于 mDNS 发现
4. 点击部署安装到远程设备

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | 检查 IP 地址和凭据 |
| Docker 拉取失败 | 检查网络连接，重试部署 |
| Watcher 找不到投屏设备 | 确保在同一网络，检查防火墙 |

### 部署完成

大屏投屏已就绪！

**测试方法：**
1. 在显示设备浏览器打开 `http://<设备IP>:8765`
2. 按 `F` 进入全屏模式
3. 说「投屏到[显示名称]」开始投屏

**语音命令：** 「打开投屏」、「关闭投屏」、「投屏状态」
