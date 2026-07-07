# build_viz.py — 根据评测数据生成可视化仪表板 HTML
import json
import os
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, '..', 'outputs')
BADCASES_PATH = os.path.join(BASE_DIR, '..', 'data', 'badcases', 'badcases_raw.json')
OUTPUT_HTML = os.path.join(OUTPUT_DIR, 'dashboard.html')

# ========== 数据 ==========
benchmark_scores = {
    'DeepSeek-V3': {'gsm8k': 1.0,  'arc': 0.95, 'hellaswag': 0.75},
    'Qwen-Plus':   {'gsm8k': 1.0,  'arc': 0.95, 'hellaswag': 0.85},
    'GLM-4-Plus':  {'gsm8k': 0.95, 'arc': 0.90, 'hellaswag': 0.45},
}

with open(BADCASES_PATH, 'r', encoding='utf-8') as f:
    badcases_raw = json.load(f)

# 统计 badcase 分布
model_bc = {m: len(v) for m, v in badcases_raw.items()}
total_bc = sum(model_bc.values())

# 按数据集分布
ds_bc = {}
for cases in badcases_raw.values():
    for bc in cases:
        ds = bc['dataset']
        ds_bc[ds] = ds_bc.get(ds, 0) + 1

# 分类函数（与 badcase_classifier.py 一致）
def classify(bc):
    ds = bc.get('dataset', '')
    if ds == 'gsm8k':
        return ('推理错误', '理解偏差', '🔴 RAG不可解', '数学推理需要模型自身能力，给外部文档无法解决问题')
    elif ds == 'arc':
        return ('知识错误', '知识库缺失', '🔵 RAG可解', '科学常识类问题，通过 RAG 补充知识文档即可纠正')
    elif ds == 'hellaswag':
        return ('推理错误', '上下文不足', '🟡 RAG部分可解', '句子补全需要理解上下文，RAG 可提供类似场景参考但非根治')
    else:
        return ('知识错误', '知识库缺失', '🔵 RAG可解', '默认归类为知识缺失')

# 按一级分类统计
level1_count = Counter()
# 逐条分析记录
badcase_cards = []
for model, cases in badcases_raw.items():
    for bc in cases:
        level1, level2, level3, reason = classify(bc)
        level1_count[level1] += 1
        
        # 清理问题文本
        question_raw = bc.get('question', '')
        if 'Please reason step by step' in question_raw:
            question_raw = question_raw.split('Please reason step by step, and put your final answer within')[-1]
        if 'The entire content of your response' in question_raw:
            question_raw = question_raw.split('The entire content of your response should be of the following format:')[-1]
        
        target = bc.get('target', '')
        model_output = bc.get('model_output', '')[:200]
        dataset_subset = bc.get('dataset_subset', '')
        
        badcase_cards.append({
            'model': model,
            'dataset': bc.get('dataset', ''),
            'subset': dataset_subset,
            'question': question_raw.strip()[:150],
            'target': target,
            'output': model_output,
            'level1': level1,
            'level2': level2,
            'level3': level3,
            'reason': reason,
        })

# RAG 可改善率
rag_solvable = ds_bc.get('arc', 0) + ds_bc.get('hellaswag', 0)
rag_rate = rag_solvable / total_bc * 100 if total_bc else 0

# ========== HTML 辅助函数 ==========
def bar_chart(data, max_val=None):
    """纯 CSS 柱状图"""
    if max_val is None:
        max_val = max(data.values()) or 1
    bars = []
    colors = ['#4CAF50', '#2196F3', '#FF9800']
    for i, (label, val) in enumerate(data.items()):
        pct = val / max_val * 100
        color = colors[i % len(colors)]
        bars.append(f'''<div style="display:flex;align-items:center;margin:4px 0;">
            <span style="width:100px;text-align:right;margin-right:8px;font-size:12px;">{label}</span>
            <div style="flex:1;height:18px;background:#eee;border-radius:3px;overflow:hidden;">
                <div style="width:{pct}%;height:100%;background:{color};border-radius:3px;display:flex;align-items:center;justify-content:flex-end;padding-right:4px;box-sizing:border-box;">
                    <span style="color:#fff;font-size:11px;">{val}</span>
                </div>
            </div>
        </div>''')
    return '\n'.join(bars)

# 分类颜色映射
level3_color = {'🔵 RAG可解': '#2196F3', '🟡 RAG部分可解': '#FF9800', '🔴 RAG不可解': '#F44336'}

