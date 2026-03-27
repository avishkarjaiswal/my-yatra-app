from app import app, db, AppSettings
with app.app_context():
    setting = AppSettings.query.filter_by(key='recent_yatra_youtube').first()
    if setting and 'youtu.be' in setting.value:
        video_id = setting.value.split('youtu.be/')[1].split('?')[0]
        setting.value = 'https://www.youtube.com/embed/' + video_id
        db.session.commit()
        print('Fixed to:', setting.value)
