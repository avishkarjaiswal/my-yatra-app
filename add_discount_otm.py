"""
Script to add Youth OTM IDs to the otm_active table for testing
Youth OTMs (containing "YOUTH" in the ID) automatically get ₹5000 fixed pricing
"""
from models import db, OTMActive
from app import app

def add_youth_otm():
    """Add Youth OTM IDs for fixed ₹5000 pricing"""
    
    # Example Youth OTM IDs
    youth_otm_ids = [
        'YOUTH2026',      # Example 1
        'YOUTHDELHI',     # Example 2
        'YOUTH001',       # Example 3
    ]
    
    with app.app_context():
        for otm_id in youth_otm_ids:
            # Check if already exists
            existing = OTMActive.query.filter_by(id=otm_id).first()
            if existing:
                print(f"⚠️  Youth OTM {otm_id} already exists")
            else:
                new_otm = OTMActive(id=otm_id, otm_type='standard')  # Type doesn't matter for Youth OTMs
                db.session.add(new_otm)
                print(f"✅ Added Youth OTM: {otm_id} (₹5000 fixed pricing will apply)")
        
        # Also add a regular OTM for comparison
        regular_otm = 'STANDARD123'
        existing_std = OTMActive.query.filter_by(id=regular_otm).first()
        if not existing_std:
            db.session.add(OTMActive(id=regular_otm, otm_type='standard'))
            print(f"✅ Added Regular OTM: {regular_otm} (normal pricing will apply)")
        
        db.session.commit()
        print(f"\n🎉 Done! Youth OTMs containing 'YOUTH' will get ₹5000 fixed pricing automatically.")
        print(f"📝 NOTE: Any OTM ID with 'YOUTH' in it (case-insensitive) triggers ₹5000 pricing.")

if __name__ == '__main__':
    add_youth_otm()
