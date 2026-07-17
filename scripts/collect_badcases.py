"""
collect_badcases.py — 自动收集 Badcase
从 final_eval + error_bucket 结果中提取低分/错误样本，写入 JSON 供仪表板显示
用法: python collect_badcases.py
输出: data/badcases/auto_badcases.json
"""

import os, sys, json, glob
from datetime import datetime
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
BADCASES_DIR = os.path.join(PROJECT_ROOT, 'data', 'badcases')
OUTPUT_FILE = os.path.join(BADCASES_DIR, 'auto_badcases.json')

os.makedirs(BADCASES_DIR, exist_ok=True)

# Judge threshold: overall_score below this = badcase
JUDGE_THRESHOLD = 3.5
# Rouge threshold
ROUGE_THRESHOLD = 0.3


def load_final_eval():
    """Load latest eval results from rag_benchmark (has per-model raw data)"""
    # Try rag_benchmark first (multi-model, per-question)
    bench_files = sorted(glob.glob(os.path.join(PROJECT_ROOT, 'outputs', 'rag_benchmark', 'rag_benchmark_*.json')), reverse=True)
    if bench_files:
        with open(bench_files[0], 'r', encoding='utf-8') as f:
            data = json.load(f)
        items = []
        for model, subsets in data.get('results', {}).items():
            for subset_name, questions in subsets.items():
                for q in questions:
                    q['_model'] = model
                    q['_subset'] = subset_name
                    items.append(q)
        if items:
            return items

    # Fallback: rag_eval (single model)
    rag_files = sorted(glob.glob(os.path.join(PROJECT_ROOT, 'outputs', 'rag_eval', 'rag_eval_*.json')), reverse=True)
    if rag_files:
        with open(rag_files[0], 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'details' in data:
            return data['details']
    return []


def load_error_bucket():
    """Load latest error_bucket JSON for classification labels"""
    eb_files = sorted(glob.glob(os.path.join(PROJECT_ROOT, 'outputs', 'error_bucket', 'error_bucket_*.json')), reverse=True)
    if eb_files:
        with open(eb_files[0], 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def collect():
    raw = load_final_eval()
    eb = load_error_bucket()
    eb_details = {d.get('question', ''): d for d in eb.get('details', [])} if eb else {}

    badcases = []
    for item in raw:
        question = item.get('question', '')[:150]
        response = item.get('response', '')[:300]
        expected = item.get('expected', '')[:200]
        rouge = item.get('rouge_l', 0)
        judge = item.get('judge', {}) if isinstance(item.get('judge'), dict) else {}
        j_overall = judge.get('overall_score', 5)
        use_rag = item.get('use_rag', False)
        subset = item.get('subset', item.get('_subset', 'unknown'))

        # Collect if: Judge low OR Rouge very low
        is_bad = j_overall < JUDGE_THRESHOLD or rouge < ROUGE_THRESHOLD
        if not is_bad:
            continue

        # Get error bucket classification
        q_key = question[:100]
        eb_info = eb_details.get(q_key, {})
        bucket = eb_info.get('bucket', 'unknown')
        reason = eb_info.get('reason', '')

        # Map bucket to readable tags
        bucket_tags = {
            'math_error': ('推理错误', 'RAG不可解'),
            'logic_gap': ('推理错误', '部分可解'),
            'context_miss': ('推理错误', '部分可解'),
            'retrieval_fail': ('推理错误', 'RAG可解'),
            'format_violation': ('格式错误', '部分可解'),
            'hallucination': ('知识错误', 'RAG可解'),
            'prompt_misread': ('推理错误', '部分可解'),
            'knowledge_gap': ('知识错误', 'RAG可解'),
            'code_syntax': ('代码错误', '部分可解'),
            'code_logic': ('代码错误', '部分可解'),
            'security_unsafe': ('知识错误', 'RAG不可解'),
            'correct_but_low_score': ('推理错误', 'RAG不可解'),
        }
        tags = bucket_tags.get(bucket, ('推理错误', '部分可解'))

        badcases.append({
            'model': item.get('_model', 'unknown'),
            'subset': subset,
            'mode': 'RAG' if use_rag else 'Base',
            'question': question,
            'expected': expected,
            'response': response,
            'rouge_l': round(rouge, 4),
            'judge_overall': j_overall,
            'error_type': tags[0],
            'rag_fixable': tags[1],
            'bucket': bucket,
            'reason': reason,
        })

    # Dedup by question + model
    seen = set()
    unique = []
    for bc in badcases:
        key = (bc['question'][:80], bc['model'], bc['mode'])
        if key not in seen:
            seen.add(key)
            unique.append(bc)

    unique.sort(key=lambda x: x['judge_overall'])

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    # Summary
    model_count = Counter(bc['model'] for bc in unique)
    type_count = Counter(bc['error_type'] for bc in unique)

    print(f'Badcases collected: {len(unique)}')
    print(f'  By model:')
    for m, c in model_count.most_common():
        print(f'    {m}: {c}')
    print(f'  By type:')
    for t, c in type_count.most_common():
        print(f'    {t}: {c}')
    print(f'Saved: {OUTPUT_FILE}')


if __name__ == '__main__':
    collect()
