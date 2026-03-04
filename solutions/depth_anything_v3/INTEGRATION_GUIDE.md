# Depth Anything V3 Solution 集成说明

本文档说明如何在本仓库中从零集成 `depth_anything_v3` 方案，并确保该方案可在前端页面显示、可点击一键部署到 Jetson。

## 1. 目标与范围

- 方案名称：Depth Anything V3 on Jetson
- 方案 ID：`depth_anything_v3`
- 部署方式：`docker_deploy` + `remote target`（底层设备类型是 `docker_remote`）
- 体验目标：用户在前端只需填写设备连接信息并点击 Deploy，无需手动输入命令

## 2. 目录结构

在 `solutions/depth_anything_v3` 下保持如下结构：

```text
solutions/depth_anything_v3/
├── solution.yaml
├── description.md
├── description_zh.md
├── guide.md
├── guide_zh.md
├── devices/
│   └── jetson.yaml
├── assets/
│   └── jetson/
│       └── docker-compose.yml
├── gallery/
│   ├── da3.png
│   └── engine.png
└── INTEGRATION_GUIDE.md
```

## 3. 第一步：准备 Docker 资产

将原项目里的 `docker run` 参数迁移为 Compose，写入：

- `assets/jetson/docker-compose.yml`

关键点：

- 使用固定镜像 tag，例如 `chenduola6/depth-anything-v3:jp6.2`
- Jetson GPU 运行时参数保留：`runtime: nvidia`
- 保留网络和设备能力：`network_mode: host`、`ipc: host`、`privileged: true`
- 映射 X11 和设备目录：`/tmp/.X11-unix`、`/dev`

本方案采用保持容器常驻的命令：

```yaml
command: ["bash", "-lc", "sleep infinity"]
```

## 4. 第二步：定义设备部署配置

在 `devices/jetson.yaml` 中定义远程部署设备，核心字段如下：

- `type: docker_remote`
- `docker_remote.compose_file: assets/jetson/docker-compose.yml`
- `docker_remote.compose_dir: assets/jetson`
- `docker_remote.remote_path: /home/{{username}}/depth-anything-v3`
- `user_inputs`: `host` / `username` / `password` / `display`

### 4.1 环境预检查（强烈建议）

通过 `actions.before` 执行 Jetson 兼容性检查：

- 是否为 Jetson（检查 `/etc/nv_tegra_release`）
- Docker 是否可用
- NVIDIA runtime 是否可用
- L4T 版本是否在允许范围
- 可用磁盘空间是否足够

这样可以把失败前置，避免用户点击部署后才在中途报错。

## 5. 第三步：配置 solution 元数据

在 `solution.yaml` 中定义方案基础信息。

必须项：

- `id: depth_anything_v3`
- `name` / `name_zh`
- `intro.summary` / `intro.summary_zh`
- `intro.description_file` / `intro.description_file_zh`
- `intro.cover_image`
- `intro.presets`
- `deployment.guide_file` / `deployment.guide_file_zh`

注意：

- `id` 需符合 `^[a-z][a-z0-9_]*$`
- 建议目录名与 `id` 一致，降低维护成本

## 6. 第四步：编写部署指南 guide

在 `guide.md` 与 `guide_zh.md` 中按规范写结构化步骤。

### 6.1 必须包含的标题格式

- Preset：
  - `## Preset: ... {#preset_id}`
  - `## 套餐: ... {#preset_id}`
- Step：
  - `## Step N: ... {#step_id type=docker_deploy required=true config=devices/jetson.yaml}`
  - `## 步骤 N: ... {#step_id type=docker_deploy required=true config=devices/jetson.yaml}`
- Target：
  - `### Target: ... {#target_id type=remote config=devices/jetson.yaml default=true}`
  - `### 部署目标: ... {#target_id type=remote config=devices/jetson.yaml default=true}`
- Troubleshooting：
  - `### Troubleshooting`
  - `### 故障排查`
- 结尾：
  - `# Deployment Complete`
  - `# 部署完成`

### 6.2 一致性要求

`guide.md` 和 `guide_zh.md` 的以下 ID 必须严格一致：

- preset ID
- step ID
- target ID

## 7. 第五步：补齐介绍文档与素材

完成以下文件：

- `description.md`
- `description_zh.md`
- `gallery/da3.png`
- `gallery/engine.png`

建议内容：

- 方案能做什么
- 核心价值
- 适用场景
- 使用须知（Jetson、Docker、网络等前提）

## 8. 第六步：启动服务并验证前端显示

在仓库根目录运行开发环境（Windows）：

```bat
dev-stop.bat
dev.bat
```

或者仅启动后端：

```bat
dev-backend.bat
```

然后验证：

1. 打开前端页面 `http://localhost:5173`
2. 刷新页面（建议 `Ctrl+F5`）
3. 在方案列表确认出现 `depth_anything_v3`
4. 进入详情页确认 Preset/Step/Target 正常显示
5. 尝试部署，确认能输入 Jetson 连接信息并执行流程

## 9. 常见问题与排查

### 9.1 前端不显示新方案

排查顺序：

1. 后端是否重启并重新加载 `solutions` 目录
2. `solution.yaml` 是否可被 YAML 正常解析
3. `solution.yaml` 中 `id` 是否合法，是否与目录语义一致
4. 前端是否有筛选条件（先切到 All）

### 9.2 进入部署页报错或步骤为空

排查顺序：

1. `guide.md` 标题格式是否符合解析规范
2. `config=devices/xxx.yaml` 路径是否真实存在
3. 中英文 guide 的 preset/step/target ID 是否一致

### 9.3 远程部署失败

排查顺序：

1. SSH 参数是否正确（IP/账号/密码）
2. 目标设备 Docker 是否可用
3. `nvidia` runtime 是否可用
4. 磁盘空间是否满足最小要求

## 10. 维护建议

- 新增镜像版本时只改 `assets/jetson/docker-compose.yml` 的 `image` tag
- Jetson 兼容策略优先写在 `devices/jetson.yaml` 的 `actions.before`
- 方案 ID 不要频繁变更，避免历史链接与前端缓存混乱
- 修改 `guide*` 后建议做一次结构一致性检查并重启后端验证

---

如果你要基于该方案再复制一个新方案，建议直接拷贝 `depth_anything_v3` 目录作为模板，只替换：

- `solution.yaml` 的 `id/name/summary/tags`
- `assets/jetson/docker-compose.yml` 镜像和参数
- `devices/jetson.yaml` 的环境检查规则
- `guide.md` / `guide_zh.md` 的业务描述
