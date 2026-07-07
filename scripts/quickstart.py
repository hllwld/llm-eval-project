# quickstart.py — EvalScope 环境验证与模型对比
"""
对应 evalscope/01_quickstart: CLI 快速入门
对应 evalscope/02_yaml_config 方式1&2: 循环对比模型 + 多数据集组合

改为走 DeepSeek API（比本地推理快 10x+），3B 已注释避免超时。
"""

import os
from dotenv import load_dotenv
from evalscope.run import run_task

# 自动加载项目根目录的 .env 文件
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

API_URL = 'https://api.deepseek.com/v1/chat/completions'
API_KEY = os.getenv('DEEPSEEK_API_KEY', '')

# ========== Quickstart: CLI 命令等价（API 模式） ==========
# 原 CLI: evalscope eval --model Qwen/Qwen2.5-0.5B-Instruct --datasets gsm8k arc --limit 5
# 改为走 DeepSeek API，速度从 30s/条 提升到 ~3s/条

task_cfg_quick = {
    'model': 'deepseek-chat',
    'model_id': 'DeepSeek-Quickstart',
    'api_url': API_URL,
    'api_key': API_KEY,
    'eval_type': 'openai_api',
    'datasets': ['gsm8k', 'arc'],
    'limit': 5,
}
run_task(task_cfg=task_cfg_quick)

# ========== 循环对比不同尺寸模型（API 模式） ==========
# 用 model_id 区分报告中的模型名，实际都走 DeepSeek API（纯流程演示）
models_to_try = [
    {'model': 'deepseek-chat', 'name': 'DeepSeek-V3'},
    {'model': 'deepseek-chat', 'name': 'DeepSeek-V3-低温度'},
    # {'model': 'deepseek-chat', 'name': 'DeepSeek-V3-高温度'},  # 3B 太慢，已注释
]

for m in models_to_try:
    print(f"\n{'='*50}")
    print(f"评测模型: {m['name']}")
    print(f"{'='*50}")
    task_cfg = {
        'model': m['model'],
        'model_id': m['name'],
        'api_url': API_URL,
        'api_key': API_KEY,
        'eval_type': 'openai_api',
        'datasets': ['gsm8k'],
        'limit': 5,
        'generation_config': {'temperature': 0.3},
    }
    run_task(task_cfg=task_cfg)

# ========== 多数据集组合评测（已注释） ==========
# task_cfg_multi = {
#     'model': 'deepseek-chat',
#     'model_id': 'DeepSeek-多数据集',
#     'api_url': API_URL, 'api_key': API_KEY, 'eval_type': 'openai_api',
#     'datasets': ['gsm8k', 'arc', 'hellaswag'],
#     'limit': 5,
# }
# run_task(task_cfg=task_cfg_multi)