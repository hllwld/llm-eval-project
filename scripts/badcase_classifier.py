# badcase_classifier.py — Badcase 三级标签分类与报告生成
# 对应 evalscope/03_multi_model_benchmark/badcase_classifier.py

import json
import os
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BADCASES_PATH = os.path.join(BASE_DIR, '..', 'data', 'badcases', 'badcases_raw.json')
REPORT_PATH = os.path.join(BASE_DIR, '..', 'data', 'reports', 'badcase_analysis_report.md')

# 分类逻辑：按数据集判定
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

# 加载数据
with open(BADCASES_PATH, 'r', encoding='utf-8') as f:
    all_data = json.load(f)

# 分析每条 badcase
analysis = []
stats = Counter()

for model, cases in all_data.items():
    for bc in cases:
        level1, level2, level3, reason = classify(bc)
        stats[level1] += 1
        stats[level2] += 1
        stats[level3] += 1

        # 清理问题文本
        question_raw = bc.get('question', '')
        if 'Please reason step by step' in question_raw:
            question_raw = question_raw.split('Please reason step by step, and put your final answer within')[-1]
        if 'The entire content of your response' in question_raw:
            question_raw = question_raw.split('The entire content of your response should be of the following format:')[-1]

        analysis.append({
            'model': bc['model'],
            'dataset': bc['dataset'],
            'dataset_subset': bc['dataset_subset'],
            'question': question_raw.strip()[:200],
            'target': bc['target'],
            'output': bc['model_output'][:200],
            'score': bc['score'],
            'level1': level1, 'level2': level2, 'level3': level3, 'reason': reason,
        })

# 生成报告
total = sum(len(v) for v in all_data.values())
rag_solvable = stats.get('🔵 RAG可解', 0) + stats.get('🟡 RAG部分可解', 0)

lines = [
    '# Badcase 分类分析报告',
    '',
    f'> 总 Badcase 数：{total} 条 | RAG 可改善率：{rag_solvable}/{total} ({rag_solvable/total*100:.1f}%)',
    '',
    '## 分类体系',
    '',
    '| 一级分类 | 数量 | 占比 | RAG 适配度 |',
    '| --- | --- | --- | --- |',
    f'| 推理错误 | {stats.get("推理错误", 0)} | {stats.get("推理错误", 0)/total*100:.1f}% | 🟡/🔴 |',
    f'| 知识错误 | {stats.get("知识错误", 0)} | {stats.get("知识错误", 0)/total*100:.1f}% | 🔵 RAG可解 |',
    '',
    '## 逐条分析',
    '',
]

for i, item in enumerate(analysis, 1):
    lines.append(f'### {i}. {item["model"]} — {item["dataset"]} ({item["dataset_subset"]})')
    lines.append(f'- **题目**：{item["question"][:100]}...')
    lines.append(f'- **正确答案**：{item["target"]} | **模型输出**：{item["output"][:80]}...')
    lines.append(f'- **标签**：{item["level1"]} → {item["level2"]} → {item["level3"]}')
    lines.append(f'- **分析**：{item["reason"]}')
    lines.append('')

# 写入文件
os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
with open(REPORT_PATH, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f'分析报告已生成：{REPORT_PATH}')
print(f'共分析 {total} 条 Badcase')
print(f'RAG 可改善：{rag_solvable} 条 ({rag_solvable/total*100:.1f}%)')