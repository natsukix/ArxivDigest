import os
import re
import io
import asyncio
import logging
import tempfile
import requests
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI
import discord
from discord.ext import commands

# PDF parsing: prefer pypdf (PyPDF2) or pdfplumber if available
try:
    from pypdf import PdfReader
except Exception:
    try:
        from PyPDF2 import PdfReader
    except Exception:
        PdfReader = None

load_dotenv()

LOGGER = logging.getLogger("discord_pdf_bot")
logging.basicConfig(level=logging.INFO)

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_FORUM_CHANNEL_ID = int(os.getenv("DISCORD_FORUM_CHANNEL_ID", "0"))  # 毎日の論文ピックアップフォーラム
DISCORD_ARXIV_ANALYSIS_CHANNEL_ID = int(os.getenv("DISCORD_ARXIV_ANALYSIS_CHANNEL_ID", "0"))  # 分析結果投稿先
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MAX_TOKENS_PER_CHUNK = int(os.getenv("MAX_TOKENS_PER_CHUNK", "4000"))
REACTION_EMOJI = os.getenv("REACTION_EMOJI", "🔍")  # リアクション対象の絵文字
PDF_ANALYSIS_MODEL = os.getenv("PDF_ANALYSIS_MODEL", "gpt-4o-mini")  # .env から読み込む

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# 環境変数の確認ログ
print(f"\n=== BOT CONFIGURATION ===")
print(f"DISCORD_BOT_TOKEN: {'SET' if DISCORD_BOT_TOKEN else 'NOT SET'}")
print(f"DISCORD_FORUM_CHANNEL_ID: {DISCORD_FORUM_CHANNEL_ID}")
print(f"DISCORD_ARXIV_ANALYSIS_CHANNEL_ID: {DISCORD_ARXIV_ANALYSIS_CHANNEL_ID}")
print(f"OPENAI_API_KEY: {'SET' if OPENAI_API_KEY else 'NOT SET'}")
print(f"REACTION_EMOJI: '{REACTION_EMOJI}'")
print(f"PDF_ANALYSIS_MODEL: {PDF_ANALYSIS_MODEL}")
print(f"========================\n")

intents = discord.Intents.all()  # すべてのIntentを有効化
intents.reactions = True  # リアクションイベントを受け取るために必要
bot = commands.Bot(command_prefix="!", intents=intents)

# ThreadPoolExecutor で OpenAI API を非同期実行
executor = ThreadPoolExecutor(max_workers=2)

ARXIV_PDF_RE = re.compile(r"(?:https?://)?(?:www\.)?arxiv\.org/(?:pdf|abs)/([0-9.]+v?\d*)")

async def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    if PdfReader is None:
        raise RuntimeError("No PDF reader available (install pypdf or PyPDF2)")

    with io.BytesIO(pdf_bytes) as fh:
        reader = PdfReader(fh)
        texts = []
        for page in reader.pages:
            try:
                txt = page.extract_text() or ""
            except Exception:
                txt = ""
            texts.append(txt)
    return "\n".join(texts)


def split_discord_message(text: str, max_length: int = 2000) -> list:
    """
    Discordの文字制限（2000文字）に合わせてテキストを分割
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


async def analyze_text_with_openai(text: str, paper_id: str) -> tuple:
    """
    分析結果を日本語と英語に分割して返す
    Returns: (japanese_analysis, english_analysis)
    """
    prompt = f"""
You are a research assistant. Analyze the following arXiv paper (id: {paper_id}).

Provide analysis in BOTH Japanese and English in the following format:

## 日本語での分析
- 短い要約（1-2文）
- 主な貢献（箇条書き）
- コア技術的アプローチ（簡潔に）
- 主要な実験結果
- 制限事項と今後の展望

## English Analysis
- Short summary (1-2 sentences)
- Main contributions (bullet points)
- Core technical approach (concise)
- Key experimental results
- Limitations and potential next steps

Use Markdown format.

