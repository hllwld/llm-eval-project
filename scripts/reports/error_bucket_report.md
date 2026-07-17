# Error Bucket 分析报告
> 2026-07-17 13:33 | 50 samples analyzed | 12 buckets

## Error Bucket 分类体系

| ID | 名称 | 描述 | 修复方向 |
| --- | --- | --- | --- |
| `math_error` | 数学计算错误 | 推理方向正确但计算过程出错 | CoT校验 / 计算器工具 |
| `logic_gap` | 逻辑链断裂 | 步骤不完整或跳跃，缺少关键推导 | CoT + 分步校验 |
| `context_miss` | 上下文遗漏 | 题目中的关键信息未被使用 | 改进 Prompt 强调信息提取 |
| `retrieval_fail` | 检索失败 | RAG 未召回正确知识或召回了无关内容 | 优化知识库 / 检索策略 |
| `format_violation` | 格式违规 | 输出格式不符合要求（非JSON/缺少字段） | 强化 Prompt 格式约束 |
| `hallucination` | 幻觉/捏造 | 编造不存在的事实、API、函数 | RAG 事实核查 / 知识库补充 |
| `prompt_misread` | Prompt理解偏差 | 误解了题目意图或要求 | 改写 Prompt 更明确 |
| `knowledge_gap` | 知识盲区 | 模型缺少相关知识，确实不知道 | RAG / 知识库扩充 |
| `code_syntax` | 代码语法错误 | 代码有语法问题无法运行 | 增加代码校验步骤 |
| `code_logic` | 代码逻辑错误 | 代码能运行但结果不符合预期 | 增加测试用例验证 |
| `security_unsafe` | 安全未拒答 | 应拒答但接受了诱导 | 安全策略加固 / RLHF |
| `correct_but_low_score` | 答案正确但评分低 | 模型答案正确但 Rouge/Judge 因格式/长度误判 | 改进评分指标 |

## 错误分布

| 错误类型 | 数量 | 占比 | 严重程度 | 修复方向 |
| --- | --- | --- | --- | --- |
| **unknown** | 47 | 94.0% | 高:0 中:47 低:0 | - |
| **答案正确但评分低** | 2 | 4.0% | 高:0 中:0 低:2 | 改进评分指标 |
| **代码逻辑错误** | 1 | 2.0% | 高:1 中:0 低:0 | 增加测试用例验证 |

## 可视化分布

```
  unknown      ████████████████████████████████████████ 47 (94.0%)
  答案正确但评分低     █ 2 (4.0%)
  代码逻辑错误       █ 1 (2.0%)
```

## 关键发现


## 改进优先级

| 优先级 | 措施 | 影响范围 |
| --- | --- | --- |
| **P0** | - | 94% (47条) |
| **P2** | 增加测试用例验证 | 2% (1条) |
| **P2** | 改进评分指标 | 4% (2条) |

## 逐条分类明细

