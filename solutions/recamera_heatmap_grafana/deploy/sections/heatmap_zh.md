### 配置热力图

1. 从 reCamera 导出相机截图，准备平面图
2. 运行校准工具：`python calibration_tool.py`，在相机图和平面图上各点击 4 个对应点
3. 将生成的校准代码粘贴到 `index.html`，配置 InfluxDB 连接信息
4. 启动服务：`python -m http.server 8080`，访问 `http://localhost:8080`
