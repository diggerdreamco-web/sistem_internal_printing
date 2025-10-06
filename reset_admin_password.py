# reset_admin_password.py
import sqlite3
import os
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_NAME = os.path.join(BASE_DIR, "bisnes.db")

def reset_password():
    """Menetapkan semula kata laluan untuk pengguna 'admin' kepada 'admin123'."""
    
    # Kata laluan baru yang kita nak set
    new_password = 'admin123'
    username_to_reset = 'admin'

    # Hasilkan hash untuk kata laluan baru
    hashed_password = generate_password_hash(new_password)
    
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        print(f"Berjaya disambungkan ke pangkalan data '{DB_NAME}'.")

        # Kemas kini kata laluan dalam jadual pengguna
        c.execute("UPDATE pengguna SET password = ? WHERE username = ?", (hashed_password, username_to_reset))
        
        # Periksa jika ada baris yang terjejas (bermakna pengguna 'admin' wujud)
        if c.rowcount > 0:
            conn.commit()
            print(f"Berjaya! Kata laluan untuk pengguna '{username_to_reset}' telah ditetapkan semula kepada '{new_password}'.")
        else:
            print(f"Ralat: Pengguna dengan username '{username_to_reset}' tidak ditemui.")

    except Exception as e:
        print(f"Satu ralat telah berlaku: {e}")
    
    finally:
        if conn:
            conn.close()
            print("Sambungan ke pangkalan data ditutup.")

if __name__ == '__main__':
    reset_password()