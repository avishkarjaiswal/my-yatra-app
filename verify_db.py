"""
Database Verification Script
This script checks the database schema and verifies data is being saved correctly.
"""
import sqlite3
import os

db_path = 'instance/yatra.db'

if not os.path.exists(db_path):
    print("❌ Database file not found!")
    print(f"   Looking for: {db_path}")
    exit(1)

print("✅ Database file found")
print("=" * 60)

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check tables
print("\n📋 DATABASE TABLES:")
print("-" * 60)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for table in tables:
    print(f"  ✓ {table[0]}")

# Check Registration schema
print("\n📊 REGISTRATION TABLE SCHEMA:")
print("-" * 60)
cursor.execute("PRAGMA table_info(registration);")
for column in cursor.fetchall():
    print(f"  {column[1]:<20} {column[2]:<15} {'NOT NULL' if column[3] else 'NULLABLE'}")

# Check Passenger schema
print("\n📊 PASSENGER TABLE SCHEMA:")
print("-" * 60)
cursor.execute("PRAGMA table_info(passenger);")
for column in cursor.fetchall():
    print(f"  {column[1]:<20} {column[2]:<15} {'NOT NULL' if column[3] else 'NULLABLE'}")

# Check Payment schema
print("\n📊 PAYMENT TABLE SCHEMA:")
print("-" * 60)
cursor.execute("PRAGMA table_info(payment);")
for column in cursor.fetchall():
    print(f"  {column[1]:<20} {column[2]:<15} {'NOT NULL' if column[3] else 'NULLABLE'}")

# Count records
print("\n📈 RECORD COUNTS:")
print("-" * 60)
cursor.execute("SELECT COUNT(*) FROM registration")
reg_count = cursor.fetchone()[0]
print(f"  Registrations: {reg_count}")

cursor.execute("SELECT COUNT(*) FROM passenger")
pass_count = cursor.fetchone()[0]
print(f"  Passengers: {pass_count}")

cursor.execute("SELECT COUNT(*) FROM payment")
pay_count = cursor.fetchone()[0]
print(f"  Payments: {pay_count}")

# Show sample data if exists
if reg_count > 0:
    print("\n📄 SAMPLE REGISTRATIONS:")
    print("-" * 60)
    cursor.execute("""
        SELECT r.id, r.created_at, COUNT(p.id) as passenger_count, py.amount, py.status
        FROM registration r
        LEFT JOIN passenger p ON p.registration_id = r.id
        LEFT JOIN payment py ON py.registration_id = r.id
        GROUP BY r.id
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"  Reg ID: {row[0]} | Created: {row[1]} | Passengers: {row[2]} | Amount: ₹{row[3]} | Status: {row[4]}")

if pass_count > 0:
    print("\n👥 SAMPLE PASSENGERS:")
    print("-" * 60)
    cursor.execute("""
        SELECT id, registration_id, name, age, gender, yatra_class, email, phone
        FROM passenger
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"  ID: {row[0]} | Reg: {row[1]} | Name: {row[2]} | Age: {row[3]} | Gender: {row[4]} | Class: {row[5]}")
        if row[6] or row[7]:
            print(f"       Email: {row[6] or 'N/A'} | Phone: {row[7] or 'N/A'}")

print("\n" + "=" * 60)
print("✅ Database verification complete!")
print("\nTo test the system:")
print("1. Visit http://127.0.0.1:5000/register")
print("2. Add travelers and submit")
print("3. Run this script again to verify data was saved")
print("=" * 60)

conn.close()
