"""
Fix missing ID fields - Assign sequential IDs to records without them
"""
from app import app, db
from models import PassengerInsider, PassengerOutsider

def fix_missing_ids():
    """Assign IDs to passenger records that don't have them"""
    
    with app.app_context():
        print("\n🔧 Fixing missing ID fields...")
        print("=" * 60)
        
        try:
            # Fix PassengerInsider
            insiders = PassengerInsider.query.all()
            insiders_fixed = 0
            
            print(f"\n📝 Checking {len(insiders)} PassengerInsider records...")
            
            # Get the highest existing ID to start from
            max_id = 0
            for p in insiders:
                if p.id and p.id > max_id:
                    max_id = p.id
            
            next_id = max_id + 1
            
            for p in insiders:
                if p.id is None:
                    p.id = next_id
                    next_id += 1
                    insiders_fixed += 1
                    print(f"   ✅ Assigned ID {p.id} to {p.name} (Order: {p.razorpay_order_id})")
            
            # Fix PassengerOutsider
            outsiders = PassengerOutsider.query.all()
            outsiders_fixed = 0
            
            print(f"\n📝 Checking {len(outsiders)} PassengerOutsider records...")
            
            # Get the highest existing ID to start from
            max_id = 0
            for p in outsiders:
                if p.id and p.id > max_id:
                    max_id = p.id
            
            next_id = max_id + 1
            
            for p in outsiders:
                if p.id is None:
                    p.id = next_id
                    next_id += 1
                    outsiders_fixed += 1
                    print(f"   ✅ Assigned ID {p.id} to {p.name} (Order: {p.razorpay_order_id})")
            
            # Commit changes
            if insiders_fixed > 0 or outsiders_fixed > 0:
                db.session.commit()
                print("\n" + "=" * 60)
                print("✅ Fix completed successfully!")
                print(f"   - Fixed {insiders_fixed} PassengerInsider records")
                print(f"   - Fixed {outsiders_fixed} PassengerOutsider records")
                print(f"   - Total: {insiders_fixed + outsiders_fixed} records updated")
            else:
                print("\n" + "=" * 60)
                print("ℹ️  No records needed fixing - all IDs are already assigned!")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    fix_missing_ids()
