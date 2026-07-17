# A/B Test Report
> 2026-07-18 04:20 | Models: 4

## 1. 成本对比

| 模型 | Input $/1M | Output $/1M | 估算单次成本 | 53题总成本 |
| --- | --- | --- | --- | --- |
| DeepSeek-V3 | $0.14 | $0.28 | $0.0002 | $0.01 |
| DeepSeek-V4-Pro | $0.55 | $2.19 | $0.0009 | $0.05 |
| Qwen-Plus | $0.80 | $2.00 | $0.0010 | $0.05 |
| GLM-5.2 | $1.00 | $4.00 | $0.0017 | $0.09 |

## 2. 综合排行榜

| 排名 | 模型 | MCQ | Reasoning Judge | Code Judge | Avg Score | 成本/题 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **Qwen-Plus** | 100% | 5.00 | 0.00 | 0.667 | $0.0010 |
| 2 | **DeepSeek-V4-Pro** | 96% | 4.65 | 0.00 | 0.631 | $0.0009 |
| 3 | **GLM-5.2** | 93% | 4.11 | 0.00 | 0.583 | $0.0017 |
| 4 | **DeepSeek-V3** | 96% | 3.55 | 0.00 | 0.558 | $0.0002 |

## 3. 统计显著性 (两两对比)

| 对比 | 维度 | p-value | 显著性 |
| --- | --- | --- | --- |
| DeepSeek-V3 vs DeepSeek-V4-Pro | Reasoning Judge | 0.0 | *** |
| DeepSeek-V3 vs DeepSeek-V4-Pro | Code Judge | 1.0 | ns |
| DeepSeek-V3 vs Qwen-Plus | Reasoning Judge | 0.0 | *** |
| DeepSeek-V3 vs Qwen-Plus | Code Judge | 1.0 | ns |
| DeepSeek-V3 vs GLM-5.2 | Reasoning Judge | 0.0 | *** |
| DeepSeek-V3 vs GLM-5.2 | Code Judge | 1.0 | ns |
| DeepSeek-V4-Pro vs Qwen-Plus | Reasoning Judge | 0.0062 | ** |
| DeepSeek-V4-Pro vs Qwen-Plus | Code Judge | 1.0 | ns |
| DeepSeek-V4-Pro vs GLM-5.2 | Reasoning Judge | 0.0 | *** |
| DeepSeek-V4-Pro vs GLM-5.2 | Code Judge | 1.0 | ns |
| Qwen-Plus vs GLM-5.2 | Reasoning Judge | 0.0 | *** |
| Qwen-Plus vs GLM-5.2 | Code Judge | 1.0 | ns |

## 4. 置信区间 (95% CI, Bootstrap)

| 模型 | Reasoning Judge CI | Code Judge CI |
| --- | --- | --- |
| DeepSeek-V3 | [3.29, 3.80] | [0.00, 0.31] |
| DeepSeek-V4-Pro | [4.39, 4.90] | [0.00, 0.31] |
| Qwen-Plus | [4.75, 5.00] | [0.00, 0.31] |
| GLM-5.2 | [3.85, 4.36] | [0.00, 0.31] |

## 5. 结论

**推荐模型**: Qwen-Plus (综合分 0.667)

### 选型矩阵

| 场景 | 推荐 | 原因 |
| --- | --- | --- |
| 知识问答 | Qwen-Plus | MCQ 100% |
| 推理 | Qwen-Plus | Judge 5.00 |
| 代码 | Qwen-Plus | Judge 0.00 |
| 成本最低 | DeepSeek-V3 | $0.0002/题 |

### 显著性说明

- `***` p < 0.001 (极显著)
- `**`  p < 0.01 (非常显著)
- `*`   p < 0.05 (显著)
- `ns`  p >= 0.05 (不显著，差异可能由随机造成)

*注：当前基于汇总统计量计算，如需精确 p-value 请使用逐题原始数据。*