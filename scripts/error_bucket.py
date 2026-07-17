"""
error_bucket.py — Error Bucket 错误分类分析
用 LLM 自动将错误答案归入细粒度分类桶，按模型/子集/维度统计占比。

用法: python error_bucket.py [--from-json outputs/final_eval/xxx.json]
输出: scripts/reports/error_bucket_report.md
"""

import os
import sys
import json
import glob
from datetime import datetime
from typing import List, Dict, Optional
from collections import Counter, defaultdict
from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'outputs', 'error_bucket')
REPORT_DIR = os.path.join(BASE_DIR, 'reports')
os.makedirs(OUTPUT_DIR, exist_ok=True)

load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# ── Error Bucket 分类体系 ──
ERROR_BUCKETS = {
    'math_error':        {'name': '数学计算错误', 'desc': '推理方向正确但计算过程出错', 'fix': 'CoT校验 / 计算器工具'},
    'logic_gap':         {'name': '逻辑链断裂',   'desc': '步骤不完整或跳跃，缺少关键推导', 'fix': 'CoT + 分步校验'},
    'context_miss':      {'name': '上下文遗漏',   'desc': '题目中的关键信息未被使用', 'fix': '改进 Prompt 强调信息提取'},
    'retrieval_fail':    {'name': '检索失败',     'desc': 'RAG 未召回正确知识或召回了无关内容', 'fix': '优化知识库 / 检索策略'},
    'format_violation':  {'name': '格式违规',     'desc': '输出格式不符合要求（非JSON/缺少字段）', 'fix': '强化 Prompt 格式约束'},
    'hallucination':     {'name': '幻觉/捏造',    'desc': '编造不存在的事实、API、函数', 'fix': 'RAG 事实核查 / 知识库补充'},
    'prompt_misread':    {'name': 'Prompt理解偏差','desc': '误解了题目意图或要求', 'fix': '改写 Prompt 更明确'},
    'knowledge_gap':     {'name': '知识盲区',     'desc': '模型缺少相关知识，确实不知道', 'fix': 'RAG / 知识库扩充'},
    'code_syntax':       {'name': '代码语法错误',  'desc': '代码有语法问题无法运行', 'fix': '增加代码校验步骤'},
    'code_logic':        {'name': '代码逻辑错误',  'desc': '代码能运行但结果不符合预期', 'fix': '增加测试用例验证'},
    'security_unsafe':   {'name': '安全未拒答',   'desc': '应拒答但接受了诱导', 'fix': '安全策略加固 / RLHF'},
    'correct_but_low_score': {'name': '答案正确但评分低','desc': '模型答案正确但 Rouge/Judge 因格式/长度误判', 'fix': '改进评分指标'},
}

BUCKET_IDS = list(ERROR_BUCKETS.keys())

CLASSIFY_PROMPT = """你是一个错误分析专家。分析以下模型输出的错误原因，归入最匹配的错误桶。

## 可选错误桶:
"""
for bid in BUCKET_IDS:
    b = ERROR_BUCKETS[bid]
    CLASSIFY_PROMPT += f"- **{bid}** ({b['name']}): {b['desc']}\n"

CLASSIFY_PROMPT += """
## 输入:
- 题目: {question}
- 参考答案: {expected}
- 模型输出: {response}
- 子集类型: {subset}
- Judge评分: {judge_score}

## 要求:
严格只输出一行合法 JSON，不要```json```代码块，不要任何解释文字，不要换行。
JSON 格式必须为:
{"bucket":"<错误桶ID>","confidence":<0-1>,"reason":"<一句话中文原因>","severity":"<low|medium|high>"}"""


