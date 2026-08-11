# 工具评测夹具

`tools-v1.json` 只描述合成工具画像和白名单，不保存任何真实客户数据。运行时仍由
`ReadOnlyToolRegistry` 生成带时点的工具快照；模型不能根据材料内容选择工具、生成 SQL、
调用 Shell 或访问任意 URL。
