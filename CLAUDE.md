# CLAUDE.md

## 项目概述

大模型评测与 RAG 优化实战项目。对 DeepSeek-V3(V4-Flash)/V4-Pro、Qwen-Plus、GLM-4-Plus 四个国产模型进行系统性评测，覆盖 53 题自建测试集 + 3 组公开数据集，并通过 RAG 知识库增强推理能力。

## 目录结构

```
llm-eval-project/
├── config/
│   └── model_config.yaml          # 模型列表 + API 配置（支持 active:false 跳过）
├── data/
│   ├── custom_testset/            # 自建测试集 v4（53题 + 安全对抗8题）
│   │   ├── mcq/                   # 选择题 CSV: knowledge(20)+security(8)，全5选项
│   │   ├── qa/                    # 问答题 JSONL: reasoning(15)+code(10)+security_adv(8)
│   │   └── metadata.yaml          # 版本 / 难度分布
│   └── knowledge_base/
│       └── reasoning_steps.jsonl  # 15条推理题解题步骤（ChromaDB 源文件）
├── scripts/
│   ├── final_eval.py              # 最终统一评测（全53题×全模型，MCQ+QA双指标）
│   ├── full_benchmark.py          # v4批量评测（Accuracy+Rouge-L-R，读外部配置）
│   ├── precheck.py                # 评测前置校验（选项熵/弱模型探测/LLM自检）
│   ├── security_eval.py           # 安全对抗评测（越狱/诱导/拒答检测）
│   ├── generate_testset.py        # 生成自定义测试集
│   ├── rag_retriever.py           # ChromaDB+BGE向量检索（15/15 Precision@1）
│   ├── rag_prompt_builder.py      # 检索结果→Prompt重组
│   ├── rag_inference.py           # RAG推理管道（检索→重组→API）
│   ├── rag_eval.py                # RAG单模型对比（格式/步骤/正确性）
│   ├── rag_benchmark.py           # RAG三模型全量评测
│   ├── rag_compare.py             # Base vs RAG三模型分析
│   ├── rag_analysis.py            # RAG逐条对比分析
│   ├── llm_as_judge.py            # LLM-as-Judge独立评分（1-5分制）
│   ├── build_viz.py               # HTML仪表板
│   ├── visualize.py               # matplotlib四维图表
│   └── reports/                   # 所有评测报告MD（对应脚本说明）
├── outputs/                       # EvalScope日志 + bench输出（gitignore）
├── chroma_db/                     # ChromaDB向量库（gitignore，可由JSONL重建）
├── docs/rag_architecture.md       # RAG技术架构蓝图
├── .env                           # API Key（gitignore）
└── README.md                      # 项目总览
```

## 核心数据

### 测试集（53题 + 安全对抗8题）

| 子集 | 条数 | 指标 | 当前最优 |
|------|------|------|---------|
| 知识 MCQ | 20 | Accuracy | Qwen 100% |
| 安全 MCQ | 8 | Accuracy | 全部 100% |
| 推理 QA | 15 | Rouge-L / LLM Judge | GLM Base 56% / RAG后Judge全满分 |
| 代码 QA | 10 | Rouge-L / LLM Judge | GLM 45.8% |
| 安全对抗 | 8 | 拒答关键词检测 | DeepSeek/Qwen 50%, GLM 25% |

### RAG 效果（推理子集）

| 指标 | Base | RAG | 提升 |
|------|------|-----|------|
| LLM Judge Format | 3.80~5.00 | **5.00** | 格式规范化 |
| LLM Judge Step | 4.00~5.00 | **5.00** | 步骤完整性 |
| LLM Judge Overall | 4.25~5.00 | **5.00** | 综合满分 |
| Rouge-L | 32~56% | 34~41% | 反而下降（已知误判） |

### 关键结论

- **Rouge-L 会误判**：RAG 使输出结构化变长，n-gram 重叠降低，但 LLM Judge 确认质量提升
- **RAG 统一格式**：所有模型 RAG 模式下 Judge 均达 5.00/5
- **代码子集不适用 RAG**：知识库仅有推理步骤，代码题无提升
- **安全知识≠安全能力**：MCQ 安全题全满分，但对抗测试 GLM 仅 25% 通过
- **V4-Pro 无明显优势**：在现有测试集上与 V4-Flash 几乎持平

## 评测流水线

```
precheck.py → final_eval.py → visualize.py → build_viz.py
(前置校验)   (全量53题)     (图表)        (仪表板)
```

快速评测（仅推理子集 RAG 对比）：
```
python scripts/rag_inference.py    # 单模型
python scripts/rag_benchmark.py    # 三模型
python scripts/rag_compare.py      # 对比分析
```

## 环境与配置

- **Python 环境**: conda activate evalscope
- **API Key**: .env 文件（DEEPSEEK_API_KEY / BAILIAN_API_KEY / ZHIPU_API_KEY）
- **模型配置**: config/model_config.yaml（active: false 可跳过不用的模型）
- **关键依赖**: evalscope, chromadb, sentence-transformers, rouge-score, openai, pyyaml, matplotlib
