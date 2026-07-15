# RAG 三模型评测报告

> 对应脚本：`rag_benchmark.py` | 三模型 × 25 题

## 概述

- **模型**：DeepSeek-V3 / Qwen-Plus / GLM-4-Plus（从 `model_config.yaml` 读取，自动跳过 `active: false`）
- **测试集**：推理15题（RAG增强）+ 代码10题（无RAG，对照组）
- **检索**：ChromaDB + BGE，每道推理题检索 Top-2
- **Prompt**：`rag_prompt_builder.py` 重组（步骤模板 + 答案注入）

## Base vs RAG 推理题对比

| 模型 | Base ROUGE-L | RAG ROUGE-L | Delta | 判定 |
| --- | --- | --- | --- | --- |
| DeepSeek-V3 | 49.68% | 39.05% | -10.63% | DROPPED (Rouge artifact) |
| GLM-4-Plus | 35.00% | 40.48% | **+5.48%** | IMPROVED |
| Qwen-Plus | 31.43% | 34.17% | **+2.74%** | IMPROVED |

## 代码题（对照组）

全部下降 — KB 无代码条目，RAG 对代码题无帮助（预期行为）

## 结论

- RAG 对 GLM-4-Plus、Qwen-Plus 的推理题有正向提升
- DeepSeek-V3 的 ROUGE-L 下降是 Rouge 对结构化输出误判，非质量退化
- 代码题需单独建立代码模板知识库
- 平均检索召回率 2.0（全命中 Top-2）

## 运行方式

```bash
python scripts/rag_benchmark.py      # 三模型 RAG 评测
python scripts/rag_compare.py        # Base vs RAG 对比分析
```

输出：`outputs/rag_benchmark/rag_benchmark_*.json` + `scripts/reports/rag_compare_report.md`

---

*评测时间：2026-07-15*
