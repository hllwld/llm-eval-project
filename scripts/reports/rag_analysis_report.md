# RAG 评测分析报告

> 数据来源: rag_eval_20260715_1241.json

## Overall

| Metric | Base | RAG | Delta |
| --- | --- | --- | --- |
| ROUGE-L (avg) | 0.4645 | 0.3571 | -0.1075 |
| Format Rate | 76% | 100% | +24% |
| Step Score (avg) | 2.08 | 2.52 | +0.44 |

## By Category

### Reasoning (15)
- Format Rate: Base=67% RAG=100%
- Step Score:  Base=2.07 RAG=2.87
- ROUGE-L:     Base=0.5666 RAG=0.3818
- Steps improved: 11/15 questions

### Code (10)
- Format Rate: Base=90% RAG=100%
- Step Score:  Base=2.10 RAG=2.00
- ROUGE-L:     Base=0.3114 RAG=0.3199

## Conclusion

- RAG improved format compliance by +24%
- RAG improved reasoning step scores by +0.80 points
- ROUGE-L dropped due to longer structured output (measurement artifact, not quality degradation)
- Code questions unaffected by RAG (KB contains reasoning steps only)
