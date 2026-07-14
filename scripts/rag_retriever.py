import json
import os
import hashlib
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')

class RAGRetriever:
    """RAG 检索器：负责知识库向量化 + 语义检索"""

    def __init__(self, collection_name: str = "reasoning_kb"):
        """
        初始化检索器

        Args:
            collection_name: ChromaDB 集合名称
        """
        # 1. 初始化 ChromaDB（项目根目录下持久化存储）
        chroma_path = os.path.join(PROJECT_ROOT, 'chroma_db')
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 2. 初始化 Embedding 模型（中文用 BGE 系列效果较好）
        # 如果你网速慢，可以换成 'paraphrase-multilingual-MiniLM-L12-v2'（更小更快）
        self.embedding_model = SentenceTransformer(
            'BAAI/bge-small-zh-v1.5',  # 中文 embedding 模型
            device='cpu'  # 有 GPU 可改为 'cuda'
        )
        
        # 3. 获取或创建集合
        self.collection_name = collection_name
        try:
            self.collection = self.chroma_client.get_collection(collection_name)
            print(f"[OK] Loaded existing collection: {collection_name}")
        except Exception:
            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"description": "推理题解题步骤知识库"}
            )
            print(f"[OK] Created new collection: {collection_name}")
    
    def _get_embedding(self, text: str) -> List[float]:
        """获取文本的向量表示"""
        return self.embedding_model.encode(text).tolist()
    
    def _generate_doc_id(self, text: str) -> str:
        """根据文本内容生成唯一 ID（去重用）"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:16]
    
    def add_knowledge(self, knowledge_items: List[Dict[str, Any]]):
        """
        批量添加知识条目到向量库
        
        Args:
            knowledge_items: 知识条目列表，每条包含:
                - id: 唯一标识
                - question: 原始问题
                - steps: 解题步骤（字符串或列表）
                - answer: 标准答案
                - keywords: 关键词列表（可选）
        """
        if not knowledge_items:
            print("[WARN] Empty knowledge list, skipping")
            return
        
        documents = []
        ids = []
        metadatas = []
        
        for item in knowledge_items:
            # 将 steps 列表转为字符串，方便检索
            if isinstance(item['steps'], list):
                steps_text = '\n'.join(item['steps'])
            else:
                steps_text = item['steps']
            
            # 构建完整的文档内容（问题 + 步骤），让检索时能匹配到相关题
            doc_text = f"问题：{item['question']}\n解题步骤：{steps_text}\n答案：{item['answer']}"
            
            # 如果有关键词，也拼进去增强检索
            if 'keywords' in item and item['keywords']:
                doc_text += f"\n关键词：{', '.join(item['keywords'])}"
            
            documents.append(doc_text)
            ids.append(item['id'])
            metadatas.append({
                'question': item['question'],
                'steps': steps_text,
                'answer': item['answer'],
                'keywords': ','.join(item.get('keywords', []))
            })
        
        # 批量向量化（效率更高）
        print(f"Embedding {len(documents)} knowledge items...")
        embeddings = self.embedding_model.encode(documents).tolist()
        
        # 入库前先去重（检查 ID 是否已存在）
        existing_ids = set(self.collection.get()['ids'])
        new_ids = [id_ for id_ in ids if id_ not in existing_ids]
        new_indices = [i for i, id_ in enumerate(ids) if id_ not in existing_ids]
        
        if not new_ids:
            print("[WARN] All items already exist in vector DB, skipping")
            return
        
        self.collection.add(
            ids=new_ids,
            documents=[documents[i] for i in new_indices],
            embeddings=[embeddings[i] for i in new_indices],
            metadatas=[metadatas[i] for i in new_indices]
        )
        
        print(f"[OK] Added {len(new_ids)} items to vector DB")
    
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        检索与查询最相关的知识条目
        
        Args:
            query: 用户问题
            top_k: 返回最相似的 k 条
        
        Returns:
            检索结果列表，每条包含:
                - id: 知识条目 ID
                - question: 原始问题
                - steps: 解题步骤
                - answer: 标准答案
                - distance: 相似度距离（越小越相似）
                - metadata: 原始元数据
        """
        # 1. 将查询转为向量
        query_embedding = self._get_embedding(query)
        
        # 2. 在向量库中检索
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=['documents', 'metadatas', 'distances']
        )
        
        # 3. 格式化输出
        retrieved_items = []
        if results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                retrieved_items.append({
                    'id': doc_id,
                    'question': results['metadatas'][0][i]['question'],
                    'steps': results['metadatas'][0][i]['steps'],
                    'answer': results['metadatas'][0][i]['answer'],
                    'distance': results['distances'][0][i],
                    'metadata': results['metadatas'][0][i]
                })
        
        return retrieved_items
    
    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        count = self.collection.count()
        return {
            'collection_name': self.collection_name,
            'total_entries': count
        }
    
    def reset_collection(self):
        """重置集合（危险操作，仅用于调试）"""
        self.chroma_client.delete_collection(self.collection_name)
        self.collection = self.chroma_client.create_collection(
            name=self.collection_name,
            metadata={"description": "推理题解题步骤知识库"}
        )
        print(f"Reset collection: {self.collection_name}")


# ========== 测试代码 ==========
if __name__ == "__main__":
    # 1. 初始化检索器
    retriever = RAGRetriever()
    print(f"KB status: {retriever.get_stats()}")

    # 2. Load reasoning knowledge base
    knowledge_file = os.path.join(PROJECT_ROOT, 'data', 'knowledge_base', 'reasoning_steps.jsonl')
    if os.path.exists(knowledge_file):
        with open(knowledge_file, 'r', encoding='utf-8') as f:
            items = [json.loads(line) for line in f]
        print(f"Loaded {len(items)} items from knowledge base")
        retriever.add_knowledge(items)
    else:
        print(f"[WARN] Knowledge file not found: {knowledge_file}")
    
    # 3. 测试检索
    test_queries = [
        "一个水箱进水3升出水2升，10分钟后有多少水？",
        "甲乙相向而行，多久能相遇？",
        "长方形的长比宽多3厘米，周长34厘米，求长和宽"
    ]
    
    print("\n" + "=" * 60)
    print("Test Retrieval")
    print("=" * 60)

    for query in test_queries:
        print(f"\nQuery: {query}")
        results = retriever.retrieve(query, top_k=2)
        if results:
            for i, r in enumerate(results):
                print(f"  [{i+1}] {r['id']}  dist={r['distance']:.4f}  steps={len(r['steps'].split(chr(10)))}")
        else:
            print("  [WARN] No results found")