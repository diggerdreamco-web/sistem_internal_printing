import sqlite3
from werkzeug.security import generate_password_hash
import os

print("Skrip ini akan memulakan pangkalan data.")
# Baris input() telah dibuang untuk membolehkan automasi di Render

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_NAME = os.path.join(BASE_DIR, "bisnes.db")

conn = sqlite3.connect(DB_NAME)
c = conn.cursor()

print("Mencipta jadual jika belum wujud...")

# Cipta semua jadual
c.execute("CREATE TABLE IF NOT EXISTS pengguna (id INTEGER PRIMARY KEY, nama TEXT, username TEXT UNIQUE, password TEXT, peranan TEXT, telefon TEXT, target_jualan REAL DEFAULT 0)")
c.execute("CREATE TABLE IF NOT EXISTS stok_bahan (id INTEGER PRIMARY KEY, nama_bahan TEXT UNIQUE, kuantiti INTEGER, unit TEXT, kuantiti_minima INTEGER)")
c.execute('''
    CREATE TABLE IF NOT EXISTS pesanan (
        id INTEGER PRIMARY KEY, nama_pelanggan TEXT, jenis_baju TEXT, saiz TEXT, 
        kuantiti INTEGER, reka_bentuk TEXT, status TEXT, 
        designer_username TEXT, total_kuantiti INTEGER,
        tarikh_masuk TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        fabrik_id INTEGER, harga REAL, dibuat_oleh TEXT,
        FOREIGN KEY (fabrik_id) REFERENCES fabrik (id)
    )''')
c.execute("CREATE TABLE IF NOT EXISTS pelanggan (id INTEGER PRIMARY KEY, nama TEXT, telefon TEXT, email TEXT, alamat TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS design_files (id INTEGER PRIMARY KEY, pesanan_id INTEGER, filename TEXT, FOREIGN KEY (pesanan_id) REFERENCES pesanan (id))")
c.execute("CREATE TABLE IF NOT EXISTS fabrik (id INTEGER PRIMARY KEY, nama_fabrik TEXT NOT NULL UNIQUE)")
c.execute('''
    CREATE TABLE IF NOT EXISTS harga_saiz (
        id INTEGER PRIMARY KEY, fabrik_id INTEGER NOT NULL, saiz TEXT NOT NULL, harga REAL NOT NULL,
        FOREIGN KEY (fabrik_id) REFERENCES fabrik (id))''')
c.execute("""
    CREATE TABLE IF NOT EXISTS tetapan (
        id INTEGER PRIMARY KEY,
        nama_tetapan TEXT NOT NULL UNIQUE,
        nilai_tetapan TEXT
    )
""")
print("Semua jadual telah disahkan wujud.")

# Masukkan data lalai (jika belum ada)
print("Memasukkan data lalai...")
default_settings = [
    ('nama_syarikat', 'PERNIAGAAN BAJU TEKSTIL'),
    ('alamat_syarikat', 'No. 20, Jln Perniagaan, 43000 Kajang, Selangor'),
    ('telefon_syarikat', '03-1234567'),
    ('email_syarikat', 'info@bajutekstil.com'),
    ('target_jualan_bulanan', '10000')
]
c.executemany("INSERT OR IGNORE INTO tetapan (nama_tetapan, nilai_tetapan) VALUES (?, ?)", default_settings)

fabriks = [('Cotton 30s',), ('Microfiber Interlock',), ('Microfiber Eyelet',)]
c.executemany("INSERT OR IGNORE INTO fabrik (nama_fabrik) VALUES (?)", fabriks)

# Masukkan pengguna lalai (jika belum ada)
default_users = [
    ('Admin Utama', 'admin', 'admin123', 'admin'),
    ('Designer Ali', 'design1', 'design123', 'designer'),
    ('Sales Siti', 'sales1', 'sales123', 'sales'),
    ('Production Mutu', 'prod1', 'prod123', 'production')
]

for nama, username, password, peranan in default_users:
    if c.execute("SELECT COUNT(*) FROM pengguna WHERE username = ?", (username,)).fetchone()[0] == 0:
        c.execute("INSERT INTO pengguna (nama, username, password, peranan) VALUES (?, ?, ?, ?)", 
                  (nama, username, generate_password_hash(password), peranan))
        print(f"Pengguna lalai '{username}' dicipta.")

print("Data lalai telah disahkan.")

conn.commit()
conn.close()

print("\nInisialisasi pangkalan data selesai.")