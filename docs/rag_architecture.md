# RAG 优化方案 — 技术架构设计

> 基于 badcase 分析结论：11% Badcase 为真知识缺失（RAG可解），89% 可通过知识注入改善推理质量

## 一、整体流程

```
                    ┌──────────────────────────────────────────────────────────┐
                    │                  RAG 增强推理流程                         │
                    ├──────────────────────────────────────────────────────────┤
                    │                                                          │
                    │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌───────┐ │
                    │  │ 用户问题  │──▶│ 向量检索  │──▶│ 召回Top-3│──▶│Prompt │ │
                    │  │ "水箱进水"│   │ ChromaDB │   │ 解题示例  │   │ 重组   │ │
                    │  └──────────┘   └──────────┘   └──────────┘   └───────┘ │
                    │                                                     │    │
                    │                                                     ▼    │
                    │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌───────┐ │
                    │  │ 结果输出  │◀──│ 模型生成  │◀──│ API调用   │◀──│增强   │ │
                    │  │ "15升"   │   │ DeepSeek │   │ 带上下文  │   │Prompt │ │
                    │  └──────────┘   └──────────┘   └──────────┘   └───────┘ │
                    │                                                          │
                    └──────────────────────────────────────────────────────────┘
```

## 二、知识库内容规划

| 子集 | 知识库内容 | 来源 | 条目 | 向量化方式 |
|------|-----------|------|------|-----------|
| **推理** | 每道推理题的**标准解题步骤** | 人工撰写 | 15 条 | text-embedding-3-small |
| **推理** | 通用数学公式/定理 | 教材整理 | 10 条 | 同上 |
| **代码** | 代码模板/最佳实践 | 人工撰写 | 10 条 | 同上 |
| **知识** | 地理/历史易错知识点 | 从 badcase 反推 | 5 条 | 同上 |
| **合计** | | | **40 条** | |

### 推理知识库示例

```json
{
  "id": "REASON-001",
  "question": "一个水箱每分钟进水3升，出水2升。原本有5升水，10分钟后有多少升？",
  "steps": [
    "步骤1: 计算净增速 = 进水 - 出水 = 3 - 2 = 1 升/分钟",
    "步骤2: 计算10分钟净增加 = 1 × 10 = 10 升",
    "步骤3: 计算最终水量 = 初始5升 + 净增10升 = 15升"
  ],
  "answer": "15升",
  "keywords": ["水箱", "进水", "出水", "净增速"]
}
```

### 知识易错点示例（来自 badcase K-013）

```json
{
  "id": "KNOW-001",
  "question": "赤道穿过哪个大洲的面积最大？",
  "knowledge": "赤道横穿非洲中部，经过加蓬、刚果（布）、刚果（金）、乌干达、肯尼亚、索马里共6国，穿越面积约380万平方公里，居各大洲之首。南美洲赤道穿越巴西、厄瓜多尔、哥伦比亚3国，面积约200万平方公里。",
  "answer": "B（非洲）",
  "keywords": ["赤道", "大洲", "非洲", "面积"]
}
```

## 三、技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| 向量数据库 | **ChromaDB**（本地模式） | 零配置、Python 原生、自带 embedding、适合 40 条规模 |
| Embedding | **text-embedding-3-small**（OpenAI） 或 **bge-small-zh**（本地 BGE） | 中文语义匹配好、成本极低 |
| 检索策略 | **相似度 Top-3 + 关键词补召** | BM25 + 向量双路，确保高召回 |
| LLM | **DeepSeek-V3**（已有 key） | 评测已验证为最强推理模型 |
| Prompt 模板 | **Few-shot 注入**：检索结果放在 system prompt 中作为示例 | 简单、可控、不污染 user message |

## 四、核心代码骨架

### 4.1 知识库构建（`build_kb.py`）

