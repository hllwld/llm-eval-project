#!/usr/bin/env python
"""
run_full_benchmark.py — 自定义测试集 × 全部模型 完整评测
- 模型 & API key 从 config/model_config.yaml + .env 读取
- 评测结果自动采集并保存为 Markdown 对比表
"""

import os
import sys
import json
import yaml
from datetime import datetime
from dotenv import load_dotenv
from evalscope import TaskConfig, run_task

# ================================================================
# 0. 路径 & 环境初始化
# ================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
OUTPUTS_DIR = os.path.join(PROJECT_ROOT, 'outputs')

# 加载 .env
env_path = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(env_path)

# ================================================================
# 1. 从外部配置文件加载模型列表
# ================================================================
config_path = os.path.join(PROJECT_ROOT, 'config', 'model_config.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

MODELS = []
for m in config['models']:
    api_key_env = m.get('api_key_env', '')
    api_key = os.getenv(api_key_env, '')
    MODELS.append({
        'name': m['name'],
        'model': m['model_id'],
        'api_url': m['api_url'],
        'api_key_env': api_key_env,
        'api_key': api_key,
    })

GENERATION_CONFIG = config.get('generation_config', {})

# 自定义测试集路径（相对于项目根目录）
MCQ_LOCAL_PATH = os.path.join(PROJECT_ROOT, 'data', 'custom_testset', 'mcq')
QA_LOCAL_PATH = os.path.join(PROJECT_ROOT, 'data', 'custom_testset', 'qa')

# 数据集统计
mcq_files = [f for f in os.listdir(MCQ_LOCAL_PATH) if f.endswith('.csv')] if os.path.isdir(MCQ_LOCAL_PATH) else []
qa_files = [f for f in os.listdir(QA_LOCAL_PATH) if f.endswith('.jsonl')] if os.path.isdir(QA_LOCAL_PATH) else []

# ================================================================
# 2. 辅助函数：从 EvalScope reports 中提取分数
# ================================================================
def _load_report(report_dir, filename):
    """安全加载一个 report JSON"""
    json_path = os.path.join(report_dir, filename)
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def _find_metric(report, metric_name):
    """在 report 中查找指定名称的 metric 块"""
    for m in report.get('metrics', []):
        if m.get('name') == metric_name:
            return m
    return None


def extract_mcq_scores(report_dir, model_name):
    """从 MCQ report 提取按子集拆分的 mean_acc 分数"""
    scores = {}
    report = _load_report(report_dir, 'general_mcq.json')
    if not report:
        return scores

    metric = _find_metric(report, 'mean_acc')
    if not metric:
        return scores

    # 取第一个 category 下的 subsets
    categories = metric.get('categories', [])
    if categories:
        for sub in categories[0].get('subsets', []):
            scores[sub['name']] = sub['score']

    # 也保存总体分数
    scores['OVERALL'] = report.get('score', 0)
    return scores


def extract_qa_scores(report_dir, model_name):
    """从 QA report 提取按子集拆分的 Rouge-L-R 分数（主指标）"""
    scores = {}
    report = _load_report(report_dir, 'general_qa.json')
    if not report:
        return scores

    # 主指标：Rouge-L-R（EvalScope 默认的主分数）
    metric = _find_metric(report, 'mean_Rouge-L-R')
    if not metric:
        # 回退到 mean_bleu-1
        metric = _find_metric(report, 'mean_bleu-1')

    if metric:
        categories = metric.get('categories', [])
        if categories:
            for sub in categories[0].get('subsets', []):
                scores[sub['name']] = sub['score']
        scores['OVERALL'] = metric.get('score', 0)

    return scores


def collect_all_scores(outputs_dir, model_name, eval_type):
    """收集某个模型在某类评测下的所有分数（按子集拆分）"""
    model_output_dir = os.path.join(outputs_dir, model_name, eval_type)
    report_dir = os.path.join(model_output_dir, 'reports', model_name)
    if not os.path.isdir(report_dir):
        return {}

    if eval_type == 'mcq':
        return extract_mcq_scores(report_dir, model_name)
    elif eval_type == 'qa':
        return extract_qa_scores(report_dir, model_name)
    return {}


# ================================================================
# 3. 评测函数
# ================================================================
def run_mcq(model_config):
    """评测选择题 (general_mcq)"""
    print(f"\n  [MCQ] 选择题评测...")
    mcq_subsets = [f.replace('_val.csv', '') for f in mcq_files if f.endswith('_val.csv')]
    if not mcq_subsets:
        print("  ⚠ 未找到 MCQ 数据文件，跳过")
        return

    task_cfg = TaskConfig(
        model=model_config['model'],
        model_id=model_config['name'],
        api_url=model_config['api_url'],
        api_key=model_config['api_key'],
        eval_type='openai_api',
        datasets=['general_mcq'],
        dataset_args={
            'general_mcq': {
                'local_path': MCQ_LOCAL_PATH,
                'subset_list': mcq_subsets,
            }
        },
        generation_config=GENERATION_CONFIG,
        limit=None,
        eval_batch_size=1,
        timeout=120,
        stream=True,
        work_dir=os.path.join(OUTPUTS_DIR, model_config['name'], 'mcq'),
        no_timestamp=True,
    )
    run_task(task_cfg=task_cfg)
    return collect_all_scores(OUTPUTS_DIR, model_config['name'], 'mcq')


def run_qa(model_config):
    """评测问答题 (general_qa)"""
    print(f"\n  [QA] 问答题评测...")
    qa_subsets = [f.replace('.jsonl', '') for f in qa_files if f.endswith('.jsonl')]
    if not qa_subsets:
        print("  ⚠ 未找到 QA 数据文件，跳过")
        return

    task_cfg = TaskConfig(
        model=model_config['model'],
        model_id=model_config['name'],
        api_url=model_config['api_url'],
        api_key=model_config['api_key'],
        eval_type='openai_api',
        datasets=['general_qa'],
        dataset_args={
            'general_qa': {
                'local_path': QA_LOCAL_PATH,
                'subset_list': qa_subsets,
            }
        },
        generation_config=GENERATION_CONFIG,
        limit=None,
        eval_batch_size=1,
        timeout=120,
        stream=True,
        work_dir=os.path.join(OUTPUTS_DIR, model_config['name'], 'qa'),
        no_timestamp=True,
    )
    run_task(task_cfg=task_cfg)
    return collect_all_scores(OUTPUTS_DIR, model_config['name'], 'qa')


# ================================================================
# 4. 结果汇总 & 保存
# ================================================================
def format_markdown_table(all_mcq_scores, all_qa_scores, models_used):
    """将评测结果格式化为 Markdown 对比表"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    lines = []
    lines.append(f'# 评测结果汇总')
    lines.append(f'')
    lines.append(f'> 生成时间：{now}  |  模型数：{len(models_used)}  |  题量：MCQ {sum(len(v) for v in all_mcq_scores.values())} 组 + QA {sum(len(v) for v in all_qa_scores.values())} 组')
    lines.append(f'')

    # --- MCQ 对比表 ---
    if any(all_mcq_scores.values()):
        # 收集所有数据集名
        mcq_datasets = sorted(set().union(*[s.keys() for s in all_mcq_scores.values() if s]))
        lines.append('## 选择题 (MCQ)')
        lines.append('')
        header = ['模型'] + mcq_datasets
        lines.append('| ' + ' | '.join(header) + ' |')
        lines.append('|' + '|'.join([' --- '] * len(header)) + '|')
        for mc in models_used:
            name = mc['name']
            scores = all_mcq_scores.get(name, {})
            row = [name]
            for ds in mcq_datasets:
                s = scores.get(ds)
                row.append(f'{s:.2%}' if isinstance(s, (int, float)) else '-')
            lines.append('| ' + ' | '.join(row) + ' |')
        lines.append('')

    # --- QA 对比表 ---
    if any(all_qa_scores.values()):
        qa_datasets = sorted(set().union(*[s.keys() for s in all_qa_scores.values() if s]))
        lines.append('## 问答题 (QA)')
        lines.append('')
        header = ['模型'] + qa_datasets
        lines.append('| ' + ' | '.join(header) + ' |')
        lines.append('|' + '|'.join([' --- '] * len(header)) + '|')
        for mc in models_used:
            name = mc['name']
            scores = all_qa_scores.get(name, {})
            row = [name]
            for ds in qa_datasets:
                s = scores.get(ds)
                row.append(f'{s:.2%}' if isinstance(s, (int, float)) else '-')
            lines.append('| ' + ' | '.join(row) + ' |')
        lines.append('')

    # --- 综合排名 ---
    lines.append('## 综合排名（所有数据集平均分）')
    lines.append('')
    lines.append('| 排名 | 模型 | 平均分 |')
    lines.append('| --- | --- | --- |')
    avg_scores = []
    for mc in models_used:
        name = mc['name']
        all_s = []
        if name in all_mcq_scores:
            all_s.extend(all_mcq_scores[name].values())
        if name in all_qa_scores:
            all_s.extend(all_qa_scores[name].values())
        if all_s:
            avg_scores.append((name, sum(all_s) / len(all_s)))
    avg_scores.sort(key=lambda x: x[1], reverse=True)
    for i, (name, avg) in enumerate(avg_scores, 1):
        lines.append(f'| {i} | {name} | {avg:.2%} |')

    return '\n'.join(lines)


def print_terminal_table(all_mcq_scores, all_qa_scores, models_used):
    """在终端打印简洁的对比表"""
    sep = '=' * 70

    # MCQ 表
    mcq_datasets = sorted(set().union(*[s.keys() for s in all_mcq_scores.values() if s]))
    if mcq_datasets:
        print(f'\n{sep}')
        print('MCQ (选择题) 对比')
        print(sep)
        header = ['Model'] + mcq_datasets
        col_widths = [max(20, len(h) + 2) for h in header]
        fmt = '  '.join(f'{{:<{w}}}' for w in col_widths)
        print(fmt.format(*header))
        print('  '.join('-' * w for w in col_widths))
        for mc in models_used:
            name = mc['name']
            scores = all_mcq_scores.get(name, {})
            row = [name] + [f'{scores.get(ds):.2%}' if scores.get(ds) is not None else '  -  ' for ds in mcq_datasets]
            print(fmt.format(*row))

    # QA 表
    qa_datasets = sorted(set().union(*[s.keys() for s in all_qa_scores.values() if s]))
    if qa_datasets:
        print(f'\n{sep}')
        print('QA (问答题) 对比')
        print(sep)
        header = ['Model'] + qa_datasets
        col_widths = [max(20, len(h) + 2) for h in header]
        fmt = '  '.join(f'{{:<{w}}}' for w in col_widths)
        print(fmt.format(*header))
        print('  '.join('-' * w for w in col_widths))
        for mc in models_used:
            name = mc['name']
            scores = all_qa_scores.get(name, {})
            row = [name] + [f'{scores.get(ds):.2%}' if scores.get(ds) is not None else '  -  ' for ds in qa_datasets]
            print(fmt.format(*row))


# ================================================================
# 5. 主流程
# ================================================================
if __name__ == '__main__':
    now = datetime.now()
    print('=' * 70)
    print(f'Full Benchmark — Custom Testset')
    print(f'Time: {now.strftime("%Y-%m-%d %H:%M")}  |  Models: {len(MODELS)}')
    print(f'MCQ files: {len(mcq_files)}  |  QA files: {len(qa_files)}')
    print('=' * 70)

    # --- 筛选有效模型（有 API key 的才跑） ---
    active_models = []
    for mc in MODELS:
        if mc['api_key']:
            active_models.append(mc)
            print(f'  [OK] {mc["name"]} — key loaded from .env ({mc["api_key_env"]})')
        else:
            print(f'  [SKIP] {mc["name"]} — .env missing {mc["api_key_env"]}')

    if not active_models:
        print('\nNo models with valid API keys. Abort.')
        sys.exit(1)

    # --- 逐模型评测 ---
    all_mcq_scores = {}
    all_qa_scores = {}

    for mc in active_models:
        model_name = mc['name']
        print(f'\n{"=" * 70}')
        print(f'>> Evaluating: {model_name}')
        print(f'{"=" * 70}')

        try:
            mcq_scores = run_mcq(mc)
            all_mcq_scores[model_name] = mcq_scores
            for ds, s in mcq_scores.items():
                print(f'     {ds}: {s:.2%}')
        except Exception as e:
            print(f'  [FAIL] MCQ: {e}')
            all_mcq_scores[model_name] = {}

        try:
            qa_scores = run_qa(mc)
            all_qa_scores[model_name] = qa_scores
            for ds, s in qa_scores.items():
                print(f'     {ds}: {s:.2%}')
        except Exception as e:
            print(f'  [FAIL] QA: {e}')
            all_qa_scores[model_name] = {}

    # --- 终端输出对比表 ---
    print_terminal_table(all_mcq_scores, all_qa_scores, active_models)

    # --- 保存 Markdown 报告 ---
    md_content = format_markdown_table(all_mcq_scores, all_qa_scores, active_models)
    md_path = os.path.join(OUTPUTS_DIR, f'benchmark_summary_{now.strftime("%Y%m%d_%H%M")}.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    # 同时保存 JSON（机器可读）
    json_path = os.path.join(OUTPUTS_DIR, f'benchmark_summary_{now.strftime("%Y%m%d_%H%M")}.json')
    json_data = {
        'time': now.isoformat(),
        'models': [m['name'] for m in active_models],
        'mcq_scores': all_mcq_scores,
        'qa_scores': all_qa_scores,
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    print(f'\n{"=" * 70}')
    print(f'Results saved:')
    print(f'  Markdown: {md_path}')
    print(f'  JSON:     {json_path}')
    print(f'{"=" * 70}')
