"""
Application settings manager for Dwarka Yatra
Stores configuration like registration status in a JSON file
"""
import json
import os
from pathlib import Path

SETTINGS_FILE = Path(__file__).parent / 'app_settings.json'

# Default settings
DEFAULT_SETTINGS = {
    'registration_enabled': True,
    'registration_closed_message': 'Thank you for showing your interest. Registration has been closed. For more information please contact our team.'
}

def get_settings():
    """Load settings from JSON file"""
    if not SETTINGS_FILE.exists():
        # Create default settings file
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading settings: {e}")
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Save settings to JSON file"""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False

def get_setting(key, default=None):
    """Get a specific setting value"""
    settings = get_settings()
    return settings.get(key, default)

def update_setting(key, value):
    """Update a specific setting"""
    settings = get_settings()
    settings[key] = value
    return save_settings(settings)

def is_registration_enabled():
    """Check if registration is currently enabled"""
    return get_setting('registration_enabled', True)
