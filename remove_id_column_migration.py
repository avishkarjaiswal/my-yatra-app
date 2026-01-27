from app import app, db, PassengerInsider, PassengerOutsider
from sqlalchemy import text

def migrate():
    with app.app_context():
        tables = ['passenger_insider', 'passenger_outsider']
        
        for table in tables:
            print(f"Migrating {table}...")
            
            # Check if table exists
            try:
                db.session.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
            except:
                print(f"Table {table} does not exist, skipping.")
                continue

            # 1. Rename existing table
            try:
                db.session.execute(text(f"ALTER TABLE {table} RENAME TO {table}_old"))
                print(f"Renamed {table} to {table}_old")
            except Exception as e:
                print(f"Error renaming {table}: {e}")
                continue
                
            # 2. Create new table from model (which now has no ID column)
            # db.create_all() will create the table because it doesn't exist (we renamed it)
            db.create_all()
            print(f"Created new {table} schema")
            
            # 3. Copy data
            # Get columns from old table to construct the SELECT statement
            result = db.session.execute(text(f"PRAGMA table_info({table}_old)"))
            # Row format: (cid, name, type, notnull, dflt_value, pk)
            # Filter out 'id'
            columns = [row[1] for row in result if row[1] != 'id']
            cols_str = ", ".join(columns)
            
            print(f"Copying data for columns: {cols_str}")
            
            try:
                db.session.execute(text(f"INSERT INTO {table} ({cols_str}) SELECT {cols_str} FROM {table}_old"))
                print(f"Data copied successfully for {table}")
            except Exception as e:
                print(f"Error copying data: {e}")
                # Restore
                db.session.execute(text(f"DROP TABLE {table}"))
                db.session.execute(text(f"ALTER TABLE {table}_old RENAME TO {table}"))
                print("Rolled back.")
                continue
            
            # 4. Drop old table
            db.session.execute(text(f"DROP TABLE {table}_old"))
            print(f"Dropped {table}_old")

        db.session.commit()
        print("Migration complete.")

if __name__ == "__main__":
    migrate()
