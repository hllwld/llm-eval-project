# 自定义测试集 v2 全量评测报告

> 对应脚本：`full_benchmark.py`

## 概述

- **目标**：用 v2 测试集（含难度标签+输出约束）对全部模型执行分难度评测
- **模型配置**：从 `config/model_config.yaml` + `.env` 读取
- **评测对象**：DeepSeek-V3 / Qwen-Plus / GLM-4-Plus / Qwen2.5-VL
- **数据集**：50 题（知识20 + 安全5 + 推理15 + 代码10）
- **指标**：MCQ 用 Accuracy，QA 用 Rouge-L-R

## v2 vs v1 区别

| 改进项 | v1 | v2 |
| --- | --- | --- |
| 难度标签 | 无 | 全部 50 题标注 easy/medium/hard |
| QA 推理输出 | 无约束，模型输出详细推导 | 追加约束「仅输出答案+计算式」 |
| 代码参考答案 | 思路描述（几句话） | 标准化实现思路 |
| 报告生成 | 手动填表 | 自动采集分数 + 分难度表 |
| 前置校验 | 无 | precheck.py |

## 评测结果

### 总分对比

| 模型 | 知识 | 安全 | 推理 (Rouge-L-R) | 代码 (Rouge-L-R) | **综合** |
| --- | --- | --- | --- | --- | --- |
| DeepSeek-V3 | 100% | 100% | 53.88% | 58.10% | **77.99%** |
| Qwen2.5-VL | 100% | 100% | 40.58% | 56.11% | **74.17%** |
| GLM-4-Plus | 95% | 100% | 43.51% | 53.41% | **72.98%** |
| Qwen-Plus | 100% | 100% | 31.27% | 57.18% | **72.11%** |

### v1 → v2 推理题变化

| 模型 | v1 推理 | v2 推理 | 变化 | 解读 |
| --- | --- | --- | --- | --- |
| DeepSeek-V3 | 62.21% | 53.88% | -8% | 分数更真实（v1 详细答案碰巧 n-gram 匹配） |
| GLM-4-Plus | 66.46% | 43.51% | -23% | 输出约束后最长推导被削，真实能力暴露 |
| Qwen-Plus | 59.27% | 31.27% | -28% | 同上 |
| Qwen2.5-VL | 57.62% | 40.58% | -17% | 同上 |

### 分难度

| 模型 | Easy | Medium | Hard |
| --- | --- | --- | --- |
| DeepSeek-V3 | 100% | 77.99% | 100% |
| GLM-4-Plus | 100% | 74.23% | 91.67% |
| Qwen-Plus | 100% | 72.11% | 100% |
| Qwen2.5-VL | 100% | 74.17% | 100% |

> Easy 全部满分说明难度标签偏低端区分度仍不足；Medium 是真正区分模型能力的档位。

## 关键发现

1. **DeepSeek-V3 综合最强**（77.99%），Qwen-Plus 最弱（72.11%）
2. **推理题是差距最大的子集**（最高-最低差 22.6%），v2 约束后分数下降但更真实
3. **代码题分差小**（4.7%），代码生成能力四模型接近
4. **Easy 题全满分** — 难度标注偏低端需要进一步校准
5. **v2 消除了 Rouge 误判** — v1 的高分来自详细输出的 n-gram 偶然匹配

## 运行方式

```bash
cd llm-eval-project

# 前置校验
python scripts/precheck.py

# 全量评测（自动生成报告到 data/reports/）
python scripts/full_benchmark.py

# 生成可视化
python scripts/visualize.py
```

## 产出文件

| 文件 | 说明 |
| --- | --- |
| `data/reports/benchmark_report_v2_*.md` | Markdown 对比报告 |
| `data/reports/benchmark_scores_v2_*.json` | 机器可读分数 |
| `data/reports/chart_*.png` | 可视化图表 |
| `outputs/{模型}/v2/` | EvalScope 原始评测结果 |

---

*评测时间：2026-07-10 | full_benchmark.py v2*
