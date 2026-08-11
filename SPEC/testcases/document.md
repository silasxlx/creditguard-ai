# Document 测试样例

## SPEC-001 基线引用

| Test Case ID | 名称 | 来源 |
|---|---|---|
| `TC-DOC-001` | 正常 PDF | SPEC-001 第 46 节 |
| `TC-DOC-002` | OCR 错误 | SPEC-001 第 46 节 |
| `TC-DOC-003` | 字段冲突 | SPEC-001 第 46 节 |

新增文档解析、OCR、表格恢复、事实抽取、来源定位和材料矛盾测试从 `TC-DOC-004` 开始，格式遵循 [测试样例模板](./README.md#测试样例模板)。

## 新增测试样例

## TC-DOC-004 上传格式与数量基础契约

- 关联 Spec / FR / User Story：SPEC-002 第7节；SPEC-004 第3节
- 测试目标：验证仅接收PDF/DOCX/XLSX及20MB/10份限制。
- 前置条件：案件已创建。
- 输入数据：允许格式、旧Office、宏文件、图片、超限文件和第11份材料。
- 执行步骤：逐类上传并记录响应。
- 预期结果：允许文件创建版本；其余返回明确Problem Details且不落入有效材料。
- 异常或边界条件：扩展名与MIME不一致。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-DOC-005 PDF本地解析与MinerU兜底

- 关联 Spec / FR / User Story：SPEC-003 第4节；AC-003-04
- 测试目标：验证文本PDF本地解析，低质量PDF按固定阈值调用MinerU适配器并规范化稳定输出。
- 前置条件：PyMuPDF与MinerU Mock可用。
- 输入数据：正常文本PDF、零文本扫描PDF、平均每页49和50个有效字符、可定位字符比例0.89和0.90的样本，以及固定`content_list.json` Mock。
- 执行步骤：解析样本；检查submit/status/fetch轮询；将page_idx和bbox转换为ParsedBlock；重复同一content hash提交。
- 预期结果：50字符且定位比例0.90的样本本地解析；零文本、49字符、0.89样本触发MinerU并记录原因；page=page_idx+1，block_id稳定，重试复用provider_task_id并记录后端/版本/结果Hash。
- 异常或边界条件：MinerU三次可重试失败进入PAUSED_RETRYABLE；认证或Schema错误进入FAILED_FINAL；不得依赖content_list_v2。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-DOC-006 DOCX与XLSX证据定位

- 关联 Spec / FR / User Story：SPEC-002 第7、8节；SPEC-004 第9节
- 测试目标：验证DOCX标题/段落和XLSX工作表/单元格定位。
- 前置条件：含已知字段的合成DOCX/XLSX。
- 输入数据：申请书和财务报表。
- 执行步骤：解析、抽取并回查15个核心字段证据。
- 预期结果：DOCX包含section_path/paragraph_index；XLSX包含sheet/cell_range。
- 异常或边界条件：合并单元格和空白段落。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-DOC-007 Excel公式缓存缺失

- 关联 Spec / FR / User Story：SPEC-003 第6.1节
- 测试目标：验证只读取公式缓存，不自行执行未知公式。
- 前置条件：准备有缓存值和无缓存值两份XLSX。
- 输入数据：包含财务关键字段的公式单元格。
- 执行步骤：以data_only读取并执行事实校验。
- 预期结果：有缓存值可用；无缓存值字段进入NEEDS_REVIEW并触发HITL-1。
- 异常或边界条件：除零公式或外部工作簿引用。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-DOC-008 加密PDF拒绝

- 关联 Spec / FR / User Story：SPEC-002 第7节
- 测试目标：验证系统不收集密码、不尝试破解、不上传外部服务。
- 前置条件：密码保护PDF。
- 输入数据：可识别为加密的PDF。
- 执行步骤：上传并尝试启动解析。
- 预期结果：材料状态REJECTED，错误码ENCRYPTED_PDF，要求重新上传。
- 异常或边界条件：文件可打开但禁止复制文本。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-DOC-009 材料重传版本不可覆盖

- 关联 Spec / FR / User Story：SPEC-002 第5、7节；AC-002-05
- 测试目标：验证同类材料重传产生新版本并保留历史。
- 前置条件：案件已有申请书v1且创建过Run。
- 输入数据：同类申请书v2。
- 执行步骤：上传v2、查询版本并创建新Run。
- 预期结果：v1和v2均存在；旧Run仍引用v1，新Run引用v2。
- 异常或边界条件：上传内容Hash与v1完全相同。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-DOC-010 数值冲突双阈值

- 关联 Spec / FR / User Story：SPEC-002 第9节；SPEC-003 第7节
- 测试目标：验证金额差异必须同时超过1%和1万元才构成实质冲突。
- 前置条件：冲突检测器可调用。
- 输入数据：仅超过1%、仅超过1万元、同时超过、恰好等于阈值四组数值。
- 执行步骤：规范化并按 `abs(a-b)/max(abs(a),abs(b))` 比较每组候选值。
- 预期结果：只有相对差异严格大于1%且绝对差严格大于1万元时material=true；任一等于阈值不命中；a、b均为0时相对差异为0。
- 异常或边界条件：单边零值、负值、不同单位换算。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-DOC-011 多格式解析与证据定位实现

- 关联 Spec / FR / User Story：SPEC-002 第7、8节；SPEC-003 第4、6节；AC-003-04
- 测试目标：验证PDF、DOCX、XLSX解析器生成稳定块ID、证据ID和格式特定定位信息。
- 前置条件：PyMuPDF、python-docx、openpyxl已安装；使用纯合成材料。
- 输入数据：含15个标准事实字段的文本PDF、带Heading的DOCX、两列财务XLSX。
- 执行步骤：分别解析三种文件，检查块文本、页码/段落/工作表定位和重复解析稳定性。
- 预期结果：PDF包含页码和bbox；DOCX包含section_path/paragraph_index；XLSX包含sheet/cell_range；相同输入的block_id/evidence_id不变。
- 异常或边界条件：空段落、表格行和解析器无法定位的低质量PDF。
- 自动化状态：AUTOMATED
- 最近执行结果：PASS（2026-08-10；`19 passed`）。
- 证据或日志引用：`backend/tests/test_materials.py::test_local_parsers_preserve_evidence_locators`。

## TC-DOC-012 MinerU兜底与Excel公式缓存缺失

- 关联 Spec / FR / User Story：SPEC-002 第7节；SPEC-003 第4、6节；AC-003-04/AC-003-07
- 测试目标：验证低质量PDF可进入MinerU适配器边界，MinerU content_list定位可审计，公式无缓存时进入复核。
- 前置条件：MinerU Mock content_list和含未缓存公式的XLSX。
- 输入数据：page_idx、bbox、provider_version及公式单元格。
- 执行步骤：解析MinerU content_list；以data_only读取XLSX并比较公式工作簿。
- 预期结果：page=page_idx+1、provider版本和bbox保留；公式缓存缺失标记FORMULA_CACHE_MISSING/NEEDS_REVIEW；不执行公式。
- 异常或边界条件：MinerU未配置时记录MINERU_NOT_CONFIGURED；外部API失败不泄露密钥。
- 自动化状态：AUTOMATED（MinerU定位）；公式缓存缺失路径已实现，专项样本待补充。
- 最近执行结果：PASS（2026-08-10；`19 passed`）。
- 证据或日志引用：`backend/tests/test_materials.py::test_mineru_content_list_keeps_page_bbox_and_provider_version`。

## TC-DOC-013 合成评测材料清单完整性

- 关联 Spec / FR / User Story：SPEC-005 第2～4、15节；AC-005-01
- 测试目标：验证20个离线案件与2个演示案件的材料清单、版本和金标文件完整。
- 前置条件：评测夹具已生成。
- 输入数据：`evals/credit-review-poc-v1/cases/`、`fixtures/demo/`。
- 执行步骤：运行评测器，检查case_id、类别数量、15字段金标和文件Hash。
- 预期结果：离线案件20例；每例包含固定金标文件；全部数据标记为synthetic_only；无重复case_id。
- 异常或边界条件：缺少一个gold文件、孤立文件或制度Hash漂移。
- 自动化状态：AUTOMATED
- 最近执行结果：PASS（2026-08-10；`run_eval.py --strict`）。
- 证据或日志引用：`scripts/run_eval.py`；`artifacts/evaluations/local-baseline/summary.json`。
