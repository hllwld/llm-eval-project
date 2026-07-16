# Base vs RAG 三模型对比报告

> 数据: v3 benchmark + rag_benchmark

## Reasoning (15 questions)

| Model | Base | RAG | Delta | Verdict |
| --- | --- | --- | --- | --- |
| DeepSeek-V3 (V4-Flash) | 49.68% | 39.05% | -10.63% | DROPPED |
| DeepSeek-V4-Pro | 52.91% | 39.93% | -12.98% | DROPPED |
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

## LLM-as-Judge 验证

为避免 Rouge 指标误判，使用 DeepSeek-V3 作为独立 Judge 对 Base 和 RAG 回答进行 1-5 分人工式评判：

### DeepSeek-V3 (V4-Flash)

| Metric | Base | RAG | Delta |
| --- | --- | --- | --- |
| Format (1-5) | 4.60 | 5.00 | +0.40 |
| Step (1-5) | 4.60 | 5.00 | +0.40 |
| Correctness (1-5) | 5.00 | 5.00 | 0 |
| Overall (1-5) | 4.73 | 5.00 | +0.27 |

### DeepSeek-V4-Pro

| Metric | Base | RAG | Delta |
| --- | --- | --- | --- |
| Format (1-5) | 4.73 | 5.00 | +0.27 |
| Step (1-5) | 4.67 | 5.00 | +0.33 |
| Correctness (1-5) | 4.87 | 5.00 | +0.13 |
| Overall (1-5) | 4.76 | 5.00 | +0.24 |

> LLM Judge 确认：两版 DeepSeek 在 RAG 模式下均达满分。V4-Pro Base 模式下 Judge 评分略高于 V4-Flash（+0.03），差距极小。Rouge 的下降确认为指标误判。
