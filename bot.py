import asyncio
import logging
import os
from dotenv import load_dotenv

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
    
    # Main Applicant
    first_name = State()
    last_name = State()
    gender = State()
    marital_status = State()
    
    # Spouse (Conditional)
    spouse_name = State()
    spouse_gender = State()
    spouse_photo = State()
    
    # Children (Conditional Loop)
    has_children = State()
    children_count = State()
    child_name = State()   # Loops
    child_gender = State() # Loops
    child_photo = State()  # Loops
    
    # Final Steps
    main_photo = State()
    review_info = State()
    payment_upload = State()

# HELPER
def get_text(data, key):
    lang = data.get('lang', 'en') 
    return TRANS[lang].get(key, "Text Missing")

# --- HANDLERS ---

# START
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    kb = [[InlineKeyboardButton(text="English 🇺🇸", callback_data="lang_en"),
           InlineKeyboardButton(text="አማርኛ 🇪🇹", callback_data="lang_am")]]
    await message.answer(TRANS['en']['welcome'] + "\n\n" + TRANS['am']['welcome'], reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(DVFlow.choosing_lang)

@dp.callback_query(F.data.startswith("lang_"))
async def language_selected(callback: CallbackQuery, state: FSMContext):
    selected_lang = callback.data.split("_")[1]
    await state.update_data(lang=selected_lang, children=[]) # Initialize empty children list
    data = await state.get_data()
    await callback.message.answer(get_text(data, 'lang_set'))
    await show_main_menu(callback.message, data)
    await state.set_state(DVFlow.main_menu)
    await callback.answer()

async def show_main_menu(message: Message, data):
    kb = [[KeyboardButton(text=get_text(data, 'btn_start'))],
          [KeyboardButton(text=get_text(data, 'btn_price')), KeyboardButton(text=get_text(data, 'btn_help'))]]
    await message.answer(get_text(data, 'main_menu'), reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

# 1. MAIN APPLICANT
@dp.message(F.text.in_([TRANS['en']['btn_start'], TRANS['am']['btn_start']]))
async def start_app(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(get_text(data, 'ask_firstname'), reply_markup=ReplyKeyboardRemove())
    await state.set_state(DVFlow.first_name)

@dp.message(DVFlow.first_name)
async def get_fname(message: Message, state: FSMContext):
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

@dp.message(DVFlow.gender)
async def get_gender(message: Message, state: FSMContext):
    await state.update_data(gender=message.text)
    data = await state.get_data()
    kb = [[KeyboardButton(text=get_text(data, 'single')), KeyboardButton(text=get_text(data, 'married'))],
          [KeyboardButton(text=get_text(data, 'divorced')), KeyboardButton(text=get_text(data, 'widowed'))]]
    await message.answer(get_text(data, 'ask_marital'), reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(DVFlow.marital_status)

# 2. MARITAL STATUS LOGIC (THE SPLIT)
@dp.message(DVFlow.marital_status)
async def process_marital(message: Message, state: FSMContext):
    status = message.text
    await state.update_data(marital_status=status)
    data = await state.get_data()
    
    # Check if Married
    if status == get_text(data, 'married'):
        # Go to Spouse Flow
        await message.answer(get_text(data, 'ask_spouse_name'), reply_markup=ReplyKeyboardRemove())
        await state.set_state(DVFlow.spouse_name)
    else:
        # Skip to Children
        await ask_about_children(message, state)

# --- SPOUSE FLOW (UPDATED SMART LOGIC) ---
@dp.message(DVFlow.spouse_name)
async def spouse_name(message: Message, state: FSMContext):
    # 1. Save Spouse Name
    await state.update_data(spouse_name=message.text)
    
    # 2. Auto-Detect Spouse Gender
    data = await state.get_data()
    main_gender = data.get('gender')
    
    # Logic to reverse gender
    spouse_sex = "Unknown"
    
    # English Check
    if main_gender == TRANS['en']['male']:      # If Main is Male
        spouse_sex = TRANS['en']['female']      # Spouse is Female
    elif main_gender == TRANS['en']['female']:  # If Main is Female
        spouse_sex = TRANS['en']['male']        # Spouse is Male
        
    # Amharic Check
    elif main_gender == TRANS['am']['male']:    # If Main is ወንድ
        spouse_sex = TRANS['am']['female']      # Spouse is ሴት
    elif main_gender == TRANS['am']['female']:  # If Main is ሴት
        spouse_sex = TRANS['am']['male']        # Spouse is ወንድ
    
    # Save the auto-detected gender
    await state.update_data(spouse_gender=spouse_sex)
    
    # 3. Skip Gender Question -> Go straight to Photo
    await message.answer(get_text(data, 'ask_spouse_photo'), reply_markup=ReplyKeyboardRemove())
    await state.set_state(DVFlow.spouse_photo)

# --- CHILDREN LOGIC ---
async def ask_about_children(message: Message, state: FSMContext):
    data = await state.get_data()
    kb = [[KeyboardButton(text=get_text(data, 'yes')), KeyboardButton(text=get_text(data, 'no'))]]
    await message.answer(get_text(data, 'ask_has_children'), reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(DVFlow.has_children)

@dp.message(DVFlow.has_children)
async def process_has_children(message: Message, state: FSMContext):
    data = await state.get_data()
    if message.text == get_text(data, 'yes'):
        await message.answer(get_text(data, 'ask_child_count'), reply_markup=ReplyKeyboardRemove())
        await state.set_state(DVFlow.children_count)
    else:
        # No children -> Go to Main Photo
        await ask_main_photo(message, state)

@dp.message(DVFlow.children_count)
async def process_child_count(message: Message, state: FSMContext):
    try:
        count = int(message.text)
        await state.update_data(total_children=count, current_child_index=1, children=[])
        # Start Loop for Child 1
        data = await state.get_data()
        msg = get_text(data, 'ask_child_name').format(n=1)
        await message.answer(msg)
        await state.set_state(DVFlow.child_name)
    except ValueError:
        await message.answer("Please enter a number (e.g., 1, 2).")

# CHILD LOOP
@dp.message(DVFlow.child_name)
async def child_name_handler(message: Message, state: FSMContext):
    # Save temp name
    await state.update_data(temp_child_name=message.text)
    data = await state.get_data()
    idx = data.get('current_child_index')
    
    kb = [[KeyboardButton(text=get_text(data, 'male')), KeyboardButton(text=get_text(data, 'female'))]]
    msg = get_text(data, 'ask_child_gender').format(n=idx)
    await message.answer(msg, reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(DVFlow.child_gender)

@dp.message(DVFlow.child_gender)
async def child_gender_handler(message: Message, state: FSMContext):
    await state.update_data(temp_child_gender=message.text)
    data = await state.get_data()
    idx = data.get('current_child_index')
    
    msg = get_text(data, 'ask_child_photo').format(n=idx)
    await message.answer(msg, reply_markup=ReplyKeyboardRemove())
    await state.set_state(DVFlow.child_photo)

@dp.message(DVFlow.child_photo, F.photo)
async def child_photo_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    children_list = data.get('children', [])
    
    # Pack current child data
    new_child = {
        'name': data.get('temp_child_name'),
        'gender': data.get('temp_child_gender'),
        'photo_id': message.photo[-1].file_id
    }
    children_list.append(new_child)
    await state.update_data(children=children_list)
    
    # Check if we need more children
    current = data.get('current_child_index')
    total = data.get('total_children')
    
    if current < total:
        # Ask for NEXT child
        next_idx = current + 1
        await state.update_data(current_child_index=next_idx)
        msg = get_text(data, 'ask_child_name').format(n=next_idx)
        await message.answer(msg)
        await state.set_state(DVFlow.child_name)
    else:
        # Done with all children -> Go to Main Photo
        await ask_main_photo(message, state)

# --- FINAL STEPS ---
async def ask_main_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(get_text(data, 'ask_main_photo'), reply_markup=ReplyKeyboardRemove())
    await state.set_state(DVFlow.main_photo)

@dp.message(DVFlow.main_photo, F.photo)
async def process_main_photo(message: Message, state: FSMContext):
    await state.update_data(main_photo_id=message.photo[-1].file_id)
    data = await state.get_data()
    
    # Build Summary
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
    
    # 1. Admin Caption (Detailed)
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
    
    # Send Payment Proof
    await bot.send_photo(chat_id=ADMIN_ID, photo=pay_id, caption=caption, reply_markup=kb)
    
    # Send All Client Photos to Admin immediately (So you don't lose them)
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