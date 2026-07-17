"""
regression_check.py — 回归检测 + 成本趋势
比较最近两次评测结果，检测:
- 正确率下降 > 5% → 告警
- Token 消耗趋势
- 模型配置版本

用法: python regression_check.py
输出: scripts/reports/regression_report.md
"""

import os
import json
import glob
import hashlib
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
REPORT_DIR = os.path.join(BASE_DIR, 'reports')
FEV_DIR = os.path.join(PROJECT_ROOT, 'outputs', 'final_eval')
MODEL_CONFIG = os.path.join(PROJECT_ROOT, 'config', 'model_config.yaml')

ALERT_THRESHOLD = 0.05  # 5% accuracy drop triggers alert


def load_history() -> list:
    """Load all final_eval JSON files sorted by time"""
    files = sorted(glob.glob(os.path.join(FEV_DIR, 'final_eval_*.json')))
    results = []
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                results.append(json.load(fh))
        except Exception:
            continue
    return results


def compute_mcq_accuracy(data: dict, model: str) -> float:
    """Extract overall MCQ accuracy for a model"""
    if model not in data:
        return 0
    m = data[model]['mcq']
    total_correct = m['knowledge_correct'] + m['security_correct']
    total = m['knowledge_total'] + m['security_total']
    return total_correct / total if total else 0


def model_config_hash() -> str:
    """Hash of model_config.yaml for version tracking"""
    if os.path.exists(MODEL_CONFIG):
        with open(MODEL_CONFIG, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()[:8]
    return 'unknown'


def run():
    history = load_history()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    config_ver = model_config_hash()

    lines = [
        '# Regression Check Report',
        f'> {now} | Model config: {config_ver}',
        '',
    ]

    if len(history) < 2:
        lines += ['## Status: Not enough data',
                  '',
                  f'Only {len(history)} eval(s) found. Need at least 2 for comparison.',
                  'Run `python run_pipeline.py` at least twice to enable regression checks.',
                  '']
    else:
        prev = history[-2]
        curr = history[-1]
        models = curr.get('models', [])

        # ── Accuracy regression ──
        lines += ['## 1. 正确率回归检测',
                  '',
                  '| 模型 | 上次 MCQ | 本次 MCQ | 变化 | 状态 |',
                  '| --- | --- | --- | --- | --- |']
        alerts = []
        for m in models:
            p_acc = compute_mcq_accuracy(prev, m)
            c_acc = compute_mcq_accuracy(curr, m)
            delta = c_acc - p_acc
            status = '✅' if delta >= -ALERT_THRESHOLD else '🚨 DROP'
            if delta < -ALERT_THRESHOLD:
                alerts.append(f'{m}: MCQ dropped {abs(delta):.1%}')
            lines.append(f'| {m} | {p_acc:.0%} | {c_acc:.0%} | {delta:+.1%} | {status} |')

        if alerts:
            lines += [
                '',
                '### 🚨 Regression Alerts:',
                '',
            ]
            for a in alerts:
                lines.append(f'- {a}')
        else:
            lines += ['', '✅ No regression detected.', '']

        # ── Cost trend ──
        lines += [
            '',
            '## 2. Token 消耗趋势',
            '',
            '| 模型 | 上次 Tokens | 本次 Tokens | 变化 |',
            '| --- | --- | --- | --- |',
        ]
        for m in models:
            p_tok = prev.get(m, {}).get('mcq', {}).get('total_tokens', 0)
            c_tok = curr.get(m, {}).get('mcq', {}).get('total_tokens', 0)
            change = c_tok - p_tok
            sign = '+' if change > 0 else ''
            lines.append(f'| {m} | {p_tok:,} | {c_tok:,} | {sign}{change:,} |')

        # ── Judge trend ──
        lines += [
            '',
            '## 3. Judge 评分趋势',
            '',
            '| 模型 | 上次 Overall | 本次 Overall | 变化 |',
            '| --- | --- | --- | --- |',
        ]
        for m in models:
            p_j = prev.get(m, {}).get('reasoning_base_judge', {}).get('overall', 0)
            c_j = curr.get(m, {}).get('reasoning_base_judge', {}).get('overall', 0)
            lines.append(f'| {m} | {p_j:.2f} | {c_j:.2f} | {c_j-p_j:+.2f} |')

    # ── Model config version ──
    lines += [
        '',
        '## 4. 模型配置版本',
        '',
        f'| 本次 Hash | 时间 |',
        '| --- | --- |',
        f'| `{config_ver}` | {now} |',
        '',
        f'*评测历史共 {len(history)} 次记录*',
    ]

    report_path = os.path.join(REPORT_DIR, 'regression_report.md')
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f'Report: {report_path}')
    if len(history) >= 2:
        has_alert = any(
            compute_mcq_accuracy(history[-2], m) - compute_mcq_accuracy(history[-1], m) > ALERT_THRESHOLD
            for m in history[-1].get('models', [])
        )
        print(f'Regression: {"ALERT!" if has_alert else "OK"}')
    print(f'Config version: {config_ver}')


if __name__ == '__main__':
    run()
