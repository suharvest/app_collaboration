## 热力图校准和配置

热力图页面在您的平面图上显示实时人流可视化。

### 第一步：从 reCamera 捕获参考图像

1. 在 reCamera Node-RED 工作区中，停止正在运行的程序
2. 拖动一个 **capture** 节点并连接到 **camera** 节点之后
3. 配置 capture 节点：
   - 间隔：2000（2 秒）
   - 保存到：/userdata/Images/
4. 点击 **Deploy** 和 **Run**
5. 等待 3-4 秒，然后点击 **Stop**

### 第二步：将图像下载到电脑

1. 进入 reCamera **Settings** > **Terminal**
2. 使用您的 reCamera 凭据登录
3. 运行：
```bash
cd /userdata/Images/
ls
```
4. 在您的电脑上，使用 SCP 下载：
```bash
scp -r recamera@<reCamera-IP>:/userdata/Images ./
```

### 第三步：准备平面图

绘制或使用您要监控区域的现有平面图图像。

### 第四步：运行校准工具

1. 从 [GitHub](https://github.com/xr686/reCamera-with-Heatmap) 下载项目
2. 安装 OpenCV：`pip install opencv-python`
3. 将您的相机图像命名为 `R1.jpg`，平面图命名为 `R2.png`
4. 运行：`python calibration_tool.py`
5. 在相机图像上点击 4 个角（顺时针：左上、右上、右下、左下）
6. 按任意键
7. 在平面图上点击对应的 4 个角
8. 按任意键
9. 复制生成的 JavaScript 代码

### 第五步：配置热力图 HTML

编辑 heatmap-demo 文件夹中的 `index.html`：

1. **背景图片**：更新为您的平面图文件名
2. **数据库配置**：
   - URL：您的 InfluxDB URL
   - ORG：您的 InfluxDB 用户名
   - BUCKET：您的存储桶名称（recamera）
   - TOKEN：您的 InfluxDB API 令牌
3. **相机分辨率**：匹配您的 reCamera 设置（如 1920x1080）
4. **校准数据**：粘贴生成的 JavaScript 代码

### 第六步：启动热力图服务器

```bash
cd heatmap-demo
python -m http.server 8080
```

访问热力图：http://localhost:8080/index.html
