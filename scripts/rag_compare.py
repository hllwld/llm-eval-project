"""
rag_compare.py — Base vs RAG 三模型对比分析
Base: v3 benchmark (full_benchmark.py 产出)
RAG: rag_benchmark.py 产出
"""

import os
import sys
import json
import glob
from collections import defaultdict
from rouge_score import rouge_scorer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
REPORT_PATH = os.path.join(BASE_DIR, 'reports', 'rag_compare_report.md')

# Base scores from v3 benchmark (full_benchmark.py)
BASE_SCORES = {
    'DeepSeek-V3': {'reasoning': 0.4968, 'code': 0.5525},
    'Qwen-Plus':   {'reasoning': 0.3143, 'code': 0.5758},
    'GLM-4-Plus':  {'reasoning': 0.3500, 'code': 0.5313},
}


def load_rag_results():
    """Load latest RAG benchmark results"""
    pattern = os.path.join(PROJECT_ROOT, 'outputs', 'rag_benchmark', 'rag_benchmark_*.json')
    files = sorted(glob.glob(pattern), reverse=True)
    if not files:
        print('[ERROR] No RAG benchmark results found. Run rag_benchmark.py first.')
        return None
    with open(files[0], 'r', encoding='utf-8') as f:
        return json.load(f)


def compute_rouge(prediction: str, reference: str) -> float:
    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    return scorer.score(reference, prediction)['rougeL'].fmeasure


def compare():
    rag_data = load_rag_results()
    if not rag_data:
        return

    rag_results = rag_data.get('results', {})
    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)

    # Compute RAG scores per model per subset
    rag_scores = {}
    for model_name, subsets in rag_results.items():
        rag_scores[model_name] = {}
        for subset, items in subsets.items():
            scores = [compute_rouge(r['response'], r['expected']) for r in items]
            rag_scores[model_name][subset] = sum(scores) / len(scores) if scores else 0

    print('=' * 70)
    print('Base vs RAG — Three-Model Comparison')
    print('=' * 70)

    # ── Reasoning ──
    print(f'\n{"Reasoning (15 questions)":-^70}')
    print(f'{"Model":<18} {"Base":>10} {"RAG":>10} {"Delta":>10} {"Verdict":>12}')
    print(f'{"-"*60}')
    for model in ['DeepSeek-V3', 'Qwen-Plus', 'GLM-4-Plus']:
        base = BASE_SCORES[model]['reasoning']
        rag = rag_scores.get(model, {}).get('reasoning', 0)
        delta = rag - base
        if delta > 0.02:
            verdict = 'IMPROVED'
        elif delta < -0.02:
            verdict = 'DROPPED'
        else:
            verdict = 'FLAT'
        print(f'{model:<18} {base:>9.2%} {rag:>9.2%} {delta:>+9.2%} {verdict:>12}')

    # ── Code ──
    print(f'\n{"Code (10 questions)":-^70}')
    print(f'{"Model":<18} {"Base":>10} {"RAG":>10} {"Delta":>10} {"Verdict":>12}')
    print(f'{"-"*60}')
    for model in ['DeepSeek-V3', 'Qwen-Plus', 'GLM-4-Plus']:
        base = BASE_SCORES[model]['code']
        rag = rag_scores.get(model, {}).get('code', 0)
        delta = rag - base
        if delta > 0.02:
            verdict = 'IMPROVED'
        elif delta < -0.02:
            verdict = 'DROPPED'
        else:
            verdict = 'FLAT'
        print(f'{model:<18} {base:>9.2%} {rag:>9.2%} {delta:>+9.2%} {verdict:>12}')

    # ── Save report ──
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write('# Base vs RAG 三模型对比报告\n\n')
        f.write(f'> 数据: v3 benchmark + rag_benchmark\n\n')

        f.write('## Reasoning (15 questions)\n\n')
        f.write('| Model | Base | RAG | Delta | Verdict |\n')
        f.write('| --- | --- | --- | --- | --- |\n')
        for model in ['DeepSeek-V3', 'Qwen-Plus', 'GLM-4-Plus']:
            base = BASE_SCORES[model]['reasoning']
            rag = rag_scores.get(model, {}).get('reasoning', 0)
            d = rag - base
            v = 'IMPROVED' if d > 0.02 else ('DROPPED' if d < -0.02 else 'FLAT')
            f.write(f'| {model} | {base:.2%} | {rag:.2%} | {d:+.2%} | {v} |\n')

        f.write('\n## Code (10 questions)\n\n')
        f.write('| Model | Base | RAG | Delta | Verdict |\n')
        f.write('| --- | --- | --- | --- | --- |\n')
        for model in ['DeepSeek-V3', 'Qwen-Plus', 'GLM-4-Plus']:
            base = BASE_SCORES[model]['code']
            rag = rag_scores.get(model, {}).get('code', 0)
            d = rag - base
            v = 'IMPROVED' if d > 0.02 else ('DROPPED' if d < -0.02 else 'FLAT')
            f.write(f'| {model} | {base:.2%} | {rag:.2%} | {d:+.2%} | {v} |\n')

        f.write('\n## Conclusion\n\n')
        f.write('- Code subset: RAG has minimal impact (KB contains reasoning steps only)\n')
        f.write('- Reasoning subset: RAG effect varies by model. Check per-model delta.\n')
        f.write('- Note: ROUGE-L penalizes longer structured output. Improvement in format/step quality may not be reflected in ROUGE-L scores.\n')

    print(f'\nReport: {REPORT_PATH}')


if __name__ == '__main__':
    compare()
