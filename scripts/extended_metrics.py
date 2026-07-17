"""
extended_metrics.py — 扩展指标评测
1. JSON 格式正确率 — json.loads + schema 校验
2. 工具调用成功率 — function calling, 匹配 tool_name + args
支持: 所有 config/model_config.yaml 中 active 的模型
输出: outputs/extended_metrics/ + scripts/reports/extended_metrics_report.md
"""

import os
import sys
import json
import time
import yaml
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
QA_DIR = os.path.join(PROJECT_ROOT, 'data', 'custom_testset', 'qa')
REPORT_DIR = os.path.join(BASE_DIR, 'reports')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'outputs', 'extended_metrics')
os.makedirs(OUTPUT_DIR, exist_ok=True)

load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# ── Tool 定义 ──
TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'get_weather',
            'description': '获取指定城市的天气信息',
            'parameters': {'type': 'object', 'properties': {'city': {'type': 'string', 'description': '城市名称'}}, 'required': ['city']},
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'calculator',
            'description': '执行数学计算',
            'parameters': {'type': 'object', 'properties': {'expression': {'type': 'string', 'description': '数学表达式'}}, 'required': ['expression']},
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'translate',
            'description': '翻译文本',
            'parameters': {'type': 'object', 'properties': {'text': {'type': 'string'}, 'target_lang': {'type': 'string', 'enum': ['zh', 'en', 'ja']}}, 'required': ['text', 'target_lang']},
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_current_time',
            'description': '获取当前时间',
            'parameters': {'type': 'object', 'properties': {'timezone': {'type': 'string'}}, 'required': ['timezone']},
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'search_papers',
            'description': '搜索学术论文',
            'parameters': {'type': 'object', 'properties': {'query': {'type': 'string'}, 'limit': {'type': 'integer', 'default': 5}}, 'required': ['query']},
        }
    },
]


def validate_json_format(response: str, schema: Optional[Dict] = None) -> Dict:
    """Try json.loads and optional schema validation. Returns {valid: bool, parsed: any, error: str}"""
    # Extract JSON from response (handle markdown code blocks)
    text = response.strip()
    if text.startswith('```'):
        lines = text.split('\n')
        text = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        return {'valid': False, 'parsed': None, 'error': f'JSON parse error: {e}'}

    if schema:
        # Basic schema validation
        stype = schema.get('type', '')
        if stype == 'object':
            if not isinstance(parsed, dict):
                return {'valid': False, 'parsed': parsed, 'error': 'Not an object'}
            for key in schema.get('required', []):
                if key not in parsed:
                    return {'valid': False, 'parsed': parsed, 'error': f'Missing required key: {key}'}
            for key, prop in schema.get('properties', {}).items():
                if key not in parsed:
                    continue
                val = parsed[key]
                pt = prop.get('type', '')
                if pt == 'string' and not isinstance(val, str):
                    return {'valid': False, 'parsed': parsed, 'error': f'{key}: expected string'}
                if pt == 'integer' and not isinstance(val, int):
                    return {'valid': False, 'parsed': parsed, 'error': f'{key}: expected integer'}
                if pt == 'number' and not isinstance(val, (int, float)):
                    return {'valid': False, 'parsed': parsed, 'error': f'{key}: expected number'}
                if pt == 'boolean' and not isinstance(val, bool):
                    return {'valid': False, 'parsed': parsed, 'error': f'{key}: expected boolean'}
                if pt == 'array':
                    if not isinstance(val, list):
                        return {'valid': False, 'parsed': parsed, 'error': f'{key}: expected array'}
                    if 'minItems' in prop and len(val) < prop['minItems']:
                        return {'valid': False, 'parsed': parsed, 'error': f'{key}: too few items'}
                if pt == 'object' and not isinstance(val, dict):
                    return {'valid': False, 'parsed': parsed, 'error': f'{key}: expected object'}

    return {'valid': True, 'parsed': parsed, 'error': None}


def validate_tool_call(tool_calls, expected_name: Optional[str], expected_args: Optional[Dict]) -> Dict:
    """Validate that the model called the right tool with right args"""
    if expected_name is None:
        # This is a "should NOT call tool" test — model should just answer in text
        if not tool_calls:
            return {'valid': True, 'error': None, 'detail': 'Correctly did not call tool'}
        return {'valid': False, 'error': 'Called tool when should not', 'detail': str(tool_calls)}

    if not tool_calls:
        return {'valid': False, 'error': 'No tool call made', 'detail': None}

    call = tool_calls[0]
    fn_name = call.function.name if hasattr(call, 'function') else call.get('function', {}).get('name', '')

    if fn_name != expected_name:
        return {'valid': False, 'error': f'Tool mismatch: called {fn_name}, expected {expected_name}', 'detail': fn_name}

    args_str = call.function.arguments if hasattr(call, 'function') else call.get('function', {}).get('arguments', '{}')
    try:
        actual_args = json.loads(args_str) if isinstance(args_str, str) else args_str
    except json.JSONDecodeError:
        return {'valid': False, 'error': 'Tool args not valid JSON', 'detail': args_str}

    if expected_args:
        for k, v in expected_args.items():
            if k not in actual_args:
                return {'valid': False, 'error': f'Missing arg: {k}', 'detail': actual_args}
            # Loose match: string values should contain expected value
            if isinstance(v, str) and isinstance(actual_args[k], str):
                if v not in actual_args[k]:
                    return {'valid': False, 'error': f'Arg mismatch for {k}: expected {v}, got {actual_args[k]}', 'detail': actual_args}

    return {'valid': True, 'error': None, 'detail': {'tool': fn_name, 'args': actual_args}}


