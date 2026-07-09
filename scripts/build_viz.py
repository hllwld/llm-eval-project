"""
build_viz.py — 根据最新评测数据生成可视化仪表板 HTML
数据来源:
  - 标准数据集: gsm8k / arc / hellaswag (multi_model_benchmark.py 产出)
  - 自定义测试集: MCQ + QA (run_full_benchmark.py 产出)
  - Badcase: 旧数据集 + 自定义数据集合并
"""

import json
import os
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'outputs')

# ── 数据源 ──
BENCHMARK_JSON = os.path.join(OUTPUT_DIR, 'benchmark_summary_20260709_1309.json')
BADCASES_OLD = os.path.join(PROJECT_ROOT, 'data', 'badcases', 'badcases_raw.json')
BADCASES_CUSTOM = os.path.join(PROJECT_ROOT, 'data', 'badcases', 'custom_badcases_labeled.json')
OUTPUT_HTML = os.path.join(OUTPUT_DIR, 'dashboard.html')

# ── 标准数据集分数（来自 multi_model_benchmark.py 产出） ──
standard_scores = {
    'DeepSeek-V3': {'gsm8k': 1.00, 'arc': 0.95, 'hellaswag': 0.75},
    'Qwen-Plus':   {'gsm8k': 1.00, 'arc': 0.95, 'hellaswag': 0.85},
    'GLM-4-Plus':  {'gsm8k': 0.95, 'arc': 0.90, 'hellaswag': 0.45},
}

# ── 自定义测试集分数（从 benchmark_summary JSON 读取） ──
try:
    with open(BENCHMARK_JSON, 'r', encoding='utf-8') as f:
        bm = json.load(f)
    custom_mcq = bm.get('mcq_scores', {})
    custom_qa = bm.get('qa_scores', {})
    custom_models = bm.get('models', [])
except (FileNotFoundError, json.JSONDecodeError):
    custom_mcq = {}
    custom_qa = {}
    custom_models = []

# ── Badcase 合并 ──
all_badcases = []

# 旧数据集 Badcase
if os.path.exists(BADCASES_OLD):
    with open(BADCASES_OLD, 'r', encoding='utf-8') as f:
        old_bc = json.load(f)
    for model, cases in old_bc.items():
        for bc in cases:
            ds = bc.get('dataset', '')
            target = bc.get('target', '')
            output = bc.get('model_output', '')[:200]
            question_raw = bc.get('question', '')
            if 'Please reason step by step' in question_raw:
                question_raw = question_raw.split('Please reason step by step')[-1][:200]

            if ds == 'gsm8k':
                tag = ('推理错误', '理解偏差', 'RAG不可解',
                       '数学推理需要模型自身能力')
            elif ds == 'arc':
                tag = ('知识错误', '知识库缺失', 'RAG可解',
                       '科学常识类，通过 RAG 补充即可纠正')
            elif ds == 'hellaswag':
                tag = ('推理错误', '上下文不足', '部分可解',
                       '上下文理解类，RAG 可提供参考')
            else:
                tag = ('知识错误', '知识库缺失', 'RAG可解', '')

            all_badcases.append({
                'source': '标准数据集',
                'model': model, 'dataset': ds,
                'question': question_raw.strip()[:150],
                'target': target, 'output': output,
                'level1': tag[0], 'level2': tag[1],
                'level3': tag[2], 'reason': tag[3],
            })

# 自定义数据集 Badcase
if os.path.exists(BADCASES_CUSTOM):
    with open(BADCASES_CUSTOM, 'r', encoding='utf-8') as f:
        custom_bc = json.load(f)
    for bc in custom_bc:
        ann = bc.get('annotation', {})
        all_badcases.append({
            'source': '自定义测试集',
            'model': bc['model'],
            'dataset': bc['subset'].replace('general_mcq_', 'MCQ-').replace('general_qa_', 'QA-'),
            'question': bc.get('question', '')[:150],
            'target': bc.get('target', '')[:200],
            'output': bc.get('actual', '')[:200],
            'level1': ann.get('error_type', ''),
            'level2': ann.get('error_location', ''),
            'level3': ann.get('rag_fixable', ''),
            'reason': ann.get('analysis', ''),
        })

