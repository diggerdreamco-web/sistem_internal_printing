# migrate_add_sales_column.py
import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_NAME = os.path.join(BASE_DIR, "bisnes.db")

def migrate():
    """Menambah lajur 'dibuat_oleh' ke dalam jadual 'pesanan'."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        print("Berjaya disambungkan ke pangkalan data.")

        c.execute('ALTER TABLE pesanan ADD COLUMN dibuat_oleh TEXT')
        
        conn.commit()
        print("Berjaya! Lajur 'dibuat_oleh' telah ditambah ke dalam jadual 'pesanan'.")

    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Info: Lajur 'dibuat_oleh' sudah wujud dalam jadual 'pesanan'. Tiada perubahan dibuat.")
        else:
            print(f"Ralat berlaku: {e}")
    
    finally:
        if conn:
            conn.close()
            print("Sambungan ke pangkalan data ditutup.")

if __name__ == '__main__':
    migrate()