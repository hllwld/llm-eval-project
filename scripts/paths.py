"""
paths.py — 统一路径管理
所有模块通过此文件获取路径，禁止各模块自行 glob。
路径命名规则变更只需改这一处，全部脚本自动生效。

用法:
    from paths import (
        PROJECT_ROOT, OUTPUTS_DIR, REPORTS_DIR,
        get_latest_final_eval, get_latest_final_eval_raw, get_all_final_eval,
        get_latest_extended_metrics, get_latest_error_bucket,
        get_latest_rag_eval, get_latest_rag_benchmark,
        FINAL_EVAL_REPORT, EXTENDED_METRICS_REPORT, SECURITY_EVAL_REPORT,
        ERROR_BUCKET_REPORT, REGRESSION_REPORT,
        INSIGHTS_JSON, SECURITY_EVAL_JSON, DASHBOARD_HTML,
        MCQ_DIR, QA_DIR, MODEL_CONFIG,
    )
"""

import os
import glob as _glob

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, 'scripts')
OUTPUTS_DIR = os.path.join(PROJECT_ROOT, 'outputs')
REPORTS_DIR = os.path.join(SCRIPTS_DIR, 'reports')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')


# ═══════════════════════════════════════════════════════════════
#  内部工具
# ═══════════════════════════════════════════════════════════════

def _ensure_dir(path: str) -> str:
    """确保路径的目录存在，返回原路径"""
    d = os.path.dirname(path) if '.' in os.path.basename(path) else path
    os.makedirs(d, exist_ok=True)
    return path

def _latest(pattern: str) -> str | None:
    """给定 glob pattern，返回最新（文件名逆序排第一）的文件路径，无匹配返回 None"""
    files = sorted(_glob.glob(pattern), reverse=True)
    return files[0] if files else None

def _all_sorted(pattern: str) -> list:
    """给定 glob pattern，返回按文件名排序的所有匹配路径"""
    return sorted(_glob.glob(pattern))


# ═══════════════════════════════════════════════════════════════
#  Final Eval
# ═══════════════════════════════════════════════════════════════

FINAL_EVAL_DIR = os.path.join(OUTPUTS_DIR, 'final_eval')
FINAL_EVAL_REPORT = os.path.join(REPORTS_DIR, 'final_eval_report.md')

def get_latest_final_eval() -> str | None:
    """最新 final_eval stats JSON（[0-9] 过滤，排除 raw 文件）"""
    return _latest(os.path.join(FINAL_EVAL_DIR, 'final_eval_[0-9]*.json'))

def get_latest_final_eval_raw() -> str | None:
    """最新 final_eval raw JSON（含原始回答）"""
    return _latest(os.path.join(FINAL_EVAL_DIR, 'final_eval_raw_*.json'))

def get_all_final_eval() -> list:
    """所有 final_eval stats JSON（按文件名排序）"""
    return _all_sorted(os.path.join(FINAL_EVAL_DIR, 'final_eval_[0-9]*.json'))


# ═══════════════════════════════════════════════════════════════
#  Extended Metrics
# ═══════════════════════════════════════════════════════════════

EXTENDED_METRICS_DIR = os.path.join(OUTPUTS_DIR, 'extended_metrics')
EXTENDED_METRICS_REPORT = os.path.join(REPORTS_DIR, 'extended_metrics_report.md')

def get_latest_extended_metrics() -> str | None:
    return _latest(os.path.join(EXTENDED_METRICS_DIR, 'extended_metrics_*.json'))


# ═══════════════════════════════════════════════════════════════
#  Error Bucket
# ═══════════════════════════════════════════════════════════════

ERROR_BUCKET_DIR = os.path.join(OUTPUTS_DIR, 'error_bucket')
ERROR_BUCKET_REPORT = os.path.join(REPORTS_DIR, 'error_bucket_report.md')

def get_latest_error_bucket() -> str | None:
    return _latest(os.path.join(ERROR_BUCKET_DIR, 'error_bucket_*.json'))


# ═══════════════════════════════════════════════════════════════
#  RAG Eval
# ═══════════════════════════════════════════════════════════════

