"""
Discord Bot権限の詳細診断スクリプト
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

bot_token = os.getenv("DISCORD_BOT_TOKEN")
forum_channel_id = os.getenv("DISCORD_FORUM_CHANNEL_ID")

print("=" * 70)
print("Discord Bot 権限診断")
print("=" * 70)

if not bot_token:
    print("\n❌ DISCORD_BOT_TOKEN が設定されていません")
    exit(1)

if not forum_channel_id:
    print("\n❌ DISCORD_FORUM_CHANNEL_ID が設定されていません")
    exit(1)

headers = {
    "Authorization": f"Bot {bot_token}",
    "Content-Type": "application/json"
}

print("\n[1] Bot情報の取得...")
print("-" * 70)

try:
    response = requests.get("https://discord.com/api/v10/users/@me", headers=headers)
    if response.status_code == 200:
        bot_info = response.json()
        print(f"✅ Bot認証成功")
        print(f"   Bot名: {bot_info.get('username')}")
        print(f"   Bot ID: {bot_info.get('id')}")
    else:
        print(f"❌ Bot認証失敗: {response.status_code}")
        print(f"   Response: {response.text}")
        exit(1)
except Exception as e:
    print(f"❌ エラー: {e}")
    exit(1)

print("\n[2] チャンネル情報の取得...")
print("-" * 70)

try:
    response = requests.get(
        f"https://discord.com/api/v10/channels/{forum_channel_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        channel_info = response.json()
        print(f"✅ チャンネル情報取得成功")
        print(f"   チャンネル名: {channel_info.get('name')}")
        print(f"   チャンネルタイプ: {channel_info.get('type')}")
        print(f"   タイプ説明:", end=" ")
        
        channel_type = channel_info.get('type')
        if channel_type == 15:
            print("フォーラムチャンネル ✅")
        elif channel_type == 0:
            print("テキストチャンネル ⚠️ (フォーラムではありません)")
        else:
            print(f"不明 ({channel_type})")
        
        print(f"   Guild ID: {channel_info.get('guild_id')}")
        
    elif response.status_code == 403:
        print(f"❌ アクセス拒否 (403)")
        print(f"   Response: {response.text}")
        print("\n原因の可能性:")
        print("   1. BotがこのサーバーにいないIntents設定が不足")
        print("   2. チャンネルへのアクセス権限がない")
        
    elif response.status_code == 404:
        print(f"❌ チャンネルが見つかりません (404)")
        print(f"   DISCORD_FORUM_CHANNEL_ID: {forum_channel_id}")
        print("\n確認事項:")
        print("   1. チャンネルIDが正しいか")
        print("   2. Discordで開発者モードが有効か")
        print("   3. フォーラムチャンネルを右クリック→IDをコピー")
        
    else:
        print(f"❌ エラー: {response.status_code}")
        print(f"   Response: {response.text}")
        
except Exception as e:
    print(f"❌ エラー: {e}")

print("\n[3] Bot権限の確認...")
print("-" * 70)

if response.status_code == 200:
    channel_info = response.json()
    guild_id = channel_info.get('guild_id')
    
    if guild_id:
        try:
            # Botのギルドメンバー情報を取得
            response = requests.get(
                f"https://discord.com/api/v10/guilds/{guild_id}/members/{bot_info['id']}",
                headers=headers
            )
            
            if response.status_code == 200:
                member_info = response.json()
                roles = member_info.get('roles', [])
                print(f"✅ Botはこのサーバーのメンバーです")
                print(f"   ロール数: {len(roles)}")
                
                # サーバー情報を取得して@everyoneの権限を確認
                response = requests.get(
                    f"https://discord.com/api/v10/guilds/{guild_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    guild_info = response.json()
                    print(f"   サーバー名: {guild_info.get('name')}")
                
            else:
                print(f"❌ Botはこのサーバーのメンバーではありません")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"⚠️ メンバー情報取得エラー: {e}")

print("\n" + "=" * 70)
print("診断完了")
print("=" * 70)

print("\n【推奨される対応】")
print()
print("1. Discord Developer Portalで以下を確認:")
print("   https://discord.com/developers/applications")
print()
print("2. あなたのアプリケーションを選択")
print()
print("3. 「OAuth2」→「URL Generator」で以下を選択:")
print("   - SCOPES: 「bot」にチェック")
print("   - BOT PERMISSIONS:")
print("     ✓ Send Messages")
print("     ✓ Send Messages in Threads")
print("     ✓ Create Public Threads")
print("     ✓ Manage Threads")
print()
print("4. 生成されたURLからBotを再招待")
print()
print("5. Discordサーバーのフォーラムチャンネルで:")
print("   - チャンネル設定 → 権限")
print("   - Botのロールを追加")
print("   - 「メッセージを送信」「スレッドを作成」を許可")
print()
