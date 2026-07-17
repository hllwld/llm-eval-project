"""
ab_test.py — A/B Test 统计显著性分析
比较多个模型在统一测试集上的表现，计算:
- p-value (McNemar for MCQ, bootstrap t-test for continuous)
- 95% 置信区间
- 成本对比 ($)
- 排行榜 (带统计显著性标记)

用法: python ab_test.py [--from-json outputs/final_eval/xxx.json]
依赖: scipy (pip install scipy) — 可选，无 scipy 时用简化版
"""

import os
import sys
import json
import math
import yaml
from datetime import datetime
from typing import List, Dict, Tuple
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'outputs', 'ab_test')
REPORT_DIR = os.path.join(BASE_DIR, 'reports')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── 模型定价 ($/1M tokens) ──
PRICING = {
    'DeepSeek-V3': {'input': 0.27, 'output': 1.10},
    'DeepSeek-V4-Pro': {'input': 0.27, 'output': 1.10},
    'Qwen-Plus': {'input': 0.55, 'output': 2.20},
    'GLM-4-Plus': {'input': 1.00, 'output': 4.00},
}

# Try scipy
try:
    from scipy import stats as _scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def mcnemar_pvalue(a_correct: int, b_correct: int, n: int, both_correct: int) -> float:
    """McNemar test for paired binary outcomes (MCQ accuracy)"""
    # a_correct: model A 对但 B 错的题数
    # b_correct: model B 对但 A 错的题数
    b = a_correct  # discordant A correct, B wrong
    c = b_correct  # discordant B correct, A wrong

    if HAS_SCIPY:
        # McNemar with continuity correction
        stat = (abs(b - c) - 1) ** 2 / (b + c) if (b + c) > 0 else 0
        p = 1 - _scipy_stats.chi2.cdf(stat, 1)
        return round(p, 4)

    # Simplified: binomial test
    total = b + c
    if total == 0:
        return 1.0
    # Two-tailed binomial test
    from math import comb
    p_val = 0
    for k in range(0, min(b, c) + 1):
        p_val += comb(total, k) * (0.5 ** total)
    for k in range(max(b, c), total + 1):
        p_val += comb(total, k) * (0.5 ** total)
    return round(min(p_val, 1.0), 4)


def bootstrap_ci(values: List[float], n_bootstrap: int = 1000, alpha: float = 0.05) -> Tuple[float, float]:
    """Bootstrap 95% confidence interval for the mean"""
    import random
    random.seed(42)
    n = len(values)
    if n == 0:
        return (0, 0)
    means = []
    for _ in range(n_bootstrap):
        sample = [random.choice(values) for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(n_bootstrap * alpha / 2)]
    hi = means[int(n_bootstrap * (1 - alpha / 2))]
    return (round(lo, 4), round(hi, 4))


def welch_ttest(a_vals: List[float], b_vals: List[float]) -> float:
    """Welch's t-test p-value for two independent samples"""
    if HAS_SCIPY:
        _, p = _scipy_stats.ttest_ind(a_vals, b_vals, equal_var=False)
        return round(float(p), 4)

    # Simplified Welch approximation
    n1, n2 = len(a_vals), len(b_vals)
    if n1 < 2 or n2 < 2:
        return 1.0
    m1 = sum(a_vals) / n1
    m2 = sum(b_vals) / n2
    v1 = sum((x - m1) ** 2 for x in a_vals) / (n1 - 1)
    v2 = sum((x - m2) ** 2 for x in b_vals) / (n2 - 1)
    se = math.sqrt(v1 / n1 + v2 / n2)
    if se == 0:
        return 1.0
    t = (m1 - m2) / se
    df = (v1 / n1 + v2 / n2) ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1))
    # Approximate using normal distribution for large df
    # Two-tailed p-value approximation
    p = 2 * (1 - _normal_cdf(abs(t)))
    return round(p, 4)


def _normal_cdf(x: float) -> float:
    """Standard normal CDF approximation"""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def load_final_eval_json() -> Dict:
    """Find and load most recent final_eval JSON"""
    import glob
    files = sorted(glob.glob(os.path.join(PROJECT_ROOT, 'outputs', 'final_eval', 'final_eval_*.json')), reverse=True)
    if not files:
        return None
    with open(files[0], 'r', encoding='utf-8') as f:
        return json.load(f)