def run():
    # ── Load models ──
    with open(os.path.join(PROJECT_ROOT, 'config', 'model_config.yaml'), 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    models = {}
    for m in config['models']:
        if not m.get('active', True):
            continue
        key = os.getenv(m.get('api_key_env', ''), '')
        if key:
            models[m['name']] = {'model': m['model_id'], 'api_url': m['api_url'], 'api_key': key}

    # ── Load testsets ──
    jf_path = os.path.join(QA_DIR, 'json_format.jsonl')
    tc_path = os.path.join(QA_DIR, 'tool_calls.jsonl')

    json_tests = [json.loads(line) for line in open(jf_path, 'r', encoding='utf-8')] if os.path.exists(jf_path) else []
    tool_tests = [json.loads(line) for line in open(tc_path, 'r', encoding='utf-8')] if os.path.exists(tc_path) else []

    print(f'JSON Format Tests: {len(json_tests)}')
    print(f'Tool Call Tests:   {len(tool_tests)}')
    print(f'Models:            {list(models.keys())}')

    results = {}

    for name, mc in models.items():
        base_url = mc['api_url'].rstrip('/').replace('/chat/completions', '')
        client = OpenAI(api_key=mc['api_key'], base_url=base_url)
        print(f'\n{"="*60}\n>> {name}\n{"="*60}')

        # ── JSON Format ──
        jf_correct = 0
        jf_details = []
        print(f'\n  [JSON Format] {len(json_tests)} tests...')
        for test in json_tests:
            resp = client.chat.completions.create(
                model=mc['model'],
                messages=[
                    {'role': 'system', 'content': '你是AI助手。请严格按要求的JSON格式输出，不要在JSON外包裹任何文字说明。'},
                    {'role': 'user', 'content': test['query']},
                ],
                temperature=0.1, max_tokens=512, timeout=30,
            )
            content = resp.choices[0].message.content
            schema = test.get('expected_schema')
            v = validate_json_format(content, schema)
            if v['valid']:
                jf_correct += 1
                print(f'    [{test["id"]}] OK')
            else:
                print(f'    [{test["id"]}] FAIL: {v["error"]}')
            jf_details.append({'id': test['id'], **v, 'response': content[:200]})
            time.sleep(0.2)

        jf_rate = jf_correct / len(json_tests) if json_tests else 0

        # ── Tool Call ──
        tc_correct = 0
        tc_details = []
        print(f'\n  [Tool Call] {len(tool_tests)} tests...')
        for test in tool_tests:
            resp = client.chat.completions.create(
                model=mc['model'],
                messages=[{'role': 'user', 'content': test['query']}],
                tools=TOOLS, tool_choice='auto',
                temperature=0.1, max_tokens=512, timeout=30,
            )
            msg = resp.choices[0].message
            v = validate_tool_call(msg.tool_calls, test.get('expected_tool'), test.get('expected_args'))
            if v['valid']:
                tc_correct += 1
                print(f'    [{test["id"]}] OK {v.get("detail", "")}')
            else:
                print(f'    [{test["id"]}] FAIL: {v["error"]}')
            tc_details.append({'id': test['id'], **v})
            time.sleep(0.2)

        tc_rate = tc_correct / len(tool_tests) if tool_tests else 0
        results[name] = {
            'json_format_rate': round(jf_rate, 4),
            'json_correct': jf_correct,
            'json_total': len(json_tests),
            'json_details': jf_details,
            'tool_call_rate': round(tc_rate, 4),
            'tool_correct': tc_correct,
            'tool_total': len(tool_tests),
            'tool_details': tc_details,
        }

    # ── Report ──
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    lines = [
        '# Extended Metrics Report',
        f'> {now} | {len(models)} models | JSON Format {len(json_tests)}q + Tool Call {len(tool_tests)}q',
        '',
        '## JSON 格式正确率',
        '',
        '| 模型 | 正确率 | 正确/总数 |',
        '| --- | --- | --- |',
    ]
    for name, r in results.items():
        lines.append(f'| {name} | {r["json_format_rate"]:.0%} | {r["json_correct"]}/{r["json_total"]} |')

    lines += ['', '## 工具调用成功率', '',
              '| 模型 | 成功率 | 正确/总数 |',
              '| --- | --- | --- |']
    for name, r in results.items():
        lines.append(f'| {name} | {r["tool_call_rate"]:.0%} | {r["tool_correct"]}/{r["tool_total"]} |')

    lines += ['', '## 综合', '',
              '| 模型 | JSON 格式率 | 工具调用率 | 综合分 |',
              '| --- | --- | --- | --- |']
    for name, r in results.items():
        avg = (r['json_format_rate'] + r['tool_call_rate']) / 2
        lines.append(f'| {name} | {r["json_format_rate"]:.0%} | {r["tool_call_rate"]:.0%} | {avg:.0%} |')

    report_path = os.path.join(REPORT_DIR, 'extended_metrics_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    json_path = os.path.join(OUTPUT_DIR, f'extended_metrics_{datetime.now().strftime("%Y%m%d")}.json')
    json_data = {'timestamp': now, 'models': list(models.keys()), 'results': {}}
    for name, r in results.items():
        json_data['results'][name] = {
            'json_format_rate': r['json_format_rate'],
            'tool_call_rate': r['tool_call_rate'],
            'json_details': r['json_details'],
            'tool_details': r['tool_details'],
        }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    print(f'\nReport: {report_path}')
    print(f'JSON:   {json_path}')


if __name__ == '__main__':
    run()
