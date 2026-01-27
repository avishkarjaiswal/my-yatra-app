# Youth OTM Discount System - Implementation Documentation

## Overview
The Youth OTM system provides **₹5000 fixed pricing** for travelers with OTM IDs containing the word "YOUTH". This is an admin-generated discount system that does NOT use a coupon code like "DISCOUNT5000".

## How It Works

### 1. Detection Logic
- The system automatically detects if an OTM ID contains the word **"YOUTH"** (case-insensitive)
- Examples of valid Youth OTM IDs:
  - `YOUTH2026`
  - `YOUTHDELHI`
  - `youth001`  
  - `MUMBAI-YOUTH`
  - Any ID with "youth" in it

### 2. Pricing Behavior
When a Youth OTM is verified:
- **Total package cost: ₹5000 (fixed)**
- **Hotel category: BASIC (locked/unchangeable)**
- **Travel option: TRAIN (locked/unchangeable)**
- Package enforces standardization - all Youth OTM users get the same package
- Age-based child discounts do NOT apply on top of Youth OTM pricing
- Users can still choose their journey dates

### 3. Admin Workflow

#### Generating Youth OTM IDs
Admins can generate Youth OTM IDs in two ways:

**Option 1: Using the script**
```bash
python add_discount_otm.py
```
This will add sample Youth OTM IDs: `YOUTH2026`, `YOUTHDELHI`, `YOUTH001`

**Option 2: Using admin panel (if OTM generation feature exists)**
- Generate OTM IDs with "YOUTH" in the name
- The system will automatically apply ₹5000 pricing

#### Verifying Youth OTMs
1. Admin creates OTM ID containing "YOUTH"
2. OTM ID is added to `otm_active` table
3. When user verifies this OTM:
   - System checks if "YOUTH" exists in OTM ID (case-insensitive)
   - Returns `is_youth_otm: true` flag
   - Frontend displays ₹5000 fixed pricing
   - Travel booking is unlocked

### 4. Technical Implementation

#### Backend (app.py)
**OTM Verification** (`/verify-otm` endpoint):
```python
is_youth_otm = 'youth' in otm_id.lower()
return jsonify({
    'valid': True,
    'is_youth_otm': is_youth_otm
})
```

**Package Selection Pricing**:
```python
is_youth_otm = False
if has_otm and otm_id:
    is_youth_otm = 'youth' in otm_id.upper()

if is_youth_otm:
    final_amount = 5000
    discount_note = "Youth OTM Package: ₹5000 Fixed Price"
else:
    # Normal pricing with age-based discounts
    ...
```

#### Frontend (package_selection.html)
**Price Calculation**:
```javascript
const isYouthOtm = otmBtn && otmBtn.getAttribute('data-is-youth-otm') === 'true';

if (isYouthOtm) {
    finalPrice = 5000;
    breakdownHTML = `Youth OTM Package - ₹5000 Fixed`;
}
```

**OTM Verification Response**:
```javascript
if (data.is_youth_otm) {
    otmStatus.innerHTML = `Youth Package (₹5000 Fixed)!`;
    unlockTravelBooking(idx);  // No package restrictions
}
```

## Key Differences from Old System

| Feature | Old System (DISCOUNT5000) | New System (Youth OTM) |
|---------|--------------------------|------------------------|
| Detection | `otm_type === 'discount'` | `'youth' in otm_id.lower()` |
| Coupon Code | Required specific code | Any OTM with "YOUTH" |
| Package Restrictions | Forced Basic Hotel + Train | Forced Basic Hotel + Train |
| Hotel Choice | Locked to Basic | Locked to Basic |
| Travel Choice | Locked to Train | Locked to Train |
| Admin Control | Had to create specific OTM type | Just include "YOUTH" in ID |
| Flexibility | Admin creates specific OTM | Admin creates any ID with "YOUTH" |

## Database Schema
No changes required! Uses existing `OTMActive` table:
```python
class OTMActive(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    otm_type = db.Column(db.String(20), default='standard')
    created_at = db.Column(db.DateTime, default=get_india_time)
```

The `otm_type` field can be ignored for Youth OTMs - detection is based on ID content.

## Testing the System

### Test Case 1: Youth OTM - Package is Locked
1. Admin creates OTM: `YOUTH2026`
2. User enters OTM ID on package selection
3. System verifies and shows: "Youth Package (₹5000 Fixed)!"
4. User sees: **Hotel locked to Basic**, **Travel locked to Train**
5. User can select journey dates (e.g., 5 days)
6. **Expected Result**: Total = ₹5000, Basic Hotel, Train Travel

### Test Case 2: Youth OTM - Selections are Overridden
1. User tries to select Premium Hotel before OTM verification
2. User verifies Youth OTM: `YOUTH2026`
3. System automatically changes selections to: Basic Hotel + Train
4. These selections become **locked and unchangeable**
5. **Expected Result**: Total = ₹5000 (Basic + Train enforced)

### Test Case 3: Regular OTM - Full Choice
1. Admin creates OTM: `STANDARD123` (no "YOUTH")
2. User verifies OTM
3. User can freely choose: Premium Hotel, Flight, 5 days
4. **Expected Result**: Normal pricing calculation applies

### Test Case 4: Case Insensitivity
1. OTM IDs work regardless of case:
   - `YOUTH001` ✅
   - `youth001` ✅
   - `Youth001` ✅
   - `yOuTh001` ✅
2. All trigger ₹5000 with Basic + Train

## User Experience Flow

### With Youth OTM:
1. User enters personal details
2. User reaches package selection page
3. User enters Youth OTM ID (e.g., `YOUTH2026`)
4. User clicks "Verify"
5. ✅ Success message: "Youth Package (₹5000 Fixed)!"
6. 🔒 **Hotel automatically set to BASIC** (locked, grayed out)
7. 🔒 **Travel automatically set to TRAIN** (locked, enabled)
8. User can only choose their journey dates
9. Price automatically shows: **₹5000** (fixed)
10. User proceeds to payment with standardized package

### Without Youth OTM:
1-4. Same as above
5. No Youth OTM detected  
6. User can freely choose hotel category
7. User can enable/choose travel option
8. Price calculated based on: hotel + food + days

## Admin Benefits
✅ **Simple to manage**: Just add "YOUTH" to OTM ID  
✅ **Flexible naming**: Can create meaningful IDs like `YOUTH-DELHI-2026`  
✅ **No database changes**: Works with existing structure  
✅ **Easy to track**: All Youth OTMs visible by name  
✅ **Standardized package**: All youth users get same Basic Hotel + Train package  
✅ **Cost predictable**: Always ₹5000 per person

## Files Modified
1. `app.py` - Updated pricing logic and verification endpoint
2. `templates/package_selection.html` - Updated frontend pricing calculation
3. `add_discount_otm.py` - Updated script to create Youth OTM examples

## Next Steps for Admin
To start using the Youth OTM system:

1. **Generate Youth OTMs**:
   ```bash
   python add_discount_otm.py
   ```

2. **Share OTM IDs with users** (e.g., YOUTH2026, YOUTHDELHI)

3. **Monitor bookings** in admin dashboard

4. **Create more as needed** - just ensure "YOUTH" is in the ID

---

**Last Updated**: January 27, 2026  
**System Status**: ✅ Active and Ready to Use
