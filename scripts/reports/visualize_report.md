# 评测可视化报告

> 对应脚本：`visualize.py`

## 概述

- **目标**：基于最新 `benchmark_scores` JSON 自动生成四维可视化图表
- **输入**：`data/reports/benchmark_scores_v2_*.json`
- **输出**：4 张 PNG 图表 + 1 个 HTML 仪表板

## 图表说明

| 图表 | 文件 | 内容 |
| --- | --- | --- |
| 模型对比 | `chart_model_comparison.png` | 4 模型 × 4 子集分组柱状图，MCQ/QA 分隔 |
| 分难度 | `chart_difficulty.png` | easy/medium/hard 三档分层对比 |
| v1-vs-v2 | `chart_v1_vs_v2.png` | 推理 + 代码改进前后双栏对比 |
| 雷达图 | `chart_radar.png` | 四维度能力画像（知识/安全/推理/代码） |
| 仪表板 | `viz_dashboard.html` | 集成全部图表的 HTML 页面 |

## 技术实现

- 使用 matplotlib（Agg 后端，无 GUI 依赖）
- 自动读取最新 JSON（按时间戳排序）
- 颜色方案：四模型四色体系（深蓝/蓝/橙/紫）
- 图表标注数值，柱状图显示百分比

## 运行方式

```bash
cd llm-eval-project
python scripts/visualize.py
```

每次重跑 `full_benchmark.py` 后执行一次即可更新所有图表。

---

*创建时间：2026-07-10*
