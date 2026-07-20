# Final Eval Report
> 2026-07-20 14:23 | Models: 4 | 28 MCQ + 15x2 Reasoning + 10 Code = 68 inferences/model

## 1. MCQ (Accuracy)

| Model | Knowledge (20) | Security (8) | Overall (28) |
| --- | --- | --- | --- |
| DeepSeek-V3 | 95% (19/20) | 100% (8/8) | 96% |
| DeepSeek-V4-Pro | 95% (19/20) | 100% (8/8) | 96% |
| Qwen-Plus | 100% (20/20) | 100% (8/8) | 100% |
| GLM-5.2 | 95% (19/20) | 100% (8/8) | 96% |

## 2. QA Reasoning (ROUGE-L)

| Model | Base | RAG | Delta |
| --- | --- | --- | --- |
| DeepSeek-V3 | 48.64% | 39.87% | -8.77% |
| DeepSeek-V4-Pro | 49.43% | 38.71% | -10.72% |
| Qwen-Plus | 32.84% | 33.62% | +0.78% |
| GLM-5.2 | 50.41% | 41.13% | -9.27% |

## 3. QA Reasoning (LLM Judge 1-5)

| Model | Mode | Format | Step | Correct | Overall |
| --- | --- | --- | --- | --- | --- |
| DeepSeek-V3 | Base | 4.40 | 4.27 | 5.00 | 4.55 |
| DeepSeek-V3 | RAG | 5.00 | 5.00 | 5.00 | 5.00 |
| DeepSeek-V4-Pro | Base | 4.73 | 4.73 | 4.87 | 4.73 |
| DeepSeek-V4-Pro | RAG | 5.00 | 5.00 | 5.00 | 5.00 |
| Qwen-Plus | Base | 4.93 | 5.00 | 5.00 | 4.98 |
| Qwen-Plus | RAG | 5.00 | 5.00 | 5.00 | 5.00 |
| GLM-5.2 | Base | 4.67 | 4.53 | 5.00 | 4.71 |
| GLM-5.2 | RAG | 5.00 | 5.00 | 5.00 | 5.00 |

## 4. QA Code (ROUGE-L + Judge)

| Model | Base Rouge | RAG Rouge | Delta | Base Judge | RAG Judge |
| --- | --- | --- | --- | --- | --- |
| DeepSeek-V3 | 39.98% | 40.92% | +0.94% | 3.90 | 3.90 |
| DeepSeek-V4-Pro | 33.69% | 39.59% | +5.90% | 4.00 | 3.70 |
| Qwen-Plus | 25.62% | 36.37% | +10.74% | 3.60 | 3.60 |
| GLM-5.2 | 44.30% | 35.48% | -8.82% | 3.50 | 3.70 |

## 5. Token 消耗统计

| Model | MCQ Tokens | Reasoning Base | Reasoning RAG | Code Base | Code RAG | Total |
| --- | --- | --- | --- | --- | --- | --- |
| DeepSeek-V3 | 5586 | 2671 | 8023 | 4800 | 10582 | **31662** |
| DeepSeek-V4-Pro | 4783 | 3267 | 7361 | 4914 | 8093 | **28418** |
| Qwen-Plus | 1924 | 3670 | 8386 | 6415 | 8576 | **28971** |
| GLM-5.2 | 8451 | 6785 | 12272 | 7388 | 11552 | **46448** |

## 6. Conclusion（LLM 自动分析）

- **自动分析失败: Unterminated string starting at: line 67 column 17 (char 241**: 请检查 eval 数据或 API 状态