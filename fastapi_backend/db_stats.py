import sqlite3

conn = sqlite3.connect('smartfood.db', timeout=30)
c = conn.cursor()

print('\n📊 COMPREHENSIVE DATABASE STATISTICS')
print('=' * 70)

# Basic counts
rest = c.execute('SELECT COUNT(*) FROM restaurants').fetchone()[0]
items = c.execute('SELECT COUNT(*) FROM menu_items').fetchone()[0]
print(f'\n✅ Total Restaurants: {rest}')
print(f'✅ Total Menu Items: {items}')
print(f'✅ Average Items per Restaurant: {items/rest:.1f}')

# Cuisine types breakdown
print(f'\n🍽️  CUISINE TYPES COVERAGE:')
print('-' * 70)
cuisines = c.execute('SELECT DISTINCT cuisine_type FROM restaurants ORDER BY cuisine_type').fetchall()
for i, (cuisine,) in enumerate(cuisines, 1):
    rest_count = c.execute('SELECT COUNT(*) FROM restaurants WHERE cuisine_type = ?', (cuisine,)).fetchone()[0]
    item_count = c.execute('''
        SELECT COUNT(*) FROM menu_items 
        JOIN restaurants ON menu_items.restaurant_id = restaurants.id 
        WHERE restaurants.cuisine_type = ?
    ''', (cuisine,)).fetchone()[0]
    print(f'  {i:2}. {cuisine:35} - {rest_count} restaurant(s), {item_count:4} items')

# Price statistics
print(f'\n💰 PRICE STATISTICS:')
print('-' * 70)
min_price = c.execute('SELECT MIN(price) FROM menu_items').fetchone()[0]
max_price = c.execute('SELECT MAX(price) FROM menu_items').fetchone()[0]
avg_price = c.execute('SELECT AVG(price) FROM menu_items').fetchone()[0]
print(f'  • Minimum Price: ₹{min_price:.0f}')
print(f'  • Maximum Price: ₹{max_price:.0f}')
print(f'  • Average Price: ₹{avg_price:.2f}')

# Sample expensive and cheap items
print(f'\n💎 Most Expensive Items:')
expensive = c.execute('SELECT name, price, category FROM menu_items ORDER BY price DESC LIMIT 5').fetchall()
for name, price, category in expensive:
    print(f'  • {name:40} - ₹{price:5.0f} ({category})')

print(f'\n🥗 Most Affordable Items:')
cheap = c.execute('SELECT name, price, category FROM menu_items ORDER BY price ASC LIMIT 5').fetchall()
for name, price, category in cheap:
    print(f'  • {name:40} - ₹{price:5.0f} ({category})')

# Category breakdown
print(f'\n📋 MENU CATEGORIES:')
print('-' * 70)
categories = c.execute('SELECT category, COUNT(*) as count FROM menu_items GROUP BY category ORDER BY count DESC').fetchall()
for category, count in categories:
    print(f'  • {category:25} - {count:4} items')

print('\n' + '=' * 70)
print('✅ Database successfully filled with comprehensive restaurant data!')
print('=' * 70)

conn.close()
