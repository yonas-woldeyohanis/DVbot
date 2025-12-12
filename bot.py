import asyncio
import logging
import os
from dotenv import load_dotenv
from ai_service import ask_gemini

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from texts import TRANS

# 1. SETUP
load_dotenv() 
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not TOKEN:
    print("Error: BOT_TOKEN not found!")
    exit()

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# 2. STATES
class DVFlow(StatesGroup):
    choosing_lang = State()
    main_menu = State()
    first_name = State()
    last_name = State()
    gender = State()
    marital_status = State()
    spouse_name = State()
    spouse_gender = State()
    spouse_photo = State()
    has_children = State()
    children_count = State()
    child_name = State()
    child_gender = State()
    child_photo = State()
    main_photo = State()
    review_info = State()
    payment_upload = State()

# HELPER
def get_text(data, key):
    lang = data.get('lang', 'en') 
    return TRANS[lang].get(key, "Text Missing")

# --- HANDLERS ---

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    kb = [[InlineKeyboardButton(text="English 🇺🇸", callback_data="lang_en"),
           InlineKeyboardButton(text="አማርኛ 🇪🇹", callback_data="lang_am")]]
    await message.answer(TRANS['en']['welcome'] + "\n\n" + TRANS['am']['welcome'], reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(DVFlow.choosing_lang)

@dp.callback_query(F.data.startswith("lang_"))
async def language_selected(callback: CallbackQuery, state: FSMContext):
    selected_lang = callback.data.split("_")[1]
    await state.update_data(lang=selected_lang, children=[]) 
    data = await state.get_data()
    await callback.message.answer(get_text(data, 'lang_set'))
    await show_main_menu(callback.message, data)
    await state.set_state(DVFlow.main_menu)
    await callback.answer()

async def show_main_menu(message: Message, data):
    kb = [[KeyboardButton(text=get_text(data, 'btn_start'))],
          [KeyboardButton(text=get_text(data, 'btn_price')), KeyboardButton(text=get_text(data, 'btn_help'))]]
    await message.answer(get_text(data, 'main_menu'), reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

# --- BUTTONS HANDLERS ---
@dp.message(F.text.in_([TRANS['en']['btn_start'], TRANS['am']['btn_start']]))
async def start_app(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(get_text(data, 'ask_firstname'), reply_markup=ReplyKeyboardRemove())
    await state.set_state(DVFlow.first_name)

@dp.message(F.text.in_([TRANS['en']['btn_price'], TRANS['am']['btn_price']]))
async def show_price(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(get_text(data, 'price_info'))

@dp.message(F.text.in_([TRANS['en']['btn_help'], TRANS['am']['btn_help']]))
async def ai_help_mode(message: Message, state: FSMContext):
    data = await state.get_data()
    prompt_msg = "🤖 **AI Assistant**\n\nAsk me anything about DV-2027.\n(Type your question below)"
    if data.get('lang') == 'am':
        prompt_msg = "🤖 **AI ረዳት**\n\nስለ DV-2027 ማንኛውንም ጥያቄ ይጠይቁ።\n(ጥያቄዎን ከታች ይጻፉ)"
    await message.answer(prompt_msg)

# --- GENERAL AI HANDLER ---
@dp.message(DVFlow.main_menu, F.text)
async def general_ai_chat(message: Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    ai_response = await ask_gemini(message.text)
    await message.answer(ai_response)

# --- FORM FLOW WITH VALIDATION ---

@dp.message(DVFlow.first_name)
async def get_fname(message: Message, state: FSMContext):
    # Basic validation: ensure it's text and not too short
    if len(message.text) < 2:
        await message.answer("⚠️ Name too short. Please enter valid name.")
        return
    await state.update_data(first_name=message.text)
    data = await state.get_data()
    await message.answer(get_text(data, 'ask_lastname'))
    await state.set_state(DVFlow.last_name)

@dp.message(DVFlow.last_name)
async def get_lname(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    data = await state.get_data()
    kb = [[KeyboardButton(text=get_text(data, 'male')), KeyboardButton(text=get_text(data, 'female'))]]
    await message.answer(get_text(data, 'ask_gender'), reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(DVFlow.gender)

# --- GENDER VALIDATION ---
@dp.message(DVFlow.gender)
async def get_gender(message: Message, state: FSMContext):
    data = await state.get_data()
    text = message.text
    
    # Valid options
    valid_options = [TRANS['en']['male'], TRANS['en']['female'], TRANS['am']['male'], TRANS['am']['female']]
    
    if text not in valid_options:
        await message.answer("⚠️ Please select one of the buttons below:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=get_text(data, 'male')), KeyboardButton(text=get_text(data, 'female'))]], 
            resize_keyboard=True))
        return # STOP HERE. Don't change state.

    await state.update_data(gender=text)
    
    # Next Step
    kb = [[KeyboardButton(text=get_text(data, 'single')), KeyboardButton(text=get_text(data, 'married'))],
          [KeyboardButton(text=get_text(data, 'divorced')), KeyboardButton(text=get_text(data, 'widowed'))]]
    await message.answer(get_text(data, 'ask_marital'), reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(DVFlow.marital_status)

# --- MARITAL VALIDATION ---
@dp.message(DVFlow.marital_status)
async def process_marital(message: Message, state: FSMContext):
    data = await state.get_data()
    text = message.text
    
    # Construct valid list
    valid_list = [
        get_text(data, 'single'), get_text(data, 'married'),
        get_text(data, 'divorced'), get_text(data, 'widowed')
    ]
    # Also allow 'am' versions if user is in 'en' mode but clicks 'am' (edge case, but safe)
    valid_list += [TRANS['am']['single'], TRANS['am']['married'], TRANS['en']['single'], TRANS['en']['married']]
    
    if text not in valid_list and text not in [TRANS['en']['divorced'], TRANS['en']['widowed'], TRANS['am']['divorced'], TRANS['am']['widowed']]:
         # Re-send buttons
        kb = [[KeyboardButton(text=get_text(data, 'single')), KeyboardButton(text=get_text(data, 'married'))],
              [KeyboardButton(text=get_text(data, 'divorced')), KeyboardButton(text=get_text(data, 'widowed'))]]
        await message.answer("⚠️ Invalid option. Please use the buttons:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        return # STOP HERE

    await state.update_data(marital_status=text)
    
    if text == get_text(data, 'married'):
        await message.answer(get_text(data, 'ask_spouse_name'), reply_markup=ReplyKeyboardRemove())
        await state.set_state(DVFlow.spouse_name)
    else:
        await ask_about_children(message, state)

# SPOUSE FLOW
@dp.message(DVFlow.spouse_name)
async def spouse_name(message: Message, state: FSMContext):
    await state.update_data(spouse_name=message.text)
    data = await state.get_data()
    main_gender = data.get('gender')
    
    spouse_sex = "Unknown"
    if main_gender == TRANS['en']['male']: spouse_sex = TRANS['en']['female']
    elif main_gender == TRANS['en']['female']: spouse_sex = TRANS['en']['male']
    elif main_gender == TRANS['am']['male']: spouse_sex = TRANS['am']['female']
    elif main_gender == TRANS['am']['female']: spouse_sex = TRANS['am']['male']
    
    await state.update_data(spouse_gender=spouse_sex)
    await message.answer(get_text(data, 'ask_spouse_photo'), reply_markup=ReplyKeyboardRemove())
    await state.set_state(DVFlow.spouse_photo)

# CHILDREN START
async def ask_about_children(message: Message, state: FSMContext):
    data = await state.get_data()
    kb = [[KeyboardButton(text=get_text(data, 'yes')), KeyboardButton(text=get_text(data, 'no'))]]
    await message.answer(get_text(data, 'ask_has_children'), reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(DVFlow.has_children)

# --- CHILDREN YES/NO VALIDATION ---
@dp.message(DVFlow.has_children)
async def process_has_children(message: Message, state: FSMContext):
    data = await state.get_data()
    text = message.text
    
    valid_yes = [TRANS['en']['yes'], TRANS['am']['yes']]
    valid_no = [TRANS['en']['no'], TRANS['am']['no']]
    
    if text not in valid_yes and text not in valid_no:
        kb = [[KeyboardButton(text=get_text(data, 'yes')), KeyboardButton(text=get_text(data, 'no'))]]
        await message.answer("⚠️ Please select Yes or No:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        return # STOP HERE

    if text in valid_yes:
        await message.answer(get_text(data, 'ask_child_count'), reply_markup=ReplyKeyboardRemove())
        await state.set_state(DVFlow.children_count)
    else:
        await ask_main_photo(message, state)

# CHILDREN COUNT
@dp.message(DVFlow.children_count)
async def process_child_count(message: Message, state: FSMContext):
    try:
        count = int(message.text)
        if count < 1 or count > 20:
             await message.answer("Please enter a realistic number (1-20).")
             return
             
        await state.update_data(total_children=count, current_child_index=1, children=[])
        data = await state.get_data()
        msg = get_text(data, 'ask_child_name').format(n=1)
        await message.answer(msg)
        await state.set_state(DVFlow.child_name)
    except ValueError:
        await message.answer("Please enter a number (e.g., 1, 2).")

# CHILD LOOP
@dp.message(DVFlow.child_name)
async def child_name_handler(message: Message, state: FSMContext):
    await state.update_data(temp_child_name=message.text)
    data = await state.get_data()
    idx = data.get('current_child_index')
    kb = [[KeyboardButton(text=get_text(data, 'male')), KeyboardButton(text=get_text(data, 'female'))]]
    msg = get_text(data, 'ask_child_gender').format(n=idx)
    await message.answer(msg, reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(DVFlow.child_gender)

# CHILD GENDER VALIDATION
@dp.message(DVFlow.child_gender)
async def child_gender_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    text = message.text
    valid_options = [TRANS['en']['male'], TRANS['en']['female'], TRANS['am']['male'], TRANS['am']['female']]
    
    if text not in valid_options:
        idx = data.get('current_child_index')
        kb = [[KeyboardButton(text=get_text(data, 'male')), KeyboardButton(text=get_text(data, 'female'))]]
        await message.answer("⚠️ Please select Male or Female.", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        return # STOP HERE

    await state.update_data(temp_child_gender=message.text)
    idx = data.get('current_child_index')
    msg = get_text(data, 'ask_child_photo').format(n=idx)
    await message.answer(msg, reply_markup=ReplyKeyboardRemove())
    await state.set_state(DVFlow.child_photo)

@dp.message(DVFlow.child_photo, F.photo)
async def child_photo_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    children_list = data.get('children', [])
    new_child = {
        'name': data.get('temp_child_name'),
        'gender': data.get('temp_child_gender'),
        'photo_id': message.photo[-1].file_id
    }
    children_list.append(new_child)
    await state.update_data(children=children_list)
    
    current = data.get('current_child_index')
    total = data.get('total_children')
    
    if current < total:
        next_idx = current + 1
        await state.update_data(current_child_index=next_idx)
        msg = get_text(data, 'ask_child_name').format(n=next_idx)
        await message.answer(msg)
        await state.set_state(DVFlow.child_name)
    else:
        await ask_main_photo(message, state)

# SMART ERROR (PHOTO VALIDATION)
@dp.message(DVFlow.spouse_photo, F.text)
@dp.message(DVFlow.child_photo, F.text)
@dp.message(DVFlow.main_photo, F.text) 
@dp.message(DVFlow.payment_upload, F.text)
async def smart_photo_error(message: Message, state: FSMContext):
    user_text = message.text
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    context_prompt = (
        f"The user is in a form flow. They MUST upload a photo (image). "
        f"Instead, they typed: '{user_text}'. "
        f"Explain politely in the appropriate language that they must upload an image file to proceed."
    )
    ai_response = await ask_gemini(context_prompt)
    await message.answer(ai_response)

# MAIN PHOTO
async def ask_main_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(get_text(data, 'ask_main_photo'), reply_markup=ReplyKeyboardRemove())
    await state.set_state(DVFlow.main_photo)

@dp.message(DVFlow.main_photo, F.photo)
async def process_main_photo(message: Message, state: FSMContext):
    await state.update_data(main_photo_id=message.photo[-1].file_id)
    data = await state.get_data()
    
    spouse_txt = f"\n💍 Spouse: {data.get('spouse_name')}" if data.get('spouse_name') else ""
    child_txt = ""
    if data.get('children'):
        for i, child in enumerate(data['children']):
            child_txt += f"\n👶 Child {i+1}: {child['name']} ({child['gender']})"
            
    summary = (
        f"{get_text(data, 'review_title')}\n\n"
        f"👤 Name: {data.get('first_name')} {data.get('last_name')}\n"
        f"⚧ Gender: {data.get('gender')}\n"
        f"❤️ Status: {data.get('marital_status')}"
        f"{spouse_txt}"
        f"{child_txt}\n\n"
        f"📸 Main Photo: [Received]"
    )
    kb = [[KeyboardButton(text=get_text(data, 'btn_confirm'))], [KeyboardButton(text=get_text(data, 'btn_edit'))]]
    await message.answer(summary, reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(DVFlow.review_info)

# REVIEW & PAYMENT
@dp.message(DVFlow.review_info)
async def process_review(message: Message, state: FSMContext):
    data = await state.get_data()
    if message.text == get_text(data, 'btn_edit'):
        await message.answer(get_text(data, 'ask_firstname'), reply_markup=ReplyKeyboardRemove())
        await state.set_state(DVFlow.first_name)
    else:
        await message.answer(get_text(data, 'payment_msg'), reply_markup=ReplyKeyboardRemove())
        await state.set_state(DVFlow.payment_upload)

@dp.message(DVFlow.payment_upload, F.photo)
async def process_payment(message: Message, state: FSMContext):
    data = await state.get_data()
    pay_id = message.photo[-1].file_id
    user = message.from_user
    
    caption = (
        f"💰 **NEW DV CLIENT**\n"
        f"User: @{user.username} (ID: {user.id})\n\n"
        f"👤 **Main:** {data.get('first_name')} {data.get('last_name')}\n"
        f"⚧ {data.get('gender')} | {data.get('marital_status')}\n"
    )
    if data.get('spouse_name'):
        caption += f"💍 **Spouse:** {data.get('spouse_name')} ({data.get('spouse_gender')})\n"
    if data.get('children'):
        caption += f"👶 **Children:** {len(data['children'])} kids.\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{user.id}")]])
    
    await bot.send_photo(chat_id=ADMIN_ID, photo=pay_id, caption=caption, reply_markup=kb)
    await bot.send_photo(chat_id=ADMIN_ID, photo=data.get('main_photo_id'), caption=f"📸 Main Photo: {data.get('first_name')}")
    if data.get('spouse_photo_id'):
        await bot.send_photo(chat_id=ADMIN_ID, photo=data.get('spouse_photo_id'), caption="📸 Spouse Photo")
    if data.get('children'):
        for i, child in enumerate(data['children']):
            await bot.send_photo(chat_id=ADMIN_ID, photo=child['photo_id'], caption=f"📸 Child {i+1}: {child['name']}")
            
    await message.answer(get_text(data, 'wait_approval'))

@dp.callback_query(F.data.startswith("approve_"))
async def approve(callback: CallbackQuery):
    uid = int(callback.data.split("_")[1])
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ **DONE**")
    try:
        await bot.send_message(uid, "✅ **APPROVED!** We are processing your application.")
    except: pass

async def main():
    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())