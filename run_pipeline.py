"""
run_pipeline.py — 一键评测流水线
用法: python run_pipeline.py [--skip-kb] [--skip-eval] [--skip-metrics] [--skip-viz]

步骤:
  1. 初始化 RAG 知识库 (reasoning_kb + code_kb)
  2. 运行 final_eval (全53题, Base+RAG, LLM Judge)
  3. 运行 extended_metrics (JSON格式率 + 工具调用成功率)
  4. 生成可视化仪表板 (HTML)
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
    skip_viz = '--skip-viz' in sys.argv

    started = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'Pipeline start: {started}')
    print(f'Flags: skip_kb={skip_kb}  skip_eval={skip_eval}  skip_metrics={skip_metrics}  skip_viz={skip_viz}')

    if not skip_kb:
        run_step('1/4  Init RAG Knowledge Base',
                 'python rag_retriever.py')

    if not skip_eval:
        run_step('2/4  Run Final Eval (MCQ + QA + Judge)',
                 'python final_eval.py')

    if not skip_metrics:
        run_step('3/4  Run Extended Metrics (JSON + Tool Call)',
                 'python extended_metrics.py')

    if not skip_viz:
        run_step('4/4  Generate Dashboard (HTML)',
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
    print(f'  Dashboard: dashboard.html')
