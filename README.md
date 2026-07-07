# LLM 评测项目 (llm-eval-project)

> 基于 EvalScope 的多模型、多数据集对比评测与 Badcase 分析项目

## 项目目标

1. 验证 EvalScope 框架在多场景下的评测能力
2. 对国产主流 LLM (DeepSeek-V3, Qwen-Plus, GLM-4-Plus) 进行多数据集基线对比
3. 建立 Badcase 分类体系与分析流程
4. 积累可复用的评测自动化脚本

## 目录结构

```
llm-eval-project/
├── README.md                    # 项目总览（本文档）
├── requirements.txt             # 依赖清单
├── .env                         # API Key 配置（不提交版本控制）
│
├── config/
│   └── model_config.yaml        # 模型参数 + 数据集配置
│
├── scripts/                     # 核心脚本 + 详细说明
│   ├── quickstart.py            # EvalScope 环境验证
│   ├── quickstart_report.md     # ↳ 评测报告
│   ├── yaml_eval.py             # YAML 配置驱动评测
│   ├── yaml_eval_report.md      # ↳ 评测报告
│   ├── multi_model_benchmark.py # 多模型对比 + Badcase 收集
│   ├── multi_model_benchmark_report.md  # ↳ 评测报告
│   ├── badcase_classifier.py    # Badcase 三级标签分类
│   └── badcase_classifier_report.md     # ↳ 分析报告
│
├── data/
│   ├── raw/                     # 原始评测输出
│   ├── badcases/
│   │   └── badcases_raw.json    # Badcase 数据（14 条）
│   └── reports/
│       └── week1_briefing.md    # 综合分析报告
│
├── outputs/                     # EvalScope 运行输出
└── notebooks/                   # Jupyter 分析
```

## 快速开始

```bash
pip install -r requirements.txt
cd scripts
python quickstart.py             # 环境验证
python yaml_eval.py              # DeepSeek 单模型
python multi_model_benchmark.py  # 三模型对比
python badcase_classifier.py     # Badcase 分析
```

## 评测结果速览

| 模型 | gsm8k | arc | hellaswag |
| --- | --- | --- | --- |
| DeepSeek-V3 | 100.00% | 95.00% | 75.00% |
| Qwen-Plus | 100.00% | 95.00% | 85.00% |
| GLM-4-Plus | 95.00% | 90.00% | 45.00% |

> 详细分析见 `scripts/` 下各 `*_report.md` 和 `data/reports/week1_briefing.md`

## 技术栈

- **评测框架**：EvalScope v1.8.1
- **评测后端**：Native (OpenAI API 兼容)
- **模型 API**：DeepSeek / 阿里云百炼 / 智谱 GLM

---

*创建时间：2026-07-07*