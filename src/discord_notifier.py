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


def format_papers_for_discord(papers_html, topic, categories, threshold):
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
    header += f"該当論文数: {len(papers_list)}件\n"
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
        header, papers_list = format_papers_for_discord(papers_html, topic, categories, threshold)
        
        # ヘッダーを送信
        payload = {
            "content": header,
            "username": "ArxivDigest Bot"
        }
        response = requests.post(webhook_url, json=payload)
        
        if response.status_code not in [200, 204]:
            print(f"Discordへの投稿に失敗しました: {response.status_code}")
            return False
        
        print(f"✓ Discordにヘッダーを投稿しました")
        
        # 要約付き論文がある場合は個別投稿（上限5件）
        if papers_with_summary:
            max_papers = 5
            display_papers = papers_with_summary[:max_papers]
            
            import time
            for idx, paper in enumerate(display_papers, 1):
                title = paper.get('title', 'タイトル不明')
                authors = paper.get('authors', '著者不明')
                link = paper.get('main_page', '')
                score = paper.get('Relevancy score', 'N/A')
                reason = paper.get('Reasons for match', '')
                summary = paper.get('summary', {})
                summary_en = summary.get('summary_en', '') if isinstance(summary, dict) else ''
                summary_ja = summary.get('summary_ja', '') if isinstance(summary, dict) else ''
                
                # 1論文ごとに1メッセージ
                paper_content = f"**【論文 {idx}/{min(len(papers_with_summary), max_papers)}】**\n\n"
                paper_content += f"**📚 {title}**\n\n"
                paper_content += f"**� 著者:** {authors}\n"
                paper_content += f"**⭐ 関連性スコア:** {score}/10\n\n"
                
                if reason:
                    paper_content += f"**💡 なぜ重要か:**\n{reason}\n\n"
                
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
                    print(f"論文 {idx} の投稿に失敗しました: {response.status_code}")
                    continue
                
                print(f"✓ 論文 {idx}/{min(len(papers_with_summary), max_papers)} を投稿しました")
                
                # Rate limit対策
                if idx < len(display_papers):
                    time.sleep(1.5)
            
            # フッター投稿
            if len(papers_with_summary) > max_papers:
                footer_content = f"\n📊 **その他の論文:** 他に {len(papers_with_summary) - max_papers} 件の重要論文があります（digest.htmlを参照）"
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
                print(f"論文リストの投稿に失敗しました: {response.status_code}")
                return False
            
            print(f"✓ 論文リストを投稿しました")
        
        total_count = len(papers_with_summary) if papers_with_summary else len(papers_list)
        display_count = min(total_count, 5 if papers_with_summary else 10)
        print(f"\n🎉 Discord投稿完了！ {display_count}件の論文を投稿しました（全{total_count}件中）")
        return True
        
    except Exception as e:
        print(f"Discordへの投稿中にエラーが発生しました: {e}")
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
