"""
Migration script to split Passenger table into PassengerInsider and PassengerOutsider
Run this script to create new tables and migrate existing data
"""
from models import db, PassengerInsider, PassengerOutsider
from app import app

def migrate_to_split_tables():
    """Create new passenger tables and optionally migrate old data"""
    with app.app_context():
        print("🔄 Starting database migration...")
        print("=" * 60)
        
        # Create all tables (including new ones)
        db.create_all()
        print("✅ Created PassengerInsider and PassengerOutsider tables")
        
        # Check if old Passenger table exists and has data
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'passenger' in tables:
                print("\n⚠️  Found old 'passenger' table")
                
                # Count records in old table
                result = db.session.execute(text("SELECT COUNT(*) FROM passenger"))
                count = result.scalar()
                
                if count > 0:
                    print(f"📊 Found {count} records in old passenger table")
                    print("\n🔄 Migrating data to new tables...")
                    
                    # Fetch all records from old table
                    result = db.session.execute(text("""
                        SELECT id, name, email, phone, alternative_phone, age, gender, 
                               city, district, state, journey_start_date, journey_end_date,
                               num_days, hotel_category, travel_medium, has_otm, otm_id,
                               yatra_class, razorpay_order_id, razorpay_payment_id,
                               amount, payment_status, created_at
                        FROM passenger
                    """))
                    
                    migrated_insiders = 0
                    migrated_outsiders = 0
                    
                    from datetime import datetime, date
                    
                    for row in result:
                        row_dict = row._asdict()
                        
                        # Convert date strings to date objects if needed
                        journey_start = row_dict['journey_start_date']
                        journey_end = row_dict['journey_end_date']
                        created_at_val = row_dict['created_at']
                        
                        if isinstance(journey_start, str):
                            journey_start = datetime.strptime(journey_start, '%Y-%m-%d').date()
                        if isinstance(journey_end, str):
                            journey_end = datetime.strptime(journey_end, '%Y-%m-%d').date()
                        if isinstance(created_at_val, str):
                            try:
                                created_at_val = datetime.strptime(created_at_val, '%Y-%m-%d %H:%M:%S.%f')
                            except:
                                created_at_val = datetime.strptime(created_at_val, '%Y-%m-%d %H:%M:%S')
                        
                        if row_dict['has_otm'] and row_dict['otm_id']:
                            # Migrate to PassengerInsider
                            insider = PassengerInsider(
                                name=row_dict['name'],
                                email=row_dict['email'],
                                phone=row_dict['phone'],
                                alternative_phone=row_dict['alternative_phone'],
                                age=row_dict['age'],
                                gender=row_dict['gender'],
                                city=row_dict['city'],
                                district=row_dict['district'],
                                state=row_dict['state'],
                                journey_start_date=journey_start,
                                journey_end_date=journey_end,
                                num_days=row_dict['num_days'],
                                hotel_category=row_dict['hotel_category'],
                                travel_medium=row_dict['travel_medium'],
                                has_otm=True,
                                otm_id=row_dict['otm_id'],
                                yatra_class=row_dict['yatra_class'],
                                razorpay_order_id=row_dict['razorpay_order_id'],
                                razorpay_payment_id=row_dict['razorpay_payment_id'],
                                amount=row_dict['amount'],
                                payment_status=row_dict['payment_status'],
                                created_at=created_at_val
                            )
                            db.session.add(insider)
                            migrated_insiders += 1
                        else:
                            # Migrate to PassengerOutsider
                            outsider = PassengerOutsider(
                                name=row_dict['name'],
                                email=row_dict['email'],
                                phone=row_dict['phone'],
                                alternative_phone=row_dict['alternative_phone'],
                                age=row_dict['age'],
                                gender=row_dict['gender'],
                                city=row_dict['city'],
                                district=row_dict['district'],
                                state=row_dict['state'],
                                journey_start_date=journey_start,
                                journey_end_date=journey_end,
                                num_days=row_dict['num_days'],
                                hotel_category=row_dict['hotel_category'],
                                travel_medium=row_dict['travel_medium'],
                                has_otm=False,
                                otm_id=None,
                                yatra_class=row_dict['yatra_class'],
                                razorpay_order_id=row_dict['razorpay_order_id'],
                                razorpay_payment_id=row_dict['razorpay_payment_id'],
                                amount=row_dict['amount'],
                                payment_status=row_dict['payment_status'],
                                created_at=created_at_val
                            )
                            db.session.add(outsider)
                            migrated_outsiders += 1
                    
                    db.session.commit()
                    
                    print(f"✅ Migrated {migrated_insiders} records to PassengerInsider table")
                    print(f"✅ Migrated {migrated_outsiders} records to PassengerOutsider table")
                    
                    print("\n⚠️  Old 'passenger' table still exists.")
                    print("   You can rename or drop it manually if you want:")
                    print("   Option 1: Rename - ALTER TABLE passenger RENAME TO passenger_backup;")
                    print("   Option 2: Drop   - DROP TABLE passenger;")
                else:
                    print("ℹ️  Old passenger table is empty, no migration needed")
        
        except Exception as e:
            print(f"ℹ️  No old passenger table found or error checking: {str(e)}")
        
        print("\n" + "=" * 60)
        print("🎉 Migration completed successfully!")
        print("\nNew table structure:")
        print("  📋 passenger_insider  - For passengers with OTM")
        print("  📋 passenger_outsider - For passengers without OTM")
        
        # Show current counts
        insiders_count = PassengerInsider.query.count()
        outsiders_count = PassengerOutsider.query.count()
        print(f"\n📊 Current data:")
        print(f"   Insiders: {insiders_count}")
        print(f"   Outsiders: {outsiders_count}")
        print(f"   Total: {insiders_count + outsiders_count}")

if __name__ == '__main__':
    migrate_to_split_tables()
