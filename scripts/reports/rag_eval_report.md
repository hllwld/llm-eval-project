# RAG 单模型评测报告

> 对应脚本：`rag_eval.py` | 模型：DeepSeek-V3 | 25 题

## 概述

- **目标**：单模型 Base vs RAG 快速对比（推理15题 + 代码10题）
- **指标**：ROUGE-L / 格式规范性(0/1) / 步骤完整性(0-3) / 答案正确性(LLM Judge)
- **评测时间**：2026-07-15

## 评测结果

| Metric | Base | RAG | Delta |
| --- | --- | --- | --- |
| ROUGE-L (avg) | 0.4645 | 0.3571 | -0.1075 |
| Format Rate | 76.0% | 100.0% | **+24.0%** |
| Step Score (avg) | 2.08 | 2.52 | **+0.44** |
| Accuracy | 100% | 100% | 0 |

### 推理（15题）

| Metric | Base | RAG | Delta |
| --- | --- | --- | --- |
| Format Rate | 67% | 100% | **+33%** |
| Step Score | 2.07 | 2.87 | **+0.80** |
| Steps Improved | — | 11/15 (73%) | — |

### 代码（10题）

未受影响（RAG 知识库仅有推理步骤，代码题无检索结果）

## 结论

- RAG 显著改善推理题的格式规范和步骤结构
- ROUGE-L 下降为已知指标误判（结构化输出长度增加导致 n-gram 重叠降低）
- 代码题不受影响，需扩充代码模板知识库后重新评测

## 运行方式

```bash
python scripts/rag_eval.py
```

输出：`outputs/rag_eval/rag_eval_*.json` + `rag_eval_*.md`

---

*评测时间：2026-07-15*
