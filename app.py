from flask import Flask, render_template, request, redirect, url_for, flash, send_file, Response, session, jsonify
from models import db, PassengerInsider, PassengerOutsider, OTMActive, OTMExpired
from email_utils import generate_receipt_pdf, send_receipt_email
import os
import pandas as pd
import io
import uuid
import razorpay
import hmac
import hashlib
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Flask Configuration - Load from environment variables
# Flask Configuration - Load from environment variables
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key-change-in-production')

# Database Configuration
database_url = os.getenv('DATABASE_URI', 'sqlite:///yatra.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Razorpay Configuration - Load from environment variables
API_KEY = os.getenv('RAZORPAY_API_KEY')
API_SECRET = os.getenv('RAZORPAY_API_SECRET')

if not API_KEY or not API_SECRET:
    raise ValueError("⚠️ RAZORPAY_API_KEY and RAZORPAY_API_SECRET must be set in .env file")

# Gmail configuration for sending receipts - Load from environment variables
GMAIL_ADDRESS = os.getenv('GMAIL_ADDRESS')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')

if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
    print("⚠️ WARNING: Gmail credentials not set. Email functionality will not work.")

# Admin credentials - Load from environment variables
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'changeme')

if ADMIN_PASSWORD == 'changeme':
    print("⚠️ WARNING: Please change the default admin password in .env file!")

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(API_KEY, API_SECRET))

db.init_app(app)

# Create database tables if they don't exist
with app.app_context():
    try:
        db.create_all()
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"⚠️ WARNING: Database table creation failed (likely due to read-only filesystem on serverless): {e}")

# Pricing for package components (in INR)
PRICING = {
    'hotel': {
        'basic': 2000,      # per day per person
        'standard': 5000,   # per day per person
        'premium': 10000    # per day per person
    },
    'food': 3000,  # per day per person (Premium only - fixed)
    'travel': {
        'self': 0,
        'train': 15000,  # per person (Delhi to Dwarka)
        'flight': 50000  # per person (Delhi to Dwarka)
    }
}

