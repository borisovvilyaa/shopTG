import sqlite3
import requests

def fetch_products():
    response = requests.get('https://fakestoreapi.com/products')
    response.raise_for_status()
    return response.json()

def create_tables():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    
    # Создание таблицы для категорий
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    ''')
    
    # Создание таблицы для товаров
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY,
        category_id INTEGER,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        image_url TEXT,
        FOREIGN KEY (category_id) REFERENCES categories(id)
    )
    ''')
    
    # Создание таблицы для корзины
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cart (
        user_id INTEGER,
        product_id INTEGER,
        quantity INTEGER DEFAULT 1,
        PRIMARY KEY (user_id, product_id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    ''')
    
    conn.commit()
    conn.close()

def populate_db():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    
    # Получение товаров из Fake Store API
    products = fetch_products()
    
    # Извлечение уникальных категорий из товаров
    categories = set(product['category'] for product in products)
    
    # Добавление категорий в базу данных
    category_map = {}
    for category in categories:
        cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category,))
        category_id = cursor.execute("SELECT id FROM categories WHERE name = ?", (category,)).fetchone()[0]
        category_map[category] = category_id
    
    # Вставка товаров в базу данных
    for product in products:
        category_id = category_map.get(product['category'], None)
        if category_id is not None:
            cursor.execute(
                "INSERT OR IGNORE INTO products (id, category_id, name, description, price, image_url) VALUES (?, ?, ?, ?, ?, ?)",
                (product['id'], category_id, product['title'], product['description'], product['price'], product['image'])
            )
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_tables()
    populate_db()
    print("Database initialized and populated successfully.")
