from app import app, db
from sqlalchemy import text

def add_missing_columns():
    with app.app_context():
        print("Checking for missing 'otm_type' columns...")
        
        try:
            # 1. Update OTMActive
            print("Updating OTMActive table...")
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE otm_active ADD COLUMN IF NOT EXISTS otm_type VARCHAR(20) DEFAULT 'standard'"))
                conn.execute(text("COMMIT"))
            print("✅ Added otm_type to otm_active")
            
            # 2. Update OTMExpired
            print("Updating OTMExpired table...")
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE otm_expired ADD COLUMN IF NOT EXISTS otm_type VARCHAR(20) DEFAULT 'standard'"))
                conn.execute(text("COMMIT"))
            print("✅ Added otm_type to otm_expired")
            
        except Exception as e:
            print(f"❌ Error adding columns: {e}")

if __name__ == "__main__":
    add_missing_columns()
