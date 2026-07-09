# 自定义测试集 Badcase 自动标注报告

## 概述

- **脚本**：`label_custom_badcases.py`
- **目标**：对 Badcase 自动打标签（错误类型 / 错误位置 / RAG 适配度）
- **输入**：`data/badcases/custom_badcases_raw.json`
- **输出**：`data/badcases/custom_badcases_labeled.json`

## 标注规则

### 错误类型判定

| 条件 | 错误类型 |
| --- | --- |
| MCQ + knowledge 子集 | 知识错误 |
| MCQ + security 子集 | 安全错误 |
| QA + code 子集 + 输出过短 | 指令违背 |
| QA + code 子集 + 正常输出 | 代码错误 |
| QA + reasoning 子集 | 推理错误 |

### RAG 适配度判定

| 错误类型 | Rouge-L-R 条件 | RAG 适配度 |
| --- | --- | --- |
| 知识错误 | — | **RAG可解** |
| 推理错误/代码错误 | > 0.15 | 部分可解 |
| 推理错误/代码错误 | ≤ 0.15 | RAG不可解 |
| 安全错误 | — | RAG不可解 |

## 终端输出

```
Loaded 9 raw badcases

Error types:
  推理错误: 5
  代码错误: 3
  知识错误: 1

RAG fixability:
  部分可解: 8
  RAG可解: 1

Saved: .../data/badcases/custom_badcases_labeled.json
```

## 标注结果统计

| 维度 | 分类 | 数量 | 占比 |
| --- | --- | --- | --- |
| 错误类型 | 推理错误 | 5 | 55.6% |
| | 代码错误 | 3 | 33.3% |
| | 知识错误 | 1 | 11.1% |
| RAG 适配度 | 部分可解 | 8 | 88.9% |
| | RAG可解 | 1 | 11.1% |

> 注意：3 条"代码错误"实际是模型输出了完整代码实现，但参考答案为思路描述，导致 Rouge 低。严格来说不算"错误"，属于评测指标局限性。

## 运行方式

```bash
cd llm-eval-project
python scripts/label_custom_badcases.py
```

## 下一步

运行 `badcase_report.py` 生成 Markdown 分析报告。

详见 [badcase_report_report.md](badcase_report_report.md)。

---

*标注时间：2026-07-09*
