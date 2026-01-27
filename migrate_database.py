"""
Database Migration Script
Updates the database schema to use razorpay_order_id as primary key
"""
from app import app, db
from models import PassengerInsider, PassengerOutsider

def migrate_database():
    """Migrate database to new schema with ORDER_ID as primary key"""
    
    with app.app_context():
        print("\n🔄 Starting database migration...")
        print("=" * 60)
        
        try:
            # Drop existing tables (WARNING: This will delete all data!)
            print("\n⚠️  WARNING: This will DELETE all existing passenger data!")
            response = input("Continue? (yes/no): ")
            
            if response.lower() != 'yes':
                print("❌ Migration cancelled.")
                return
            
            print("\n📦 Dropping old tables...")
            db.drop_all()
            print("✅ Old tables dropped")
            
            print("\n🏗️  Creating new tables with ORDER_ID as primary key...")
            db.create_all()
            print("✅ New tables created successfully!")
            
            print("\n" + "=" * 60)
            print("✅ Database migration completed successfully!")
            print("\nNew schema:")
            print("  - PassengerInsider: razorpay_order_id (PRIMARY KEY)")
            print("  - PassengerOutsider: razorpay_order_id (PRIMARY KEY)")
            print("\nOrder ID prefixes:")
            print("  - Insider (OTM): INS_PENDING_xxx or INS_ORDER_xxx")
            print("  - Outsider (No OTM): OUT_PENDING_xxx or OUT_ORDER_xxx")
            print("\nThis ensures NO ID clashes between tables! ✨")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    migrate_database()
