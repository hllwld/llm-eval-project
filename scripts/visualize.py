"""
visualize.py — 基于最新评测数据生成可视化图表
读取 benchmark_scores JSON，输出 PNG + HTML 仪表板
"""

import json
import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE_DIR, '..')
REPORTS_DIR = os.path.join(ROOT, 'data', 'reports')

# ── 加载数据 ──
def load_latest_scores():
    """加载最新的 benchmark_scores JSON"""
    best = None
    best_ts = ''
    for f in os.listdir(REPORTS_DIR):
        if f.startswith('benchmark_scores_v2_') and f.endswith('.json'):
            ts = f.replace('benchmark_scores_v2_', '').replace('.json', '')
            if ts > best_ts:
                best_ts = ts
                best = f
    if not best:
        print('No benchmark_scores JSON found')
        sys.exit(1)
    with open(os.path.join(REPORTS_DIR, best), 'r', encoding='utf-8') as f:
        return json.load(f)

data = load_latest_scores()
models = data['models']
all_scores = data['all_scores']
diff_scores = data['diff_scores']
avg_scores = data['avg_scores']

# v1 QA scores (for comparison)
v1_qa = {
    'DeepSeek-V3': {'reasoning': 0.6221, 'code': 0.5444},
    'Qwen-Plus':   {'reasoning': 0.5927, 'code': 0.5653},
    'GLM-4-Plus':  {'reasoning': 0.6646, 'code': 0.5369},
    'Qwen2.5-VL':  {'reasoning': 0.5762, 'code': 0.5476},
}

# 颜色
MODEL_COLORS = ['#1a237e', '#2196F3', '#FF9800', '#9C27B0']
SUBSET_COLORS = ['#4CAF50', '#2196F3', '#F44336', '#FF9800']
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ================================================================
# 图 1: 四模型 × 四子集 分组柱状图
# ================================================================
def chart_model_comparison():
    subsets = ['knowledge', 'security', 'reasoning', 'code']
    labels = ['Knowledge', 'Security', 'Reasoning', 'Code']

    x = np.arange(len(labels))
    width = 0.18

    fig, ax = plt.subplots(figsize=(14, 7))
    for i, model in enumerate(models):
        scores = [all_scores[model].get(s, 0) for s in subsets]
        offset = (i - 1.5) * width
        bars = ax.bar(x + offset, scores, width, label=model, color=MODEL_COLORS[i], edgecolor='white', linewidth=0.5)
        for bar in bars:
            h = bar.get_height()
            ax.annotate(f'{h:.0%}' if h > 0.05 else '', xy=(bar.get_x() + bar.get_width()/2, h),
                        xytext=(0, 3), textcoords='offset points', ha='center', fontsize=7, fontweight='bold')

    # 分隔线：MCQ vs QA
    ax.axvline(x=1.5, color='#999', linestyle='--', linewidth=1, alpha=0.5)
    ax.text(0.5, 1.02, 'MCQ (Accuracy)', transform=ax.get_xaxis_transform(), ha='center', fontsize=10, color='#666')
    ax.text(2.5, 1.02, 'QA (Rouge-L-R)', transform=ax.get_xaxis_transform(), ha='center', fontsize=10, color='#666')

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel('Score', fontsize=12)
    ax.set_title(f'Custom Testset v2 — Model Comparison ({data.get("version", "v2")})', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)
    ax.set_ylim(0, 1.15)
    ax.grid(axis='y', linestyle='--', alpha=0.3)

    plt.tight_layout()
    path = os.path.join(REPORTS_DIR, 'chart_model_comparison.png')
    plt.savefig(path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f'[1/4] Model comparison: {path}')

