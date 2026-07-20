# LLM 评测项目 (llm-eval-project)

> 国产大模型评测与 RAG 优化 — 一键 Pipeline · 7 维指标 · Error Bucket · CI/CD

## 一键评测

```bash
python run_pipeline.py              # 全量评测 + 报告 + 仪表板
python run_pipeline.py --tier smoke  # 快速验证（7题，CI用）
```

流水线自动执行: RAG KB → 评测 → Judge → 扩展指标 → A/B Test → Error Bucket → Badcase收集 → AI洞察 → 仪表板 → 回归检测

输出全部集中在 `results/latest/`：5 份报告 + 1 个交互式仪表板
仪表板在线: https://hllwld.github.io/llm-eval-project/dashboard.html

## 评测能力矩阵

| 能力 | 脚本 | 说明 |
|------|------|------|
| 统一评测 | `final_eval.py` | 64题, MCQ+QA推理+代码, Base/RAG双模 |
| 扩展指标 | `extended_metrics.py` | JSON格式率 + 工具调用成功率 |
| A/B Test | `ab_test.py` | p-value + 95% CI + 成本对比 + 排行榜 |
| Error Bucket | `error_bucket.py` | LLM自动11类错误分桶 |
| Badcase 收集 | `collect_badcases.py` | 自动筛选低分样本 + 分类入库 |
| AI 洞察 | `insight_generator.py` | LLM 自动分析数据生成结论 |
| Prompt Benchmark | `prompt_benchmark.py` | 多Prompt变体对比 (Accuracy/Cost/Latency/Hallu) |
| 可视化仪表板 | `build_viz.py` | Chart.js 交互式 HTML (8张图表) |
| 回归检测 | `regression_check.py` | 正确率告警 + Token趋势 + 版本锁定 |
| 安全对抗 | `security_eval.py` | 越狱/诱导/拒答检测 |
| 前置校验 | `precheck.py` | 测试集三级质量校验 |

## 目录结构

```
llm-eval-project/
├── run_pipeline.py                    # 一键评测入口
├── README.md
├── config/model_config.yaml           # 模型配置 (支持 active:false)
├── .github/workflows/ci.yml           # CI/CD (smoke on push)
│
├── scripts/
│   ├── final_eval.py                  # 统一评测 (MCQ + QA + Judge)
│   ├── extended_metrics.py            # JSON格式率 + 工具调用成功率
│   ├── ab_test.py                     # A/B Test (p-value + 成本)
│   ├── error_bucket.py                # Error Bucket 错误分类
│   ├── prompt_benchmark.py            # Prompt 变体对比
│   ├── build_viz.py                   # HTML 仪表板
│   ├── rag_retriever.py / rag_prompt_builder.py  # RAG 检索+重组
│   ├── llm_as_judge.py                # LLM-as-Judge (1-5分)
│   ├── rag_eval.py / rag_benchmark.py / rag_compare.py / rag_analysis.py  # RAG分析套件
│   ├── rag_inference.py               # RAG 推理管道
│   ├── regression_check.py            # 回归检测 (告警+趋势)
│   ├── security_eval.py               # 安全对抗评测
│   ├── precheck.py                    # 前置校验
│   ├── generate_testset.py            # 测试集生成
│   └── reports/                       # 所有评测报告 MD
│
├── data/
│   ├── custom_testset/
│   │   ├── CHANGELOG.md               # 测试集版本变更日志
│   │   ├── mcq/ (CSV) + qa/ (JSONL)   # 64题 (含 tier: smoke/full)
│   │   └── metadata.yaml
│   ├── knowledge_base/
│   │   ├── reasoning_steps.jsonl      # 推理知识库 (15条)
│   │   └── code_templates.jsonl       # 代码知识库 (10条)
│   ├── badcases/                      # Badcase 数据
│   └── reports/                       # 分析报告
│
├── results/                           # 报告输出 (每次运行归档，gitignore)
│   └── latest/                        # 最新结果快捷访问
├── outputs/                           # 中间数据 (gitignore)
└── chroma_db/                         # 向量库 (gitignore)
```

## 测试集 (v4, 72题)

| 子集 | 题数 | 指标 | Smoke |
|------|------|------|-------|
| 知识 MCQ | 20 | Accuracy | 2 |
| 安全 MCQ | 8 | Accuracy | 1 |
| 推理 QA | 15 | ROUGE-L + Judge | 2 |
| 代码 QA | 10 | ROUGE-L + Judge | 1 |
| JSON 格式 | 5 | JSON 格式正确率 | 1 |
| 工具调用 | 6 | 工具调用成功率 | 1 |
| 安全对抗 | 8 | PASS/WARN/FAIL | 1 |

## 快速开始

```bash
pip install -r requirements.txt

# 快速验证 (7题, ~2分钟)
python run_pipeline.py --tier smoke

# 全量评测 (64题, 含所有报告)
python run_pipeline.py
```

## 技术栈

- **评测框架**: Python final_eval.py + LLM-as-Judge
- **向量数据库**: ChromaDB + BAAI/bge-small-zh-v1.5
- **模型 API**: DeepSeek / Qwen / GLM
- **指标**: Accuracy / ROUGE-L / LLM Judge / Latency / Tokens (Cost) / 拒答率 / 幻觉率 / JSON 格式率 / 工具调用成功率
- **CI/CD**: GitHub Actions — push 自动 smoke，手动触发 full

---

*创建时间: 2026-06-22 | 更新: 2026-07-17*
