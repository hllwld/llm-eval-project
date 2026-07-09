# 自定义测试集 Badcase 提取报告

## 概述

- **脚本**：`extract_custom_badcases.py`
- **目标**：从 EvalScope review 文件中提取错误/低质量样本
- **输入**：`outputs/*/mcq/reviews/` 和 `outputs/*/qa/reviews/` 下的 JSONL 文件
- **输出**：`data/badcases/custom_badcases_raw.json`

## 提取规则

| 评测类型 | 判定标准 | 说明 |
| --- | --- | --- |
| MCQ（选择题） | `acc == 0.0` | 模型答案与正确答案不匹配 |
| QA（问答题） | `Rouge-L-R < 0.4` | 回答与期望答案差异显著 |

## 终端输出

```
Found 16 review files
Extracted 9 badcases

Badcase distribution:
  DeepSeek-V3:
    - general_qa_code: 1
  GLM-4-Plus:
    - general_mcq_knowledge: 1
    - general_qa_code: 1
    - general_qa_reasoning: 2
  Qwen-Plus:
    - general_qa_code: 1
    - general_qa_reasoning: 2
  Qwen2.5-VL:
    - general_qa_reasoning: 1

Saved: .../data/badcases/custom_badcases_raw.json
```

## 提取结果概览

| 模型 | Badcase 数 | 分布 |
| --- | --- | --- |
| GLM-4-Plus | 4 | 1 MCQ知识 + 1 QA代码 + 2 QA推理 |
| Qwen-Plus | 3 | 1 QA代码 + 2 QA推理 |
| DeepSeek-V3 | 1 | 1 QA代码 |
| Qwen2.5-VL | 1 | 1 QA推理 |
| **合计** | **9** | |

## 代码实现要点

- 通过 `os.path.relpath` 解析目录结构，提取模型名、评测类型、子集名
- 搜索 `outputs/*/mcq/reviews/*/*.jsonl` 和 `outputs/*/qa/reviews/*/*.jsonl` 两层嵌套
- 每条记录包含：问题、期望答案、模型输出、得分明细、样本元数据
- 兼容 MCQ 的 `acc` 字段和 QA 的 `Rouge-L-R` 字段

## 运行方式

```bash
cd llm-eval-project
python scripts/extract_custom_badcases.py
```

## 下一步

运行 `label_custom_badcases.py` 对提取的 9 条 Badcase 进行自动标注分类。

详见 [label_custom_badcases_report.md](label_custom_badcases_report.md)。

---

*提取时间：2026-07-09*
