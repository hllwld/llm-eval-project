# 自定义测试集生成报告

## 概述

- **脚本**：`generate_testset.py`
- **目标**：生成四大领域的知识问答 + 推理/代码/安全 评测数据集
- **输出格式**：CSV（选择题，EvalScope `general_mcq` 兼容）+ JSONL（问答题，`general_qa` 兼容）+ JSON（完整备份含解析）

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

## 后续评测

生成的测试集通过 `run_full_benchmark.py` 加载，使用 EvalScope 的 `general_mcq` 和 `general_qa` 数据集类型评测。

详见 [run_full_benchmark_report.md](run_full_benchmark_report.md)。

---

*生成时间：2026-07-09*
