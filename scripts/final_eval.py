"""
final_eval.py — 最终统一评测（全 53 题）
- MCQ (28题): Accuracy
- QA 推理 (15题): ROUGE-L + LLM Judge + RAG对比
- QA 代码 (10题): ROUGE-L + LLM Judge
- 配置: model_config.yaml + .env
- 输出: scripts/reports/final_eval_report.md
"""

import os
import sys
import csv
import json
import time
import yaml
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI
from rouge_score import rouge_scorer

from paths import (
    PROJECT_ROOT, MCQ_DIR, QA_DIR, FINAL_EVAL_REPORT as REPORT_PATH,
    FINAL_EVAL_DIR as OUTPUT_DIR, INSIGHTS_JSON,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rag_retriever import RAGRetriever
from rag_prompt_builder import RAGPromptBuilder
from llm_as_judge import LLMJudge

load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

os.makedirs(OUTPUT_DIR, exist_ok=True)


class FinalEval:
    def __init__(self, tier: str = 'full'):
        self.tier = tier
        self.models = self._load_models()
        self.reasoning_retriever = RAGRetriever('reasoning_kb')
        self.code_retriever = RAGRetriever('code_kb')
        self.builder = RAGPromptBuilder(max_docs=2, include_answer=True)
        self.scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
        self.judge = LLMJudge()
        self.mcq = self._load_mcq()
        self.reasoning = self._load_qa('reasoning.jsonl')
        self.code = self._load_qa('code.jsonl')
        if tier != 'full':
            print(f'[TIER] Filtering: {tier} (MCQ={len(self.mcq)}, Reasoning={len(self.reasoning)}, Code={len(self.code)})')

    def _load_models(self) -> Dict:
        with open(os.path.join(PROJECT_ROOT, 'config', 'model_config.yaml'), 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        models = {}
        for m in config['models']:
            if not m.get('active', True):
                continue
            key = os.getenv(m.get('api_key_env', ''), '')
            if key:
                models[m['name']] = {'model': m['model_id'], 'api_url': m['api_url'], 'api_key': key}
        return models

    def _load_mcq(self) -> List[Dict]:
        items = []
        for fname in ['knowledge_val.csv', 'security_val.csv']:
            path = os.path.join(MCQ_DIR, fname)
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8') as f:
                    for row in csv.DictReader(f):
                        tier = row.get('tier', 'full')
                        if self.tier == 'smoke' and tier != 'smoke':
                            continue
                        opts = [row.get(k, '') for k in ['A', 'B', 'C', 'D', 'E'] if row.get(k, '').strip()]
                        items.append({
                            'id': row.get('id', ''),
                            'subset': fname.replace('_val.csv', ''),
                            'question': row['question'],
                            'options': opts,
                            'answer': row['answer'].strip().upper(),
                        })
        return items

    def _load_qa(self, fname: str) -> List[Dict]:
        items = []
        path = os.path.join(QA_DIR, fname)
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        tier = item.get('tier', 'full')
                        if self.tier == 'smoke' and tier != 'smoke':
                            continue
                        items.append({
                            'question': item['query'].split('\n\n')[0].strip(),
                            'expected': item['response']
                        })
        return items

    def _call(self, mc: Dict, messages: List[Dict]) -> tuple:
        """Returns (response_text, token_usage_dict, latency_ms)"""
        base_url = mc['api_url'].rstrip('/').replace('/chat/completions', '')
        client = OpenAI(api_key=mc['api_key'], base_url=base_url)
        t0 = time.time()
        resp = client.chat.completions.create(
            model=mc['model'], messages=messages, temperature=0.3, max_tokens=1024, timeout=60
        )
        latency = (time.time() - t0) * 1000
        tokens = {'prompt': 0, 'completion': 0, 'total': 0}
        if resp.usage:
            tokens = {'prompt': resp.usage.prompt_tokens, 'completion': resp.usage.completion_tokens, 'total': resp.usage.total_tokens}
        return resp.choices[0].message.content, tokens, latency

    def _eval_mcq(self, mc: Dict) -> Dict:
        """Run all 28 MCQ questions, return accuracy per subset + token stats"""
        correct = {'knowledge': 0, 'security': 0}
        total = {'knowledge': 0, 'security': 0}
        all_tokens = []
        print(f'\n  [MCQ] {len(self.mcq)} questions...')

        for i, q in enumerate(self.mcq):
            opts_text = '\n'.join(f'{chr(65+j)}) {o}' for j, o in enumerate(q['options']))
            prompt = f"单选题，选出正确答案，只输出字母。\n\n{q['question']}\n{opts_text}"
            resp, tokens, lat = self._call(mc, [{'role': 'user', 'content': prompt}])
            all_tokens.append(tokens)
            ans = ''.join(c for c in resp.strip().upper()[:5] if c in 'ABCDE') or '?'
            ans = ans[0] if ans else '?'
            if ans == q['answer']:
                correct[q['subset']] += 1
            total[q['subset']] += 1
            if (i + 1) % 10 == 0:
                print(f'    {i+1}/{len(self.mcq)}...')

        sum_tokens = sum(t['total'] for t in all_tokens) if all_tokens else 0
        n = len(all_tokens) if all_tokens else 1
        return {
            'knowledge_acc': correct['knowledge'] / total['knowledge'] if total['knowledge'] else 0,
            'security_acc': correct['security'] / total['security'] if total['security'] else 0,
            'knowledge_correct': correct['knowledge'], 'knowledge_total': total['knowledge'],
            'security_correct': correct['security'], 'security_total': total['security'],
            'total_tokens': sum_tokens, 'avg_tokens': round(sum_tokens / n, 1),
        }

    def _eval_qa(self, mc: Dict, questions: List[Dict], subset: str, use_rag: bool = False) -> List[Dict]:
        mode = 'RAG' if use_rag else 'Base'
        results = []
        print(f'\n  [{mode}] {subset} {len(questions)} questions...')

        for i, q in enumerate(questions):
            if use_rag and subset == 'reasoning':
                docs = self.reasoning_retriever.retrieve(q['question'], top_k=2)
                messages = self.builder.build_messages(q['question'], docs) if docs else [
                    {'role': 'user', 'content': q['question']}
                ]
            elif use_rag and subset == 'code':
                docs = self.code_retriever.retrieve(q['question'], top_k=2)
                messages = self.builder.build_messages(q['question'], docs) if docs else [
                    {'role': 'user', 'content': q['question']}
                ]
            else:
                messages = [
                    {'role': 'system', 'content': '你是AI助手，请直接回答问题。'},
                    {'role': 'user', 'content': q['question']}
                ]

            response, tokens, lat = self._call(mc, messages)
            rouge = self.scorer.score(q['expected'], response)['rougeL'].fmeasure
            results.append({
                'question': q['question'], 'expected': q['expected'],
                'response': response, 'rouge_l': round(rouge, 4),
                'tokens': tokens, 'latency_ms': round(lat, 1),
            })
            if (i + 1) % 5 == 0:
                print(f'    {i+1}/{len(questions)}...')
            time.sleep(0.3)

        # LLM Judge
        samples = [{'question': r['question'], 'expected': r['expected'], 'response': r['response']} for r in results]
        judged = self.judge.batch_judge(samples, subset=subset)
        for r, j in zip(results, judged):
            r['judge'] = j['judge_scores']
        return results

    def _eval_one_model(self, name: str, mc: Dict) -> Dict:
        """Run all 5 eval steps for one model"""
        print(f'\n{"="*60}')
        print(f'>> {name} ({mc["model"]})')
        print(f'{"="*60}')

        mcq_result = self._eval_mcq(mc)
        reasoning_base = self._eval_qa(mc, self.reasoning, 'reasoning', use_rag=False)
        reasoning_rag = self._eval_qa(mc, self.reasoning, 'reasoning', use_rag=True)
        code_base = self._eval_qa(mc, self.code, 'code', use_rag=False)
        code_rag = self._eval_qa(mc, self.code, 'code', use_rag=True)

        return {
            'mcq': mcq_result,
            'reasoning_base': reasoning_base,
            'reasoning_rag': reasoning_rag,
            'code_base': code_base,
            'code_rag': code_rag,
        }

    def run(self):
        print(f'Models: {list(self.models.keys())}')
        print(f'Testset: MCQ={len(self.mcq)}  Reasoning={len(self.reasoning)}x2  Code={len(self.code)}x2  Total={len(self.mcq)+len(self.reasoning)*2+len(self.code)*2}')

        # Parallel execution: all models run simultaneously
        from concurrent.futures import ThreadPoolExecutor, as_completed
        all_results = {}
        with ThreadPoolExecutor(max_workers=len(self.models)) as executor:
            futures = {executor.submit(self._eval_one_model, name, mc): name for name, mc in self.models.items()}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    all_results[name] = future.result()
                except Exception as e:
                    print(f'[FATAL] Model {name} failed: {e}')
                    raise

        self._save_report(all_results)

    def _save_report(self, all_results: Dict):
        now = datetime.now().strftime('%Y-%m-%d %H:%M')

        def qa_stats(rows, key):
            if callable(key):
                vals = [key(r) for r in rows]
            else:
                vals = [r[key] for r in rows]
            return sum(vals) / len(vals) if vals else 0

        lines = [
            '# Final Eval Report',
            f'> {now} | Models: {len(self.models)} | 28 MCQ + 15x2 Reasoning + 10 Code = 68 inferences/model',
            '',
            '## 1. MCQ (Accuracy)',
            '',
            '| Model | Knowledge (20) | Security (8) | Overall (28) |',
            '| --- | --- | --- | --- |',
        ]
        for name, data in all_results.items():
            m = data['mcq']
            k = m['knowledge_acc']; s = m['security_acc']
            o = (m['knowledge_correct'] + m['security_correct']) / (m['knowledge_total'] + m['security_total'])
            lines.append(f'| {name} | {k:.0%} ({m["knowledge_correct"]}/{m["knowledge_total"]}) | {s:.0%} ({m["security_correct"]}/{m["security_total"]}) | {o:.0%} |')

        lines += [
            '',
            '## 2. QA Reasoning (ROUGE-L)',
            '',
            '| Model | Base | RAG | Delta |',
            '| --- | --- | --- | --- |',
        ]
        for name, data in all_results.items():
            b = qa_stats(data['reasoning_base'], 'rouge_l')
            r = qa_stats(data['reasoning_rag'], 'rouge_l')
            lines.append(f'| {name} | {b:.2%} | {r:.2%} | {r-b:+.2%} |')

        lines += [
            '',
            '## 3. QA Reasoning (LLM Judge 1-5)',
            '',
            '| Model | Mode | Format | Step | Correct | Overall |',
            '| --- | --- | --- | --- | --- | --- |',
        ]
        for name, data in all_results.items():
            for mode, key in [('Base', 'reasoning_base'), ('RAG', 'reasoning_rag')]:
                rows = data[key]
                f = qa_stats(rows, lambda r: r['judge'].get('format_score', 0))
                s = qa_stats(rows, lambda r: r['judge'].get('step_score', 0))
                c = qa_stats(rows, lambda r: r['judge'].get('correctness_score', 0))
                o = qa_stats(rows, lambda r: r['judge'].get('overall_score', 0))
                lines.append(f'| {name} | {mode} | {f:.2f} | {s:.2f} | {c:.2f} | {o:.2f} |')

        lines += [
            '',
            '## 4. QA Code (ROUGE-L + Judge)',
            '',
            '| Model | Base Rouge | RAG Rouge | Delta | Base Judge | RAG Judge |',
            '| --- | --- | --- | --- | --- | --- |',
        ]
        for name, data in all_results.items():
            base_rows = data['code_base']
            rag_rows = data['code_rag']
            br = qa_stats(base_rows, 'rouge_l')
            rr = qa_stats(rag_rows, 'rouge_l')
            bj = qa_stats(base_rows, lambda r: r['judge'].get('overall_score', 0))
            rj = qa_stats(rag_rows, lambda r: r['judge'].get('overall_score', 0))
            lines.append(f'| {name} | {br:.2%} | {rr:.2%} | {rr-br:+.2%} | {bj:.2f} | {rj:.2f} |')

        lines += [
            '',
            '## 5. Token 消耗统计',
            '',
            '| Model | MCQ Tokens | Reasoning Base | Reasoning RAG | Code Base | Code RAG | Total |',
            '| --- | --- | --- | --- | --- | --- | --- |',
        ]
        for name, data in all_results.items():
            mt = data['mcq'].get('total_tokens', 0)
            rb = sum(r['tokens']['total'] for r in data['reasoning_base']) if 'tokens' in data['reasoning_base'][0] else 0
            rr = sum(r['tokens']['total'] for r in data['reasoning_rag'])
            cb = sum(r['tokens']['total'] for r in data['code_base'])
            cr = sum(r['tokens']['total'] for r in data['code_rag'])
            total = mt + rb + rr + cb + cr
            lines.append(f'| {name} | {mt} | {rb} | {rr} | {cb} | {cr} | **{total}** |')

        # Load AI-generated insights if available
        lines += ['', '## 6. Conclusion（LLM 自动分析）', '']
        if os.path.exists(INSIGHTS_JSON):
            with open(INSIGHTS_JSON, 'r', encoding='utf-8') as _f:
                _ins = json.load(_f)
            for ins in _ins.get('insights', []):
                emoji = '[+]' if ins.get('sentiment') == 'positive' else ('[-]' if ins.get('sentiment') == 'negative' else '[*]')
                lines.append(f'- **{ins["title"]}**: {ins["detail"]}')
            if _ins.get('improvements'):
                lines += ['', '### 改进建议', '']
                for imp in _ins['improvements']:
                    lines.append(f'- **[{imp["priority"]}]** {imp["measure"]} — {imp["effect"]}')
        else:
            lines += ['- Run insight_generator.py to generate AI analysis', '']

        report = '\n'.join(lines)
        os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
        with open(REPORT_PATH, 'w', encoding='utf-8') as f:
            f.write(report)

        # Aggregated stats (for dashboard)
        json_path = os.path.join(OUTPUT_DIR, f'final_eval_{now[:10].replace("-","")}.json')
        json_data = {'timestamp': now, 'models': list(self.models.keys())}

        # Raw responses (for audit)
        raw_path = os.path.join(OUTPUT_DIR, f'final_eval_raw_{now[:10].replace("-","")}.json')
        raw_data = {'timestamp': now, 'models': list(self.models.keys())}
        for name, data in all_results.items():
            json_data[name] = {
                'mcq': data['mcq'],
                'reasoning_base_tokens': sum(r['tokens']['total'] for r in data['reasoning_base']) if data['reasoning_base'] and 'tokens' in data['reasoning_base'][0] else 0,
                'reasoning_rag_tokens': sum(r['tokens']['total'] for r in data['reasoning_rag']) if data['reasoning_rag'] and 'tokens' in data['reasoning_rag'][0] else 0,
                'code_base_tokens': sum(r['tokens']['total'] for r in data['code_base']) if data['code_base'] and 'tokens' in data['code_base'][0] else 0,
                'code_rag_tokens': sum(r['tokens']['total'] for r in data['code_rag']) if data['code_rag'] and 'tokens' in data['code_rag'][0] else 0,
                'avg_latency_ms': round(
                    sum(r.get('latency_ms', 0) for r in (data['reasoning_base'] + data['reasoning_rag'] + data['code_base'] + data['code_rag']))
                    / max(len(data['reasoning_base'] + data['reasoning_rag'] + data['code_base'] + data['code_rag']), 1), 1
                ),
                'hallucination_rate': round(
                    sum(1 for r in (data['reasoning_base'] + data['reasoning_rag'] + data['code_base'] + data['code_rag'])
                        if r.get('judge', {}).get('correctness_score', 5) < 3)
                    / max(len(data['reasoning_base'] + data['reasoning_rag'] + data['code_base'] + data['code_rag']), 1), 4
                ),
                'reasoning_base_rouge': qa_stats(data['reasoning_base'], 'rouge_l'),
                'reasoning_rag_rouge': qa_stats(data['reasoning_rag'], 'rouge_l'),
                'reasoning_base_judge': {
                    'format': qa_stats(data['reasoning_base'], lambda r: r['judge'].get('format_score', 0)),
                    'step': qa_stats(data['reasoning_base'], lambda r: r['judge'].get('step_score', 0)),
                    'overall': qa_stats(data['reasoning_base'], lambda r: r['judge'].get('overall_score', 0)),
                },
                'reasoning_rag_judge': {
                    'format': qa_stats(data['reasoning_rag'], lambda r: r['judge'].get('format_score', 0)),
                    'step': qa_stats(data['reasoning_rag'], lambda r: r['judge'].get('step_score', 0)),
                    'overall': qa_stats(data['reasoning_rag'], lambda r: r['judge'].get('overall_score', 0)),
                },
                'code_base_rouge': qa_stats(data['code_base'], 'rouge_l'),
                'code_rag_rouge': qa_stats(data['code_rag'], 'rouge_l'),
                'code_base_judge': {
                    'format': qa_stats(data['code_base'], lambda r: r['judge'].get('format_score', 0)),
                    'overall': qa_stats(data['code_base'], lambda r: r['judge'].get('overall_score', 0)),
                },
                'code_rag_judge': {
                    'format': qa_stats(data['code_rag'], lambda r: r['judge'].get('format_score', 0)),
                    'overall': qa_stats(data['code_rag'], lambda r: r['judge'].get('overall_score', 0)),
                },
            }
            # Raw responses for audit
            raw_data[name] = {
                'mcq_responses': [{
                    'question': q['question'], 'answer': q['answer'],
                    'subset': q['subset'], 'options': q['options'],
                } for q in self.mcq],
                'reasoning_base': [{
                    'question': r['question'], 'expected': r['expected'],
                    'response': r['response'], 'rouge_l': r['rouge_l'],
                    'tokens': r['tokens'], 'latency_ms': r.get('latency_ms', 0),
                    'judge': r['judge'],
                } for r in data['reasoning_base']],
                'reasoning_rag': [{
                    'question': r['question'], 'expected': r['expected'],
                    'response': r['response'], 'rouge_l': r['rouge_l'],
                    'tokens': r['tokens'], 'latency_ms': r.get('latency_ms', 0),
                    'judge': r['judge'],
                } for r in data['reasoning_rag']],
                'code_base': [{
                    'question': r['question'], 'expected': r['expected'],
                    'response': r['response'], 'rouge_l': r['rouge_l'],
                    'tokens': r['tokens'], 'latency_ms': r.get('latency_ms', 0),
                    'judge': r['judge'],
                } for r in data['code_base']],
                'code_rag': [{
                    'question': r['question'], 'expected': r['expected'],
                    'response': r['response'], 'rouge_l': r['rouge_l'],
                    'tokens': r['tokens'], 'latency_ms': r.get('latency_ms', 0),
                    'judge': r['judge'],
                } for r in data['code_rag']],
            }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        with open(raw_path, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, indent=2, ensure_ascii=False)

        print(f'\nReport: {REPORT_PATH}')
        print(f'Stats:  {json_path}')
        print(f'Raw:    {raw_path}')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--tier', default='full', choices=['smoke', 'full'], help='Test tier (default: full)')
    args = p.parse_args()
    FinalEval(tier=args.tier).run()
