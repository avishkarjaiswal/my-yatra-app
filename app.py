from flask import Flask, render_template, request, redirect, url_for, flash, send_file, Response, session, jsonify
from models import db, LoginDetails, YatraDetails, AppSettings, CarouselImage

import os
import uuid
import json
from datetime import datetime
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

# Set up robust application logging
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler = RotatingFileHandler('app.log', maxBytes=10485760, backupCount=5)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

app_logger = logging.getLogger('yatra_app')
app_logger.setLevel(logging.INFO)
app_logger.addHandler(file_handler)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Flask Configuration - Load from environment variables
# Flask Configuration - Load from environment variables
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key-change-in-production')
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Server-side Session Configuration
from flask_session import Session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
import tempfile as _tempfile
app.config['SESSION_FILE_DIR'] = os.path.join(_tempfile.gettempdir(), 'flask_session')
os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
Session(app)

# Database Configuration
database_url = os.getenv('DATABASE_URI', 'sqlite:///yatra.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

def _is_postgres():
    """Return True if the configured database is PostgreSQL."""
    return database_url.startswith('postgresql')

def _table_exists(table_name):
    """Check if a table exists in the database (works for both SQLite and PostgreSQL)."""
    from sqlalchemy import text as _t
    if _is_postgres():
        row = db.session.execute(
            _t("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public' AND tablename=:n"),
            {'n': table_name}
        ).fetchone()
    else:
        row = db.session.execute(
            _t("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),
            {'n': table_name}
        ).fetchone()
    return row is not None

def _get_all_yatra_table_names():
    """Return a list of all dynamic yatra table names (works for both SQLite and PostgreSQL)."""
    from sqlalchemy import text as _t
    if _is_postgres():
        rows = db.session.execute(
            _t("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public' AND tablename LIKE 'yatra_%' AND tablename != 'yatra_details'")
        ).fetchall()
    else:
        rows = db.session.execute(
            _t("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'yatra_%' AND name != 'yatra_details'")
        ).fetchall()
    return [row[0] for row in rows]



# Razorpay configuration
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_API_KEY', '')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_API_SECRET', '')
if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    print("⚠️ WARNING: RAZORPAY_API_KEY / RAZORPAY_API_SECRET not set. Payment integration will not work.")

# Admin credentials
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'changeme')
if ADMIN_PASSWORD == 'changeme':
    print("⚠️ WARNING: Please change the default admin password in .env file!")

db.init_app(app)

