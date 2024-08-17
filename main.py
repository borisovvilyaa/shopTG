import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.utils import executor
import sqlite3

API_TOKEN = '7516681734:AAG4axYoAu-wz9XkvU1D5uVT5cPUskqkfHw'

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

def get_db_connection():
    try:
        conn = sqlite3.connect('shop.db')
        logger.info("Database connection established.")
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

# Создание клавиатур
def create_main_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(KeyboardButton("🛍️ Categories"))
    keyboard.add(KeyboardButton("🛒 Cart"))
    keyboard.add(KeyboardButton("💳 Checkout"))
    return keyboard

def create_category_menu_keyboard(categories):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for cat in categories:
        keyboard.add(KeyboardButton(f"📦 {cat[1]}"))
    keyboard.add(KeyboardButton("↩️ Back"))
    return keyboard

def create_product_navigation_keyboard(product_id, category_id, page, total_pages):
    keyboard = InlineKeyboardMarkup(row_width=2)  # Устанавливаем ширину строки 2
    
    # Добавляем кнопку "Previous", если страница не первая
    if page > 1:
        keyboard.insert(InlineKeyboardButton("⬅️ Previous", callback_data=f'prev_{category_id}_{page-1}'))
    
    # Добавляем кнопку "Next", если страница не последняя
    if page < total_pages:
        keyboard.insert(InlineKeyboardButton("➡️ Next", callback_data=f'next_{category_id}_{page+1}'))
    
    # Добавляем кнопку "Add to Cart" в конце ряда
    keyboard.add(InlineKeyboardButton("🛒 Add to Cart", callback_data=f'add_{product_id}'))
    
    return keyboard

def create_cart_keyboard(cart_items, total_price):
    keyboard = InlineKeyboardMarkup()
    for item in cart_items:
        item_name, quantity, price, product_id = item
        keyboard.add(
            InlineKeyboardButton(f"🛒 {item_name} x{quantity}", callback_data=f'show_{product_id}'),
            InlineKeyboardButton(f"🗑️ Remove", callback_data=f'remove_{product_id}')
        )
    keyboard.add(InlineKeyboardButton(f"💳 Checkout - ${total_price:.2f}", callback_data='checkout'))
    return keyboard

def get_categories():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories")
        categories = cursor.fetchall()
        conn.close()
        return categories
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        return []

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    try:
        keyboard = create_main_menu_keyboard()
        await message.reply("Welcome to the Shop Bot! Use the buttons below to navigate.", reply_markup=keyboard)
        logger.info(f"Sent welcome message to {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error in /start handler: {e}")

@dp.message_handler(text="🛍️ Categories")
async def list_categories(message: types.Message):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories")
        categories = cursor.fetchall()
        conn.close()

        if categories:
            response = "Categories:"
            keyboard = create_category_menu_keyboard(categories)
        else:
            response = "No categories available."
            keyboard = create_main_menu_keyboard()

        await message.reply(response, reply_markup=keyboard)
        logger.info(f"Sent categories list to {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error in /categories handler: {e}")

