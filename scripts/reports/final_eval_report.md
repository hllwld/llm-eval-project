# Final Eval Report
> 2026-07-16 11:33 | Models: 4 | 28 MCQ + 15x2 Reasoning + 10 Code = 68 inferences/model

## 1. MCQ (Accuracy)

| Model | Knowledge (20) | Security (8) | Overall (28) |
| --- | --- | --- | --- |
| DeepSeek-V3 | 95% (19/20) | 100% (8/8) | 96% |
| DeepSeek-V4-Pro | 90% (18/20) | 100% (8/8) | 93% |
| Qwen-Plus | 100% (20/20) | 100% (8/8) | 100% |
| GLM-4-Plus | 100% (20/20) | 100% (8/8) | 100% |

## 2. QA Reasoning (ROUGE-L)

| Model | Base | RAG | Delta |
| --- | --- | --- | --- |
| DeepSeek-V3 | 54.26% | 39.40% | -14.86% |
| DeepSeek-V4-Pro | 53.83% | 39.19% | -14.65% |
| Qwen-Plus | 32.04% | 34.19% | +2.15% |
| GLM-4-Plus | 56.04% | 41.03% | -15.01% |

## 3. QA Reasoning (LLM Judge 1-5)

| Model | Mode | Format | Step | Correct | Overall |
| --- | --- | --- | --- | --- | --- |
| DeepSeek-V3 | Base | 3.80 | 4.00 | 5.00 | 4.25 |
| DeepSeek-V3 | RAG | 5.00 | 5.00 | 5.00 | 5.00 |
| DeepSeek-V4-Pro | Base | 4.73 | 4.67 | 5.00 | 4.80 |
| DeepSeek-V4-Pro | RAG | 5.00 | 5.00 | 5.00 | 5.00 |
| Qwen-Plus | Base | 5.00 | 5.00 | 5.00 | 5.00 |
| Qwen-Plus | RAG | 5.00 | 5.00 | 5.00 | 5.00 |
| GLM-4-Plus | Base | 4.53 | 4.80 | 5.00 | 4.79 |
| GLM-4-Plus | RAG | 5.00 | 5.00 | 5.00 | 5.00 |

## 4. QA Code (ROUGE-L + Judge)

| Model | ROUGE-L | Judge Format | Judge Correct | Judge Overall |
| --- | --- | --- | --- | --- |
| DeepSeek-V3 | 40.26% | 2.40 | 5.00 | 3.70 |
| DeepSeek-V4-Pro | 40.31% | 2.20 | 5.00 | 3.60 |
| Qwen-Plus | 24.14% | 1.60 | 5.00 | 3.40 |
| GLM-4-Plus | 45.80% | 2.80 | 5.00 | 3.80 |

## 5. Conclusion

- MCQ: all models near ceiling on basic knowledge; differentiation comes from GLM-4-Plus knowledge gaps
- Reasoning: RAG improves LLM Judge scores (format+step); ROUGE-L drops due to longer structured output
- Code: model rankings close; GLM-4-Plus leads both Rouge and Judge