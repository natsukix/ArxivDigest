#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'src')
from download_new_papers import get_papers

# 1件だけ取得してテスト
papers = get_papers('cs', limit=3)
for i, paper in enumerate(papers):
    print(f"\nPaper {i+1}:")
    print(f"  Title: {paper.get('title', 'N/A')[:50]}...")
    print(f"  Main Page: {paper.get('main_page', 'N/A')}")
    print(f"  PDF: {paper.get('pdf', 'N/A')}")
