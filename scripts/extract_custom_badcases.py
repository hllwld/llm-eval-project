"""
extract_custom_badcases.py — 从 EvalScope review 文件中提取 Badcase
- 搜索 outputs/*/mcq/reviews 和 outputs/*/qa/reviews 目录
- MCQ：acc=0 的即为 badcase
- QA：Rouge-L-R < 0.3 的为低质量回答（badcase）
"""

import json
import glob
import os
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
OUTPUTS_DIR = os.path.join(PROJECT_ROOT, 'outputs')
BADCASES_DIR = os.path.join(PROJECT_ROOT, 'data', 'badcases')


def extract_badcases(output_dir=OUTPUTS_DIR):
    """从 EvalScope 输出目录提取 MCQ 和 QA 的错误样本"""
    badcases = []

    # 匹配 outputs/ModelName/mcq/reviews/ModelName/*.jsonl
    mcq_pattern = os.path.join(output_dir, '*', 'mcq', 'reviews', '*', '*.jsonl')
    qa_pattern = os.path.join(output_dir, '*', 'qa', 'reviews', '*', '*.jsonl')

    review_files = sorted(glob.glob(mcq_pattern)) + sorted(glob.glob(qa_pattern))
    print(f'Found {len(review_files)} review files')

    for review_file in review_files:
        # 相对路径: ModelName/(mcq|qa)/reviews/ModelName/subset.jsonl
        rel = os.path.relpath(review_file, output_dir).replace('\\', '/')
        parts = rel.split('/')
        model_name = parts[0]   # e.g. DeepSeek-V3
        eval_type = parts[1]    # mcq or qa
        subset = os.path.splitext(parts[-1])[0]  # e.g. general_mcq_knowledge

        with open(review_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                score_data = record.get('sample_score', {}).get('score', {})
                values = score_data.get('value', {})
                messages = record.get('messages', [])

                is_badcase = False
                if eval_type == 'mcq':
                    # MCQ: acc == 0 or < 1 means wrong
                    is_badcase = (values.get('acc', 1.0) == 0.0)
                else:
                    # QA: Rouge-L-R < 0.4 as badcase threshold
                    is_badcase = (values.get('Rouge-L-R', 1.0) < 0.4)

                if not is_badcase:
                    continue

                # 提取问题文本（去模板前缀）
                question_raw = ''
                if messages:
                    q = messages[0].get('content', '')
                    if isinstance(q, list):
                        question_raw = ''.join(
                            p.get('text', '') for p in q if isinstance(p, dict)
                        )
                    else:
                        question_raw = str(q)
                    # 去掉 MCQ 模板前缀
                    if '问题：' in question_raw:
                        question_raw = question_raw.split('问题：', 1)[1].strip()

                target = str(record.get('target', ''))
                prediction = str(score_data.get('prediction', ''))

                # QA: 从最后一条 assistant message 提取回答
                actual = prediction
                if eval_type == 'qa':
                    for msg in reversed(messages):
                        if msg.get('role') == 'assistant':
                            actual = str(msg.get('content', prediction))
                            break

                badcases.append({
                    'model': model_name,
                    'eval_type': eval_type,
                    'subset': subset,
                    'question': question_raw[:800],
                    'target': target[:800],
                    'actual': actual[:800],
                    'score': {k: round(v, 4) for k, v in values.items()},
                    'sample_id': record.get('sample_score', {}).get('sample_id', ''),
                    'sample_metadata': record.get('sample_score', {}).get('sample_metadata', {}),
                })

    return badcases


if __name__ == '__main__':
    badcases = extract_badcases()
    print(f'Extracted {len(badcases)} badcases')

    # 统计
    stats = defaultdict(lambda: defaultdict(int))
    for bc in badcases:
        stats[bc['model']][bc['subset']] += 1

    print('\nBadcase distribution:')
    for model, subsets in sorted(stats.items()):
        print(f'  {model}:')
        for subset, count in sorted(subsets.items()):
            print(f'    - {subset}: {count}')

    # 保存
    os.makedirs(BADCASES_DIR, exist_ok=True)
    output_path = os.path.join(BADCASES_DIR, 'custom_badcases_raw.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(badcases, f, indent=2, ensure_ascii=False)

    print(f'\nSaved: {output_path}')
