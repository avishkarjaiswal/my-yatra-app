"""
Script to add sample OTM IDs to the otm_active table for testing
Run this after starting the Flask app to populate some test OTM IDs
"""
from models import db, OTMActive
from app import app

def add_sample_otm_ids():
    """Add some sample OTM IDs to the database"""
    sample_ids = [
        # Mixed alphanumeric patterns
        'GMPA1B2C',
        'GMPX9Y8Z',
        'GMP12345',
        'GMPABC12',
        'GMPXYZ99',
        'GMP54321',
        'GMPD4E5F',
        'GMP7G8H9',
        'GMPM1N2P',
        'GMPQ3R4S',
        
        # Sequential numeric
        'GMP00001',
        'GMP00002',
        'GMP00003',
        'GMP00004',
        'GMP00005',
        'GMP00010',
        'GMP00020',
        'GMP00030',
        
        # More alphanumeric combinations
        'GMPT5U6V',
        'GMPW7X8Y',
        'GMPZ9A0B',
        'GMPC1D2E',
        'GMPF3G4H',
        'GMPK7L8M',
        'GMPN9P0Q',
        'GMPR1S2T',
        'GMPV3W4X',
        'GMPY5Z6A',
        
        # Random alphanumeric patterns
        'GMP3B7D9',
        'GMPE4F8G',
        'GMP1H5J2',
        'GMPI6K0L',
        'GMP9M3N7',
        'GMPO8P4Q',
        'GMP2R6S1',
        'GMPT0U5V',
        'GMP4W8X3',
        'GMPY7Z9A',
        
        # Starting with letters
        'GMPAB123',
        'GMPCD456',
        'GMPEF789',
        'GMPGH012',
        'GMPIJ345',
        'GMPKL678',
        'GMPMN901',
        'GMPOP234',
        'GMPQR567',
        'GMPST890',
        
        # Ending with letters
        'GMP123AB',
        'GMP456CD',
        'GMP789EF',
        'GMP012GH',
        'GMP345IJ',
        'GMP678KL',
        'GMP901MN',
        'GMP234OP',
        'GMP567QR',
        'GMP890ST'
    ]
    
    with app.app_context():
        # Check and add each ID
        added = 0
        for otm_id in sample_ids:
            # Check if already exists
            existing = OTMActive.query.filter_by(id=otm_id).first()
            if not existing:
                new_otm = OTMActive(id=otm_id)
                db.session.add(new_otm)
                added += 1
                print(f"✅ Added OTM ID: {otm_id}")
            else:
                print(f"⚠️  OTM ID already exists: {otm_id}")
        
        db.session.commit()
        print(f"\n🎉 Successfully added {added} new OTM IDs to the database!")
        print(f"📊 Total active OTM IDs: {OTMActive.query.count()}")

if __name__ == '__main__':
    add_sample_otm_ids()