# Create database tables if they don't exist
with app.app_context():
    try:
        db.create_all()
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"⚠️ WARNING: Database table creation failed: {e}")
    
    # Migration: add is_active column
    try:
        from sqlalchemy import text as _text
        db.session.execute(_text("ALTER TABLE yatra_details ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # Migration: add about_image column
    try:
        from sqlalchemy import text as _text
        db.session.execute(_text("ALTER TABLE yatra_details ADD COLUMN about_image VARCHAR(255)"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # Migration: add yatra_message and yatra_link columns
    try:
        from sqlalchemy import text as _text
        db.session.execute(_text("ALTER TABLE yatra_details ADD COLUMN yatra_message TEXT"))
        db.session.execute(_text("ALTER TABLE yatra_details ADD COLUMN yatra_link VARCHAR(500)"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # Migration: add sort_order column to carousel_images
    try:
        from sqlalchemy import text as _text
        db.session.execute(_text("ALTER TABLE carousel_images ADD COLUMN sort_order INTEGER DEFAULT 0"))
        db.session.commit()
    except Exception:
        db.session.rollback()


# Authentication decorator
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            if request.is_json:
                return jsonify({'success': False, 'message': 'Session expired. Please log in again.', 'redirect': url_for('admin_login')}), 401
            flash('Please login to access admin panel.', 'error')
            return redirect(url_for('admin_login'))  # redirects to /admin224151/login
        return f(*args, **kwargs)
    return decorated_function


def _is_valid_table(table_name):
    """Return True only if table_name is a known, whitelisted dynamic yatra table.

    This is the single gatekeeper that prevents SQL injection whenever a
    user-supplied name is used to build a raw SQL string.
    """
    # Only names that start with 'yatra_' and are NOT the schema table itself
    if not isinstance(table_name, str):
        return False
    if not table_name.startswith('yatra_') or table_name == 'yatra_details':
        return False
    # Confirm the table physically exists
    return _table_exists(table_name)

def phone_required(f):
    """Decorator that ensures the user has verified their mobile number."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('phone_verified') or not session.get('verified_phone'):
            flash('Please verify your mobile number first.', 'warning')
            return redirect(url_for('verify_phone'))
        return f(*args, **kwargs)
    return decorated_function

# @app.before_request
# def create_tables():
#     try:
#         db.create_all()
#     except:
#         pass

@app.errorhandler(Exception)
def handle_exception(e):
    # Pass through HTTP errors
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return e
    # Log the unhandled exception
    app_logger.error(f"Unhandled Exception: {str(e)}", exc_info=True)
    return jsonify(error=str(e)) if request.path.startswith('/api') else ("An internal server error occurred. It has been logged.", 500)

@app.route('/')
def index():
    carousel_images = CarouselImage.query.order_by(CarouselImage.sort_order.asc(), CarouselImage.created_at.desc()).all()
    
    youtube_links = []
    setting = AppSettings.query.filter_by(key='recent_yatra_youtube_list').first()
    if setting and setting.value:
        import json
        try:
            youtube_links = json.loads(setting.value)
        except Exception:
            pass
    else:
        # Fallback to legacy single link
        old_setting = AppSettings.query.filter_by(key='recent_yatra_youtube').first()
        if old_setting and old_setting.value:
            youtube_links.append(old_setting.value)
        else:
            youtube_links.append("https://www.youtube.com/embed/zTeCw1twHRY")
    
    processed_links = []
    for link in youtube_links:
        if not link:
            continue
        if "watch?v=" in link:
            video_id = link.split("watch?v=")[1].split("&")[0]
            link = f"https://www.youtube.com/embed/{video_id}"
        elif "youtu.be/" in link:
            video_id = link.split("youtu.be/")[1].split("?")[0]
            link = f"https://www.youtube.com/embed/{video_id}"
        processed_links.append(link)

    return render_template('index.html', carousel_images=carousel_images, youtube_links=processed_links)


@app.route('/catalog')
def catalog():
    """Display Yatra memories catalog page with folder counts"""
    import os
    
    # Photos live in static/images/<FolderName>
    images_base = os.path.join(os.path.dirname(__file__), 'static', 'images')
    
    def get_folder_info(folder_name):
        folder_path = os.path.join(images_base, folder_name)
        if os.path.exists(folder_path):
            files = sorted([f for f in os.listdir(folder_path)
                            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))])
            count = len(files)
            thumbnail = files[0] if files else None
            return count, thumbnail
        return 0, None
    
    vrindavan_count, vrindavan_thumb = get_folder_info('Vrindavan')
    banaras_count, banaras_thumb     = get_folder_info('Banaras')
    jagannath_puri_count, jagannath_puri_thumb = get_folder_info('Jagannath Puri')
    
    return render_template('catalog.html',
                           vrindavan_count=vrindavan_count,
                           banaras_count=banaras_count,
                           jagannath_puri_count=jagannath_puri_count,
                           vrindavan_thumb=vrindavan_thumb,
                           banaras_thumb=banaras_thumb,
                           jagannath_puri_thumb=jagannath_puri_thumb)

@app.route('/catalog/<folder_name>')
def view_catalog_folder(folder_name):
    """View photos in a specific catalog folder"""
    import os
    
    # Security: Only allow specific folder names
    allowed_folders = ['Vrindavan', 'Banaras', 'Jagannath Puri']
    if folder_name not in allowed_folders:
        flash('Invalid folder name', 'error')
        return redirect(url_for('catalog'))
    
    # Photos live in static/images/<folder_name>
    folder_path = os.path.join(os.path.dirname(__file__), 'static', 'images', folder_name)
    
    photos = []
    if os.path.exists(folder_path):
        photos = sorted([f for f in os.listdir(folder_path)
                         if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))])
    
    return render_template('catalog_folder.html',
                           folder_name=folder_name,
                           photos=photos)

@app.route('/catalog/<folder_name>/<filename>')
def serve_catalog_image(folder_name, filename):
    """Serve images from static/images/<folder_name>"""
    import os
    from flask import send_from_directory
    
    # Security: Only allow specific folder names
    allowed_folders = ['Vrindavan', 'Banaras', 'Jagannath Puri']
    if folder_name not in allowed_folders:
        flash('Invalid folder name', 'error')
        return redirect(url_for('catalog'))
    
    images_path = os.path.join(os.path.dirname(__file__), 'static', 'images', folder_name)
    return send_from_directory(images_path, filename)

@app.route('/admin/carousel')
@login_required
def admin_carousel():
    """Admin: Manage homepage carousel photos"""
    images = CarouselImage.query.order_by(CarouselImage.sort_order.asc(), CarouselImage.created_at.desc()).all()
    return render_template('admin_carousel.html', images=images)

@app.route('/admin/carousel/upload', methods=['POST'])
@login_required
def admin_carousel_upload():
    """Admin: Upload photo(s) to carousel"""
    import os
    import uuid
    from werkzeug.utils import secure_filename

    ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
    files = request.files.getlist('photos')

    if not files or all(f.filename == '' for f in files):
        flash('No files selected.', 'error')
        return redirect(url_for('admin_carousel'))

    upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'carousel')
    os.makedirs(upload_folder, exist_ok=True)

    # Find the current max sort_order
    max_order_img = CarouselImage.query.order_by(CarouselImage.sort_order.desc()).first()
    current_max_order = max_order_img.sort_order if max_order_img else 0

    uploaded = 0
    for f in files:
        if f and f.filename:
            ext = os.path.splitext(f.filename)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue
            filename = secure_filename(f.filename)
            base, extension = os.path.splitext(filename)
            unique_filename = f"{base}_{uuid.uuid4().hex[:8]}{extension}"
            save_path = os.path.join(upload_folder, unique_filename)
            f.save(save_path)
            
            current_max_order += 1
            new_image = CarouselImage(image_path=f"uploads/carousel/{unique_filename}", sort_order=current_max_order)
            db.session.add(new_image)
            uploaded += 1

    if uploaded > 0:
        db.session.commit()
        flash(f'✅ Successfully uploaded {uploaded} carousel image(s).', 'success')
    return redirect(url_for('admin_carousel'))

@app.route('/admin/carousel/reorder', methods=['POST'])
@login_required
def admin_carousel_reorder():
    """Admin: Reorder carousel photos"""
    data = request.get_json()
    order_list = data.get('order', [])
    try:
        for idx, img_id in enumerate(order_list):
            img = CarouselImage.query.get(img_id)
            if img:
                img.sort_order = idx
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@app.route('/register', methods=['GET', 'POST'])
def register():
    # Check if registration is enabled
    if not settings.is_registration_enabled():
        message = settings.get_setting('registration_closed_message', 
                                       'Thank you for your overwhelming response. All seats are currently booked as of today. Kindly wait until 1st April 2026 for the opening of the second registration slot.')
        return render_template('registration_closed.html', message=message)
    
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

@app.route('/admin/carousel/delete', methods=['POST'])
@login_required
def admin_carousel_delete():
    import os
    data = request.get_json()
    image_id = (data or {}).get('image_id')

    if not image_id:
        return jsonify({'success': False, 'message': 'Invalid image ID.'})

    img = CarouselImage.query.get(image_id)
    if not img:
        return jsonify({'success': False, 'message': 'Image not found.'})

    try:
        if img.image_path:
            full_path = os.path.join(app.root_path, 'static', img.image_path)
            if os.path.exists(full_path):
                os.remove(full_path)
        
        db.session.delete(img)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Deleted successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


import re
import random

def normalize_phone(phone_str):
    """Normalize phone number to +91XXXXXXXXXX or plain 10-digit XXXXXXXXXX format.
    Returns (normalized, error_message)."""
    phone = phone_str.strip()
    # Strip +91 prefix if present
    if phone.startswith('+91'):
        digits = phone[3:]
    elif phone.startswith('91') and len(phone) == 12:
        digits = phone[2:]
    else:
        digits = phone
    # Must be exactly 10 digits
    if not re.fullmatch(r'\d{10}', digits):
        return None, f'Phone number must be in +91XXXXXXXXXX or XXXXXXXXXX format (10 digits after country code).'
    # Return with +91 prefix for consistency
    return f'+91{digits}', None


# ===== MOBILE OTP VERIFICATION ROUTES (via Fast2SMS) =====

@app.route('/verify-phone', methods=['GET'])
def verify_phone():
    """Show the mobile OTP verification page"""
    reg_setting = AppSettings.query.filter_by(key='registration_enabled').first()
    is_enabled = reg_setting.value != 'false' if reg_setting else True

    if not is_enabled:
        title_setting = AppSettings.query.filter_by(key='registration_closed_title').first()
        desc_setting = AppSettings.query.filter_by(key='registration_closed_description').first()
        title = title_setting.value if title_setting else "Registration is now Closed"
        description = desc_setting.value if desc_setting else "Thank you for your interest! We have reached our maximum capacity for this Yatra and registrations are currently closed. Please check back later for any updates or cancellations."
        return render_template('registration_closed.html', title=title, description=description)

    # If already verified in this session, skip to register
    if session.get('phone_verified'):
        return redirect(url_for('dashboard'))
    return render_template('verify_phone.html')

# Backward-compat redirect: /verify-email → /verify-phone
@app.route('/verify-email', methods=['GET'])
def verify_email():
    return redirect(url_for('verify_phone'))


@app.route('/send-otp', methods=['POST'])
def send_otp():
    """Bypassed OTP verification - immediately verify and redirect to dashboard"""
    # Check registration_enabled from AppSettings
    reg_setting = AppSettings.query.filter_by(key='registration_enabled').first()
    is_enabled = reg_setting.value != 'false' if reg_setting else True
    
    data = request.get_json()
    phone_raw = (data or {}).get('phone', '').strip()

    # Validate and normalise
    norm_phone, phone_err = normalize_phone(phone_raw)
    if phone_err:
        return jsonify({'success': False, 'message': phone_err})

    if not is_enabled:
        # Still allow login if the phone number is already registered
        existing_user = LoginDetails.query.filter_by(login_id=norm_phone).first()
        if not existing_user:
            return jsonify({'success': False, 'message': 'Registration is currently closed for new users.'})

    # Bypass OTP logic — generate a tab-bound token for sessionStorage isolation
    tab_token = uuid.uuid4().hex
    session['phone_verified'] = True
    session['verified_phone'] = norm_phone
    session['tab_token'] = tab_token

    return jsonify({
        'success': True,
        'message': 'Login successful! Redirecting...',
        'tab_token': tab_token,
        'redirect': url_for('dashboard')
    })





# ===== DASHBOARD ROUTES =====

@app.route('/dashboard')
@phone_required
def dashboard():
    """Dashboard showing passengers from UNION of login_details + yatra tables"""
        
    verified_phone = session.get('verified_phone')
    from sqlalchemy import text as _txt
    from types import SimpleNamespace
    from datetime import datetime
    current_year = datetime.now().year

    # ── 1. Passengers from login_details ──
    active_passengers = LoginDetails.query.filter_by(login_id=verified_phone).all()
    deleted_passengers = LoginDetails.query.filter_by(login_id=f"#del#{verified_phone}").all()
    # deleted_by_id mapping for quick lookup
    deleted_by_id = {p.id: p for p in deleted_passengers}

    active_names = set(p.name for p in active_passengers)
    deleted_names = set(p.name for p in deleted_passengers)

    # Active yatras for the dropdown
    yatras = YatraDetails.query.filter_by(is_active=True).all()
    # ALL yatras for passenger lookup (including inactive)
    all_yatras = YatraDetails.query.all()
    selected_yatra_id = session.get('selected_yatra_id', '')

    # ── 2. Collect passenger keys from ALL yatra tables ──
    # Map passenger_id to boolean (true if exists in any yatra table)
    # Also store name lookup for virtual accounts
    ids_in_yatras = set()
    names_in_yatras = {} # name -> data for virtuals
    
    for yatra in all_yatras:
        tname = sanitize_table_name(yatra.title)
        try:
            if not _table_exists(tname):
                continue
            # Select relevant fields + passenger_id
            rows = db.session.execute(
                _txt(f"SELECT name, year_of_birth, email, phone, gender, city, district, state, passenger_id FROM {tname} WHERE login_id=:lid"),
                {'lid': verified_phone}
            ).fetchall()
            for row in rows:
                rname = row[0]
                pid = row[8]
                if pid:
                    ids_in_yatras.add(pid)
                if rname not in names_in_yatras:
                    names_in_yatras[rname] = {
                        'name': rname, 'year_of_birth': row[1], 'email': row[2] or '',
                        'phone': row[3] or '', 'gender': row[4] or '',
                        'city': row[5] or '', 'district': row[6] or '', 'state': row[7] or '',
                    }
        except Exception:
            pass

    # ── 3. Build combined passenger list (UNION) ──
    passengers = []
    soft_deleted_ids = set()
    yatra_only_ids = set()

    # 3a. Active passengers (from login_details)
    for p in active_passengers:
        p._soft_deleted = False
        p.age = current_year - p.year_of_birth if p.year_of_birth else '—'
        passengers.append(p)

    # 3b. Soft-deleted passengers that have yatra entries OR are interest-level → restore as read-only
    for pid, p in deleted_by_id.items():
        if pid in ids_in_yatras:
            p._soft_deleted = True
            soft_deleted_ids.add(p.id)
            p.age = current_year - p.year_of_birth if p.year_of_birth else '—'
            passengers.append(p)

    # 3c. Names that exist ONLY in yatra tables (pure virtuals if any exist)
    already_included_names = active_names | deleted_names
    virtual_counter = 900000
    for name, data in names_in_yatras.items():
        if name in already_included_names:
            continue
        virtual_counter += 1
        virtual = SimpleNamespace(
            id=virtual_counter, login_id=verified_phone,
            name=data['name'], year_of_birth=data['year_of_birth'], email=data['email'],
            phone=data['phone'], gender=data['gender'],
            city=data['city'], district=data['district'], state=data['state'],
            photo=None, aadhar='', _soft_deleted=True,
            age=current_year - data['year_of_birth'] if data['year_of_birth'] else '—'
        )
        yatra_only_ids.add(virtual_counter)
        soft_deleted_ids.add(virtual_counter)
        passengers.append(virtual)

    # ── 4. Build saved_packages from active yatra tables ──
    saved_packages = {}
    for yatra in yatras:
        tname = sanitize_table_name(yatra.title)
        try:
            if not _table_exists(tname):
                continue
            rows = db.session.execute(
                _txt(f"SELECT name, hotel_package, travel_package, start_date, end_date, status, razorpay_id, passenger_id FROM {tname} WHERE login_id=:lid"),
                {'lid': verified_phone}
            ).fetchall()
            for row in rows:
                db_name, hotel_pkg, travel_pkg, s_date, e_date, status, razorpay_id, db_pid = row
                for p in passengers:
                    # Match explicitly by passenger_id (new way) or fallback to name (legacy)
                    if (db_pid is not None and p.id == db_pid) or (db_pid is None and p.name == db_name):
                        key = f"{yatra.id}:{p.id}"
                        saved_packages[key] = {
                            'yatra_id': yatra.id,
                            'passenger_id': p.id,
                            'hotel_package': hotel_pkg or '',
                            'travel_package': travel_pkg or '',
                            'start_date': s_date or '',
                            'end_date': e_date or '',
                            'status': status or 'Interest',
                            'razorpay_id': razorpay_id or '',
                        }
                        break
        except Exception as e:
            print(f"[WARNING] Could not read saved packages from {tname}: {e}")

    # Session data overrides DB but preserves DB fields like razorpay_id
    for reg in session.get('yatra_registrations', []):
        key = reg.get('key', f"{reg['yatra_id']}:{reg['passenger_id']}")
        if key not in saved_packages:
            saved_packages[key] = {}
        
        db_status = saved_packages[key].get('status', 'Interest')
        sess_status = reg.get('status', 'Interest')
        final_status = 'Paid' if db_status == 'Paid' else sess_status
        
        saved_packages[key].update({
            'yatra_id': reg['yatra_id'],
            'passenger_id': reg['passenger_id'],
            'hotel_package': reg.get('hotel_package', ''),
            'travel_package': reg.get('travel_package', ''),
            'start_date': reg.get('start_date', ''),
            'end_date': reg.get('end_date', ''),
            'status': final_status,
        })

    # ── 5. Build helper sets for template ──
    yatra_registrations = [
        {'yatra_id': v['yatra_id'], 'passenger_id': v['passenger_id']}
        for v in saved_packages.values()
    ]

    passengers_with_packages = set()
    for key in saved_packages:
        try:
            _, p_id_str = key.split(':', 1)
            passengers_with_packages.add(int(p_id_str))
        except (ValueError, TypeError):
            pass

    # ── 6. Load accept_payment_mode setting ──
    apm_setting = AppSettings.query.filter_by(key='accept_payment_mode').first()
    accept_payment_mode = apm_setting.value == 'true' if apm_setting else False

    return render_template('dashboard.html',
        passengers=passengers,
        verified_phone=verified_phone,
        yatras=yatras,
        passenger_packages=session.get('passenger_packages', {}),
        selected_yatra_id=selected_yatra_id,
        yatra_registrations=yatra_registrations,
        saved_packages=saved_packages,
        passengers_with_packages=passengers_with_packages,
        soft_deleted_ids=soft_deleted_ids,
        current_year=current_year,
        tab_token=session.get('tab_token', ''),
        accept_payment_mode=accept_payment_mode,
        razorpay_key_id=RAZORPAY_KEY_ID)

@app.route('/save-passenger-package', methods=['POST'])
@phone_required
def save_passenger_package():
    """Save an individual passenger's chosen Yatra package config to the database via AJAX"""
        
    yatra_id = request.form.get('yatra_id')
    p_id = request.form.get('passenger_id')
    hotel_pkg = request.form.get('hotel')
    travel_pkg = request.form.get('travel')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    
    if not yatra_id or not p_id or not hotel_pkg or not travel_pkg:
        return jsonify({'success': False, 'message': 'Please completely fill out the Yatra package options.'})

    passenger = LoginDetails.query.get(p_id)
    if not passenger:
        return jsonify({'success': False, 'message': 'Passenger not found.'})
        
    start_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
            
    end_date = None
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    # Save package selection into session (keyed by yatra_id:passenger_id)
    regs = session.get('yatra_registrations', [])
    key = f"{yatra_id}:{p_id}"
    regs = [r for r in regs if r.get('key') != key]
    regs.append({
        'key': key,
        'yatra_id': yatra_id,
        'passenger_id': p_id,
        'hotel_package': hotel_pkg,
        'travel_package': travel_pkg,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'status': 'Interest',
    })
    session['yatra_registrations'] = regs
    session['selected_yatra_id'] = yatra_id

    # Also insert/update into the Yatra's dedicated dynamic table
    try:
        yatra = YatraDetails.query.get(int(yatra_id))
        if yatra:
            from sqlalchemy import text
            tname = sanitize_table_name(yatra.title)
            # Check if table exists
            exists = _table_exists(tname)
            if exists:
                old_row = db.session.execute(text(f"SELECT status, razorpay_id FROM {tname} WHERE passenger_id=:pid OR (passenger_id IS NULL AND login_id=:lid AND name=:nm)"),
                                             {'pid': p_id, 'lid': session.get('verified_phone'), 'nm': passenger.name}).fetchone()
                existing_status = old_row[0] if old_row else 'Interest'
                existing_rzp = old_row[1] if old_row else None

                # Delete old entry for this passenger in this yatra table
                db.session.execute(text(f"DELETE FROM {tname} WHERE passenger_id=:pid OR (passenger_id IS NULL AND login_id=:lid AND name=:nm)"),
                                   {'pid': p_id, 'lid': session.get('verified_phone'), 'nm': passenger.name})
                # Insert fresh
                db.session.execute(text(f"""
                    INSERT INTO {tname} (login_id, passenger_id, name, year_of_birth, email, phone, gender, city, district, state,
                        hotel_package, travel_package, start_date, end_date, status, razorpay_id)
                    VALUES (:login_id,:passenger_id,:name,:year_of_birth,:email,:phone,:gender,:city,:district,:state,
                        :hotel_package,:travel_package,:start_date,:end_date,:status,:rzp)
                """), {
                    'login_id': session.get('verified_phone'),
                    'passenger_id': p_id,
                    'name': passenger.name,
                    'year_of_birth': passenger.year_of_birth,
                    'email': passenger.email or '',
                    'phone': passenger.phone or session.get('verified_phone'),
                    'gender': passenger.gender,
                    'city': passenger.city or '',
                    'district': passenger.district or '',
                    'state': passenger.state or '',
                    'hotel_package': hotel_pkg,
                    'travel_package': travel_pkg,
                    'start_date': start_date_str or '',
                    'end_date': end_date_str or '',
                    'status': existing_status,
                    'rzp': existing_rzp,
                })
                db.session.commit()
    except Exception as e:
        print(f"[WARNING] Could not insert into Yatra table: {e}")
        existing_status = 'Interest'

    return jsonify({'success': True, 'message': 'Package saved!', 'status': existing_status if 'existing_status' in locals() else 'Interest'})


@app.route('/create-razorpay-order', methods=['POST'])
@phone_required
def create_razorpay_order():
    """Create a Razorpay order for a single passenger payment."""
    # Check accept_payment_mode
    apm_setting = AppSettings.query.filter_by(key='accept_payment_mode').first()
    accept_payment_mode = apm_setting.value == 'true' if apm_setting else False
    if not accept_payment_mode:
        return jsonify({'success': False, 'message': 'Payment is not currently accepted. Please contact the organizer.'})

    data = request.get_json()
    yatra_id = data.get('yatra_id')
    passenger_id = data.get('passenger_id')
    amount_paise = data.get('amount_paise')  # amount in paise (INR * 100)

    if not yatra_id or passenger_id is None or not amount_paise:
        return jsonify({'success': False, 'message': 'Missing required data.'})

    try:
        import razorpay
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        order = client.order.create({
            'amount': int(amount_paise),
            'currency': 'INR',
            'receipt': f'yatra_{yatra_id}_p_{passenger_id}_{uuid.uuid4().hex[:6]}',
            'payment_capture': 1
        })
        return jsonify({'success': True, 'order_id': order['id'], 'amount': order['amount'], 'currency': order['currency']})
    except Exception as e:
        app_logger.error(f"Razorpay order creation failed: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'Could not create payment order: {str(e)}'})


@app.route('/verify-razorpay-payment', methods=['POST'])
@phone_required
def verify_razorpay_payment():
    """Verify Razorpay payment signature and mark passenger as Paid."""
    data = request.get_json()
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    yatra_id = data.get('yatra_id')
    passenger_id = data.get('passenger_id')

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature, yatra_id, passenger_id]):
        return jsonify({'success': False, 'message': 'Missing payment verification data.'})

    try:
        import razorpay
        import hmac, hashlib
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        # Verify signature
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        client.utility.verify_payment_signature(params_dict)
    except Exception as e:
        app_logger.error(f"Razorpay signature verification failed: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Payment verification failed. Please contact support.'})

    # Signature valid — update DB
    try:
        yatra = YatraDetails.query.get(yatra_id)
        passenger = LoginDetails.query.get(passenger_id)
        if not yatra or not passenger:
            return jsonify({'success': False, 'message': 'Yatra or passenger not found.'})

        from sqlalchemy import text
        tname = sanitize_table_name(yatra.title)
        verified_phone = session.get('verified_phone')

        db.session.execute(text(f"""
            UPDATE {tname}
            SET status = 'Paid', razorpay_id = :rzp
            WHERE login_id = :lid AND name = :nm
        """), {'rzp': razorpay_payment_id, 'lid': verified_phone, 'nm': passenger.name})
        db.session.commit()

        # Update session
        regs = session.get('yatra_registrations', [])
        for r in regs:
            if str(r.get('yatra_id')) == str(yatra_id) and str(r.get('passenger_id')) == str(passenger_id):
                r['status'] = 'Paid'
        session['yatra_registrations'] = regs
        session.modified = True

        return jsonify({'success': True, 'message': 'Payment verified and recorded!', 'razorpay_payment_id': razorpay_payment_id})
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"DB update after payment failed: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)})


@app.route('/pay-all', methods=['POST'])
@phone_required
def pay_all():
    """Mark all pending passengers as paid (used after bulk Razorpay payment)"""
    data = request.get_json()
    yatra_id = data.get('yatra_id')
    razorpay_payment_id = data.get('razorpay_payment_id', '')
    if not yatra_id:
        return jsonify({'success': False, 'message': 'Yatra ID is required.'})

    yatra = YatraDetails.query.get(yatra_id)
    if not yatra:
        return jsonify({'success': False, 'message': 'Yatra not found.'})

    try:
        from sqlalchemy import text
        tname = sanitize_table_name(yatra.title)
        exists = _table_exists(tname)
        
        if not exists:
            return jsonify({'success': False, 'message': 'Yatra table not found.'})

        verified_phone = session.get('verified_phone')
        rzp_id = razorpay_payment_id if razorpay_payment_id else f"pay_{uuid.uuid4().hex[:14]}"
        
        # Update status to Paid for all non-Paid entries for this user
        db.session.execute(text(f"""
            UPDATE {tname} 
            SET status = 'Paid', razorpay_id = :rzp
            WHERE login_id = :lid AND (status IS NULL OR status != 'Paid')
        """), {'lid': verified_phone, 'rzp': rzp_id})
        
        db.session.commit()

        # Update session override so dashboard doesn't revert to Interest
        regs = session.get('yatra_registrations', [])
        for r in regs:
            if str(r.get('yatra_id')) == str(yatra_id):
                r['status'] = 'Paid'
        session['yatra_registrations'] = regs
        session.modified = True

        return jsonify({'success': True, 'message': 'Payment successful!'})
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"Payment failed during execution of /pay-all: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)})


@app.route('/pay-passenger', methods=['POST'])
@phone_required
def pay_passenger():
    """Dummy endpoint to mark a single pending passenger as paid for the selected yatra"""
    data = request.get_json()
    yatra_id = data.get('yatra_id')
    passenger_id = data.get('passenger_id')

    if not yatra_id or not passenger_id:
        return jsonify({'success': False, 'message': 'Missing data.'})

    yatra = YatraDetails.query.get(yatra_id)
    passenger = LoginDetails.query.get(passenger_id)
    if not yatra or not passenger:
        return jsonify({'success': False, 'message': 'Yatra or passenger not found.'})

    try:
        from sqlalchemy import text
        tname = sanitize_table_name(yatra.title)
        
        verified_phone = session.get('verified_phone')
        import uuid
        dummy_rzp = f"pay_{uuid.uuid4().hex[:14]}"
        
        db.session.execute(text(f"""
            UPDATE {tname} 
            SET status = 'Paid', razorpay_id = :rzp
            WHERE login_id = :lid AND name = :nm AND (status IS NULL OR status != 'Paid')
        """), {'lid': verified_phone, 'nm': passenger.name, 'rzp': dummy_rzp})
        
        db.session.commit()

        # Update session override
        regs = session.get('yatra_registrations', [])
        for r in regs:
            if str(r.get('yatra_id')) == str(yatra_id) and str(r.get('passenger_id')) == str(passenger_id):
                r['status'] = 'Paid'
        session['yatra_registrations'] = regs
        session.modified = True

        return jsonify({'success': True, 'message': 'Payment successful!'})
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"Single payment failed for passenger {passenger_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete-traveler/<int:traveler_id>', methods=['POST'])
@phone_required
def delete_traveler(traveler_id):
    """Soft-delete a traveler by prefixing their login_id with #del#.
    Only modifies the login_details table — yatra table entries are untouched."""
    verified_phone = session.get('verified_phone')
    traveler = LoginDetails.query.get_or_404(traveler_id)

    # Ensure this user owns the traveler
    if traveler.login_id != verified_phone:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))

    try:
        traveler.login_id = f"#del#{traveler.login_id}"
        db.session.commit()
        flash(f'Traveler "{traveler.name}" removed successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing traveler: {str(e)}', 'error')

    return redirect(url_for('dashboard'))


@app.route('/add-traveler', methods=['GET', 'POST'])
@phone_required
def add_traveler():
    """Add a new traveler to the Login Details table"""
        
    verified_phone = session.get('verified_phone')
    
    if request.method == 'POST':
        import os
        from werkzeug.utils import secure_filename
        
        name = request.form.get('name')
        aadhar = request.form.get('aadhar')
        yob = request.form.get('year_of_birth')
        gender = request.form.get('gender')
        email = request.form.get('email')
        alt_phone = request.form.get('phone')
        city = request.form.get('city')
        district = request.form.get('district')
        state = request.form.get('state')

        # Validate Aadhar (12 digits if provided)
        if aadhar and (not aadhar.isdigit() or len(aadhar) != 12):
            flash('Aadhar number must be exactly 12 digits.', 'error')
            return render_template('add_traveler.html', current_year=datetime.now().year)

        # Validate Alt Phone (10 digits if provided)
        if alt_phone and (not alt_phone.isdigit() or len(alt_phone) != 10):
            flash('Alternative phone number must be exactly 10 digits.', 'error')
            return render_template('add_traveler.html', current_year=datetime.now().year)

        # Prevent exact duplicate names under same login_id
        existing_traveler = LoginDetails.query.filter(
            LoginDetails.login_id == verified_phone,
            db.func.lower(db.func.trim(LoginDetails.name)) == db.func.lower(name.strip())
        ).first()
        if existing_traveler:
            flash(f'A traveler named "{name.strip()}" is already registered under this phone number. Please update the existing profile instead.', 'error')
            return render_template('add_traveler.html', current_year=datetime.now().year)
        
        photo_file = request.files.get('photo')
        photo_path = None
        
        if photo_file and photo_file.filename != '':
            filename = secure_filename(photo_file.filename)
            base, extension = os.path.splitext(filename)
            unique_filename = f"{base}_{uuid.uuid4().hex[:8]}{extension}"
            
            upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'passengers')
            os.makedirs(upload_folder, exist_ok=True)
            
            photo_file.save(os.path.join(upload_folder, unique_filename))
            photo_path = f"uploads/passengers/{unique_filename}"
        
        try:
            new_traveler = LoginDetails(
                login_id=verified_phone,
                photo=photo_path,
                name=name,
                aadhar=aadhar,
                year_of_birth=int(yob) if yob and str(yob).isdigit() else 0,
                gender=gender,
                email=email,
                phone=alt_phone,
                city=city,
                district=district,
                state=state
            )
            db.session.add(new_traveler)
            db.session.commit()
            flash('Traveler added successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding traveler: {str(e)}', 'error')
            
    current_year = datetime.now().year
    return render_template('add_traveler.html', current_year=current_year)

@app.route('/edit-traveler/<int:traveler_id>', methods=['GET', 'POST'])
@phone_required
def edit_traveler(traveler_id):
    """Edit an existing traveler"""
        
    verified_phone = session.get('verified_phone')
    traveler = LoginDetails.query.get_or_404(traveler_id)
    
    # Ensure this user owns the traveler
    if traveler.login_id != verified_phone:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        import os
        from werkzeug.utils import secure_filename
        
        traveler.name = request.form.get('name')
        traveler.aadhar = request.form.get('aadhar')
        
        yob_str = request.form.get('year_of_birth')
        if yob_str and str(yob_str).isdigit():
            traveler.year_of_birth = int(yob_str)
        
        traveler.gender = request.form.get('gender')
        traveler.email = request.form.get('email')
        traveler.phone = request.form.get('phone')
        traveler.city = request.form.get('city')
        traveler.district = request.form.get('district')
        traveler.state = request.form.get('state')

        # Validate Aadhar (12 digits if provided)
        if traveler.aadhar and (not traveler.aadhar.isdigit() or len(traveler.aadhar) != 12):
            flash('Aadhar number must be exactly 12 digits.', 'error')
            return render_template('edit_traveler.html', traveler=traveler, current_year=datetime.now().year)

        # Validate Alt Phone (10 digits if provided)
        if traveler.phone and (not traveler.phone.isdigit() or len(traveler.phone) != 10):
            flash('Alternative phone number must be exactly 10 digits.', 'error')
            return render_template('edit_traveler.html', traveler=traveler, current_year=datetime.now().year)

        # Prevent exact duplicate names under same login_id (excluding the current traveler)
        new_name = traveler.name.strip() if traveler.name else ""
        existing_traveler = LoginDetails.query.filter(
            LoginDetails.login_id == verified_phone,
            LoginDetails.id != traveler.id,
            db.func.lower(db.func.trim(LoginDetails.name)) == db.func.lower(new_name)
        ).first()
        if existing_traveler:
            flash(f'A traveler named "{new_name}" is already registered under this phone number. Names must be unique per login.', 'error')
            return render_template('edit_traveler.html', traveler=traveler, current_year=datetime.now().year)
        
        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename != '':
            filename = secure_filename(photo_file.filename)
            base, extension = os.path.splitext(filename)
            import uuid
            unique_filename = f"{base}_{uuid.uuid4().hex[:8]}{extension}"
            
            upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'passengers')
            os.makedirs(upload_folder, exist_ok=True)
            
            import os
            if traveler.photo:
                old_path = os.path.join(app.root_path, 'static', traveler.photo)
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass
            
            photo_file.save(os.path.join(upload_folder, unique_filename))
            traveler.photo = f"uploads/passengers/{unique_filename}"
            
        try:
            db.session.commit()
            
            # Sync edits back to dynamic Yatra tables
            try:
                from sqlalchemy import text
                tables = get_dynamic_yatra_tables()
                for yt in tables:
                    tname = yt['table_name']
                    sync_query = text(f"""
                        UPDATE {tname}
                        SET name = :name, year_of_birth = :yob, gender = :gender, email = :email,
                            phone = :phone, city = :city, district = :district, state = :state
                        WHERE passenger_id = :pid
                    """)
                    db.session.execute(sync_query, {
                        'name': traveler.name,
                        'yob': traveler.year_of_birth,
                        'gender': traveler.gender,
                        'email': traveler.email,
                        'phone': traveler.phone,
                        'city': traveler.city,
                        'district': traveler.district,
                        'state': traveler.state,
                        'pid': traveler.id
                    })
                db.session.commit()
            except Exception as sync_e:
                app.logger.error(f"Error syncing dynamic tables: {sync_e}")
                
            flash('Traveler details updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating traveler: {str(e)}', 'error')
            
    current_year = datetime.now().year
    return render_template('edit_traveler.html', traveler=traveler, current_year=current_year)


@app.route('/admin224151/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page — supports both AJAX JSON and regular form POST"""
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            username = (data or {}).get('username', '')
            password = (data or {}).get('password', '')
        else:
            username = request.form.get('username')
            password = request.form.get('password')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            admin_tab_token = uuid.uuid4().hex
            session['admin_logged_in'] = True
            session['admin_tab_token'] = admin_tab_token
            if request.is_json:
                return jsonify({'success': True, 'admin_tab_token': admin_tab_token,
                                'redirect': url_for('admin_dashboard')})
            flash('Successfully logged in as admin!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Invalid credentials.'})
            flash('Invalid credentials. Please try again.', 'error')

    return render_template('admin_login.html')

@app.route('/admin224151/logout')
def admin_logout():
    """Logout admin — clear session including admin tab token"""
    session.pop('admin_logged_in', None)
    session.pop('admin_tab_token', None)
    flash('Successfully logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    """Logout passenger user — clear phone verification + tab token."""
    session.pop('phone_verified', None)
    session.pop('verified_phone', None)
    session.pop('tab_token', None)

    session.pop('yatra_registrations', None)
    session.pop('selected_yatra_id', None)
    session.pop('passenger_packages', None)
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('verify_phone'))

import re as _re

def sanitize_table_name(title):
    """Convert a Yatra title to a valid SQLite table name."""
    name = title.lower().strip()
    name = _re.sub(r'[^a-z0-9]', '_', name)
    name = _re.sub(r'_+', '_', name).strip('_')
    return f"yatra_{name}"

def get_dynamic_yatra_tables():
    """Return list of dicts for all dynamic Yatra tables with is_active status."""
    table_names = _get_all_yatra_table_names()
    tables = []
    all_yatras = YatraDetails.query.all()
    for tname in table_names:
        display = tname[6:].replace('_', ' ').title()
        # Match to a YatraDetails record by comparing sanitized title
        matched = next((yd for yd in all_yatras if sanitize_table_name(yd.title) == tname), None)
        tables.append({
            'table_name': tname,
            'display': display,
            'yatra_id': matched.id if matched else None,
            'is_active': matched.is_active if matched else True,
        })
    return tables

@app.context_processor
def inject_tokens():
    return {
        'tab_token': session.get('tab_token', ''),
        'admin_tab_token': session.get('admin_tab_token', '')
    }

@app.route('/admin/registration-status', methods=['GET'])
@login_required
def get_registration_status():
    reg_setting = AppSettings.query.filter_by(key='registration_enabled').first()
    is_enabled = reg_setting.value != 'false' if reg_setting else True
    return jsonify({'enabled': is_enabled})

@app.route('/admin/toggle-registration', methods=['POST'])
@login_required
def toggle_registration():
    data = request.get_json()
    enabled = data.get('enabled', True)
    
    reg_setting = AppSettings.query.filter_by(key='registration_enabled').first()
    if not reg_setting:
        reg_setting = AppSettings(key='registration_enabled')
        db.session.add(reg_setting)
        
    reg_setting.value = 'true' if enabled else 'false'
    db.session.commit()
    
    msg = "Registration has been enabled." if enabled else "Registration has been disabled."
    return jsonify({'success': True, 'enabled': enabled, 'message': msg})

@app.route('/admin/accept-payment-status', methods=['GET'])
@login_required
def get_accept_payment_status():
    apm_setting = AppSettings.query.filter_by(key='accept_payment_mode').first()
    is_mode = apm_setting.value == 'true' if apm_setting else False
    return jsonify({'accept_payment_mode': is_mode})

@app.route('/admin/toggle-accept-payment', methods=['POST'])
@login_required
def toggle_accept_payment():
    data = request.get_json()
    accept_payment = data.get('accept_payment_mode', False)
    
    apm_setting = AppSettings.query.filter_by(key='accept_payment_mode').first()
    if not apm_setting:
        apm_setting = AppSettings(key='accept_payment_mode')
        db.session.add(apm_setting)
        
    apm_setting.value = 'true' if accept_payment else 'false'
    db.session.commit()
    
    msg = "Accept Payment Mode is now ON. Travelers can make payments." if accept_payment else "Accept Payment Mode is now OFF. Payments are paused."
    return jsonify({'success': True, 'accept_payment_mode': accept_payment, 'message': msg})

@app.route('/admin/registration-closed-settings', methods=['GET', 'POST'])
@login_required
def admin_registration_closed_settings():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        
        setting_title = AppSettings.query.filter_by(key='registration_closed_title').first()
        if not setting_title:
            setting_title = AppSettings(key='registration_closed_title')
            db.session.add(setting_title)
        setting_title.value = title
        
        setting_desc = AppSettings.query.filter_by(key='registration_closed_description').first()
        if not setting_desc:
            setting_desc = AppSettings(key='registration_closed_description')
            db.session.add(setting_desc)
        setting_desc.value = description
        
        db.session.commit()
        flash('Registration Closed settings updated successfully.', 'success')
        return redirect(url_for('admin_registration_closed_settings'))
        
    title_setting = AppSettings.query.filter_by(key='registration_closed_title').first()
    desc_setting = AppSettings.query.filter_by(key='registration_closed_description').first()
    
    current_title = title_setting.value if title_setting else "Registration is now Closed"
    current_desc = desc_setting.value if desc_setting else "Thank you for your interest! We have reached our maximum capacity for this Yatra and registrations are currently closed. Please check back later for any updates or cancellations."
    
    return render_template('admin_registration_closed_settings.html', 
                           title=current_title, 
                           description=current_desc)

@app.route('/admin/youtube-link-settings', methods=['GET', 'POST'])
@login_required
def admin_youtube_settings():
    if request.method == 'POST':
        links = []
        for i in range(1, 4):
            link = request.form.get(f'youtube_link_{i}', '').strip()
            if link:
                if "watch?v=" in link:
                    video_id = link.split("watch?v=")[1].split("&")[0]
                    link = f"https://www.youtube.com/embed/{video_id}"
                elif "youtu.be/" in link:
                    video_id = link.split("youtu.be/")[1].split("?")[0]
                    link = f"https://www.youtube.com/embed/{video_id}"
                links.append(link)
            else:
                links.append("")
        
        setting = AppSettings.query.filter_by(key='recent_yatra_youtube_list').first()
        if not setting:
            setting = AppSettings(key='recent_yatra_youtube_list')
            db.session.add(setting)
            
        import json
        setting.value = json.dumps(links)
        db.session.commit()
        
        flash('YouTube Links updated successfully.', 'success')
        return redirect(url_for('admin_youtube_settings'))
        
    setting = AppSettings.query.filter_by(key='recent_yatra_youtube_list').first()
    youtube_links = ["", "", ""]
    if setting and setting.value:
        import json
        try:
            parsed = json.loads(setting.value)
            for i in range(min(3, len(parsed))):
                youtube_links[i] = parsed[i]
        except Exception:
            pass
    else:
        # Fallback
        old_setting = AppSettings.query.filter_by(key='recent_yatra_youtube').first()
        if old_setting and old_setting.value:
            youtube_links[0] = old_setting.value
        else:
            youtube_links[0] = "https://www.youtube.com/embed/zTeCw1twHRY"
    
    return render_template('admin_youtube_settings.html', youtube_links=youtube_links)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard showing all database tables"""
    from sqlalchemy import text
    table_type = request.args.get('table', 'passengers')
    
    headers = []
    records = []
    dynamic_yatra_tables = get_dynamic_yatra_tables()
    
    
    if table_type == 'passengers':
        headers = ['Photo', 'Profile ID', 'Login Key (Phone)', 'Name', 'Aadhar No', 'Year of Birth', 'Phone', 'Email', 'City', 'District', 'State', 'Created At']
        items = LoginDetails.query.order_by(LoginDetails.created_at.desc()).all()
        for item in items:
            records.append({
                'id': item.id,
                'cols': [
                    {'type': 'photo', 'url': url_for('static', filename=item.photo) if item.photo else None},
                    item.id,
                    item.login_id,
                    item.name,
                    item.aadhar or '-',
                    item.year_of_birth,
                    item.phone or '-',
                    item.email or '-',
                    item.city or '-',
                    item.district or '-',
                    item.state or '-',
                    item.created_at.strftime('%Y-%m-%d %H:%M') if item.created_at else '-'
                ]
            })
            
    elif table_type == 'yatra_details':
        headers = ['ID', 'Title', 'Starting Date', 'Fixed Start', 'End Date', 'Fixed End', 'Hotel Packages', 'Travel Packages', 'Message', 'Link', 'Created At']
        items = YatraDetails.query.order_by(YatraDetails.created_at.desc()).all()
        for item in items:
            h_str = '-'
            if item.hotel_packages and item.hotel_packages != 'null':
                try:
                    h_list = json.loads(item.hotel_packages)
                    h_str = ", ".join([f"{x['title']} (₹{x['price']})" if isinstance(x, dict) else str(x) for x in h_list])
                except Exception:
                    h_str = item.hotel_packages
                    
            t_str = '-'
            if item.travel_packages and item.travel_packages != 'null':
                try:
                    t_list = json.loads(item.travel_packages)
                    t_str = ", ".join([f"{x['title']} (₹{x['price']})" if isinstance(x, dict) else str(x) for x in t_list])
                except Exception:
                    t_str = item.travel_packages
                    
            records.append({
                'id': item.id,
                'cols': [
                    item.id,
                    item.title,
                    item.starting_date.strftime('%Y-%m-%d') if item.starting_date else '-',
                    'Yes' if item.is_start_fixed else 'No',
                    item.end_date.strftime('%Y-%m-%d') if item.end_date else '-',
                    'Yes' if item.is_end_fixed else 'No',
                    h_str,
                    t_str,
                    item.yatra_message or '-',
                    item.yatra_link or '-',
                    item.created_at.strftime('%Y-%m-%d %H:%M') if item.created_at else '-'
                ]
            })
            
    else:
        # Strict whitelist via _is_valid_table — prevents SQL injection
        if _is_valid_table(table_type):
            from sqlalchemy import text
            headers = ['Photo', 'Profile ID', 'Record ID', 'Parent Login (Phone)', 'Name', 'Year of Birth', 'Aadhar No', 'Email', 'Phone', 'Gender', 'City', 'District', 'State', 'Hotel Package', 'Travel Package', 'Start Date', 'End Date', 'Status', 'RazorPay ID', 'Created At']
            query = f"""
                SELECT id, login_id, name, year_of_birth, email, phone, gender,
                       city, district, state, hotel_package, travel_package,
                       start_date, end_date, status, razorpay_id, created_at, passenger_id
                FROM {table_type} ORDER BY created_at DESC
            """
            rows = db.session.execute(text(query)).fetchall()

            # Fetch photos for all passenger IDs in these rows
            passenger_ids = [row[17] for row in rows if row[17]]
            login_details = LoginDetails.query.filter(LoginDetails.id.in_(passenger_ids)).all() if passenger_ids else []
            info_map = {p.id: {'photo': p.photo, 'aadhar': p.aadhar} for p in login_details}

            for row in rows:
                row_id = row[0]
                lid = row[1]
                nm = row[2]
                passenger_id = row[17]
                
                info = info_map.get(passenger_id, {})
                photo = info.get('photo')
                aadhar = info.get('aadhar') or '-'
                photo_col = {'type': 'photo', 'url': url_for('static', filename=photo) if photo else None}
                
                cols = [
                    photo_col,
                    passenger_id,
                    row_id,
                    lid,
                    nm,
                    row[3],
                    aadhar,
                    row[4],
                    row[5],
                    row[6],
                    row[7],
                    row[8],
                    row[9],
                    row[10],
                    row[11],
                    row[12],
                    row[13],
                    row[14],
                    row[15],
                    row[16]
                ]
                records.append({'id': row_id, 'cols': cols, 'status': row[14]})
        else:
            # Invalid / unknown table — silent fallback to passengers view
            table_type = 'passengers'
            headers = ['Photo', 'Profile ID', 'Login Key (Phone)', 'Name', 'Aadhar No', 'Year of Birth', 'Phone', 'Email', 'City', 'District', 'State', 'Created At']
            items = LoginDetails.query.order_by(LoginDetails.created_at.desc()).all()
            for item in items:
                records.append({'id': item.id, 'cols': [{'type': 'photo', 'url': url_for('static', filename=item.photo) if item.photo else None}, item.id, item.login_id, item.name, item.aadhar or '-', item.year_of_birth, item.phone or '-', item.email or '-', item.city or '-', item.district or '-', item.state or '-', item.created_at.strftime('%Y-%m-%d %H:%M') if item.created_at else '-']})

    return render_template('admin_dashboard.html',
                         headers=headers,
                         records=records,
                         current_table=table_type,
                         dynamic_yatra_tables=dynamic_yatra_tables,
                         admin_tab_token=session.get('admin_tab_token', ''))

@app.route('/admin/manage-yatra', methods=['GET', 'POST'])
@login_required
def admin_manage_yatra():
    """Admin route to create a new Yatra details"""
    if request.method == 'POST':
        title = request.form.get('title')
        start_date_str = request.form.get('starting_date')
        is_start_fixed = 'is_start_fixed' in request.form
        end_date_str = request.form.get('end_date')
        is_end_fixed = 'is_end_fixed' in request.form
        yatra_message = request.form.get('yatra_message')
        yatra_link = request.form.get('yatra_link')
        
        # Process dynamic hotel packages
        hotel_titles = request.form.getlist('hotel_title[]')
        hotel_prices = request.form.getlist('hotel_price[]')
        hotel_packages = []
        for t, p in zip(hotel_titles, hotel_prices):
            if t.strip() and p.strip():
                try:
                    hotel_packages.append({'title': t.strip(), 'price': float(p.strip())})
                except ValueError:
                    pass
                    
        # Process dynamic travel packages
        travel_titles = request.form.getlist('travel_title[]')
        travel_prices = request.form.getlist('travel_price[]')
        travel_packages = []
        for t, p in zip(travel_titles, travel_prices):
            if t.strip() and p.strip():
                try:
                    travel_packages.append({'title': t.strip(), 'price': float(p.strip())})
                except ValueError:
                    pass

        import os
        from werkzeug.utils import secure_filename
        import uuid
        about_image_path = None
        photo_file = request.files.get('about_image')
        if photo_file and photo_file.filename != '':
            filename = secure_filename(photo_file.filename)
            base, extension = os.path.splitext(filename)
            unique_filename = f"{base}_{uuid.uuid4().hex[:8]}{extension}"
            upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'yatra_images')
            os.makedirs(upload_folder, exist_ok=True)
            photo_file.save(os.path.join(upload_folder, unique_filename))
            about_image_path = f"uploads/yatra_images/{unique_filename}"
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
            
            yatra = YatraDetails(
                title=title,
                starting_date=start_date,
                is_start_fixed=is_start_fixed,
                end_date=end_date,
                is_end_fixed=is_end_fixed,
                hotel_packages=json.dumps(hotel_packages),
                travel_packages=json.dumps(travel_packages),
                about_image=about_image_path,
                yatra_message=yatra_message,
                yatra_link=yatra_link
            )
            db.session.add(yatra)
            db.session.commit()
            
            # Create a dedicated table for this Yatra
            from sqlalchemy import text
            tname = sanitize_table_name(title)
            if _is_postgres():
                db.session.execute(text(f'''
                    CREATE TABLE IF NOT EXISTS {tname} (
                        id SERIAL PRIMARY KEY,
                        login_id TEXT,
                        name TEXT,
                        year_of_birth INTEGER,
                        email TEXT,
                        phone TEXT,
                        gender TEXT,
                        city TEXT,
                        district TEXT,
                        state TEXT,
                        hotel_package TEXT,
                        travel_package TEXT,
                        start_date TEXT,
                        end_date TEXT,
                        status TEXT DEFAULT 'Interest',
                        razorpay_id TEXT,
                        passenger_id INTEGER,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                '''))
            else:
                db.session.execute(text(f'''
                    CREATE TABLE IF NOT EXISTS {tname} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        login_id TEXT,
                        name TEXT,
                        year_of_birth INTEGER,
                        email TEXT,
                        phone TEXT,
                        gender TEXT,
                        city TEXT,
                        district TEXT,
                        state TEXT,
                        hotel_package TEXT,
                        travel_package TEXT,
                        start_date TEXT,
                        end_date TEXT,
                        status TEXT DEFAULT 'Interest',
                        razorpay_id TEXT,
                        passenger_id INTEGER,
                        created_at TEXT DEFAULT (datetime('now', 'localtime'))
                    )
                '''))
            db.session.commit()
            
            flash(f'New Yatra "{title}" created successfully with its dedicated table!', 'success')
            return redirect(url_for('admin_dashboard', table=tname))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating Yatra: {str(e)}', 'error')
            
    return render_template('admin_manage_yatra.html')

@app.route('/admin/edit-yatra/<int:yatra_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_yatra(yatra_id):
    """Admin route to edit an existing Yatra details"""
    yatra = YatraDetails.query.get_or_404(yatra_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        start_date_str = request.form.get('starting_date')
        is_start_fixed = 'is_start_fixed' in request.form
        end_date_str = request.form.get('end_date')
        is_end_fixed = 'is_end_fixed' in request.form
        yatra_message = request.form.get('yatra_message')
        yatra_link = request.form.get('yatra_link')
        
        # Process dynamic hotel packages
        hotel_titles = request.form.getlist('hotel_title[]')
        hotel_prices = request.form.getlist('hotel_price[]')
        hotel_packages = []
        for t, p in zip(hotel_titles, hotel_prices):
            if t.strip() and p.strip():
                try:
                    hotel_packages.append({'title': t.strip(), 'price': float(p.strip())})
                except ValueError:
                    pass
                    
        # Process dynamic travel packages
        travel_titles = request.form.getlist('travel_title[]')
        travel_prices = request.form.getlist('travel_price[]')
        travel_packages = []
        for t, p in zip(travel_titles, travel_prices):
            if t.strip() and p.strip():
                try:
                    travel_packages.append({'title': t.strip(), 'price': float(p.strip())})
                except ValueError:
                    pass
        
        try:
            old_title = yatra.title
            
            yatra.title = title
            yatra.starting_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            yatra.is_start_fixed = is_start_fixed
            yatra.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
            yatra.is_end_fixed = is_end_fixed
            yatra.hotel_packages = json.dumps(hotel_packages)
            yatra.travel_packages = json.dumps(travel_packages)
            yatra.yatra_message = yatra_message
            yatra.yatra_link = yatra_link
            
            import os
            from werkzeug.utils import secure_filename
            import uuid
            photo_file = request.files.get('about_image')
            if photo_file and photo_file.filename != '':
                filename = secure_filename(photo_file.filename)
                base, extension = os.path.splitext(filename)
                unique_filename = f"{base}_{uuid.uuid4().hex[:8]}{extension}"
                upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'yatra_images')
                os.makedirs(upload_folder, exist_ok=True)
                
                import os
                if yatra.about_image:
                    old_path = os.path.join(app.root_path, 'static', yatra.about_image)
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except Exception:
                            pass
                
                photo_file.save(os.path.join(upload_folder, unique_filename))
                yatra.about_image = f"uploads/yatra_images/{unique_filename}"
            
            db.session.commit()
            
            # Optionally, rename the associated table if title changed (SQLite does support RENAME TABLE)
            if old_title != title:
                old_tname = sanitize_table_name(old_title)
                new_tname = sanitize_table_name(title)
                if old_tname != new_tname:
                    from sqlalchemy import text
                    if _table_exists(old_tname):
                        db.session.execute(text(f"ALTER TABLE {old_tname} RENAME TO {new_tname}"))
                        db.session.commit()

            flash(f'Yatra "{title}" updated successfully!', 'success')
            return redirect(url_for('admin_dashboard', table='yatra_details'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating Yatra: {str(e)}', 'error')
            
    try:
        hotel_packages_list = json.loads(yatra.hotel_packages) if yatra.hotel_packages and yatra.hotel_packages != 'null' else []
    except Exception:
        hotel_packages_list = []
        
    try:
        travel_packages_list = json.loads(yatra.travel_packages) if yatra.travel_packages and yatra.travel_packages != 'null' else []
    except Exception:
        travel_packages_list = []
        
    return render_template('admin_edit_yatra.html', yatra=yatra, hotel_packages=hotel_packages_list, travel_packages=travel_packages_list)



@app.route('/admin/update-record', methods=['POST'])
@login_required
def admin_update_record():
    """Update a record in the specified table — returns JSON for AJAX calls."""
    record_id = request.form.get('record_id')
    table_name = request.form.get('table_name')

    if not record_id or not table_name:
        return jsonify({'success': False, 'message': 'Invalid data provided.'})

    try:
        if table_name == 'passengers':
            record = LoginDetails.query.get(record_id)
            if not record:
                return jsonify({'success': False, 'message': 'Passenger record not found.'})

            mapping = {
                'Login ID (Verified Phone)': 'login_id',
                'Name': 'name',
                'Aadhar No': 'aadhar',
                'Year of Birth': 'year_of_birth',
                'Phone': 'phone',
                'Email': 'email',
                'City': 'city',
                'District': 'district',
                'State': 'state'
            }

            for form_key, model_attr in mapping.items():
                if form_key in request.form:
                    val = request.form.get(form_key)
                    if model_attr == 'year_of_birth':
                        try:
                            val = int(val) if val and str(val).strip().isdigit() else 0
                        except ValueError:
                            val = 0
                    setattr(record, model_attr, val)

            db.session.commit()

            updated = {
                'Login ID (Verified Phone)': record.login_id or '-',
                'Name': record.name or '-',
                'Aadhar No': record.aadhar or '-',
                'Year of Birth': str(record.year_of_birth) if record.year_of_birth else '-',
                'Phone': record.phone or '-',
                'Email': record.email or '-',
                'City': record.city or '-',
                'District': record.district or '-',
                'State': record.state or '-',
            }
            return jsonify({'success': True, 'message': 'Passenger record updated successfully!', 'updated_values': updated})

        elif table_name == 'yatra_details':
            return jsonify({'success': False, 'message': 'Please use the dedicated edit page for Yatra Details.'})

        else:
            if not _is_valid_table(table_name):
                return jsonify({'success': False, 'message': 'Invalid table name.'})

            mapping = {
                'Login ID': 'login_id',
                'Name': 'name',
                'Year of Birth': 'year_of_birth',
                'Email': 'email',
                'Phone': 'phone',
                'Gender': 'gender',
                'City': 'city',
                'District': 'district',
                'State': 'state',
                'Hotel Package': 'hotel_package',
                'Travel Package': 'travel_package',
                'Start Date': 'start_date',
                'End Date': 'end_date',
                'Status': 'status',
                'RazorPay ID': 'razorpay_id'
            }

            update_parts = []
            update_values = {'id': record_id}
            updated = {}

            for form_key, col_name in mapping.items():
                if form_key in request.form:
                    val = request.form.get(form_key)
                    update_parts.append(f"{col_name} = :{col_name}")
                    update_values[col_name] = val
                    updated[form_key] = val or '-'

            if update_parts:
                from sqlalchemy import text
                query = text(f"UPDATE {table_name} SET {', '.join(update_parts)} WHERE id = :id")
                db.session.execute(query, update_values)
                db.session.commit()
                return jsonify({'success': True, 'message': 'Record updated successfully!', 'updated_values': updated})
            return jsonify({'success': False, 'message': 'Nothing to update.'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating record: {str(e)}'})



@app.route('/admin/delete-record', methods=['POST'])
@login_required
def admin_delete_record():
    """Permanently deletes a record from the specified table"""
    data = request.get_json()
    if not data or 'record_id' not in data or 'table_name' not in data:
        return jsonify({'success': False, 'message': 'Invalid data provided.'})

    table_name = data['table_name']
    record_id = data['record_id']

    try:
        if table_name == 'passengers':
            record = LoginDetails.query.get(record_id)
            if record:
                db.session.delete(record)
                db.session.commit()
                return jsonify({'success': True, 'message': 'Passenger deleted successfully.'})
            return jsonify({'success': False, 'message': 'Passenger not found.'})
            
        elif table_name == 'yatra_details':
            record = YatraDetails.query.get(record_id)
            if record:
                title = record.title
                image_path = record.about_image
                db.session.delete(record)
                db.session.commit()
                
                # Optionally drop the associated dynamic table
                tname = sanitize_table_name(title)
                from sqlalchemy import text
                db.session.execute(text(f"DROP TABLE IF EXISTS {tname}"))
                db.session.commit()
                
                # Delete the physical image from filesystem if it exists
                if image_path:
                    import os
                    full_image_path = os.path.join(app.root_path, 'static', image_path)
                    if os.path.exists(full_image_path):
                        os.remove(full_image_path)
                
                return jsonify({'success': True, 'message': 'Yatra deleted successfully.'})
            return jsonify({'success': False, 'message': 'Yatra not found.'})
            
        else:
            # Strict whitelist via _is_valid_table — prevents SQL injection
            if not _is_valid_table(table_name):
                return jsonify({'success': False, 'message': 'Invalid table name.'})
            from sqlalchemy import text
            db.session.execute(text(f"DELETE FROM {table_name} WHERE id = :id"), {'id': record_id})
            db.session.commit()
            return jsonify({'success': True, 'message': 'Record deleted successfully.'})
                
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/delete-yatra-table/<table_name>', methods=['POST'])
@login_required
def admin_delete_yatra_table(table_name):
    """Drop a specific dynamic Yatra table from the database"""
    from sqlalchemy import text
    # Strict whitelist prevents SQL injection in DROP TABLE
    if not _is_valid_table(table_name):
        flash('Invalid table name. Cannot delete.', 'error')
        return redirect(url_for('admin_dashboard'))
    try:
        db.session.execute(text(f'DROP TABLE IF EXISTS {table_name}'))
        db.session.commit()
        flash(f'Table "{table_name}" deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting table: {str(e)}', 'error')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/toggle-yatra/<int:yatra_id>', methods=['POST'])
@login_required
def admin_toggle_yatra(yatra_id):
    """Toggle a Yatra's is_active status (AJAX)"""
    yatra = YatraDetails.query.get_or_404(yatra_id)
    yatra.is_active = not yatra.is_active
    db.session.commit()
    return jsonify({'success': True, 'is_active': yatra.is_active})


@app.route('/admin/export/excel')
@login_required
def export_excel():
    """Export data to Excel (admin only)"""
    import pandas as pd
    import io

    table_type = request.args.get('table', 'passengers')
    data = []
    filename = "export.xlsx"

    try:
        if table_type == 'passengers':
            passengers = LoginDetails.query.order_by(LoginDetails.created_at.desc()).all()
            for p in passengers:
                data.append({
                    'Login ID': p.login_id,
                    'Name': p.name,
                    'Aadhar No': p.aadhar or '',
                    'Year of Birth': p.year_of_birth,
                    'Gender': p.gender or '',
                    'Phone': p.phone or '',
                    'Email': p.email or '',
                    'City': p.city or '',
                    'District': p.district or '',
                    'State': p.state or '',
                    'Created At': p.created_at.strftime('%Y-%m-%d %H:%M') if p.created_at else ''
                })
            filename = "passengers.xlsx"

        elif table_type == 'yatra_details':
            items = YatraDetails.query.order_by(YatraDetails.created_at.desc()).all()
            for item in items:
                data.append({
                    'ID': item.id,
                    'Title': item.title,
                    'Starting Date': item.starting_date.strftime('%Y-%m-%d') if item.starting_date else '',
                    'Fixed Start': 'Yes' if item.is_start_fixed else 'No',
                    'End Date': item.end_date.strftime('%Y-%m-%d') if item.end_date else '',
                    'Fixed End': 'Yes' if item.is_end_fixed else 'No',
                    'Hotel Packages': item.hotel_packages or '',
                    'Travel Packages': item.travel_packages or '',
                    'Message': item.yatra_message or '',
                    'Link': item.yatra_link or '',
                    'Created At': item.created_at.strftime('%Y-%m-%d %H:%M') if item.created_at else ''
                })
            filename = "yatra_details.xlsx"

        else: # dynamic yatra table — validate before any SQL
            if not _is_valid_table(table_type):
                flash('Invalid table name.', 'error')
                return redirect(url_for('admin_dashboard'))
            from sqlalchemy import text
            query = f"""
                SELECT id, login_id, name, year_of_birth, email, phone, gender,
                       city, district, state, hotel_package, travel_package,
                       start_date, end_date, status, razorpay_id, order_id, created_at
                FROM {table_type} ORDER BY created_at DESC
            """
            rows = db.session.execute(text(query)).fetchall()
            for row in rows:
                data.append({
                    'Order ID': row[16],
                    'ID': row[0],
                    'Login ID': row[1],
                    'Name': row[2],
                    'Year of Birth': row[3],
                    'Email': row[4],
                    'Phone': row[5],
                    'Gender': row[6],
                    'City': row[7],
                    'District': row[8],
                    'State': row[9],
                    'Hotel Package': row[10],
                    'Travel Package': row[11],
                    'Start Date': row[12],
                    'End Date': row[13],
                    'Status': row[14],
                    'Razorpay ID': row[15],
                    'Created At': row[17],
                })
            filename = f"{table_type}_export.xlsx"

        if not data:
            flash('No data to export', 'warning')
            return redirect(url_for('admin_dashboard', table=table_type))

        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Data')
        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        flash(f'Error exporting to Excel: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard', table=table_type))



@app.route('/admin/export/csv')
@login_required
def export_csv():
    """Export data to CSV (admin only)"""
    import pandas as pd
    import io
    
    table_type = request.args.get('table', 'passengers')
    data = []
    filename = "export.csv"

    try:
        if table_type == 'passengers':
            passengers = LoginDetails.query.order_by(LoginDetails.created_at.desc()).all()
            for p in passengers:
                data.append({
                    'Login ID': p.login_id,
                    'Name': p.name,
                    'Aadhar No': p.aadhar or '',
                    'Year of Birth': p.year_of_birth,
                    'Gender': p.gender or '',
                    'Phone': p.phone or '',
                    'Email': p.email or '',
                    'City': p.city or '',
                    'District': p.district or '',
                    'State': p.state or '',
                    'Created At': p.created_at.strftime('%Y-%m-%d %H:%M') if p.created_at else ''
                })
            filename = "passengers.csv"

        elif table_type == 'yatra_details':
            items = YatraDetails.query.order_by(YatraDetails.created_at.desc()).all()
            for item in items:
                data.append({
                    'ID': item.id,
                    'Title': item.title,
                    'Starting Date': item.starting_date.strftime('%Y-%m-%d') if item.starting_date else '',
                    'Fixed Start': 'Yes' if item.is_start_fixed else 'No',
                    'End Date': item.end_date.strftime('%Y-%m-%d') if item.end_date else '',
                    'Fixed End': 'Yes' if item.is_end_fixed else 'No',
                    'Hotel Packages': item.hotel_packages or '',
                    'Travel Packages': item.travel_packages or '',
                    'Message': item.yatra_message or '',
                    'Link': item.yatra_link or '',
                    'Created At': item.created_at.strftime('%Y-%m-%d %H:%M') if item.created_at else ''
                })
            filename = "yatra_details.csv"

        else: # dynamic yatra table — validate before any SQL
            if not _is_valid_table(table_type):
                flash('Invalid table name.', 'error')
                return redirect(url_for('admin_dashboard'))
            from sqlalchemy import text
            query = f"""
                SELECT id, login_id, name, year_of_birth, email, phone, gender,
                       city, district, state, hotel_package, travel_package,
                       start_date, end_date, status, razorpay_id, order_id, created_at
                FROM {table_type} ORDER BY created_at DESC
            """
            rows = db.session.execute(text(query)).fetchall()
            for row in rows:
                data.append({
                    'Order ID': row[16],
                    'ID': row[0],
                    'Login ID': row[1],
                    'Name': row[2],
                    'Year of Birth': row[3],
                    'Email': row[4],
                    'Phone': row[5],
                    'Gender': row[6],
                    'City': row[7],
                    'District': row[8],
                    'State': row[9],
                    'Hotel Package': row[10],
                    'Travel Package': row[11],
                    'Start Date': row[12],
                    'End Date': row[13],
                    'Status': row[14],
                    'Razorpay ID': row[15],
                    'Created At': row[17],
                })
            filename = f"{table_type}_export.csv"

        if not data:
            flash('No data to export', 'warning')
            return redirect(url_for('admin_dashboard', table=table_type))

        df = pd.DataFrame(data)
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        flash(f'Error exporting to CSV: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard', table=table_type))


