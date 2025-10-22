"""
論文要約生成機能
"""
import openai
import time
import sys
import io
from typing import List, Dict

# Windows環境でのUnicode出力対応
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


SUMMARY_PROMPT = """You are an AI research assistant. Your task is to read the following arXiv paper's title, authors, and abstract, then generate a comprehensive summary in both English and Japanese.

The summary should:
1. Explain what problem the paper addresses (background/motivation)
2. Describe the key approach or methodology 
3. Highlight the main contributions or results
4. Be approximately 500 characters in English and 500 characters in Japanese (total ~1000 characters)
5. Be clear and understandable

Format your response as JSON:
{{
  "summary_en": "English summary here",
  "summary_ja": "日本語の要約をここに記載"
}}

Paper information:
Title: {title}
Authors: {authors}
Abstract: {abstract}

Generate the summary in JSON format:"""


def generate_summary(paper: Dict, model_name: str = "gpt-3.5-turbo") -> str:
    """
    単一の論文の要約を生成
    
    Args:
        paper: 論文情報（title, authors, abstract を含む辞書）
        model_name: 使用するOpenAIモデル
    
    Returns:
        str: 生成された要約（日本語）
    """
    prompt = SUMMARY_PROMPT.format(
        title=paper.get("title", ""),
        authors=paper.get("authors", ""),
        abstract=paper.get("abstract", "")
    )
    
    try:
        response = openai.ChatCompletion.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful research assistant that summarizes academic papers in both English and Japanese."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1200
        )
        
        content = response.choices[0].message.content.strip()
        
        # JSONパースを試みる
        import json
        import re
        
        # JSON部分を抽出
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            summary_data = json.loads(json_match.group())
            return {
                "summary_en": summary_data.get("summary_en", ""),
                "summary_ja": summary_data.get("summary_ja", "")
            }
        else:
            # JSON形式でない場合は空の辞書を返す
            return {"summary_en": content, "summary_ja": ""}
            
    except Exception as e:
        print(f"要約生成エラー: {str(e)}")
        return {"summary_en": "(Summary generation failed)", "summary_ja": "（要約生成に失敗しました）"}


def generate_summaries_batch(papers: List[Dict], model_name: str = "gpt-3.5-turbo") -> List[Dict]:
    """
    複数の論文の要約を一括生成
    
    Args:
        papers: 論文情報のリスト
        model_name: 使用するOpenAIモデル
    
    Returns:
        List[Dict]: 要約付きの論文情報リスト
    """
    print(f"\nGenerating summaries... ({len(papers)} papers)")
    
    for idx, paper in enumerate(papers, 1):
        print(f"  {idx}/{len(papers)}: {paper.get('title', '')[:60]}...")
        
        summary = generate_summary(paper, model_name)
        paper['summary'] = summary
        
        # Rate limit対策
        if idx < len(papers):
            time.sleep(1)
    
    print("Summary generation completed")
    return papers
