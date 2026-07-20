# CLAUDE.md

> ⚠️ **重要规则**:
> - 任何代码改动前，先向用户说明改动方案并征得同意，不要直接修改代码。
> - Git 提交备注使用中文。

## 项目概述

大模型评测与 RAG 优化实战项目。对 DeepSeek-V3(V4-Flash)/V4-Pro、Qwen-Plus、GLM-5.2 四个国产模型进行系统性评测，72 题自建测试集 v4.0（含 64 题主测试集 + 8 题安全对抗），支持 RAG 增强 + LLM-as-Judge + CI/CD。

## 一键评测

```bash
python run_pipeline.py              # 全量 (10步, ~33min)
python run_pipeline.py --tier smoke  # 快速验证 (7题, ~2min)
```

流水线 (10步): KB Init → final_eval → extended_metrics → security_eval → ab_test → error_bucket → collect_badcases → insight_generator → build_viz → regression_check

报告输出: `results/latest/` (5份 MD + dashboard.html + raw_responses.json)

## 目录结构

```
llm-eval-project/
├── run_pipeline.py                    # 一键评测入口
├── config/model_config.yaml           # 模型配置 (active:false 跳过)
├── .github/workflows/ci.yml           # CI/CD (push→smoke, 手动→full)
├── data/
│   ├── custom_testset/                # 72题 v4.0 (含 CHANGELOG.md)
│   │   ├── mcq/ (CSV) + qa/ (JSONL)   # tier: smoke/full 标签
│   │   └── metadata.yaml
│   └── knowledge_base/
│       ├── reasoning_steps.jsonl      # 推理知识库 15条
│       └── code_templates.jsonl       # 代码知识库 10条
├── scripts/                           # 20个核心脚本
│   ├── final_eval.py                  # 统一评测 (MCQ+QA, Base/RAG双模)
│   ├── extended_metrics.py            # JSON格式率 + 工具调用成功率
│   ├── security_eval.py               # 安全对抗评测
│   ├── ab_test.py                     # A/B Test (p-value + cost + CI)
│   ├── error_bucket.py                # Error Bucket 12类自动分桶
│   ├── collect_badcases.py            # 自动收集 Badcase
│   ├── insight_generator.py           # AI 洞察生成 (LLM分析)
│   ├── prompt_benchmark.py            # Prompt变体对比 + 自动推荐
│   ├── regression_check.py            # 回归检测 + Token趋势 + 版本锁定
│   ├── build_viz.py                   # Chart.js 8图仪表板
│   ├── rag_retriever.py / rag_prompt_builder.py  # RAG 检索+重组
│   ├── rag_inference.py               # RAG 推理
│   ├── llm_as_judge.py                # LLM-as-Judge 1-5分
│   ├── rag_eval.py / rag_benchmark.py / rag_compare.py / rag_analysis.py  # RAG分析套件
│   ├── precheck.py                    # 评测前置校验
│   ├── generate_testset.py            # 测试集生成
│   └── reports/                       # 报告模板
├── results/                           # 评测报告产出 (gitignore)
│   └── latest/                        # 最新结果快捷访问
├── outputs/                           # 中间数据 (gitignore)
└── chroma_db/                         # 向量库 (gitignore)
```

## 测试集 (v4, 72题)

| 子集 | 题数 | 指标 | Smoke题 |
|------|------|------|---------|
| 知识 MCQ | 20 | Accuracy | 2 |
| 安全 MCQ | 8 | Accuracy | 1 |
| 推理 QA | 15 | ROUGE-L + Judge (Base+RAG) | 2 |
| 代码 QA | 10 | ROUGE-L + Judge (Base+RAG) | 1 |
| JSON 格式 | 5 | JSON 格式正确率 | 1 |
| 工具调用 | 6 | 工具调用成功率 | 1 |
| 安全对抗 | 8 | PASS/WARN/FAIL | 1 |

## 7 维指标体系

Accuracy | Latency | Tokens (Cost) | 拒答率 | 幻觉率 | JSON 格式率 | 工具调用成功率

## RAG 效果

| 子集 | Base Judge | RAG Judge | 变化 |
|------|-----------|-----------|------|
| 推理 | 4.55~4.98 | **5.00** (全员满分) | +0.02~+0.45 |
| 代码 | 3.70~5.00 | 3.70~4.00 | 多数下降，噪声大于帮助 |
| 检索精度 | — | 15/15 Precision@1 | 100% |

## 关键发现

- **Rouge-L 不适合结构化问答**: RAG 输出变长导致 Rouge 反降 15pp，LLM Judge 反证质量提升
- **安全知识 ≠ 安全能力**: MCQ 全员满分，对抗测试各模型 25~88% 通过率差异大
- **V4-Pro 无显著优势**: 综合分与 V4-Flash 持平 (0.631)，仅安全对抗领先
- **代码 RAG 效果有限**: 四模型中三个 Judge 下降 (GLM-5.2: 5.00→4.00)，知识库噪声大于帮助
- **工具调用全模型 100%**: 正向5题全部 PASS，反向测试部分模型误调
- **GLM-5.2 延迟极高**: 12226ms（V3仅3526ms），但JSON格式率80%最高

## 环境

- **Python**: conda activate evalscope
- **API Key**: .env (DEEPSEEK_API_KEY / BAILIAN_API_KEY / ZHIPU_API_KEY)
- **关键依赖**: chromadb, sentence-transformers, rouge-score, openai, pyyaml, python-docx
- **CI/CD**: GitHub Actions, Secrets 需配 3 个 API Key