Paper text (first 100k chars):\n
{text[:100000]}
"""
    
    response = client.chat.completions.create(
        model=PDF_ANALYSIS_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    content = response.choices[0].message.content
    
    # レスポンスを日本語と英語に分割
    # "## English Analysis" で分割
    parts = content.split("## English Analysis")
    japanese_analysis = parts[0].replace("## 日本語での分析", "").strip()
    english_analysis = parts[1].strip() if len(parts) > 1 else ""
    
    return japanese_analysis, english_analysis


def analyze_text_with_openai_sync(text: str, paper_id: str) -> tuple:
    """同期版 (ThreadPoolExecutor で実行用)"""
    return asyncio.run(analyze_text_with_openai(text, paper_id))


@bot.event
async def on_ready():
    LOGGER.info(f"Bot ready: {bot.user}")
    LOGGER.info(f"Bot intents: {bot.intents}")


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """Raw リアクションイベント（フォーラム含む）"""
    LOGGER.info(f"=== ON_RAW_REACTION_ADD CALLED ===")
    LOGGER.info(f"Payload: user_id={payload.user_id}, channel_id={payload.channel_id}, message_id={payload.message_id}, emoji={payload.emoji}")
    
    # ボット自身のリアクションは無視
    if payload.user_id == bot.user.id:
        LOGGER.info("Ignoring bot reaction")
        return
    
    # チャンネルまたはスレッドを取得
    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(payload.channel_id)
        except Exception as e:
            LOGGER.error(f"Failed to fetch channel: {e}")
            return
    
    # フォーラムチャンネルか、スレッド（親がフォーラム）か確認
    is_forum_post = False
    if hasattr(channel, 'parent_id') and channel.parent_id == DISCORD_FORUM_CHANNEL_ID:
        # スレッド（フォーラム投稿）
        is_forum_post = True
        LOGGER.info(f"✅ Thread in forum: parent_id={channel.parent_id}")
    elif payload.channel_id == DISCORD_FORUM_CHANNEL_ID:
        # フォーラムチャンネル直下（ただし通常はこないはず）
        is_forum_post = True
        LOGGER.info(f"✅ Direct forum channel")
    else:
        LOGGER.warning(f"Not in target forum: channel_id={payload.channel_id}, parent_id={getattr(channel, 'parent_id', None)}")
        return
    
    # 指定されたリアクション絵文字か確認
    if str(payload.emoji) != REACTION_EMOJI:
        LOGGER.warning(f"Wrong emoji: {str(payload.emoji)} != {REACTION_EMOJI}")
        return
    
    LOGGER.info(f"✅ All conditions matched! Processing reaction...")
    
    # メッセージを取得
    try:
        channel = bot.get_channel(payload.channel_id)
        if channel is None:
            channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
    except Exception as e:
        LOGGER.error(f"Failed to fetch message: {e}")
        return
    
    LOGGER.info(f"Message content: {message.content[:100]}")

    # メッセージからarXivリンクを抽出
    m = ARXIV_PDF_RE.search(message.content)
    if not m:
        LOGGER.warning("No arXiv link found in message")
        return

    arxiv_id = m.group(1)
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    LOGGER.info(f"Detected arXiv id: {arxiv_id} -> {pdf_url}")

    # 分析用チャンネルを取得
    try:
        analysis_channel = await bot.fetch_channel(DISCORD_ARXIV_ANALYSIS_CHANNEL_ID)
    except Exception as e:
        LOGGER.error(f"Failed to fetch analysis channel: {e}")
        return

    # ステータスメッセージを投稿（フォーラムなので新しいスレッドを作成）
    try:
        # REST API を使用してスレッドを作成
        url = f"https://discord.com/api/v10/channels/{DISCORD_ARXIV_ANALYSIS_CHANNEL_ID}/threads"
        headers = {
            "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "name": f"Analysis: arXiv:{arxiv_id}",
            "message": {
                "content": f"🔎 Downloading and analyzing arXiv:{arxiv_id} from {message.author}..."
            }
        }
        
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code not in [200, 201]:
            LOGGER.error(f"Failed to create thread: {response.status_code} - {response.text}")
            return
        
        thread_data = response.json()
        thread_id = thread_data.get('id')
        thread = await bot.fetch_channel(thread_id)
        LOGGER.info(f"✓ Thread created: ID={thread_id}")
        
    except Exception as e:
        LOGGER.error(f"Failed to create thread: {e}")
        return

    try:
        r = requests.get(pdf_url, timeout=30)
        r.raise_for_status()
        pdf_bytes = r.content

        text = await extract_text_from_pdf_bytes(pdf_bytes)
        
        # OpenAI API を ThreadPoolExecutor で非同期実行
        loop = asyncio.get_event_loop()
        japanese_analysis, english_analysis = await loop.run_in_executor(
            executor, 
            lambda: analyze_text_with_openai_sync(text, arxiv_id)
        )

        # メッセージ1: オリジナル投稿情報
        original_info = f"""🔗 **Original Post Information**
**arXiv ID:** {arxiv_id}
**URL:** https://arxiv.org/abs/{arxiv_id}
**Posted by:** {message.author}
**Original message:** [Link]({message.jump_url})
"""
        await thread.send(original_info)
        
        # メッセージ2: 日本語の分析（長い場合は分割）
        japanese_header = "📖 **日本語での分析**\n\n"
        japanese_chunks = split_discord_message(japanese_analysis, max_length=1900)
        for i, chunk in enumerate(japanese_chunks):
            if i == 0:
                msg = japanese_header + chunk
            else:
                msg = f"**(続き)**\n{chunk}"
            await thread.send(msg)
        
        # メッセージ3: 英語の分析（長い場合は分割）
        english_header = "📝 **English Analysis**\n\n"
        english_chunks = split_discord_message(english_analysis, max_length=1900)
        for i, chunk in enumerate(english_chunks):
            if i == 0:
                msg = english_header + chunk
            else:
                msg = f"**(Continued)**\n{chunk}"
            await thread.send(msg)
        
        LOGGER.info(f"✅ Analysis completed and posted for arXiv:{arxiv_id}")

    except Exception as e:
        LOGGER.exception("Failed to analyze PDF")
        try:
            await thread.send(f"❌ Failed to analyze arXiv:{arxiv_id}: {str(e)[:200]}")
        except Exception:
            pass





if __name__ == '__main__':
    if not DISCORD_BOT_TOKEN:
        print("DISCORD_BOT_TOKEN not set, exiting")
        raise SystemExit(1)

    bot.run(DISCORD_BOT_TOKEN)
