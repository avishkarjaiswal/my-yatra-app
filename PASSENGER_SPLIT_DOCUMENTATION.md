# Database Schema Update - Passenger Split

## Overview
The database schema has been successfully updated to split passenger data into two separate tables based on OTM (One Time Membership) status.

## Changes Made

### 1. **New Database Models** (`models.py`)

#### PassengerInsider Table
- **Purpose**: Stores data for passengers who have a valid OTM ID
- **Table Name**: `passenger_insider`
- **Key Fields**:
  - All standard passenger fields (name, email, phone, age, etc.)
  - `has_otm`: Always `True`
  - `otm_id`: Required field (cannot be NULL)
  - All package and payment fields

#### PassengerOutsider Table
- **Purpose**: Stores data for passengers who do NOT have an OTM ID
- **Table Name**: `passenger_outsider`
- **Key Fields**:
  - All standard passenger fields (name, email, phone, age, etc.)
  - `has_otm`: Always `False`
  - `otm_id`: Optional (usually NULL)
  - All package and payment fields

### 2. **Application Logic Updates** (`app.py`)

#### Updated Routes:
1. **`/payment`** (create_payment)
   - Now routes passengers to the correct table based on `has_otm` status
   - Insiders go to `PassengerInsider` table
   - Outsiders go to `PassengerOutsider` table

2. **`/verify-payment`**
   - Searches both tables when updating payment status
   - Handles OTM transfer from active to expired (only for insiders)

3. **`/receipt/<order_ids>`**
   - Queries both tables to retrieve all passengers

4. **`/download-receipt/<order_ids>`**
   - Queries both tables for PDF generation

5. **`/admin/dashboard`**
   - Shows passengers from both tables combined
   - Provides counts for insiders and outsiders

6. **`/admin/export/excel`** and **`/admin/export/csv`**
   - Exports data from both tables
   - Includes "Passenger Type" column to distinguish insiders from outsiders
   - Shows OTM ID for insiders, "N/A" for outsiders

### 3. **Migration Script** (`migrate_split_passengers.py`)

A migration script was created and executed to:
- Create the new `passenger_insider` and `passenger_outsider` tables
- Migrate existing data from the old `passenger` table
- Route passengers to the correct table based on their OTM status

**Migration Results**:
- ✅ 0 passengers migrated to `passenger_insider`
- ✅ 1 passenger migrated to `passenger_outsider`

## How It Works

### For New Registrations:

1. **User fills registration form** → Personal details stored in session
2. **User selects package options** → Chooses whether they have OTM
3. **User proceeds to payment** → System determines table based on OTM status:
   - If `has_otm = True` and valid OTM ID → Save to `PassengerInsider`
   - If `has_otm = False` or no OTM ID → Save to `PassengerOutsider`

### For Admin Dashboard:

- Shows all passengers from both tables combined
- Displays separate counts for insiders and outsiders
- Export functions include passenger type information

### For Receipts & Emails:

- System queries both tables to find all passengers for an order
- Works seamlessly regardless of which table the passenger is in

## Benefits

1. **Clear Data Segregation**: Easy to identify and manage OTM members separately
2. **Better Analytics**: Quick counts and reports on OTM vs non-OTM passengers
3. **Data Integrity**: OTM ID is required for insiders, ensuring data quality
4. **Flexible Exports**: Admin can see which passengers are insiders/outsiders in exports

## Database Status

### Current Tables:
- ✅ `passenger_insider` - Active (0 records)
- ✅ `passenger_outsider` - Active (1 record)
- ⚠️  `passenger` - Old table (still exists, can be dropped)

### Recommendation:
You can safely drop or rename the old `passenger` table after verifying everything works:

```sql
-- Option 1: Rename as backup
ALTER TABLE passenger RENAME TO passenger_backup;

-- Option 2: Drop completely (make sure you have a backup!)
DROP TABLE passenger;
```

## Testing Checklist

Before going live, test the following scenarios:

- [ ] Register a passenger WITH OTM ID → Verify data goes to `passenger_insider`
- [ ] Register a passenger WITHOUT OTM ID → Verify data goes to `passenger_outsider`
- [ ] Complete payment for both types → Verify payment updates correctly
- [ ] View receipts → Verify receipts work for both types
- [ ] Admin dashboard → Verify all passengers appear
- [ ] Export to Excel/CSV → Verify passenger type column appears
- [ ] OTM ID verification → Verify valid/invalid OTM IDs work correctly

## Notes

- All existing functionality remains the same from the user's perspective
- The change is transparent to end users
- Only the underlying data storage has changed
- Admin interface now shows more detailed information about passenger types
