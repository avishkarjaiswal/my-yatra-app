# Timezone and Registration Form Updates

## Date: 2026-01-22

## Changes Implemented

### 1. ✅ Fixed Timezone to India Standard Time (IST)

**Problem**: The `created_at` column was storing dates and times in UTC instead of India timezone (IST = UTC+5:30).

**Solution**: Updated all database models to use India timezone.

#### Files Modified:

**`models.py`**:
- Added `get_india_time()` utility function that calculates IST from UTC
- Updated all `created_at` fields in:
  - `PassengerInsider` model
  - `PassengerOutsider` model
  - `OTMActive` model
- Updated `expired_at` field in `OTMExpired` model
- All timestamps now use `default=get_india_time` instead of `default=datetime.utcnow`

**`app.py`**:
- Updated `cleanup_pending_registrations()` function to use `get_india_time()` instead of `datetime.utcnow()` for accurate time-based filtering

#### India Time Function:
```python
def get_india_time():
    """Returns current time in India Standard Time (IST)"""
    utc_now = datetime.utcnow()
    ist_offset = timedelta(hours=5, minutes=30)
    return utc_now + ist_offset
```

#### Impact:
- ✅ All new registrations will have correct India timestamps
- ✅ Admin dashboard will show correct local times
- ✅ Cleanup function will work with correct timezone
- ✅ Existing records will remain unchanged (migration not needed for timestamps)

---

### 2. ✅ Updated Registration Form - Add Traveler Button Required

**Problem**: The registration form automatically showed one traveler input field on page load without user interaction.

**Solution**: Modified the form to require users to explicitly click the "Add Traveler" button first.

#### Files Modified:

**`templates/register.html`**:

1. **Removed Auto-Add Functionality**:
   - Deleted the `DOMContentLoaded` event listener that automatically added the first passenger
   - Now the form starts with an empty traveler container

2. **Added Validation**:
   - Added form submission validation to check if at least one traveler has been added
   - Shows alert: "Please add at least one traveler by clicking the 'Add Traveler' button."
   - Prevents form submission if no travelers are added

#### User Experience Flow:

**Before**:
```
Page Load → First Traveler Form Automatically Shown → Continue
```

**After**:
```
Page Load → Empty Form → User Clicks "Add Traveler" → Traveler Form Appears → Continue
```

#### Benefits:
- ✅ More intentional user interaction
- ✅ Clearer UI - users understand they need to add travelers
- ✅ Prevents accidental submissions with default values
- ✅ Maintains all existing functionality (guardian selection, state-district mapping, etc.)

---

## Testing Checklist

### Timezone Testing:
- [ ] Create a new registration and verify `created_at` shows India time
- [ ] Check admin dashboard displays correct timestamps
- [ ] Verify cleanup function uses correct timezone for filtering
- [ ] Check OTM active/expired timestamps are in IST

### Registration Form Testing:
- [ ] Open registration page - confirm no traveler fields are shown initially
- [ ] Click "Add Traveler" button - confirm traveler form appears
- [ ] Add multiple travelers - confirm all work correctly
- [ ] Try to submit form without adding travelers - confirm validation error
- [ ] Add traveler and submit - confirm form submits successfully
- [ ] Test guardian selection still works for children
- [ ] Test state-district dropdown still works
- [ ] Test removing travelers still works

---

## Notes

### Timezone Considerations:
- The timezone change only affects **new records** created after this update
- Existing records in the database will still have UTC timestamps
- To convert existing records, create a migration script (optional)
- The IST offset is hardcoded (5 hours 30 minutes) and doesn't account for DST (India doesn't observe DST)

### Form Behavior:
- The "Add Traveler" button must be clicked at least once before submission
- All other form validations remain intact (required fields, guardian selection, etc.)
- Remove traveler functionality unchanged
- Form can still add unlimited travelers

---

## Code Changes Summary

### models.py
- ➕ Added `get_india_time()` function
- 🔄 Changed 4 `datetime.utcnow` references to `get_india_time`

### app.py
- 🔄 Updated cleanup function to import and use `get_india_time()`

### templates/register.html
- ➖ Removed auto-add first passenger on page load
- ➕ Added validation for empty traveler list
- 🔄 Updated form submission handler

---

## Future Enhancements

Consider implementing:
1. **Migration Script**: Convert existing UTC timestamps to IST (if needed)
2. **Timezone Display**: Show timezone indicator in admin dashboard (e.g., "22 Jan 2026, 16:14 IST")
3. **User Timezone**: Allow admin to configure timezone preference
4. **Helpful Text**: Add text on registration page: "Click 'Add Traveler' to begin"
