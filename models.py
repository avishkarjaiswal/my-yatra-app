from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

db = SQLAlchemy()

# Utility function to get India time (IST = UTC+5:30)
def get_india_time():
    """Returns current time in India Standard Time (IST)"""
    utc_now = datetime.utcnow()
    ist_offset = timedelta(hours=5, minutes=30)
    return utc_now + ist_offset

class LoginDetails(db.Model):
    """Stores traveler details linked to a verified phone number"""
    __tablename__ = 'login_details'
    id = db.Column(db.Integer, primary_key=True)
    login_id = db.Column(db.String(20), nullable=False) # The phone number used for login
    photo = db.Column(db.String(255), nullable=True) # file path or string
    name = db.Column(db.String(100), nullable=False)
    aadhar = db.Column(db.String(20), nullable=True)
    year_of_birth = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    district = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=get_india_time)

class YatraDetails(db.Model):
    """Stores the created Yatras by Admin"""
    __tablename__ = 'yatra_details'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    starting_date = db.Column(db.Date, nullable=True)
    is_start_fixed = db.Column(db.Boolean, default=True)
    end_date = db.Column(db.Date, nullable=True)
    is_end_fixed = db.Column(db.Boolean, default=True)
    hotel_packages = db.Column(db.Text, nullable=True) # store JSON array of strings
    travel_packages = db.Column(db.Text, nullable=True) # store JSON array of strings
    is_active = db.Column(db.Boolean, default=True)  # Controls visibility on passenger dashboard
    created_at = db.Column(db.DateTime, default=get_india_time)
    about_image = db.Column(db.String(255), nullable=True) # Attached image for details
    yatra_message = db.Column(db.Text, nullable=True) # Message for passengers
    yatra_link = db.Column(db.String(500), nullable=True) # External link for passengers

class CarouselImage(db.Model):
    __tablename__ = 'carousel_images'
    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=get_india_time)
    sort_order = db.Column(db.Integer, default=0)

class AppSettings(db.Model):
    """Stores global application settings like Registration Closed title and description"""
    __tablename__ = 'app_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
