import os
import sys
import json
from datetime import datetime
from typing import Optional, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# Add scripts/ to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rag_retriever import RAGRetriever
from rag_prompt_builder import RAGPromptBuilder

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

class RAGInference:
    """RAG 推理引擎：检索 → 重组 → 调用模型"""
    
    def __init__(self, 
                 model_name: str = "deepseek-chat",
                 api_key: Optional[str] = None,
                 api_base: str = "https://api.deepseek.com/v1",
                 use_rag: bool = True,
                 top_k: int = 3):
        """
        初始化 RAG 推理引擎
        
        Args:
            model_name: 模型名称
            api_key: API Key
            api_base: API 地址
            use_rag: 是否启用 RAG（False 则直接调用原始模型）
            top_k: 检索 Top-K 数量
        """
        self.model_name = model_name
        self.use_rag = use_rag
        
        # 初始化 OpenAI 客户端（兼容 DeepSeek/Qwen/GLM）
        self.client = OpenAI(
            api_key=api_key or os.getenv('DEEPSEEK_API_KEY'),
            base_url=api_base
        )
        
        # 如果启用 RAG，初始化检索器和 Prompt 构建器
        if use_rag:
            self.retriever = RAGRetriever()
            self.prompt_builder = RAGPromptBuilder(max_docs=top_k, include_answer=True)
        else:
            self.retriever = None
            self.prompt_builder = None
        
        print(f"[OK] RAG engine initialized")
        print(f"   Model: {model_name}  |  RAG: {'ON' if use_rag else 'OFF'}")
    
    def inference(self, query: str, temperature: float = 0.7) -> Dict[str, Any]:
        """
        执行推理
        
        Args:
            query: 用户问题
            temperature: 模型温度参数
        
        Returns:
            包含答案和中间信息的字典
        """
        result = {
            'query': query,
            'use_rag': self.use_rag,
            'timestamp': datetime.now().isoformat()
        }
        
        # ----- 步骤1: 检索（如果启用 RAG）-----
        retrieved_docs = []
        if self.use_rag and self.retriever:
            retrieved_docs = self.retriever.retrieve(query, top_k=3)
            result['retrieved_docs'] = [
                {
                    'id': doc['id'],
                    'question': doc['question'],
                    'distance': doc['distance']
                }
                for doc in retrieved_docs
            ]
        
        # ----- 步骤2: 构建 Prompt / Messages -----
        if self.use_rag and self.prompt_builder and retrieved_docs:
            messages = self.prompt_builder.build_messages(query, retrieved_docs)
        else:
            # 无 RAG：直接发原始问题
            messages = [
                {"role": "system", "content": "你是一个擅长数学推理的AI助手。"},
                {"role": "user", "content": query}
            ]
        
        result['messages'] = messages
        
        # ----- 步骤3: 调用模型 -----
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=2048,
            )
            
            result['response'] = response.choices[0].message.content
            result['success'] = True
            
        except Exception as e:
            result['response'] = None
            result['success'] = False
            result['error'] = str(e)
        
        return result


# ========== 测试代码 ==========
if __name__ == "__main__":
    # 测试用例：覆盖不同题型
    test_queries = [
        "一个水箱每分钟进水3升，出水2升。原本有5升水，10分钟后有多少升？",
        "甲乙两人从相距100公里的两地相向而行，甲速6km/h，乙速4km/h。甲出发1小时后乙才出发，问相遇时甲走了多少公里？",
        "一个长方形，长比宽多5厘米，周长是50厘米，求长和宽。"
    ]
    
    print("=" * 70)
    print("RAG Inference Engine Test")
    print("=" * 70)

    # 1. RAG enhanced
    print("\n" + "=" * 70)
    print("[Mode] RAG ON")
    print("=" * 70)

    rag_engine = RAGInference(
        model_name="deepseek-chat",
        use_rag=True,
        top_k=2
    )

    for query in test_queries:
        print(f"\nQuery: {query}")
        result = rag_engine.inference(query)

        if result['success']:
            print(f"  [OK] Answer: {result['response'][:200]}...")

            if result.get('retrieved_docs'):
                print(f"  Retrieved docs:")
                for doc in result['retrieved_docs']:
                    print(f"     - {doc['id']} dist={doc['distance']:.4f}")
        else:
            print(f"  [FAIL] {result.get('error')}")

        print("-" * 40)

    # 2. No RAG baseline
    print("\n" + "=" * 70)
    print("[Mode] RAG OFF (baseline)")
    print("=" * 70)

    base_engine = RAGInference(
        model_name="deepseek-chat",
        use_rag=False
    )

    query = test_queries[0]
    print(f"\nQuery: {query}")
    result = base_engine.inference(query)
    if result['success']:
        print(f"  [OK] Answer: {result['response'][:200]}...")