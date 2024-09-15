from aiogram.types import Message, CallbackQuery, ContentType
from loader import dp, db, bot
from aiogram import F
from aiogram import exceptions
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
import sqlite3

# SQLite database connection
conn = sqlite3.connect('channels.db')
cursor = conn.cursor()

# Kanallar jadvali yaratish (birinchi marta bo'lsa)
cursor.execute('''CREATE TABLE IF NOT EXISTS user_channels (
    user_id INTEGER,
    channel_id INTEGER,
    channel_title TEXT
)''')
conn.commit()

# ReplyKeyboardButton'lar
def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="✏️ 1-post yaratish")
    builder.button(text="📢 Mening kanallarim")
    builder.button(text="➕ Kanal qo'shish")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# Foydalanuvchiga kanallarini inline button sifatida ko'rsatish
async def show_user_channels(user_id):
    cursor.execute("SELECT channel_id, channel_title FROM user_channels WHERE user_id=?", (user_id, ))
    channels = cursor.fetchall()

    if channels:
        builder = InlineKeyboardBuilder()
        for channel in channels:
            builder.button(text=f"{channel[1]} (ID: {channel[0]})", callback_data=f"send_post_{channel[0]}")
        builder.adjust(1)
        return builder.as_markup()
    else:
        return None

# Foydalanuvchi uchun kanalni qo'shish
def add_user_channel(user_id, channel_id, channel_title):
    cursor.execute("INSERT INTO user_channels (user_id, channel_id, channel_title) VALUES (?, ?, ?)",
                   (user_id, channel_id, channel_title))
    conn.commit()

# Post qabul qilish
posts = {}

async def send_post_to_channel(channel_id, post_data):
    try:
        if post_data['type'] == 'text':
            await bot.send_message(chat_id=channel_id, text=post_data['content'], parse_mode="html")
        elif post_data['type'] == 'photo':
            await bot.send_photo(chat_id=channel_id, photo=post_data['content'], caption=post_data.get('text', ''), parse_mode="html")
        elif post_data['type'] == 'video':
            await bot.send_video(chat_id=channel_id, video=post_data['content'], caption=post_data.get('text', ''), parse_mode="html")
        elif post_data['type'] == 'audio':
            await bot.send_audio(chat_id=channel_id, audio=post_data['content'], caption=post_data.get('text', ''), parse_mode="html")
        elif post_data['type'] == 'sticker':
            await bot.send_sticker(chat_id=channel_id, sticker=post_data['content'])
        print("Post yuborildi.")
    except exceptions.TelegramForbiddenError:
        await bot.send_message(chat_id=channel_id, text="🚫 Kechirasiz, bot hali kanalning a'zosi emas yoki admin emas. Botni kanalga qo'shishni yoki admin huquqlarini berishni tekshiring.")
    except Exception as e:
        print(f"Post yuborishda xatolik: {e}")

@dp.message(CommandStart())
async def start_command(message: Message):
    full_name = message.from_user.full_name
    telegram_id = message.from_user.id
    try:
        db.add_user(full_name=full_name, telegram_id=telegram_id)  # Foydalanuvchi bazaga qo'shildi
        await message.answer(text="🌟 Assalomu alaykum, botimizga hush kelibsiz! 🌟", reply_markup=main_menu())
    except:
        await message.answer(text="🌟 Assalomu alaykum! 🌟", reply_markup=main_menu())

@dp.message(F.text == "📢 Mening kanallarim")
async def show_channels(message: Message):
    user_id = message.from_user.id
    channels_keyboard = await show_user_channels(user_id)
    
    if channels_keyboard:
        await message.answer("🔍 Sizning kanallaringiz:", reply_markup=channels_keyboard)
    else:
        await message.answer("📭 Sizda hali kanal qo'shilmagan. Kanalni forward qilib qo'shing yoki yangi kanal qo'shing.")

