from typing import List, Dict, Any

class RAGPromptBuilder:
    """RAG Prompt 构建器：将检索到的知识重组为模型输入"""
    
    def __init__(self, max_docs: int = 3, include_answer: bool = False):
        """
        Args:
            max_docs: 最多插入几条检索结果
            include_answer: 是否在示例中包含答案（True = 提供完整示例，False = 只给步骤）
        """
        self.max_docs = max_docs
        self.include_answer = include_answer
    
    def build_prompt(self, query: str, retrieved_docs: List[Dict[str, Any]]) -> str:
        """
        构建 RAG 增强后的 Prompt
        
        Args:
            query: 用户原始问题
            retrieved_docs: 检索结果列表，每条包含 question、steps、answer 等字段
        
        Returns:
            完整的 Prompt 字符串
        """
        # 如果没有检索到任何文档，返回原始问题
        if not retrieved_docs:
            return query
        
        # 限制文档数量
        docs_to_use = retrieved_docs[:self.max_docs]
        
        # 构建 Prompt 头部
        prompt_parts = [
            "你是一个擅长数学推理的助手。请参考以下解题示例，用同样的分步推理方式回答用户问题。",
            "",
            "【参考示例】"
        ]
        
        # 逐个插入检索到的示例
        for i, doc in enumerate(docs_to_use, 1):
            prompt_parts.append(f"\n示例 {i}：")
            prompt_parts.append(f"问题：{doc['question']}")
            prompt_parts.append(f"解题步骤：\n{doc['steps']}")
            if self.include_answer:
                prompt_parts.append(f"答案：{doc['answer']}")
        
        # 添加用户问题
        prompt_parts.extend([
            "",
            "【用户问题】",
            f"{query}",
            "",
            "请按以下格式输出：",
            "1. 推理过程：（分步展示你的推理）",
            "2. 最终答案：（给出最终结果）"
        ])
        
        return '\n'.join(prompt_parts)
    
    def build_messages(self, query: str, retrieved_docs: List[Dict[str, Any]], 
                       system_prompt: str = None) -> List[Dict[str, str]]:
        """
        构建 OpenAI 格式的 messages 列表（用于 API 调用）
        
        Args:
            query: 用户原始问题
            retrieved_docs: 检索结果列表
            system_prompt: 自定义 System Prompt（可选）
        
        Returns:
            OpenAI Chat 格式的 messages 列表
        """
        if system_prompt is None:
            system_prompt = "你是一个擅长数学推理和解题的AI助手。"
        
        user_content = self.build_prompt(query, retrieved_docs)
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]


# ========== 测试代码 ==========
if __name__ == "__main__":
    # 模拟检索结果
    mock_docs = [
        {
            'id': 'R-001',
            'question': '一个水箱每分钟进水3升，出水2升。原本有5升水，10分钟后有多少升？',
            'steps': '步骤1: 净增速 = 3 - 2 = 1 升/分钟\n步骤2: 10分钟净增 = 1 × 10 = 10 升\n步骤3: 最终水量 = 5 + 10 = 15升',
            'answer': '15升'
        },
        {
            'id': 'R-003',
            'question': '一个班级有40人，其中男生占60%，女生中有25%是近视。问男生有多少人？女生中近视的有多少人？',
            'steps': '步骤1: 男生 = 40 × 60% = 24 人\n步骤2: 女生 = 40 - 24 = 16 人\n步骤3: 女生中近视 = 16 × 25% = 4 人',
            'answer': '男生24人，女生中近视4人'
        }
    ]
    
    builder = RAGPromptBuilder(max_docs=2, include_answer=True)
    
    # 测试 Prompt 构建
    query = "一个水池有进水管和出水管，进水管5小时注满，出水管8小时放完，两管同时开多久注满？"
    prompt = builder.build_prompt(query, mock_docs)
    
    print("=" * 60)
    print("RAG Prompt Preview")
    print("=" * 60)
    print(prompt)

    # Test messages format
    messages = builder.build_messages(query, mock_docs)
    print("\n" + "=" * 60)
    print("Messages (API format)")
    print("=" * 60)
    for msg in messages:
        print(f"{msg['role'].upper()}: {msg['content'][:100]}...")