total_bc = len(all_badcases)

# ── 统计 ──
model_bc = Counter(bc['model'] for bc in all_badcases)
ds_bc = Counter(bc['dataset'] for bc in all_badcases)
level1_count = Counter(bc['level1'] for bc in all_badcases)
level3_count = Counter(bc['level3'] for bc in all_badcases)

# RAG 可改善率
rag_solvable = level3_count.get('RAG可解', 0) + level3_count.get('部分可解', 0)
rag_rate = rag_solvable / total_bc * 100 if total_bc else 0

# 全部模型列表
all_models = sorted(set(list(standard_scores.keys()) + custom_models))
standard_datasets = ['gsm8k', 'arc', 'hellaswag']

# ── HTML 辅助 ──
def bar(percent, color, text, height=18):
    return (
        f'<div style="flex:1;height:{height}px;background:#eee;'
        f'border-radius:3px;overflow:hidden;min-width:40px">'
        f'<div style="width:{percent}%;height:100%;background:{color};'
        f'border-radius:3px;display:flex;align-items:center;'
        f'justify-content:flex-end;padding-right:4px;box-sizing:border-box;">'
        f'<span style="color:#fff;font-size:11px;">{text}</span></div></div>')

def bar_row(label, percent, color, text, max_pct=100):
    w = max(0, min(percent / max_pct * 100, 100))
    return (
        f'<div class="bar-row">'
        f'<span class="bar-label">{label}</span>'
        f'{bar(w, color, text)}</div>')

TAG_COLOR = {'RAG可解': '#2196F3', '部分可解': '#FF9800', 'RAG不可解': '#F44336'}

def badcase_card(bc, i):
    c = TAG_COLOR.get(bc['level3'], '#999')
    return f'''
    <div class="badcase" style="border-left-color:{c};">
        <div class="badcase-header">
            <strong>#{i} {bc['model']} — {bc['dataset']}</strong>
            <span class="badge" style="background:{c};">{bc['level3']}</span>
        </div>
        <div class="badcase-body"><strong>题目：</strong>{bc['question']}</div>
        <div class="badcase-answer">
            <span>答案：{bc['target']}</span>
            <span>输出：{bc['output'][:100]}...</span>
        </div>
        <div class="badcase-tags">
            {bc['level1']} → {bc['level2']} → {bc['level3']} | {bc['reason']}
        </div>
    </div>'''

# ── 表格行 ──
std_rows = ''
for model in ['DeepSeek-V3', 'Qwen-Plus', 'GLM-4-Plus']:
    std_rows += '<tr>'
    std_rows += f'<td><strong>{model}</strong></td>'
    for ds in standard_datasets:
        s = standard_scores[model][ds]
        color = '#4CAF50' if s >= 0.9 else ('#FF9800' if s >= 0.7 else '#F44336')
        std_rows += f'<td style="color:{color};font-weight:bold;text-align:center;">{s:.0%}</td>'
    std_rows += '</tr>'

# 自定义 MCQ 表
mcq_rows = ''
for m in custom_models:
    scores = custom_mcq.get(m, {})
    mcq_rows += '<tr>'
    mcq_rows += f'<td><strong>{m}</strong></td>'
    mcq_rows += f'<td style="text-align:center;">{scores.get("knowledge"):.0%}</td>' if scores.get("knowledge") is not None else '<td style="text-align:center;">-</td>'
    mcq_rows += f'<td style="text-align:center;">{scores.get("security"):.0%}</td>' if scores.get("security") is not None else '<td style="text-align:center;">-</td>'
    mcq_rows += f'<td style="text-align:center;font-weight:bold;">{scores.get("OVERALL"):.0%}</td>' if scores.get("OVERALL") is not None else '<td style="text-align:center;">-</td>'
    mcq_rows += '</tr>'

