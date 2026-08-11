# Security Policy

CreditGuard AI 使用本地合成数据作为公开演示材料，不是生产银行服务。请勿上传真实客户材料、凭据、API Key 或外部服务原始响应。

## Reporting a vulnerability

请不要在公开 Issue 中提交密钥或可利用细节。请通过与仓库关联的 GitHub 账号私下联系维护者，并提供最小复现、受影响版本和影响范围。报告前请删除所有凭据和个人信息。

## Security boundaries

- Demo 模式必须显式开启；普通 API 启动不会注册 Demo 路由。
- 工具为固定白名单的只读操作，不允许任意 SQL、Shell 或 URL。
- 上传文件经过扩展名、MIME、大小、数量、宏文件、加密文件和路径检查。
- 材料内容和模型输出均视为不可信数据，报告使用清洗后的安全文本渲染。
- CI 使用确定性 Mock；外部模型调用只能通过显式手动流程和 Secrets 执行。
- 审计信息不包含 API Key、原始外部响应或本机绝对路径。

详细架构边界见 [系统架构](docs/architecture.md)。
