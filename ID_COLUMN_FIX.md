# Database Schema Fix - ID Column Addition

## Issue
The application was throwing an `AttributeError: 'PassengerInsider' object has no attribute 'id'` when trying to access the admin dashboard.

## Root Cause
The `PassengerInsider` and `PassengerOutsider` models were using `razorpay_order_id` as the primary key, but the code in `admin_dashboard()` and other places was trying to access an `id` attribute that didn't exist.

## Solution
We added an auto-incrementing `id` column to both passenger tables while maintaining `razorpay_order_id` as the primary key.

### Changes Made

#### 1. Updated Models (`models.py`)
- **PassengerInsider**: Added `id = db.Column(db.Integer, autoincrement=True, unique=True, nullable=False)` before the `razorpay_order_id` field
- **PassengerOutsider**: Added the same `id` column

#### 2. Created Migration Script (`add_id_column_migration.py`)
- Script adds the `id` column to both tables using `ALTER TABLE`
- Assigns sequential IDs to existing records based on `rowid`
- Creates unique indexes on the `id` columns for both tables
- Preserves all existing data

#### 3. Executed Migration
- Ran `python add_id_column_migration.py` successfully
- Both tables now have the `id` column with unique sequential values

## Database Schema After Fix

### PassengerInsider
- `id` (INTEGER, UNIQUE, AUTO-INCREMENT) - For reference and display
- `razorpay_order_id` (STRING, PRIMARY KEY) - Main identifier for payments
- Other fields remain unchanged

### PassengerOutsider  
- `id` (INTEGER, UNIQUE, AUTO-INCREMENT) - For reference and display
- `razorpay_order_id` (STRING, PRIMARY KEY) - Main identifier for payments
- Other fields remain unchanged

## Benefits
1. **Fixed AttributeError**: The `admin_dashboard()` function can now access `p.id` without errors
2. **Backward Compatibility**: Existing code using `razorpay_order_id` continues to work
3. **Data Preservation**: All existing passenger records retained their data
4. **OTM Tracking**: The `OTMExpired` table can now properly track which passenger ID used an OTM code

## Testing
After restarting the Flask app, the admin dashboard should now load without errors. The `id` field is displayed in all admin views.

## Important Notes
- The `id` is auto-incrementing but is NOT the primary key
- The primary key remains `razorpay_order_id` to prevent ID conflicts between Insider and Outsider tables
- When creating new records, the `id` field will be automatically populated by SQLite
- The migration is idempotent - running it again won't cause issues (it checks if columns exist first)
