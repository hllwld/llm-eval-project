# RAG 检索器报告

> 对应脚本：`rag_retriever.py` | Day 13

## 概述

- **向量数据库**：ChromaDB v1.5.9（本地持久化，`chroma_db/`）
- **Embedding 模型**：BAAI/bge-small-zh-v1.5（中文优化，CPU 推理）
- **知识库规模**：15 条推理题解题步骤
- **检索精度**：Precision@1 = 100%（15/15 全命中）

## 技术实现

```python
# 初始化
chroma_client = chromadb.PersistentClient(path="./chroma_db/")
embedding_model = SentenceTransformer('BAAI/bge-small-zh-v1.5')

# 向量化入库
embeddings = embedding_model.encode(documents).tolist()
collection.add(ids=ids, documents=docs, embeddings=embeddings)

# 语义检索
results = collection.query(query_embeddings=[query_vec], n_results=3)
```

## 检索验证结果

| 查询 | Top-1 ID | 距离 | 命中 |
|---|---|---|---|
| 水箱进水出水 | R-001 | 0.24 | HIT |
| 相向而行相遇 | R-004 | 0.21 | HIT |
| 长方形对角线 | R-007 | 0.31 | HIT |
| ...（全部 15 题） | ... | 0.17~0.41 | **100%** |

## 运行方式

```bash
cd llm-eval-project
python scripts/rag_retriever.py
```

首次运行自动从 `data/knowledge_base/reasoning_steps.jsonl` 向量化入库，后续运行检测已存在则跳过（去重）。

---

*创建时间：2026-07-14*
