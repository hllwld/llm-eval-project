# Badcase 分类分析报告

> 总 Badcase 数：13 条 | RAG 可改善率：12/13 (92.3%)

## 分类体系

| 一级分类 | 数量 | 占比 | RAG 适配度 |
| --- | --- | --- | --- |
| 推理错误 | 7 | 53.8% | 🟡/🔴 |
| 知识错误 | 6 | 46.2% | 🔵 RAG可解 |

## 逐条分析

### 1. DeepSeek-V3 — arc (arc_ARC-Challenge)
- **题目**：'ANSWER: [LETTER]' (without quotes) where [LETTER] is one of A,B,C,D.

An astronaut drops a 1.0 kg o...
- **正确答案**：D | **模型输出**：ANSWER: C...
- **标签**：知识错误 → 知识库缺失 → 🔵 RAG可解
- **分析**：科学常识类问题，通过 RAG 补充知识文档即可纠正

### 2. DeepSeek-V3 — arc (arc_ARC-Easy)
- **题目**：'ANSWER: [LETTER]' (without quotes) where [LETTER] is one of A,B,C,D.

All living and nonliving mate...
- **正确答案**：2 | **模型输出**：ANSWER: B...
- **标签**：知识错误 → 知识库缺失 → 🔵 RAG可解
- **分析**：科学常识类问题，通过 RAG 补充知识文档即可纠正

### 3. DeepSeek-V3 — hellaswag (hellaswag_default)
- **题目**：'ANSWER: [LETTER]' (without quotes) where [LETTER] is one of A,B,C,D.

A boy is running down a track...
- **正确答案**：C | **模型输出**：ANSWER: D...
- **标签**：推理错误 → 上下文不足 → 🟡 RAG部分可解
- **分析**：句子补全需要理解上下文，RAG 可提供类似场景参考但非根治

### 4. DeepSeek-V3 — hellaswag (hellaswag_default)
- **题目**：'ANSWER: [LETTER]' (without quotes) where [LETTER] is one of A,B,C,D.

A cartoon animation video is ...
- **正确答案**：A | **模型输出**：ANSWER: D...
- **标签**：推理错误 → 上下文不足 → 🟡 RAG部分可解
- **分析**：句子补全需要理解上下文，RAG 可提供类似场景参考但非根治

### 5. Qwen-Plus — arc (arc_ARC-Challenge)
- **题目**：'ANSWER: [LETTER]' (without quotes) where [LETTER] is one of A,B,C,D.

An astronaut drops a 1.0 kg o...
- **正确答案**：D | **模型输出**：ANSWER: C...
- **标签**：知识错误 → 知识库缺失 → 🔵 RAG可解
- **分析**：科学常识类问题，通过 RAG 补充知识文档即可纠正

### 6. Qwen-Plus — arc (arc_ARC-Easy)
- **题目**：'ANSWER: [LETTER]' (without quotes) where [LETTER] is one of A,B,C,D.

All living and nonliving mate...
- **正确答案**：2 | **模型输出**：ANSWER: B...
- **标签**：知识错误 → 知识库缺失 → 🔵 RAG可解
- **分析**：科学常识类问题，通过 RAG 补充知识文档即可纠正

### 7. Qwen-Plus — hellaswag (hellaswag_default)
- **题目**：'ANSWER: [LETTER]' (without quotes) where [LETTER] is one of A,B,C,D.

A man is standing in front of...
- **正确答案**：C | **模型输出**：ANSWER: A...
- **标签**：推理错误 → 上下文不足 → 🟡 RAG部分可解
- **分析**：句子补全需要理解上下文，RAG 可提供类似场景参考但非根治

### 8. Qwen-Plus — hellaswag (hellaswag_default)
- **题目**：'ANSWER: [LETTER]' (without quotes) where [LETTER] is one of A,B,C,D.

A cartoon animation video is ...
- **正确答案**：A | **模型输出**：ANSWER: D...
- **标签**：推理错误 → 上下文不足 → 🟡 RAG部分可解
- **分析**：句子补全需要理解上下文，RAG 可提供类似场景参考但非根治

### 9. GLM-4-Plus — gsm8k (gsm8k_main)
- **题目**：Here are some examples of how to solve similar problems:

Natalia sold clips to 48 of her friends in...
- **正确答案**：13 | **模型输出**：Reasoning:
First, let's calculate the net profit Carlos makes each year. He sell...
- **标签**：推理错误 → 理解偏差 → 🔴 RAG不可解
- **分析**：数学推理需要模型自身能力，给外部文档无法解决问题

### 10. GLM-4-Plus — arc (arc_ARC-Challenge)
- **题目**：'ANSWER: [LETTER]' (without quotes) where [LETTER] is one of A,B,C,D.

An astronaut drops a 1.0 kg o...
- **正确答案**：D | **模型输出**：ANSWER: C...
- **标签**：知识错误 → 知识库缺失 → 🔵 RAG可解
- **分析**：科学常识类问题，通过 RAG 补充知识文档即可纠正

### 11. GLM-4-Plus — arc (arc_ARC-Challenge)
- **题目**：'ANSWER: [LETTER]' (without quotes) where [LETTER] is one of A,B,C,D.

Devil facial tumor disease (D...
- **正确答案**：B | **模型输出**：ANSWER: D...
- **标签**：知识错误 → 知识库缺失 → 🔵 RAG可解
- **分析**：科学常识类问题，通过 RAG 补充知识文档即可纠正

### 12. GLM-4-Plus — hellaswag (hellaswag_default)
- **题目**：'ANSWER: [LETTER]' (without quotes) where [LETTER] is one of A,B,C,D.

A lady walks to a barbell. Sh...
- **正确答案**：D | **模型输出**：ANSWER: B...
- **标签**：推理错误 → 上下文不足 → 🟡 RAG部分可解
- **分析**：句子补全需要理解上下文，RAG 可提供类似场景参考但非根治

### 13. GLM-4-Plus — hellaswag (hellaswag_default)
- **题目**：'ANSWER: [LETTER]' (without quotes) where [LETTER] is one of A,B,C,D.

Two women in a child are show...
- **正确答案**：C | **模型输出**：ANSWER: B...
- **标签**：推理错误 → 上下文不足 → 🟡 RAG部分可解
- **分析**：句子补全需要理解上下文，RAG 可提供类似场景参考但非根治
