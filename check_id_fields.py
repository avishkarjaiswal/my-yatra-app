"""
Check if ID fields are properly set in passenger tables
"""
from app import app, db
from models import PassengerInsider, PassengerOutsider

def check_id_fields():
    with app.app_context():
        print("\n🔍 Checking ID fields in database...")
        print("=" * 60)
        
        # Check PassengerInsider
        insiders = PassengerInsider.query.all()
        print(f"\n📊 PassengerInsider records: {len(insiders)}")
        
        insiders_without_id = [p for p in insiders if p.id is None]
        print(f"   - Records WITH id: {len(insiders) - len(insiders_without_id)}")
        print(f"   - Records WITHOUT id: {len(insiders_without_id)}")
        
        if insiders_without_id:
            print(f"\n⚠️  Found {len(insiders_without_id)} insider records without ID:")
            for p in insiders_without_id[:5]:  # Show first 5
                print(f"      - {p.name} (Order ID: {p.razorpay_order_id})")
        
        # Check PassengerOutsider
        outsiders = PassengerOutsider.query.all()
        print(f"\n📊 PassengerOutsider records: {len(outsiders)}")
        
        outsiders_without_id = [p for p in outsiders if p.id is None]
        print(f"   - Records WITH id: {len(outsiders) - len(outsiders_without_id)}")
        print(f"   - Records WITHOUT id: {len(outsiders_without_id)}")
        
        if outsiders_without_id:
            print(f"\n⚠️  Found {len(outsiders_without_id)} outsider records without ID:")
            for p in outsiders_without_id[:5]:  # Show first 5
                print(f"      - {p.name} (Order ID: {p.razorpay_order_id})")
        
        # Show some sample IDs
        if insiders and insiders[0].id:
            print(f"\n✅ Sample Insider IDs: {[p.id for p in insiders[:5]]}")
        if outsiders and outsiders[0].id:
            print(f"✅ Sample Outsider IDs: {[p.id for p in outsiders[:5]]}")
        
        print("\n" + "=" * 60)
        
        if insiders_without_id or outsiders_without_id:
            print("❌ Action needed: Some records are missing IDs!")
            print("   Run the fix script to assign IDs to these records.")
        else:
            print("✅ All records have IDs!")

if __name__ == '__main__':
    check_id_fields()
