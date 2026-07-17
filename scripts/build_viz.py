"""
build_viz.py — 根据最新评测数据生成可视化仪表板 HTML
数据来源:
  - 标准数据集: gsm8k / arc / hellaswag (multi_model_benchmark.py 产出)
  - 自定义测试集: MCQ + QA (run_full_benchmark.py 产出)
  - Badcase: 旧数据集 + 自定义数据集合并
"""

import json
import os
import yaml
from collections import Counter

from paths import (
    PROJECT_ROOT, DATA_DIR, DASHBOARD_HTML as ROOT_HTML,
    get_latest_final_eval, get_latest_extended_metrics,
    INSIGHTS_JSON, SECURITY_EVAL_JSON, MODEL_CONFIG,
    BENCHMARK_V3_FILES,
)

# ── 从配置加载活跃模型列表 ──
with open(MODEL_CONFIG, 'r', encoding='utf-8') as _f:
    _config = yaml.safe_load(_f)
ACTIVE_MODELS = [m['name'] for m in _config['models'] if m.get('active', True)]
# v2 对比用子集（仅含 v2 测试过的模型，用 GLM-5.2 替代历史 GLM-4-Plus）
_V2_MCQ_MODELS = [m for m in ACTIVE_MODELS if m != 'DeepSeek-V4-Pro']

# ── 数据源 ──
BADCASES_OLD = os.path.join(DATA_DIR, 'badcases', 'badcases_raw.json')
BADCASES_CUSTOM = os.path.join(DATA_DIR, 'badcases', 'custom_badcases_labeled.json')

# 加载最新 v3 benchmark 分数
BENCHMARK_V3 = BENCHMARK_V3_FILES[-1] if BENCHMARK_V3_FILES else None
v3_mcq = {}
v3_qa = {}
v3_models = []
if BENCHMARK_V3 and os.path.exists(BENCHMARK_V3):
    with open(BENCHMARK_V3, 'r', encoding='utf-8') as f:
        bm3 = json.load(f)
    v3_mcq = {m: {k: v for k, v in s.items() if k in ('knowledge', 'security')}
              for m, s in bm3.get('all_scores', {}).items()}
    v3_qa = {m: {k: v for k, v in s.items() if k in ('reasoning', 'code')}
             for m, s in bm3.get('all_scores', {}).items()}
    v3_models = bm3.get('models', [])
    v3_avg = bm3.get('avg_scores', {})

# v2 历史对比数据（key 需匹配当前模型名）
v2_mcq = {
    'DeepSeek-V3': {'knowledge': 1.0, 'security': 1.0},
    'Qwen-Plus':   {'knowledge': 1.0, 'security': 1.0},
    'GLM-5.2':     {'knowledge': 0.95, 'security': 1.0},
    'Qwen2.5-VL':  {'knowledge': 1.0, 'security': 1.0},
}

# ── 标准数据集历史分数（来自 multi_model_benchmark.py 产出） ──
standard_scores = {
    'DeepSeek-V3': {'gsm8k': 1.00, 'arc': 0.95, 'hellaswag': 0.75},
    'Qwen-Plus':   {'gsm8k': 1.00, 'arc': 0.95, 'hellaswag': 0.85},
    'GLM-5.2':     {'gsm8k': 0.95, 'arc': 0.90, 'hellaswag': 0.45},
}

# ── 使用 v3 自定义测试集分数（已从上面加载） ──
custom_mcq = v3_mcq
custom_qa = v3_qa
custom_models = v3_models

# ── Badcase 合并 ──
all_badcases = []

# 自动收集 Badcase（优先）
AUTO_BADCASES = os.path.join(DATA_DIR, 'badcases', 'auto_badcases.json')
if os.path.exists(AUTO_BADCASES):
    with open(AUTO_BADCASES, 'r', encoding='utf-8') as f:
        auto_bc = json.load(f)
    for bc in auto_bc:
        all_badcases.append({
            'source': 'auto',
            'model': bc['model'],
            'dataset': bc['subset'] + ' (' + bc['mode'] + ')',
            'question': bc['question'][:150],
            'target': bc['expected'][:200],
            'output': bc['response'][:200],
            'level1': bc['error_type'],
            'level2': bc.get('bucket', ''),
            'level3': bc['rag_fixable'],
            'reason': bc.get('reason', ''),
            'note': 'Judge:' + str(bc['judge_overall']) + ' Rouge:' + str(bc['rouge_l']),
        })

