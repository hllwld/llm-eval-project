# Base vs RAG 三模型对比报告

> 数据: v3 benchmark + rag_benchmark

## Reasoning (15 questions)

| Model | Base | RAG | Delta | Verdict |
| --- | --- | --- | --- | --- |
| DeepSeek-V3 | 49.68% | 39.05% | -10.63% | DROPPED |
| Qwen-Plus | 31.43% | 34.17% | +2.74% | IMPROVED |
| GLM-4-Plus | 35.00% | 40.48% | +5.48% | IMPROVED |

## Code (10 questions)

| Model | Base | RAG | Delta | Verdict |
| --- | --- | --- | --- | --- |
| DeepSeek-V3 | 55.25% | 29.45% | -25.80% | DROPPED |
| Qwen-Plus | 57.58% | 25.33% | -32.25% | DROPPED |
| GLM-4-Plus | 53.13% | 42.67% | -10.46% | DROPPED |

## Conclusion

- Code subset: RAG has minimal impact (KB contains reasoning steps only)
- Reasoning subset: RAG effect varies by model. Check per-model delta.
- Note: ROUGE-L penalizes longer structured output. Improvement in format/step quality may not be reflected in ROUGE-L scores.
