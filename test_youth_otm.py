"""
Quick test to verify Youth OTM IDs in database
"""
from models import db, OTMActive
from app import app

with app.app_context():
    print("\n=== Checking Youth OTM IDs in Database ===\n")
    
    # Check for Youth OTM IDs
    youth_otms = OTMActive.query.filter(OTMActive.id.like('%YOUTH%')).all()
    
    if youth_otms:
        print(f"✅ Found {len(youth_otms)} Youth OTM(s):")
        for otm in youth_otms:
            # Test the detection logic
            is_youth = 'youth' in otm.id.lower()
            is_youth_upper = 'YOUTH' in otm.id.upper()
            print(f"  - ID: {otm.id}")
            print(f"    Type: {otm.otm_type}")
            print(f"    Lowercase check ('youth' in id.lower()): {is_youth}")
            print(f"    Uppercase check ('YOUTH' in id.upper()): {is_youth_upper}")
            print()
    else:
        print("❌ No Youth OTM IDs found in database!")
        print("\nRun: python add_discount_otm.py to create them")
    
    # List all OTM IDs
    all_otms = OTMActive.query.all()
    print(f"\n=== All OTM IDs in Database ({len(all_otms)} total) ===")
    for otm in all_otms:
        print(f"  - {otm.id} ({otm.otm_type})")
