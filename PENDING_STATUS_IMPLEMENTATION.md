# Pending Status Implementation - Documentation

## Overview
This document outlines the implementation of the pending status flow for user registrations in the Dwarka Yatra application.

## User Requirements
1. **Email Notification**: Show a message on the receipt page indicating that the registration receipt has been sent to the user's email.
2. **Pending Status Flow**: 
   - When a user proceeds to the payment page, save their registration data in the database with a "Pending" payment status
   - After successful payment, update the status from "Pending" to "Paid"
   - If payment is not completed, delete the pending registrations from the database

## Implementation Details

### 1. Email Notification on Receipt Page
**File**: `templates/receipt.html`

- Added an info alert box below the success message showing that the email has been sent
- The message displays: "Email Sent! We have sent your registration receipt to your email address."
- Styled with Bootstrap's alert-info class for visibility

### 2. Pending Status Flow Implementation

#### A. Database Schema
**File**: `models.py`

The `payment_status` field already exists in both `PassengerInsider` and `PassengerOutsider` models:
```python
payment_status = db.Column(db.String(20), default='Pending')  # Pending, Paid, Failed
```

#### B. Saving Pending Registrations
**File**: `app.py` - `confirm_and_pay()` function (Line 430-537)

When users click "Confirm & Proceed to Payment" on the registration summary page:
1. Generate unique order IDs with "PENDING_" prefix for each traveler
2. Create passenger records in the appropriate table (PassengerInsider or PassengerOutsider)
3. Set `payment_status='Pending'` and `razorpay_payment_id=None`
4. Commit to database
5. Store pending order IDs in session for later update
6. Proceed to payment page

**Key Features**:
- Handles both OTM and non-OTM users
- Parses journey dates properly
- Includes all package details
- Error handling with rollback on failure

#### C. Updating to Paid Status
**File**: `app.py` - `verify_payment()` function (Line 624-782)

After successful Razorpay payment verification:
1. Retrieve pending order IDs from session
2. Find and update existing pending records rather than creating new ones
3. Update:
   - `razorpay_order_id` to the new confirmed order ID
   - `razorpay_payment_id` to the actual payment ID
   - `payment_status` to 'Paid'
4. Handle OTM ID transfer from active to expired table
5. Send confirmation emails
6. Redirect to receipt page

**Fallback Mechanism**:
- If pending records are not found (edge case), falls back to creating new records
- Ensures no payment is lost even if database cleanup happens prematurely

#### D. Cleanup of Pending Registrations
**File**: `app.py` - `cleanup_pending_registrations()` function (Line 1671-1711)

Automatic cleanup function that:
- Deletes registrations with status 'Pending' older than 30 minutes (configurable)
- Queries both PassengerInsider and PassengerOutsider tables
- Uses timestamp-based filtering
- Returns count of deleted records
- Includes error handling and rollback

**Execution Points**:
1. **On App Startup**: Called automatically when `__main__` runs
2. **Manual Admin Trigger**: Via admin dashboard button
3. **Can be scheduled**: Using cron jobs or task schedulers (future enhancement)

#### E. Admin Manual Cleanup
**File**: `app.py` - `admin_cleanup_pending()` function (Line 1713-1723)

Admin route to manually trigger cleanup:
- Accessible via `/admin/cleanup-pending` (POST)
- Requires admin login
- Shows flash message with deleted count
- Redirects back to admin dashboard

**File**: `templates/admin_dashboard.html` (Line 20-25)

Added cleanup button in admin toolbar:
- Red "Cleanup Pending" button with trash icon
- Confirmation dialog before executing
- Inline form submission

## Payment Flow Diagram

```
User Registration
       ↓
Package Selection
       ↓
Review Summary
       ↓
[Click "Confirm & Proceed to Payment"]
       ↓
Save to DB with status='Pending'  ← NEW STEP
       ↓
Payment Gateway (Razorpay)
       ↓
   ┌─────────┬─────────┐
   │         │         │
Payment   Payment   Payment
Success   Failed    Abandoned
   │         │         │
   ↓         ↓         ↓
Update    Leave     Auto-cleanup
to Paid   Pending   after 30 min
   ↓         ↓
Receipt   Database cleanup
  Page    (manual or scheduled)
   ↓
Email sent
```

## Database Cleanup Strategy

### Automatic Cleanup
- **Trigger**: App startup
- **Frequency**: On each app restart
- **Age Threshold**: 30 minutes
- **Scope**: Both Insider and Outsider tables

### Manual Cleanup
- **Trigger**: Admin clicks "Cleanup Pending" button
- **Access**: Admin dashboard
- **Confirmation**: Required
- **Feedback**: Flash message with count

### Future Enhancements
Consider implementing:
1. **Scheduled Cleanup**: Using celery or APScheduler
2. **Webhook for Failed Payments**: Listen to Razorpay webhook for failed payments
3. **User Notification**: Email users about abandoned registrations
4. **Grace Period**: Different cleanup times based on user activity

## Benefits of This Implementation

1. **Data Integrity**: All registrations are tracked even before payment
2. **Recovery**: Admin can see pending registrations and follow up if needed
3. **Analytics**: Can analyze payment abandonment rates
4. **User Experience**: Registration data is safe even if payment temporarily fails
5. **Clean Database**: Automatic cleanup prevents database bloat
6. **Admin Control**: Manual cleanup option for immediate action

## Testing Checklist

- [ ] User completes registration → Check pending record created
- [ ] User completes payment → Check status updated to Paid
- [ ] User abandons payment → Check pending record remains
- [ ] Wait 30 minutes → Check cleanup deletes old pending records
- [ ] Admin clicks cleanup button → Check pending records deleted
- [ ] Multiple users in same session → Check all updated correctly
- [ ] App restart → Check cleanup runs automatically
- [ ] Receipt page shows email notification message

## Notes

- **OTM Handling**: OTM IDs are only moved to expired table after payment is confirmed (Paid status)
- **Session Management**: Pending order IDs stored in session for correlation
- **Error Handling**: Comprehensive try-catch blocks with rollback
- **Logging**: Detailed console logs for debugging
- **Razorpay Integration**: Unchanged, still uses existing order creation flow
