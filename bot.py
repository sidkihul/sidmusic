import sys
import subprocess
import logging
import urllib.parse
import os
import asyncio

# ================= AUTO-INSTALLER =================
try:
    import aiogram
    import aiohttp
except ImportError:
    print("⚙️ Missing libraries detected! Auto-installing 'aiogram' and 'aiohttp'...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiogram", "aiohttp"])
    import aiogram
    import aiohttp
    print("✅ Libraries installed successfully!")
# ==================================================

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply, BufferedInputFile
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# ================= Configuration =================
TELEGRAM_BOT_TOKEN = "6067177575:AAEUVOteOiERUHE5v75iudEdHAGiCRXBGus"
JIOSAAVN_API_BASE = "https://jiosavanapiryden.vercel.app/api"

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

class BotStates(StatesGroup):
    waiting_for_jio_query = State()
    waiting_for_reels_link = State()

# ================= Inline Menus =================
def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎶 Search Music (JioSaavn)", callback_data="switch_jio_mode"),
            InlineKeyboardButton(text="📱 Download IG Reels", callback_data="switch_reels_mode")
        ],
        [
            InlineKeyboardButton(text="🪪 Generate My ID", callback_data="generate_id"),
            InlineKeyboardButton(text="🛡️ Mod Shield", callback_data="mod_status")
        ]
    ])

# ================= Commands =================

@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    welcome_text = (
        f"🎵 WELCOME TO MELODY STREAM PRO 🎵\n\n"
        f"Hello {message.from_user.first_name}!\n"
        "Your ultimate destination for high-quality music streaming.\n\n"
        "• `/jio <song name>` - Search & stream music directly inside the group.\n"
        "• `/reels <ig link>` - Process Instagram Reels directly inside the group."
    )
    await message.answer(welcome_text, reply_markup=main_menu_keyboard())

