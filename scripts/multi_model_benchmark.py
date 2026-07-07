# multi_model_benchmark.py — 多模型对比评测 + Badcase 收集
# 对应 evalscope/03_multi_model_benchmark/multi_model.py

import os
import json
import yaml
from datetime import datetime
from dotenv import load_dotenv
from evalscope.run import run_task

# 自动加载项目根目录的 .env 文件
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

# 加载模型配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(BASE_DIR, '..', 'config', 'model_config.yaml')

with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 构建模型列表
MODELS = []
for m in config['models']:
    api_key_env = m.get('api_key_env', '')
    MODELS.append({
        'name': m['name'],
        'model': m['model_id'],
        'api_url': m['api_url'],
        'api_key_env': api_key_env,
        # 从 .env 环境变量读 key（需先 source .env 或使用 dotenv）
        'api_key': os.getenv(api_key_env, ''),
    })

DATASETS = [d['name'] for d in config['datasets']]
LIMIT = config['datasets'][0]['limit']
GENERATION_CONFIG = config.get('generation_config', {})

OUTPUTS_DIR = os.path.join(BASE_DIR, '..', 'outputs')
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# ========== 辅助函数 ==========
def extract_score(work_dir, model_key, dataset):
    report_dir = os.path.join(work_dir, 'reports', model_key)
    if not os.path.isdir(report_dir):
        return None
    json_path = os.path.join(report_dir, f'{dataset}.json')
    if not os.path.isfile(json_path):
        return None
    with open(json_path, 'r', encoding='utf-8') as f:
        report = json.load(f)
    def _find(obj):
        if isinstance(obj, dict):
            if obj.get('name') == 'mean_acc' and 'score' in obj:
                return obj['score']
            for v in obj.values():
                r = _find(v)
                if r is not None:
                    return r
        elif isinstance(obj, list):
            for item in obj:
                r = _find(item)
                if r is not None:
                    return r
        return None
    return _find(report)

def collect_badcases(work_dir, model_key, max_per_model=5):
    reviews_dir = os.path.join(work_dir, 'reviews', model_key)
    if not os.path.isdir(reviews_dir):
        return []

    badcases = []
    for filename in os.listdir(reviews_dir):
        if not filename.endswith('.jsonl'):
            continue
        with open(os.path.join(reviews_dir, filename), 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                except:
                    continue
                score_meta = record.get('sample_score', {}).get('score', {})
                values = score_meta.get('value', {})
                is_correct = all(
                    (isinstance(v, (int, float)) and v == 1.0) or not isinstance(v, (int, float))
                    for v in values.values()
                )
                if is_correct:
                    continue

                target = record.get('target', '')
                messages = record.get('messages', [])
                question = messages[0].get('content', '') if messages else ''
                model_output = ''
                if len(messages) > 1:
                    last_msg = messages[-1].get('content', '')
                    if isinstance(last_msg, list):
                        model_output = ''.join(
                            p.get('text', '') for p in last_msg
                            if isinstance(p, dict) and p.get('type') == 'text'
                        )
                    else:
                        model_output = last_msg

                badcases.append({
                    'dataset_subset': filename.replace('.jsonl', ''),
                    'question': question[:500],
                    'target': target,
                    'model_output': model_output[:800],
                    'score': values,
                })
                if len(badcases) >= max_per_model * 5:
                    break
    return badcases[:max_per_model]

# ========== 执行评测 ==========
all_scores = {}
all_badcases = {}

print("=" * 60)
print("多模型对比评测")
print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"模型数: {len(MODELS)} | 数据集: {len(DATASETS)} | 每题: {LIMIT} 条")
print("=" * 60)

for mc in MODELS:
    model_name = mc['name']
    print(f"\n--- 评测: {model_name} ---")
    if not mc['api_key']:
        print(f"  跳过: .env 未配置 {mc.get('api_key_env', '未知key')}")
        continue

    all_scores[model_name] = {}
    for ds in DATASETS:
        print(f"  数据集: {ds}")
        try:
            work_dir = os.path.join(OUTPUTS_DIR, model_name, ds)
            task_cfg = {
                'model': mc['model'], 'model_id': mc['name'],
                'api_url': mc['api_url'], 'api_key': mc['api_key'],
                'eval_type': 'openai_api', 'datasets': [ds],
                'limit': LIMIT, 'generation_config': GENERATION_CONFIG,
                'eval_batch_size': 1, 'timeout': 60, 'stream': True,
                'work_dir': work_dir, 'no_timestamp': True,
            }
            run_task(task_cfg=task_cfg)
            score = extract_score(work_dir, mc['name'], ds)
            if score is not None:
                all_scores[model_name][ds] = score
                print(f"    ➤ {ds}: {score:.2%}")
            else:
                print(f"    ⚠ 报告未找到")
        except Exception as e:
            print(f"  ❌ 失败: {e}")

    # 收集 Badcase
    model_badcases = []
    for ds in DATASETS:
        for bc in collect_badcases(os.path.join(OUTPUTS_DIR, model_name, ds), mc['name'], max_per_model=2):
            bc['model'] = model_name
            bc['dataset'] = ds
            model_badcases.append(bc)
    all_badcases[model_name] = model_badcases[:5]
    print(f"  📋 Badcase: {len(all_badcases[model_name])} 条")

# 保存 Badcase
badcase_path = os.path.join(BASE_DIR, '..', 'data', 'badcases', 'badcases_raw.json')
os.makedirs(os.path.dirname(badcase_path), exist_ok=True)
with open(badcase_path, 'w', encoding='utf-8') as f:
    json.dump(all_badcases, f, indent=2, ensure_ascii=False)
print(f"\nBadcase 已保存至: {badcase_path}")

# 生成对比表
def format_table(scores):
    h = ['模型'] + DATASETS
    lines = ['| ' + ' | '.join(h) + ' |', '|' + '|'.join([' --- '] * len(h)) + '|']
    for mc in MODELS:
        name = mc['name']
        row = [name] + [
            f'{scores.get(name, {}).get(ds):.2%}'
            if isinstance(scores.get(name, {}).get(ds), (int, float)) else '-'
            for ds in DATASETS
        ]
        lines.append('| ' + ' | '.join(row) + ' |')
    return '\n'.join(lines)

print("\n" + "=" * 60)
print("📊 对比总表")
print("=" * 60)
print(format_table(all_scores))
print("=" * 60)