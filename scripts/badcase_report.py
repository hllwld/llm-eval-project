"""
badcase_report.py — Badcase 分析报告生成
读取标注好的 badcase，生成 Markdown 统计报告
"""

import json
import os
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')

INPUT_FILE = os.path.join(PROJECT_ROOT, 'data', 'badcases', 'custom_badcases_labeled.json')
OUTPUT_FILE = os.path.join(PROJECT_ROOT, 'data', 'reports', 'badcase_analysis.md')

if __name__ == '__main__':
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        labeled = json.load(f)

    print('=' * 60)
    print('Custom Testset Badcase Analysis Report')
    print('=' * 60)

    print(f'\nTotal Badcases: {len(labeled)}')

    # 按模型统计
    model_stats = Counter([c['model'] for c in labeled])
    print('\nBy Model:')
    for model, count in model_stats.most_common():
        print(f'  {model}: {count}')

    # 按子集统计
    subset_stats = Counter([c['subset'] for c in labeled])
    print('\nBy Subset:')
    for subset, count in subset_stats.most_common():
        print(f'  {subset}: {count}')

    # 错误类型分布
    error_types = Counter([c['annotation']['error_type'] for c in labeled])
    print('\nError Types:')
    for etype, count in error_types.most_common():
        pct = count / len(labeled) * 100
        print(f'  {etype}: {count} ({pct:.1f}%)')

    # 错误位置分布
    error_locations = Counter([c['annotation']['error_location'] for c in labeled])
    print('\nError Locations:')
    for loc, count in error_locations.most_common():
        pct = count / len(labeled) * 100
        print(f'  {loc}: {count} ({pct:.1f}%)')

    # RAG 适配度
    rag_stats = Counter([c['annotation']['rag_fixable'] for c in labeled])
    print('\nRAG Fixability:')
    for level, count in rag_stats.most_common():
        pct = count / len(labeled) * 100
        print(f'  {level}: {count} ({pct:.1f}%)')

    # 核心结论
    rag_solvable = sum(1 for c in labeled if c['annotation']['rag_fixable'] == 'RAG可解')
    rag_partial = sum(1 for c in labeled if c['annotation']['rag_fixable'] == '部分可解')
    rag_not = sum(1 for c in labeled if c['annotation']['rag_fixable'] == 'RAG不可解')

    print('\n' + '=' * 60)
    print('Key Conclusions')
    print('=' * 60)
    print(f'  RAG-solvable:    {rag_solvable}/{len(labeled)} ({rag_solvable/len(labeled)*100:.1f}%)')
    print(f'  RAG-partial:     {rag_partial}/{len(labeled)} ({rag_partial/len(labeled)*100:.1f}%)')
    print(f'  RAG-unsolvable:  {rag_not}/{len(labeled)} ({rag_not/len(labeled)*100:.1f}%)')

    # 按类型分析 RAG 可解率
    print('\nRAG Solvable Rate by Error Type:')
    for etype in error_types:
        cases = [c for c in labeled if c['annotation']['error_type'] == etype]
        solvable = sum(1 for c in cases if c['annotation']['rag_fixable'] == 'RAG可解')
        print(f'  {etype}: {solvable}/{len(cases)} ({solvable/len(cases)*100:.1f}%)')

    # ========== 保存 Markdown 报告 ==========
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('# Day 10 Badcase Analysis Report\n\n')
        f.write(f'## 1. Overview\n')
        f.write(f'- Total Badcases: {len(labeled)}\n')
        f.write(f'- Models: {", ".join(model_stats.keys())}\n\n')

        f.write('## 2. Error Type Distribution\n')
        for etype, count in error_types.most_common():
            f.write(f'- {etype}: {count}\n')
        f.write('\n')

        f.write('## 3. RAG Fixability\n')
        f.write(f'- RAG-solvable: {rag_solvable} ({rag_solvable/len(labeled)*100:.1f}%)\n')
        f.write(f'- RAG-partial: {rag_partial} ({rag_partial/len(labeled)*100:.1f}%)\n')
        f.write(f'- RAG-unsolvable: {rag_not} ({rag_not/len(labeled)*100:.1f}%)\n\n')

        f.write('## 4. Sample Badcases\n')
        for i, case in enumerate(labeled[:5]):
            f.write(f'\n### Case {i+1}\n')
            f.write(f'- **Model**: {case["model"]}\n')
            f.write(f'- **Subset**: {case["subset"]}\n')
            f.write(f'- **Question**: {case["question"][:200]}...\n')
            f.write(f'- **Expected**: {case["target"][:150]}...\n')
            f.write(f'- **Actual**: {case["actual"][:150]}...\n')
            f.write(f'- **Error Type**: {case["annotation"]["error_type"]}\n')
            f.write(f'- **Analysis**: {case["annotation"]["analysis"]}\n')
            f.write(f'- **RAG**: {case["annotation"]["rag_fixable"]}\n')

    print(f'\nReport saved: {OUTPUT_FILE}')
