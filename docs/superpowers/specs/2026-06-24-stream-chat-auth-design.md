# 流式聊天登录态修复设计

## 背景与根因

用户完成首次管理员注册并成功登录后，普通 REST 请求通过 Axios 客户端发送。Axios 请求拦截器会从本地存储读取 Token，并附加 `Authorization: Bearer <token>`。

流式聊天 `/api/chat/stream` 为了读取浏览器流式响应，单独使用原生 `fetch`。该请求目前只发送 `Content-Type`，没有携带 Token，因此后端 `get_current_user` 返回 401，聊天界面显示“请先登录”。

## 本轮目标

- 已登录用户发送流式聊天请求时自动携带当前 Token。
- 流式请求收到 401 时清理失效登录态并跳转登录页，与 Axios 行为一致。
- 保持现有 SSE 事件解析、取消请求和聊天消息展示行为不变。
- 重新生成 FastAPI 提供的前端构建资源。

## 方案

新增 `frontend/src/api/authFetch.ts`，提供统一的 `authFetch(input, init)`：

1. 从 `authToken.ts` 读取当前 Token。
2. 合并调用方 Headers，存在 Token 时写入 `Authorization`。
3. 调用原生 `fetch`，保留 `Response.body` 流读取能力。
4. 收到 401 时清理 Token，并在不处于 `/login` 时跳转登录页。
5. 返回原始 `Response`，由聊天 API 继续处理 SSE 数据。

`frontend/src/api/chat.ts` 只把 `fetch('/api/chat/stream', ...)` 替换为 `authFetch('/api/chat/stream', ...)`，不改动 SSE 协议与回调接口。

## 错误处理

- 无 Token：请求照常发送，由后端返回 401，随后统一清理并跳转登录页。
- Token 过期或无效：401 触发退出逻辑，避免页面仍显示已登录用户。
- 403/500/网络错误：不清理登录态，继续由现有 `onError` 和消息提示处理。
- 调用方已传入其他请求头：保留原请求头，只补充或覆盖认证头。

## 测试与验证

- 新增前端认证请求契约测试，先证明当前流式请求缺少 Token。
- 验证 `authFetch` 在有 Token 时添加 Bearer Header，无 Token 时不添加。
- 验证 401 会清理 Token 并跳转，非 401 不清理。
- 运行后端认证与路由测试、前端类型检查、Vite 生产构建和编码回归测试。
- 检查生成的 `index.html` 引用资源均存在。

## 非本轮范围

- 管理员新增、停用、重置其他用户。
- 用户列表、角色管理和用户管理页面。
- 修改 Token 格式、有效期或后端权限模型。
