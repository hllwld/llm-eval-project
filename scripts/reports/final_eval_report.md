# Final Eval Report
> 2026-07-17 13:24 | Models: 4 | 28 MCQ + 15x2 Reasoning + 10 Code = 68 inferences/model

## 1. MCQ (Accuracy)

| Model | Knowledge (20) | Security (8) | Overall (28) |
| --- | --- | --- | --- |
| DeepSeek-V3 | 95% (19/20) | 88% (7/8) | 93% |
| DeepSeek-V4-Pro | 95% (19/20) | 100% (8/8) | 96% |
| Qwen-Plus | 100% (20/20) | 100% (8/8) | 100% |
| GLM-4-Plus | 100% (20/20) | 100% (8/8) | 100% |

## 2. QA Reasoning (ROUGE-L)

| Model | Base | RAG | Delta |
| --- | --- | --- | --- |
| DeepSeek-V3 | 46.17% | 39.57% | -6.60% |
| DeepSeek-V4-Pro | 53.64% | 39.34% | -14.30% |
| Qwen-Plus | 33.34% | 34.40% | +1.06% |
| GLM-4-Plus | 54.90% | 40.48% | -14.41% |

## 3. QA Reasoning (LLM Judge 1-5)

| Model | Mode | Format | Step | Correct | Overall |
| --- | --- | --- | --- | --- | --- |
| DeepSeek-V3 | Base | 3.53 | 3.33 | 5.00 | 3.95 |
| DeepSeek-V3 | RAG | 5.00 | 5.00 | 5.00 | 5.00 |
| DeepSeek-V4-Pro | Base | 4.80 | 4.80 | 5.00 | 4.87 |
| DeepSeek-V4-Pro | RAG | 5.00 | 5.00 | 5.00 | 5.00 |
| Qwen-Plus | Base | 5.00 | 5.00 | 5.00 | 5.00 |
| Qwen-Plus | RAG | 5.00 | 5.00 | 5.00 | 5.00 |
| GLM-4-Plus | Base | 4.67 | 4.73 | 5.00 | 4.81 |
| GLM-4-Plus | RAG | 5.00 | 5.00 | 5.00 | 5.00 |

## 4. QA Code (ROUGE-L + Judge)

| Model | Base Rouge | RAG Rouge | Delta | Base Judge | RAG Judge |
| --- | --- | --- | --- | --- | --- |
| DeepSeek-V3 | 40.00% | 45.23% | +5.23% | 3.50 | 3.10 |
| DeepSeek-V4-Pro | 42.95% | 43.25% | +0.31% | 3.70 | 3.30 |
| Qwen-Plus | 26.18% | 36.64% | +10.47% | 3.50 | 3.00 |
| GLM-4-Plus | 41.40% | 45.96% | +4.57% | 4.00 | 3.60 |

## 5. Token 消耗统计

| Model | MCQ Tokens | Reasoning Base | Reasoning RAG | Code Base | Code RAG | Total |
| --- | --- | --- | --- | --- | --- | --- |
| DeepSeek-V3 | 5390 | 2358 | 8263 | 5003 | 11017 | **32031** |
| DeepSeek-V4-Pro | 4634 | 3041 | 7289 | 4677 | 10286 | **29927** |
| Qwen-Plus | 1924 | 3538 | 8318 | 6704 | 10421 | **30905** |
| GLM-4-Plus | 1868 | 1829 | 6687 | 3369 | 8754 | **22507** |

## 6. Conclusion

- MCQ: 所有模型基础知识题接近满分，区分度集中在 DeepSeek-V4-Pro 的知识短板
- Reasoning: RAG 改善 LLM Judge 评分（格式+步骤），ROUGE-L 因结构变长而下降（已知误判）
- Code: 新增代码知识库（10条模板），RAG 对代码格式和规范性提升待验证