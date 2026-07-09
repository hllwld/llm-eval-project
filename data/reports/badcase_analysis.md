# Day 10 Badcase Analysis Report

## 1. Overview
- Total Badcases: 9
- Models: GLM-4-Plus, DeepSeek-V3, Qwen-Plus, Qwen2.5-VL

## 2. Error Type Distribution
- 推理错误: 5
- 代码错误: 3
- 知识错误: 1

## 3. RAG Fixability
- RAG-solvable: 1 (11.1%)
- RAG-partial: 8 (88.9%)
- RAG-unsolvable: 0 (0.0%)

## 4. Sample Badcases

### Case 1
- **Model**: GLM-4-Plus
- **Subset**: general_mcq_knowledge
- **Question**: "赤道"穿过哪个大洲的面积最大？
选项：
A) 亚洲
B) 非洲
C) 南美洲
D) 大洋洲...
- **Expected**: B...
- **Actual**: 答案：A...
- **Error Type**: 知识错误
- **Analysis**: 知识错误：模型在"general_mcq_knowledge"子集中选择错误，期望"B"但输出了不同答案
- **RAG**: RAG可解

### Case 2
- **Model**: DeepSeek-V3
- **Subset**: general_qa_code
- **Question**: 用 Python 写一个多线程下载器，支持断点续传。...
- **Expected**: 思路：使用 requests 库的 Range header 分段下载，每段一个线程，最后合并。核心代码需 import requests, threading；通过 Content-Length 获取文件总大小，按线程数等分，各线程写入临时文件，下载完毕后按顺序合并。...
- **Actual**: 我来为你写一个支持断点续传的多线程下载器：

```python
import os
import requests
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import json
...
- **Error Type**: 代码错误
- **Analysis**: 代码生成质量低（Rouge-L-R=0.32），期望与输出差异显著
- **RAG**: 部分可解

### Case 3
- **Model**: GLM-4-Plus
- **Subset**: general_qa_code
- **Question**: 用 Python 写一个多线程下载器，支持断点续传。...
- **Expected**: 思路：使用 requests 库的 Range header 分段下载，每段一个线程，最后合并。核心代码需 import requests, threading；通过 Content-Length 获取文件总大小，按线程数等分，各线程写入临时文件，下载完毕后按顺序合并。...
- **Actual**: # Python 多线程下载器（支持断点续传）

下面是一个支持断点续传的多线程下载器的实现。这个下载器会：
1. 使用多线程下载文件
2. 支持断点续传（从上次中断的位置继续下载）
3. 显示下载进度
4. 处理下载错误

```python
import os
import threading
...
- **Error Type**: 代码错误
- **Analysis**: 代码生成质量低（Rouge-L-R=0.38），期望与输出差异显著
- **RAG**: 部分可解

### Case 4
- **Model**: GLM-4-Plus
- **Subset**: general_qa_reasoning
- **Question**: 甲、乙两人相距 100 米相向而行，甲速度 6m/s，乙 4m/s，几秒后相遇？...
- **Expected**: 10 秒（100 ÷ (6+4) = 10）...
- **Actual**: 要计算甲、乙两人相向而行后相遇的时间，可以按照以下步骤进行：

1. **确定相对速度**：
   
   两人相向而行时，他们的相对速度是两者速度之和。
   \[
   \text{相对速度} = 6\,\text{m/s} + 4\,\text{m/s} = 10\,\text{m/s}
  ...
- **Error Type**: 推理错误
- **Analysis**: 推理链不完整或有误（Rouge-L-R=0.38）
- **RAG**: 部分可解

### Case 5
- **Model**: GLM-4-Plus
- **Subset**: general_qa_reasoning
- **Question**: 一个圆形花坛半径 7 米，面积约多少平方米？（π≈3.14）...
- **Expected**: 约 153.86 m²（π×7² = 3.14×49 = 153.86）...
- **Actual**: 要计算圆形花坛的面积，可以使用圆的面积公式：

\[
\text{面积} = \pi \times r^2
\]

其中，\( r \) 是圆的半径，\( \pi \approx 3.14 \)。

**步骤如下：**

1. **已知条件：**
   - 半径 \( r = 7 \) 米
   -...
- **Error Type**: 推理错误
- **Analysis**: 推理链不完整或有误（Rouge-L-R=0.38）
- **RAG**: 部分可解
