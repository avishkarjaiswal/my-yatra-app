"""
Database Migration Script - Add ID Column
Adds auto-incrementing ID column to PassengerInsider and PassengerOutsider tables
while preserving razorpay_order_id as primary key
"""
from app import app, db
from models import PassengerInsider, PassengerOutsider

def add_id_column():
    """Add id column to passenger tables"""
    
    with app.app_context():
        print("\n🔄 Starting database migration to add ID column...")
        print("=" * 60)
        
        try:
            # Get SQL connection
            connection = db.engine.raw_connection()
            cursor = connection.cursor()
            
            # Check if columns already exist
            cursor.execute("PRAGMA table_info(passenger_insider)")
            insider_columns = [col[1] for col in cursor.fetchall()]
            
            cursor.execute("PRAGMA table_info(passenger_outsider)")
            outsider_columns = [col[1] for col in cursor.fetchall()]
            
            # Add id column to PassengerInsider if it doesn't exist
            if 'id' not in insider_columns:
                print("\n📝 Adding id column to PassengerInsider...")
                cursor.execute('''
                    ALTER TABLE passenger_insider 
                    ADD COLUMN id INTEGER
                ''')
                
                # Update existing records to have sequential IDs
                cursor.execute('''
                    UPDATE passenger_insider 
                    SET id = (
                        SELECT COUNT(*) 
                        FROM passenger_insider AS p2 
                        WHERE p2.rowid <= passenger_insider.rowid
                    )
                ''')
                
                # Create unique index on id column
                try:
                    cursor.execute('CREATE UNIQUE INDEX idx_insider_id ON passenger_insider(id)')
                except:
                    pass  # Index might already exist
                    
                print("✅ Added id column to PassengerInsider")
            else:
                print("ℹ️  id column already exists in PassengerInsider")
            
            # Add id column to PassengerOutsider if it doesn't exist
            if 'id' not in outsider_columns:
                print("\n📝 Adding id column to PassengerOutsider...")
                cursor.execute('''
                    ALTER TABLE passenger_outsider 
                    ADD COLUMN id INTEGER
                ''')
                
                # Update existing records to have sequential IDs
                cursor.execute('''
                    UPDATE passenger_outsider 
                    SET id = (
                        SELECT COUNT(*) 
                        FROM passenger_outsider AS p2 
                        WHERE p2.rowid <= passenger_outsider.rowid
                    )
                ''')
                
                # Create unique index on id column
                try:
                    cursor.execute('CREATE UNIQUE INDEX idx_outsider_id ON passenger_outsider(id)')
                except:
                    pass  # Index might already exist
                    
                print("✅ Added id column to PassengerOutsider")
            else:
                print("ℹ️  id column already exists in PassengerOutsider")

            
            connection.commit()
            cursor.close()
            connection.close()
            
            print("\n" + "=" * 60)
            print("✅ Database migration completed successfully!")
            print("\nUpdated schema:")
            print("  - PassengerInsider: razorpay_order_id (PRIMARY KEY) + id (UNIQUE)")
            print("  - PassengerOutsider: razorpay_order_id (PRIMARY KEY) + id (UNIQUE)")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    add_id_column()
