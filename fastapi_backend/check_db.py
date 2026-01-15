import sqlite3
import time

# Wait a bit for database to be ready
time.sleep(2)

# Connect to database
conn = sqlite3.connect('smartfood.db', timeout=10)
cursor = conn.cursor()

# Get tables
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

print('\n' + '='*70)
print('✅ SMARTFOOD.DB - DATABASE VERIFICATION')
print('='*70)

print('\n📋 Database Tables:')
for t in tables:
    print(f'   • {t[0]}')

if tables:
    # Get counts
    rest_count = cursor.execute('SELECT COUNT(*) FROM restaurants').fetchone()[0]
    item_count = cursor.execute('SELECT COUNT(*) FROM menu_items').fetchone()[0]
    
    # Get sample data
    sample_restaurants = cursor.execute(
        'SELECT name, cuisine_type, rating FROM restaurants LIMIT 5'
    ).fetchall()
    
    sample_items = cursor.execute(
        'SELECT name, price, category FROM menu_items LIMIT 5'
    ).fetchall()
    
    print(f'\n📊 Total Records:')
    print(f'   • Restaurants: {rest_count}')
    print(f'   • Menu Items: {item_count}')
    
    print(f'\n🍽️  Sample Restaurants:')
    for i, r in enumerate(sample_restaurants, 1):
        print(f'   {i}. {r[0]} ({r[1]}) - {r[2]}★')
    
    print(f'\n🍕 Sample Menu Items:')
    for item in sample_items:
        print(f'   • {item[0]}: ₹{item[1]:.0f} ({item[2]})')
    
    print(f'\n✓ Database file: smartfood.db')
    print(f'✓ All data persisted and ready to use!')
else:
    print('\n⚠ No tables found')

print('='*70 + '\n')

conn.close()
