import os
import re
import io
import asyncio
import logging
import tempfile
import requests
from dotenv import load_dotenv

import openai
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

openai.api_key = OPENAI_API_KEY

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True  # リアクションイベントを受け取るために必要
bot = commands.Bot(command_prefix="!", intents=intents)

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


async def analyze_text_with_openai(text: str, paper_id: str) -> str:
    prompt = f"""
You are a research assistant. Analyze the following arXiv paper (id: {paper_id}). Provide:
- Short 1-2 sentence summary
- Main contributions (bullet list)
- Core technical approach (concise)
- Key experimental results
- Limitations and potential next steps
Reply in Markdown.

Paper text (first 100k chars):\n
{text[:100000]}
"""
    # Use OpenAI ChatCompletion (OpenAI 1.3.0互換)
    try:
        # まず互換性シムを試す
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.1,
        )
        return response.choices[0].message.content
    except Exception:
        # フォールバック：OpenAI 1.3.0直接使用
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.1,
        )
        return response.choices[0].message.content


@bot.event
async def on_ready():
    LOGGER.info(f"Bot ready: {bot.user}")


@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    """リアクション追加時に、フォーラムチャンネルかつ指定の絵文字でのみ処理"""
    # ボット自身のリアクションは無視
    if user.bot:
        return

    LOGGER.info(f"Reaction added: {reaction.emoji} by {user} in channel {reaction.message.channel.id}")
    LOGGER.info(f"Expected channel: {DISCORD_FORUM_CHANNEL_ID}, Expected emoji: {REACTION_EMOJI}")

    # 対象のフォーラムチャンネルか確認
    if reaction.message.channel.id != DISCORD_FORUM_CHANNEL_ID:
        LOGGER.warning(f"Reaction in wrong channel: {reaction.message.channel.id}")
        return

    # 指定されたリアクション絵文字か確認
    if str(reaction.emoji) != REACTION_EMOJI:
        LOGGER.warning(f"Wrong emoji: {str(reaction.emoji)} != {REACTION_EMOJI}")
        return

    message = reaction.message
    LOGGER.info(f"Reaction detected on message from {message.author}: {message.content[:50]}")

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

    # ステータスメッセージを投稿
    status_msg = await analysis_channel.send(f"🔎 Downloading and analyzing arXiv:{arxiv_id} from {message.author}...")

    try:
        r = requests.get(pdf_url, timeout=30)
        r.raise_for_status()
        pdf_bytes = r.content

        text = await extract_text_from_pdf_bytes(pdf_bytes)
        summary = await analyze_text_with_openai(text, arxiv_id)

        # 分析結果を投稿タイトルと本文で構成
        title = f"Analysis: arXiv:{arxiv_id}"
        
        # フォーラムに新しい投稿を作成
        thread = await analysis_channel.create_thread(
            name=title,
            content=f"**Original message:** {message.jump_url}\n**Author:** {message.author}\n\n{summary}"
        )
        await status_msg.edit(content=f"✅ Analysis completed for arXiv:{arxiv_id}\nResult: {thread.jump_url}")

    except Exception as e:
        LOGGER.exception("Failed to analyze PDF")
        try:
            await status_msg.edit(content=f"❌ Failed to analyze arXiv:{arxiv_id}: {str(e)[:100]}")
        except Exception:
            pass


if __name__ == '__main__':
    if not DISCORD_BOT_TOKEN:
        print("DISCORD_BOT_TOKEN not set, exiting")
        raise SystemExit(1)

    bot.run(DISCORD_BOT_TOKEN)
