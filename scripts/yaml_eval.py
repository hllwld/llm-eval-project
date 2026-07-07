# yaml_eval.py — YAML 配置驱动的单模型 DeepSeek 评测
"""
对应 evalscope/02_yaml_config:
  - 从 YAML 文件加载配置
  - 自定义生成参数
  - API Key 从 .env 读取（替代 apikey.yaml）
"""

import os
import yaml
from dotenv import load_dotenv
from evalscope.run import run_task

# 自动加载项目根目录的 .env 文件
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

# ========== 加载配置 ==========
with open('../config/model_config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 取第一个模型（DeepSeek-V3）做单模型评测
model = config['models'][0]
api_key = os.getenv(model.get('api_key_env', ''), '')

# ========== 自定义生成参数 ==========
task_cfg = {
    'model': model['model_id'],
    'model_id': model['name'],
    'api_url': model['api_url'],
    'api_key': api_key,
    'eval_type': 'openai_api',
    'datasets': ['gsm8k', 'arc'],
    'limit': 10,
    'generation_config': {
        'temperature': 0.3,
        'max_tokens': 1024,
        'top_p': 0.9,
    },
}

run_task(task_cfg=task_cfg)