| # | Bucket | 置信度 | 严重度 | 原因 | 题目 |
| --- | --- | --- | --- | --- | --- |
| 1 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 一个水箱每分钟进水 3 升，出水 2 升。原本有 5 升水，10 分钟后有多少升？ |
| 2 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 小明买 3 支笔和 2 个本子共花 17 元，1 支笔 3 元，问 1 个本子多少钱？ |
| 3 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 一个数列：2, 4, 8, 16, ...，第 8 项是多少？ |
| 4 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 甲、乙两人相距 100 米相向而行，甲速度 6m/s，乙 4m/s，几秒后相遇？ |
| 5 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 一个班级 50 人，男生占 60%，女生有多少人？ |
| 6 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 已知 A > B, B > C, C > D，以下哪个选项一定成立？ |
| 7 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 一个长方形长 12cm，宽 8cm，对角线长约多少 cm？ |
| 8 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 如果今天是星期三，100 天后是星期几？ |
| 9 | 答案正确但评分低 | 90% | low | 答案正确但评分低，可能是格式问题。 | 三个连续偶数的和是 36，这三个数分别是多少？ |
| 10 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 一个骰子掷两次，两次点数之和为 7 的概率是多少？ |
| 11 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 一个圆形花坛半径 7 米，面积约多少平方米？（π≈3.14） |
| 12 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 把 1 到 100 的所有整数相加，总和是多少？ |
| 13 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 甲完成一件工作需要 6 天，乙需要 12 天，两人合作需要几天？ |
| 14 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 一个两位数，十位数是个位数的 2 倍，且两数之和为 12，这个数是多少？ |
| 15 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 以下逻辑推理是否正确："所有 A 都是 B，C 是 B，所以 C 是 A。" |
| 16 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 用 Python 写一个函数，判断一个数是否为质数。 |
| 17 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 用 Python 实现斐波那契数列的前 N 项（N 由参数传入）。 |
| 18 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 写一个 Python 函数，统计字符串中每个字符出现的次数，返回字典。 |
| 19 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 用 Python 实现二分查找算法，在有序列表中查找目标值。 |
| 20 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 写一个 Python 函数，判断一个字符串是否为回文串（忽略大小写和空格）。 |
| 21 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 用 Python 写一个装饰器，打印函数的执行时间。 |
| 22 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 用 Python 实现冒泡排序算法。 |
| 23 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 用 Python 读取一个 CSV 文件，计算某一列的平均值。 |
| 24 | 代码逻辑错误 | 95% | high | put方法中缺少添加新项的赋值语句 | 用 Python 实现一个 LRU 缓存类（使用 OrderedDict）。 |
| 25 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 用 Python 写一个多线程下载器，支持断点续传。 |
| 26 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 一个水箱每分钟进水 3 升，出水 2 升。原本有 5 升水，10 分钟后有多少升？ |
| 27 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 小明买 3 支笔和 2 个本子共花 17 元，1 支笔 3 元，问 1 个本子多少钱？ |
| 28 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 一个数列：2, 4, 8, 16, ...，第 8 项是多少？ |
| 29 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 甲、乙两人相距 100 米相向而行，甲速度 6m/s，乙 4m/s，几秒后相遇？ |
| 30 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 一个班级 50 人，男生占 60%，女生有多少人？ |
| 31 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 已知 A > B, B > C, C > D，以下哪个选项一定成立？ |
| 32 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 一个长方形长 12cm，宽 8cm，对角线长约多少 cm？ |
| 33 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 如果今天是星期三，100 天后是星期几？ |
| 34 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 三个连续偶数的和是 36，这三个数分别是多少？ |
| 35 | 答案正确但评分低 | 10% | low | 模型答案正确且推理完整，但可能因评分标准问题被误判 | 一个骰子掷两次，两次点数之和为 7 的概率是多少？ |
| 36 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 一个圆形花坛半径 7 米，面积约多少平方米？（π≈3.14） |
| 37 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 把 1 到 100 的所有整数相加，总和是多少？ |
| 38 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 甲完成一件工作需要 6 天，乙需要 12 天，两人合作需要几天？ |
| 39 | unknown | 0% | medium | Unterminated string starting at: line 4 column 13 (char 72) | 一个两位数，十位数是个位数的 2 倍，且两数之和为 12，这个数是多少？ |
| 40 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 以下逻辑推理是否正确："所有 A 都是 B，C 是 B，所以 C 是 A。" |
| 41 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 用 Python 写一个函数，判断一个数是否为质数。 |
| 42 | unknown | 0% | medium | Expecting ',' delimiter: line 1 column 52 (char 51) | 用 Python 实现斐波那契数列的前 N 项（N 由参数传入）。 |
| 43 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 写一个 Python 函数，统计字符串中每个字符出现的次数，返回字典。 |
| 44 | unknown | 0% | medium | Expecting ',' delimiter: line 3 column 18 (char 51) | 用 Python 实现二分查找算法，在有序列表中查找目标值。 |
| 45 | unknown | 0% | medium | Unterminated string starting at: line 2 column 13 (char 14) | 写一个 Python 函数，判断一个字符串是否为回文串（忽略大小写和空格）。 |
| 46 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 用 Python 写一个装饰器，打印函数的执行时间。 |
| 47 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 用 Python 实现冒泡排序算法。 |
| 48 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 用 Python 读取一个 CSV 文件，计算某一列的平均值。 |
| 49 | unknown | 0% | medium | Expecting value: line 1 column 1 (char 0) | 用 Python 实现一个 LRU 缓存类（使用 OrderedDict）。 |
| 50 | unknown | 0% | medium | Expecting property name enclosed in double quotes: line 2 column 1 (char 2) | 用 Python 写一个多线程下载器，支持断点续传。 |