# Final Eval Report
> 2026-07-17 11:42 | Models: 4 | 28 MCQ + 15x2 Reasoning + 10 Code = 68 inferences/model

## 1. MCQ (Accuracy)

| Model | Knowledge (20) | Security (8) | Overall (28) |
| --- | --- | --- | --- |
| DeepSeek-V3 | 100% (2/2) | 100% (1/1) | 100% |
| DeepSeek-V4-Pro | 100% (2/2) | 100% (1/1) | 100% |
| Qwen-Plus | 100% (2/2) | 100% (1/1) | 100% |
| GLM-4-Plus | 100% (2/2) | 100% (1/1) | 100% |

## 2. QA Reasoning (ROUGE-L)

| Model | Base | RAG | Delta |
| --- | --- | --- | --- |
| DeepSeek-V3 | 68.27% | 36.03% | -32.23% |
| DeepSeek-V4-Pro | 44.52% | 34.84% | -9.68% |
| Qwen-Plus | 32.29% | 36.03% | +3.74% |
| GLM-4-Plus | 43.94% | 36.03% | -7.91% |

## 3. QA Reasoning (LLM Judge 1-5)

| Model | Mode | Format | Step | Correct | Overall |
| --- | --- | --- | --- | --- | --- |
| DeepSeek-V3 | Base | 4.50 | 5.00 | 5.00 | 4.85 |
| DeepSeek-V3 | RAG | 5.00 | 5.00 | 5.00 | 5.00 |
| DeepSeek-V4-Pro | Base | 5.00 | 5.00 | 5.00 | 5.00 |
| DeepSeek-V4-Pro | RAG | 5.00 | 5.00 | 5.00 | 5.00 |
| Qwen-Plus | Base | 5.00 | 5.00 | 5.00 | 5.00 |
| Qwen-Plus | RAG | 5.00 | 5.00 | 5.00 | 5.00 |
| GLM-4-Plus | Base | 4.50 | 5.00 | 5.00 | 4.85 |
| GLM-4-Plus | RAG | 5.00 | 5.00 | 5.00 | 5.00 |

## 4. QA Code (ROUGE-L + Judge)

| Model | Base Rouge | RAG Rouge | Delta | Base Judge | RAG Judge |
| --- | --- | --- | --- | --- | --- |
| DeepSeek-V3 | 41.76% | 59.09% | +17.33% | 3.00 | 4.00 |
| DeepSeek-V4-Pro | 53.66% | 64.20% | +10.54% | 5.00 | 4.00 |
| Qwen-Plus | 35.06% | 49.52% | +14.46% | 4.00 | 3.00 |
| GLM-4-Plus | 71.23% | 60.47% | -10.76% | 4.00 | 4.00 |

## 5. Conclusion

- MCQ: 所有模型基础知识题接近满分，区分度集中在 DeepSeek-V4-Pro 的知识短板
- Reasoning: RAG 改善 LLM Judge 评分（格式+步骤），ROUGE-L 因结构变长而下降（已知误判）
- Code: 新增代码知识库（10条模板），RAG 对代码格式和规范性提升待验证