# Final Eval Report
> 2026-07-18 04:16 | Models: 4 | 28 MCQ + 15x2 Reasoning + 10 Code = 68 inferences/model

## 1. MCQ (Accuracy)

| Model | Knowledge (20) | Security (8) | Overall (28) |
| --- | --- | --- | --- |
| DeepSeek-V3 | 95% (19/20) | 100% (8/8) | 96% |
| Qwen-Plus | 100% (20/20) | 100% (8/8) | 100% |
| DeepSeek-V4-Pro | 95% (19/20) | 100% (8/8) | 96% |
| GLM-5.2 | 90% (18/20) | 100% (8/8) | 93% |

## 2. QA Reasoning (ROUGE-L)

| Model | Base | RAG | Delta |
| --- | --- | --- | --- |
| DeepSeek-V3 | 44.55% | 39.49% | -5.06% |
| Qwen-Plus | 33.82% | 32.35% | -1.47% |
| DeepSeek-V4-Pro | 51.36% | 38.44% | -12.92% |
| GLM-5.2 | 46.85% | 41.03% | -5.83% |

## 3. QA Reasoning (LLM Judge 1-5)

| Model | Mode | Format | Step | Correct | Overall |
| --- | --- | --- | --- | --- | --- |
| DeepSeek-V3 | Base | 2.87 | 2.80 | 5.00 | 3.55 |
| DeepSeek-V3 | RAG | 5.00 | 5.00 | 5.00 | 5.00 |
| Qwen-Plus | Base | 5.00 | 5.00 | 5.00 | 5.00 |
| Qwen-Plus | RAG | 5.00 | 5.00 | 5.00 | 5.00 |
| DeepSeek-V4-Pro | Base | 4.47 | 4.53 | 5.00 | 4.65 |
| DeepSeek-V4-Pro | RAG | 5.00 | 5.00 | 5.00 | 5.00 |
| GLM-5.2 | Base | 3.73 | 3.73 | 5.00 | 4.11 |
| GLM-5.2 | RAG | 5.00 | 5.00 | 5.00 | 5.00 |

## 4. QA Code (ROUGE-L + Judge)

| Model | Base Rouge | RAG Rouge | Delta | Base Judge | RAG Judge |
| --- | --- | --- | --- | --- | --- |
| DeepSeek-V3 | 43.24% | 37.46% | -5.78% | 3.80 | 3.50 |
| Qwen-Plus | 25.89% | 36.01% | +10.12% | 3.70 | 3.50 |
| DeepSeek-V4-Pro | 40.06% | 44.63% | +4.57% | 4.00 | 3.30 |
| GLM-5.2 | 43.29% | 35.57% | -7.72% | 3.80 | 3.10 |

## 5. Token 消耗统计

| Model | MCQ Tokens | Reasoning Base | Reasoning RAG | Code Base | Code RAG | Total |
| --- | --- | --- | --- | --- | --- | --- |
| DeepSeek-V3 | 4680 | 2341 | 8524 | 4596 | 10279 | **30420** |
| Qwen-Plus | 1924 | 3565 | 8560 | 6854 | 8449 | **29352** |
| DeepSeek-V4-Pro | 4353 | 2894 | 7311 | 4642 | 8166 | **27366** |
| GLM-5.2 | 9157 | 6351 | 12109 | 8122 | 11461 | **47200** |

## 6. Conclusion（LLM 自动分析）

- **自动分析失败: Expecting value: line 59 column 12 (char 2104)**: 请检查 eval 数据或 API 状态