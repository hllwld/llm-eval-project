"""
precheck.py — 评测前置校验（Sanity Check）
免跑完整评测，秒级侦测：题目过简单 / 选项无效 / 答案格式错配
LLM 自检层用 DeepSeek API
"""

import os
import sys
import json
import csv
import yaml
import statistics
from collections import Counter
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE_DIR, '..')
load_dotenv(os.path.join(ROOT, '.env'))

# ── 配置 ──
MCQ_DIR = os.path.join(ROOT, 'data', 'custom_testset', 'mcq')
QA_DIR = os.path.join(ROOT, 'data', 'custom_testset', 'qa')
DEEPSEEK_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL = 'https://api.deepseek.com/v1/chat/completions'

# 阈值
WEAK_MODEL_THRESHOLD = 0.85      # 弱模型正确率 >85% 触发警告
OPTION_UNIFORM_MIN = 0.10         # 每个错误选项至少被选 10%
LENGTH_BIAS_RATIO = 2.0           # 正确/错误平均长度比 >2x 警告
DIFFICULTY_HARD_MIN = 0.20        # hard 题至少占 20%

warnings = []
errors = []


# ================================================================
# 第一层：规则扫描
# ================================================================
def check_option_entropy(csv_path):
    """检查正确选项分布和干扰项有效性"""
    with open(csv_path, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    answers = [r.get('answer', '').strip().upper() for r in rows]
    letters = ['A', 'B', 'C', 'D']
    dist = Counter(answers)

    total = len(answers)
    # 检查是否某选项占比过高
    for letter in letters:
        pct = dist.get(letter, 0) / total
        if pct > 0.50:
            errors.append(f'[选项分布] 正确答案 {letter} 占 {pct:.0%}，超过 50% 阈值，模型可能蒙对')

    # 检查选项是否集中在某几个
    used = set(answers)
    if len(used) < len(letters):
        unused = set(letters) - used
        warnings.append(f'[选项分布] 正确答案从未出现: {unused}，可能暗示选项顺序固化')

    print(f'  [OK] Option entropy: {len(rows)} questions, answer dist={dict(dist)}')
    return dist


def check_difficulty_distribution():
    """检查难度标签是否合理"""
    diff_count = Counter()
    for fname in ['knowledge_val.csv', 'security_val.csv']:
        path = os.path.join(MCQ_DIR, fname)
        if not os.path.isfile(path):
            continue
        with open(path, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                diff_count[row.get('difficulty', 'medium')] += 1

    for fname in ['reasoning.jsonl', 'code.jsonl']:
        path = os.path.join(QA_DIR, fname)
        if not os.path.isfile(path):
            continue
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    item = json.loads(line)
                    diff_count[item.get('difficulty', 'medium')] += 1
                except json.JSONDecodeError:
                    continue

    total = sum(diff_count.values())
    if total == 0:
        errors.append('[难度标签] 未找到任何难度标签，请先在 testset 中注入')
        return diff_count

    hard_pct = diff_count.get('hard', 0) / total
    if hard_pct < DIFFICULTY_HARD_MIN:
        warnings.append(f'[难度标签] hard 题仅 {hard_pct:.0%}，建议 >= {DIFFICULTY_HARD_MIN:.0%}')
    if diff_count.get('easy', 0) / total > 0.50:
        warnings.append(f'[难度标签] easy 题超过 50%，区分度可能不足')

    print(f'  [OK] Difficulty dist: {dict(diff_count)} (total={total})')
    return diff_count


def check_answer_length_bias():
    """检查 QA 答案长度偏差"""
    for fname, label in [('reasoning.jsonl', 'reasoning'), ('code.jsonl', 'code')]:
        path = os.path.join(QA_DIR, fname)
        if not os.path.isfile(path):
            continue
        items = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        ref_lens = [len(item.get('response', '')) for item in items]
        if not ref_lens:
            continue
        avg_len = statistics.mean(ref_lens)
        cv = statistics.stdev(ref_lens) / avg_len if avg_len > 0 and len(ref_lens) > 2 else 0

        if cv < 0.2:
            warnings.append(f'[答案长度] {label}: 参考答案长度几乎一致 (CV={cv:.2f})，模型可能学到长度特征')
        if avg_len < 20:
            warnings.append(f'[答案长度] {label}: 参考答案平均仅 {avg_len:.0f} 字符，过短导致 Rouge 不可靠')

        print(f'  [OK] Answer length ({label}): avg={avg_len:.0f} chars, CV={cv:.2f}')


# ================================================================
# 第二层：LLM 自检（DeepSeek API）
# ================================================================
def llm_difficulty_review():
    """用 DeepSeek 评估选择题难度"""
    if not DEEPSEEK_KEY:
        warnings.append('[LLM自检] 未配置 DEEPSEEK_API_KEY，跳过')
        return

    # 收集所有 MCQ 题目
    questions = []
    for fname in ['knowledge_val.csv', 'security_val.csv']:
        path = os.path.join(MCQ_DIR, fname)
        if not os.path.isfile(path):
            continue
        with open(path, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                questions.append({
                    'id': row.get('id', ''),
                    'q': row.get('question', ''),
                    'A': row.get('A', ''), 'B': row.get('B', ''),
                    'C': row.get('C', ''), 'D': row.get('D', ''),
                    'answer': row.get('answer', ''),
                    'difficulty': row.get('difficulty', ''),
                })

    if len(questions) > 20:
        # 采样：每种难度各取 3 题
        sample = []
        for d in ['easy', 'medium', 'hard']:
            pool = [q for q in questions if q['difficulty'] == d]
            sample.extend(pool[:3])
        questions = sample

    # 构造 prompt
    q_text = '\n'.join(
        f"ID={q['id']} diff={q['difficulty']} | Q:{q['q'][:80]}... | Ans:{q['answer']} | "
        f"Options: A){q['A'][:30]} B){q['B'][:30]} C){q['C'][:30]} D){q['D'][:30]}"
        for q in questions[:15]
    )

    prompt = f"""你是教育测评专家。请评估以下选择题的难度。标准：
- 若随机猜测（25%正确率）与受过普通教育的人预期正确率差小于30%，判定为"过简单"
- 若正确选项过于常识，选项之间区分度过低，判定为"充数题"

请逐题分析，输出JSON数组，每项包含: id, verdict(OK/过简单/充数题), reason(≤20字)
仅输出JSON，不要其他内容。

题目：
{q_text}"""

    try:
        import requests
        resp = requests.post(
            DEEPSEEK_URL,
            headers={'Authorization': f'Bearer {DEEPSEEK_KEY}', 'Content-Type': 'application/json'},
            json={
                'model': 'deepseek-chat',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.1, 'max_tokens': 1024,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            warnings.append(f'[LLM自检] API 返回 {resp.status_code}: {resp.text[:100]}')
            return

        result = resp.json()
        content = result['choices'][0]['message']['content']
        # 提取 JSON
        start = content.find('[')
        end = content.rfind(']') + 1
        if start >= 0 and end > start:
            verdicts = json.loads(content[start:end])
            too_easy = [v for v in verdicts if v.get('verdict') in ('过简单', '充数题')]
            filler = [v for v in verdicts if v.get('verdict') == '充数题']
            if too_easy:
                ids = ', '.join(v['id'] for v in too_easy)
                warnings.append(f'[LLM自检] {len(too_easy)}/{len(verdicts)} 题疑似过简单: {ids}')
            if filler:
                ids = ', '.join(v['id'] for v in filler)
                warnings.append(f'[LLM自检] {len(filler)} 题疑似充数题: {ids}')
            print(f'  [OK] LLM self-review: {len(verdicts)} questions checked, {len(too_easy)} flagged')
        else:
            warnings.append(f'[LLM自检] 无法解析返回JSON: {content[:200]}')
    except Exception as e:
        warnings.append(f'[LLM自检] 调用失败: {e}')


# ================================================================
# 第三层：弱模型快速探测
# ================================================================
def weak_model_smoke_test():
    """用已有 review 数据替代弱模型推理：检查 MCQ 正确率"""
    # 从 outputs 找最近的 review 做统计
    outputs_dir = os.path.join(ROOT, 'outputs')
    if not os.path.isdir(outputs_dir):
        print('  [SKIP] No outputs/ found for smoke test')
        return

    # 统计所有模型的 MCQ 正确率
    for model_dir in sorted(os.listdir(outputs_dir)):
        mcq_path = os.path.join(outputs_dir, model_dir, 'v2', 'mcq')
        if not os.path.isdir(mcq_path):
            mcq_path = os.path.join(outputs_dir, model_dir, 'mcq')  # fallback v1
        if not os.path.isdir(mcq_path):
            continue

        for subset in ['knowledge', 'security']:
            reviews = os.path.join(mcq_path, subset, 'reviews', model_dir)
            if not os.path.isdir(reviews):
                continue
            correct = 0
            total = 0
            for fname in os.listdir(reviews):
                if not fname.endswith('.jsonl'):
                    continue
                with open(os.path.join(reviews, fname), 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            rec = json.loads(line)
                            acc = rec.get('sample_score', {}).get('score', {}).get('value', {}).get('acc', 1.0)
                            if acc == 1.0:
                                correct += 1
                            total += 1
                        except json.JSONDecodeError:
                            continue
            if total > 0:
                rate = correct / total
                if rate > WEAK_MODEL_THRESHOLD:
                    warnings.append(f'[弱模型探测] {model_dir}/{subset}: 正确率 {rate:.0%} > {WEAK_MODEL_THRESHOLD:.0%} 阈值 — MCQ 区分度不足')
                else:
                    print(f'  [OK] Weak model smoke: {model_dir}/{subset} = {rate:.0%}')
                return  # 只测第一个模型/子集即可


# ================================================================
# Main
# ================================================================
if __name__ == '__main__':
    print('=' * 60)
    print('Precheck — Testset Sanity Check')
    print('=' * 60)

    # 1. 选项熵检测
    print('\n[1/5] Option entropy check...')
    for fname in ['knowledge_val.csv', 'security_val.csv']:
        path = os.path.join(MCQ_DIR, fname)
        if os.path.isfile(path):
            check_option_entropy(path)

    # 2. 难度分布
    print('\n[2/5] Difficulty distribution check...')
    check_difficulty_distribution()

    # 3. 答案长度
    print('\n[3/5] Answer length bias check...')
    check_answer_length_bias()

    # 4. 弱模型探测
    print('\n[4/5] Weak model smoke test...')
    weak_model_smoke_test()

    # 5. LLM 自检
    print('\n[5/5] LLM self-review...')
    llm_difficulty_review()

    # ── 汇总 ──
    print('\n' + '=' * 60)
    print('Precheck Report')
    print('=' * 60)

    if errors:
        print(f'\nERRORS ({len(errors)}):')
        for e in errors:
            print(f'  X  {e}')

    if warnings:
        print(f'\nWARNINGS ({len(warnings)}):')
        for w in warnings:
            print(f'  !  {w}')

    if not errors and not warnings:
        print('\n  All checks passed. Ready to run full benchmark.')
    elif errors:
        print(f'\n  Precheck FAILED: {len(errors)} errors. Review before running benchmark.')
    else:
        print(f'\n  Precheck OK with {len(warnings)} warnings. Review warnings before running benchmark.')

    # 返回码
    sys.exit(1 if errors else 0)
