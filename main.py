import config
import os
import asyncio
import random
import logging
from telethon import TelegramClient
from telethon.network import ConnectionTcpAbridged
from telethon.errors import (
    SessionPasswordNeededError,
    FloodWaitError,
    ChatWriteForbiddenError
)
from telethon.tl.functions.messages import GetHistoryRequest

# የቴሌተን ሎግ ስህተቶች እንዳይመላ
logging.getLogger('telethon').setLevel(logging.CRITICAL)

# ─── የፋይል አቅጣጫዎች ───
FORWARD_SESSION_DIR = 'sessions_forward'

# ─── የምንሰበስብበት እና የምንልክባቸው ቻናሎች ───
SOURCE_CHANNEL = '@ET_TIKVAH'
TARGET_CHANNELS = [
    '@et_forward1',
    '@et_forward2',
    '@et_forward3',
    '@et_forward4',
    '@et_forward5',
    '@et_forward6',
    '@et_forward7',
    '@et_forward8'
]

def load_api_credentials():
    if hasattr(config, 'API_LIST') and len(config.API_LIST) > 0:
        return config.API_LIST[0]['id'], config.API_LIST[0]['hash']
    return None, None

async def login_account():
    print("\n" + "="*40)
    print("🔐 Auto Forward - Account Login")
    print("="*40)
    
    api_id, api_hash = load_api_credentials()
    if not api_id or not api_hash:
        print("❌ ከ config.py API መረጃ ማግኘት አልተቻለም!")
        return None

    phone = input("📱 የስልክ ቁጥር ያስገቡ (ለምሳሌ +2519...): ").strip()
    if not phone.startswith('+'):
        phone = '+' + phone

    if not os.path.exists(FORWARD_SESSION_DIR):
        os.makedirs(FORWARD_SESSION_DIR)

    session_path = os.path.join(FORWARD_SESSION_DIR, phone)
    
    client = TelegramClient(
        session_path, 
        api_id, 
        api_hash,
        connection=ConnectionTcpAbridged,
        connection_retries=5,
        retry_delay=2,
        timeout=30
    )
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(f"📤 ኮድ በመላክ ላይ ወደ {phone}...")
            await client.send_code_request(phone)
            
            code = input("🔢 የተላከውን ኮድ ያስገቡ: ").strip()
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("🔑 የ 2FA ፓስወርድ ያስገቡ: ").strip()
                await client.sign_in(password=password)
                
        me = await client.get_me()
        name = me.first_name if me.first_name else "Unknown"
        print(f"✅ በተሳካ ሁኔታ ገብቷል! እንደ {name} ({phone})")
        return client
            
    except Exception as e:
        print(f"❌ የመግቢያ ስህተት: {e}")
        try:
            await client.disconnect()
        except:
            pass
        return None

async def get_all_messages(client, channel):
    """በቻናሉ ውስጥ ያሉትን ሁሉንም መልዕክቶች በሙሉ የሚያነብ ተግባር (Looping)"""
    all_messages = []
    offset_id = 0
    limit = 100 

    print(f"🔍 ከ {channel} ሁሉንም ፖስቶች በማንበብ ላይ... (ይህ ረጅም ጊዜ ሊወስድ ይችላል)")

    while True:
        try:
            history = await client(GetHistoryRequest(
                peer=channel,
                limit=limit,
                offset_date=None,
                offset_id=offset_id,
                max_id=0,
                min_id=0,
                add_offset=0,
                hash=0
            ))
            
            if not history.messages:
                break
                
            messages = history.messages
            all_messages.extend(messages)
            offset_id = messages[-1].id
            
            print(f"  ⏳ {len(all_messages)} ፖስቶች ተነብበዋል...")
            
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"⚠️ ፖስቶችን በማንበብ ላይ ስህተት: {e}")
            break

    print(f"✅ በአጠቃላይ {len(all_messages)} ፖስቶች በተሳካ ሁኔታ ተነብበዋል።\n")
    return all_messages

async def auto_forward_task(client):
    """የማስተላለፍ ስራ (Forwarding Loop)"""
    print("\n🚀 Auto Forward ስራ ተጀምሯል!")
    print(f"📥 ምንጭ: {SOURCE_CHANNEL}")
    print(f"📤 መዳረሻ: {len(TARGET_CHANNELS)} ቻናሎች")
    print("⏳ በየ 5-10 ደቂቃው በራሱ ያስተላልፋል...\n")

    # በየሉፑ መጀመሪያ ላይ ፖስቶችን እናንብብ
    all_posts = await get_all_messages(client, SOURCE_CHANNEL)
    
    if not all_posts:
        print("❌ በምንጩ ቻናል ውስጥ ምንም ፖስት አልተገኘም። ስራው ተቋርጧል።")
        return

    while True:
        try:
            # ወደ ሁሉም ቻናሎች ማስተላለፍ
            success_count = 0
            for target in TARGET_CHANNELS:
                try:
                    # ⭐ [ማሻሻያ]፡ ለእያንዳንዱ ቻናል የተለየ ፖስት በዘፈቀደ መምረጥ
                    random_post = random.choice(all_posts)
                    
                    await client.forward_messages(
                        entity=target, 
                        messages=random_post
                    )
                    print(f"  ✅ ወደ {target} ተልኳል (ፖስት ID: {random_post.id})")
                    success_count += 1
                    await asyncio.sleep(2) # ስፓም እንዳይሆን ትንሽ ማቆየት
                except ChatWriteForbiddenError:
                    print(f"  ❌ ወደ {target} መላክ አልተቻለም (Admin አይደለም)")
                except FloodWaitError as e:
                    print(f"  ⏳ FloodWait: ለ {e.seconds} ሰከንድ ማቆየት አለበት።")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"  ❌ ወደ {target} መላክ አልተቻለም: {str(e)[:50]}")
            
            print(f"📊 የተሳካ: {success_count}/{len(TARGET_CHANNELS)} ቻናሎች\n")

        except Exception as e:
            print(f"⚠️ ዋና ስህተት: {e}\n")

        # 4. በዘፈቀደ ከ 5 እስከ 10 ደቂቃ (300 - 600 ሰከንድ) መጠበቅ
        wait_time = random.randint(300, 600)
        minutes = wait_time // 60
        seconds = wait_time % 60
        print(f"⏳ ቀጣዩ የማስተላለፍ ስራ ከ {minutes} ደቂቃ እና {seconds} ሰከንድ በኋላ ይጀምራል...\n")
        
        for _ in range(wait_time):
            await asyncio.sleep(1)

async def main():
    print("="*40)
    print("🤖 AUTO FORWARD BOT")
    print("="*40)

    client = await login_account()
    if not client:
        return

    try:
        await auto_forward_task(client)
    except KeyboardInterrupt:
        print("\n🛑 ስራው በ Ctrl+C ተቋርጧል!")
    finally:
        if client.is_connected():
            await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())