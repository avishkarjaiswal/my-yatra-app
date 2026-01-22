from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

db = SQLAlchemy()

# Utility function to get India time (IST = UTC+5:30)
def get_india_time():
    """Returns current time in India Standard Time (IST)"""
    utc_now = datetime.utcnow()
    ist_offset = timedelta(hours=5, minutes=30)
    return utc_now + ist_offset

class PassengerInsider(db.Model):
    """Represents a traveler who has OTM (One Time Membership)"""
    __tablename__ = 'passenger_insider'
    id = db.Column(db.Integer, primary_key=True)
    
    # Personal Details
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    alternative_phone = db.Column(db.String(20), nullable=True)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    city = db.Column(db.String(100), nullable=True)
    district = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)

    # Package Details - Dynamic Components
    journey_start_date = db.Column(db.Date, nullable=True)
    journey_end_date = db.Column(db.Date, nullable=True)
    num_days = db.Column(db.Integer, nullable=True)
    hotel_category = db.Column(db.String(20), nullable=True)  # basic, standard, premium
    travel_medium = db.Column(db.String(20), nullable=True)  # self, train, flight
    has_otm = db.Column(db.Boolean, default=True)  # Always True for insiders
    otm_id = db.Column(db.String(50), nullable=False)  # Required for insiders
    
    # Legacy field (kept for backward compatibility)
    yatra_class = db.Column(db.String(20), nullable=True, default='Standard')
    
    # Payment Details
    razorpay_order_id = db.Column(db.String(100), unique=True, nullable=False)
    razorpay_payment_id = db.Column(db.String(100), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), default='Pending')  # Pending, Paid, Failed
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=get_india_time)
    
    def __repr__(self):
        return f'<PassengerInsider {self.name} - OTM: {self.otm_id}>'

class PassengerOutsider(db.Model):
    """Represents a traveler who does not have OTM (One Time Membership)"""
    __tablename__ = 'passenger_outsider'
    id = db.Column(db.Integer, primary_key=True)
    
    # Personal Details
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    alternative_phone = db.Column(db.String(20), nullable=True)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    city = db.Column(db.String(100), nullable=True)
    district = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)

    # Package Details - Dynamic Components
    journey_start_date = db.Column(db.Date, nullable=True)
    journey_end_date = db.Column(db.Date, nullable=True)
    num_days = db.Column(db.Integer, nullable=True)
    hotel_category = db.Column(db.String(20), nullable=True)  # basic, standard, premium
    travel_medium = db.Column(db.String(20), nullable=True)  # self, train, flight
    has_otm = db.Column(db.Boolean, default=False)  # Always False for outsiders
    otm_id = db.Column(db.String(50), nullable=True)  # Not applicable for outsiders
    
    # Legacy field (kept for backward compatibility)
    yatra_class = db.Column(db.String(20), nullable=True, default='Standard')
    
    # Payment Details
    razorpay_order_id = db.Column(db.String(100), unique=True, nullable=False)
    razorpay_payment_id = db.Column(db.String(100), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), default='Pending')  # Pending, Paid, Failed
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=get_india_time)
    
    def __repr__(self):
        return f'<PassengerOutsider {self.name}>'

class OTMActive(db.Model):
    """Tracks valid/active OTM IDs that can be used"""
    __tablename__ = 'otm_active'
    id = db.Column(db.String(50), primary_key=True)  # OTM ID itself is the primary key
    created_at = db.Column(db.DateTime, default=get_india_time)
    
    def __repr__(self):
        return f'<OTMActive {self.id}>'

class OTMExpired(db.Model):
    """Tracks used/expired OTM IDs"""
    __tablename__ = 'otm_expired'
    id = db.Column(db.String(50), primary_key=True)  # OTM ID itself is the primary key
    used_by_passenger_id = db.Column(db.Integer, nullable=True)  # Reference to passenger who used it
    expired_at = db.Column(db.DateTime, default=get_india_time)
    
    def __repr__(self):
        return f'<OTMExpired {self.id}>'
