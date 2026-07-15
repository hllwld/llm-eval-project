# 多模型对比评测 & Badcase 收集报告

## 概述

- **脚本**：`multi_model_benchmark.py`
- **目标**：国产三模型在多数据集上的基线对比
- **评测对象**：DeepSeek-V3 / Qwen-Plus / GLM-4-Plus
- **评测数据集**：gsm8k（数学推理，4-shot CoT）、arc（科学常识，0-shot）、hellaswag（句子补全，0-shot）
- **规模**：每个数据集 20 条

## 评测结果

| 模型 | gsm8k | arc | hellaswag |
| --- | --- | --- | --- |
| DeepSeek-V3 | 100.00% | 95.00% | 75.00% |
| Qwen-Plus | 100.00% | 95.00% | 85.00% |
| GLM-4-Plus | 95.00% | 90.00% | 45.00% |

### 关键发现

- **gsm8k**：DeepSeek-V3 和 Qwen-Plus 均为 100%，GLM-4-Plus 95%，数学推理能力接近
- **arc**：三模型差距小（90%~95%），科学常识能力接近
- **hellaswag**：GLM-4-Plus 严重落后（45% vs 75%~85%），常识推理是明显短板

> 本次评测数据已于 2026-06-22 13:31 通过 `multi_model_benchmark.py` 自动生成，三模型各 3 数据集 × 20 条。

## Badcase 收集

- 自动从 EvalScope 的 `reviews/*.jsonl` 提取非满分条目
- 每模型收集 ≤5 条，总计 14 条（DeepSeek-V3 5 / Qwen-Plus 4 / GLM-4-Plus 5）
- 保存至 `data/badcases/badcases_raw.json`
- 包含：题目、正确答案、模型输出、得分明细

## 代码实现要点

```python
# 从 model_config.yaml 读取三模型配置
# 从 .env 自动加载 API Key（通过 python-dotenv）
# 使用固定 work_dir 方便定位报告
# 评测完成后自动提取 mean_acc 分数
# 从 reviews/*.jsonl 中筛选 acc != 1.0 的条目作为 Badcase
# 生成 Markdown 对比表格
```

## 运行方式

```bash
cd scripts
python multi_model_benchmark.py
```

运行后输出：
- `outputs/{模型名}/{数据集}/` — EvalScope 完整评测结果
- `data/badcases/badcases_raw.json` — Badcase 原始数据
- 终端打印 Markdown 对比表格

## 后续分析

运行 `python badcase_classifier.py` 对 Badcase 进行三级标签分类，详见 `badcase_classifier_report.md`。

---

*记录时间：2026-06-22 | EvalScope v1.8.1*