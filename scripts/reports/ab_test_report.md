# A/B Test Report
> 2026-07-17 13:26 | Models: 4

## 1. 成本对比

| 模型 | Input $/1M | Output $/1M | 估算单次成本 | 53题总成本 |
| --- | --- | --- | --- | --- |
| DeepSeek-V3 | $0.27 | $1.10 | $0.0005 | $0.02 |
| DeepSeek-V4-Pro | $0.27 | $1.10 | $0.0005 | $0.02 |
| Qwen-Plus | $0.55 | $2.20 | $0.0009 | $0.05 |
| GLM-4-Plus | $1.00 | $4.00 | $0.0017 | $0.09 |

## 2. 综合排行榜

| 排名 | 模型 | MCQ | Reasoning Judge | Code Judge | Avg Score | 成本/题 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **Qwen-Plus** | 100% | 5.00 | 0.00 | 0.667 | $0.0009 |
| 2 | **GLM-4-Plus** | 100% | 4.81 | 0.00 | 0.654 | $0.0017 |
| 3 | **DeepSeek-V4-Pro** | 96% | 4.87 | 0.00 | 0.646 | $0.0005 |
| 4 | **DeepSeek-V3** | 93% | 3.95 | 0.00 | 0.573 | $0.0005 |

## 3. 统计显著性 (两两对比)

| 对比 | 维度 | p-value | 显著性 |
| --- | --- | --- | --- |
| DeepSeek-V3 vs DeepSeek-V4-Pro | Reasoning Judge | 0.0 | *** |
| DeepSeek-V3 vs DeepSeek-V4-Pro | Code Judge | 1.0 | ns |
| DeepSeek-V3 vs Qwen-Plus | Reasoning Judge | 0.0 | *** |
| DeepSeek-V3 vs Qwen-Plus | Code Judge | 1.0 | ns |
| DeepSeek-V3 vs GLM-4-Plus | Reasoning Judge | 0.0 | *** |
| DeepSeek-V3 vs GLM-4-Plus | Code Judge | 1.0 | ns |
| DeepSeek-V4-Pro vs Qwen-Plus | Reasoning Judge | 0.309 | ns |
| DeepSeek-V4-Pro vs Qwen-Plus | Code Judge | 1.0 | ns |
| DeepSeek-V4-Pro vs GLM-4-Plus | Reasoning Judge | 0.631 | ns |
| DeepSeek-V4-Pro vs GLM-4-Plus | Code Judge | 1.0 | ns |
| Qwen-Plus vs GLM-4-Plus | Reasoning Judge | 0.1342 | ns |
| Qwen-Plus vs GLM-4-Plus | Code Judge | 1.0 | ns |

## 4. 置信区间 (95% CI, Bootstrap)

| 模型 | Reasoning Judge CI | Code Judge CI |
| --- | --- | --- |
| DeepSeek-V3 | [3.70, 4.20] | [0.00, 0.31] |
| DeepSeek-V4-Pro | [4.62, 5.00] | [0.00, 0.31] |
| Qwen-Plus | [4.75, 5.00] | [0.00, 0.31] |
| GLM-4-Plus | [4.55, 5.00] | [0.00, 0.31] |

## 5. 结论

**推荐模型**: Qwen-Plus (综合分 0.667)

### 选型矩阵

| 场景 | 推荐 | 原因 |
| --- | --- | --- |
| 知识问答 | Qwen-Plus | MCQ 100% |
| 推理 | Qwen-Plus | Judge 5.00 |
| 代码 | Qwen-Plus | Judge 0.00 |
| 成本最低 | DeepSeek-V4-Pro | $0.0005/题 |

### 显著性说明

- `***` p < 0.001 (极显著)
- `**`  p < 0.01 (非常显著)
- `*`   p < 0.05 (显著)
- `ns`  p >= 0.05 (不显著，差异可能由随机造成)

*注：当前基于汇总统计量计算，如需精确 p-value 请使用逐题原始数据。*