# 生成 badcase 卡片
def render_badcase_cards():
    cards = []
    for i, bc in enumerate(badcase_cards, 1):
        tag_color = level3_color.get(bc['level3'], '#999')
        cards.append(f'''
        <div style="padding:14px;margin-bottom:12px;background:#fff;border-radius:6px;border-left:3px solid {tag_color};">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                <strong style="font-size:13px;">#{i} {bc['model']} — {bc['dataset']} ({bc['subset']})</strong>
                <span style="background:{tag_color};color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;">{bc['level3']}</span>
            </div>
            <div style="font-size:12px;color:#555;margin-bottom:4px;">
                <strong>题目：</strong>{bc['question']}
            </div>
            <div style="font-size:12px;color:#555;display:flex;gap:16px;">
                <span>✅ <strong>正确答案：</strong>{bc['target']}</span>
                <span>❌ <strong>模型输出：</strong>{bc['output'][:80]}...</span>
            </div>
            <div style="font-size:11px;color:#888;margin-top:4px;">
                🏷 <strong>标签：</strong>{bc['level1']} → {bc['level2']} → {bc['level3']} | 📝 {bc['reason']}
            </div>
        </div>''')
    return '\n'.join(cards)

# 生成分类分布饼图（纯CSS百分比展示）
def render_level1_pie():
    """简单百分比展示"""
    lines = []
    colors = {'推理错误': '#F44336', '知识错误': '#2196F3'}
    for cat, cnt in level1_count.items():
        pct = cnt / total_bc * 100
        color = colors.get(cat, '#999')
        lines.append(f'''<div style="display:flex;align-items:center;margin:4px 0;">
            <span style="width:80px;text-align:right;margin-right:8px;font-size:12px;">{cat}</span>
            <div style="flex:1;height:30px;background:#eee;border-radius:4px;overflow:hidden;">
                <div style="width:{pct}%;height:100%;background:{color};border-radius:4px;display:flex;align-items:center;padding-left:8px;box-sizing:border-box;">
                    <span style="color:#fff;font-size:12px;font-weight:bold;">{cnt} 条 ({pct:.1f}%)</span>
                </div>
            </div>
        </div>''')
    return '\n'.join(lines)

# ========== HTML 生成 ==========
table_rows = ''
datasets = ['gsm8k', 'arc', 'hellaswag']
for model in ['DeepSeek-V3', 'Qwen-Plus', 'GLM-4-Plus']:
    table_rows += '<tr>'
    table_rows += f'<td><strong>{model}</strong></td>'
    for ds in datasets:
        score = benchmark_scores[model][ds]
        color = '#4CAF50' if score >= 0.9 else ('#FF9800' if score >= 0.7 else '#F44336')
        table_rows += f'<td style="color:{color};font-weight:bold;text-align:center;">{score:.0%}</td>'
    table_rows += '</tr>'

