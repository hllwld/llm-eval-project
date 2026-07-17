# 测试集变更日志 (Dataset CHANGELOG)

## v4.0 — 2026-07-17
### Added
- 测试题新增 `tier` 标签（smoke/full），支持分层评测
- 新增 JSON 格式题 5 道 (`json_format.jsonl`)
- 新增工具调用题 6 道 (`tool_calls.jsonl`)
- smoke tier: 8 题（知识2 + 安全1 + 推理2 + 代码1 + JSON1 + Tool1）

### Changed
- 所有现有题目 `tier` 默认为 `full`
- `final_eval.py` 支持 `--tier smoke|full` 参数

### Stats
- **总题数**: 53 → 64（+11）
- **smoke**: 8 题，用于 CI/CD 快速验证
- **full**: 56 题，用于正式报告

---

## v3.0 — 2026-07-10
### Added
- 安全对抗子集 (8题): 越狱提示词、角色扮演边界、有害内容生成、恶意代码诱导
- 安全 MCQ 新增 S-006/S-007/S-008（钓鱼邮件/隐私保护/AIGC伦理）

### Changed
- QA 推理题 query 追加输出约束
- 代码题参考答案从思路描述改为标准实现代码
- 难度标签注入 JSONL `difficulty` 字段
- 全部 MCQ 升为 5 选项

### Stats
- **总题数**: 50 → 61（+11: 安全对抗8 + 安全MCQ3）

---

## v2.0 — 2026-07-07
### Added
- 难度标签: easy/medium/hard 三级
- 陷阱项: 知识题增加"以上都不对"同义干扰项
- 输出约束: 推理题追加"仅输出最终答案和一行计算式"

### Stats
- **总题数**: 50

---

## v1.0 — 2026-06-28
### Added
- 初始测试集: 知识20 + 安全5 + 推理15 + 代码10
- 格式: MCQ (CSV) + QA (JSONL)

### Stats
- **总题数**: 50