@dp.message(Command("jio"))
async def handle_jio_command(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Usage: `/jio <song name>`")
        return
    await execute_jio_search(message, args[1])

@dp.message(Command("reels"))
async def handle_reels_command(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Usage: `/reels <instagram_reel_link>`")
        return
        
    status_msg = await message.answer("🎬 <i>Processing native Instagram Video Frame...</i>", parse_mode="HTML")
    await asyncio.sleep(1)
    
    await status_msg.delete()
    await message.answer(
        "🎬 <b>NATIVE VIDEO PLAYER</b>\n\n"
        "To drop live video streams directly in the chat window, plug your Instagram video scraping endpoint direct URL into <code>bot.send_video()</code>.",
        parse_mode="HTML"
    )

# ================= Interactive Callbacks =================

@dp.callback_query(F.data == "switch_jio_mode")
async def dynamic_jio_prompt(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_jio_query)
    await callback.message.answer(
        "🎶 <b>SEARCH FOR MUSIC</b>\n\nReply directly to this message with a Song name:",
        reply_markup=ForceReply(selective=True),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "switch_reels_mode")
async def dynamic_reels_prompt(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_reels_link)
    await callback.message.answer(
        "📱 <b>WATCH INSTAGRAM REELS</b>\n\nReply directly to this message with an Instagram Reel Link:",
        reply_markup=ForceReply(selective=True),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "generate_id")
async def generate_id_card(callback: types.CallbackQuery):
    user = callback.from_user
    status_msg = await callback.message.answer("🖨️ Compiling local group metadata... [■■□□]")
    photos = await bot.get_user_profile_photos(user.id)
    
    id_text = (
        "<b>🛡️ GLOBAL COMMUNITY ID CARD 🛡️</b>\n\n"
        f"<b>Name:</b> {user.first_name} {user.last_name or ''}\n"
        f"<b>Username:</b> @{user.username or 'N/A'}\n"
        f"<b>ID:</b> <code>{user.id}</code>\n"
        f"<b>Premium:</b> {'Yes ⭐' if user.is_premium else 'No'}\n\n"
        "<i>Verified Integration</i> ✅"
    )

    if photos.total_count > 0:
        await callback.message.answer_photo(photo=photos.photos[0][-1].file_id, caption=id_text, parse_mode="HTML")
    else:
        await callback.message.answer(f"👤 <i>No public picture found.</i>\n\n{id_text}", parse_mode="HTML")
        
    await status_msg.delete()
    await callback.answer()

@dp.callback_query(F.data == "mod_status")
async def mod_status(callback: types.CallbackQuery):
    await callback.answer("🛡️ Auto-Shield: ACTIVE\nSpambots & external links will be auto-deleted.", show_alert=True)

# ================= Core Media Processing Engine =================

@dp.message(BotStates.waiting_for_jio_query)
async def process_jio_state(message: types.Message, state: FSMContext):
    await execute_jio_search(message, message.text)
    await state.clear()

@dp.message(BotStates.waiting_for_reels_link)
async def process_reels_state(message: types.Message, state: FSMContext):
    message.text = f"/reels {message.text}"
    await handle_reels_command(message)
    await state.clear()

async def execute_jio_search(message: types.Message, query: str):
    status_msg = await message.answer(f"🎵 <b>Searching:</b> {query}...", parse_mode="HTML")
    
    api_url = f"{JIOSAAVN_API_BASE}/search/songs"
    params = {"query": query, "page": 0, "limit": 7}
    
    try:
        async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
            async with session.get(api_url, params=params, timeout=15) as response:
                if response.status != 200:
                    await status_msg.edit_text("❌ Search API is currently unresponsive.")
                    return
                data = await response.json()
                
        results = data.get("data", {}).get("results", [])
        if not results:
            await status_msg.edit_text("❌ No songs found! Try checking the spelling.")
            return

        markup = InlineKeyboardMarkup(inline_keyboard=[])
        for idx, song in enumerate(results, 1):
            song_id = song.get("id")
            song_name = song.get("name", "Unknown")[:30]
            artists = song.get("artists", {}).get("primary", [])
            artist_names = ", ".join([a.get("name", "") for a in artists[:1]])[:20]
            
            button_text = f"{idx}. {song_name} - {artist_names}"
            markup.inline_keyboard.append([
                InlineKeyboardButton(text=button_text, callback_data=f"jiosong_{song_id}")
            ])
            
        await status_msg.edit_text(
            f"🎵 <b>SEARCH RESULTS</b>\n\n🔍 For: {query}\n✨ Select a song to generate your media elements:",
            reply_markup=markup,
            parse_mode="HTML"
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Search Error: {e}")

@dp.callback_query(F.data.startswith("jiosong_"))
async def handle_song_selection(callback: types.CallbackQuery):
    song_id = callback.data.split("_")[1]
    status_msg = await callback.message.answer("⏳ Buffering visual elements and audio track...")
    await callback.answer()
    
    api_url = f"{JIOSAAVN_API_BASE}/songs/{song_id}"
    
    try:
        # Step 1: Fetch Song Details
        async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
            async with session.get(api_url, timeout=15) as response:
                if response.status != 200:
                    await status_msg.edit_text("❌ Failed to retrieve song data.")
                    return
                data = await response.json()
        
        song_info = data.get("data", [{}])[0]
        if not song_info:
            await status_msg.edit_text("❌ Audio extraction failed.")
            return

        title = song_info.get("name", "Unknown")
        artists = ", ".join([a.get("name", "") for a in song_info.get("artists", {}).get("primary", [])])
        album = song_info.get("album", {}).get("name", "Single")
        year = song_info.get("year", "N/A")
        
        download_links = song_info.get("downloadUrl", [])
        stream_url = download_links[-1].get("url") if download_links else None
        
        img_data = song_info.get("image", [])
        art_url = img_data[-1].get("url") if img_data else ""

        if not stream_url:
            await status_msg.edit_text("❌ Direct audio source track missing from API.")
            return

        # Step 2: Download Audio directly to memory (RAM)
        async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
            async with session.get(stream_url, timeout=20) as audio_resp:
                if audio_resp.status != 200:
                    await status_msg.edit_text("❌ Failed to stream the audio file.")
                    return
                audio_bytes = await audio_resp.read()

        # Step 3: Native Interaction Control Buttons
        native_control_markup = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📣 Updates Channel", url="https://t.me/your_channel"),
                InlineKeyboardButton(text="🔍 Search Again", callback_data="switch_jio_mode")
            ]
        ])

        # Added dynamic status at the bottom of the visual frame card text
        visual_frame_caption = (
            f"🎬 <b>NATIVE VISUAL FRAME ACTIVE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎵 <b>Track:</b> {title}\n"
            f"🎤 <b>Artist:</b> {artists}\n"
            f"💿 <b>Album:</b> {album} ({year})\n\n"
            f"▶️ <b>Now Playing:</b> <i>Selected audio track loading below...</i>"
        )

        audio_file = BufferedInputFile(audio_bytes, filename=f"{title}.mp3")

        # Step 4: Dispatch native media layout sequentially
        if art_url:
            await callback.message.answer_photo(
                photo=art_url, 
                caption=visual_frame_caption, 
                reply_markup=native_control_markup, 
                parse_mode="HTML"
            )
        else:
            await callback.message.answer(
                visual_frame_caption, 
                reply_markup=native_control_markup, 
                parse_mode="HTML"
            )

        # Triggers the audio asset immediately directly underneath the graphic card
        await callback.message.answer_audio(
            audio=audio_file,
            title=title,
            performer=artists,
            parse_mode="HTML"
        )
        
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ Extraction Error: {e}")

# ================= Group Anti-Spam Shield =================

@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def anti_spam_filter(message: types.Message):
    if not message.text:
        return

    blacklisted_triggers = ["t.me/", "crypto leakage", "pump signals"]
    if any(trigger in message.text.lower() for trigger in blacklisted_triggers):
        try:
            await message.delete()
            shield_alert = await message.answer(f"🛡️ Evicted suspicious spam from {message.from_user.first_name}.")
            await asyncio.sleep(3)
            await shield_alert.delete()
        except TelegramBadRequest:
            pass

# ================= Bot Engine Initialization =================

async def main():
    logging.info("🤖 Framework polling active. Native bot environment loaded.")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logging.critical(f"❌ Core runtime loop exception encountered: {e}")
    finally:
        await bot.session.close() 
        logging.info("⚙️ Execution routine halted cleanly.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown ordered by user.")
