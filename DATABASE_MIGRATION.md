# Database Schema Update - ORDER_ID as Primary Key

## Summary of Changes

### ✅ **What Was Changed**

1. **Primary Key Updated**:
   - **Before**: Auto-incrementing `id` (Integer)
   - **After**: `razorpay_order_id` (String) as PRIMARY KEY

2. **ID Clash Prevention**:
   - **Insider Orders** (with OTM): Use prefix `INS_`
   - **Outsider Orders** (no OTM): Use prefix `OUT_`

### 📊 **Order ID Format**

| Status | Insider (OTM) | Outsider (No OTM) |
|--------|---------------|-------------------|
| **Pending** | `INS_PENDING_XXXXXXXXXXXX` | `OUT_PENDING_XXXXXXXXXXXX` |
| **Confirmed** | `INS_ORDER_XXXXXXXXXXXX` | `OUT_ORDER_XXXXXXXXXXXX` |

*XXXXXXXXXXXX = 12-character random hex*

### 🔧 **Files Modified**

1. **`models.py`**:
   - `PassengerInsider`: razorpay_order_id as primary key
   - `PassengerOutsider`: razorpay_order_id as primary key
   - Removed auto-increment `id` field

2. **`app.py`**:
   - `confirm_and_pay()`: Added INS_/OUT_ prefix to pending order IDs
   - `create_payment()`: Added INS_/OUT_ prefix to final order IDs

### 🚀 **How to Apply Migration**

**Option 1: Fresh Start (Recommended for Testing)**
```bash
python migrate_database.py
```
This will:
- Drop existing tables
- Recreate with new schema
- All data will be lost (ask for confirmation)

**Option 2: Manual Migration (For Production)**
If you have important data:
1. Backup your database first
2. Export existing passenger data
3. Run migration
4. Re-import data with new order ID format

### 📝 **Example Usage**

**Insider Registration (with OTM YOUTH2026)**:
```
Pending: INS_PENDING_A1B2C3D4E5F6
Confirmed: INS_ORDER_7G8H9I0J1K2L
```

**Outsider Registration (no OTM)**:
```
Pending: OUT_PENDING_M3N4O5P6Q7R8
Confirmed: OUT_ORDER_S9T0U1V2W3X4
```

### ✨ **Benefits**

1. ✅ **No ID Clashes**: Insider and Outsider IDs are clearly separated
2. ✅ **Better Tracking**: Can identify user type from order ID alone
3. ✅ **Razorpay Integration**: Order ID is the natural primary key
4. ✅ **Scalability**: String-based IDs can handle any format

### 🔍 **Testing**

After migration:
1. Register an Insider (with Youth OTM)
   - Check order ID starts with `INS_`
2. Register an Outsider (no OTM)
   - Check order ID starts with `OUT_`
3. Verify in database:
   ```python
   python test_database.py
   ```

### ⚠️ **Important Notes**

- **Database Structure**: Primary key is now `razorpay_order_id` (not `id`)
- **Existing Code**: All references to `passenger.id` should use `passenger.razorpay_order_id`
- **Unique Constraint**: ORDER_ID is unique across BOTH tables
- **No Auto-Increment**: IDs are generated using UUID, not sequential numbers

### 🎯 **Next Steps**

1. **Backup** your current database
2. **Run** `python migrate_database.py`
3. **Test** a complete registration flow
4. **Verify** order IDs in database tables

---

**Last Updated**: January 27, 2026  
**Status**: ✅ Ready for Migration
