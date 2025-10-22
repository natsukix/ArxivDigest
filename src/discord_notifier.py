"""
Discord Webhook通知機能
"""
import requests
import json
from datetime import date


def split_message(text, max_length=2000):
    """
    Discordのメッセージ長制限(2000文字)に合わせてテキストを分割
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    for line in text.split('\n'):
        if len(current_chunk) + len(line) + 1 > max_length:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = line
        else:
            if current_chunk:
                current_chunk += '\n' + line
            else:
                current_chunk = line
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def html_to_discord_markdown(html_text):
    """
    HTMLをDiscordのMarkdown形式に変換
    """
    # 簡易的な変換
    text = html_text.replace('<br>', '\n')
    text = text.replace('<br/>', '\n')
    text = text.replace('<br />', '\n')
    
    # リンクの変換: <a href="url">text</a> -> [text](url)
    import re
    text = re.sub(r'<a href="([^"]+)">([^<]+)</a>', r'[\2](\1)', text)
    
    # その他のHTMLタグを削除
    text = re.sub(r'<[^>]+>', '', text)
    
    return text


def format_papers_for_discord(papers_html, topic, categories, threshold, paper_count=None):
    """
    論文情報をDiscord用にフォーマット
    """
    papers_text = html_to_discord_markdown(papers_html)
    papers_list = papers_text.split('\n\n')
    
    # ヘッダー
    today = date.today().strftime('%Y年%m月%d日')
    header = f"📚 **arXiv論文ダイジェスト - {today}**\n"
    header += f"トピック: {topic}\n"
    if categories:
        header += f"カテゴリ: {', '.join(categories)}\n"
    header += f"関連性スコア閾値: {threshold}以上\n"
    # paper_countが指定されていればそれを使用、なければpapers_listの長さ
    count = paper_count if paper_count is not None else len(papers_list)
    header += f"該当論文数: {count}件\n"
    header += "─" * 40 + "\n\n"
    
    return header, papers_list


def send_to_discord(webhook_url, papers_html, topic, categories, threshold, papers_with_summary=None):
    """
    Discord Webhookに論文情報を投稿
    
    Args:
        webhook_url: Discord Webhook URL
        papers_html: HTML形式の論文リスト
        topic: トピック名
        categories: カテゴリリスト
        threshold: 関連性スコア閾値
        papers_with_summary: 要約付き論文リスト（オプション）
    
    Returns:
        bool: 成功した場合True
    """
    if not webhook_url:
        print("Discord Webhook URLが設定されていません。スキップします。")
        return False
    
    try:
        # 実際の論文数を計算（papers_with_summaryがある場合はそれを使用）
        actual_paper_count = len(papers_with_summary) if papers_with_summary else None
        header, papers_list = format_papers_for_discord(papers_html, topic, categories, threshold, paper_count=actual_paper_count)
        
        # ヘッダーを送信
        payload = {
            "content": header,
            "username": "ArxivDigest Bot"
        }
        response = requests.post(webhook_url, json=payload)
        
        if response.status_code not in [200, 204]:
            print(f"Failed to post to Discord: {response.status_code}")
            return False
        
        print(f"Posted header to Discord")
        
        # 要約付き論文がある場合は個別投稿（カテゴリ毎に上位2件）
        if papers_with_summary:
            import time
            from relevancy import process_subject_fields
            
            # カテゴリ毎に論文を分類
            papers_by_category = {}
            for paper in papers_with_summary:
                processed_subjects = process_subject_fields(paper.get('subjects', ''))
                # 指定カテゴリに該当するものを分類
                matched_category = None
                for cat in categories:
                    if cat in processed_subjects:
                        matched_category = cat
                        break
                
                if matched_category:
                    if matched_category not in papers_by_category:
                        papers_by_category[matched_category] = []
                    papers_by_category[matched_category].append(paper)
            
            print(f"\n=== Discord投稿: カテゴリ毎に上位2件 ===")
            total_posted = 0
            max_per_category = 2
            
            for category, cat_papers in papers_by_category.items():
                # 上位2件を投稿
                display_papers = cat_papers[:max_per_category]
                for idx, paper in enumerate(display_papers, 1):
                    title = paper.get('title', 'タイトル不明')
                    authors = paper.get('authors', '著者不明')
                    
                    # リンクを取得（複数の可能性をチェック）
                    main_page = paper.get('main_page') or paper.get('link') or paper.get('url') or ''
                    
                    # PDFリンクに変換
                    if main_page and '/abs/' in main_page:
                        link = main_page.replace('/abs/', '/pdf/') + '.pdf'
                    elif main_page:
                        link = main_page
                    else:
                        link = '（リンク情報なし）'
                    score = paper.get('Relevancy score', 'N/A')
                    reason_en = paper.get('Reasons for match', '')
                    reason_ja = paper.get('Reasons for match (ja)', '')
                    summary = paper.get('summary', {})
                    summary_en = summary.get('summary_en', '') if isinstance(summary, dict) else ''
                    summary_ja = summary.get('summary_ja', '') if isinstance(summary, dict) else ''
                    
                    # 1論文を1つのメッセージにまとめる（カテゴリヘッダー含む）
                    paper_content = f"━━━━━━━━━━━━━━━━━━━━\n"
                    paper_content += f"**📂 カテゴリ: {category}** ({len(cat_papers)}件中 {idx}/{min(len(cat_papers), max_per_category)}件目)\n"
                    paper_content += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    paper_content += f"**📚 {title}**\n\n"
                    paper_content += f"**👥 著者:** {authors}\n"
                    paper_content += f"**⭐ 関連性スコア:** {score}/10\n\n"
                    
                    # 日本語と英語の両方を表示
                    if reason_ja:
                        paper_content += f"**💡 なぜ重要か（日本語）:**\n{reason_ja}\n\n"
                    if reason_en:
                        paper_content += f"**💡 Why Important (English):**\n{reason_en}\n\n"
                    
                    if summary_ja:
                        paper_content += f"**📄 要約（日本語）:**\n{summary_ja}\n\n"
                    
                    if summary_en:
                        paper_content += f"**📄 Summary (English):**\n{summary_en}\n\n"
                    
                    paper_content += f"**🔗 リンク:** {link}\n"
                    paper_content += "─" * 40
                    
                    # 2000文字制限チェック
                    if len(paper_content) > 1950:
                        paper_content = paper_content[:1950] + "\n\n... (要約が長すぎるため省略)"
                    
                    payload = {
                        "content": paper_content,
                        "username": "ArxivDigest Bot"
                    }
                    response = requests.post(webhook_url, json=payload)
                    
                    if response.status_code not in [200, 204]:
                        print(f"Failed to post paper: {response.status_code}")
                        continue
                    
                    total_posted += 1
                    print(f"Posted {category}: paper {idx}/{min(len(cat_papers), max_per_category)}")
                    
                    # Rate limit対策
                    time.sleep(1.5)
            
            # 総計フッター
            total_papers = sum(len(papers) for papers in papers_by_category.values())
            footer_content = f"\n📊 **投稿完了:** 全{total_posted}件の論文を投稿しました（全{total_papers}件中）"
            footer_payload = {
                "content": footer_content,
                "username": "ArxivDigest Bot"
            }
            requests.post(webhook_url, json=footer_payload)
        else:
            # 要約なしの場合は従来の簡易形式
            max_papers = 10
            display_papers = papers_list[:max_papers]
            
            if len(papers_list) > max_papers:
                footer = f"\n\n... 他 {len(papers_list) - max_papers} 件の論文があります（digest.htmlを参照）"
            else:
                footer = ""
            
            papers_content = ""
            for idx, paper in enumerate(display_papers, 1):
                if paper.strip():
                    papers_content += f"\n**【{idx}】**\n{paper.strip()}\n"
            
            papers_content += footer
            
            if len(papers_content) > 1900:
                papers_content = papers_content[:1900] + "\n\n... (メッセージが長すぎるため省略)"
            
            payload = {
                "content": papers_content,
                "username": "ArxivDigest Bot"
            }
            response = requests.post(webhook_url, json=payload)
            
            if response.status_code not in [200, 204]:
                print(f"Failed to post paper list: {response.status_code}")
                return False
            
            print(f"Posted paper list to Discord")
        
        total_count = len(papers_with_summary) if papers_with_summary else len(papers_list)
        display_count = min(total_count, 5 if papers_with_summary else 10)
        print(f"\nDiscord posting completed! Posted {display_count} papers (out of {total_count} total)")
        return True
        
    except Exception as e:
        print(f"Discordへの投稿中にエラーが発生しました: {e}")
        return False


def send_to_discord_forum(bot_token, forum_channel_id, papers_html, topic, categories, threshold, papers_with_summary=None):
    """
    Discordのフォーラムチャンネルに1日1トピックとして投稿
    
    Args:
        bot_token: Discord Bot Token
        forum_channel_id: フォーラムチャンネルのID
        papers_html: HTML形式の論文リスト
        topic: トピック名
        categories: カテゴリリスト
        threshold: 関連性スコア閾値
        papers_with_summary: 要約付き論文リスト（オプション）
    
    Returns:
        bool: 成功した場合True
    """
    if not bot_token or not forum_channel_id:
        print("Discord Bot TokenまたはForum Channel IDが設定されていません。")
        return False
    
    try:
        import time
        
        # 実際の論文数を計算
        actual_paper_count = len(papers_with_summary) if papers_with_summary else None
        header, papers_list = format_papers_for_discord(papers_html, topic, categories, threshold, paper_count=actual_paper_count)
        
        # スレッド（トピック）のタイトル
        today = date.today().strftime('%Y年%m月%d日')
        thread_name = f"📚 arXiv論文ダイジェスト - {today}"
        
        # API endpoint
        url = f"https://discord.com/api/v10/channels/{forum_channel_id}/threads"
        
        headers = {
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json"
        }
        
        # 最初の投稿内容（スレッド作成時の初回メッセージ）
        initial_message = header
        if actual_paper_count and actual_paper_count > 0:
            initial_message += "\n詳細は以下の返信をご覧ください 👇"
        else:
            initial_message += "\n該当する論文がありませんでした。"
        
        # スレッド作成
        payload = {
            "name": thread_name,
            "message": {
                "content": initial_message
            }
        }
        
        print(f"Creating forum thread: {thread_name}")
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code not in [200, 201]:
            print(f"Failed to create forum thread: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        thread_data = response.json()
        thread_id = thread_data.get('id')
        print(f"✓ Forum thread created: ID={thread_id}")
        
        # 論文を投稿
        if papers_with_summary and len(papers_with_summary) > 0:
            from relevancy import process_subject_fields
            
            # カテゴリ毎に論文を分類
            papers_by_category = {}
            for paper in papers_with_summary:
                processed_subjects = process_subject_fields(paper.get('subjects', ''))
                matched_category = None
                for cat in categories:
                    if cat in processed_subjects:
                        matched_category = cat
                        break
                
                if matched_category:
                    if matched_category not in papers_by_category:
                        papers_by_category[matched_category] = []
                    papers_by_category[matched_category].append(paper)
            
            print(f"\n=== Posting to forum thread: Top 2 per category ===")
            total_posted = 0
            max_per_category = 2
            
            # スレッドにメッセージを投稿するエンドポイント
            message_url = f"https://discord.com/api/v10/channels/{thread_id}/messages"
            
            for category, cat_papers in papers_by_category.items():
                display_papers = cat_papers[:max_per_category]
                for idx, paper in enumerate(display_papers, 1):
                    title = paper.get('title', 'タイトル不明')
                    authors = paper.get('authors', '著者不明')
                    main_page = paper.get('main_page') or paper.get('link') or paper.get('url') or ''
                    
                    if main_page and '/abs/' in main_page:
                        pdf_link = main_page.replace('/abs/', '/pdf/')
                    else:
                        pdf_link = main_page
                    
                    score = paper.get('Relevancy score', 'N/A')
                    reasons = paper.get('Reasons for match', '理由なし')
                    
                    summary = paper.get('summary', {})
                    summary_ja = summary.get('summary_ja', '要約なし') if isinstance(summary, dict) else '要約なし'
                    
                    content = f"## 📄 {title}\n\n"
                    content += f"**著者:** {authors}\n"
                    content += f"**関連性スコア:** {score}/10\n"
                    content += f"**カテゴリ:** {category}\n\n"
                    content += f"**マッチ理由:**\n{reasons}\n\n"
                    content += f"**要約:**\n{summary_ja}\n\n"
                    content += f"🔗 [arXivページ]({main_page})"
                    if pdf_link and pdf_link != main_page:
                        content += f" | [PDF]({pdf_link})"
                    
                    # Discordの文字数制限（2000文字）に合わせて分割
                    chunks = split_message(content, max_length=1900)
                    
                    for chunk in chunks:
                        message_payload = {"content": chunk}
                        response = requests.post(message_url, headers=headers, json=message_payload)
                        
                        if response.status_code not in [200, 201]:
                            print(f"Failed to post message: {response.status_code}")
                            continue
                        
                        time.sleep(1.5)  # Rate limit対策
                    
                    total_posted += 1
                    print(f"✓ Posted {category}: paper {idx}/{min(len(cat_papers), max_per_category)}")
            
            # 完了フッター
            total_papers = sum(len(papers) for papers in papers_by_category.values())
            footer_content = f"📊 **投稿完了:** 全{total_posted}件の論文を投稿しました（全{total_papers}件中）"
            footer_payload = {"content": footer_content}
            requests.post(message_url, headers=headers, json=footer_payload)
            
            print(f"\n✓ Forum posting completed! Posted {total_posted} papers")
        
        return True
        
    except Exception as e:
        print(f"Discordフォーラムへの投稿中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False


def send_error_to_discord(webhook_url, error_message):
    """
    エラーメッセージをDiscordに投稿
    """
    if not webhook_url:
        return False
    
    try:
        today = date.today().strftime('%Y年%m月%d日')
        payload = {
            "content": f"⚠️ **ArxivDigest エラー - {today}**\n```\n{error_message}\n```",
            "username": "ArxivDigest Bot"
        }
        response = requests.post(webhook_url, json=payload)
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"エラーメッセージのDiscord投稿に失敗: {e}")
        return False
