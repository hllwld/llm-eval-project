"""
rag_benchmark.py — 多模型 RAG 增强评测
模型: 由 config/model_config.yaml active 模型决定
测试集: 推理15题 + 代码10题
模式: RAG 检索 + 解题模板注入
"""

import os
import sys
import json
import time
import yaml
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
sys.path.insert(0, BASE_DIR)
from rag_retriever import RAGRetriever
from rag_prompt_builder import RAGPromptBuilder

load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

QA_DIR = os.path.join(PROJECT_ROOT, 'data', 'custom_testset', 'qa')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'outputs', 'rag_benchmark')
os.makedirs(OUTPUT_DIR, exist_ok=True)


class RAGBenchmark:
    """三模型 RAG 增强评测"""

    def __init__(self):
        self.retriever = RAGRetriever()
        self.prompt_builder = RAGPromptBuilder(max_docs=2, include_answer=True)
        self.models = self._load_models()
        self.results = {}

    def _load_models(self) -> Dict:
        with open(os.path.join(PROJECT_ROOT, 'config', 'model_config.yaml'), 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        models = {}
        for m in config['models']:
            if not m.get('active', True):
                continue
            key = os.getenv(m.get('api_key_env', ''), '')
            if key:
                models[m['name']] = {
                    'model': m['model_id'],
                    'api_url': m['api_url'],
                    'api_key': key,
                }
        return models

    def _call_model(self, mc: Dict, messages: List[Dict]) -> str:
        base_url = mc['api_url'].rstrip('/').replace('/chat/completions', '')
        client = OpenAI(api_key=mc['api_key'], base_url=base_url)
        try:
            resp = client.chat.completions.create(
                model=mc['model'], messages=messages,
                temperature=0.3, max_tokens=1024, timeout=60,
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f'[ERROR: {e}]'

    def evaluate(self, model_name: str, test_data: List[Dict], subset: str) -> List[Dict]:
        mc = self.models[model_name]
        results = []

        print(f'\n{"="*60}')
        print(f'[{model_name}] {subset} ({len(test_data)} questions)')
        print(f'{"="*60}')

        for idx, item in enumerate(test_data, 1):
            q = item['query'].split('\n\n')[0].strip()
            print(f'  [{idx:2d}/{len(test_data)}] {q[:55]}...', end=' ', flush=True)

            docs = self.retriever.retrieve(q, top_k=2) if subset == 'reasoning' else []
            messages = self.prompt_builder.build_messages(q, docs) if docs else [
                {'role': 'system', 'content': '你是一个AI助手，请直接回答问题。'},
                {'role': 'user', 'content': q},
            ]
            response = self._call_model(mc, messages)

            results.append({
                'question': q,
                'expected': item['response'],
                'response': response,
                'retrieved_ids': [d['id'] for d in docs],
                'retrieved_count': len(docs),
            })
            print(f'done (retrieved {len(docs)})')
            time.sleep(0.3)

        return results

    def run(self):
        # Load questions
        reasoning_qs = []
        code_qs = []
        for fname, lst in [('reasoning.jsonl', reasoning_qs), ('code.jsonl', code_qs)]:
            path = os.path.join(QA_DIR, fname)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    lst.extend(json.loads(line) for line in f if line.strip())

        print(f'Models: {list(self.models.keys())}')
        print(f'Questions: reasoning={len(reasoning_qs)} code={len(code_qs)}')

        now = datetime.now().strftime('%Y%m%d_%H%M')

        for model_name in self.models:
            self.results[model_name] = {}

            # Reasoning with RAG
            r_results = self.evaluate(model_name, reasoning_qs, 'reasoning')
            self.results[model_name]['reasoning'] = r_results

            # Code without RAG (KB has no code entries)
            c_results = self.evaluate(model_name, code_qs, 'code')
            self.results[model_name]['code'] = c_results

            # Checkpoint
            cp_path = os.path.join(OUTPUT_DIR, f'{model_name}_{now}.json')
            with open(cp_path, 'w', encoding='utf-8') as f:
                json.dump({model_name: self.results[model_name]}, f, indent=2, ensure_ascii=False)
            print(f'  Checkpoint: {cp_path}')

        # Final summary
        print(f'\n{"="*60}')
        print('Summary')
        print(f'{"="*60}')
        for model_name in self.models:
            r = self.results[model_name].get('reasoning', [])
            c = self.results[model_name].get('code', [])
            avg_recall = sum(x['retrieved_count'] for x in r) / len(r) if r else 0
            print(f'  {model_name}: reasoning={len(r)} code={len(c)} avg_recall={avg_recall:.1f}')

        # Save full results
        full_path = os.path.join(OUTPUT_DIR, f'rag_benchmark_{now}.json')
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump({'timestamp': now, 'models': list(self.models.keys()), 'results': self.results},
                      f, indent=2, ensure_ascii=False)
        print(f'\nFull results: {full_path}')


if __name__ == '__main__':
    RAGBenchmark().run()
