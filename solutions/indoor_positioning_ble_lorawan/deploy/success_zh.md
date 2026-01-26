## 部署成功！

室内定位应用程序现已运行。

### 访问定位仪表板

打开浏览器访问：**http://localhost:5173**

**默认账号**：
- 用户名：`admin`
- 密码：`83EtWJUbGrPnQjdCqyKq`

> 首次登录后请立即修改密码！

### 配置地图和信标

1. **上传楼层地图**：在"地图设置"中上传您的楼层平面图
2. **标记信标位置**：点击地图，输入信标 MAC 地址，标记每个信标的安装位置
3. **配置 Webhook**：在 LoRaWAN 网络服务器（SenseCraft Data 或 ChirpStack）中，将 Webhook 地址设置为：
   ```
   http://您的电脑IP:5173/api/webhook
   ```

### 验证定位

1. 走到信标附近，按追踪器按钮触发上报
2. 在网页地图上查看追踪器位置是否正确显示
3. 如果位置不准，检查信标坐标是否标记正确

### 需要帮助？

- [Wiki 文档](https://wiki.seeedstudio.com/cn/solutions/indoor-positioning-bluetooth-lorawan-tracker/)
- [GitHub 仓库](https://github.com/Seeed-Solution/Solution_IndoorPositioning_H5)
