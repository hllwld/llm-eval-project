"""
insight_generator.py — LLM 自动分析评测数据，生成关键洞察 + 改进措施
用法: python insight_generator.py
输出: outputs/insights.json → build_viz.py 读取替换硬编码内容
"""

import os, sys, json, glob, yaml
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'outputs', 'insights')
os.makedirs(OUTPUT_DIR, exist_ok=True)

load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

PROMPT = """你是一个大模型评测专家。请根据以下评测数据，完成两项任务：

## 数据
{data_summary}

## 任务1：关键洞察（5-8条）
分析数据中的关键发现，每条格式：
- **标题**（一句话，如：GLM-5.2 推理最强但代码被 RAG 拉低）
- **数据支撑**（引用具体数字，如：Base Judge 4.81 vs RAG 5.00）
- 不要泛泛而谈，必须有数据支撑

关注重点：
- RAG 在不同模型/子集上的效果差异（Rouge 涨跌、Judge 涨跌）
- 异常值（延迟异常高、某项指标全员满分、某项突然下降）
- 模型间排名变化（和之前对比如果有历史数据）
- 代码子集 RAG 的特殊表现（Rouge升但Judge降）
- JSON 格式率和工具调用率的模型差异

## 任务2：改进措施（3-5条）
根据数据中暴露的问题，给出具体改进措施，每条格式：
- #编号 措施描述 | 优先级(高/中/低) | 预期效果

关注方向：
- 如果 JSON 格式率低 → Prompt 优化
- 如果某模型幻觉率高 → 安全策略加强
- 如果 Rouge 和 Judge 背离 → 指标方案优化
- 如果延迟差异大 → 模型选型建议

## 输出格式
返回纯 JSON（不要 Markdown 包裹）:
{{
  "insights": [
    {{"title": "...", "detail": "...", "sentiment": "positive|negative|neutral"}}
  ],
  "improvements": [
    {{"id": 1, "measure": "...", "priority": "高|中|低", "effect": "..."}}
  ]
}}"""


def load_data():
    """Load evaluation stats from latest JSON files"""
    summary = []

    # final_eval
    fev_files = sorted(glob.glob(os.path.join(PROJECT_ROOT, 'outputs', 'final_eval', 'final_eval_*.json')), reverse=True)
    if fev_files:
        with open(fev_files[0], 'r', encoding='utf-8') as f:
            fev = json.load(f)
        summary.append(f"=== 最终评测 ({fev.get('timestamp','?')}) ===")
        models = fev.get('models', [])
        for m in models:
            if m not in fev: continue
            d = fev[m]
            mcq = d['mcq']
            k_acc = mcq.get('knowledge_acc', 0)
            s_acc = mcq.get('security_acc', 0)
            rj = d.get('reasoning_base_judge', {})
            rj_rag = d.get('reasoning_rag_judge', {})
            cj = d.get('code_base_judge', {})
            cj_rag = d.get('code_rag_judge', {})
            lat = d.get('avg_latency_ms', 0)
            hallu = d.get('hallucination_rate', 0)
            summary.append(
                f"  {m}: MCQ知识{k_acc:.0%}/安全{s_acc:.0%}, "
                f"推理Judge Base={rj.get('overall',0):.2f} RAG={rj_rag.get('overall',0):.2f}, "
                f"代码Judge Base={cj.get('overall',0):.2f} RAG={cj_rag.get('overall',0):.2f}, "
                f"延迟{lat:.0f}ms, 幻觉率{hallu:.0%}"
            )

    # extended_metrics
    em_files = sorted(glob.glob(os.path.join(PROJECT_ROOT, 'outputs', 'extended_metrics', 'extended_metrics_*.json')), reverse=True)
    if em_files:
        with open(em_files[0], 'r', encoding='utf-8') as f:
            em = json.load(f)
        summary.append(f"\n=== 扩展指标 ({em.get('timestamp','?')}) ===")
        for m, r in em.get('results', {}).items():
            jf = r.get('json_format_rate', 0)
            tc = r.get('tool_call_rate', 0)
            summary.append(f"  {m}: JSON格式率{jf:.0%}, 工具调用率{tc:.0%}")

    # error_bucket
    eb_files = sorted(glob.glob(os.path.join(PROJECT_ROOT, 'outputs', 'error_bucket', 'error_bucket_*.json')), reverse=True)
    if eb_files:
        with open(eb_files[0], 'r', encoding='utf-8') as f:
            eb = json.load(f)
        summary.append(f"\n=== 错误分布 ===")
        dist = eb.get('distribution', {})
        for k, v in sorted(dist.items(), key=lambda x: x[1], reverse=True)[:5]:
            total = eb.get('total', 1)
            summary.append(f"  {k}: {v}条 ({v/total*100:.1f}%)")

    return '\n'.join(summary)


def run():
    data = load_data()
    if not data.strip():
        print('[ERROR] No evaluation data found. Run final_eval.py first.')
        sys.exit(1)

    print(f'Data: {len(data)} chars')
    print(f'Calling DeepSeek for analysis...')

    api_key = os.getenv('DEEPSEEK_API_KEY', '')
    client = OpenAI(api_key=api_key, base_url='https://api.deepseek.com')

    result = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model='deepseek-v4-flash',
                messages=[{'role': 'user', 'content': PROMPT.format(data_summary=data)}],
                temperature=0.3, max_tokens=2000, timeout=60,
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith('```'):
                raw = raw.split('```')[1]
                if raw.startswith('json'):
                    raw = raw[4:]
                raw = raw.strip()
            result = json.loads(raw)
            break
        except Exception as e:
            if attempt < 2:
                import time as t
                t.sleep(0.5)
            else:
                print(f'[WARN] AI insight generation failed after 3 attempts: {e}')
                result = {
                    'insights': [{'sentiment': 'neutral',
                                  'title': f'自动分析失败: {str(e)[:60]}',
                                  'detail': '请检查 eval 数据或 API 状态'}],
                    'improvements': [],
                    'summary': 'LLM analysis unavailable — review raw data manually.',
                }

    # Save
    now = datetime.now().strftime('%Y%m%d_%H%M')
    out_path = os.path.join(OUTPUT_DIR, f'insights_{now}.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Also save latest
    latest_path = os.path.join(OUTPUT_DIR, 'latest.json')
    with open(latest_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f'Saved: {out_path}')
    print(f'Latest: {latest_path}')

    # Print summary
    print(f'\n=== LLM Generated Insights ===')
    for i, ins in enumerate(result.get('insights', []), 1):
        emoji = {'positive': '[+]', 'negative': '[-]', 'neutral': '[*]'}.get(ins.get('sentiment', 'neutral'), '')
        print(f'  {emoji} {ins["title"]}')
        print(f'     {ins["detail"]}')

    print(f'\n=== LLM Generated Improvements ===')
    for imp in result.get('improvements', []):
        print(f'  #{imp["id"]} [{imp["priority"]}] {imp["measure"]}')
        print(f'     预期: {imp["effect"]}')


if __name__ == '__main__':
    run()
