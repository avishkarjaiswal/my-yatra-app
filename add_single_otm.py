"""
Script to add a single OTM ID to the otm_active table
"""
from models import db, OTMActive
from app import app

def add_otm_id(otm_id):
    """Add a single OTM ID to the database"""
    with app.app_context():
        # Check if already exists
        existing = OTMActive.query.filter_by(id=otm_id).first()
        if existing:
            print(f"⚠️  OTM ID '{otm_id}' already exists in the database")
        else:
            new_otm = OTMActive(id=otm_id)
            db.session.add(new_otm)
            db.session.commit()
            print(f"✅ Successfully added OTM ID: {otm_id}")
        
        # Show total count
        total = OTMActive.query.count()
        print(f"📊 Total active OTM IDs: {total}")

if __name__ == '__main__':
    add_otm_id('GMP890ST')