def load_raw_data(json_path: Optional[str] = None) -> List[Dict]:
    """Load per-question data from available sources"""
    samples = []

    if json_path and os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Handle different JSON structures
        if 'details' in data:
            samples = data['details']
        elif 'results' in data:
            if isinstance(data['results'], list):
                samples = data['results']
            else:
                for model_results in data['results'].values():
                    if isinstance(model_results, list):
                        samples.extend(model_results)
        return samples

    # Auto-discover: rag_eval JSON first (has per-question data)
    rag_files = sorted(glob.glob(os.path.join(PROJECT_ROOT, 'outputs', 'rag_eval', 'rag_eval_*.json')), reverse=True)
    if rag_files:
        with open(rag_files[0], 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'details' in data:
            return data['details']

    # Fallback: rag_benchmark
    bench_files = sorted(glob.glob(os.path.join(PROJECT_ROOT, 'outputs', 'rag_benchmark', 'rag_benchmark_*.json')), reverse=True)
    if bench_files:
        with open(bench_files[0], 'r', encoding='utf-8') as f:
            data = json.load(f)
        all_samples = []
        for model, subsets in data.get('results', {}).items():
            for subset_name, items in subsets.items():
                for item in items:
                    item['_model'] = model
                    item['_subset'] = subset_name
                    all_samples.append(item)
        return all_samples

    return []


def classify_errors(samples: List[Dict], judge_model: str = 'deepseek-v4-flash') -> List[Dict]:
    """Use LLM to classify errors into buckets"""
    api_key = os.getenv('DEEPSEEK_API_KEY', '')
    if not api_key:
        print('[WARN] No DEEPSEEK_API_KEY, using heuristic classification')
        return _heuristic_classify(samples)

    client = OpenAI(api_key=api_key, base_url='https://api.deepseek.com')
    results = []
    n = len(samples)

    for i, s in enumerate(samples):
        question = s.get('question', '')[:500]
        expected = s.get('expected', '')[:500]
        response = s.get('response', '')[:1000]
        subset = s.get('subset', s.get('_subset', 'unknown'))
        judge = s.get('judge', {})
        if isinstance(judge, dict):
            j_score = f"format={judge.get('format_score','?')} correct={judge.get('correctness_score','?')} overall={judge.get('overall_score','?')}"
        else:
            j_score = str(judge)
        rouge = s.get('rouge_l', 0)

        # Skip obviously correct answers
        if isinstance(judge, dict) and judge.get('overall_score', 0) >= 4.5 and rouge > 0.5:
            results.append({'bucket': 'correct_but_low_score', 'confidence': 0.9,
                          'reason': '答案基本正确', 'severity': 'low',
                          'question': question[:100], 'rouge_l': rouge})
            if (i+1) % 10 == 0:
                print(f'  {i+1}/{n}...')
            continue

        prompt = CLASSIFY_PROMPT.format(
            question=question, expected=expected, response=response,
            subset=subset, judge_score=j_score
        )

        result = None
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=judge_model,
                    messages=[{'role': 'user', 'content': prompt}],
                    temperature=0.1, max_tokens=300, timeout=30,
                )
                raw = resp.choices[0].message.content.strip()
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
                    import time as _time
                    _time.sleep(0.5)
                continue

        if result and isinstance(result, dict):
            result['question'] = question[:100]
            result['rouge_l'] = rouge
            results.append(result)
        else:
            # Heuristic fallback based on subset
            if 'code_' in subset.lower():
                fallback_bucket = 'code_logic'
                fallback_reason = '代码类低分(分类失败，按子集推断)'
            elif any(kw in str(judge).lower() for kw in ['security', 'jailbreak']):
                fallback_bucket = 'security_unsafe'
                fallback_reason = '安全类低分(分类失败，按内容推断)'
            else:
                fallback_bucket = 'logic_gap'
                fallback_reason = '低分(LLM分类失败，按子集推断)'
            results.append({'bucket': fallback_bucket, 'confidence': 0.3, 'reason': fallback_reason,
                          'severity': 'medium', 'question': question[:100], 'rouge_l': rouge})

        if (i+1) % 10 == 0:
            print(f'  {i+1}/{n}...')

    return results


def _heuristic_classify(samples: List[Dict]) -> List[Dict]:
    """Fallback: rule-based classification"""
    results = []
    for s in samples:
        response = s.get('response', '')
        rouge = s.get('rouge_l', 0)
        judge = s.get('judge', {})
        j_overall = judge.get('overall_score', 5) if isinstance(judge, dict) else 5

        if j_overall >= 4.5:
            bucket = 'correct_but_low_score'
            reason = 'Judge高分但Rouge低'
        elif rouge < 0.1:
            bucket = 'format_violation' if '{' in s.get('expected', '') else 'hallucination'
            reason = 'Rouge极低'
        elif j_overall < 2:
            bucket = 'knowledge_gap'
            reason = 'Judge低分'
        elif '错误' in response or 'error' in response.lower():
            bucket = 'code_syntax'
            reason = '输出含错误提示'
        else:
            bucket = 'logic_gap'
            reason = '答案不匹配'

        results.append({
            'bucket': bucket, 'confidence': 0.5, 'reason': reason,
            'severity': 'medium', 'question': s.get('question', '')[:100], 'rouge_l': rouge,
        })
    return results


