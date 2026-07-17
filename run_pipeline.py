"""
run_pipeline.py — 一键评测流水线
用法: python run_pipeline.py [--tier smoke|full] [--skip-kb] [--skip-eval] [--skip-metrics] [--skip-ab] [--skip-bucket] [--skip-viz]

步骤:
  1. 初始化 RAG 知识库 (reasoning_kb + code_kb)
  2. 运行 final_eval (全53题, Base+RAG, LLM Judge)
  3. 运行 extended_metrics (JSON格式率 + 工具调用成功率)
  4. A/B Test 统计分析 (p-value + cost + CI)
  5. Error Bucket 错误分类 (LLM自动分桶)
  6. 生成可视化仪表板 (HTML)
"""

import sys
import os
import subprocess
import time
from datetime import datetime

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')

def run_step(name, cmd):
    print(f'\n{"="*60}')
    print(f'  [{name}]')
    print(f'  {cmd}')
    print(f'{"="*60}')
    t0 = time.time()
    result = subprocess.run(cmd, shell=True, cwd=SCRIPTS)
    elapsed = time.time() - t0
    if result.returncode != 0:
        print(f'\n[FAIL] {name} (exit={result.returncode}, {elapsed:.0f}s)')
        sys.exit(1)
    print(f'[OK]   {name} ({elapsed:.0f}s)')
    return True


if __name__ == '__main__':
    skip_kb = '--skip-kb' in sys.argv
    skip_eval = '--skip-eval' in sys.argv
    skip_metrics = '--skip-metrics' in sys.argv
    skip_ab = '--skip-ab' in sys.argv
    skip_bucket = '--skip-bucket' in sys.argv
    skip_viz = '--skip-viz' in sys.argv

    # Tier: smoke or full
    tier = 'full'
    for i, arg in enumerate(sys.argv):
        if arg == '--tier' and i + 1 < len(sys.argv):
            tier = sys.argv[i + 1]

    started = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'Pipeline start: {started}')
    print(f'Tier: {tier}')
    print(f'Flags: skip_kb={skip_kb}  skip_eval={skip_eval}  skip_metrics={skip_metrics}  skip_ab={skip_ab}  skip_bucket={skip_bucket}  skip_viz={skip_viz}')

    if not skip_kb:
        run_step('1/6  Init RAG Knowledge Base',
                 'python rag_retriever.py')

    if not skip_eval:
        run_step(f'2/6  Run Final Eval (tier={tier})',
                 f'python final_eval.py --tier {tier}')

    if not skip_metrics:
        run_step('3/6  Run Extended Metrics (JSON + Tool Call)',
                 'python extended_metrics.py')

    if not skip_ab:
        run_step('4/6  A/B Test Analysis (p-value + cost + CI)',
                 'python ab_test.py')

    if not skip_bucket:
        run_step('5/6  Error Bucket Classification',
                 'python error_bucket.py')

    if not skip_viz:
        run_step('6/6  Generate Dashboard (HTML)',
                 'python build_viz.py')

    ended = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'\n{"="*60}')
    print(f'  Pipeline Complete!')
    print(f'  Started: {started}')
    print(f'  Ended:   {ended}')
    print(f'{"="*60}')
    print(f'  Reports:')
    print(f'    scripts/reports/final_eval_report.md')
    print(f'    scripts/reports/extended_metrics_report.md')
    print(f'    scripts/reports/ab_test_report.md')
    print(f'    scripts/reports/error_bucket_report.md')
    print(f'  Dashboard: dashboard.html')