# 自定义 QA 表
qa_rows = ''
for m in custom_models:
    scores = custom_qa.get(m, {})
    qa_rows += '<tr>'
    qa_rows += f'<td><strong>{m}</strong></td>'
    qa_rows += f'<td style="text-align:center;">{scores.get("code"):.1%}</td>' if scores.get("code") is not None else '<td style="text-align:center;">-</td>'
    qa_rows += f'<td style="text-align:center;">{scores.get("reasoning"):.1%}</td>' if scores.get("reasoning") is not None else '<td style="text-align:center;">-</td>'
    qa_rows += f'<td style="text-align:center;font-weight:bold;">{scores.get("OVERALL"):.1%}</td>' if scores.get("OVERALL") is not None else '<td style="text-align:center;">-</td>'
    qa_rows += '</tr>'

# ── 错误类型分布的柱状图 ──
level1_bars = '\n'.join(
    bar_row(name, count, color, f'{count} 条 ({count/total_bc*100:.1f}%)', max_pct=max(level1_count.values()) if level1_count else 1)
    for name, color, count in [('知识错误', '#2196F3', level1_count.get('知识错误', 0)),
                                ('推理错误', '#F44336', level1_count.get('推理错误', 0)),
                                ('代码错误', '#FF9800', level1_count.get('代码错误', 0))]
    if count > 0
)

# 模型分布柱状图
model_bars = '\n'.join(
    bar_row(model, count / max(model_bc.values()) * 100, ['#4CAF50','#2196F3','#FF9800','#9C27B0'][i],
            str(count))
    for i, (model, count) in enumerate(model_bc.most_common())
)