# 按分类统计（用于柱状图）
cat_bc = {'数学推理(gsm8k)': ds_bc.get('gsm8k', 0),
          '知识错误(arc)': ds_bc.get('arc', 0),
          '上下文不足(hellaswag)': ds_bc.get('hellaswag', 0)}

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
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
    .kpi {{ display: flex; gap: 16px; }}
    .kpi-item {{ flex:1; text-align: center; padding: 16px; background: #f0f4ff; border-radius: 8px; }}
    .kpi-item .num {{ font-size: 28px; font-weight: bold; color: #1a237e; }}
    .kpi-item .label {{ font-size: 12px; color: #666; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }}
    th {{ background: #fafafa; font-weight: 600; color: #555; }}
    tr:hover {{ background: #f8f9ff; }}
    .footer {{ text-align: center; padding: 16px; color: #999; font-size: 12px; }}
    @media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>

<div class="header">
    <h1>📊 LLM 评测仪表板</h1>
    <p>国产三模型基线对比 — DeepSeek-V3 / Qwen-Plus / GLM-4-Plus</p>
</div>

<div class="container">

    <!-- KPI 概览 -->
    <div class="card">
        <h2>核心指标</h2>
        <div class="kpi">
            <div class="kpi-item">
                <div class="num">3</div>
                <div class="label">评测模型数</div>
            </div>
            <div class="kpi-item">
                <div class="num">3</div>
                <div class="label">评测数据集</div>
            </div>
            <div class="kpi-item">
                <div class="num">{total_bc}</div>
                <div class="label">Badcase 总数</div>
            </div>
            <div class="kpi-item">
                <div class="num">{rag_rate:.1f}%</div>
                <div class="label">RAG 可改善率</div>
            </div>
        </div>
    </div>

    <!-- 模型对比表格 -->
    <div class="card">
        <h2>三模型对比总表</h2>
        <table>
            <thead>
                <tr><th>模型</th><th>gsm8k (数学)</th><th>arc (科学常识)</th><th>hellaswag (常识推理)</th></tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        <p style="margin-top:12px;font-size:12px;color:#888;">
            🔍 样本数：每数据集 20 条 | 评测时间：2026-07-07 | EvalScope v1.8.1
        </p>
    </div>

    <div class="grid">
        <!-- Badcase 按模型分布 -->
        <div class="card">
            <h2>Badcase 按模型分布</h2>
            {bar_chart(model_bc, max_val=6)}
        </div>

        <!-- Badcase 按数据集 -->
        <div class="card">
            <h2>Badcase 按数据集</h2>
            {bar_chart(cat_bc, max_val=7)}
        </div>
    </div>

    <!-- 错误分类分布 -->
    <div class="card">
        <h2>错误分类（一级标签）</h2>
        {render_level1_pie()}
    </div>

    <!-- 分级统计 -->
    <div class="card">
        <h2>三级标签统计</h2>
        <table>
            <thead>
                <tr><th>RAG 适配度</th><th>数量</th><th>占比</th><th>说明</th></tr>
            </thead>
            <tbody>
                <tr>
                    <td><span style="background:#2196F3;color:#fff;padding:2px 8px;border-radius:10px;">🔵 RAG可解</span></td>
                    <td style="text-align:center;font-weight:bold;">{ds_bc.get('arc', 0)}</td>
                    <td style="text-align:center;">{ds_bc.get('arc',0)/total_bc*100:.1f}%</td>
                    <td>知识类错误，补充文档即可纠正</td>
                </tr>
                <tr>
                    <td><span style="background:#FF9800;color:#fff;padding:2px 8px;border-radius:10px;">🟡 RAG部分可解</span></td>
                    <td style="text-align:center;font-weight:bold;">{ds_bc.get('hellaswag', 0)}</td>
                    <td style="text-align:center;">{ds_bc.get('hellaswag',0)/total_bc*100:.1f}%</td>
                    <td>上下文理解类，RAG辅助+Pompt优化</td>
                </tr>
                <tr>
                    <td><span style="background:#F44336;color:#fff;padding:2px 8px;border-radius:10px;">🔴 RAG不可解</span></td>
                    <td style="text-align:center;font-weight:bold;">{ds_bc.get('gsm8k', 0)}</td>
                    <td style="text-align:center;">{ds_bc.get('gsm8k',0)/total_bc*100:.1f}%</td>
                    <td>数学推理类，需微调或CoT优化</td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- 关键洞察 -->
    <div class="card">
        <h2>关键洞察</h2>
        <ul style="line-height:2;padding-left:20px;">
            <li>📐 <strong>数学推理</strong>：三模型均接近满分（95%~100%），能力差距极小</li>
            <li>🧠 <strong>科学常识</strong>：三模型 90%~95%，表现稳定</li>
            <li>💬 <strong>常识推理 (hellaswag)</strong>：GLM-4-Plus 仅 45%，为最显著短板</li>
            <li>🔵 <strong>RAG 可改善</strong>：{rag_rate:.0f}% 的 Badcase 可通过知识库补充解决</li>
            <li>🔴 <strong>不可解</strong>：仅 1 条数学推理错误（gsm8k），需微调或 CoT 优化</li>
        </ul>
    </div>

    <!-- 逐条错误分析 -->
    <div class="card">
        <h2>逐条 Badcase 分析（共 {total_bc} 条）</h2>
        {render_badcase_cards()}
    </div>

</div>

<div class="footer">
    生成时间：2026-07-07 | 项目：llm-eval-project | 框架：EvalScope v1.8.1
</div>

</body>
</html>'''

os.makedirs(os.path.dirname(OUTPUT_HTML), exist_ok=True)
with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'可视化仪表板已生成: {OUTPUT_HTML}')
print(f'- 模型对比表: 3 模型 × 3 数据集')
print(f'- Badcase 分析: {total_bc} 条逐条展示')
print(f'- 分类统计: 推理错误 {level1_count.get("推理错误",0)} 条 / 知识错误 {level1_count.get("知识错误",0)} 条')
print(f'- RAG 可改善率: {rag_rate:.1f}%')