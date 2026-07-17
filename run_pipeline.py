"""
run_pipeline.py — 一键评测流水线
用法: python run_pipeline.py [--tier smoke|full] [--skip-kb] [--skip-eval] [--skip-metrics] [--skip-ab] [--skip-bucket] [--skip-security] [--skip-viz]

步骤:
  1. 初始化 RAG 知识库 (reasoning_kb + code_kb)
  2. 运行 final_eval (全64题, Base+RAG, LLM Judge)
  3. 运行 extended_metrics (JSON格式率 + 工具调用成功率)
  4. 安全对抗评测 (越狱/诱导/拒答检测)
  5. A/B Test 统计分析 (p-value + cost + CI)
  6. Error Bucket 错误分类 (LLM自动分桶)
  7. 自动收集 Badcase
  8. AI 洞察生成
  9. 生成可视化仪表板 (HTML)
 10. 回归检测 (告警 + Token趋势)
"""

import sys
import os
import shutil
import subprocess
import time
from datetime import datetime

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results')
REPORTS_SRC = os.path.join(SCRIPTS, 'reports')

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
    skip_security = '--skip-security' in sys.argv
    skip_viz = '--skip-viz' in sys.argv

    # Tier: smoke or full
    tier = 'full'
    for i, arg in enumerate(sys.argv):
        if arg == '--tier' and i + 1 < len(sys.argv):
            tier = sys.argv[i + 1]

    started = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'Pipeline start: {started}')
    print(f'Tier: {tier}')
    print(f'Flags: skip_kb={skip_kb}  skip_eval={skip_eval}  skip_metrics={skip_metrics}  skip_security={skip_security}  skip_ab={skip_ab}  skip_bucket={skip_bucket}  skip_viz={skip_viz}')

    if not skip_kb:
        run_step('1/10  Init RAG Knowledge Base',
                 'python rag_retriever.py')

    if not skip_eval:
        run_step(f'2/10  Run Final Eval (tier={tier})',
                 f'python final_eval.py --tier {tier}')

    if not skip_metrics:
        run_step('3/10  Run Extended Metrics (JSON + Tool Call)',
                 'python extended_metrics.py')

    if not skip_security:
        run_step('4/10  Security Adversarial Eval',
                 'python security_eval.py')

    if not skip_ab:
        run_step('5/10  A/B Test Analysis (p-value + cost + CI)',
                 'python ab_test.py')

    if not skip_bucket:
        run_step('6/10  Error Bucket Classification',
                 'python error_bucket.py')

    run_step('7/10  Collect Badcases',
             'python collect_badcases.py')

    run_step('8/10  AI Insight Generator (LLM analysis)',
             'python insight_generator.py')

    if not skip_viz:
        run_step('9/10  Generate Dashboard (HTML)',
                 'python build_viz.py')

    run_step('10/10  Regression Check (alert + cost trend)',
             'python regression_check.py')

    ended = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Collect all outputs into results/
    run_id = datetime.now().strftime('%Y%m%d_%H%M')
    out_dir = os.path.join(RESULTS_DIR, run_id)
    os.makedirs(out_dir, exist_ok=True)

    # Copy reports
        # Copy raw data too
    import glob as _glob
    raw_files = sorted(_glob.glob(os.path.join(PROJECT_ROOT, 'outputs', 'final_eval', 'final_eval_raw_*.json')), reverse=True)
    if raw_files:
        shutil.copy2(raw_files[0], os.path.join(out_dir, 'raw_responses.json'))

    for f in ['final_eval_report.md', 'extended_metrics_report.md', 'ab_test_report.md', 'error_bucket_report.md', 'regression_report.md']:
        src = os.path.join(REPORTS_SRC, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(out_dir, f))

    # Copy dashboard
    dash_src = os.path.join(PROJECT_ROOT, 'dashboard.html')
    if os.path.exists(dash_src):
        shutil.copy2(dash_src, os.path.join(out_dir, 'dashboard.html'))

    # Copy latest to results/latest/
    latest_dir = os.path.join(RESULTS_DIR, 'latest')
    if os.path.exists(latest_dir):
        shutil.rmtree(latest_dir)
    shutil.copytree(out_dir, latest_dir)

    print(f'\n{"="*60}')
    print(f'  Pipeline Complete!')
    print(f'  Started: {started}')
    print(f'  Ended:   {ended}')
    print(f'{"="*60}')
    print(f'  All outputs: {out_dir}')
    print(f'  Quick access: results/latest/')
    for f in os.listdir(out_dir):
        print(f'    {f}')

    # GitHub Pages 更新提示
    print(f'\n  GitHub Pages: https://hllwld.github.io/llm-eval-project/dashboard.html')
    print(f'  To update:    git add dashboard.html && git commit -m "update dashboard" && git push')