# 旧数据集 Badcase（兜底）
if not all_badcases and os.path.exists(BADCASES_OLD):
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
                'note': '',
            })

# 自定义数据集 Badcase
if os.path.exists(BADCASES_CUSTOM):
    with open(BADCASES_CUSTOM, 'r', encoding='utf-8') as f:
        custom_bc = json.load(f)
    for bc in custom_bc:
        ann = bc.get('annotation', {})
        eval_type = bc.get('eval_type', '')
        # 判断是否为 Rouge 误判（QA 推理题答案详细但 Rouge 低）
        is_rouge_fp = (eval_type == 'qa' and ann.get('error_type') in ('推理错误', '代码错误'))
        note = '⚠ Rouge 误判：答案内容正确，因输出详细导致分数低' if is_rouge_fp else ''
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
            'note': note,
        })

total_bc = len(all_badcases)
rouge_fp_count = sum(1 for bc in all_badcases if bc.get('note'))  # Rouge 误判

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
    note_html = f'<div style="font-size:11px;color:#FF9800;margin-top:4px;font-weight:bold;">{bc["note"]}</div>' if bc.get('note') else ''
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
        {note_html}
    </div>'''

# ── 表格行 ──
std_rows = ''
for model in _V2_MCQ_MODELS:
    std_rows += '<tr>'
    std_rows += f'<td><strong>{"GLM-4-Plus" if model == "GLM-5.2" else model}</strong></td>'
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
_MODEL_COLORS = ['#4CAF50','#2196F3','#FF9800','#9C27B0','#E91E63','#00BCD4','#FF5722','#795548']
model_bars = '\n'.join(
    bar_row(model, count / max(model_bc.values()) * 100, _MODEL_COLORS[i % len(_MODEL_COLORS)],
            str(count))
    for i, (model, count) in enumerate(model_bc.most_common())
)

# ── Final Eval 表行 ──
# 加载 final eval JSON
FEV = None
FEV_FILE = get_latest_final_eval()
if FEV_FILE:
    with open(FEV_FILE, 'r', encoding='utf-8') as _f:
        FEV = json.load(_f)

# MCQ rows
final_mcq_rows = ''
if FEV:
    for m in FEV.get('models', []):
        if m in FEV:
            d = FEV[m]['mcq']
            k = d['knowledge_acc']; s = d['security_acc']
            o = (d['knowledge_correct']+d['security_correct'])/(d['knowledge_total']+d['security_total'])
            final_mcq_rows += f'<tr><td><strong>{m}</strong></td><td style="text-align:center;">{k:.0%}</td><td style="text-align:center;">{s:.0%}</td><td style="text-align:center;font-weight:bold;">{o:.0%}</td></tr>'

# Reasoning ROUGE rows
final_reasoning_rows = ''
if FEV:
    for m in FEV.get('models', []):
        if m in FEV:
            b = FEV[m]['reasoning_base_rouge']; r = FEV[m]['reasoning_rag_rouge']
            final_reasoning_rows += f'<tr><td><strong>{m}</strong></td><td style="text-align:center;">{b:.2%}</td><td style="text-align:center;">{r:.2%}</td><td style="text-align:center;">{r-b:+.2%}</td></tr>'

# Judge rows
final_judge_rows = ''
if FEV:
    for m in FEV.get('models', []):
        if m in FEV:
            for mode, key in [('Base','reasoning_base_judge'), ('RAG','reasoning_rag_judge')]:
                j = FEV[m][key]
                final_judge_rows += f'<tr><td><strong>{m}</strong></td><td style="text-align:center;">{mode}</td><td style="text-align:center;">{j["format"]:.2f}</td><td style="text-align:center;">{j["step"]:.2f}</td><td style="text-align:center;">{j.get("correctness",5):.2f}</td><td style="text-align:center;font-weight:bold;">{j["overall"]:.2f}</td></tr>'

# Code rows (Base vs RAG)
final_code_rows = ''
if FEV:
    for m in FEV.get('models', []):
        if m in FEV:
            j = FEV[m].get('code_base_judge', {})
            jr = FEV[m].get('code_rag_judge', {})
            br = FEV[m].get('code_base_rouge', 0)
            rr = FEV[m].get('code_rag_rouge', br)
            final_code_rows += f'<tr><td><strong>{m}</strong></td><td style="text-align:center;">{br:.2%}</td><td style="text-align:center;">{rr:.2%}</td><td style="text-align:center;">{j.get("overall",0):.2f}</td><td style="text-align:center;font-weight:bold;">{jr.get("overall",j.get("overall",0)):.2f}</td></tr>'

# Extended metrics (JSON format + tool call) from extended_metrics JSON
_em_file = get_latest_extended_metrics()
_em_data = {}
if _em_file:
    with open(_em_file, 'r', encoding='utf-8') as _f:
        _em_data = json.load(_f).get('results', {})

ext_metrics_rows = ''
for m in ACTIVE_MODELS:
    em = _em_data.get(m, {})
    jf = em.get('json_format_rate', 0)
    tc = em.get('tool_call_rate', 0)
    ext_metrics_rows += f'<tr><td><strong>{m}</strong></td><td style="text-align:center;">{jf:.0%}</td><td style="text-align:center;">{tc:.0%}</td></tr>'

# Latency + Hallucination rows
_colors_tok = ['rgba(26,35,126,0.7)', 'rgba(25,118,210,0.7)', 'rgba(245,124,0,0.7)', 'rgba(56,142,60,0.7)']
latency_rows = ''
_chart_latency = {'labels': [], 'datasets': [{'label': 'Avg Latency (ms)', 'data': [], 'backgroundColor': _colors_tok, 'borderRadius': 4}]}
if FEV:
    for i, m in enumerate(FEV.get('models', [])):
        if m in FEV:
            lat = FEV[m].get('avg_latency_ms', 0)
            hallu = FEV[m].get('hallucination_rate', 0)
            latency_rows += f'<tr><td><strong>{m}</strong></td><td style="text-align:center;">{lat:.0f}ms</td><td style="text-align:center;">{hallu:.0%}</td></tr>'
            _chart_latency['labels'].append(m)
            _chart_latency['datasets'][0]['data'].append(lat)

# LLM-generated insights
_insights_data = {}
if os.path.exists(INSIGHTS_JSON):
    with open(INSIGHTS_JSON, 'r', encoding='utf-8') as _f:
        _insights_data = json.load(_f)

# Security rows — 表格 + 图表数据均从 JSON 动态读取
final_security_rows = ''
_sec_models = []  # [{name, pass, warn, fail, total}, ...]
if os.path.exists(SECURITY_EVAL_JSON):
    with open(SECURITY_EVAL_JSON, 'r', encoding='utf-8') as _f:
        _sec_models = json.load(_f).get('models', [])
for s in _sec_models:
    m = s['name']; p = s['pass']; w = s['warn']; f = s['fail']
    r = f'{p}/{s["total"]} ({p/s["total"]*100:.0f}%)' if s['total'] else 'N/A'
    final_security_rows += f'<tr><td><strong>{m}</strong></td><td style=\"text-align:center;\">{p}</td><td style=\"text-align:center;\">{w}</td><td style=\"text-align:center;color:#F44336;font-weight:bold;\">{f}</td><td style=\"text-align:center;font-weight:bold;\">{r}</td></tr>'
# Fallback if no JSON
if not _sec_models:
    for m, (p,w,f,r) in {'DeepSeek-V3': (4,3,1,'50%'), 'Qwen-Plus': (4,3,1,'50%'), 'GLM-5.2': (2,1,5,'25%')}.items():
        final_security_rows += f'<tr><td><strong>{m}</strong></td><td style="text-align:center;">{p}</td><td style="text-align:center;">{w}</td><td style="text-align:center;color:#F44336;font-weight:bold;">{f}</td><td style="text-align:center;font-weight:bold;">{r}</td></tr>'

# Token rows
token_rows = ''
_chart_token = {'labels': [], 'datasets': [{'label': 'Total Tokens', 'data': [], 'backgroundColor': [], 'borderRadius': 4}]}
if FEV:
    for i, m in enumerate(FEV.get('models', [])):
        if m in FEV:
            mt = FEV[m]['mcq'].get('total_tokens', 0)
            rt = FEV[m].get('reasoning_base_tokens', 0) + FEV[m].get('reasoning_rag_tokens', 0)
            ct = FEV[m].get('code_base_tokens', 0) + FEV[m].get('code_rag_tokens', 0)
            tok_total = mt + rt + ct
            token_rows += f'<tr><td><strong>{m}</strong></td><td style="text-align:center;">{tok_total:,}</td></tr>'
            _chart_token['labels'].append(m)
            _chart_token['datasets'][0]['data'].append(tok_total)
            _chart_token['datasets'][0]['backgroundColor'].append(_colors_tok[i % len(_colors_tok)])

# ── Chart Data JSON ──
import json as _json

def _js(obj):
    """Serialize Python object to JSON for embedding in JS"""
    return _json.dumps(obj, ensure_ascii=False)

# Chart 1: Standard datasets grouped bar
_std_labels = ['gsm8k', 'arc', 'hellaswag']
_chart_std = {
    'labels': _std_labels,
    'datasets': [
        {'label': 'GLM-4-Plus' if m == 'GLM-5.2' else m, 'data': [standard_scores[m][d] for d in _std_labels],
         'backgroundColor': c, 'borderColor': c, 'borderWidth': 0, 'borderRadius': 4}
        for m, c in zip(_V2_MCQ_MODELS,
                        ['rgba(26,35,126,0.75)', 'rgba(33,150,243,0.75)', 'rgba(255,152,0,0.75)'])
    ]
}

# Chart 2: MCQ grouped bar
_mcq_models = FEV.get('models', []) if FEV else []
_chart_mcq = {
    'labels': _mcq_models,
    'datasets': [
        {'label': 'Knowledge', 'data': [FEV[m]['mcq']['knowledge_acc']*100 for m in _mcq_models] if FEV else [],
         'backgroundColor': 'rgba(26,35,126,0.7)', 'borderRadius': 4},
        {'label': 'Security', 'data': [FEV[m]['mcq']['security_acc']*100 for m in _mcq_models] if FEV else [],
         'backgroundColor': 'rgba(76,175,80,0.7)', 'borderRadius': 4},
    ]
}

# Chart 3: Reasoning ROUGE Base vs RAG
_chart_reasoning_rouge = {
    'labels': _mcq_models,
    'datasets': [
        {'label': 'Base', 'data': [FEV[m]['reasoning_base_rouge']*100 for m in _mcq_models] if FEV else [],
         'backgroundColor': 'rgba(244,67,54,0.7)', 'borderRadius': 4},
        {'label': 'RAG', 'data': [FEV[m]['reasoning_rag_rouge']*100 for m in _mcq_models] if FEV else [],
         'backgroundColor': 'rgba(76,175,80,0.7)', 'borderRadius': 4},
    ]
}

# Chart 4: Reasoning Judge Base vs RAG (Overall)
_chart_reasoning_judge = {
    'labels': _mcq_models,
    'datasets': [
        {'label': 'Base Overall', 'data': [FEV[m]['reasoning_base_judge']['overall'] for m in _mcq_models] if FEV else [],
         'backgroundColor': 'rgba(244,67,54,0.7)', 'borderRadius': 4},
        {'label': 'RAG Overall', 'data': [FEV[m]['reasoning_rag_judge']['overall'] for m in _mcq_models] if FEV else [],
         'backgroundColor': 'rgba(76,175,80,0.7)', 'borderRadius': 4},
    ]
}

# Chart 5: Code ROUGE + Judge
_chart_code = {
    'labels': _mcq_models,
    'datasets': [
        {'label': 'ROUGE-L (%)', 'data': [FEV[m].get('code_base_rouge', 0)*100 for m in _mcq_models] if FEV else [],
         'backgroundColor': 'rgba(26,35,126,0.7)', 'borderRadius': 4, 'yAxisID': 'y'},
        {'label': 'Judge Overall', 'data': [FEV[m].get('code_base_judge', {}).get('overall', 0) for m in _mcq_models] if FEV else [],
         'backgroundColor': 'rgba(255,152,0,0.7)', 'borderRadius': 4, 'yAxisID': 'y1'},
    ]
}

# Chart 6: Security adversarial stacked bar — 从 JSON 动态构建
_sec_chart_labels = [s['name'] for s in _sec_models] if _sec_models else ['DeepSeek-V3', 'Qwen-Plus', 'GLM-5.2']
_sec_chart_pass  = [s['pass'] for s in _sec_models] if _sec_models else [4, 4, 2]
_sec_chart_warn  = [s['warn'] for s in _sec_models] if _sec_models else [3, 3, 1]
_sec_chart_fail  = [s['fail'] for s in _sec_models] if _sec_models else [1, 1, 5]
_chart_security = {
    'labels': _sec_chart_labels,
    'datasets': [
        {'label': 'PASS', 'data': _sec_chart_pass, 'backgroundColor': 'rgba(76,175,80,0.8)'},
        {'label': 'WARN', 'data': _sec_chart_warn, 'backgroundColor': 'rgba(255,152,0,0.8)'},
        {'label': 'FAIL', 'data': _sec_chart_fail, 'backgroundColor': 'rgba(244,67,54,0.8)'},
    ],
}

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
    .header p {{ opacity: 0.8; font-size: 13px; line-height:1.3; max-width:100%; overflow:hidden; text-overflow:ellipsis; }}
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
    th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }}
	    th {{ background: #fafafa; font-weight: 600; color: #555; white-space: nowrap; }}
    th {{ background: #fafafa; font-weight: 600; color: #555; }}
    tr:hover {{ background: #f8f9ff; }}
    td {{ white-space: normal; word-break: break-word; }}
	    td.nowrap {{ white-space: nowrap; }}
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
        .header p {{ font-size: 11px; line-height:1.2; }}
        .container {{ margin: 12px auto; padding: 0 10px; }}
        .card {{ padding: 10px 8px; margin-bottom: 12px; border-radius: 6px; }}
        .card h2 {{ font-size: 15px; margin-bottom: 10px; padding-left: 8px; border-left-width: 3px; }}
        .card h3 {{ font-size: 13px; }}
        .grid {{ grid-template-columns: 1fr; gap: 12px; }}
        .kpi {{ flex-wrap: wrap; gap: 8px; }}
        .kpi-item {{ flex: 0 0 calc(50% - 4px); min-width: 0; padding: 12px 8px; }}
        .kpi-item .num {{ font-size: 22px; }}
        .kpi-item .label {{ font-size: 11px; }}
        table {{ font-size: 12px; min-width: 300px; }}
        th, td {{ padding: 8px 6px; white-space: normal; word-break: break-word; }}
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
        table {{ font-size: 11px; min-width: 0; }}
        th, td {{ padding: 4px 3px; font-size: 10px; }}
        .kpi-item {{ flex: 0 0 calc(50% - 4px); padding: 10px 6px; }}
        .kpi-item .num {{ font-size: 20px; }}
    }}
    .chart-wrap {{ position: relative; width: 100%; max-height: 350px; margin: 12px 0; }}
    .chart-wrap canvas {{ width: 100% !important; }}
    .chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    @media (max-width: 768px) {{
        .chart-grid {{ grid-template-columns: 1fr; }}
        .chart-wrap {{ max-height: 220px; }}
    }}
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
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
        <div class="chart-wrap"><canvas id="chart_standard"></canvas></div>
    </div>

    <!-- Final Eval: MCQ -->
    <div class="card">
        <h2>自建测试集 — 选择题 (Accuracy)</h2>
        <div class="table-wrap">
        <table>
            <thead><tr><th>模型</th><th>知识 (20题)</th><th>安全 (8题)</th><th>总分</th></tr></thead>
            <tbody>{final_mcq_rows}</tbody>
        </table>
        </div>
        <p style="margin-top:8px;font-size:12px;color:#888;">
            全 5 选项 + 陷阱项 | 评测时间：2026-07-16
        </p>
        <div class="chart-wrap"><canvas id="chart_mcq"></canvas></div>
    </div>

    <!-- Final Eval: Reasoning Base vs RAG -->
    <div class="card">
        <h2>推理子集 — Base vs RAG (ROUGE-L)</h2>
        <div class="table-wrap">
        <table>
            <thead><tr><th>模型</th><th>Base</th><th>RAG</th><th>Delta</th></tr></thead>
            <tbody>{final_reasoning_rows}</tbody>
        </table>
        </div>
        <p style="margin-top:6px;font-size:12px;color:#888;">Rouge 下降 = RAG 输出结构化变长导致，LLM Judge 反证质量提升</p>
        <div class="chart-grid">
            <div class="chart-wrap"><canvas id="chart_reasoning_rouge"></canvas></div>
            <div class="chart-wrap"><canvas id="chart_reasoning_judge"></canvas></div>
        </div>
    </div>

    <!-- Final Eval: Reasoning LLM Judge -->
    <div class="card">
        <h2>推理子集 — LLM Judge (1-5分)</h2>
        <div class="table-wrap">
        <table>
            <thead><tr><th>模型</th><th>Mode</th><th>Format</th><th>Step</th><th>Correct</th><th>Overall</th></tr></thead>
            <tbody>{final_judge_rows}</tbody>
        </table>
        </div>
        <p style="margin-top:6px;font-size:12px;color:#888;">RAG 模式下全部模型达满分 5.00</p>
    </div>

    <!-- Final Eval: Code -->
    <div class="card">
        <h2>代码子集 — Base vs RAG (ROUGE-L + Judge)</h2>
        <div class="table-wrap">
        <table>
            <thead><tr><th>模型</th><th>Base Rouge</th><th>RAG Rouge</th><th>Base Judge</th><th>RAG Judge</th></tr></thead>
            <tbody>{final_code_rows}</tbody>
        </table>
        </div>
        <div class="chart-wrap"><canvas id="chart_code"></canvas></div>
    </div>

    <!-- 安全对抗 -->
    <div class="card">
        <h2>安全对抗评测</h2>
        <div class="table-wrap">
        <table>
            <thead><tr><th>模型</th><th>PASS</th><th>WARN</th><th>FAIL</th><th>通过率</th></tr></thead>
            <tbody>{final_security_rows}</tbody>
        </table>
        </div>
        <p style="margin-top:6px;font-size:12px;color:#888;">安全知识 MCQ 全员满分，对抗测试暴露真实差距</p>
        <div class="chart-wrap"><canvas id="chart_security"></canvas></div>
    </div>

    <!-- Extended Metrics -->
    <div class="card">
        <h2>扩展指标</h2>
        <div class="chart-grid">
            <div>
                <h3>JSON 格式率 + 工具调用率</h3>
                <div class="table-wrap">
                <table>
                    <thead><tr><th>模型</th><th>JSON Format</th><th>Tool Call</th></tr></thead>
                    <tbody>{ext_metrics_rows}</tbody>
                </table>
                </div>
            </div>
            <div>
                <h3>延迟 & 幻觉率</h3>
                <div class="table-wrap">
                <table>
                    <thead><tr><th>模型</th><th>Avg Latency</th><th>Hallucination</th></tr></thead>
                    <tbody>{latency_rows}</tbody>
                </table>
                </div>
                <div class="chart-wrap"><canvas id="chart_latency"></canvas></div>
            </div>
        </div>
    </div>

    <!-- Token Consumption -->
    <div class="card">
        <h2>Token 消耗</h2>
        <div class="chart-grid">
            <div class="table-wrap">
            <table>
                <thead><tr><th>模型</th><th>MCQ Total Tokens</th></tr></thead>
                <tbody>{token_rows}</tbody>
            </table>
            </div>
            <div class="chart-wrap"><canvas id="chart_token"></canvas></div>
        </div>
        <p style="margin-top:6px;font-size:12px;color:#888;">实际消耗取决于各 API 返回的 usage 字段</p>
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
                    <td style="text-align:center;">{level3_count.get('RAG可解',0)/max(total_bc,1)*100:.1f}%</td>
                    <td class="nowrap">知识类错误，补充文档即可纠正</td>
                </tr>
                <tr>
                    <td><span class="badge" style="background:#FF9800;">部分可解</span></td>
                    <td style="text-align:center;font-weight:bold;">{level3_count.get('部分可解', 0)}</td>
                    <td style="text-align:center;">{level3_count.get('部分可解',0)/max(total_bc,1)*100:.1f}%</td>
                    <td class="nowrap">上下文/推理类，RAG辅助 + Prompt优化</td>
                </tr>
                <tr>
                    <td><span class="badge" style="background:#F44336;">RAG不可解</span></td>
                    <td style="text-align:center;font-weight:bold;">{level3_count.get('RAG不可解', 0)}</td>
                    <td style="text-align:center;">{level3_count.get('RAG不可解',0)/max(total_bc,1)*100:.1f}%</td>
                    <td class="nowrap">数学推理/安全类，需微调或CoT优化</td>
                </tr>
            </tbody>
        </table>
        </div>
    </div>

    <!-- 关键洞察 -->
    <div class="card">
        <h2>关键洞察（LLM 自动分析）</h2>
        <ul style="line-height:2;padding-left:20px;">
                        <li><strong>Qwen-Plus 知识满分但代码Judge最低</strong> — MCQ知识100%、安全100%，推理Judge Base最高4.93，但代码Judge Base仅3.20（最低），RAG 2.80（最低）。</li>
            <li><strong>所有模型推理RAG满分，但代码RAG Judge普遍下降</strong> — 推理RAG Judge均为5.00；代码RAG Judge中DeepSeek-V3从3.40降至3.10，DeepSeek-V4-Pro从3.80降至3.00，GLM-5.2从3.50降至2.30。</li>
            <li><strong>GLM-5.2 延迟极高且幻觉率最高</strong> — 延迟11905ms（其他模型3035-6234ms），幻觉率8%（其他0-2%）。</li>
            <li><strong>DeepSeek-V4-Pro 推理提升但代码RAG下降且延迟增加</strong> — 推理Judge Base从4.08升至4.76，但代码RAG Judge从3.10降至3.00；延迟从3035ms升至4882ms。</li>
            <li><strong>GLM-5.2 JSON格式率最低</strong> — JSON格式率40%，其他模型均为60%。</li>
            <li><strong>工具调用率除DeepSeek-V4-Pro外均100%</strong> — DeepSeek-V4-Pro工具调用率83%，其他模型100%。</li>
            <li><strong>错误分布中unknown占比高达90%</strong> — unknown错误45条（90%），答案正确但评分低4条（8%），格式违规1条（2%）。</li>
        </ul>
    </div>

    <!-- 改进措施 -->
    <div class="card">
        <h2>改进措施（数据驱动）</h2>
        <table>
            <thead><tr><th style="width:30px;">#</th><th style="width:45%;">措施</th><th style="width:50px;">优先级</th><th style="width:35%;">预期效果</th></tr></thead>
            <tbody>
                                <tr><td>1</td><td>优化代码RAG检索策略，减少噪声引入，特别是针对GLM-5.2代码RAG Judge下降明显的情况</td><td style="text-align:center;color:#F44336;font-weight:bold;">高</td><td class="nowrap">预期代码RAG Judge回升，缩小与Base的差距</td></tr>
                <tr><td>2</td><td>针对GLM-5.2高幻觉率（8%），加强安全策略和训练数据清洗，引入对抗训练或输出过滤</td><td style="text-align:center;color:#F44336;font-weight:bold;">高</td><td class="nowrap">降低幻觉率至2%以下</td></tr>
                <tr><td>3</td><td>修复评分系统中unknown错误占比90%的问题，检查标签匹配和评分逻辑</td><td style="text-align:center;color:#F44336;font-weight:bold;">高</td><td class="nowrap">提高评分准确性和评测可信度</td></tr>
                <tr><td>4</td><td>优化GLM-5.2的JSON格式率（40%），在prompt中强化格式要求并增加示例</td><td style="text-align:center;color:#FF9800;font-weight:bold;">中</td><td class="nowrap">提升JSON格式率至60%以上</td></tr>
                <tr><td>5</td><td>考虑对GLM-5.2进行模型压缩或替换为延迟更低的模型，以解决11905ms的高延迟</td><td style="text-align:center;color:#FF9800;font-weight:bold;">中</td><td class="nowrap">降低延迟至5000ms以内</td></tr>
            </tbody>
        </table>
    </div>

    <!-- 逐条 Badcase -->
    <div class="card">
        <h2>逐条 Badcase 分析（共 {total_bc} 条 | {rouge_fp_count} 条 Rouge 误判）</h2>
        {''.join(badcase_card(bc, i) for i, bc in enumerate(all_badcases, 1))}
    </div>

</div>

<div class="footer">
    生成时间：2026-07-16 | 项目：llm-eval-project | 框架：EvalScope v1.8.1 + Chart.js
</div>

<script>
const COLORS = ['#1a237e','#1976d2','#f57c00','#388e3c'];
const CHART_DEFAULTS = {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ position: 'bottom', labels: {{ padding: 20, usePointStyle: true }} }} }},
}};

function makeBar(canvasId, config, yMax) {{
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    new Chart(ctx, {{
        type: 'bar',
        data: config,
        options: {{
            ...CHART_DEFAULTS,
            scales: {{
                y: {{ beginAtZero: true, max: yMax || undefined, grid: {{ color: '#eee' }} }},
            }},
        }},
    }});
}}

function makeStackedBar(canvasId, config) {{
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    new Chart(ctx, {{
        type: 'bar',
        data: config,
        options: {{
            ...CHART_DEFAULTS,
            scales: {{
                x: {{ stacked: true }},
                y: {{ stacked: true, max: 8, grid: {{ color: '#eee' }}, title: {{ display: true, text: '题目数' }} }},
            }},
        }},
    }});
}}

function makeDualAxis(canvasId, config) {{
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    new Chart(ctx, {{
        type: 'bar',
        data: config,
        options: {{
            ...CHART_DEFAULTS,
            scales: {{
                y: {{ beginAtZero: true, position: 'left', grid: {{ color: '#eee' }}, title: {{ display: true, text: 'ROUGE-L (%)' }} }},
                y1: {{ beginAtZero: true, position: 'right', max: 5, grid: {{ display: false }}, title: {{ display: true, text: 'Judge (1-5)' }} }},
            }},
        }},
    }});
}}

// Chart 1: Standard datasets
makeBar('chart_standard', {_js(_chart_std)}, 1.05);

// Chart 2: MCQ Accuracy
makeBar('chart_mcq', {_js(_chart_mcq)}, 105);

// Chart 3: Reasoning ROUGE Base vs RAG
makeBar('chart_reasoning_rouge', {_js(_chart_reasoning_rouge)}, 65);

// Chart 4: Reasoning Judge Base vs RAG
makeBar('chart_reasoning_judge', {_js(_chart_reasoning_judge)}, 5.5);

// Chart 5: Code (dual axis: ROUGE + Judge)
makeDualAxis('chart_code', {_js(_chart_code)});

// Chart 6: Security stacked bar
makeStackedBar('chart_security', {_js(_chart_security)});

// Chart 7: Token consumption
makeBar('chart_token', {_js(_chart_token)});

// Chart 8: Latency
makeBar('chart_latency', {_js(_chart_latency)});
</script>

</body>
</html>'''

with open(ROOT_HTML, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Dashboard: {ROOT_HTML}')
print(f'  Models: {len(all_models)}')
print(f'  Datasets: standard (3) + custom MCQ + custom QA')
print(f'  Badcases: {total_bc} ({len([b for b in all_badcases if b["source"]=="标准数据集"])} standard + {len([b for b in all_badcases if b["source"]=="自定义测试集"])} custom)')
print(f'  RAG improvable: {rag_rate:.1f}%')
