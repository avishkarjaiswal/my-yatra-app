"""
DEMO SCRIPT: Simulating Orphaned Booking Recovery
-------------------------------------------------
This script simulates what happens when a payment is successful 
but the database fails to save the ticket.
"""
import json
import os
from datetime import datetime

def simulate_critical_failure():
    print("🚀 Simulating Payment Verification Process...")
    
    # 1. Mock Data (Simulating what would be in the session)
    razorpay_payment_id = "pay_Demo12345Verify"
    razorpay_order_id = "order_Demo98765"
    
    travelers_data = [
        {
            "name": "Amit Kumar",
            "age": 35,
            "gender": "Male",
            "phone": "9876543210",
            "email": "amit.demo@example.com",
            "package": "Premium Hotel",
            "amount": 25000,
            "has_otm": True,
            "otm_id": "GMP_DEMO_01"
        },
        {
            "name": "Priya Singh",
            "age": 32,
            "gender": "Female",
            "phone": "9876543210",
            "email": "priya.demo@example.com",
            "package": "Premium Hotel",
            "amount": 25000,
            "has_otm": False,
            "otm_id": None
        }
    ]

    print(f"✅ Payment Verified: {razorpay_payment_id}")
    print("⚡ Attempting to save to database...")
    
    # 2. Simulate a Database Crash
    try:
        # Intentionally raising an error to simulate DB failure
        raise Exception("Simulated Database Connection Timeout - INSERT FAILED")
        
    except Exception as db_error:
        print(f"❌ [CRITICAL ERROR] Database Insert Failed: {str(db_error)}")
        print("🛡️  Activating Emergency Backup Protocol...")
        
        # 3. THE EMERGENCY BACKUP LOGIC (Copied from app.py)
        orphaned_data = {
            'timestamp': datetime.now().isoformat(),
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_order_id': razorpay_order_id,
            'error': str(db_error),
            'travelers_data': travelers_data
        }
        
        backup_file = 'orphaned_bookings.json'
        try:
            # Append to existing file or create new
            existing_data = []
            if os.path.exists(backup_file):
                with open(backup_file, 'r') as f:
                    try:
                        existing_data = json.load(f)
                    except json.JSONDecodeError:
                        existing_data = []
            
            existing_data.append(orphaned_data)
            
            with open(backup_file, 'w') as f:
                json.dump(existing_data, f, indent=4)
                
            print(f"✅ [SUCCESS] Orphaned booking saved to {os.path.abspath(backup_file)}")
            print("📝 You can now open this file to recover the data.")
            
        except Exception as backup_error:
            print(f"[FATAL] Could not save backup file: {str(backup_error)}")

if __name__ == "__main__":
    simulate_critical_failure()
