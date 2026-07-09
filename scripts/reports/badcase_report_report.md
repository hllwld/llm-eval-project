# Badcase 分析报告生成

## 概述

- **脚本**：`badcase_report.py`
- **目标**：读取标注好的 Badcase，生成统计分析报告
- **输入**：`data/badcases/custom_badcases_labeled.json`
- **输出**：`data/reports/badcase_analysis.md`

## 终端输出

```
============================================================
Custom Testset Badcase Analysis Report
============================================================

Total Badcases: 9

By Model:
  GLM-4-Plus: 4
  Qwen-Plus: 3
  DeepSeek-V3: 1
  Qwen2.5-VL: 1

By Subset:
  general_qa_reasoning: 5
  general_qa_code: 3
  general_mcq_knowledge: 1

Error Types:
  推理错误: 5 (55.6%)
  代码错误: 3 (33.3%)
  知识错误: 1 (11.1%)

RAG Fixability:
  部分可解: 8 (88.9%)
  RAG可解: 1 (11.1%)

============================================================
Key Conclusions
============================================================
  RAG-solvable:    1/9 (11.1%)
  RAG-partial:     8/9 (88.9%)
  RAG-unsolvable:  0/9 (0.0%)

Report saved: .../data/reports/badcase_analysis.md
```

## 报告内容

生成的 Markdown 报告包含：
1. **数据概览** — 总 Badcase 数、涉及模型
2. **错误类型分布** — 按错误类型统计
3. **RAG 适配度结论** — 可解/部分可解/不可解比例
4. **典型案例** — 前 5 条 Badcase 的详细信息（问题、期望、实际、分析）

## 核心结论

- **MCQ 几乎全对**：25 道选择题仅 GLM-4-Plus 错 1 题，说明选择题偏简单
- **QA 推理是主战场**：5 条推理错误占比最高，模型在推理题上的回答质量待提升
- **RAG 改善空间大**：88.9% 的 Badcase 可通过 RAG 部分缓解，无完全不可解的案例
- **评测指标局限性**：QA 用 Rouge-L-R 评分，会因回答风格差异（简洁 vs 详细）导致分数偏差

## 运行方式

```bash
cd llm-eval-project
python scripts/badcase_report.py
```

## 完整流程

Badcase 分析三件套按顺序执行：
```
extract_custom_badcases.py → label_custom_badcases.py → badcase_report.py
```

---

*报告时间：2026-07-09*
