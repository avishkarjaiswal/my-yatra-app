import sqlite3

def add_columns():
    conn = sqlite3.connect('instance/yatra.db')
    cursor = conn.cursor()
    
    try:
        # Add otm_type to otm_active
        cursor.execute("ALTER TABLE otm_active ADD COLUMN otm_type TEXT DEFAULT 'standard'")
        print("✅ Added otm_type to otm_active")
    except sqlite3.OperationalError as e:
        print(f"⚠️ otm_active: {e}")

    try:
        # Add otm_type to otm_expired
        cursor.execute("ALTER TABLE otm_expired ADD COLUMN otm_type TEXT DEFAULT 'standard'")
        print("✅ Added otm_type to otm_expired")
    except sqlite3.OperationalError as e:
        print(f"⚠️ otm_expired: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_columns()
