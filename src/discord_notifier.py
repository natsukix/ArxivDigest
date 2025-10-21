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


def send_to_discord(webhook_url, papers_html, topic, categories, threshold):
    """
    Discord Webhookに論文情報を投稿
    
    Args:
        webhook_url: Discord Webhook URL
        papers_html: HTML形式の論文リスト
        topic: トピック名
        categories: カテゴリリスト
        threshold: 関連性スコア閾値
    
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
        
        # 論文リストを1つのメッセージにまとめる（上位10件まで）
        max_papers = 10
        display_papers = papers_list[:max_papers]
        
        if len(papers_list) > max_papers:
            footer = f"\n\n... 他 {len(papers_list) - max_papers} 件の論文があります（digest.htmlを参照）"
        else:
            footer = ""
        
        # 論文を番号付きでまとめる
        papers_content = ""
        for idx, paper in enumerate(display_papers, 1):
            if paper.strip():
                papers_content += f"\n**【{idx}】**\n{paper.strip()}\n"
        
        papers_content += footer
        
        # メッセージが長すぎる場合は分割して送信
        chunks = split_message(papers_content)
        
        for chunk_idx, chunk in enumerate(chunks, 1):
            payload = {
                "content": chunk,
                "username": "ArxivDigest Bot"
            }
            response = requests.post(webhook_url, json=payload)
            
            if response.status_code not in [200, 204]:
                print(f"チャンク {chunk_idx} の投稿に失敗しました: {response.status_code}")
                continue
            
            # Rate limit対策（少し待機）
            import time
            time.sleep(1)
            
            print(f"✓ チャンク {chunk_idx}/{len(chunks)} を投稿しました")
        
        print(f"\n🎉 Discord投稿完了！ {min(len(papers_list), max_papers)}件の論文を投稿しました（全{len(papers_list)}件中）")
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
