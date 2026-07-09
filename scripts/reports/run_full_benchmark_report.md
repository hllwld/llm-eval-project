# 自定义测试集 × 全部模型 完整评测报告

## 概述

- **脚本**：`run_full_benchmark.py`
- **目标**：用自定义测试集对全部模型执行完整评测，自动汇总对比结果
- **模型配置**：从 `config/model_config.yaml` + `.env` 读取（非硬编码）
- **评测对象**：DeepSeek-V3 / Qwen-Plus / GLM-4-Plus / Qwen2.5-VL
- **评测数据集**：自定义 MCQ（25 道选择题）+ QA（25 道问答题）
- **规模**：4 模型 × 50 题 = 200 次推理

## 评测结果

### 选择题 (MCQ) — mean_acc

| 模型 | 知识 (20题) | 安全 (5题) | **总分** |
| --- | --- | --- | --- |
| DeepSeek-V3 | 100.00% | 100.00% | **100.00%** |
| Qwen-Plus | 100.00% | 100.00% | **100.00%** |
| Qwen2.5-VL | 100.00% | 100.00% | **100.00%** |
| GLM-4-Plus | 95.00% | 100.00% | **96.00%** |

> GLM-4-Plus 仅错 1 题："赤道穿过哪个大洲的面积最大"答成亚洲（正确答案：非洲）

### 问答题 (QA) — Rouge-L-R

| 模型 | 代码 (10题) | 推理 (15题) | **总分** |
| --- | --- | --- | --- |
| GLM-4-Plus | 53.69% | 66.46% | **61.35%** |
| DeepSeek-V3 | 54.44% | 62.21% | **59.10%** |
| Qwen-Plus | 56.53% | 59.27% | **58.17%** |
| Qwen2.5-VL | 54.76% | 57.62% | **56.48%** |

### 关键发现

- **选择题过于简单**：除 GLM-4-Plus 错 1 题外，其余模型全部满分，区分度不足
- **问答题 GLM-4-Plus 推理最强**（66.46%），但代码最弱（53.69%），两极分化
- **DeepSeek-V3 最均衡**：代码和推理都在中上水平
- **Qwen2.5-VL 推理偏弱**（57.62%），作为视觉模型做纯文本评测不占优势

## 终端输出（截取）

```
======================================================================
>> Evaluating: DeepSeek-V3
  [MCQ] 选择题评测...
     knowledge: 100.00%  security: 100.00%
  [QA] 问答题评测...
     code: 54.44%  reasoning: 62.21%

>> Evaluating: Qwen-Plus
     knowledge: 100.00%  security: 100.00%
     code: 56.53%  reasoning: 59.27%

>> Evaluating: GLM-4-Plus
     knowledge: 95.00%  security: 100.00%
     code: 53.69%  reasoning: 66.46%

>> Evaluating: Qwen2.5-VL
     knowledge: 100.00%  security: 100.00%
     code: 54.76%  reasoning: 57.62%

======================================================================
MCQ (选择题) 对比
======================================================================
Model                 knowledge    security
--------------------  -----------  ----------
DeepSeek-V3           100.00%      100.00%
Qwen-Plus             100.00%      100.00%
GLM-4-Plus            95.00%       100.00%
Qwen2.5-VL            100.00%      100.00%

======================================================================
Results saved:
  Markdown: outputs/benchmark_summary_*.md
  JSON:     outputs/benchmark_summary_*.json
======================================================================
```

## 代码实现要点

- API Key 从 `config/model_config.yaml` 引用 `.env` 中的环境变量名，无硬编码
- MCQ 分数从 report 的 `mean_acc` metric 按子集（knowledge/security）拆分提取
- QA 分数从 report 的 `mean_Rouge-L-R` metric 按子集（code/reasoning）拆分提取
- 评测结果同时保存为 Markdown 和 JSON 格式到 `outputs/`

## 运行方式

```bash
cd llm-eval-project
python scripts/run_full_benchmark.py
```

运行后输出：
- `outputs/{模型名}/mcq/` — EvalScope MCQ 评测结果
- `outputs/{模型名}/qa/` — EvalScope QA 评测结果
- `outputs/benchmark_summary_*.md` — Markdown 对比报告
- `outputs/benchmark_summary_*.json` — JSON 机器可读报告

## 后续分析

运行 Badcase 提取 → 标注 → 报告流程：
```bash
python scripts/extract_custom_badcases.py
python scripts/label_custom_badcases.py
python scripts/badcase_report.py
```

详见 [extract_custom_badcases_report.md](extract_custom_badcases_report.md)。

---

*评测时间：2026-07-09 | EvalScope v1.8.1*
