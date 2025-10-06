# migrate_add_user_target_column.py
import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_NAME = os.path.join(BASE_DIR, "bisnes.db")

def migrate():
    """Menambah lajur 'target_jualan' ke dalam jadual 'pengguna'."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        print("Berjaya disambungkan ke pangkalan data.")

        # Tambah lajur baru dengan nilai lalai 0
        c.execute('ALTER TABLE pengguna ADD COLUMN target_jualan REAL DEFAULT 0')
        
        conn.commit()
        print("Berjaya! Lajur 'target_jualan' telah ditambah ke dalam jadual 'pengguna'.")

    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Info: Lajur 'target_jualan' sudah wujud. Tiada perubahan dibuat.")
        else:
            print(f"Ralat berlaku: {e}")
    
    finally:
        if conn:
            conn.close()
            print("Sambungan ke pangkalan data ditutup.")

if __name__ == '__main__':
    migrate()