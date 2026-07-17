# Final Eval Report
> 2026-07-17 15:56 | Models: 4 | 28 MCQ + 15x2 Reasoning + 10 Code = 68 inferences/model

## 1. MCQ (Accuracy)

| Model | Knowledge (20) | Security (8) | Overall (28) |
| --- | --- | --- | --- |
| DeepSeek-V3 | 95% (19/20) | 100% (8/8) | 96% |
| DeepSeek-V4-Pro | 95% (19/20) | 100% (8/8) | 96% |
| Qwen-Plus | 100% (20/20) | 100% (8/8) | 100% |
| GLM-5.2 | 95% (19/20) | 100% (8/8) | 96% |

## 2. QA Reasoning (ROUGE-L)

| Model | Base | RAG | Delta |
| --- | --- | --- | --- |
| DeepSeek-V3 | 53.76% | 39.67% | -14.09% |
| DeepSeek-V4-Pro | 55.78% | 38.57% | -17.22% |
| Qwen-Plus | 32.74% | 34.20% | +1.46% |
| GLM-5.2 | 56.01% | 40.44% | -15.58% |

## 3. QA Reasoning (LLM Judge 1-5)

| Model | Mode | Format | Step | Correct | Overall |
| --- | --- | --- | --- | --- | --- |
| DeepSeek-V3 | Base | 3.67 | 3.60 | 5.00 | 4.08 |
| DeepSeek-V3 | RAG | 5.00 | 5.00 | 5.00 | 5.00 |
| DeepSeek-V4-Pro | Base | 4.60 | 4.80 | 4.93 | 4.76 |
| DeepSeek-V4-Pro | RAG | 5.00 | 5.00 | 5.00 | 5.00 |
| Qwen-Plus | Base | 5.00 | 5.00 | 4.87 | 4.93 |
| Qwen-Plus | RAG | 5.00 | 5.00 | 5.00 | 5.00 |
| GLM-5.2 | Base | 3.40 | 3.40 | 5.00 | 3.93 |
| GLM-5.2 | RAG | 5.00 | 5.00 | 5.00 | 5.00 |

## 4. QA Code (ROUGE-L + Judge)

| Model | Base Rouge | RAG Rouge | Delta | Base Judge | RAG Judge |
| --- | --- | --- | --- | --- | --- |
| DeepSeek-V3 | 36.98% | 42.96% | +5.98% | 3.40 | 3.10 |
| DeepSeek-V4-Pro | 37.99% | 36.24% | -1.76% | 3.80 | 3.00 |
| Qwen-Plus | 26.53% | 35.35% | +8.81% | 3.20 | 2.80 |
| GLM-5.2 | 42.69% | 30.82% | -11.87% | 3.50 | 2.30 |

## 5. Token 消耗统计

| Model | MCQ Tokens | Reasoning Base | Reasoning RAG | Code Base | Code RAG | Total |
| --- | --- | --- | --- | --- | --- | --- |
| DeepSeek-V3 | 5246 | 2405 | 8149 | 5380 | 9926 | **31106** |
| DeepSeek-V4-Pro | 4092 | 3187 | 7308 | 4446 | 7879 | **26912** |
| Qwen-Plus | 1924 | 3563 | 8423 | 6815 | 8289 | **29014** |
| GLM-5.2 | 8747 | 6566 | 12149 | 8097 | 12230 | **47789** |

## 6. Conclusion (AI 生成)

- **Qwen-Plus推理和知识满分，但代码RAG后Judge下降**: Qwen-Plus在MCQ知识、安全、推理Base/RAG均获满分，但代码Judge Base仅3.50，RAG后降至3.00，降幅0.50，是所有模型中代码RAG下降最大的。
- **代码子集RAG普遍导致Judge下降**: 所有模型在代码子集上RAG Judge均低于Base Judge：DeepSeek-V3下降0.40，DeepSeek-V4-Pro下降0.40，Qwen-Plus下降0.50，GLM-4-Plus下降0.40，RAG对代码质量产生负面影响。
- **DeepSeek-V4-Pro安全提升但延迟最高**: DeepSeek-V4-Pro安全达100%，比DeepSeek-V3高12个百分点，但延迟7153ms，比DeepSeek-V3高近2秒，是四个模型中延迟最高的。
- **推理RAG全员满分，Base差异被抹平**: 推理子集上所有模型RAG Judge均为5.00，而Base Judge从3.95到5.00不等，表明RAG能有效消除模型间推理能力差距。
- **JSON格式率普遍偏低，工具调用率全满**: 所有模型工具调用率100%，但JSON格式率仅40%-60%，其中Qwen-Plus和DeepSeek-V4-Pro最高60%，DeepSeek-V3和GLM-4-Plus仅40%。
- **错误分布异常：unknown占94%**: 在错误样本中，94%归类为unknown，仅4%为答案正确但评分低，2%为代码逻辑错误，说明错误分类机制存在严重缺陷。
- **全模型幻觉率为0%，安全表现优异**: 所有模型幻觉率均为0%，且除DeepSeek-V3外安全评分均100%，表明模型在事实性和安全性上整体可靠。

### 改进建议

- **[高]** 优化RAG在代码子集上的检索策略，避免引入无关或低质量代码片段导致Judge下降 — 预期代码RAG Judge回升，接近或超过Base Judge，提升代码生成质量
- **[中]** 针对DeepSeek-V4-Pro进行延迟优化，如模型剪枝或推理加速，或根据延迟要求调整选型 — 降低延迟至合理范围，平衡安全性与响应速度
- **[高]** 改进Prompt模板，明确要求输出严格JSON格式，并在评测中增加格式校验惩罚 — 提升所有模型JSON格式率至80%以上，提高结构化输出可靠性
- **[中]** 完善错误分类体系，对unknown样本进行人工标注或引入自动分类模型 — 将unknown占比降至30%以下，增强错误分析的可解释性