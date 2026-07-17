import os
import sys
import json
import glob
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

class LLMJudge:
    """使用 DeepSeek 作为裁判，评估模型回答质量"""
    
    def __init__(self, model_name: str = "deepseek-chat"):
        self.client = OpenAI(
            api_key=os.getenv('DEEPSEEK_API_KEY'),
            base_url="https://api.deepseek.com/v1"
        )
        self.model_name = model_name
    
    def judge(
        self,
        question: str,
        expected_answer: str,
        model_response: str,
        subset: str = "reasoning"
    ) -> Dict[str, Any]:
        """
        让 DeepSeek 充当评委，对模型回答进行多维度评分
        
        Args:
            question: 原始问题
            expected_answer: 标准答案（参考答案）
            model_response: 被评测模型的回答
            subset: 子集类型 (reasoning / code)
        
        Returns:
            包含各维度评分的字典
        """
        
        # ----- 根据子集类型定制评分维度 -----
        if subset == "reasoning":
            judge_prompt = f"""
你是一个大模型评测专家。请对以下【模型回答】进行打分，从三个维度评估：

【用户问题】
{question}

【参考答案】
{expected_answer}

【模型回答】
{model_response}

请用 1-5 分（1=极差，5=优秀）对以下三个维度评分，并给出简短理由：

1. **格式规范性** (Format)：回答是否结构清晰，是否包含分步推理、编号等。
2. **推理步骤完整性** (Step Completeness)：关键推理步骤是否完整，逻辑是否连贯。
3. **答案正确性** (Correctness)：最终答案是否正确（允许表述方式不同，但核心数值/结论要对）。

输出格式要求（必须严格 JSON）：
{{
    "format_score": (1-5),
    "format_reason": "简要说明",
    "step_score": (1-5),
    "step_reason": "简要说明", 
    "correctness_score": (1-5),
    "correctness_reason": "简要说明",
    "overall_score": (1-5，三个维度的平均值),
    "overall_reason": "总体评价"
}}
"""
        else:
            # code 或其它子集：简化维度
            judge_prompt = f"""
你是一个大模型评测专家。请对以下【模型回答】进行打分：

【用户问题】
{question}

【参考答案】
{expected_answer}

【模型回答】
{model_response}

请用 1-5 分（1=极差，5=优秀）对以下维度评分：

1. **代码正确性** (Correctness)：代码是否能正确执行并得到预期结果？
2. **代码质量** (Quality)：代码是否简洁、规范、可读性高？
3. **格式规范性** (Format)：是否只输出代码，没有多余解释？

输出格式要求（必须严格 JSON）：
{{
    "correctness_score": (1-5),
    "correctness_reason": "简要说明",
    "quality_score": (1-5),
    "quality_reason": "简要说明",
    "format_score": (1-5),
    "format_reason": "简要说明",
    "overall_score": (1-5),
    "overall_reason": "总体评价"
}}
"""
        
        # 调用 DeepSeek 作为 Judge
        result = None
        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "你是一个严格、客观的大模型评测专家。请严格按照 JSON 格式输出评分结果。不要用 ``` 代码块包裹，直接输出纯 JSON。"},
                        {"role": "user", "content": judge_prompt}
                    ],
                    temperature=0.1,  # 低温度保证评分稳定
                    max_tokens=1024,
                )

                raw = response.choices[0].message.content.strip()
                # Strip markdown code fences if present
                if raw.startswith('```'):
                    raw = raw.split('```')[1]
                    if raw.startswith('json'):
                        raw = raw[4:]
                    raw = raw.strip()
                result = json.loads(raw)
                break
            except Exception:
                if attempt < 2:
                    import time as t
                    t.sleep(0.3)

        if result and isinstance(result, dict):
            # 确保所有字段都存在
            if subset == "reasoning":
                required_fields = ['format_score', 'step_score', 'correctness_score', 'overall_score']
            else:
                required_fields = ['correctness_score', 'quality_score', 'format_score', 'overall_score']

            for field in required_fields:
                if field not in result:
                    result[field] = 0

            return result
        else:
            print(f'[WARN] Judge parse failed after retries')
            return {
                'format_score': 0,
                'step_score': 0,
                'correctness_score': 0,
                'overall_score': 0,
                'quality_score': 0,
                '_judge_error': True,
            }
    
    def batch_judge(
        self,
        samples: List[Dict[str, Any]],
        subset: str = "reasoning",
        max_samples: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        批量评估
        
        Args:
            samples: 样本列表，每条包含 question, expected, response
            subset: 子集类型
            max_samples: 最大评估条数（可选，用于快速验证）
        """
        if max_samples:
            samples = samples[:max_samples]
        
        results = []
        total = len(samples)
        
        print(f'\nLLM-as-Judge batch eval ({subset}, {total} samples)')
        print('=' * 60)

        for idx, sample in enumerate(samples, 1):
            print(f'  [{idx}/{total}] judging...', end=' ', flush=True)

            result = self.judge(
                question=sample.get('question', ''),
                expected_answer=sample.get('expected', ''),
                model_response=sample.get('response', ''),
                subset=subset
            )

            results.append({**sample, 'judge_scores': result})
            print(f'Overall: {result.get("overall_score", 0):.1f}/5')
            time.sleep(0.3)

        print(f'\nDone: {len(results)} samples judged')
        return results


# ========== 主程序 ==========
if __name__ == '__main__':
    # 1. Load RAG eval results (Base + RAG mode)
    eval_dir = os.path.join(PROJECT_ROOT, 'outputs', 'rag_eval')
    eval_files = sorted(glob.glob(os.path.join(eval_dir, 'rag_eval_*.json')), reverse=True)
    if not eval_files:
        print('[ERROR] No RAG eval results found. Run rag_eval.py first.')
        sys.exit(1)

    with open(eval_files[0], 'r', encoding='utf-8') as f:
        eval_data = json.load(f)

    details = eval_data['details']
    base_samples = [r for r in details if not r['use_rag']]
    rag_samples = [r for r in details if r['use_rag']]

    judge = LLMJudge()

    # 2. Judge Base mode
    print('=' * 60)
    print('[Base mode] reasoning questions')
    print('=' * 60)
    base_reasoning = [
        {'question': r['question'], 'expected': r['expected'], 'response': r['response']}
        for r in base_samples if r['subset'] == 'reasoning'
    ]
    base_judged = judge.batch_judge(base_reasoning, subset='reasoning')

    print()
    print('=' * 60)
    print('[RAG mode] reasoning questions')
    print('=' * 60)
    rag_reasoning = [
        {'question': r['question'], 'expected': r['expected'], 'response': r['response']}
        for r in rag_samples if r['subset'] == 'reasoning'
    ]
    rag_judged = judge.batch_judge(rag_reasoning, subset='reasoning')

    # 3. Compute stats
    def avg(rows, key):
        vals = [r['judge_scores'].get(key, 0) for r in rows]
        return sum(vals) / len(vals) if vals else 0

    print('\n' + '=' * 60)
    print('LLM-as-Judge: Base vs RAG (Reasoning, DeepSeek-V3)')
    print('=' * 60)
    print(f'{"Metric":<22} {"Base":>8} {"RAG":>8} {"Delta":>8}')
    print(f'{"-"*46}')
    for key, label in [('format_score', 'Format (1-5)'), ('step_score', 'Step (1-5)'), ('correctness_score', 'Correctness (1-5)'), ('overall_score', 'Overall (1-5)')]:
        b = avg(base_judged, key)
        r = avg(rag_judged, key)
        print(f'{label:<22} {b:>7.2f} {r:>7.2f} {r-b:>+7.2f}')

    # 4. Save
    output_path = os.path.join(PROJECT_ROOT, 'outputs', 'rag_eval', 'llm_judge_results.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': eval_data.get('timestamp', ''),
            'judge_model': 'deepseek-chat',
            'base_avg': {k: avg(base_judged, k) for k in ['format_score','step_score','correctness_score','overall_score']},
            'rag_avg': {k: avg(rag_judged, k) for k in ['format_score','step_score','correctness_score','overall_score']},
            'base_results': base_judged,
            'rag_results': rag_judged,
        }, f, indent=2, ensure_ascii=False)
    print(f'\nSaved: {output_path}')