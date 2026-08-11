# Security 测试样例

## SPEC-001 基线引用

| Test Case ID | 名称 | 来源 |
|---|---|---|
| `TC-SEC-001` | Prompt Injection | SPEC-001 第 49 节 |
| `TC-SEC-002` | Tool Injection | SPEC-001 第 49 节 |
| `TC-SEC-003` | Unauthorized Tool | SPEC-001 第 49 节 |

新增身份认证、RBAC、数据脱敏、越权访问、工具白名单和审计测试从 `TC-SEC-004` 开始，格式遵循 [测试样例模板](./README.md#测试样例模板)。

## 新增测试样例

## TC-SEC-004 演示用户RBAC

- 关联 Spec / FR / User Story：SPEC-002 第4节；SPEC-004 第2、3节
- 测试目标：验证后端按固定用户映射授权，客户端role字段无效。
- 前置条件：demo-rm与demo-reviewer已配置。
- 输入数据：合法、未知、缺失用户ID及伪造role。
- 执行步骤：访问上传、事实裁定、报告确认和草稿接口。
- 预期结果：未知身份401；越权403；RM看不到未确认草稿。
- 异常或边界条件：大小写和空白变体用户ID。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-SEC-005 上传内容校验

- 关联 Spec / FR / User Story：SPEC-002 第7节；SPEC-003 第14节
- 测试目标：验证扩展名、MIME、文件头、大小和数量联合校验。
- 前置条件：上传API可用。
- 输入数据：伪装扩展名、21MB文件、第11份文件和合法边界文件。
- 执行步骤：逐项上传并检查存储目录。
- 预期结果：非法文件被拒绝且不进入解析；合法边界文件创建随机storage_key。
- 异常或边界条件：Content-Length缺失或伪造。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-SEC-006 文件名路径穿越

- 关联 Spec / FR / User Story：SPEC-003 第14节
- 测试目标：验证原始文件名不能控制服务器路径。
- 前置条件：隔离的上传目录。
- 输入数据：`../`、绝对路径、保留设备名和Unicode分隔符文件名。
- 执行步骤：上传并检查实际存储位置。
- 预期结果：仅使用服务器随机名，目标始终位于案件存储目录内。
- 异常或边界条件：同名和超长文件名。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-SEC-007 Office压缩包与宏防护

- 关联 Spec / FR / User Story：SPEC-002 第7节；SPEC-005 第10节
- 测试目标：验证宏格式、异常ZIP展开大小和过多条目被拒绝。
- 前置条件：安全的恶意样例生成器。
- 输入数据：DOCM/XLSM、展开总大小100MB/100MB+1、条目5000/5001、压缩比100:1/刚超过及合法DOCX/XLSX。
- 执行步骤：上传并触发预检。
- 预期结果：超过100MB、5000条目或100:1任一上限的文件在解析前以ZIP_LIMIT_EXCEEDED拒绝；等于上限且其余校验合法时可进入UPLOADED；宏文件拒绝。
- 异常或边界条件：扩展名改为DOCX但内部含宏部件。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-SEC-008 工具与参数注入

- 关联 Spec / FR / User Story：SPEC-003 第9、14节；SPEC-004 第12节
- 测试目标：验证模型无法调用白名单外工具或传入危险参数。
- 前置条件：工具注册表和恶意模型Mock。
- 输入数据：Shell、SQL、URL、文件路径及未知工具请求。
- 执行步骤：运行工具节点并检查调用审计。
- 预期结果：仅固定三个工具和已验证参数被调用，其他请求被拒绝并记录。
- 异常或边界条件：合法工具名配额外字段。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-SEC-009 密钥与路径脱敏

- 关联 Spec / FR / User Story：SPEC-003 第14、15节；SPEC-005 第10节
- 测试目标：验证API、日志、报告和评测产物不泄露密钥或本机路径。
- 前置条件：设置仅用于测试的假密钥和含路径异常。
- 输入数据：外部API失败响应和解析异常。
- 执行步骤：执行失败路径并扫描所有输出。
- 预期结果：仅出现错误码/trace_id；假密钥和绝对路径均不存在。
- 异常或边界条件：第三方异常消息回显请求头。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-SEC-010 报告Markdown XSS

- 关联 Spec / FR / User Story：SPEC-003 第4、14节；SPEC-005 第10节
- 测试目标：验证LLM内容不能执行脚本或危险链接。
- 前置条件：前端报告渲染页。
- 输入数据：script、事件属性、javascript链接和恶意SVG片段。
- 执行步骤：生成并展示报告，运行Playwright检查DOM。
- 预期结果：危险内容被转义或清除，无脚本执行和外部请求。
- 异常或边界条件：编码和大小写绕过。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-SEC-011 公开仓库材料元数据

- 关联 Spec / FR / User Story：SPEC-003 第14、16节
- 测试目标：验证合成PDF和仓库文件不包含作者、本机路径或真实数据。
- 前置条件：待提交样例和Git工作区。
- 输入数据：5份制度PDF、22个案件和配置模板。
- 执行步骤：扫描文件元数据、文本、历史路径模式和密钥模式。
- 预期结果：仅含合成标识和公开信息；敏感模式检查通过。
- 异常或边界条件：Office/PDF生成器自动写入用户名。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-SEC-012 CI与真实API密钥隔离

- 关联 Spec / FR / User Story：SPEC-003 第11节；SPEC-005 第12、15节；AC-005-05/06
- 测试目标：验证PR/fork只用Mock，真实DashScope/MinerU仅可由手动workflow读取Secrets。
- 前置条件：GitHub Actions配置和无真实凭据的fork环境。
- 输入数据：PR、fork PR、普通push和workflow_dispatch四类事件。
- 执行步骤：检查触发条件与权限；执行Mock CI；在授权环境手动触发真实冒烟并扫描artifact。
- 预期结果：PR/fork完整通过且不请求Secrets/外网；真实冒烟不能被自动事件触发；日志和artifact不含密钥或完整原始响应。
- 异常或边界条件：来自fork的workflow_dispatch、第三方错误回显Authorization头。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-SEC-013 报告内容后端转义

- 关联 Spec / FR / User Story：SPEC-003 第10、14节；SPEC-005 第10节；AC-004-05
- 测试目标：验证报告生成器不会把材料中的HTML脚本标记原样写入Markdown。
- 前置条件：报告模板和合成事实快照。
- 输入数据：script标签、事件属性和尖括号企业名称。
- 执行步骤：生成报告并扫描Markdown正文。
- 预期结果：尖括号被转义；报告不包含原始script标签；前端后续渲染仍须使用安全Markdown策略。
- 异常或边界条件：大小写、换行和表格分隔符。
- 自动化状态：AUTOMATED
- 最近执行结果：PASS（2026-08-10；`19 passed`）。
- 证据或日志引用：`backend/tests/test_report.py::test_report_template_escapes_untrusted_fact_markup`。

## TC-SEC-014 仓库密钥、绝对路径与动态规则扫描

- 关联 Spec / FR / User Story：SPEC-003 第14、15节；SPEC-005 第10、12节；AC-005-05/06
- 测试目标：验证公开仓库文本、评测产物和规则包不包含密钥、本机绝对路径或动态执行操作符。
- 前置条件：合成数据仓库和安全扫描脚本。
- 输入数据：Python、Markdown、YAML、JSON、前端源文件及配置模板。
- 执行步骤：运行`security_scan.py --json`；检查findings为空。
- 预期结果：扫描PASS；`.env.example`只包含空配置模板；规则包不含eval/exec/shell。
- 异常或边界条件：加入假密钥、绝对路径、私钥头或动态操作符时退出码非零。
- 自动化状态：AUTOMATED
- 最近执行结果：PASS（2026-08-10）。
- 证据或日志引用：`scripts/security_scan.py`；`backend/tests/test_security.py::test_security_scan_has_no_repository_findings`。

## TC-SEC-015 上传路径、宏文件与工具白名单

- 关联 Spec / FR / User Story：SPEC-003 第9、14节；SPEC-004 第12节；AC-004-05
- 测试目标：验证文件名路径穿越被隔离、宏Office格式被拒绝、白名单外工具无法调用。
- 前置条件：隔离SQLite和临时存储目录。
- 输入数据：`..\\..\\evidence.pdf`、DOCM文件和`execute_sql`工具请求。
- 执行步骤：上传合成PDF；检查original_filename/storage_key；尝试宏文件和未知工具。
- 预期结果：文件只写入案件随机目录；DOCM返回415；未知工具抛出allowlist错误；不产生业务写入。
- 异常或边界条件：Unicode分隔符、重复幂等键和工具额外参数。
- 自动化状态：AUTOMATED
- 最近执行结果：PASS（2026-08-10；22 passed）。
- 证据或日志引用：`backend/tests/test_security.py`；`backend/app/service.py`；`backend/app/tools.py`。

## TC-SEC-016 手动真实API冒烟与密钥隔离

- 关联 Spec / FR / User Story：SPEC-005 第11、12、15节；AC-005-06
- 测试目标：验证真实DashScope调用只能由明确的workflow_dispatch触发，输出只保留模型元数据、Hash、时延和结果形状。
- 前置条件：GitHub Secrets中配置短期测试密钥，使用纯合成Query和制度句子。
- 输入数据：固定期限制度Query与一句合成制度文本。
- 执行步骤：手动勾选`enable_external=true`；运行`manual-external-smoke.yml`；下载脱敏artifact。
- 预期结果：PR/push不触发真实API；artifact不含Authorization、密钥或完整外部响应；失败只记录错误类型。
- 异常或边界条件：缺少Secret、第三方超时、Provider返回模型别名变化。
- 自动化状态：MANUAL
- 最近执行结果：NOT_RUN（需要后续明确授权和有效Secrets）。
- 证据或日志引用：`.github/workflows/manual-external-smoke.yml`；`scripts/run_external_smoke.py`。

## TC-SEC-017 真实API冒烟证据脱敏

- 关联 Spec / FR / User Story：SPEC-003 第14、15节；SPEC-005 第11、12、15节；AC-005-06
- 测试目标：验证DashScope/MinerU真实调用只记录模型、状态、时延、Hash和结果形状，不记录密钥或完整原始响应。
- 前置条件：仅通过环境变量注入测试密钥，使用合成Query和官方示例文档。
- 输入数据：`DASHSCOPE_API_KEY`、`MINERU_API_KEY`及最小冒烟输入。
- 执行步骤：运行两个冒烟脚本；检查JSON证据和日志；扫描输出敏感模式。
- 预期结果：调用成功或以错误类型可解释失败；证据中`secrets_recorded=false`；无Bearer值、Token、原始Markdown正文或本机绝对路径。
- 异常或边界条件：401/403、429、超时、任务失败和模型别名变更。
- 自动化状态：MANUAL
- 最近执行结果：PASS（2026-08-11；DashScope embedding/reranker与MinerU v4均成功，证据已脱敏）。
- 证据或日志引用：`scripts/run_external_smoke.py`；`scripts/run_mineru_smoke.py`；`artifacts/external-smoke/final-acceptance-dashscope.json`；`final-acceptance-mineru.json`。

## TC-SEC-018 非Demo模式隐藏场景初始化接口

- 关联 Spec / FR / User Story：SPEC-006 第7、8节；AC-006-03、AC-006-08
- 测试目标：验证普通启动方式不会注册Demo场景初始化路由。
- 前置条件：CREDIT_REVIEW_DEMO_MODE未设置或为false。
- 输入数据：POST /api/v1/demo/scenarios/DEMO-NORMAL-001。
- 执行步骤：检查OpenAPI路径；调用Demo接口；检查业务库和上传目录。
- 预期结果：OpenAPI不包含Demo路由；调用返回404；不产生案件、材料、任务、Run或文件。
- 异常或边界条件：大小写环境变量、进程重启、测试配置残留和直接导入应用。
- 自动化状态：AUTOMATED
- 最近执行结果：PASS（2026-08-11；默认配置OpenAPI不含Demo路径，实际POST返回404）。
- 证据或日志引用：`backend/tests/test_demo.py::test_demo_routes_are_hidden_by_default`。

## TC-SEC-019 Demo接口固定场景与输入白名单

- 关联 Spec / FR / User Story：SPEC-006 第7节；AC-006-03、AC-006-08
- 测试目标：验证Demo接口不能读取任意路径、URL或创建未登记场景。
- 前置条件：Demo模式启用；两个固定清单有效。
- 输入数据：未知scenario_id、路径穿越、编码路径、URL样式、SQL和额外请求体。
- 执行步骤：逐项请求接口；检查Problem Details、审计事件、业务库和文件系统。
- 预期结果：仅两个精确场景ID可用；恶意输入返回404或422；无任意文件/网络访问和部分写入。
- 异常或边界条件：双重编码、反斜杠、超长输入、Unicode混淆和幂等键冲突。
- 自动化状态：AUTOMATED
- 最近执行结果：PASS（2026-08-11；固定场景创建、未知场景404和任意参数不进入接口契约）。
- 证据或日志引用：`backend/tests/test_demo.py`；`backend/app/demo.py`；本地API冒烟记录。

## TC-SEC-020 报告Markdown与恶意HTML清洗

- 关联 Spec / FR / User Story：SPEC-006 第8节；AC-006-08
- 测试目标：验证报告Markdown不会通过脚本、事件属性或危险URL执行前端代码。
- 前置条件：报告页面使用禁用原始HTML并经过清洗的渲染链路。
- 输入数据：script、img onerror、svg/onload、iframe、javascript URL和HTML实体混淆样本。
- 执行步骤：将恶意内容放入报告摘要和风险解释；打开Reviewer/RM报告页面；检查DOM和浏览器事件。
- 预期结果：危险节点和属性被移除或转义；无脚本执行、外部请求或DOM注入；正常Markdown可读。
- 异常或边界条件：嵌套标签、编码绕过、超长Markdown和返回报告刷新。
- 自动化状态：AUTOMATED
- 最近执行结果：PASS（2026-08-11；报告以安全`pre`文本渲染，后端报告转义测试通过）。
- 证据或日志引用：`web/src/App.vue`；`backend/tests/test_report.py::test_report_template_escapes_untrusted_fact_markup`。

## TC-SEC-021 公开仓库与演示资产脱敏

- 关联 Spec / FR / User Story：SPEC-006 第9～11节；AC-006-09、AC-006-11
- 测试目标：验证Git跟踪文件、README、验收报告、PNG、GIF和Release资产只包含合成数据。
- 前置条件：公开交付文件和媒体已生成并暂存。
- 输入数据：git ls-files、Release材料包和全部公开媒体。
- 执行步骤：运行密钥/绝对路径/PII模式扫描；检查图片和GIF帧；核对合成数据声明与验收报告字段。
- 预期结果：无API Key、Authorization、请求ID、真实客户数据、本机路径或原始外部响应；媒体无终端和个人浏览器信息。
- 异常或边界条件：EXIF元数据、隐藏帧、压缩包内部文件、示例.env和错误日志。
- 自动化状态：MANUAL
- 最近执行结果：PASS（2026-08-11；公开文档与媒体扫描通过，四张PNG和GIF人工复核，Release资产核对通过）。
- 证据或日志引用：`scripts/check_release_docs.py`；`docs/assets/`；`docs/acceptance/poc-v0.1.0.md`；[v0.1.0 Release](https://github.com/silasxlx/creditguard-ai/releases/tag/v0.1.0)。

## TC-SEC-022 GitHub Workflow最小权限与Secrets隔离

- 关联 Spec / FR / User Story：SPEC-006 第11、12节；AC-006-10、AC-006-11
- 测试目标：验证普通push、PR和fork不能读取外部服务Secrets或调用真实DashScope/MinerU。
- 前置条件：CI、E2E和手动外部冒烟Workflow已定义。
- 输入数据：Workflow YAML、fork/PR触发条件和GitHub权限配置。
- 执行步骤：静态检查permissions、events和Secret引用；运行普通CI；核对网络调用与Artifact内容。
- 预期结果：普通Workflow仅contents:read并使用本地Mock；只有workflow_dispatch外部冒烟引用Secrets；首次发布未配置现有本机密钥。
- 异常或边界条件：pull_request_target、可写GITHUB_TOKEN、Artifact泄露、日志展开环境变量和依赖脚本绕过。
- 自动化状态：MANUAL
- 最近执行结果：PASS（2026-08-11；Workflow静态检查确认普通CI仅`contents:read`且外部Secrets仅手动Workflow引用）。
- 证据或日志引用：`.github/workflows/ci.yml`；`.github/workflows/manual-external-smoke.yml`；首次发布未上传本机密钥。