RAG_EVAL_DIR = os.path.join(OUTPUTS_DIR, 'rag_eval')

def get_latest_rag_eval() -> str | None:
    return _latest(os.path.join(RAG_EVAL_DIR, 'rag_eval_*.json'))


# ═══════════════════════════════════════════════════════════════
#  RAG Benchmark
# ═══════════════════════════════════════════════════════════════

RAG_BENCHMARK_DIR = os.path.join(OUTPUTS_DIR, 'rag_benchmark')

def get_latest_rag_benchmark() -> str | None:
    return _latest(os.path.join(RAG_BENCHMARK_DIR, 'rag_benchmark_*.json'))


# ═══════════════════════════════════════════════════════════════
#  Security Eval
# ═══════════════════════════════════════════════════════════════

SECURITY_EVAL_DIR = os.path.join(OUTPUTS_DIR, 'security_eval')
SECURITY_EVAL_JSON = os.path.join(SECURITY_EVAL_DIR, 'latest.json')
SECURITY_EVAL_REPORT = os.path.join(REPORTS_DIR, 'security_eval_report.md')


# ═══════════════════════════════════════════════════════════════
#  A/B Test
# ═══════════════════════════════════════════════════════════════

AB_TEST_DIR = os.path.join(OUTPUTS_DIR, 'ab_test')
AB_TEST_REPORT = os.path.join(REPORTS_DIR, 'ab_test_report.md')


# ═══════════════════════════════════════════════════════════════
#  Insights
# ═══════════════════════════════════════════════════════════════

INSIGHTS_DIR = os.path.join(OUTPUTS_DIR, 'insights')
INSIGHTS_JSON = os.path.join(INSIGHTS_DIR, 'latest.json')


# ═══════════════════════════════════════════════════════════════
#  Regression
# ═══════════════════════════════════════════════════════════════

REGRESSION_REPORT = os.path.join(REPORTS_DIR, 'regression_report.md')


# ═══════════════════════════════════════════════════════════════
#  RAG Analysis / Compare
# ═══════════════════════════════════════════════════════════════

RAG_ANALYSIS_REPORT = os.path.join(REPORTS_DIR, 'rag_analysis_report.md')
RAG_COMPARE_REPORT = os.path.join(REPORTS_DIR, 'rag_compare_report.md')


# ═══════════════════════════════════════════════════════════════
#  Dashboard
# ═══════════════════════════════════════════════════════════════

DASHBOARD_HTML = os.path.join(PROJECT_ROOT, 'dashboard.html')


# ═══════════════════════════════════════════════════════════════
#  Data
# ═══════════════════════════════════════════════════════════════

CUSTOM_TESTSET_DIR = os.path.join(DATA_DIR, 'custom_testset')
MCQ_DIR = os.path.join(CUSTOM_TESTSET_DIR, 'mcq')
QA_DIR = os.path.join(CUSTOM_TESTSET_DIR, 'qa')

# benchmark v3 历史数据
BENCHMARK_V3_PATTERN = os.path.join(DATA_DIR, 'reports', 'benchmark_scores_v3_*.json')
BENCHMARK_V3_FILES = _all_sorted(BENCHMARK_V3_PATTERN)


# ═══════════════════════════════════════════════════════════════
#  Config
# ═══════════════════════════════════════════════════════════════

MODEL_CONFIG = os.path.join(PROJECT_ROOT, 'config', 'model_config.yaml')


# ═══════════════════════════════════════════════════════════════
#  预创建目录（避免 CI 报 FileNotFoundError）
# ═══════════════════════════════════════════════════════════════

def ensure_all_dirs():
    """确保所有输出和报告目录存在"""
    for d in [
        FINAL_EVAL_DIR, EXTENDED_METRICS_DIR, ERROR_BUCKET_DIR,
        RAG_EVAL_DIR, RAG_BENCHMARK_DIR, SECURITY_EVAL_DIR,
        AB_TEST_DIR, INSIGHTS_DIR, REPORTS_DIR,
    ]:
        os.makedirs(d, exist_ok=True)
