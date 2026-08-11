# RAG 测试样例

## SPEC-001 基线引用

| Test Case ID | 名称 | 来源 |
|---|---|---|
| `TC-RAG-001` | 正确制度 | SPEC-001 第 45 节 |
| `TC-RAG-002` | 失效制度 | SPEC-001 第 45 节 |
| `TC-RAG-003` | 无答案 | SPEC-001 第 45 节 |
| `TC-RAG-004` | 条款引用 | SPEC-001 第 45 节 |

新增 Chunk、Metadata Filter、BM25 + Dense、RRF、Reranker、Citation 和制度版本测试从 `TC-RAG-005` 开始，格式遵循 [测试样例模板](./README.md#测试样例模板)。

## 新增测试样例

## TC-RAG-005 制度包与索引版本

- 关联 Spec / FR / User Story：SPEC-003 第8.1节；SPEC-004 第15节
- 测试目标：验证制度及完整索引清单决定版本，索引可重建且Run固定版本。
- 前置条件：5份合成制度PDF。
- 输入数据：原制度包及修改一条条款后的制度包。
- 执行步骤：分别构建索引并创建Run；修改制度、金融词典、停用词、模型返回标识和有序chunk列表后逐项校验。
- 预期结果：清单记录模型/维度/归一化、policy hash、分词配置hash、有序chunk ID和构建器版本；任一不一致触发重建；旧Run继续引用旧索引且结果可复现。
- 异常或边界条件：无法重建时启动失败；版本号相同但文件Hash不同。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-RAG-006 结构化条款切分

- 关联 Spec / FR / User Story：SPEC-003 第8.1节
- 测试目标：验证按章/节/条/句边界切分并携带父标题。
- 前置条件：含短条款、700字条款、列表和表格的制度。
- 输入数据：合成额度期限制度PDF。
- 执行步骤：解析并执行chunking。
- 预期结果：短条款不拆；长条款按自然边界拆分并约80字重叠；表格重复表头。
- 异常或边界条件：无法识别标题层级。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-RAG-007 BM25与Dense候选规模

- 关联 Spec / FR / User Story：SPEC-003 第8.2节
- 测试目标：验证规则模板Query分别获得BM25和Dense Top30。
- 前置条件：制度索引完成，Embedding API使用固定Mock。
- 输入数据：R01～R10查询模板及同义表达。
- 执行步骤：执行两路召回并保存候选。
- 预期结果：每路最多30条，包含rank、score、chunk和索引版本。
- 异常或边界条件：语料少于30条、重复chunk。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-RAG-008 RRF融合确定性

- 关联 Spec / FR / User Story：SPEC-003 第8.2节
- 测试目标：验证k=60公式、chunk去重和Top20顺序。
- 前置条件：固定BM25与Dense排名列表。
- 输入数据：包含重叠和单路候选的排名。
- 执行步骤：计算RRF并与手工金标比较。
- 预期结果：排名从1开始，分数为各路 `1/(60+rank)` 之和；RRF同分依次按最佳单路排名升序、chunk_id升序，结果与输入迭代顺序无关。
- 异常或边界条件：单路候选、完全同分、重复chunk和不足20条。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-RAG-009 Reranker Top5

- 关联 Spec / FR / User Story：SPEC-003 第8.2节
- 测试目标：验证融合Top20全部进入qwen3-rerank并只选择Top5。
- 前置条件：Rerank Mock返回固定分数。
- 输入数据：20条候选及规则Query。
- 执行步骤：调用重排并记录结果。
- 预期结果：保存请求别名、返回模型、区域、分数、排名和索引清单Hash；不使用未校准硬阈值；输出最多5条；同分按chunk_id升序。
- 异常或边界条件：候选不足5条、相同分数或服务重试后失败。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-RAG-010 制度引用精确回查

- 关联 Spec / FR / User Story：SPEC-002 第10、11节；SPEC-004 第13节
- 测试目标：验证Top5证据可回到制度PDF页和条款。
- 前置条件：制度chunk包含locator。
- 输入数据：期限上限规则查询。
- 执行步骤：从报告引用沿hit、chunk、document回查源PDF。
- 预期结果：页码、标题路径、条款Hash一致且支持对应结论。
- 异常或边界条件：引用属于其他制度版本。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-RAG-011 无有效制度证据

- 关联 Spec / FR / User Story：SPEC-005 第6、8节
- 测试目标：验证召回结果不支持结论时不伪造引用。
- 前置条件：查询无金标相关条款。
- 输入数据：超出5份制度范围的问题。
- 执行步骤：完成召回、重排和证据校验。
- 预期结果：记录基线候选；风险标记UNSUPPORTED并从正式结论移除。
- 异常或边界条件：Top1分数较高但语义不支持。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-RAG-012 BM25、Dense、RRF与Reranker闭环

- 关联 Spec / FR / User Story：SPEC-003 第8.1～8.2节；SPEC-004 第11节；AC-003-05/AC-004-06
- 测试目标：验证制度包切分、BM25与Dense各取Top30、RRF k=60融合Top20、Reranker选择Top5以及引用元数据完整。
- 前置条件：5份纯合成制度文本、jieba金融分词、1024维归一化HashEmbedding Mock、LexicalReranker Mock。
- 输入数据：R07期限制度查询模板及固定制度索引。
- 执行步骤：构建索引两次；执行检索；核对chunk_id、BM25/Dense排名、RRF公式、重排顺序、manifest Hash和制度定位。
- 预期结果：索引Hash可复现；RRF按60常数和最佳单路排名稳定排序；输出不超过20条且恰有Top5 selected；期限命中可回查03-limit-and-tenor.md条款。
- 异常或边界条件：语料少于30条、候选少于5条、同分按chunk_id排序；远程模型未配置时不调用外部API。
- 自动化状态：AUTOMATED
- 最近执行结果：PASS（2026-08-10；`15 passed`）。
- 证据或日志引用：`backend/tests/test_retrieval_rules.py::test_policy_index_runs_bm25_dense_rrf_and_reranker_deterministically`。

## TC-RAG-013 RAG离线基线指标

- 关联 Spec / FR / User Story：SPEC-003 第8节；SPEC-005 第6、11、15节；AC-005-03
- 测试目标：记录BM25、Dense、RRF和Reranker链路的Recall@5、MRR、NDCG@5基线。
- 前置条件：五份合成制度和20个离线案件的retrieval.gold.json。
- 输入数据：规则模板Query与制度条款金标chunk_id。
- 执行步骤：运行确定性评测器，保存各阶段候选、相关chunk和指标。
- 预期结果：指标可重复计算，查询和chunk定位可追溯；首版不使用未校准分数阈值拒绝证据。
- 异常或边界条件：制度Hash变化、金标chunk不存在、Reranker候选为空。
- 自动化状态：AUTOMATED
- 最近执行结果：PASS（2026-08-10；Recall@5=1.0，MRR=1.0，NDCG@5=1.0）。
- 证据或日志引用：`scripts/run_eval.py`；`backend/tests/test_retrieval_rules.py::test_dashscope_reranker_uses_compatible_api_reranks_endpoint`；`artifacts/evaluations/local-baseline/metrics.json`。