@dp.message(F.text == "➕ Kanal qo'shish")
async def add_channel_prompt(message: Message):
    await message.answer("📝 Kanalni qo'shish uchun, kanaldan xabarni forward qilib yuboring yoki kanal ID'sini kiriting.")

@dp.message(F.forward_from_chat)
async def handle_forwarded_channel(message: Message):
    if message.forward_from_chat.type == "channel":
        channel_id = message.forward_from_chat.id
        channel_title = message.forward_from_chat.title
        user_id = message.from_user.id
        add_user_channel(user_id, channel_id, channel_title)
        await message.answer(f"✅ Kanal qo'shildi: Nomi {channel_title} (ID: {channel_id})")
    else:
        await message.answer("⚠️ Iltimos, kanalni forward qiling yoki kanal ID'sini kiriting.")

# 1-post yaratish tugmasi bosilganda foydalanuvchidan postni kiritishni so'raydi
@dp.message(F.text == "✏️ 1-post yaratish")
async def prompt_post_creation(message: Message):
    await message.answer("📝 Iltimos, postingizni yozib yuboring yoki media yuboring (rasm, video, musiqa, sticker):")

@dp.message(F.content_type.in_([ContentType.TEXT, ContentType.PHOTO, ContentType.VIDEO, ContentType.AUDIO, ContentType.STICKER]))
async def handle_post_creation(message: Message):
    user_id = message.from_user.id
    post_type = None
    post_content = None
    post_text = None

    if message.text:
        post_type = 'text'
        post_content = message.text
    elif message.photo:
        post_type = 'photo'
        post_content = message.photo[-1].file_id
        post_text = message.caption or ''
    elif message.video:
        post_type = 'video'
        post_content = message.video.file_id
        post_text = message.caption or ''
    elif message.audio:
        post_type = 'audio'
        post_content = message.audio.file_id
        post_text = message.caption or ''
    elif message.sticker:
        post_type = 'sticker'
        post_content = message.sticker.file_id

    if post_type and post_content:
        posts[user_id] = {'type': post_type, 'content': post_content, 'text': post_text}
        
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Postni tasdiqlash", callback_data="confirm_post")
        builder.button(text="❌ Postni bekor qilish", callback_data="cancel_post")
        builder.adjust(2)
        
        post_preview = post_text if post_text else "🖼️ Media: " + post_content
        await message.answer(f"📩 Post qabul qilindi:\n\n{post_preview}", reply_markup=builder.as_markup())
    else:
        await message.answer("❌ Qo'llab-quvvatlanmaydigan format. Iltimos, matn, rasm, video, musiqa yoki sticker yuboring.")

@dp.callback_query(F.data == "confirm_post")
async def confirm_post(call: CallbackQuery):
    user_id = call.from_user.id
    channels_keyboard = await show_user_channels(user_id)
    
    if channels_keyboard:
        await call.message.answer("📢 Qaysi kanalga postni yubormoqchisiz?", reply_markup=channels_keyboard)
        await call.message.delete()
    else:
        await call.message.answer("📭 Sizda hali kanal qo'shilmagan.")

@dp.callback_query(F.data == "cancel_post")
async def cancel_post(call: CallbackQuery):
    user_id = call.from_user.id
    
    # Remove the message that contains the post preview
    await call.message.delete()

    # Send a message with the main menu
    await call.message.answer("🚫 Post bekor qilindi.", reply_markup=main_menu())

@dp.callback_query(F.data.startswith("send_post_"))
async def handle_post_sending(call: CallbackQuery):
    user_id = call.from_user.id
    channel_id = call.data.split("_")[2]
    
    post = posts.get(user_id)
    
    if post:
        await send_post_to_channel(channel_id, post)
        await call.message.answer(f"✅ Post {channel_id} kanaliga yuborildi:\n\n{post['content']}")
        await call.message.delete()
    else:
        await call.message.answer("⚠️ Xatolik yuz berdi, post topilmadi.")
