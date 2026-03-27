from app import app, db, AppSettings
with app.app_context():
    print(AppSettings.query.filter_by(key='recent_yatra_youtube').first().value)
