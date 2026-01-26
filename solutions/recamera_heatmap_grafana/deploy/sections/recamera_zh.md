## 配置 reCamera

让 reCamera 把检测到的人流数据发送到数据库。

### 操作步骤

1. 访问 [SenseCraft reCamera](https://sensecraft.seeed.cc/ai/recamera)，部署人流分布图应用到 reCamera
2. 进入 reCamera 的 Node-RED 界面，安装 `node-red-contrib-influxdb` 节点
3. 配置数据库节点：
   - URL 填写 `http://<你的电脑IP>:8086`
   - 粘贴上一步获取的 API 令牌
4. 点击 Deploy 部署流程