@app.route('/admin/create-registration', methods=['GET', 'POST'])
@login_required
def admin_create_registration():
    """Admin: Create a new registration for a specific (titled) Yatra.
    Inserts into login_details (if phone not already pre-existing for this name)
    AND into the selected Yatra's dedicated dynamic table."""
    from sqlalchemy import text

    yatras = YatraDetails.query.order_by(YatraDetails.created_at.desc()).all()

    if request.method == 'POST':
        yatra_id    = request.form.get('yatra_id')
        name        = request.form.get('name', '').strip()
        phone       = request.form.get('phone', '').strip()
        alt_phone   = request.form.get('alternative_phone', '').strip()
        email       = request.form.get('email', '').strip()
        aadhar      = request.form.get('aadhar', '').strip()
        yob         = request.form.get('year_of_birth', '').strip()
        gender      = request.form.get('gender', '').strip()
        city        = request.form.get('city', '').strip()
        district    = request.form.get('district', '').strip()
        state       = request.form.get('state', '').strip()
        hotel_pkg   = request.form.get('hotel_category', '').strip()
        travel_pkg  = request.form.get('travel_medium', '').strip()
        start_date  = request.form.get('journey_start_date', '').strip()
        end_date    = request.form.get('journey_end_date', '').strip()
        base_amount = request.form.get('base_amount', '0')
        discount    = request.form.get('custom_discount', '0')
        pay_status  = request.form.get('payment_status', 'Paid')
        payment_id  = request.form.get('razorpay_payment_id', '').strip()

        # Basic validation
        if not yatra_id or not name or not phone:
            flash('Yatra, Full Name and Phone are required.', 'error')
            return render_template('admin_create_registration.html', yatras=yatras)

        # Normalize phone to +91XXXXXXXXXX
        norm_phone, phone_err = normalize_phone(phone)
        if phone_err:
            flash(phone_err, 'error')
            return render_template('admin_create_registration.html', yatras=yatras)

        # Validate Aadhar
        if aadhar and (not aadhar.isdigit() or len(aadhar) != 12):
            flash('Aadhar number must be exactly 12 digits.', 'error')
            return render_template('admin_create_registration.html', yatras=yatras)

        yob_int = int(yob) if yob and yob.isdigit() else 0

        # Try final amount calculation
        try:
            base_f = float(base_amount)
            disc_f = float(discount)
            final_amount = base_f * (1 - disc_f / 100)
        except Exception:
            final_amount = 0.0

        # Generate razorpay IDs if blank
        if not payment_id:
            payment_id = f"admin_pay_{uuid.uuid4().hex[:10]}"

        try:
            yatra = YatraDetails.query.get(int(yatra_id))
            if not yatra:
                flash('Selected Yatra not found.', 'error')
                return render_template('admin_create_registration.html', yatras=yatras)

            # ── 1. Upsert into login_details ──
            existing = LoginDetails.query.filter_by(
                login_id=norm_phone, name=name
            ).first()
            if existing:
                # Update details
                existing.aadhar       = aadhar or existing.aadhar
                existing.year_of_birth= yob_int or existing.year_of_birth
                existing.gender       = gender or existing.gender
                existing.email        = email or existing.email
                existing.phone        = alt_phone or existing.phone
                existing.city         = city or existing.city
                existing.district     = district or existing.district
                existing.state        = state or existing.state
            else:
                new_login = LoginDetails(
                    login_id=norm_phone,
                    name=name,
                    aadhar=aadhar,
                    year_of_birth=yob_int,
                    gender=gender,
                    email=email,
                    phone=alt_phone,
                    city=city,
                    district=district,
                    state=state
                )
                db.session.add(new_login)
            db.session.flush()
            p_id = existing.id if existing else new_login.id

            # ── 2. Insert into Yatra's dynamic table ──
            tname = sanitize_table_name(yatra.title)
            tbl_exists = _table_exists(tname)

            if tbl_exists:
                # Remove any existing entry for this phone+name combo in this yatra
                db.session.execute(
                    text(f"DELETE FROM {tname} WHERE passenger_id=:pid OR (passenger_id IS NULL AND login_id=:lid AND name=:nm)"),
                    {'pid': p_id, 'lid': norm_phone, 'nm': name}
                )
                db.session.execute(text(f"""
                    INSERT INTO {tname}
                        (login_id, passenger_id, name, year_of_birth, email, phone, gender,
                         city, district, state, hotel_package, travel_package,
                         start_date, end_date, status, razorpay_id)
                    VALUES
                        (:login_id, :passenger_id, :name, :yob, :email, :phone, :gender,
                         :city, :district, :state, :hotel_pkg, :travel_pkg,
                         :start_date, :end_date, :status, :rzp_id)
                """), {
                    'login_id':   norm_phone,
                    'passenger_id': p_id,
                    'name':       name,
                    'yob':        yob_int,
                    'email':      email,
                    'phone':      alt_phone or norm_phone,
                    'gender':     gender,
                    'city':       city,
                    'district':   district,
                    'state':      state,
                    'hotel_pkg':  hotel_pkg,
                    'travel_pkg': travel_pkg,
                    'start_date': start_date,
                    'end_date':   end_date,
                    'status':     pay_status,
                    'rzp_id':     payment_id,
                })

            db.session.commit()
            flash(f'✅ Registration for "{name}" in "{yatra.title}" created successfully! Final Amount: ₹{final_amount:.2f}', 'success')
            return redirect(url_for('admin_dashboard', table=tname))

        except Exception as e:
            db.session.rollback()
            app_logger.error(f"Admin create registration error: {e}", exc_info=True)
            flash(f'Error creating registration: {str(e)}', 'error')

    return render_template('admin_create_registration.html', yatras=yatras)


if __name__ == '__main__':
    # debug mode is controlled by FLASK_DEBUG in .env (default: off)
    _debug = os.getenv('FLASK_DEBUG', 'False').strip().lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=5000, debug=_debug)
