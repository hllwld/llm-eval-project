# LLM 评测项目 (llm-eval-project)

> 基于 EvalScope 的多模型、多数据集对比评测与 Badcase 分析项目

## 项目目标

1. 验证 EvalScope 框架在多场景下的评测能力
2. 对国产主流 LLM (DeepSeek-V3, Qwen-Plus, GLM-4-Plus, Qwen2.5-VL) 进行多数据集基线对比
3. 建立 Badcase 分类体系与分析流程
4. 积累可复用的评测自动化脚本

## 目录结构

```
llm-eval-project/
├── README.md                          # 项目总览（本文档）
├── requirements.txt                   # 依赖清单
├── .env                               # API Key 配置（不提交版本控制）
│
├── config/
│   └── model_config.yaml              # 模型参数 + 数据集配置
│
├── docs/
│   └── rag_architecture.md            # RAG 优化方案技术架构（Day 13-17）
│
├── scripts/                           # 核心评测脚本
│   ├── quickstart.py                  # EvalScope 环境验证
│   ├── yaml_eval.py                   # YAML 配置驱动评测
│   ├── multi_model_benchmark.py       # 多模型对比 + Badcase 收集（标准数据集）
│   ├── badcase_classifier.py          # Badcase 三级标签分类（旧数据集）
│   ├── build_viz.py                   # 生成可视化仪表板
│   ├── generate_testset.py            # 生成自定义测试集 (50 题)
│   ├── run_full_benchmark.py          # 自定义测试集 × 全部模型 完整评测
│   ├── extract_custom_badcases.py     # 从 review 文件中提取 Badcase
│   ├── label_custom_badcases.py       # 自动标注 Badcase 标签
│   ├── badcase_report.py              # 生成 Badcase 分析报告
│   ├── full_benchmark.py              # v2 自定义测试集全量评测（读外部配置）
│   ├── precheck.py                    # 评测前置校验（规则扫描+LLM自检）
│   ├── visualize.py                   # 生成可视化图表+HTML仪表板
│   │
│   └── reports/                       # 脚本对应的评测/分析报告
│       ├── quickstart_report.md        # ↳ 环境验证报告
│       ├── yaml_eval_report.md         # ↳ YAML 配置评测报告
│       ├── multi_model_benchmark_report.md   # ↳ 多模型对比报告
│       ├── badcase_classifier_report.md      # ↳ Badcase 分类分析
│       ├── generate_testset_report.md        # ↳ 测试集 v2 题目清单
│       ├── run_full_benchmark_report.md      # ↳ 自定义评测结果
│       ├── full_benchmark_report.md          # ↳ v2 分难度评测报告
│       ├── precheck_report.md                # ↳ 前置校验说明
│       ├── visualize_report.md               # ↳ 可视化图表说明
│       ├── extract_custom_badcases_report.md # ↳ Badcase 提取说明
│       ├── label_custom_badcases_report.md   # ↳ 自动标注规则
│       └── badcase_report_report.md          # ↳ 分析报告说明
│
├── data/
│   ├── custom_testset/                # 自定义测试集
│   │   ├── metadata.yaml              # 测试集元数据
│   │   ├── mcq/                       # 选择题 (CSV, EvalScope general_mcq 格式)
│   │   ├── qa/                        # 问答题 (JSONL, EvalScope general_qa 格式)
│   │   └── knowledge_qa_all.json      # 全部 25 道选择题 + 解析
│   ├── badcases/
│   │   ├── badcases_raw.json          # 旧数据集 Badcase (14 条)
│   │   ├── custom_badcases_raw.json   # 自定义数据集 Badcase (9 条)
│   │   └── custom_badcases_labeled.json  # 标注后的 Badcase
│   └── reports/
│       ├── week1_briefing.md          # 第一周综合分析
│       └── badcase_analysis.md        # 自定义测试集 Badcase 分析报告
│
├── outputs/                           # EvalScope 运行输出
│   ├── {模型名}/mcq/                  # 选择题评测结果
│   ├── {模型名}/qa/                   # 问答题评测结果
│   ├── benchmark_summary_*.md         # 评测汇总 Markdown
│   ├── benchmark_summary_*.json       # 评测汇总 JSON
│   └── dashboard.html                 # 可视化仪表板
│
└── notebooks/                         # Jupyter 分析
```

## 评测结果速览

### 标准数据集 (gsm8k / arc / hellaswag)

| 模型 | gsm8k | arc | hellaswag |
| --- | --- | --- | --- |
| DeepSeek-V3 | 100.00% | 95.00% | 75.00% |
| Qwen-Plus | 100.00% | 95.00% | 85.00% |
| GLM-4-Plus | 95.00% | 90.00% | 45.00% |

### 自定义测试集 (MCQ 选择题)

| 模型 | 知识 (20题) | 安全 (5题) | 总分 |
| --- | --- | --- | --- |
| DeepSeek-V3 | 100.00% | 100.00% | **100.00%** |
| Qwen-Plus | 100.00% | 100.00% | **100.00%** |
| Qwen2.5-VL | 100.00% | 100.00% | **100.00%** |
| GLM-4-Plus | 95.00% | 100.00% | **96.00%** |

### 自定义测试集 (QA 问答题, Rouge-L-R)

| 模型 | 代码 (10题) | 推理 (15题) | 总分 |
| --- | --- | --- | --- |
| GLM-4-Plus | 53.69% | 66.46% | **61.35%** |
| DeepSeek-V3 | 54.44% | 62.21% | **59.10%** |
| Qwen-Plus | 56.53% | 59.27% | **58.17%** |
| Qwen2.5-VL | 54.76% | 57.62% | **56.48%** |

### v2 测试集（难度标签 + 输出约束）

| 模型 | 知识 | 安全 | 推理 | 代码 | **综合** |
| --- | --- | --- | --- | --- | --- |
| DeepSeek-V3 | 100% | 100% | 53.88% | 58.10% | **77.99%** |
| Qwen2.5-VL | 100% | 100% | 40.58% | 56.11% | **74.17%** |
| GLM-4-Plus | 95% | 100% | 43.51% | 53.41% | **72.98%** |
| Qwen-Plus | 100% | 100% | 31.27% | 57.18% | **72.11%** |

> 详细分析见 `scripts/reports/` 下各 `*_report.md` 和 `data/reports/`

## 快速开始

```bash
pip install -r requirements.txt
cd llm-eval-project

# 1. 生成自定义测试集
python scripts/generate_testset.py

# 2. 前置校验（评测前先检查测试集质量）
python scripts/precheck.py

# 3. 运行完整评测（v2 含难度分层）
python scripts/full_benchmark.py

# 4. 生成可视化图表
python scripts/visualize.py

# 5. Badcase 分析流程
python scripts/extract_custom_badcases.py
python scripts/label_custom_badcases.py
python scripts/badcase_report.py

# 旧版脚本（标准数据集）
python scripts/quickstart.py
python scripts/multi_model_benchmark.py
```

## 技术栈

- **评测框架**：EvalScope v1.8.1
- **评测后端**：Native (OpenAI API 兼容)
- **模型 API**：DeepSeek / 阿里云百炼 (Qwen) / 智谱 GLM
- **评估指标**：Accuracy (MCQ) / BLEU + Rouge (QA)

---

*创建时间：2026-07-07 | 更新：2026-07-10*
