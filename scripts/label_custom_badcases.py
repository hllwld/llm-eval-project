"""
label_custom_badcases.py — 自动标注 Badcase
基于子集类型、错误特征等自动打标签（非交互式，可批量处理）
"""

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
BADCASES_DIR = os.path.join(PROJECT_ROOT, 'data', 'badcases')

INPUT_FILE = os.path.join(BADCASES_DIR, 'custom_badcases_raw.json')
OUTPUT_FILE = os.path.join(BADCASES_DIR, 'custom_badcases_labeled.json')

# ================================================================
# 标注规则
# ================================================================
def auto_label(case):
    """根据 case 的特征自动标注"""

    eval_type = case.get('eval_type', '')
    subset = case.get('subset', '')
    question = case.get('question', '')
    target = case.get('target', '')
    actual = case.get('actual', '')
    score = case.get('score', {})

    # --- 1. 错误类型 ---
    if eval_type == 'mcq' and 'knowledge' in subset:
        error_type = '知识错误'
    elif eval_type == 'mcq' and 'security' in subset:
        error_type = '安全错误'
    elif eval_type == 'qa' and 'code' in subset:
        # 检查是否答案完全跑偏
        if len(actual) < 20:
            error_type = '指令违背'      # 模型拒绝回答或输出过短
        else:
            error_type = '代码错误'
    elif eval_type == 'qa' and 'reasoning' in subset:
        error_type = '推理错误'
    else:
        error_type = '推理错误'          # 默认

    # --- 2. 错误位置 ---
    if error_type == '知识错误':
        error_location = '知识库缺失'
    elif error_type == '安全错误':
        error_location = '过度拒绝' if len(actual) < 30 else '违规通过'
    elif error_type == '代码错误':
        # 按严重程度细分
        rouge = score.get('Rouge-L-R', 1.0)
        if rouge < 0.1:
            error_location = '逻辑错误'
        elif rouge < 0.2:
            error_location = '答非所问'
        else:
            error_location = '边界条件未处理'
    elif error_type == '推理错误':
        error_location = '逻辑链条断裂'
    elif error_type == '指令违背':
        error_location = '格式不符要求'
    else:
        error_location = '逻辑错误'

    # --- 3. RAG 适配度 ---
    if error_type == '知识错误':
        rag_fixable = 'RAG可解'
    elif error_type in ('推理错误', '代码错误'):
        # 部分推理错误可通过检索增强
        rouge = score.get('Rouge-L-R', 1.0)
        if rouge > 0.15:
            rag_fixable = '部分可解'
        else:
            rag_fixable = 'RAG不可解'
    elif error_type == '安全错误':
        rag_fixable = 'RAG不可解'        # 安全类不适合 RAG
    elif error_type == '指令违背':
        rag_fixable = '部分可解'
    else:
        rag_fixable = '部分可解'

    # --- 4. 简要分析 ---
    if eval_type == 'mcq':
        analysis = f'{error_type}：模型在"{subset}"子集中选择错误，期望"{target}"但输出了不同答案'
    elif eval_type == 'qa' and 'code' in subset:
        rouge = score.get('Rouge-L-R', 0)
        analysis = f'代码生成质量低（Rouge-L-R={rouge:.2f}），期望与输出差异显著'
    elif eval_type == 'qa' and 'reasoning' in subset:
        rouge = score.get('Rouge-L-R', 0)
        analysis = f'推理链不完整或有误（Rouge-L-R={rouge:.2f}）'
    else:
        analysis = f'{error_type}错误，位于{error_location}'

    case['annotation'] = {
        'error_type': error_type,
        'error_location': error_location,
        'rag_fixable': rag_fixable,
        'analysis': analysis,
    }
    return case


# ================================================================
# Main
# ================================================================
if __name__ == '__main__':
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        badcases = json.load(f)

    print(f'Loaded {len(badcases)} raw badcases')

    labeled = [auto_label(case) for case in badcases]

    # 统计标注结果
    from collections import Counter
    etypes = Counter([c['annotation']['error_type'] for c in labeled])
    rags = Counter([c['annotation']['rag_fixable'] for c in labeled])

    print('\nError types:')
    for t, n in etypes.most_common():
        print(f'  {t}: {n}')
    print('\nRAG fixability:')
    for r, n in rags.most_common():
        print(f'  {r}: {n}')

    os.makedirs(BADCASES_DIR, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(labeled, f, indent=2, ensure_ascii=False)

    print(f'\nSaved: {OUTPUT_FILE}')