# Authentication decorator
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please login to access admin panel.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# @app.before_request
# def create_tables():
#     try:
#         db.create_all()
#     except:
#         pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/catalog')
def catalog():
    """Display Yatra memories catalog page"""
    return render_template('catalog.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Get all passenger personal data (no package selection yet)
            passenger_names = request.form.getlist('passenger_name[]')
            passenger_emails = request.form.getlist('passenger_email[]')
            passenger_phones = request.form.getlist('passenger_phone[]')
            passenger_alt_phones = request.form.getlist('passenger_alt_phone[]')
            passenger_ages = request.form.getlist('passenger_age[]')
            passenger_genders = request.form.getlist('passenger_gender[]')
            passenger_cities = request.form.getlist('passenger_city[]')
            passenger_districts = request.form.getlist('passenger_district[]')
            passenger_states = request.form.getlist('passenger_state[]')
            passenger_guardians = request.form.getlist('passenger_guardian[]')  # Guardian IDs
            
            travelers_personal = {}
            
            print(f"[DEBUG] Processing {len(passenger_names)} travelers")
            
            # First pass: collect all traveler data without guardian names
            for idx, (name, email, phone, alt_phone, age, gender, city, district, state) in enumerate(zip(
                passenger_names, passenger_emails, passenger_phones, passenger_alt_phones,
                passenger_ages, passenger_genders, passenger_cities, passenger_districts, passenger_states
            )):
                if name and age and gender and email and phone:  # Email and phone are now required
                    # Validate and clean data
                    try:
                        age_int = int(age)
                        if age_int < 0 or age_int > 150:
                            flash(f'Invalid age: {age}', 'error')
                            continue
                    except ValueError:
                        flash(f'Invalid age value: {age}', 'error')
                        continue
                    
                    # Get guardian ID if provided
                    guardian_id = passenger_guardians[idx] if idx < len(passenger_guardians) and passenger_guardians[idx] else None
                    
                    # Validate phones are different
                    if alt_phone and phone.strip() == alt_phone.strip():
                        flash(f'Alternate phone cannot be same as primary phone for {name}', 'error')
                        return redirect(url_for('register'))
                    
                    travelers_personal[str(idx)] = {
                        'name': name.strip(),
                        'original_name': name.strip(),  # Store original name
                        'email': email.strip(),
                        'phone': phone.strip(),
                        'alternative_phone': alt_phone.strip() if alt_phone else None,
                        'age': age_int,
                        'gender': gender,
                        'city': city.strip() if city else None,
                        'district': district.strip() if district else None,
                        'state': state.strip() if state else None,
                        'guardian_id': guardian_id,
                        'guardian_name': None  # Will be filled in second pass
                    }
                    print(f"[DEBUG] Added Traveler: {name}, Age: {age_int}, Guardian ID: {guardian_id}")
            
            if len(travelers_personal) == 0:
                flash('Please add at least one traveler with valid details.', 'error')
                return redirect(url_for('register'))
            
            # Second pass: append guardian names to children's names
            for idx, traveler in travelers_personal.items():
                if traveler['age'] <= 10 and traveler['guardian_id']:
                    # Find guardian by ID
                    for g_idx, guardian in travelers_personal.items():
                        # Guardian ID is stored as data-passenger-id from the form
                        # We need to match it with the index
                        if traveler['guardian_id'] == str(int(g_idx) + 1):  # Guardian ID is 1-indexed in form
                            traveler['guardian_name'] = guardian['original_name']
                            # Update display name to include guardian
                            traveler['name'] = f"{traveler['original_name']} ({guardian['original_name']})"
                            print(f"[DEBUG] Child {traveler['original_name']} linked to guardian {guardian['original_name']}")
                            break
            
            # Store travelers personal data in session
            session['travelers_personal'] = travelers_personal
            
            print(f"[SUCCESS] ✅ {len(travelers_personal)} travelers' personal data stored in session")
            
            # Redirect to package selection page
            return redirect(url_for('package_selection'))
            
        except Exception as e:
            print(f"[ERROR] ❌ Registration failed: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'Registration failed: {str(e)}', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/package-selection', methods=['GET', 'POST'])
def package_selection():
    # Check if we have travelers' personal data
    travelers_personal = session.get('travelers_personal')
    if not travelers_personal:
        flash('No traveler data found. Please start from registration.', 'error')
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        try:
            from datetime import datetime
            
            # Collect package component selections for each traveler
            travelers_data = []
            total_amount = 0
            
            # First pass: collect package selections for adults (>10 years)
            guardian_packages = {}  # Store guardian packages by traveler index
            
            for idx in travelers_personal.keys():
                traveler_age = travelers_personal[idx]['age']
                
                # Only process adults in first pass
                if traveler_age > 10:
                    # Get form data for this traveler
                    start_date_str = request.form.get(f'start_date_{idx}')
                    end_date_str = request.form.get(f'end_date_{idx}')
                    hotel = request.form.get(f'hotel_{idx}', 'basic')
                    travel = request.form.get(f'travel_{idx}', 'self')
                    has_otm = request.form.get(f'otm_{idx}') == 'yes'
                    otm_id = request.form.get(f'otm_id_{idx}', '').strip() if has_otm else None
                    
                    # Store for potential children
                    guardian_packages[idx] = {
                        'start_date_str': start_date_str,
                        'end_date_str': end_date_str,
                        'hotel': hotel,
                        'travel': travel,
                        'has_otm': has_otm,
                        'otm_id': otm_id
                    }
            
            # Second pass: process all travelers (copy guardian data to children)
            for idx in travelers_personal.keys():
                traveler_age = travelers_personal[idx]['age']
                guardian_id = travelers_personal[idx].get('guardian_id')
                
                # Check if this is a child who needs guardian's package
                if traveler_age <= 10 and guardian_id:
                    # Find guardian's package data
                    guardian_idx = None
                    for g_idx in travelers_personal.keys():
                        if guardian_id == str(int(g_idx) + 1):  # Guardian ID is 1-indexed
                            guardian_idx = g_idx
                            break
                    
                    if guardian_idx and guardian_idx in guardian_packages:
                        # Copy guardian's package selections
                        pkg = guardian_packages[guardian_idx]
                        start_date_str = pkg['start_date_str']
                        end_date_str = pkg['end_date_str']
                        hotel = pkg['hotel']
                        travel = pkg['travel']
                        has_otm = pkg['has_otm']
                        otm_id = pkg['otm_id']
                        print(f"[DEBUG] Child {travelers_personal[idx]['name']} inheriting package from guardian")
                    else:
                        # Fallback: use default values if guardian not found
                        start_date_str = '2026-01-31'
                        end_date_str = '2026-02-05'
                        hotel = 'basic'
                        travel = 'self'
                        has_otm = False
                        otm_id = None
                        print(f"[WARNING] Guardian package not found for child {travelers_personal[idx]['name']}, using defaults")
                else:
                    # Adult: get from form
                    start_date_str = request.form.get(f'start_date_{idx}')
                    end_date_str = request.form.get(f'end_date_{idx}')
                    hotel = request.form.get(f'hotel_{idx}', 'basic')
                    travel = request.form.get(f'travel_{idx}', 'self')
                    has_otm = request.form.get(f'otm_{idx}') == 'yes'
                    otm_id = request.form.get(f'otm_id_{idx}', '').strip() if has_otm else None
                    
                    # Debug: Show what we received from the form
                    print(f"[DEBUG FORM] Traveler {idx}: has_otm={has_otm}, otm_id='{otm_id}', hotel={hotel}, travel={travel}")
                
                # Parse and validate dates
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                    
                    if end_date < start_date:
                        flash(f'Invalid date range for {travelers_personal[idx]["name"]}', 'error')
                        return redirect(url_for('package_selection'))
                    
                    num_days = (end_date - start_date).days + 1  # Include both start and end day
                    
                except ValueError:
                    flash(f'Invalid date format for {travelers_personal[idx]["name"]}', 'error')
                    return redirect(url_for('package_selection'))
                
                
                # Calculate costs with age-based discounts
                # Get traveler age
                traveler_age = travelers_personal[idx]['age']
                
                # Check for Youth OTM Special Package (OTM ID contains "YOUTH")
                is_youth_otm = False
                if has_otm and otm_id:
                    # Check if OTM ID contains "YOUTH" (case-insensitive)
                    is_youth_otm = 'YOUTH' in otm_id.upper()
                    print(f"[DEBUG] OTM ID: {otm_id}, Uppercase: {otm_id.upper()}, is_youth_otm: {is_youth_otm}")
                
                if is_youth_otm:
                    # Youth OTM Special Logic: Fixed Price ₹5000 with Basic Hotel + Train
                    # Override user selections to enforce package standardization
                    hotel = 'basic'
                    travel = 'train'
                    
                    final_amount = 5000
                    discount_note = "Youth OTM Package: ₹5000 Fixed (Basic Hotel). Train charges applicable later."
                    
                else:
                    # Standard Pricing Logic (for non-youth OTMs and non-OTM users)
                    base_hotel_cost = PRICING['hotel'].get(hotel, PRICING['hotel']['basic']) * num_days
                    base_food_cost = PRICING['food'] * num_days
                    # Travel cost is NOT included in payment (Pay Later model)
                    travel_cost = 0
                    
                    # Apply age-based discounts for hotel and food
                    if traveler_age <= 5:
                        # Children 5 and under: FREE hotel and food
                        hotel_cost = 0
                        food_cost = 0
                        discount_note = "Child (≤5 years): Free hotel & food"
                    elif 6 <= traveler_age <= 10:
                        # Children 6-10: 50% discount on hotel and food
                        hotel_cost = base_hotel_cost * 0.5
                        food_cost = base_food_cost * 0.5
                        discount_note = "Child (6-10 years): 50% off hotel & food"
                    else:
                        # Adults: Full price
                        hotel_cost = base_hotel_cost
                        food_cost = base_food_cost
                        discount_note = None
                    
                    subtotal = hotel_cost + food_cost + travel_cost
                    final_amount = subtotal

                
                total_amount += final_amount
                
                print(f"[DEBUG] Traveler {idx} ({travelers_personal[idx]['name']}, Age: {traveler_age}): "
                      f"{num_days} days, {hotel} hotel, {travel} travel, "
                      f"Total: ₹{final_amount}" + (f" ({discount_note})" if discount_note else ""))

                
                # Combine personal data with package selections
                traveler_full_data = {
                    **travelers_personal[idx],  # Spread personal data
                    'journey_start_date': start_date_str,
                    'journey_end_date': end_date_str,
                    'num_days': num_days,
                    'hotel_category': hotel,
                    'travel_medium': travel,
                    'has_otm': has_otm,
                    'otm_id': otm_id,
                    'is_youth_otm': is_youth_otm,  # Store youth OTM flag
                    'amount': final_amount,
                    'discount_note': discount_note,  # Add discount information
                    # Package for legacy compatibility
                    'package': f'{hotel.capitalize()} Hotel'
                }
                
                travelers_data.append(traveler_full_data)

            
            # Store combined data in session for payment
            session['travelers_data'] = travelers_data
            session['total_amount'] = total_amount
            
            print(f"[SUCCESS] ✅ Package selections stored, total: ₹{total_amount}")
            
            # Redirect to registration summary page
            return redirect(url_for('registration_summary'))
            
        except Exception as e:
            print(f"[ERROR] ❌ Package selection failed: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'Package selection failed: {str(e)}', 'error')
            return redirect(url_for('package_selection'))
    
    # GET request - show package selection form
    # Sort travelers: Adults first, then children
    sorted_travelers = {}
    
    # First, add all adults (age > 10)
    for idx, traveler in travelers_personal.items():
        if traveler['age'] > 10:
            sorted_travelers[idx] = traveler
    
    # Then, add all children (age <= 10)
    for idx, traveler in travelers_personal.items():
        if traveler['age'] <= 10:
            sorted_travelers[idx] = traveler
    
    return render_template('package_selection.html', travelers=sorted_travelers, pricing=PRICING)

@app.route('/verify-otm', methods=['POST'])
def verify_otm():
    """Verify if an OTM ID exists in the active table"""
    try:
        data = request.get_json()
        otm_id = data.get('otm_id', '').strip()
        
        if not otm_id:
            return jsonify({'valid': False, 'message': 'Please enter an OTM ID'})
        
        # Check if OTM ID exists in active table
        otm_record = OTMActive.query.filter_by(id=otm_id).first()
        
        if otm_record:
            # Check if OTM ID contains "YOUTH" (case-insensitive)
            is_youth_otm = 'youth' in otm_id.lower()
            print(f"[DEBUG VERIFY] OTM ID: {otm_id}, Lowercase: {otm_id.lower()}, is_youth_otm: {is_youth_otm}")
            
            return jsonify({
                'valid': True, 
                'message': f'OTM ID verified successfully! ✓',
                'otm_id': otm_id,
                'otm_type': otm_record.otm_type, # Return type for backward compatibility
                'is_youth_otm': is_youth_otm  # Youth OTM flag for ₹5000 fixed pricing
            })
        else:
            return jsonify({
                'valid': False, 
                'message': 'Invalid OTM ID. Please check and try again.'
            })
            
    except Exception as e:
        print(f"[ERROR] ❌ OTM verification failed: {str(e)}")
        return jsonify({'valid': False, 'message': 'Verification failed. Please try again.'})


@app.route('/registration-summary')
def registration_summary():
    """Display registration summary before payment"""
    travelers_data = session.get('travelers_data')
    total_amount = session.get('total_amount')
    
    if not travelers_data or not total_amount:
        flash('No booking data found. Please start from registration.', 'error')
        return redirect(url_for('register'))
    
    # Sort travelers: Adults first, then children
    sorted_travelers = sorted(travelers_data, key=lambda x: (x['age'] <= 10, x.get('name', '')))
    
    return render_template('registration_summary.html', 
                         travelers=sorted_travelers, 
                         total_amount=total_amount)

@app.route('/confirm-and-pay', methods=['POST'])
def confirm_and_pay():
    """Confirm registration summary and proceed to payment"""
    travelers_data = session.get('travelers_data')
    total_amount = session.get('total_amount')
    
    if not travelers_data or not total_amount:
        flash('No booking data found. Please start from registration.', 'error')
        return redirect(url_for('register'))
    
    # Save registrations with "Pending" status before payment
    try:
        from datetime import datetime
        import uuid
        
        # Generate unique order IDs and save with Pending status
        pending_order_ids = []
        
        for traveler in travelers_data:
            # Parse dates if they exist
            journey_start = None
            journey_end = None
            if traveler.get('journey_start_date'):
                journey_start = datetime.strptime(traveler['journey_start_date'], '%Y-%m-%d').date()
            if traveler.get('journey_end_date'):
                journey_end = datetime.strptime(traveler['journey_end_date'], '%Y-%m-%d').date()
            
            # Determine which table to use based on OTM status
            has_otm = traveler.get('has_otm', False)
            
            # Generate a unique order ID with prefix to prevent clashes between tables
            # INS_ = Insider (has OTM), OUT_ = Outsider (no OTM)
            prefix = "INS_PENDING" if has_otm else "OUT_PENDING"
            pending_order_id = f"{prefix}_{uuid.uuid4().hex[:12].upper()}"
            pending_order_ids.append(pending_order_id)
            
            if has_otm:
                # Create in PassengerInsider table with Pending status
                passenger = PassengerInsider(
                    name=traveler['name'],
                    email=traveler['email'],
                    phone=traveler['phone'],
                    alternative_phone=traveler.get('alternative_phone'),
                    age=traveler['age'],
                    gender=traveler['gender'],
                    city=traveler.get('city'),
                    district=traveler.get('district'),
                    state=traveler.get('state'),
                    
                    # Package component fields
                    journey_start_date=journey_start,
                    journey_end_date=journey_end,
                    num_days=traveler.get('num_days'),
                    hotel_category=traveler.get('hotel_category'),
                    travel_medium=traveler.get('travel_medium'),
                    has_otm=True,
                    otm_id=traveler.get('otm_id'),

                    yatra_class=traveler.get('package', 'N/A'),
                    razorpay_order_id=pending_order_id,
                    razorpay_payment_id=None,
                    amount=traveler['amount'],
                    payment_status='Pending'
                )
            else:
                # Create in PassengerOutsider table with Pending status
                passenger = PassengerOutsider(
                    name=traveler['name'],
                    email=traveler['email'],
                    phone=traveler['phone'],
                    alternative_phone=traveler.get('alternative_phone'),
                    age=traveler['age'],
                    gender=traveler['gender'],
                    city=traveler.get('city'),
                    district=traveler.get('district'),
                    state=traveler.get('state'),
                    
                    # Package component fields
                    journey_start_date=journey_start,
                    journey_end_date=journey_end,
                    num_days=traveler.get('num_days'),
                    hotel_category=traveler.get('hotel_category'),
                    travel_medium=traveler.get('travel_medium'),
                    has_otm=False,
                    otm_id=None,

                    yatra_class=traveler.get('package', 'N/A'),
                    razorpay_order_id=pending_order_id,
                    razorpay_payment_id=None,
                    amount=traveler['amount'],
                    payment_status='Pending'
                )
            
            db.session.add(passenger)
        
        # Commit all pending registrations
        db.session.commit()
        
        # Store pending order IDs in session for later update
        session['pending_order_ids'] = pending_order_ids
        
        print(f"[INFO] 📝 Saved {len(pending_order_ids)} pending registrations to database")
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] ❌ Failed to save pending registrations: {str(e)}")
        # Continue to payment even if pending save fails (not critical)
    
    # User confirmed, proceed to payment
    return redirect(url_for('create_payment'))

@app.route('/payment')
def create_payment():
    """Create Razorpay order and show payment page"""
    travelers_data = session.get('travelers_data')
    total_amount = session.get('total_amount')
    
    if not travelers_data or not total_amount:
        flash('No booking data found. Please start from registration.', 'error')
        return redirect(url_for('register'))
    
    try:
        # Create Razorpay order with retry logic
        order_data = {
            'amount': int(total_amount * 100),  # Amount in paise
            'currency': 'INR',
            'payment_capture': 1  # Auto capture payment
        }
        
        # Retry logic for API connection issues
        max_retries = 3
        retry_delay = 1  # seconds
        razorpay_order = None
        last_error = None
        
        for attempt in range(max_retries):
            try:
                print(f"[INFO] Attempting to create Razorpay order (attempt {attempt + 1}/{max_retries})...")
                razorpay_order = razorpay_client.order.create(data=order_data)
                break  # Success, exit retry loop
            except Exception as retry_error:
                last_error = retry_error
                print(f"[WARNING] ⚠️ Razorpay API attempt {attempt + 1} failed: {str(retry_error)}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
        
        if not razorpay_order:
            # All retries failed
            error_msg = str(last_error) if last_error else "Unknown error"
            print(f"[ERROR] ❌ All Razorpay API attempts failed: {error_msg}")
            
            # Check if it's a connection error
            if 'Connection' in error_msg or 'Remote' in error_msg:
                flash('Unable to connect to payment gateway. Please check your internet connection and try again.', 'error')
            else:
                flash(f'Payment initialization failed: {error_msg}. Please try again.', 'error')
            
            return redirect(url_for('registration_summary'))
        
        order_id = razorpay_order['id']
        
        # Generate unique order IDs for each passenger (but don't save to DB yet)
        # Data will be saved only after successful payment verification
        passenger_order_ids = []
        for traveler in travelers_data:
            # Generate unique order ID for this passenger
            passenger_order_id = f"{uuid.uuid4().hex[:12].upper()}"
            passenger_order_ids.append(passenger_order_id)
            print(f"[DEBUG] Generated order ID for {traveler['name']}: {passenger_order_id}")
        
        # Store order IDs in session for later use
        session['razorpay_order_id'] = order_id
        session['passenger_order_ids'] = passenger_order_ids
        
        print(f"[SUCCESS] ✅ Razorpay order created: {order_id}")
        print(f"[INFO] 📋 {len(passenger_order_ids)} passengers ready (will be saved after payment verification)")
        
        # Sort travelers: Adults first, then children
        sorted_travelers = sorted(travelers_data, key=lambda x: (x['age'] <= 10, x.get('name', '')))
        
        return render_template('payment.html', 
                             travelers=sorted_travelers,
                             total_amount=total_amount,
                             razorpay_key=API_KEY,
                             order_id=order_id,
                             session_order_ids=','.join(passenger_order_ids))
    
    except Exception as e:
        print(f"[ERROR] ❌ Payment creation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Payment initialization failed: {str(e)}', 'error')
        return redirect(url_for('register'))

@app.route('/verify-payment', methods=['POST'])
def verify_payment():
    """Verify Razorpay payment and update database"""
    try:
        data = request.get_json()
        
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')
        session_order_ids = data.get('session_order_ids')
        
        # Verify signature
        generated_signature = hmac.new(
            API_SECRET.encode(),
            f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        if generated_signature != razorpay_signature:
            print(f"[ERROR] ❌ Payment signature verification failed")
            return jsonify({'success': False, 'error': 'Invalid signature'})
        
        # Get travelers data from session
        travelers_data = session.get('travelers_data')
        pending_order_ids = session.get('pending_order_ids', [])
        
        if not travelers_data:
            print(f"[ERROR] ❌ No travelers data found in session")
            return jsonify({'success': False, 'error': 'Session data not found'})
        
        # Update pending passengers to Paid status
        passenger_ids = session_order_ids.split(',')
        all_passengers = []
        
        from datetime import datetime
        
        # If we have pending order IDs, update those records
        if pending_order_ids and len(pending_order_ids) == len(passenger_ids):
            for pending_order_id, new_order_id in zip(pending_order_ids, passenger_ids):
                # Try to find and update the pending record
                pending_passenger = PassengerInsider.query.filter_by(
                    razorpay_order_id=pending_order_id,
                    payment_status='Pending'
                ).first()
                
                if not pending_passenger:
                    pending_passenger = PassengerOutsider.query.filter_by(
                        razorpay_order_id=pending_order_id,
                        payment_status='Pending'
                    ).first()
                
                if pending_passenger:
                    # Update the pending record
                    pending_passenger.razorpay_order_id = new_order_id
                    pending_passenger.razorpay_payment_id = razorpay_payment_id
                    pending_passenger.payment_status = 'Paid'
                    all_passengers.append(pending_passenger)
                    print(f"[SUCCESS] ✅ Updated {pending_passenger.name} from Pending to Paid")
                else:
                    print(f"[WARNING] ⚠️ Pending record not found for {pending_order_id}, will create new record")
        
        # If we couldn't update pending records, create new ones (fallback)
        if len(all_passengers) != len(travelers_data):
            print(f"[INFO] 📝 Some pending records not found, creating new records as fallback")
            all_passengers = []  # Clear and recreate
            
            for idx, (traveler, passenger_order_id) in enumerate(zip(travelers_data, passenger_ids)):
                # Parse dates if they exist
                journey_start = None
                journey_end = None
                if traveler.get('journey_start_date'):
                    journey_start = datetime.strptime(traveler['journey_start_date'], '%Y-%m-%d').date()
                if traveler.get('journey_end_date'):
                    journey_end = datetime.strptime(traveler['journey_end_date'], '%Y-%m-%d').date()
                
                # Determine which table to use based on OTM status
                has_otm = traveler.get('has_otm', False)
                
                if has_otm:
                    # Create in PassengerInsider table
                    passenger = PassengerInsider(
                        name=traveler['name'],
                        email=traveler['email'],
                        phone=traveler['phone'],
                        alternative_phone=traveler.get('alternative_phone'),
                        age=traveler['age'],
                        gender=traveler['gender'],
                        city=traveler.get('city'),
                        district=traveler.get('district'),
                        state=traveler.get('state'),
                        
                        # Package component fields
                        journey_start_date=journey_start,
                        journey_end_date=journey_end,
                        num_days=traveler.get('num_days'),
                        hotel_category=traveler.get('hotel_category'),
                        travel_medium=traveler.get('travel_medium'),
                        has_otm=True,
                        otm_id=traveler.get('otm_id'),

                        yatra_class=traveler.get('package', 'N/A'),
                        razorpay_order_id=passenger_order_id,
                        razorpay_payment_id=razorpay_payment_id,
                        amount=traveler['amount'],
                        payment_status='Paid'  # Direct to Paid status
                    )
                    print(f"[SUCCESS] ✅ Created PassengerInsider: {traveler['name']} with OTM: {traveler.get('otm_id')}")
                else:
                    # Create in PassengerOutsider table
                    passenger = PassengerOutsider(
                        name=traveler['name'],
                        email=traveler['email'],
                        phone=traveler['phone'],
                        alternative_phone=traveler.get('alternative_phone'),
                        age=traveler['age'],
                        gender=traveler['gender'],
                        city=traveler.get('city'),
                        district=traveler.get('district'),
                        state=traveler.get('state'),
                        
                        # Package component fields
                        journey_start_date=journey_start,
                        journey_end_date=journey_end,
                        num_days=traveler.get('num_days'),
                        hotel_category=traveler.get('hotel_category'),
                        travel_medium=traveler.get('travel_medium'),
                        has_otm=False,
                        otm_id=None,

                        yatra_class=traveler.get('package', 'N/A'),
                        razorpay_order_id=passenger_order_id,
                        razorpay_payment_id=razorpay_payment_id,
                        amount=traveler['amount'],
                        payment_status='Paid'  # Direct to Paid status
                    )
                    print(f"[SUCCESS] ✅ Created PassengerOutsider: {traveler['name']} (No OTM)")
                
                db.session.add(passenger)
                all_passengers.append(passenger)
            
                # Handle OTM ID transfer from active to expired (for all passengers)
            for passenger in all_passengers:
                if isinstance(passenger, PassengerInsider) and passenger.has_otm and passenger.otm_id:
                    # Check if OTM ID exists in active table
                    otm_active = OTMActive.query.filter_by(id=passenger.otm_id).first()
                    if otm_active:
                        # We need to flush to get the passenger ID for the OTM expired record
                        db.session.flush()
                        
                        # Create expired record
                        otm_expired = OTMExpired(
                            id=passenger.otm_id,
                            used_by_passenger_id=passenger.id,
                            otm_type=otm_active.otm_type # Preserve type
                        )
                        # Remove from active table
                        db.session.delete(otm_active)
                        # Add to expired table
                        db.session.add(otm_expired)
                        print(f"[SUCCESS] ✅ Moved OTM ID {passenger.otm_id} from active to expired (Type: {otm_active.otm_type})")
        
        try:
            db.session.commit()
            
            # Send email receipt asynchronously (don't block the response)
            def send_emails_async():
                with app.app_context():  # Add Flask context for background thread
                    try:
                        if all_passengers:
                            # Calculate total amount
                            total_amount = sum(p.amount for p in all_passengers)
                            
                            # Collect unique email addresses from all passengers
                            unique_emails = set()
                            for passenger in all_passengers:
                                if passenger.email and passenger.email.strip():
                                    unique_emails.add(passenger.email.strip().lower())
                            
                            if unique_emails:
                                emails_sent = 0
                                
                                # Send individual email to each unique email address
                                for recipient_email in unique_emails:
                                    try:
                                        # Generate fresh PDF for each recipient
                                        pdf_buffer = generate_receipt_pdf(all_passengers, total_amount)
                                        
                                        send_receipt_email(
                                            to_email=recipient_email,
                                            pdf_buffer=pdf_buffer,
                                            passengers=all_passengers,
                                            total_amount=total_amount,
                                            gmail_address=GMAIL_ADDRESS,
                                            gmail_app_password=GMAIL_APP_PASSWORD
                                        )
                                        emails_sent += 1
                                    except Exception as individual_email_error:
                                        print(f"[ERROR] ❌ Failed to send email to {recipient_email}: {str(individual_email_error)}")
                                
                                print(f"[INFO] 📧 Sent {emails_sent} individual receipt email(s) to unique travelers")
                            else:
                                print(f"[WARNING] ⚠️ No email addresses found for travelers, skipping email")
                    except Exception as email_error:
                        # Don't fail the payment if email fails
                        print(f"[ERROR] ❌ Email sending failed but payment successful: {str(email_error)}")
                        import traceback
                        traceback.print_exc()
            
            # Start email sending in background thread
            import threading
            email_thread = threading.Thread(target=send_emails_async)
            email_thread.daemon = True
            email_thread.start()
            print("[INFO] 📧 Email sending started in background thread")
            
            
            
            # Clear session data
            session.pop('travelers_data', None)
            session.pop('total_amount', None)
            session.pop('razorpay_order_id', None)
            session.pop('passenger_order_ids', None)
            
            print(f"[SUCCESS] ✅ Payment verified and database updated")
            
            return jsonify({
                'success': True, 
                'redirect_url': url_for('receipt', order_ids=session_order_ids)
            })
            
        except Exception as db_error:
            db.session.rollback()
            print(f"[CRITICAL ERROR] ❌ Payment received but Database Insert Failed: {str(db_error)}")
            
            # EMERGENCY BACKUP: Save orphaned booking to file
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
                    
                print(f"[SAFETY NET] ✅ Orphaned booking saved to {backup_file}")
                
            except Exception as backup_error:
                print(f"[FATAL] ❌ Could not save backup file: {str(backup_error)}")
            
            # Return verification success (because they paid!) but with a warning redirect or message
            # Ideally we might want a special 'success_with_error' page, but for now we return error to API
            # so the frontend stays on the page, but provides a specific message.
            return jsonify({
                'success': False, 
                'error': f'Payment successful (ID: {razorpay_payment_id}) but ticket generation failed. Your booking data is safe. Please contact admin.'
            })

    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] ❌ Payment verification failed: {error_msg}")
        import traceback
        traceback.print_exc()
        
        # Ensure we return valid JSON even if there's an encoding issue
        try:
            return jsonify({'success': False, 'error': error_msg}), 500
        except:
            return {'success': False, 'error': 'Internal server error'}, 500



@app.route('/receipt/<order_ids>')
def receipt(order_ids):
    # Get all passengers by their order IDs from both tables
    order_list = order_ids.split(',')
    insiders = PassengerInsider.query.filter(PassengerInsider.razorpay_order_id.in_(order_list)).all()
    outsiders = PassengerOutsider.query.filter(PassengerOutsider.razorpay_order_id.in_(order_list)).all()
    passengers = insiders + outsiders
    
    if not passengers:
        flash('Receipt not found', 'error')
        return redirect(url_for('index'))
    
    # Sort passengers: Adults first, then children
    sorted_passengers = sorted(passengers, key=lambda x: (x.age <= 10, x.name))
    
    # Calculate total amount
    total_amount = sum(p.amount for p in passengers)
    
    return render_template('receipt.html', passengers=sorted_passengers, total_amount=total_amount, order_ids=order_ids)

@app.route('/download-receipt/<order_ids>')
def download_receipt(order_ids):
    """Generate and download PDF receipt"""
    try:
        # Get all passengers by their order IDs from both tables
        order_list = order_ids.split(',')
        insiders = PassengerInsider.query.filter(PassengerInsider.razorpay_order_id.in_(order_list)).all()
        outsiders = PassengerOutsider.query.filter(PassengerOutsider.razorpay_order_id.in_(order_list)).all()
        passengers = insiders + outsiders
        
        if not passengers:
            flash('Receipt not found', 'error')
            return redirect(url_for('index'))
        
        # Sort passengers: Adults first, then children
        sorted_passengers = sorted(passengers, key=lambda x: (x.age <= 10, x.name))
        
        # Calculate total amount
        total_amount = sum(p.amount for p in passengers)
        
        # Generate PDF receipt
        pdf_buffer = generate_receipt_pdf(sorted_passengers, total_amount)
        
        # Send file as download
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name='Dwarka_Yatra_Receipt.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"[ERROR] ❌ PDF download failed: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('Failed to generate receipt PDF', 'error')
        return redirect(url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Successfully logged in as admin!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """Logout admin"""
    session.pop('admin_logged_in', None)
    flash('Successfully logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard showing all database tables"""
    table_type = request.args.get('table', 'all_passengers')
    
    headers = []
    records = []
    
    if table_type == 'passenger_insider':
        headers = ['Order ID', 'Name', 'Email', 'Phone', 'Alt Phone', 'Location', 'Age/Gen', 'OTM ID', 'Package Details', 'Amount', 'Status', 'Date']
        items = PassengerInsider.query.order_by(PassengerInsider.created_at.desc()).all()
        for item in items:
            loc = f"{item.city or '-'}, {item.district or '-'}, {item.state or '-'}"
            pkg = f"{item.hotel_category or '-'} | {item.travel_medium or '-'}"
            records.append({
                'id': item.razorpay_order_id,
                'cols': [
                    item.razorpay_order_id,
                    item.name, 
                    item.email, 
                    item.phone,
                    item.alternative_phone or '-',
                    loc,
                    f"{item.age}/{item.gender}",
                    item.otm_id, 
                    pkg, 
                    f"₹{item.amount}", 
                    item.payment_status, 
                    item.created_at.strftime('%Y-%m-%d %H:%M') if item.created_at else '-'
                ]
            })
            
    elif table_type == 'passenger_outsider':
        headers = ['Order ID', 'Name', 'Email', 'Phone', 'Alt Phone', 'Location', 'Age/Gen', 'Package Details', 'Amount', 'Status', 'Date']
        items = PassengerOutsider.query.order_by(PassengerOutsider.created_at.desc()).all()
        for item in items:
            loc = f"{item.city or '-'}, {item.district or '-'}, {item.state or '-'}"
            pkg = f"{item.hotel_category or '-'} | {item.travel_medium or '-'}"
            records.append({
                'id': item.razorpay_order_id,
                'cols': [
                    item.razorpay_order_id,
                    item.name, 
                    item.email, 
                    item.phone, 
                    item.alternative_phone or '-',
                    loc,
                    f"{item.age}/{item.gender}",
                    pkg, 
                    f"₹{item.amount}", 
                    item.payment_status, 
                    item.created_at.strftime('%Y-%m-%d %H:%M') if item.created_at else '-'
                ]
            })
            
    elif table_type == 'otm_active':
        headers = ['OTM ID', 'Created At']
        items = OTMActive.query.order_by(OTMActive.created_at.desc()).all()
        for item in items:
            records.append({
                'id': item.id,
                'cols': [item.id, item.created_at.strftime('%Y-%m-%d %H:%M') if item.created_at else '-']
            })
            
    elif table_type == 'otm_expired':
        headers = ['OTM ID', 'Used By Passenger ID', 'Expired At']
        items = OTMExpired.query.order_by(OTMExpired.expired_at.desc()).all()
        for item in items:
            records.append({
                'id': item.id,
                'cols': [item.id, item.used_by_passenger_id, item.expired_at.strftime('%Y-%m-%d %H:%M') if item.expired_at else '-']
            })
    
    elif table_type == 'transactions':
        headers = ['Passenger Name', 'Order ID', 'Payment ID', 'Amount', 'Payment Status', 'Created Date']
        # Get all passengers from both tables
        insiders = PassengerInsider.query.order_by(PassengerInsider.created_at.desc()).all()
        outsiders = PassengerOutsider.query.order_by(PassengerOutsider.created_at.desc()).all()
        
        # Combine transactions
        all_transactions = []
        for p in insiders:
            all_transactions.append({
                'obj': p,
                'sort_date': p.created_at
            })
        for p in outsiders:
            all_transactions.append({
                'obj': p,
                'sort_date': p.created_at
            })
        
        # Sort by date descending (handle None dates safely)
        all_transactions.sort(key=lambda x: x['sort_date'] or datetime.min, reverse=True)
        
        for item in all_transactions:
            p = item['obj']
            records.append({
                'id': p.razorpay_order_id,
                'cols': [
                    p.name,
                    p.razorpay_order_id or 'N/A',
                    p.razorpay_payment_id or 'N/A',
                    f"₹{p.amount}",
                    p.payment_status,
                    p.created_at.strftime('%Y-%m-%d %H:%M') if p.created_at else '-'
                ]
            })
            
    else: # all_passengers
        headers = ['Order ID', 'Type', 'Name', 'Email', 'Phone', 'Alt Phone', 'Location', 'Age/Gen', 'Pkg/Amt', 'Status', 'Date']
        insiders = PassengerInsider.query.all()
        outsiders = PassengerOutsider.query.all()
        
        # Combine and sort
        all_items = []
        for p in insiders:
            all_items.append({
                'obj': p,
                'type': 'Insider',
                'sort_date': p.created_at
            })
        for p in outsiders:
            all_items.append({
                'obj': p,
                'type': 'Outsider',
                'sort_date': p.created_at
            })
            
        all_items.sort(key=lambda x: x['sort_date'] or datetime.min, reverse=True)
        
        for item in all_items:
            p = item['obj']
            loc = f"{p.city or '-'}, {p.district or '-'}, {p.state or '-'}"
            pkg_amt = f"{p.hotel_category or '-'} | ₹{p.amount}"
            records.append({
                'id': p.razorpay_order_id,
                'cols': [
                    p.razorpay_order_id,
                    item['type'], 
                    p.name, 
                    p.email, 
                    p.phone,
                    p.alternative_phone or '-',
                    loc,
                    f"{p.age}/{p.gender}",
                    pkg_amt, 
                    p.payment_status, 
                    p.created_at.strftime('%Y-%m-%d %H:%M') if p.created_at else '-'
                ]
            })

    return render_template('admin_dashboard.html', 
                         headers=headers, 
                         records=records, 
                         current_table=table_type)

@app.route('/admin/export/excel')
@login_required
def export_excel():
    """Export data to Excel (admin only)"""
    import pandas as pd
    import io
    
    table_type = request.args.get('table', 'all_passengers')
    data = []
    filename = "export.xlsx"
    
    if table_type == 'passenger_insider':
        # Export only insiders
        passengers = PassengerInsider.query.all()
        for p in passengers:
            data.append({
                'ID': p.id,
                'Name': p.name,
                'Email': p.email,
                'Phone': p.phone,
                'Age': p.age,
                'Gender': p.gender,
                'OTM ID': p.otm_id,
                'Package': p.yatra_class,
                'Amount': p.amount,
                'Status': p.payment_status,
                'Created At': p.created_at
            })
        filename = "insider_passengers.xlsx"
        
    elif table_type == 'passenger_outsider':
        # Export only outsiders
        passengers = PassengerOutsider.query.all()
        for p in passengers:
            data.append({
                'ID': p.id,
                'Name': p.name,
                'Email': p.email,
                'Phone': p.phone,
                'Age': p.age,
                'Gender': p.gender,
                'Package': p.yatra_class,
                'Amount': p.amount,
                'Status': p.payment_status,
                'Created At': p.created_at
            })
        filename = "outsider_passengers.xlsx"
        
    elif table_type == 'transactions':
        # Export transactions
        insiders = PassengerInsider.query.all()
        outsiders = PassengerOutsider.query.all()
        for p in insiders + outsiders:
            data.append({
                'Passenger Name': p.name,
                'Order ID': p.razorpay_order_id or 'N/A',
                'Payment ID': p.razorpay_payment_id or 'N/A',
                'Amount': p.amount,
                'Payment Status': p.payment_status,
                'Created Date': p.created_at
            })
        filename = "transactions.xlsx"
        
    elif table_type == 'otm_active':
        # Export active OTM IDs
        otms = OTMActive.query.all()
        for otm in otms:
            data.append({
                'OTM ID': otm.id,
                'Created At': otm.created_at
            })
        filename = "active_otm_ids.xlsx"
        
    elif table_type == 'otm_expired':
        # Export expired OTM IDs
        otms = OTMExpired.query.all()
        for otm in otms:
            data.append({
                'OTM ID': otm.id,
                'Used By Passenger ID': otm.used_by_passenger_id,
                'Expired At': otm.expired_at
            })
        filename = "expired_otm_ids.xlsx"
        
    else:  # all_passengers
        # Export all passengers
        insiders = PassengerInsider.query.all()
        outsiders = PassengerOutsider.query.all()
        
        for passenger in insiders:
            data.append({
                'Type': 'Insider (OTM)',
                'ID': passenger.id,
                'Name': passenger.name,
                'Email': passenger.email,
                'Phone': passenger.phone,
                'Age': passenger.age,
                'Gender': passenger.gender,
                'OTM ID': passenger.otm_id,
                'Package': passenger.yatra_class,
                'Amount': passenger.amount,
                'Status': passenger.payment_status,
                'Created At': passenger.created_at
            })
        
        for passenger in outsiders:
            data.append({
                'Type': 'Outsider',
                'ID': passenger.id,
                'Name': passenger.name,
                'Email': passenger.email,
                'Phone': passenger.phone,
                'Age': passenger.age,
                'Gender': passenger.gender,
                'OTM ID': 'N/A',
                'Package': passenger.yatra_class,
                'Amount': passenger.amount,
                'Status': passenger.payment_status,
                'Created At': passenger.created_at
            })
        filename = "all_passengers.xlsx"
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    output.seek(0)
    
    return send_file(output, download_name=filename, as_attachment=True)

@app.route('/admin/export/csv')
@login_required
def export_csv():
    """Export data to CSV (admin only)"""
    # Get all passengers from both tables
    insiders = PassengerInsider.query.all()
    outsiders = PassengerOutsider.query.all()
    data = []
    
    for passenger in insiders:
        data.append({
            'Passenger Type': 'Insider (OTM)',
            'Passenger ID': passenger.id,
            'Name': passenger.name,
            'Email': passenger.email,
            'Phone': passenger.phone,
            'Alternative Phone': passenger.alternative_phone or '',
            'Age': passenger.age,
            'Gender': passenger.gender,
            'City': passenger.city or '',
            'District': passenger.district or '',
            'State': passenger.state or '',
            'OTM ID': passenger.otm_id,
            'Yatra Class': passenger.yatra_class,
            'Order ID': passenger.razorpay_order_id,
            'Payment ID': passenger.razorpay_payment_id or '',
            'Amount': passenger.amount,
            'Payment Status': passenger.payment_status,
            'Created At': passenger.created_at
        })
    
    for passenger in outsiders:
        data.append({
            'Passenger Type': 'Outsider (No OTM)',
            'Passenger ID': passenger.id,
            'Name': passenger.name,
            'Email': passenger.email,
            'Phone': passenger.phone,
            'Alternative Phone': passenger.alternative_phone or '',
            'Age': passenger.age,
            'Gender': passenger.gender,
            'City': passenger.city or '',
            'District': passenger.district or '',
            'State': passenger.state or '',
            'OTM ID': 'N/A',
            'Yatra Class': passenger.yatra_class,
            'Order ID': passenger.razorpay_order_id,
            'Payment ID': passenger.razorpay_payment_id or '',
            'Amount': passenger.amount,
            'Payment Status': passenger.payment_status,
            'Created At': passenger.created_at
        })
    
    df = pd.DataFrame(data)
    
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=yatra_passengers.csv'}
    )

@app.route('/admin/update-record', methods=['POST'])
@login_required
def admin_update_record():
    """Update a passenger record (admin only)"""
    try:
        record_id = request.form.get('record_id')
        table_name = request.form.get('table_name')
        
        record = None
        
        # Determine which table to update
        if table_name == 'passenger_insider' or table_name == 'all_passengers':
            try:
                record = PassengerInsider.query.filter_by(razorpay_order_id=record_id).first()
            except:
                pass
            
            if not record and table_name == 'all_passengers':
                try:
                    record = PassengerOutsider.query.filter_by(razorpay_order_id=record_id).first()
                except:
                    pass
                    
        elif table_name == 'passenger_outsider':
            try:
                record = PassengerOutsider.query.filter_by(razorpay_order_id=record_id).first()
            except:
                pass
                
        elif table_name == 'transactions':
            try:
                record = PassengerInsider.query.filter_by(razorpay_order_id=record_id).first()
            except:
                pass
            if not record:
                try:
                    record = PassengerOutsider.query.filter_by(razorpay_order_id=record_id).first()
                except:
                    pass
        
        if not record:
            flash('Record not found', 'error')
            return redirect(url_for('admin_dashboard', table=table_name))
        
        # Update fields from form
        for key, value in request.form.items():
            if key not in ['record_id', 'table_name'] and hasattr(record, key.lower().replace(' ', '_')):
                setattr(record, key.lower().replace(' ', '_'), value)
        
        db.session.commit()
        flash('Record updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating record: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard', table=table_name))


@app.route('/admin/delete-record', methods=['POST'])
@login_required
def admin_delete_record():
    """Delete a passenger record (admin only)"""
    try:
        data = request.get_json()
        record_id = data.get('record_id')
        table_name = data.get('table_name')
        
        record = None
        
        # Determine which table to delete from
        if table_name == 'passenger_insider' or table_name == 'all_passengers':
            # Try to find in insider table
            try:
                record = PassengerInsider.query.filter_by(razorpay_order_id=record_id).first()
            except:
                pass
            
            # If not found and it's all_passengers, try outsider
            if not record and table_name == 'all_passengers':
                try:
                    record = PassengerOutsider.query.filter_by(razorpay_order_id=record_id).first()
                except:
                    pass
                    
        elif table_name == 'passenger_outsider':
            try:
                record = PassengerOutsider.query.filter_by(razorpay_order_id=record_id).first()
            except:
                pass
                
        elif table_name == 'transactions':
            # For transactions, try both tables
            try:
                record = PassengerInsider.query.filter_by(razorpay_order_id=record_id).first()
            except:
                pass
            if not record:
                try:
                    record = PassengerOutsider.query.filter_by(razorpay_order_id=record_id).first()
                except:
                    pass
                    
        elif table_name == 'otm_active':
            record = OTMActive.query.get(record_id)  # OTM ID is string
            
        elif table_name == 'otm_expired':
            record = OTMExpired.query.get(record_id)  # OTM ID is string
        
        if not record:
            return jsonify({'success': False, 'message': 'Record not found'})
        
        db.session.delete(record)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Record deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/create-registration', methods=['GET', 'POST'])
@login_required
def admin_create_registration():
    """Admin creates a new registration with custom discount"""
    if request.method == 'POST':
        try:
            from datetime import datetime
            import uuid
            
            # Get form data
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            alternative_phone = request.form.get('alternative_phone')
            age = int(request.form.get('age'))
            gender = request.form.get('gender')
            city = request.form.get('city')
            district = request.form.get('district')
            state = request.form.get('state')
            
            # Package details
            journey_start_date = datetime.strptime(request.form.get('journey_start_date'), '%Y-%m-%d').date()
            journey_end_date = datetime.strptime(request.form.get('journey_end_date'), '%Y-%m-%d').date()
            num_days = (journey_end_date - journey_start_date).days + 1
            hotel_category = request.form.get('hotel_category')
            travel_medium = request.form.get('travel_medium')
            # Auto-generate yatra_class from hotel_category
            yatra_class = f'{hotel_category.capitalize()} Hotel'
            
            # OTM details
            has_otm = request.form.get('has_otm') == 'yes'
            otm_id = request.form.get('otm_id', '').strip() if has_otm else None
            
            # Payment & Discount
            base_amount = float(request.form.get('base_amount'))
            custom_discount = float(request.form.get('custom_discount', 0))
            payment_status = request.form.get('payment_status')
            razorpay_order_id = request.form.get('razorpay_order_id', '').strip() or f"admin_{uuid.uuid4().hex[:12]}"
            razorpay_payment_id = request.form.get('razorpay_payment_id', '').strip() or None
            
            # Calculate final amount with custom discount
            final_amount = base_amount * (1 - custom_discount / 100)
            
            # Determine which table to use
            if has_otm and otm_id:
                # Create PassengerInsider
                passenger = PassengerInsider(
                    name=name,
                    email=email,
                    phone=phone,
                    alternative_phone=alternative_phone,
                    age=age,
                    gender=gender,
                    city=city,
                    district=district,
                    state=state,
                    journey_start_date=journey_start_date,
                    journey_end_date=journey_end_date,
                    num_days=num_days,
                    hotel_category=hotel_category,
                    travel_medium=travel_medium,
                    yatra_class=yatra_class,
                    otm_id=otm_id,
                    amount=final_amount,
                    razorpay_order_id=razorpay_order_id,
                    razorpay_payment_id=razorpay_payment_id,
                    payment_status=payment_status
                )
            else:
                # Create PassengerOutsider
                passenger = PassengerOutsider(
                    name=name,
                    email=email,
                    phone=phone,
                    alternative_phone=alternative_phone,
                    age=age,
                    gender=gender,
                    city=city,
                    district=district,
                    state=state,
                    journey_start_date=journey_start_date,
                    journey_end_date=journey_end_date,
                    num_days=num_days,
                    hotel_category=hotel_category,
                    travel_medium=travel_medium,
                    yatra_class=yatra_class,
                    amount=final_amount,
                    razorpay_order_id=razorpay_order_id,
                    razorpay_payment_id=razorpay_payment_id,
                    payment_status=payment_status
                )
            
            db.session.add(passenger)
            db.session.commit()
            
            flash(f'Registration created successfully for {name}! Final amount: ₹{final_amount:.2f} (Discount: {custom_discount}%)', 'success')
            return redirect(url_for('admin_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating registration: {str(e)}', 'error')
            return redirect(url_for('admin_create_registration'))
    
    return render_template('admin_create_registration.html')

@app.route('/admin/generate-otm-ids', methods=['POST'])
@login_required
def generate_otm_ids():
    """Generate multiple OTM IDs (admin only)"""
    try:
        import random
        import string
        
        quantity = int(request.form.get('quantity', 10))
        prefix = request.form.get('prefix', '').strip()
        
        # Validate quantity
        if quantity < 1 or quantity > 100:
            flash('Please enter a quantity between 1 and 100', 'error')
            return redirect(url_for('admin_dashboard', table='otm_active'))
        
        generated_ids = []
        
        for i in range(quantity):
            # Generate 5-character alphanumeric code (uppercase letters + numbers)
            characters = string.ascii_uppercase + string.digits
            random_code = ''.join(random.choices(characters, k=5))
            
            if prefix:
                otm_id = f"{prefix}{random_code}"  # No underscore
            else:
                otm_id = random_code
            
            # Check if ID already exists
            existing = OTMActive.query.filter_by(id=otm_id).first()
            if not existing:
                # Create new OTM ID
                new_otm = OTMActive(id=otm_id)
                db.session.add(new_otm)
                generated_ids.append(otm_id)
        
        db.session.commit()
        
        flash(f'Successfully generated {len(generated_ids)} OTM IDs!', 'success')
        return redirect(url_for('admin_dashboard', table='otm_active'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error generating OTM IDs: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard', table='otm_active'))

@app.route('/admin/generate-receipt/<record_id>')
@login_required
def admin_generate_receipt(record_id):
    """Generate receipt for a specific passenger (admin only)"""
    try:
        table = request.args.get('table', 'all_passengers')
        
        # Determine which table to query based on the table parameter
        passenger = None
        
        if table == 'passenger_insider':
            passenger = PassengerInsider.query.filter_by(razorpay_order_id=record_id).first()
        elif table == 'passenger_outsider':
            passenger = PassengerOutsider.query.filter_by(razorpay_order_id=record_id).first()
        elif table == 'all_passengers' or table == 'transactions':
            # Try both tables
            passenger = PassengerInsider.query.filter_by(razorpay_order_id=record_id).first()
            if not passenger:
                passenger = PassengerOutsider.query.filter_by(razorpay_order_id=record_id).first()
        
        if not passenger:
            flash('Passenger record not found', 'error')
            return redirect(url_for('admin_dashboard', table=table))
        
        # Get all passengers with the same razorpay_order_id (grouped booking)
        order_id = passenger.razorpay_order_id
        
        # Query both tables for passengers with the same order ID
        insiders = PassengerInsider.query.filter_by(razorpay_order_id=order_id).all()
        outsiders = PassengerOutsider.query.filter_by(razorpay_order_id=order_id).all()
        passengers = insiders + outsiders
        
        if not passengers:
            passengers = [passenger]  # Fallback to single passenger
        
        # Sort passengers: Adults first, then children
        sorted_passengers = sorted(passengers, key=lambda x: (x.age <= 10, x.name))
        
        # Calculate total amount
        total_amount = sum(p.amount for p in passengers)
        
        # Create order_ids string for download link
        order_ids = ','.join([p.razorpay_order_id for p in passengers])
        
        return render_template('receipt.html', 
                             passengers=sorted_passengers, 
                             total_amount=total_amount,
                             order_ids=order_ids)
        
    except Exception as e:
        print(f"[ERROR] ❌ Admin receipt generation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error generating receipt: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard', table=table))


@app.route('/health')
def health_check():
    return jsonify({'status': 'ok', 'message': 'Server is running'})

@app.route('/debug-db')
def debug_db():
    try:
        # verify admin login
        if not session.get('admin_logged_in'):
            return "Unauthorized", 401
            
        # Force create tables
        with app.app_context():
            db.create_all()
            
            # Inspect tables
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
        return jsonify({
            'status': 'success',
            'message': 'Database tables created!',
            'tables': tables,
            'db_uri': app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1] # hide password
        })
    except Exception as e:
        return jsonify({'error': str(e)})

def cleanup_pending_registrations(minutes=30):
    """
    Delete pending registrations older than specified minutes.
    This cleans up abandoned registrations where users didn't complete payment.
    """
    try:
        from datetime import timedelta
        from models import get_india_time
        
        cutoff_time = get_india_time() - timedelta(minutes=minutes)
        
        # Delete old pending insiders
        pending_insiders = PassengerInsider.query.filter(
            PassengerInsider.payment_status == 'Pending',
            PassengerInsider.created_at < cutoff_time
        ).all()
        
        # Delete old pending outsiders
        pending_outsiders = PassengerOutsider.query.filter(
            PassengerOutsider.payment_status == 'Pending',
            PassengerOutsider.created_at < cutoff_time
        ).all()
        
        deleted_count = len(pending_insiders) + len(pending_outsiders)
        
        if deleted_count > 0:
            for passenger in pending_insiders:
                db.session.delete(passenger)
            for passenger in pending_outsiders:
                db.session.delete(passenger)
            
            db.session.commit()
            print(f"[CLEANUP] 🧹 Deleted {deleted_count} pending registrations older than {minutes} minutes")
        else:
            print(f"[CLEANUP] ✓ No pending registrations to clean up")
            
        return deleted_count
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] ❌ Cleanup failed: {str(e)}")
        return 0

@app.route('/admin/cleanup-pending', methods=['POST'])
@login_required
def admin_cleanup_pending():
    """Admin route to manually trigger cleanup of pending registrations"""
    try:
        deleted_count = cleanup_pending_registrations(minutes=30)
        flash(f'Cleanup complete: {deleted_count} pending registrations deleted', 'success')
    except Exception as e:
        flash(f'Cleanup failed: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

# Force update - v2
if __name__ == '__main__':
    with app.app_context():
        # Cleanup old pending registrations on startup
        cleanup_pending_registrations(minutes=30)
    app.run(debug=True)
