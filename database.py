import sqlite3

# Nama fail database
DB_NAME = "bisnes.db"

def init_db():
    # Sambung ke database. Jika fail tak wujud, ia akan dicipta
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Jadual untuk Maklumat Pelanggan
    c.execute('''
        CREATE TABLE IF NOT EXISTS pelanggan (
            id INTEGER PRIMARY KEY,
            nama TEXT NOT NULL,
            telefon TEXT,
            emel TEXT,
            alamat TEXT
        )
    ''')

    # Jadual untuk Prospek Jualan
    c.execute('''
        CREATE TABLE IF NOT EXISTS prospek_jualan (
            id INTEGER PRIMARY KEY,
            nama TEXT NOT NULL,
            status TEXT NOT NULL,
            catatan TEXT,
            jurujual_id INTEGER,
            FOREIGN KEY (jurujual_id) REFERENCES pengguna(id)
        )
    ''')

    # Jadual untuk Pengguna (Ahli Pasukan)
    c.execute('''
        CREATE TABLE IF NOT EXISTS pengguna (
            id INTEGER PRIMARY KEY,
            nama TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            peranan TEXT NOT NULL -- admin, sales, dsb.
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print(f"Pangkalan data '{DB_NAME}' dan jadual-jadualnya berjaya dicipta.")