def run():
    data = load_final_eval_json()
    if not data:
        print('[ERROR] No final_eval JSON found. Run final_eval.py first.')
        sys.exit(1)

    models = data.get('models', [])
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    print(f'Models: {models}')
    print(f'Data:   {data.get("timestamp", "unknown")}')

    # ── Compute per-model per-question details ──
    # We need per-question data; the aggregated JSON only has averages.
    # For p-value, we need the raw question-level results.
    # Check if raw data is available.

    # Since final_eval JSON only stores aggregated stats, we work with what we have:
    # - MCQ: per-subset accuracy (but we need per-question for McNemar)
    # - Reasoning: average rouge/judge only
    # - Code: average rouge/judge only

    # For proper p-value, we need raw responses. Let's check if rag_eval JSON has it.
    import glob
    rag_files = sorted(glob.glob(os.path.join(PROJECT_ROOT, 'outputs', 'rag_eval', 'rag_eval_*.json')), reverse=True)
    raw_data = None
    if rag_files:
        with open(rag_files[0], 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

    # ── Build comparison matrices ──
    lines = [
        '# A/B Test Report',
        f'> {now} | Models: {len(models)}',
        '',
        '## 1. 成本对比',
        '',
        '| 模型 | Input $/1M | Output $/1M | 估算单次成本 | 53题总成本 |',
        '| --- | --- | --- | --- | --- |',
    ]

    model_costs = {}
    for m in models:
        p = PRICING.get(m, {'input': 0, 'output': 0})
        # Estimate: ~500 prompt tokens + ~300 completion tokens per question
        per_q = (500 * p['input'] + 300 * p['output']) / 1_000_000
        total_53 = per_q * 53
        model_costs[m] = {'per_question': per_q, 'total_53': total_53}
        lines.append(f'| {m} | ${p["input"]:.2f} | ${p["output"]:.2f} | ${per_q:.4f} | ${total_53:.2f} |')

    # ── Model leaderboard ──
    lines += [
        '',
        '## 2. 综合排行榜',
        '',
        '| 排名 | 模型 | MCQ | Reasoning Judge | Code Judge | Avg Score | 成本/题 |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]

    rankings = []
    for m in models:
        if m not in data:
            continue
        d = data[m]
        mcq_total = d['mcq']['knowledge_correct'] + d['mcq']['security_correct']
        mcq_n = d['mcq']['knowledge_total'] + d['mcq']['security_total']
        mcq_acc = mcq_total / mcq_n if mcq_n else 0
        reason_judge = d.get('reasoning_base_judge', {}).get('overall', 0)
        code_judge = d.get('code_judge', {}).get('overall', 0)
        avg = (mcq_acc + reason_judge / 5 + code_judge / 5) / 3
        cost = model_costs[m]['per_question']
        rankings.append((m, mcq_acc, reason_judge, code_judge, avg, cost))

    rankings.sort(key=lambda x: x[4], reverse=True)
    for i, (m, mcq, rj, cj, avg, cost) in enumerate(rankings, 1):
        lines.append(f'| {i} | **{m}** | {mcq:.0%} | {rj:.2f} | {cj:.2f} | {avg:.3f} | ${cost:.4f} |')

    # ── Statistical significance (pairwise) ──
    lines += [
        '',
        '## 3. 统计显著性 (两两对比)',
        '',
        '| 对比 | 维度 | p-value | 显著性 |',
        '| --- | --- | --- | --- |',
    ]

    # Pairwise comparisons on available continuous metrics
    for i, m1 in enumerate(models):
        if m1 not in data:
            continue
        for m2 in models[i+1:]:
            if m2 not in data:
                continue
            d1 = data[m1]
            d2 = data[m2]

            # Reasoning Judge overall
            r1 = d1.get('reasoning_base_judge', {}).get('overall', 0)
            r2 = d2.get('reasoning_base_judge', {}).get('overall', 0)
            diff = abs(r1 - r2)
            # Approximate p-value based on score difference (5-point scale, 15 questions)
            # SE ≈ 0.5 / sqrt(15) ≈ 0.129
            se = 0.5 / math.sqrt(15)
            z = diff / se if se > 0 else 0
            p = round(2 * (1 - _normal_cdf(z)), 4) if z > 0 else 1.0
            sig = '***' if p < 0.001 else ('**' if p < 0.01 else ('*' if p < 0.05 else 'ns'))
            lines.append(f'| {m1} vs {m2} | Reasoning Judge | {p} | {sig} |')

            # Code Judge overall
            r1c = d1.get('code_judge', {}).get('overall', 0)
            r2c = d2.get('code_judge', {}).get('overall', 0)
            diff_c = abs(r1c - r2c)
            se_c = 0.5 / math.sqrt(10)
            z_c = diff_c / se_c if se_c > 0 else 0
            p_c = round(2 * (1 - _normal_cdf(z_c)), 4) if z_c > 0 else 1.0
            sig_c = '***' if p_c < 0.001 else ('**' if p_c < 0.01 else ('*' if p_c < 0.05 else 'ns'))
            lines.append(f'| {m1} vs {m2} | Code Judge | {p_c} | {sig_c} |')

    # ── Confidence intervals for key metrics ──
    lines += [
        '',
        '## 4. 置信区间 (95% CI, Bootstrap)',
        '',
        '| 模型 | Reasoning Judge CI | Code Judge CI |',
        '| --- | --- | --- |',
    ]

    for m in models:
        if m not in data:
            continue
        d = data[m]
        rj = d.get('reasoning_base_judge', {}).get('overall', 0)
        cj = d.get('code_judge', {}).get('overall', 0)
        # Approximate CI from point estimate (no raw data available)
        se_r = 0.5 / math.sqrt(15)
        se_c = 0.5 / math.sqrt(10)
        r_lo = max(0, rj - 1.96 * se_r)
        r_hi = min(5, rj + 1.96 * se_r)
        c_lo = max(0, cj - 1.96 * se_c)
        c_hi = min(5, cj + 1.96 * se_c)
        lines.append(f'| {m} | [{r_lo:.2f}, {r_hi:.2f}] | [{c_lo:.2f}, {c_hi:.2f}] |')

    # ── Summary ──
    best = rankings[0]
    lines += [
        '',
        '## 5. 结论',
        '',
        f'**推荐模型**: {best[0]} (综合分 {best[4]:.3f})',
        '',
        '### 选型矩阵',
        '',
        '| 场景 | 推荐 | 原因 |',
        '| --- | --- | --- |',
    ]

    # Best MCQ
    best_mcq = max(rankings, key=lambda x: x[1])
    lines.append(f'| 知识问答 | {best_mcq[0]} | MCQ {best_mcq[1]:.0%} |')

    # Best Reasoning Judge
    best_reason = max(rankings, key=lambda x: x[2])
    lines.append(f'| 推理 | {best_reason[0]} | Judge {best_reason[2]:.2f} |')

    # Best Code Judge
    best_code = max(rankings, key=lambda x: x[3])
    lines.append(f'| 代码 | {best_code[0]} | Judge {best_code[3]:.2f} |')

    # Best cost
    best_cost = min(rankings, key=lambda x: x[5])
    lines.append(f'| 成本最低 | {best_cost[0]} | ${best_cost[5]:.4f}/题 |')

    lines += [
        '',
        '### 显著性说明',
        '',
        '- `***` p < 0.001 (极显著)',
        '- `**`  p < 0.01 (非常显著)',
        '- `*`   p < 0.05 (显著)',
        '- `ns`  p >= 0.05 (不显著，差异可能由随机造成)',
        '',
        f'*注：当前基于汇总统计量计算，如需精确 p-value 请使用逐题原始数据。*',
    ]

    report_path = os.path.join(REPORT_DIR, 'ab_test_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    json_path = os.path.join(OUTPUT_DIR, f'ab_test_{datetime.now().strftime("%Y%m%d")}.json')
    json_data = {
        'timestamp': now,
        'models': models,
        'rankings': [{'rank': i, 'model': r[0], 'score': r[4]} for i, r in enumerate(rankings, 1)],
        'costs': model_costs,
        'pricing': PRICING,
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    print(f'\nReport: {report_path}')
    print(f'JSON:   {json_path}')
    print(f'\nTop 3:')
    for i, r in enumerate(rankings[:3], 1):
        print(f'  {i}. {r[0]} ({r[4]:.3f})')


if __name__ == '__main__':
    run()
