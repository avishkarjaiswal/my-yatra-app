import sqlite3
import json

def migrate():
    print("Starting migration...")
    conn = sqlite3.connect('instance/yatra.db')
    cursor = conn.cursor()
    
    # Get all dynamic yatra tables
    # Find all tables except the known ones
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    core_tables = ['login_details', 'yatra_details', 'app_settings', 'carousel_image', 'sqlite_sequence']
    
    for table_name in tables:
        if table_name not in core_tables and not table_name.startswith('sqlite_'):
            # It's a dynamic yatra table
            print(f"Checking table: {table_name}")
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = [info[1] for info in cursor.fetchall()]
            
            if 'order_id' not in columns:
                print(f"Adding order_id to {table_name}...")
                cursor.execute(f"ALTER TABLE '{table_name}' ADD COLUMN order_id TEXT")
                
                # We can also generate an order_id for existing rows
                cursor.execute(f"SELECT id FROM '{table_name}'")
                rows = cursor.fetchall()
                if rows:
                    import uuid
                    for r in rows:
                        row_id = r[0]
                        new_order_id = f"ORD-LEGACY-{uuid.uuid4().hex[:8].upper()}"
                        cursor.execute(f"UPDATE '{table_name}' SET order_id = ? WHERE id = ?", (new_order_id, row_id))

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == '__main__':
    migrate()