@dp.message_handler(text="🛒 Cart")
async def view_cart(message: types.Message):
    try:
        user_id = message.from_user.id
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.name, c.quantity, p.price, c.product_id 
            FROM cart c 
            JOIN products p ON c.product_id = p.id 
            WHERE c.user_id=?
        """, (user_id,))
        items = cursor.fetchall()

        total_price = sum(item[1] * item[2] for item in items)  # Считаем общую стоимость
        conn.close()

        if items:
            keyboard = create_cart_keyboard(items, total_price)
            response = "Your Cart:\n" + "\n".join([f"• {item[0]} x{item[1]} - ${item[1] * item[2]:.2f}" for item in items]) + f"\n\nTotal Price: ${total_price:.2f}"
        else:
            response = "Your cart is empty."
            keyboard = create_main_menu_keyboard()

        await message.reply(response, reply_markup=keyboard)
        logger.info(f"Sent cart contents to {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error in /cart handler: {e}")

@dp.message_handler(text="💳 Checkout")
async def checkout(message: types.Message):
    await message.reply("Checkout is not yet implemented.", reply_markup=create_main_menu_keyboard())

@dp.message_handler(text="↩️ Back")
async def go_back(message: types.Message):
    try:
        keyboard = create_main_menu_keyboard()
        await message.reply("Back to main menu.", reply_markup=keyboard)
        logger.info(f"Returned to main menu for {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error in Back handler: {e}")

@dp.message_handler(lambda message: any(message.text.startswith('📦') and message.text[2:] == cat[1] for cat in get_categories()))
async def show_products_by_category(message: types.Message):
    try:
        category_name = message.text[2:]
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM categories WHERE name=?", (category_name,))
        category_id = cursor.fetchone()[0]

        # Initialize page
        page = 1

        # Get total number of products
        cursor.execute("SELECT COUNT(*) FROM products WHERE category_id=?", (category_id,))
        total_products = cursor.fetchone()[0]
        total_pages = (total_products + 1) // 1  # Assuming 1 product per page

        # Show first product
        cursor.execute("SELECT * FROM products WHERE category_id=? LIMIT 1 OFFSET ?", (category_id, (page-1)))
        product = cursor.fetchone()
        conn.close()
        if product:
            response = (f"<b>Product:</b> {product[2]}\n"
                        f"<b>Description:</b> <i>{product[3]}</i>\n\n"
                        f"<b>Price:</b> <u>${product[4]:.2f}</u>")

            photo_url = product[5]
            keyboard = create_product_navigation_keyboard(product[0], category_id, page, total_pages)
            await message.reply_photo(photo=photo_url, caption=response, reply_markup=keyboard, parse_mode='HTML')
            logger.info(f"Displayed product {product[2]} to {message.from_user.id}")
        else:
            await message.reply("No products found in this category.")
            logger.info(f"No products found for category {category_name} requested by {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error in show_products_by_category handler: {e}")

@dp.callback_query_handler(lambda c: c.data.startswith(('add_', 'prev_', 'next_', 'show_', 'checkout', 'cart', 'remove_')))
async def process_callback(callback_query: types.CallbackQuery):
    try:
        data = callback_query.data.split('_')
        action = data[0]
        conn = get_db_connection()
        cursor = conn.cursor()

        if action == 'add':
            product_id = int(data[1])
            user_id = callback_query.from_user.id
            cursor.execute("SELECT name, price FROM products WHERE id=?", (product_id,))
            product = cursor.fetchone()
            
            if product:
                cursor.execute("""
                    INSERT INTO cart (user_id, product_id, quantity)
                    VALUES (?, ?, 1)
                    ON CONFLICT(user_id, product_id)
                    DO UPDATE SET quantity = quantity + 1
                    """, (user_id, product_id))
                conn.commit()
                response = f"Added {product[0]} to your cart for ${product[1]:.2f}."
            else:
                response = "Product not found."
            
            await bot.answer_callback_query(callback_query.id, text=response)
            await bot.send_message(callback_query.from_user.id, response)
            logger.info(f"Processed add request for product {product_id} by {user_id}")
        
        elif action in ('prev', 'next'):
            category_id = int(data[1])
            page = int(data[2])
            cursor.execute("SELECT COUNT(*) FROM products WHERE category_id=?", (category_id,))
            total_products = cursor.fetchone()[0]
            total_pages = (total_products + 1) // 1

            if 1 <= page <= total_pages:
                cursor.execute("SELECT * FROM products WHERE category_id=? LIMIT 1 OFFSET ?", (category_id, (page-1)))
                product = cursor.fetchone()
                if product:
                    response = f"Product: {product[2]}\nDescription: {product[3]}\nPrice: ${product[4]:.2f}"
                    photo_url = product[5]
                    media = InputMediaPhoto(media=photo_url, caption=response)
                    keyboard = create_product_navigation_keyboard(product[0], category_id, page, total_pages)
                    await bot.edit_message_media(media=media, chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, reply_markup=keyboard)
                    logger.info(f"Displayed product {product[2]} to {callback_query.from_user.id} (page {page})")
                else:
                    await bot.edit_message_text("No products found in this category.", chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, reply_markup=None)
                    logger.info(f"No products found on page {page} for category {category_id} requested by {callback_query.from_user.id}")
            else:
                await bot.answer_callback_query(callback_query.id, text="No more products.")
                logger.info(f"Page {page} is out of range for category {category_id}")

        elif action == 'show':
            product_id = int(data[1])
            cursor.execute("SELECT * FROM products WHERE id=?", (product_id,))
            product = cursor.fetchone()
            conn.close()

            if product:
                response = (f"Product: {product[2]}\n"
                            f"Description: {product[3]}\n"
                            f"Price: ${product[4]:.2f}")
                photo_url = product[5]
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton("↩️ Back to Cart", callback_data='cart'))

                await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
                await bot.send_photo(chat_id=callback_query.message.chat.id, photo=photo_url, caption=response, reply_markup=keyboard)
                logger.info(f"Displayed product {product[2]} to {callback_query.from_user.id}")
            else:
                await bot.send_message(chat_id=callback_query.message.chat.id, text="Product not found.")
                logger.info(f"Product with ID {product_id} not found for {callback_query.from_user.id}")

        elif action == 'remove':
            product_id = int(data[1])
            user_id = callback_query.from_user.id
            cursor.execute("DELETE FROM cart WHERE user_id=? AND product_id=?", (user_id, product_id))
            conn.commit()
            
            # Получаем оставшиеся товары в корзине
            cursor.execute("""
                SELECT p.name, c.quantity, p.price, c.product_id 
                FROM cart c 
                JOIN products p ON c.product_id = p.id 
                WHERE c.user_id=?
            """, (user_id,))
            items = cursor.fetchall()
            total_price = sum(item[1] * item[2] for item in items)
            conn.close()

            if items:
                keyboard = create_cart_keyboard(items, total_price)
                response = "Your Cart:\n" + "\n".join([f"• {item[0]} x{item[1]} - ${item[1] * item[2]:.2f}" for item in items]) + f"\n\nTotal Price: ${total_price:.2f}"
            else:
                response = "Your cart is empty."
                keyboard = create_main_menu_keyboard()

            await bot.answer_callback_query(callback_query.id, text="Removed from cart.")
            if items:
                await bot.edit_message_text(text=response, chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, reply_markup=keyboard)
            else:
                await bot.edit_message_text(text=response, chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, reply_markup=None)
            logger.info(f"Removed product {product_id} from cart for {user_id}")

        elif action == 'checkout':
            await bot.answer_callback_query(callback_query.id, text="Checkout is not yet implemented.")
            logger.info(f"Checkout requested by {callback_query.from_user.id}, but it's not implemented yet.")
        
        elif action == 'cart':
            user_id = callback_query.from_user.id
            cursor.execute("""
                SELECT p.name, c.quantity, p.price, c.product_id 
                FROM cart c 
                JOIN products p ON c.product_id = p.id 
                WHERE c.user_id=?
            """, (user_id,))
            items = cursor.fetchall()
            
            total_price = sum(item[1] * item[2] for item in items)
            conn.close()

            if items:
                keyboard = create_cart_keyboard(items, total_price)
                response = "Your Cart:\n" + "\n".join([f"• {item[0]} x{item[1]} - ${item[1] * item[2]:.2f}" for item in items]) + f"\n\nTotal Price: ${total_price:.2f}"
            else:
                response = "Your cart is empty."
                keyboard = create_main_menu_keyboard()

            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
            await bot.send_message(chat_id=callback_query.message.chat.id, text=response, reply_markup=keyboard)
            logger.info(f"Returned to cart for {callback_query.from_user.id}")

    except Exception as e:
        logger.error(f"Error in process_callback handler: {e}")
        await bot.answer_callback_query(callback_query.id, text="An error occurred.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
