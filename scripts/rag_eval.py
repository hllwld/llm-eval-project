"""
rag_eval.py — RAG 增强 vs 基线 对比评测
模型: DeepSeek-V3 | 测试集: 推理15题 + 代码10题
指标: ROUGE-L / 格式规范性 / 步骤完整性 / 答案正确性
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI
from rouge_score import rouge_scorer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
sys.path.insert(0, BASE_DIR)
from rag_retriever import RAGRetriever
from rag_prompt_builder import RAGPromptBuilder

load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

QA_DIR = os.path.join(PROJECT_ROOT, 'data', 'custom_testset', 'qa')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'outputs', 'rag_eval')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── LLM Judge Prompt ──
JUDGE_PROMPT = """你是评测专家。根据以下信息对模型回答进行评判。仅输出JSON。

【问题】
{question}

【参考答案】
{reference}

【模型回答】
{response}

评判标准:
- format_score: 0或1 (1=包含结构化推理标记，如"步骤1/步骤2/首先/然后/最终答案")
- step_score: 0-3整数 (3=完整清晰 2=有步骤但跳跃 1=零散推理 0=无推理)
- answer_correct: true或false (最终答案是否与参考答案实质一致)

仅输出JSON，不要解释: {{"format_score": 1, "step_score": 2, "answer_correct": true}}"""


class RAGEvaluator:
    """RAG 效果评测器：对比 Base vs RAG 模式"""

    def __init__(self, model_name: str = "deepseek-chat"):
        self.model_name = model_name
        self.client = OpenAI(
            api_key=os.getenv('DEEPSEEK_API_KEY'),
            base_url="https://api.deepseek.com/v1"
        )
        self.retriever = RAGRetriever()
        self.prompt_builder = RAGPromptBuilder(max_docs=2, include_answer=True)
        self.scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)

    def _call_model(self, messages: List[Dict[str, str]]) -> str:
        try:
            resp = self.client.chat.completions.create(
                model=self.model_name, messages=messages,
                temperature=0.3, max_tokens=1024,
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"  [WARN] API error: {e}")
            return ""

    def _llm_judge(self, question: str, reference: str, response: str) -> Dict:
        prompt = JUDGE_PROMPT.format(question=question, reference=reference, response=response)
        try:
            resp = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.1, max_tokens=256,
            )
            content = resp.choices[0].message.content
            start = content.find('{')
            end = content.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except:
            pass
        return {'format_score': 0, 'step_score': 0, 'answer_correct': False}

    def eval_question(self, question: str, expected: str,
                      use_rag: bool = True, subset: str = "reasoning") -> Dict[str, Any]:
        # 1. RAG retrieval
        retrieved_docs = []
        if use_rag and subset == "reasoning":
            retrieved_docs = self.retriever.retrieve(question, top_k=2)

        # 2. Build prompt
        if use_rag and retrieved_docs:
            messages = self.prompt_builder.build_messages(question, retrieved_docs)
        else:
            system = "你是一个AI助手，请直接回答问题。"
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": question}
            ]

        # 3. Call model
        response = self._call_model(messages)

        # 4. ROUGE-L
        rouge_scores = self.scorer.score(expected, response)
        rouge_l = rouge_scores['rougeL'].fmeasure

        # 5. LLM Judge
        judge = self._llm_judge(question, expected, response)

        return {
            'question': question,
            'expected': expected,
            'response': response,
            'use_rag': use_rag,
            'subset': subset,
            'rouge_l': round(rouge_l, 4),
            'format_score': judge['format_score'],
            'step_score': judge['step_score'],
            'answer_correct': judge['answer_correct'],
            'retrieved_docs': [
                {'id': d['id'], 'distance': round(d['distance'], 4)}
                for d in retrieved_docs
            ]
        }

    def run_eval(self, test_data: List[Dict], subset: str = "reasoning",
                 use_rag: bool = True) -> List[Dict]:
        results = []
        total = len(test_data)
        mode = "RAG" if use_rag else "Base"

        print(f'\n{"="*60}')
        print(f'[{mode}] {subset} ({total} questions)')
        print(f'{"="*60}')

        for idx, item in enumerate(test_data, 1):
            q = item['query'].split('\n\n')[0].strip()
            print(f'  [{idx}/{total}] {q[:60]}...', end=' ', flush=True)

            result = self.eval_question(
                question=q, expected=item['response'],
                use_rag=use_rag, subset=subset
            )
            results.append(result)
            print(f'RougeL={result["rouge_l"]:.3f} fmt={result["format_score"]} step={result["step_score"]} correct={result["answer_correct"]}')
            time.sleep(0.3)

        return results


# ── Stats helper ──
def compute_stats(results: List[Dict]) -> Dict:
    n = len(results)
    if n == 0:
        return {}
    return {
        'count': n,
        'rouge_l_avg': sum(r['rouge_l'] for r in results) / n,
        'format_rate': sum(r['format_score'] for r in results) / n * 100,
        'step_avg': sum(r['step_score'] for r in results) / n,
        'accuracy': sum(1 for r in results if r['answer_correct']) / n * 100,
    }


# ========== Main ==========
if __name__ == '__main__':
    # 1. Load questions
    reasoning_qs = []
    code_qs = []
    for fname, lst in [('reasoning.jsonl', reasoning_qs), ('code.jsonl', code_qs)]:
        path = os.path.join(QA_DIR, fname)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                lst.extend(json.loads(line) for line in f if line.strip())

    print(f'Loaded: reasoning={len(reasoning_qs)} code={len(code_qs)}')

    evaluator = RAGEvaluator()

    # 2. Run Base mode
    base_r = evaluator.run_eval(reasoning_qs, subset="reasoning", use_rag=False)
    base_c = evaluator.run_eval(code_qs, subset="code", use_rag=False)

    # 3. Run RAG mode
    rag_r = evaluator.run_eval(reasoning_qs, subset="reasoning", use_rag=True)
    rag_c = evaluator.run_eval(code_qs, subset="code", use_rag=True)

    # 4. Compute stats
    base_all = base_r + base_c
    rag_all = rag_r + rag_c
    base_s = compute_stats(base_all)
    rag_s = compute_stats(rag_all)

    base_rs = compute_stats(base_r)
    rag_rs = compute_stats(rag_r)
    base_cs = compute_stats(base_c)
    rag_cs = compute_stats(rag_c)

    # 5. Print summary
    print(f'\n{"="*70}')
    print('RAG Eval Summary')
    print(f'{"="*70}')
    print(f'{"Metric":<22} {"Base":>10} {"RAG":>10} {"Delta":>10}')
    print(f'{"-"*52}')
    for label, b, r in [
        ('ROUGE-L (avg)', base_s['rouge_l_avg'], rag_s['rouge_l_avg']),
        ('Format Rate', base_s['format_rate'], rag_s['format_rate']),
        ('Step Score (avg)', base_s['step_avg'], rag_s['step_avg']),
        ('Accuracy', base_s['accuracy'], rag_s['accuracy']),
    ]:
        if isinstance(b, float) and b < 1:
            print(f'{label:<22} {b:>10.4f} {r:>10.4f} {r-b:>+10.4f}')
        else:
            print(f'{label:<22} {b:>9.1f}% {r:>9.1f}% {r-b:>+9.1f}%')

    print(f'\n-- Reasoning --')
    print(f'  Accuracy: Base={base_rs["accuracy"]:.1f}% RAG={rag_rs["accuracy"]:.1f}% Delta={rag_rs["accuracy"]-base_rs["accuracy"]:+.1f}%')
    print(f'  Step Avg: Base={base_rs["step_avg"]:.2f} RAG={rag_rs["step_avg"]:.2f} Delta={rag_rs["step_avg"]-base_rs["step_avg"]:+.2f}')
    print(f'\n-- Code --')
    print(f'  Accuracy: Base={base_cs["accuracy"]:.1f}% RAG={rag_cs["accuracy"]:.1f}% Delta={rag_cs["accuracy"]-base_cs["accuracy"]:+.1f}%')
    print(f'  Step Avg: Base={base_cs["step_avg"]:.2f} RAG={rag_cs["step_avg"]:.2f} Delta={rag_cs["step_avg"]-base_cs["step_avg"]:+.2f}')

    # 6. Save
    now = datetime.now().strftime('%Y%m%d_%H%M')
    json_path = os.path.join(OUTPUT_DIR, f'rag_eval_{now}.json')
    md_path = os.path.join(OUTPUT_DIR, f'rag_eval_{now}.md')

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {'base': base_s, 'rag': rag_s,
                        'base_reasoning': base_rs, 'rag_reasoning': rag_rs,
                        'base_code': base_cs, 'rag_code': rag_cs},
            'details': base_all + rag_all
        }, f, indent=2, ensure_ascii=False)

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f'# RAG Eval Report\n\n')
        f.write(f'> {now} | Model: DeepSeek-V3 | 25 questions\n\n')
        f.write(f'## Overall\n\n')
        f.write(f'| Metric | Base | RAG | Delta |\n')
        f.write(f'| --- | --- | --- | --- |\n')
        f.write(f'| ROUGE-L | {base_s["rouge_l_avg"]:.4f} | {rag_s["rouge_l_avg"]:.4f} | {rag_s["rouge_l_avg"]-base_s["rouge_l_avg"]:+.4f} |\n')
        f.write(f'| Format Rate | {base_s["format_rate"]:.1f}% | {rag_s["format_rate"]:.1f}% | {rag_s["format_rate"]-base_s["format_rate"]:+.1f}% |\n')
        f.write(f'| Step Score | {base_s["step_avg"]:.2f} | {rag_s["step_avg"]:.2f} | {rag_s["step_avg"]-base_s["step_avg"]:+.2f} |\n')
        f.write(f'| Accuracy | {base_s["accuracy"]:.1f}% | {rag_s["accuracy"]:.1f}% | {rag_s["accuracy"]-base_s["accuracy"]:+.1f}% |\n')
        f.write(f'\n## By Category\n\n')
        f.write(f'### Reasoning\n')
        f.write(f'| Metric | Base | RAG | Delta |\n')
        f.write(f'| --- | --- | --- | --- |\n')
        f.write(f'| Accuracy | {base_rs["accuracy"]:.1f}% | {rag_rs["accuracy"]:.1f}% | {rag_rs["accuracy"]-base_rs["accuracy"]:+.1f}% |\n')
        f.write(f'| Step Avg | {base_rs["step_avg"]:.2f} | {rag_rs["step_avg"]:.2f} | {rag_rs["step_avg"]-base_rs["step_avg"]:+.2f} |\n')
        f.write(f'\n### Code\n')
        f.write(f'| Metric | Base | RAG | Delta |\n')
        f.write(f'| --- | --- | --- | --- |\n')
        f.write(f'| Accuracy | {base_cs["accuracy"]:.1f}% | {rag_cs["accuracy"]:.1f}% | {rag_cs["accuracy"]-base_cs["accuracy"]:+.1f}% |\n')
        f.write(f'| Step Avg | {base_cs["step_avg"]:.2f} | {rag_cs["step_avg"]:.2f} | {rag_cs["step_avg"]-base_cs["step_avg"]:+.2f} |\n')

    print(f'\nSaved: {json_path}')
    print(f'Saved: {md_path}')