# ── HTML ──
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LLM 评测仪表板 — llm-eval-project</title>
<style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #333; }}
    .header {{ background: linear-gradient(135deg, #1a237e, #283593); color: #fff; padding: 24px 32px; text-align: center; }}
    .header h1 {{ font-size: 24px; margin-bottom: 4px; }}
    .header p {{ opacity: 0.8; font-size: 14px; }}
    .container {{ max-width: 1100px; margin: 24px auto; padding: 0 16px; }}
    .card {{ background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 20px 24px; margin-bottom: 20px; }}
    .card h2 {{ font-size: 18px; margin-bottom: 16px; border-left: 4px solid #1a237e; padding-left: 10px; }}
    .card h3 {{ font-size: 15px; margin: 16px 0 10px; color: #555; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
    .kpi {{ display: flex; gap: 16px; }}
    .kpi-item {{ flex:1; text-align: center; padding: 16px; background: #f0f4ff; border-radius: 8px; }}
    .kpi-item .num {{ font-size: 28px; font-weight: bold; color: #1a237e; }}
    .kpi-item .label {{ font-size: 12px; color: #666; margin-top: 4px; }}
    .table-wrap {{ width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; min-width: 420px; }}
    th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; white-space: nowrap; }}
    th {{ background: #fafafa; font-weight: 600; color: #555; }}
    tr:hover {{ background: #f8f9ff; }}
    td.nowrap {{ white-space: normal; }}
    .bar-row {{ display: flex; align-items: center; margin: 6px 0; }}
    .bar-label {{ font-size: 12px; margin-right: 8px; flex-shrink: 0; text-align: right; }}
    .badge {{ color: #fff; padding: 2px 8px; border-radius: 10px; font-size: 11px; white-space: nowrap; flex-shrink: 0; }}
    .badcase {{ padding: 14px; margin-bottom: 12px; background: #fff; border-radius: 6px; border-left: 3px solid #ccc; }}
    .badcase-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; gap: 8px; flex-wrap: wrap; }}
    .badcase-header strong {{ font-size: 13px; }}
    .badcase-body {{ font-size: 12px; color: #555; margin-bottom: 4px; word-break: break-all; }}
    .badcase-answer {{ font-size: 12px; color: #555; display: flex; gap: 16px; flex-wrap: wrap; }}
    .badcase-tags {{ font-size: 11px; color: #888; margin-top: 4px; word-break: break-all; }}
    .footer {{ text-align: center; padding: 16px; color: #999; font-size: 12px; }}
    @media (max-width: 768px) {{
        .header {{ padding: 18px 14px; }}
        .header h1 {{ font-size: 18px; }}
        .header p {{ font-size: 12px; }}
        .container {{ margin: 12px auto; padding: 0 10px; }}
        .card {{ padding: 14px 12px; margin-bottom: 12px; border-radius: 6px; }}
        .card h2 {{ font-size: 15px; margin-bottom: 10px; padding-left: 8px; border-left-width: 3px; }}
        .card h3 {{ font-size: 13px; }}
        .grid {{ grid-template-columns: 1fr; gap: 12px; }}
        .kpi {{ flex-wrap: wrap; gap: 8px; }}
        .kpi-item {{ flex: 0 0 calc(50% - 4px); min-width: 0; padding: 12px 8px; }}
        .kpi-item .num {{ font-size: 22px; }}
        .kpi-item .label {{ font-size: 11px; }}
        table {{ font-size: 12px; min-width: 380px; }}
        th, td {{ padding: 8px 6px; }}
        .bar-label {{ font-size: 11px; }}
        .badcase {{ padding: 10px 12px; }}
        .badcase-header strong {{ font-size: 11px; }}
        .badge {{ font-size: 10px; padding: 2px 6px; }}
        .badcase-body {{ font-size: 11px; }}
        .badcase-answer {{ flex-direction: column; gap: 4px; font-size: 11px; }}
        .badcase-tags {{ font-size: 10px; }}
        .footer {{ font-size: 11px; padding: 12px 8px; }}
    }}
    @media (max-width: 400px) {{
        .header h1 {{ font-size: 16px; }}
        .kpi-item {{ flex: 0 0 calc(50% - 4px); padding: 10px 6px; }}
        .kpi-item .num {{ font-size: 20px; }}
    }}
</style>
</head>
<body>

<div class="header">
    <h1>LLM 评测仪表板</h1>
    <p>国产大模型基线对比 — 标准数据集 + 自定义测试集 | 4 模型</p>
</div>

<div class="container">

    <!-- KPI -->
    <div class="card">
        <h2>核心指标</h2>
        <div class="kpi">
            <div class="kpi-item"><div class="num">{len(all_models)}</div><div class="label">评测模型数</div></div>
            <div class="kpi-item"><div class="num">6</div><div class="label">评测数据集</div></div>
            <div class="kpi-item"><div class="num">{total_bc}</div><div class="label">Badcase 总数</div></div>
            <div class="kpi-item"><div class="num">{rag_rate:.0f}%</div><div class="label">RAG 可改善率</div></div>
        </div>
    </div>

    <!-- 标准数据集表格 -->
    <div class="card">
        <h2>标准数据集对比</h2>
        <div class="table-wrap">
        <table>
            <thead><tr><th>模型</th><th>gsm8k (数学)</th><th>arc (科学常识)</th><th>hellaswag (常识推理)</th></tr></thead>
            <tbody>{std_rows}</tbody>
        </table>
        </div>
        <p style="margin-top:12px;font-size:12px;color:#888;">
            样本数：每数据集 20 条 | 评测时间：2026-07-07 | EvalScope v1.8.1
        </p>
    </div>

    <!-- 自定义测试集 - MCQ -->
    <div class="card">
        <h2>自定义测试集 — 选择题 (Accuracy)</h2>
        <div class="table-wrap">
        <table>
            <thead><tr><th>模型</th><th>知识 (20题)</th><th>安全 (5题)</th><th>总分</th></tr></thead>
            <tbody>{mcq_rows}</tbody>
        </table>
        </div>
        <p style="margin-top:8px;font-size:12px;color:#888;">
            共 25 题 | 评测时间：2026-07-09
        </p>
    </div>

    <!-- 自定义测试集 - QA -->
    <div class="card">
        <h2>自定义测试集 — 问答题 (Rouge-L-R)</h2>
        <div class="table-wrap">
        <table>
            <thead><tr><th>模型</th><th>代码 (10题)</th><th>推理 (15题)</th><th>总分</th></tr></thead>
            <tbody>{qa_rows}</tbody>
        </table>
        </div>
        <p style="margin-top:8px;font-size:12px;color:#888;">
            共 25 题 | 评测时间：2026-07-09
        </p>
    </div>

    <div class="grid">
        <!-- Badcase 按模型分布 -->
        <div class="card">
            <h2>Badcase 按模型分布</h2>
            {model_bars}
        </div>

        <!-- 错误类型分布 -->
        <div class="card">
            <h2>错误分类（一级标签）</h2>
            {level1_bars}
        </div>
    </div>

    <!-- RAG 适配度 -->
    <div class="card">
        <h2>RAG 适配度统计</h2>
        <div class="table-wrap">
        <table>
            <thead><tr><th>RAG 适配度</th><th>数量</th><th>占比</th><th>说明</th></tr></thead>
            <tbody>
                <tr>
                    <td><span class="badge" style="background:#2196F3;">RAG可解</span></td>
                    <td style="text-align:center;font-weight:bold;">{level3_count.get('RAG可解', 0)}</td>
                    <td style="text-align:center;">{level3_count.get('RAG可解',0)/total_bc*100:.1f}%</td>
                    <td class="nowrap">知识类错误，补充文档即可纠正</td>
                </tr>
                <tr>
                    <td><span class="badge" style="background:#FF9800;">部分可解</span></td>
                    <td style="text-align:center;font-weight:bold;">{level3_count.get('部分可解', 0)}</td>
                    <td style="text-align:center;">{level3_count.get('部分可解',0)/total_bc*100:.1f}%</td>
                    <td class="nowrap">上下文/推理类，RAG辅助 + Prompt优化</td>
                </tr>
                <tr>
                    <td><span class="badge" style="background:#F44336;">RAG不可解</span></td>
                    <td style="text-align:center;font-weight:bold;">{level3_count.get('RAG不可解', 0)}</td>
                    <td style="text-align:center;">{level3_count.get('RAG不可解',0)/total_bc*100:.1f}%</td>
                    <td class="nowrap">数学推理/安全类，需微调或CoT优化</td>
                </tr>
            </tbody>
        </table>
        </div>
    </div>

    <!-- 关键洞察 -->
    <div class="card">
        <h2>关键洞察</h2>
        <ul style="line-height:2;padding-left:20px;">
            <li><strong>数学推理</strong>：三模型均接近满分（95%~100%），能力差距极小</li>
            <li><strong>科学常识</strong>：三模型 90%~95%，表现稳定</li>
            <li><strong>常识推理 (hellaswag)</strong>：GLM-4-Plus 仅 45%，为最显著短板</li>
            <li><strong>选择题</strong>：自定义 25 道 MCQ 仅 GLM-4-Plus 错 1 题，整体偏简单</li>
            <li><strong>问答题</strong>：GLM-4-Plus 推理最强（66.5%），但代码最弱（53.7%）；DeepSeek-V3 最均衡</li>
            <li><strong>RAG 可改善</strong>：{rag_rate:.0f}% 的 Badcase 可通过知识库或 Prompt 优化解决</li>
        </ul>
    </div>

    <!-- 逐条 Badcase -->
    <div class="card">
        <h2>逐条 Badcase 分析（共 {total_bc} 条）</h2>
        {''.join(badcase_card(bc, i) for i, bc in enumerate(all_badcases, 1))}
    </div>

</div>

<div class="footer">
    生成时间：2026-07-09 | 项目：llm-eval-project | 框架：EvalScope v1.8.1
</div>

</body>
</html>'''

os.makedirs(os.path.dirname(OUTPUT_HTML), exist_ok=True)
with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Dashboard generated: {OUTPUT_HTML}')
print(f'  Models: {len(all_models)}')
print(f'  Datasets: standard (3) + custom MCQ + custom QA')
print(f'  Badcases: {total_bc} ({len([b for b in all_badcases if b["source"]=="标准数据集"])} standard + {len([b for b in all_badcases if b["source"]=="自定义测试集"])} custom)')
print(f'  RAG improvable: {rag_rate:.1f}%')
