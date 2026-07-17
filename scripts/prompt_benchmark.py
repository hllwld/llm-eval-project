"""
prompt_benchmark.py — Prompt Benchmark (多 Prompt 变体对比评测)
比较: Accuracy | Cost (tokens) | Latency (ms) | Hallucination | ROUGE-L + Judge
输出: 自动推荐最优 Prompt

用法: python scripts/prompt_benchmark.py
配置: PROMPT_VARIANTS (本文件) + config/model_config.yaml + .env
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
sys.path.insert(0, BASE_DIR)
from llm_as_judge import LLMJudge

load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# ── Prompt 变体定义 ──
PROMPT_VARIANTS = {
    'A_baseline': {
        'name': 'A. 基线 (无约束)',
        'system': '你是AI助手，请直接回答问题。',
        'desc': '无任何输出格式要求',
    },
    'B_structured': {
        'name': 'B. 结构化 (分步)',
        'system': '请按以下格式回答：\n1. 分析：简要分析问题\n2. 过程：逐步推导或实现\n3. 答案：给出最终答案',
        'desc': '要求分步骤输出',
    },
    'C_concise': {
        'name': 'C. 简洁 (仅答案)',
        'system': '请直接给出答案。不要解释过程，不要多余的话。如果是代码题只输出代码，如果是计算题只输出算式和结果。',
        'desc': '强制最简输出',
    },
}

# ── 路径 ──
MCQ_DIR = os.path.join(PROJECT_ROOT, 'data', 'custom_testset', 'mcq')
QA_DIR = os.path.join(PROJECT_ROOT, 'data', 'custom_testset', 'qa')
REPORT_DIR = os.path.join(BASE_DIR, 'reports')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'outputs', 'prompt_benchmark')
os.makedirs(OUTPUT_DIR, exist_ok=True)


class PromptBenchmark:
    def __init__(self):
        self.models = self._load_models()
        self.judge = LLMJudge()
        self.scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
        self.mcq_qs = self._load_mcq()
        self.reasoning_qs = self._load_qa('reasoning.jsonl')
        self.code_qs = self._load_qa('code.jsonl')

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
                        items.append({
                            'question': item['query'].split('\n\n')[0].strip(),
                            'expected': item['response'],
                        })
        return items

    def _call(self, mc: Dict, messages: List[Dict]) -> tuple:
        """Returns (response_text, token_usage, latency_ms)"""
        base_url = mc['api_url'].rstrip('/').replace('/chat/completions', '')
        client = OpenAI(api_key=mc['api_key'], base_url=base_url)
        t0 = time.time()
        resp = client.chat.completions.create(
            model=mc['model'], messages=messages, temperature=0.3, max_tokens=1024, timeout=60
        )
        latency = (time.time() - t0) * 1000
        usage = resp.usage
        tokens = {
            'prompt': usage.prompt_tokens if usage else 0,
            'completion': usage.completion_tokens if usage else 0,
            'total': usage.total_tokens if usage else 0,
        }
        return resp.choices[0].message.content, tokens, latency

    def _eval_mcq(self, mc: Dict, prompt_key: str) -> Dict:
        """Run MCQ for one prompt variant, return accuracy + cost + latency"""
        pv = PROMPT_VARIANTS[prompt_key]
        correct = 0
        total_tokens = {'prompt': 0, 'completion': 0, 'total': 0}
        total_latency = 0

        for q in self.mcq_qs:
            opts_text = '\n'.join(f'{chr(65+j)}) {o}' for j, o in enumerate(q['options']))
            user_msg = f"单选题，选出正确答案，只输出字母。\n\n{q['question']}\n{opts_text}"
            messages = [
                {'role': 'system', 'content': pv['system']},
                {'role': 'user', 'content': user_msg},
            ]
            resp, tokens, lat = self._call(mc, messages)
            ans = ''.join(c for c in resp.strip().upper()[:5] if c in 'ABCDE') or '?'
            if ans and ans[0] == q['answer']:
                correct += 1
            for k in total_tokens:
                total_tokens[k] += tokens.get(k, 0)
            total_latency += lat
            time.sleep(0.2)

        n = len(self.mcq_qs)
        return {
            'accuracy': correct / n if n else 0,
            'correct': correct,
            'total': n,
            'avg_tokens': round(total_tokens['total'] / n, 1) if n else 0,
            'avg_latency_ms': round(total_latency / n, 1) if n else 0,
            'total_cost_tokens': total_tokens['total'],
        }

    def _eval_qa(self, mc: Dict, questions: List[Dict], prompt_key: str, subset: str) -> List[Dict]:
        """Run QA for one prompt variant, return per-question results"""
        pv = PROMPT_VARIANTS[prompt_key]
        results = []
        for q in questions:
            messages = [
                {'role': 'system', 'content': pv['system']},
                {'role': 'user', 'content': q['question']},
            ]
            resp, tokens, lat = self._call(mc, messages)
            rouge = self.scorer.score(q['expected'], resp)['rougeL'].fmeasure
            results.append({
                'question': q['question'],
                'expected': q['expected'],
                'response': resp,
                'rouge_l': round(rouge, 4),
                'tokens': tokens,
                'latency_ms': round(lat, 1),
            })
            time.sleep(0.3)

        # LLM Judge + hallucination check
        samples = [{'question': r['question'], 'expected': r['expected'], 'response': r['response']} for r in results]
        judged = self.judge.batch_judge(samples, subset=subset)
        for r, j in zip(results, judged):
            r['judge'] = j['judge_scores']
            # Hallucination heuristic: if correctness_score < 2, likely hallucinated
            r['hallucination'] = j['judge_scores'].get('correctness_score', 5) < 2
        return results

    def run(self):
        prompts = list(PROMPT_VARIANTS.keys())
        print(f'Prompt Variants: {len(prompts)} ({", ".join(prompts)})')
        print(f'Models: {list(self.models.keys())}')
        print(f'Testset: MCQ={len(self.mcq_qs)}  Reasoning={len(self.reasoning_qs)}  Code={len(self.code_qs)}')
        print(f'Total runs: {len(self.models)} x {len(prompts)} x ({len(self.mcq_qs)}+{len(self.reasoning_qs)}+{len(self.code_qs)})')

        all_results = {}
        for model_name, mc in self.models.items():
            all_results[model_name] = {}
            for pk in prompts:
                pv = PROMPT_VARIANTS[pk]
                print(f'\n{"="*60}')
                print(f'>> {model_name} | {pv["name"]}')
                print(f'{"="*60}')

                mcq_r = self._eval_mcq(mc, pk)
                reason_r = self._eval_qa(mc, self.reasoning_qs, pk, 'reasoning')
                code_r = self._eval_qa(mc, self.code_qs, pk, 'code')

                all_results[model_name][pk] = {
                    'mcq': mcq_r,
                    'reasoning': reason_r,
                    'code': code_r,
                }

        self._save_report(all_results, prompts)
        self._save_json(all_results, prompts)

    def _save_report(self, all_results: Dict, prompts: List[str]):
        """Generate auto-recommendation report"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        lines = [
            '# Prompt Benchmark Report',
            f'> {now} | {len(self.models)} models x {len(prompts)} prompts',
            '',
            '## Prompt 变体定义',
            '',
            '| ID | 名称 | System Prompt |',
            '| --- | --- | --- |',
        ]
        for pk in prompts:
            pv = PROMPT_VARIANTS[pk]
            sys_short = pv['system'].replace('\n', ' ')[:80]
            lines.append(f'| {pk} | {pv["name"]} | {sys_short}... |')

        # MCQ 对比
        lines += ['', '## 1. MCQ Accuracy 对比', '']
        header = '| Model | ' + ' | '.join(PROMPT_VARIANTS[pk]['name'] for pk in prompts) + ' |'
        lines.append(header)
        lines.append('| --- | ' + ' | '.join(['---'] * len(prompts)) + ' |')
        for model_name, data in all_results.items():
            row = f'| {model_name} | '
            row += ' | '.join(f'{data[pk]["mcq"]["accuracy"]:.0%}' for pk in prompts)
            row += ' |'
            lines.append(row)

        # Reasoning ROUGE 对比
        lines += ['', '## 2. Reasoning ROUGE-L + Judge 对比', '']
        lines.append('| Model | Prompt | ROUGE-L | Judge Overall | Hallucination Rate | Avg Latency | Avg Tokens |')
        lines.append('| --- | --- | --- | --- | --- | --- | --- |')
        for model_name, data in all_results.items():
            for pk in prompts:
                rows = data[pk]['reasoning']
                n = len(rows)
                rouge = sum(r['rouge_l'] for r in rows) / n if n else 0
                judge = sum(r['judge'].get('overall_score', 0) for r in rows) / n if n else 0
                hallu = sum(1 for r in rows if r.get('hallucination')) / n if n else 0
                lat = sum(r['latency_ms'] for r in rows) / n if n else 0
                tok = sum(r['tokens']['total'] for r in rows) / n if n else 0
                lines.append(f'| {model_name} | {PROMPT_VARIANTS[pk]["name"]} | {rouge:.2%} | {judge:.2f} | {hallu:.0%} | {lat:.0f}ms | {tok:.0f} |')

        # Code ROUGE 对比
        lines += ['', '## 3. Code ROUGE-L + Judge 对比', '']
        lines.append('| Model | Prompt | ROUGE-L | Judge Overall | Hallucination Rate | Avg Latency | Avg Tokens |')
        lines.append('| --- | --- | --- | --- | --- | --- | --- |')
        for model_name, data in all_results.items():
            for pk in prompts:
                rows = data[pk]['code']
                n = len(rows)
                rouge = sum(r['rouge_l'] for r in rows) / n if n else 0
                judge = sum(r['judge'].get('overall_score', 0) for r in rows) / n if n else 0
                hallu = sum(1 for r in rows if r.get('hallucination')) / n if n else 0
                lat = sum(r['latency_ms'] for r in rows) / n if n else 0
                tok = sum(r['tokens']['total'] for r in rows) / n if n else 0
                lines.append(f'| {model_name} | {PROMPT_VARIANTS[pk]["name"]} | {rouge:.2%} | {judge:.2f} | {hallu:.0%} | {lat:.0f}ms | {tok:.0f} |')

        # ── 自动推荐 ──
        lines += ['', '## 4. 自动推荐', '']
        recommendations = self._auto_recommend(all_results, prompts)
        lines.append('### 综合评分排名')
        lines.append('')
        lines.append('| 排名 | Prompt | 综合分 | Accuracy | ROUGE-L | Judge | Latency | Cost | Hallu |')
        lines.append('| --- | --- | --- | --- | --- | --- | --- | --- | --- |')
        for rank, rec in enumerate(recommendations, 1):
            lines.append(
                f'| {rank} | **{rec["prompt_name"]}** | {rec["score"]:.3f} | '
                f'{rec["accuracy"]:.0%} | {rec["rouge"]:.2%} | {rec["judge"]:.2f} | '
                f'{rec["latency_ms"]:.0f}ms | {rec["tokens"]:.0f} | {rec["hallu_rate"]:.0%} |'
            )

        best = recommendations[0]
        lines += [
            '',
            f'### 🏆 推荐：{best["prompt_name"]}',
            '',
            f'- **综合得分**: {best["score"]:.3f} (最高)',
            f'- **Accuracy**: {best["accuracy"]:.0%}',
            f'- **ROUGE-L**: {best["rouge"]:.2%}',
            f'- **LLM Judge**: {best["judge"]:.2f}/5',
            f'- **Hallucination**: {best["hallu_rate"]:.0%}',
            f'- **平均延迟**: {best["latency_ms"]:.0f}ms',
            f'- **平均 Tokens**: {best["tokens"]:.0f}',
            '',
            '### 评分公式',
            '',
            '`Score = Accuracy×0.20 + ROUGE×0.15 + Judge/5×0.30 + (1-Hallu)×0.20 + Latency_norm×0.05 + Token_norm×0.10`',
            '',
            '- Accuracy、ROUGE、Judge 越高越好',
            '- Hallucination、Latency、Tokens 越低越好（取反后归一化）',
        ]

        report_path = os.path.join(REPORT_DIR, 'prompt_benchmark_report.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f'\nReport: {report_path}')

    def _auto_recommend(self, all_results: Dict, prompts: List[str]) -> List[Dict]:
        """Score each prompt across all models, return ranked list"""
        scores = []
        # Aggregate across models per prompt
        for pk in prompts:
            mcq_accs = [data[pk]['mcq']['accuracy'] for data in all_results.values()]
            avg_acc = sum(mcq_accs) / len(mcq_accs)

            reason_rows = [r for data in all_results.values() for r in data[pk]['reasoning']]
            code_rows = [r for data in all_results.values() for r in data[pk]['code']]
            all_rows = reason_rows + code_rows

            n = len(all_rows)
            avg_rouge = sum(r['rouge_l'] for r in all_rows) / n if n else 0
            avg_judge = sum(r['judge'].get('overall_score', 0) for r in all_rows) / n if n else 0
            avg_hallu = sum(1 for r in all_rows if r.get('hallucination')) / n if n else 0
            avg_lat = sum(r['latency_ms'] for r in all_rows) / n if n else 0
            avg_tok = sum(r['tokens']['total'] for r in all_rows) / n if n else 0

            # Normalize latency and tokens (lower is better, invert)
            scores.append({
                'prompt_key': pk,
                'prompt_name': PROMPT_VARIANTS[pk]['name'],
                'accuracy': avg_acc,
                'rouge': avg_rouge,
                'judge': avg_judge,
                'hallu_rate': avg_hallu,
                'latency_ms': avg_lat,
                'tokens': avg_tok,
            })

        # Min-max normalize latency and tokens for scoring
        lats = [s['latency_ms'] for s in scores]
        toks = [s['tokens'] for s in scores]
        lat_min, lat_max = min(lats), max(lats)
        tok_min, tok_max = min(toks), max(toks)

        def norm(v, lo, hi):
            return (hi - v) / (hi - lo) if hi > lo else 0.5

        for s in scores:
            s['score'] = (
                s['accuracy'] * 0.20 +
                s['rouge'] * 0.15 +
                (s['judge'] / 5) * 0.30 +
                (1 - s['hallu_rate']) * 0.20 +
                norm(s['latency_ms'], lat_min, lat_max) * 0.05 +
                norm(s['tokens'], tok_min, tok_max) * 0.10
            )

        scores.sort(key=lambda x: x['score'], reverse=True)
        return scores

    def _save_json(self, all_results: Dict, prompts: List[str]):
        now = datetime.now().strftime('%Y%m%d_%H%M')
        # Simplify for JSON
        json_data = {
            'timestamp': now,
            'models': list(self.models.keys()),
            'prompts': {pk: PROMPT_VARIANTS[pk]['name'] for pk in prompts},
            'results': {},
        }
        for model_name, data in all_results.items():
            json_data['results'][model_name] = {}
            for pk in prompts:
                rows = data[pk]
                reason_n = len(rows['reasoning'])
                code_n = len(rows['code'])
                all_qa = rows['reasoning'] + rows['code']
                n = len(all_qa)
                json_data['results'][model_name][pk] = {
                    'mcq_accuracy': rows['mcq']['accuracy'],
                    'avg_rouge': sum(r['rouge_l'] for r in all_qa) / n if n else 0,
                    'avg_judge': sum(r['judge'].get('overall_score', 0) for r in all_qa) / n if n else 0,
                    'hallu_rate': sum(1 for r in all_qa if r.get('hallucination')) / n if n else 0,
                    'avg_latency_ms': sum(r['latency_ms'] for r in all_qa) / n if n else 0,
                    'avg_tokens': sum(r['tokens']['total'] for r in all_qa) / n if n else 0,
                }

        json_path = os.path.join(OUTPUT_DIR, f'prompt_benchmark_{now}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f'JSON:   {json_path}')


if __name__ == '__main__':
    PromptBenchmark().run()
