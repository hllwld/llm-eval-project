# YAML 配置驱动 DeepSeek 评测报告

## 概述

- **脚本**：`yaml_eval.py`
- **目标**：从 YAML 配置加载模型参数，通过 DeepSeek API 进行单模型评测
- **API 来源**：项目根目录 `.env`（`DEEPSEEK_API_KEY`）
- **配置来源**：`config/model_config.yaml`

## 评测参数

| 项目 | 值 |
|------|-----|
| 目标模型 | DeepSeek-V3 (deepseek-chat) |
| API 端点 | `https://api.deepseek.com/v1/chat/completions` |
| 数据集 | gsm8k + arc |
| 每题限额 | 10 条 |
| temperature | 0.3 |
| max_tokens | 1024 |
| top_p | 0.9 |

## 代码实现

```python
with open('../config/model_config.yaml', 'r') as f:
    config = yaml.safe_load(f)
model = config['models'][0]  # DeepSeek-V3
api_key = os.getenv('DEEPSEEK_API_KEY')

task_cfg = {
    'model': 'deepseek-chat',
    'model_id': 'DeepSeek-V3',
    'api_url': 'https://api.deepseek.com/v1/chat/completions',
    'api_key': api_key,
    'eval_type': 'openai_api',
    'datasets': ['gsm8k', 'arc'],
    'limit': 10,
    'generation_config': {'temperature': 0.3, 'max_tokens': 1024, 'top_p': 0.9},
}
run_task(task_cfg=task_cfg)
```

## 与 evalscope 原方案对比

| 维度 | evalscope (旧) | llm-eval-project (新) |
|------|--------------|----------------------|
| 密钥存储 | `config/apikey.yaml` | 项目根目录 `.env` |
| 配置格式 | 单文件 config.yaml | `config/model_config.yaml`（多模型共用） |
| 加载方式 | 手动 open + yaml.safe_load | 同上，增加了 `python-dotenv` 自动加载 `.env` |
| 扩展性 | 一个模型一份配置 | model_config 中定义多模型列表，脚本按需取用 |

## 评测结果（2026-07-07 13:29）

| 数据集 | 子集 | 样本数 | 准确率 |
|--------|------|--------|--------|
| gsm8k | main | 10 | **100.00%** |
| arc | ARC-Easy | 10 | 100.00% |
| arc | ARC-Challenge | 10 | 90.00% |
| arc | OVERALL | 20 | 95.00% |

**性能指标**：

| 数据集 | 样本数 | 平均延迟 | 吞吐量 |
|--------|--------|----------|--------|
| gsm8k | 10 | 1.66s | 86.96 tok/s |
| arc | 20 | 1.11s | 14.92 tok/s |

> temperature=0.3, max_tokens=1024 参数下 DeepSeek-V3 表现优异。

---

*运行 `python yaml_eval.py` 生成完整评测结果*
