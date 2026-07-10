# 自定义测试集生成报告

> 对应脚本：`generate_testset.py` | 版本：v2.0

## 概述

- **目标**：生成四大领域的知识问答 + 推理/代码/安全 评测数据集
- **输出格式**：CSV（选择题，含 difficulty 字段）+ JSONL（问答题，含难度 + 输出约束）
- **新特性**：每道题标注 easy/medium/hard、推理题追加输出约束、代码答案规范化

## 测试集规模

| 类别 | 题型 | 数量 | 领域覆盖 |
| --- | --- | --- | --- |
| 知识类 | 4 选 1 选择题 | 20 条 | 科技(5) / 历史(5) / 地理(5) / 文化(5) |
| 安全类 | 4 选 1 选择题 | 5 条 | 法律合规 / 网络安全 / 隐私保护 / AI 伦理 |
| 推理类 | 开放式问答题 | 15 条 | 数学运算 / 逻辑推理 |
| 代码类 | 开放式问答题 | 10 条 | 算法 / 数据结构 / 工程实践 |
| **合计** | | **50 条** | |

## 终端输出

```
============================================================
[OK] Testset generation complete!
   Output: .../data/custom_testset
   Knowledge MCQ  (with explanation): 20 -> mcq/knowledge_val.csv
   Security MCQ:                     5  -> mcq/security_val.csv
   Reasoning QA:                     15 -> qa/reasoning.jsonl
   Code QA:                          10 -> qa/code.jsonl
   All MCQ JSON (with explanation):  25 -> knowledge_qa_all.json
============================================================
```

## 题目质量控制

- 全部基于可靠事实，通过逐条事实核查
- 干扰项均为真实概念/人物/地名/时期，具备"对称混淆"特性
- 难度控制在中等水平，兼具区分度
- 每道题附带简短解析

## 输出文件

| 文件 | 格式 | 说明 |
| --- | --- | --- |
| `data/custom_testset/mcq/knowledge_val.csv` | CSV | 20 道知识选择题 |
| `data/custom_testset/mcq/security_val.csv` | CSV | 5 道安全选择题 |
| `data/custom_testset/qa/reasoning.jsonl` | JSONL | 15 道推理问答题 |
| `data/custom_testset/qa/code.jsonl` | JSONL | 10 道代码问答题 |
| `data/custom_testset/knowledge_qa_all.json` | JSON | 25 道选择题 + 解析（完整版） |

## 运行方式

```bash
cd llm-eval-project
python scripts/generate_testset.py
```

## 难度分布

| 子集 | Easy | Medium | Hard |
| --- | --- | --- | --- |
| 知识 | 6 | 8 | 6 |
| 安全 | 2 | 2 | 1 |
| 推理 | 4 | 6 | 5 |
| 代码 | 3 | 4 | 3 |
| **合计** | **15** | **20** | **15** |

## v2 改进记录

基于 [badcase 分析报告](../../data/reports/badcase_analysis.md) 的建议：
1. **QA 推理输出约束**：追加 `【输出要求】仅输出最终答案和一行计算式，无需推导过程。`
2. **代码答案规范化**：多线程下载器参考答案改为标准实现思路
3. **难度标签注入**：CSV 增加 `difficulty` 列，JSONL 增加 `difficulty` 字段
4. **metadata.yaml**：记录版本号和变更历史

## 后续评测

生成的测试集通过 `run_full_benchmark.py` 加载，使用 EvalScope 的 `general_mcq` 和 `general_qa` 数据集类型评测。

详见 [run_full_benchmark_report.md](run_full_benchmark_report.md)。

---

*生成时间：2026-07-09*
