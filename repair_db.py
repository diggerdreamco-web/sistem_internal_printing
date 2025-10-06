import sqlite3
import os

# Pastikan nama DB sama seperti dalam app.py
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_NAME = os.path.join(BASE_DIR, "bisnes.db")

def tambah_lajur_telefon():
    """
    Fungsi ini akan menambah lajur 'telefon' ke dalam jadual 'pengguna'
    jika ia belum wujud.
    """
    conn = None
    try:
        # Sambung ke pangkalan data
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        print("Berjaya disambungkan ke pangkalan data.")

        # Arahan SQL untuk menambah lajur baru
        c.execute('ALTER TABLE pengguna ADD COLUMN telefon TEXT')
        
        # Simpan perubahan
        conn.commit()
        print("Berjaya! Lajur 'telefon' telah ditambah ke dalam jadual 'pengguna'.")

    except sqlite3.OperationalError as e:
        # Ralat akan berlaku jika lajur sudah wujud, ini adalah normal.
        if "duplicate column name" in str(e):
            print("Info: Lajur 'telefon' sudah wujud dalam jadual 'pengguna'. Tiada perubahan dibuat.")
        else:
            print(f"Ralat berlaku: {e}")
    
    finally:
        # Tutup sambungan walau apa pun yang terjadi
        if conn:
            conn.close()
            print("Sambungan ke pangkalan data ditutup.")

# Jalankan fungsi apabila skrip ini dieksekusi
if __name__ == '__main__':
    tambah_lajur_telefon()