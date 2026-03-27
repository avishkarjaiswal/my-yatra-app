import sqlite3

def migrate():
    print("Starting migration...")
    conn = sqlite3.connect('instance/yatra.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    core_tables = ['login_details', 'yatra_details', 'app_settings', 'carousel_image', 'carousel_images', 'sqlite_sequence']
    
    for table_name in tables:
        if table_name not in core_tables and not table_name.startswith('sqlite_'):
            print(f"Checking table: {table_name}")
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = [info[1] for info in cursor.fetchall()]
            
            if 'passenger_id' not in columns:
                print(f"Adding passenger_id to {table_name}...")
                cursor.execute(f"ALTER TABLE '{table_name}' ADD COLUMN passenger_id INTEGER")
                
                # Backfill passenger_id for existing rows
                cursor.execute(f"SELECT id, login_id, name FROM '{table_name}'")
                rows = cursor.fetchall()
                for r in rows:
                    row_id, lid, nm = r
                    cursor.execute("SELECT id FROM login_details WHERE (login_id=? OR login_id=?) AND name=?", (lid, f"#del#{lid}", nm))
                    p_match = cursor.fetchone()
                    if p_match:
                        cursor.execute(f"UPDATE '{table_name}' SET passenger_id = ? WHERE id = ?", (p_match[0], row_id))

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == '__main__':
    migrate()