```python
import chromadb
import json

# 初始化 ChromaDB（本地持久化）
client = chromadb.PersistentClient(path="./data/rag_chroma")
collection = client.get_or_create_collection(
    name="math_reasoning",
    metadata={"hnsw:space": "cosine"}
)

# 加载知识库
with open("data/rag_knowledge/reasoning.json", "r") as f:
    knowledge = json.load(f)

# 逐条入库
for item in knowledge:
    collection.add(
        documents=[json.dumps(item["steps"], ensure_ascii=False)],
        metadatas=[{"id": item["id"], "keywords": ",".join(item["keywords"])}],
        ids=[item["id"]]
    )
```

### 4.2 检索 + 增强推理（`rag_infer.py`）

```python
def rag_enhanced_query(question: str, collection, model_config: dict) -> str:
    """检索相似知识 + 构造增强 Prompt + 调用模型"""
    
    # Step 1: 向量检索 Top-3
    results = collection.query(query_texts=[question], n_results=3)
    
    # Step 2: 构造 Few-shot Prompt
    examples = "\n\n".join(
        f"【示例 {i+1}】\n{doc}"
        for i, doc in enumerate(results["documents"][0])
    )
    
    enhanced_prompt = f"""你是一个解题助手。以下是类似的解题示例，请参考其步骤解答用户问题。

{examples}

【用户问题】
{question}

请按步骤解答，最终输出答案。"""
    
    # Step 3: 调用 LLM
    import requests
    resp = requests.post(
        model_config["api_url"],
        headers={"Authorization": f'Bearer {model_config["api_key"]}'},
        json={
            "model": model_config["model"],
            "messages": [
                {"role": "system", "content": "你是一个数学解题助手。"},
                {"role": "user", "content": enhanced_prompt}
            ],
            "temperature": 0.3, "max_tokens": 1024
        }
    )
    return resp.json()["choices"][0]["message"]["content"]
```

### 4.3 Prompt 模板层级

```
┌─────────────────────────────────────────┐
│ System Prompt（固定）                    │
│ "你是一个数学解题助手。"                   │
├─────────────────────────────────────────┤
│ Few-shot Examples（动态，检索注入）        │
│ 【示例1】水箱问题 → 步骤1/2/3             │
│ 【示例2】相遇问题 → 相对速度公式           │
│ 【示例3】百分比计算 → 基数×比例            │
├─────────────────────────────────────────┤
│ User Question（用户输入）                  │
│ "一个班级50人，男生占60%，女生多少人？"     │
└─────────────────────────────────────────┘
```

## 五、评测方案

### 对比实验设计

| 实验组 | 配置 | 预期 |
|------|------|------|
| **Baseline** | 无 RAG，直接调用 DeepSeek-V3 | 基准分（当前 v3 推理 49.68%） |
| **RAG-Top1** | 检索 1 条最相似示例注入 | 推理分 +5~8pp |
| **RAG-Top3** | 检索 3 条相似示例注入 | 推理分 +8~15pp |
| **RAG+关键词** | 向量 + BM25 双路召回 | 推理分 +10~18pp |

### 指标

- **Rouge-L-R**（与 v3 可比）
- **人工抽检**（5 题 × 0/1/2 三档评分）
- **RAG 命中率**：检索到的示例与题目真正相关的比例

### 预期收益

```
知识类 MCQ:  95% ──RAG知识库──▶ 98%（补 1 道错题的知识盲区）
推理类 QA:   50% ──RAG步骤示例─▶ 60~65%（参考同类题解题模式）
代码类 QA:   56% ──RAG模板注入─▶ 60~65%（代码模板减少格式偏差）
                            ─────
            综合提升预估: +5~10 个百分点
```

## 六、实施计划

| Day | 任务 | 产出 |
|-----|------|------|
| Day 13 | 搭建 ChromaDB + 构建知识库 | `build_kb.py` + `data/rag_knowledge/` |
| Day 14 | 实现 RAG 推理管道 | `rag_infer.py` |
| Day 15 | 跑 Baseline→RAG-Top3 对比实验 | 对比报告 |
| Day 16 | 调优：双路召回 + Prompt 模板 | 优化版 |
| Day 17 | 全量评测 + 对比报告 | `rag_eval_report.md` |

---

*创建时间：2026-07-10 | 对应 badcase 分析见 `scripts/reports/badcase_report_report.md`*
