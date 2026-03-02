import sqlite3

# Connect to the database
conn = sqlite3.connect('instance/qcm.db')
cursor = conn.cursor()

try:
    # Add new column time_per_question
    cursor.execute("ALTER TABLE quiz ADD COLUMN time_per_question INTEGER DEFAULT 30")
    conn.commit()
    print("Migration successful: Added time_per_question column.")
except sqlite3.OperationalError as e:
    print(f"Migration skipped or failed: {e}")

conn.close()