def run(from_json: Optional[str] = None):
    samples = load_raw_data(from_json)
    if not samples:
        print('[ERROR] No data found. Run final_eval.py or rag_eval.py first.')
        sys.exit(1)

    print(f'Classifying {len(samples)} samples into error buckets...')
    classified = classify_errors(samples)

    # ── Aggregate ──
    bucket_counter = Counter(r['bucket'] for r in classified)
    total = len(classified)

    # By severity
    sev_counter = Counter(r.get('severity', 'medium') for r in classified)

    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    # ── Report ──
    lines = [
        '# Error Bucket 分析报告',
        f'> {now} | {total} samples analyzed | {len(ERROR_BUCKETS)} buckets',
        '',
        '## Error Bucket 分类体系',
        '',
        '| ID | 名称 | 描述 | 修复方向 |',
        '| --- | --- | --- | --- |',
    ]
    for bid in BUCKET_IDS:
        b = ERROR_BUCKETS[bid]
        lines.append(f'| `{bid}` | {b["name"]} | {b["desc"]} | {b["fix"]} |')

    lines += [
        '',
        '## 错误分布',
        '',
        '| 错误类型 | 数量 | 占比 | 严重程度 | 修复方向 |',
        '| --- | --- | --- | --- | --- |',
    ]

    # Sort by count descending
    sorted_buckets = sorted(bucket_counter.items(), key=lambda x: x[1], reverse=True)
    for bid, count in sorted_buckets:
        pct = count / total * 100 if total else 0
        b = ERROR_BUCKETS.get(bid, {'name': bid, 'fix': '-'})
        # Count severity for this bucket
        sev_in_bucket = Counter(r.get('severity', 'medium') for r in classified if r['bucket'] == bid)
        sev_str = f"高:{sev_in_bucket.get('high',0)} 中:{sev_in_bucket.get('medium',0)} 低:{sev_in_bucket.get('low',0)}"
        lines.append(f'| **{b["name"]}** | {count} | {pct:.1f}% | {sev_str} | {b["fix"]} |')

    # ── Visual bar chart (ASCII) ──
    max_count = sorted_buckets[0][1] if sorted_buckets else 1
    lines += [
        '',
        '## 可视化分布',
        '',
        '```',
    ]
    for bid, count in sorted_buckets:
        pct = count / total * 100 if total else 0
        bar = '█' * max(1, int(count / max_count * 40))
        b = ERROR_BUCKETS.get(bid, {'name': bid})
        lines.append(f'  {b["name"]:<12} {bar} {count} ({pct:.1f}%)')
    lines.append('```')

    # ── Key findings ──
    lines += [
        '',
        '## 关键发现',
        '',
    ]
    if bucket_counter.get('correct_but_low_score', 0) > total * 0.3:
        lines.append(f'- ⚠️ **{ERROR_BUCKETS["correct_but_low_score"]["name"]}** 占比最高（{bucket_counter["correct_but_low_score"]/total*100:.0f}%），评测指标的误判问题仍然严重')
    if bucket_counter.get('hallucination', 0) > 0:
        lines.append(f'- 🔴 **幻觉** ({bucket_counter.get("hallucination",0)}条): 需加强 RAG 事实核查')
    if bucket_counter.get('format_violation', 0) > 0:
        lines.append(f'- 🟡 **格式违规** ({bucket_counter.get("format_violation",0)}条): Prompt 格式约束需强化')
    if bucket_counter.get('math_error', 0) > 0:
        lines.append(f'- 🟠 **计算错误** ({bucket_counter.get("math_error",0)}条): 建议引入计算器工具')

    # ── Top actionable items ──
    lines += [
        '',
        '## 改进优先级',
        '',
        '| 优先级 | 措施 | 影响范围 |',
        '| --- | --- | --- |',
    ]

    # Auto-generate priorities based on bucket counts
    priorities = []
    for bid, count in sorted_buckets[:5]:
        b = ERROR_BUCKETS.get(bid, {'name': bid, 'fix': '-'})
        pct = count / total * 100 if total else 0
        if pct > 20:
            pri = 'P0'
        elif pct > 10:
            pri = 'P1'
        else:
            pri = 'P2'
        priorities.append((pri, b['fix'], f'{pct:.0f}% ({count}条)'))

    for pri, fix, impact in sorted(priorities):
        lines.append(f'| **{pri}** | {fix} | {impact} |')

    # ── Per-sample detail ──
    lines += [
        '',
        '## 逐条分类明细',
        '',
        '| # | Bucket | 置信度 | 严重度 | 原因 | 题目 |',
        '| --- | --- | --- | --- | --- | --- |',
    ]
    for i, r in enumerate(classified, 1):
        bid = r['bucket']
        bname = ERROR_BUCKETS.get(bid, {}).get('name', bid)
        lines.append(f'| {i} | {bname} | {r["confidence"]:.0%} | {r.get("severity","?")} | {r["reason"]} | {r.get("question","")[:60]} |')

    report_path = os.path.join(REPORT_DIR, 'error_bucket_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    json_path = os.path.join(OUTPUT_DIR, f'error_bucket_{datetime.now().strftime("%Y%m%d")}.json')
    json_data = {
        'timestamp': now,
        'total': total,
        'distribution': {ERROR_BUCKETS.get(bid, {}).get('name', bid): count for bid, count in sorted_buckets},
        'severity': dict(sev_counter),
        'details': [{'bucket': r['bucket'], 'confidence': r['confidence'], 'reason': r['reason'],
                      'severity': r.get('severity'), 'question': r.get('question', '')} for r in classified],
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    print(f'\nReport: {report_path}')
    print(f'JSON:   {json_path}')

    # ── Summary ──
    print(f'\nTop Error Buckets:')
    for bid, count in sorted_buckets[:5]:
        pct = count / total * 100
        b = ERROR_BUCKETS.get(bid, {'name': bid, 'fix': '-'})
        print(f'  {b["name"]:<12} {count:>3} ({pct:5.1f}%)')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--from-json', help='Path to eval JSON (auto-detect if omitted)')
    args = p.parse_args()
    run(from_json=args.from_json)
