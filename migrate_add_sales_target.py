# migrate_add_sales_target.py
import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_NAME = os.path.join(BASE_DIR, "bisnes.db")

def migrate():
    """Menambah tetapan 'target_jualan_bulanan' jika belum wujud."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        print("Berjaya disambungkan ke pangkalan data.")

        # Masukkan nilai lalai 10000 jika tetapan ini belum ada lagi
        c.execute("INSERT OR IGNORE INTO tetapan (nama_tetapan, nilai_tetapan) VALUES (?, ?)", 
                  ('target_jualan_bulanan', '10000'))
        
        conn.commit()
        print("Berjaya! Tetapan 'target_jualan_bulanan' telah ditambah/disahkan wujud.")

    except Exception as e:
        print(f"Ralat berlaku: {e}")
    
    finally:
        if conn:
            conn.close()
            print("Sambungan ke pangkalan data ditutup.")

if __name__ == '__main__':
    migrate()