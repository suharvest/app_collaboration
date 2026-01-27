# 仓库管理系统

提供库存管理、入库出库等核心功能的 REST API，是整个语音控制方案的业务后端。

## 部署后设置

部署完成后，需要手动完成以下设置：

### 1. 创建管理员账户

1. 打开 `http://localhost:2125`
2. 填写用户名和密码，点击 **Register**

> 第一个注册的用户自动成为管理员

### 2. 创建 API 密钥

1. 登录后进入 **User Management**
2. 在 **API Key Management** 区域输入密钥名称
3. 点击 **Create API Key**
4. **立即复制密钥**（格式：`wh_xxxx...`，仅显示一次）

## 验证

- 前端界面：`http://localhost:2125`
- API 文档：`http://localhost:2124/docs`