# ================================================================
# 图 2: 分难度对比
# ================================================================
def chart_difficulty():
    diffs = ['easy', 'medium', 'hard']
    x = np.arange(len(diffs))
    width = 0.18

    fig, ax = plt.subplots(figsize=(10, 6))
    for i, model in enumerate(models):
        scores = [diff_scores[model].get(d, 0) for d in diffs]
        offset = (i - 1.5) * width
        bars = ax.bar(x + offset, scores, width, label=model, color=MODEL_COLORS[i], edgecolor='white', linewidth=0.5)
        for bar in bars:
            h = bar.get_height()
            ax.annotate(f'{h:.0%}' if h > 0.05 else '', xy=(bar.get_x() + bar.get_width()/2, h),
                        xytext=(0, 3), textcoords='offset points', ha='center', fontsize=8, fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(['Easy', 'Medium', 'Hard'], fontsize=12)
    ax.set_ylabel('Score', fontsize=12)
    ax.set_title('Difficulty Stratified Comparison', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.set_ylim(0, 1.15)
    ax.grid(axis='y', linestyle='--', alpha=0.3)

    plt.tight_layout()
    path = os.path.join(REPORTS_DIR, 'chart_difficulty.png')
    plt.savefig(path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f'[2/4] Difficulty chart: {path}')

# ================================================================
# 图 3: v1 vs v2 推理+代码对比
# ================================================================
def chart_v1_vs_v2():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    for ax, task in [(ax1, 'reasoning'), (ax2, 'code')]:
        x = np.arange(len(models))
        width = 0.3
        v1_vals = [v1_qa[m].get(task, 0) for m in models]
        v2_vals = [all_scores[m].get(task, 0) for m in models]

        bars1 = ax.bar(x - width/2, v1_vals, width, label='v1', color='#90CAF9', edgecolor='white')
        bars2 = ax.bar(x + width/2, v2_vals, width, label='v2', color='#1a237e', edgecolor='white')

        for bar in bars1:
            h = bar.get_height()
            ax.annotate(f'{h:.0%}', xy=(bar.get_x() + bar.get_width()/2, h),
                        xytext=(0, 3), textcoords='offset points', ha='center', fontsize=8)
        for bar in bars2:
            h = bar.get_height()
            ax.annotate(f'{h:.0%}', xy=(bar.get_x() + bar.get_width()/2, h),
                        xytext=(0, 3), textcoords='offset points', ha='center', fontsize=8, fontweight='bold')

        ax.set_xticks(x)
        ax.set_xticklabels(models, fontsize=9)
        ax.set_title(f'{task.title()} — v1 vs v2', fontsize=13, fontweight='bold')
        ax.legend(fontsize=9)
        ax.set_ylim(0, 0.9)
        ax.grid(axis='y', linestyle='--', alpha=0.3)

    fig.suptitle('QA Improvement: v1 → v2 (Output Constraint + Standardized Answers)', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    path = os.path.join(REPORTS_DIR, 'chart_v1_vs_v2.png')
    plt.savefig(path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f'[3/4] v1-vs-v2 chart: {path}')

# ================================================================
# 图 4: 雷达图（四维度能力画像）
# ================================================================
def chart_radar():
    subsets = ['Knowledge', 'Security', 'Reasoning', 'Code']
    angles = np.linspace(0, 2 * np.pi, len(subsets), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    for i, model in enumerate(models):
        values = [all_scores[model].get(s.lower(), 0) for s in subsets]
        values += values[:1]
        ax.fill(angles, values, alpha=0.1, color=MODEL_COLORS[i])
        ax.plot(angles, values, 'o-', linewidth=2, label=model, color=MODEL_COLORS[i])
        # 标注点
        for a, v in zip(angles[:-1], values[:-1]):
            ax.annotate(f'{v:.0%}', xy=(a, v), fontsize=8, ha='center', color=MODEL_COLORS[i])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(subsets, fontsize=11)
    ax.set_ylim(0, 1.1)
    ax.set_title('Model Capability Radar', fontsize=14, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=9)

    plt.tight_layout()
    path = os.path.join(REPORTS_DIR, 'chart_radar.png')
    plt.savefig(path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f'[4/4] Radar chart: {path}')


# ================================================================
# HTML 仪表板
# ================================================================
def generate_html():
    """生成包含图表的 HTML 可视化页面"""
    charts = ['chart_model_comparison.png', 'chart_difficulty.png',
              'chart_v1_vs_v2.png', 'chart_radar.png']

    chart_html = '\n'.join(
        f'<div class="card"><h2>{c.replace(".png","").replace("chart_","").replace("_"," ").title()}</h2>'
        f'<img src="{c}" style="width:100%;max-width:900px;border-radius:6px;"></div>'
        for c in charts
    )

    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LLM Eval — v2 Visualization</title>
<style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #333; }}
    .header {{ background: linear-gradient(135deg, #1a237e, #283593); color: #fff; padding: 24px; text-align: center; }}
    .header h1 {{ font-size: 22px; }}
    .header p {{ opacity: 0.8; font-size: 13px; margin-top: 4px; }}
    .container {{ max-width: 1000px; margin: 20px auto; padding: 0 16px; }}
    .card {{ background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 20px; margin-bottom: 20px; }}
    .card h2 {{ font-size: 16px; margin-bottom: 12px; border-left: 4px solid #1a237e; padding-left: 10px; }}
    .footer {{ text-align: center; padding: 16px; color: #999; font-size: 12px; }}
    @media (max-width: 768px) {{
        .header h1 {{ font-size: 18px; }}
        .card {{ padding: 12px; }}
    }}
</style>
</head>
<body>
<div class="header">
    <h1>LLM Eval — v2 Visualization</h1>
    <p>4 Models × 4 Subsets × 3 Difficulty Levels | {now}</p>
</div>
<div class="container">
    {chart_html}
</div>
<div class="footer">Generated: {now} | visualize.py</div>
</body>
</html>'''

    html_path = os.path.join(REPORTS_DIR, 'viz_dashboard.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'HTML dashboard: {html_path}')

    # 也复制一份到 outputs
    out_html = os.path.join(ROOT, 'outputs', 'viz_dashboard.html')
    with open(out_html, 'w', encoding='utf-8') as f:
        f.write(html)
    # 复制 PNG 到 outputs（HTML 引用相对路径）
    for c in charts:
        src = os.path.join(REPORTS_DIR, c)
        dst = os.path.join(ROOT, 'outputs', c)
        if os.path.isfile(src):
            import shutil
            shutil.copy(src, dst)


# ================================================================
# Main
# ================================================================
if __name__ == '__main__':
    print(f'Generating charts for {len(models)} models...')
    chart_model_comparison()
    chart_difficulty()
    chart_v1_vs_v2()
    chart_radar()
    generate_html()
    print('\nDone. All charts + HTML dashboard generated in data/reports/')
