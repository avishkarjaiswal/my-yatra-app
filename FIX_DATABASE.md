# Fixing the Database Schema Error

## The Problem
The error `table user has no column named yatra_class` occurs because:

1. **You updated the Model** (`models.py`) to include `yatra_class` field
2. **The Database Already Exists** with the old schema (without `yatra_class`)
3. **SQLAlchemy's `db.create_all()` doesn't alter existing tables** - it only creates NEW tables

## Why SQLite Doesn't Auto-Update Schemas

SQLAlchemy's `db.create_all()` is designed to be **safe** and **non-destructive**:
- It checks if a table exists
- If it exists, it does **nothing** (won't add/remove/modify columns)
- If it doesn't exist, it creates the table

This is intentional to prevent data loss. To modify existing tables, you need:
- **Manual SQL ALTER statements**, OR
- **Database migrations** (using Flask-Migrate/Alembic), OR
- **Delete and recreate** the database (acceptable for development)

## Solution

### Step 1: Stop the Flask Server
In the terminal where Flask is running, press `Ctrl+C` to stop it.

### Step 2: Delete the Old Database
Run the command I've proposed above to delete `instance/yatra.db`.

### Step 3: Restart Flask
```bash
python app.py
```

Flask will automatically create a fresh database with the new schema including the `yatra_class` column.

### Step 4: Test
Visit `http://127.0.0.1:5000/register` and you should now see the package selection.

## For Production
For production databases with real data, you should use **Flask-Migrate**:
```bash
pip install Flask-Migrate
# Initialize migrations
flask db init
flask db migrate -m "Add yatra_class column"
flask db upgrade
```
This preserves existing data while updating the schema.
