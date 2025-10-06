import os
import sqlite3
import io
import zipfile
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, send_from_directory, g, jsonify
from werkzeug.utils import secure_filename
from fpdf import FPDF 
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'kunci_rahsia_default_jika_tiada_env')

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_NAME = os.path.join(BASE_DIR, "bisnes.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'ai', 'psd', 'cdr'} 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_NAME)
        g.db.row_factory = sqlite3.Row  
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'logged_in' not in session or session.get('peranan') not in allowed_roles:
                flash('Akses ditolak.', 'flash-error')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.context_processor
def inject_now():
    return {'now': datetime.now(), 'peranan': session.get('peranan', 'guest')}

@app.context_processor
def inject_notifications():
    notification_count = 0
    if 'logged_in' in session:
        conn = get_db_connection()
        peranan = session.get('peranan')
        username = session.get('username')
        if peranan in ['sales', 'admin']:
            count = conn.execute("SELECT COUNT(id) FROM pesanan WHERE status = 'Baru' AND (designer_username IS NULL OR designer_username = '')").fetchone()[0]
            notification_count = count
        elif peranan == 'designer':
            count = conn.execute("SELECT COUNT(id) FROM pesanan WHERE designer_username = ? AND status = 'Design Dalam Proses'", (username,)).fetchone()[0]
            notification_count = count
    return dict(notification_count=notification_count)

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session:
        peranan = session.get('peranan')
        if peranan == 'admin': return redirect(url_for('dashboard'))
        elif peranan in ['sales', 'production']: return redirect(url_for('urus_pesanan'))
        elif peranan == 'designer': return redirect(url_for('urus_design'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # --- MULA BAHAGIAN DEBUG ---
        print("\n--- CUBAAN LOG MASUK BARU ---")
        print(f"Username dari borang: {username}")
        # --- AKHIR BAHAGIAN DEBUG ---

        conn = get_db_connection()
        pengguna = conn.execute('SELECT * FROM pengguna WHERE username = ?', (username,)).fetchone()
        
        if pengguna:
            # --- MULA BAHAGIAN DEBUG ---
            print("Pengguna ditemui dalam pangkalan data.")
            print(f"Hash kata laluan dari DB: {pengguna['password']}")
            
            is_password_correct = check_password_hash(pengguna['password'], password)
            print(f"Hasil semakan kata laluan: {is_password_correct}")
            # --- AKHIR BAHAGIAN DEBUG ---

            if is_password_correct:
                print("Log masuk BERJAYA.")
                session['logged_in'], session['username'], session['peranan'] = True, pengguna['username'], pengguna['peranan']
                flash(f'Login berjaya! Selamat datang, {pengguna["nama"]}.', 'flash-success')
                if pengguna['peranan'] == 'admin': return redirect(url_for('dashboard'))
                elif pengguna['peranan'] in ['sales', 'production']: return redirect(url_for('urus_pesanan'))
                elif pengguna['peranan'] == 'designer': return redirect(url_for('urus_design'))
            else:
                # --- MULA BAHAGIAN DEBUG ---
                print("Log masuk GAGAL: Kata laluan tidak sepadan.")
                print("--- AKHIR CUBAAN LOG MASUK ---\n")
                # --- AKHIR BAHAGIAN DEBUG ---
                flash('Username atau password salah.', 'flash-error')
        else:
            # --- MULA BAHAGIAN DEBUG ---
            print("Log masuk GAGAL: Username tidak ditemui dalam pangkalan data.")
            print("--- AKHIR CUBAAN LOG MASUK ---\n")
            # --- AKHIR BAHAGIAN DEBUG ---
            flash('Username atau password salah.', 'flash-error')
            
    return render_template('login.html')

@app.route('/dashboard')
@role_required(['admin'])
def dashboard():
    conn = get_db_connection()
    stats = {
        'pesanan_baru': conn.execute("SELECT COUNT(id) FROM pesanan WHERE status = 'Baru'").fetchone()[0],
        'pesanan_proses': conn.execute("SELECT COUNT(id) FROM pesanan WHERE status IN ('Design Dalam Proses', 'Sedia untuk Production', 'Dalam Proses')").fetchone()[0],
        'pesanan_selesai': conn.execute("SELECT COUNT(id) FROM pesanan WHERE status = 'Selesai'").fetchone()[0]
    }
    pesanan_terkini = conn.execute("SELECT * FROM pesanan ORDER BY id DESC LIMIT 5").fetchall()
    stok_rendah = conn.execute("SELECT * FROM stok_bahan WHERE kuantiti <= kuantiti_minima").fetchall()

    start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    query_prestasi = """
        SELECT 
            u.nama,
            u.target_jualan, 
            COUNT(p.id) as jumlah_pesanan,
            SUM(p.harga) as jumlah_jualan
        FROM pengguna u
        LEFT JOIN pesanan p ON u.username = p.dibuat_oleh AND p.tarikh_masuk >= ?
        WHERE u.peranan = 'sales'
        GROUP BY u.username, u.nama, u.target_jualan
        ORDER BY jumlah_jualan DESC
    """
    prestasi_jualan_rows = conn.execute(query_prestasi, (start_of_month,)).fetchall()
    
    prestasi_jualan = []
    for row in prestasi_jualan_rows:
        row_dict = dict(row)
        target = row_dict['target_jualan'] or 0
        jualan = row_dict['jumlah_jualan'] or 0
        peratus = (jualan / target * 100) if target > 0 else 0
        row_dict['peratus_pencapaian'] = peratus
        prestasi_jualan.append(row_dict)

    target_jualan_row = conn.execute("SELECT nilai_tetapan FROM tetapan WHERE nama_tetapan = 'target_jualan_bulanan'").fetchone()
    target_jualan = float(target_jualan_row['nilai_tetapan']) if target_jualan_row else 0.0

    jumlah_jualan_semasa_row = conn.execute("SELECT SUM(harga) as total FROM pesanan WHERE tarikh_masuk >= ?", (start_of_month,)).fetchone()
    jumlah_jualan_semasa = jumlah_jualan_semasa_row['total'] if jumlah_jualan_semasa_row['total'] else 0.0
    
    peratus_kemajuan = (jumlah_jualan_semasa / target_jualan * 100) if target_jualan > 0 else 0

    return render_template('dashboard.html', 
                           username=session['username'], 
                           statistik=stats, 
                           pesanan_terkini=pesanan_terkini, 
                           stok_rendah=stok_rendah,
                           prestasi_jualan=prestasi_jualan,
                           target_jualan=target_jualan,
                           jumlah_jualan_semasa=jumlah_jualan_semasa,
                           peratus_kemajuan=peratus_kemajuan)

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah log keluar.', 'flash-info')
    return redirect(url_for('login'))

@app.route('/tambah_pengguna', methods=['GET', 'POST'])
@role_required(['admin'])
def tambah_pengguna():
    conn = get_db_connection()
    if request.method == 'POST':
        nama, username, telefon, password, peranan = request.form['nama'], request.form['username'], request.form.get('telefon'), request.form['password'], request.form['peranan']
        try:
            conn.execute("INSERT INTO pengguna (nama, username, telefon, password, peranan) VALUES (?, ?, ?, ?, ?)", (nama, username, telefon, generate_password_hash(password), peranan))
            conn.commit()
            flash(f"Pengguna {username} berjaya ditambah.", 'flash-success')
        except sqlite3.IntegrityError:
            flash("Username sudah wujud, sila guna yang lain.", 'flash-error')
        return redirect(url_for('tambah_pengguna'))
    pengguna = conn.execute('SELECT * FROM pengguna').fetchall()
    return render_template('tambah_pengguna.html', pengguna=pengguna)

@app.route('/padam_pengguna/<int:pengguna_id>', methods=['POST'])
@role_required(['admin'])
def padam_pengguna(pengguna_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM pengguna WHERE id = ?', (pengguna_id,))
    conn.commit()
    flash('Pengguna berjaya dipadam!', 'flash-success')
    return redirect(url_for('tambah_pengguna'))

@app.route('/kemaskini_target_jualan', methods=['POST'])
@role_required(['admin'])
def kemaskini_target_jualan():
    conn = get_db_connection()
    try:
        pengguna_id = request.form['pengguna_id']
        target_jualan = request.form['target_jualan']
        
        conn.execute("UPDATE pengguna SET target_jualan = ? WHERE id = ?", (target_jualan, pengguna_id))
        conn.commit()
        flash('Target jualan berjaya dikemaskini.', 'flash-success')
    except Exception as e:
        flash(f'Gagal mengemaskini target: {e}', 'flash-error')
        
    return redirect(url_for('tambah_pengguna'))

@app.route('/get_pengguna_details/<int:pengguna_id>')
@role_required(['admin'])
def get_pengguna_details(pengguna_id):
    conn = get_db_connection()
    pengguna = conn.execute('SELECT * FROM pengguna WHERE id = ?', (pengguna_id,)).fetchone()
    if pengguna is None:
        return jsonify({'error': 'Pengguna tidak ditemui'}), 404
    
    pengguna_dict = dict(pengguna)
    return jsonify(pengguna_dict)

@app.route('/tambah_pesanan', methods=['GET', 'POST'])
@role_required(['admin', 'sales']) 
def tambah_pesanan():
    conn = get_db_connection()
    designers = conn.execute("SELECT username, nama FROM pengguna WHERE peranan = 'designer'").fetchall()
    fabriks = conn.execute("SELECT * FROM fabrik ORDER BY nama_fabrik").fetchall()
    if request.method == 'POST':
        form = request.form
        nama_pelanggan, jenis_baju, keterangan, designer = form.get('nama_pelanggan'), form.get('jenis_baju', ''), form.get('reka_bentuk', '').strip(), form.get('designer_username', '')
        fabrik_id, harga_akhir = form.get('fabrik_id'), form.get('harga_akhir')
        if not nama_pelanggan or not fabrik_id:
            flash('Nama Pelanggan dan Jenis Fabrik wajib diisi.', 'flash-error')
            return redirect(url_for('tambah_pesanan'))
        lists = request.form.getlist
        total_qty, details_list, saiz_summary = 0, [], {}
        for nama, no, saiz in zip(lists('pemain_nama[]'), lists('jersi_no[]'), lists('saiz[]')):
            if saiz.strip():
                total_qty += 1
                details_list.append(f"{nama.strip() or 'N/A'}|{no.strip() or 'N/A'}:{saiz.strip().upper()}")
                saiz_summary[saiz.strip().upper()] = saiz_summary.get(saiz.strip().upper(), 0) + 1
        if total_qty == 0:
            flash('Sila masukkan sekurang-kurangnya satu baris item dengan Saiz.', 'flash-error')
            return redirect(url_for('tambah_pesanan'))
        saiz_string = ", ".join([f"{s} x {q}" for s, q in sorted(saiz_summary.items())])
        reka_bentuk = "\n".join(details_list) + (f"\n\nKeterangan Tambahan: {keterangan}" if keterangan else "")
        dibuat_oleh = session.get('username')
        try:
            conn.execute("INSERT INTO pesanan (nama_pelanggan, jenis_baju, saiz, kuantiti, reka_bentuk, status, designer_username, total_kuantiti, fabrik_id, harga, dibuat_oleh) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (nama_pelanggan, jenis_baju, saiz_string, total_qty, reka_bentuk, 'Baru', designer or None, total_qty, fabrik_id, harga_akhir, dibuat_oleh))
            conn.commit()
            flash('Pesanan berjaya ditambah!', 'flash-success')
        except Exception as e:
            flash(f'Ralat ketika menambah pesanan: {e}', 'flash-error')
        return redirect(url_for('urus_pesanan'))
    return render_template('tambah_pesanan.html', designers=designers, fabriks=fabriks)

@app.route('/get_harga_semua_saiz/<int:fabrik_id>')
@role_required(['admin', 'sales'])
def get_harga_semua_saiz(fabrik_id):
    conn = get_db_connection()
    harga_data = conn.execute("SELECT saiz, harga FROM harga_saiz WHERE fabrik_id = ?", (fabrik_id,)).fetchall()
    harga_map = {item['saiz']: item['harga'] for item in harga_data}
    return jsonify(harga_map)

@app.route('/urus_pesanan')
@role_required(['admin', 'production', 'sales']) 
def urus_pesanan():
    conn = get_db_connection()
    pesanan_list = conn.execute('SELECT p.*, f.nama_fabrik FROM pesanan p LEFT JOIN fabrik f ON p.fabrik_id = f.id ORDER BY p.id DESC').fetchall()
    fabriks = conn.execute('SELECT * FROM fabrik ORDER BY nama_fabrik').fetchall()

    files_map = {}
    if pesanan_list:
        pesanan_ids = [p['id'] for p in pesanan_list]
        placeholders = ','.join('?' for _ in pesanan_ids)
        files_data = conn.execute(f"SELECT pesanan_id, filename FROM design_files WHERE pesanan_id IN ({placeholders})", pesanan_ids).fetchall()
        
        for file in files_data:
            pid = file['pesanan_id']
            if pid not in files_map:
                files_map[pid] = []
            files_map[pid].append(file)

    sales_stats, tindakan_segera = None, None
    if session.get('peranan') == 'sales':
        perlu_tindakan = conn.execute("SELECT COUNT(id) FROM pesanan WHERE status = 'Baru' AND (designer_username IS NULL OR designer_username = '')").fetchone()[0]
        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        jualan_bulan_ini = conn.execute("SELECT COUNT(id) FROM pesanan WHERE tarikh_masuk >= ?", (start_of_month,)).fetchone()[0]
        sales_stats = {'perlu_tindakan': perlu_tindakan, 'jualan_bulan_ini': jualan_bulan_ini}
        tindakan_segera = conn.execute("SELECT p.*, f.nama_fabrik FROM pesanan p LEFT JOIN fabrik f ON p.fabrik_id = f.id WHERE p.status = 'Baru' AND (p.designer_username IS NULL OR p.designer_username = '') ORDER BY p.id DESC LIMIT 5").fetchall()
        
    return render_template('urus_pesanan.html', 
                           pesanan=pesanan_list, 
                           sales_stats=sales_stats, 
                           tindakan_segera=tindakan_segera, 
                           fabriks=fabriks,
                           files_map=files_map)

@app.route('/update_pesanan/<int:pesanan_id>', methods=['POST'])
@role_required(['admin', 'production', 'sales'])
def update_pesanan(pesanan_id):
    conn = get_db_connection()
    conn.execute('UPDATE pesanan SET status = ? WHERE id = ?', (request.form['status_baru'], pesanan_id))
    conn.commit()
    flash('Status pesanan berjaya dikemaskini!', 'flash-success')
    return redirect(url_for('urus_pesanan'))

@app.route('/assign_designer/<int:pesanan_id>', methods=['GET', 'POST'])
@role_required(['admin', 'sales']) 
def assign_designer(pesanan_id):
    conn = get_db_connection()
    if request.method == 'POST':
        designer = request.form['designer_username']
        conn.execute('UPDATE pesanan SET designer_username = ?, status = ? WHERE id = ?', (designer, 'Design Dalam Proses', pesanan_id))
        conn.commit()
        flash(f'Pesanan ID {pesanan_id} berjaya ditetapkan kepada {designer}.', 'flash-success')
        return redirect(url_for('urus_pesanan'))
    pesanan = conn.execute('SELECT * FROM pesanan WHERE id = ?', (pesanan_id,)).fetchone()
    designers = conn.execute("SELECT username, nama FROM pengguna WHERE peranan = 'designer'").fetchall()
    if not pesanan:
        flash('Pesanan tidak ditemui.', 'flash-error')
        return redirect(url_for('urus_pesanan'))
    return render_template('assign_designer.html', pesanan=pesanan, designers=designers)

@app.route('/urus_design')
@role_required(['admin', 'designer'])
def urus_design():
    conn = get_db_connection()
    pesanan_list, designer_stats = [], None
    peranan, username = session.get('peranan'), session.get('username')
    if peranan == 'designer':
        pesanan_list = conn.execute("SELECT * FROM pesanan WHERE designer_username = ? AND status IN ('Design Dalam Proses', 'Sedia untuk Production') ORDER BY id DESC", (username,)).fetchall()
        designer_stats = {
            'tugasan_aktif': len(pesanan_list),
            'rekabentuk_selesai': conn.execute("SELECT COUNT(id) FROM pesanan WHERE designer_username = ? AND status NOT IN ('Baru', 'Design Dalam Proses')", (username,)).fetchone()[0]
        }
    elif peranan == 'admin':
        pesanan_list = conn.execute("SELECT * FROM pesanan WHERE status IN ('Baru', 'Design Dalam Proses', 'Sedia untuk Production') ORDER BY id DESC").fetchall()
    return render_template('urus_design.html', pesanan=pesanan_list, designer_stats=designer_stats)

@app.route('/update_design_status/<int:pesanan_id>', methods=['POST'])
@role_required(['admin', 'designer'])
def update_design_status(pesanan_id):
    conn = get_db_connection()
    pesanan = conn.execute('SELECT designer_username FROM pesanan WHERE id = ?', (pesanan_id,)).fetchone()
    if pesanan and session['peranan'] == 'designer' and pesanan['designer_username'] != session['username']:
        flash('Anda tidak dibenarkan mengemaskini pesanan ini.', 'flash-error')
        return redirect(url_for('urus_design'))
    files_uploaded_count = 0
    for file in request.files.getlist('design_file'):
        if file and file.filename and allowed_file(file.filename):
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn.execute("INSERT INTO design_files (pesanan_id, filename) VALUES (?, ?)", (pesanan_id, filename))
            files_uploaded_count += 1
    conn.execute('UPDATE pesanan SET status = ? WHERE id = ?', (request.form['status_baru'], pesanan_id))
    conn.commit()
    flash(f'Status dikemaskini & {files_uploaded_count} fail dimuat naik!' if files_uploaded_count else 'Status dikemaskini!', 'flash-success')
    return redirect(url_for('urus_design'))

@app.route('/pesanan/<int:pesanan_id>/files')
@role_required(['admin', 'designer', 'production', 'sales'])
def view_files(pesanan_id):
    conn = get_db_connection()
    files = conn.execute("SELECT * FROM design_files WHERE pesanan_id = ?", (pesanan_id,)).fetchall()
    pesanan = conn.execute("SELECT id, nama_pelanggan FROM pesanan WHERE id = ?", (pesanan_id,)).fetchone()
    return render_template('view_files.html', files=files, pesanan=pesanan)

@app.route('/download_design/<filename>')
@role_required(['admin', 'designer', 'production', 'sales']) 
def download_design(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], secure_filename(filename), as_attachment=True)
    except FileNotFoundError:
        flash('Fail reka bentuk tidak dijumpai.', 'flash-error')
        return redirect(request.referrer or url_for('dashboard'))

@app.route('/download_all_files/<int:pesanan_id>')
@role_required(['admin', 'designer', 'production', 'sales']) 
def download_all_files(pesanan_id):
    conn = get_db_connection()
    files = conn.execute("SELECT filename FROM design_files WHERE pesanan_id = ?", (pesanan_id,)).fetchall()

    if not files:
        flash('Tiada fail reka bentuk ditemui untuk pesanan ini.', 'flash-error')
        return redirect(url_for('urus_pesanan'))

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            filename = file['filename']
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                zipf.write(file_path, os.path.basename(file_path))

    memory_file.seek(0)
    
    return send_file(
        memory_file,
        download_name=f'Pesanan_{pesanan_id}_files.zip',
        as_attachment=True,
        mimetype='application/zip'
    )

@app.route('/urus_stok', methods=['GET', 'POST'])
@role_required(['admin', 'production'])
def urus_stok():
    conn = get_db_connection()
    if request.method == 'POST':
        try:
            conn.execute("INSERT INTO stok_bahan (nama_bahan, kuantiti, unit, kuantiti_minima) VALUES (?, ?, ?, ?)",
                         (request.form['nama_bahan'], request.form['kuantiti'], request.form['unit'], request.form['kuantiti_minima']))
            conn.commit()
            flash(f'Bahan {request.form["nama_bahan"]} berjaya ditambah!', 'flash-success')
        except sqlite3.IntegrityError:
            flash(f'Bahan {request.form["nama_bahan"]} sudah wujud.', 'flash-error')
        return redirect(url_for('urus_stok'))
    stok = conn.execute('SELECT * FROM stok_bahan ORDER BY nama_bahan').fetchall()
    return render_template('urus_stok.html', stok=stok)

@app.route('/update_stok/<int:bahan_id>', methods=['POST'])
@role_required(['admin', 'production'])
def update_stok(bahan_id):
    conn = get_db_connection()
    bahan = conn.execute('SELECT kuantiti FROM stok_bahan WHERE id = ?', (bahan_id,)).fetchone()
    if bahan:
        kuantiti_baru = bahan['kuantiti'] + 1 if request.form['action'] == 'tambah' else (bahan['kuantiti'] - 1 if bahan['kuantiti'] > 0 else 0)
        conn.execute('UPDATE stok_bahan SET kuantiti = ? WHERE id = ?', (kuantiti_baru, bahan_id))
        conn.commit()
        flash('Stok berjaya dikemaskini!', 'flash-success')
    else:
        flash('Bahan tidak dijumpai.', 'flash-error')
    return redirect(url_for('urus_stok'))

@app.route('/padam_bahan/<int:bahan_id>', methods=['POST'])
@role_required(['admin', 'production'])
def padam_bahan(bahan_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM stok_bahan WHERE id = ?', (bahan_id,))
    conn.commit()
    flash('Bahan berjaya dipadam!', 'flash-success')
    return redirect(url_for('urus_stok'))

@app.route('/urus_pelanggan', methods=['GET', 'POST'])
@role_required(['admin', 'sales']) 
def urus_pelanggan():
    conn = get_db_connection()
    if request.method == 'POST':
        try:
            conn.execute("INSERT INTO pelanggan (nama, telefon, email, alamat) VALUES (?, ?, ?, ?)",
                         (request.form['nama'], request.form.get('telefon'), request.form.get('email'), request.form.get('alamat')))
            conn.commit()
            flash(f'Pelanggan {request.form["nama"]} berjaya ditambah.', 'flash-success')
        except Exception as e:
            flash(f'Ralat ketika menambah pelanggan: {e}', 'flash-error')
        return redirect(url_for('urus_pelanggan'))
    
    pelanggan = conn.execute('SELECT * FROM pelanggan ORDER BY nama').fetchall()
    fabriks = conn.execute('SELECT * FROM fabrik ORDER BY nama_fabrik').fetchall()
    return render_template('urus_pelanggan.html', pelanggan=pelanggan, fabriks=fabriks)

@app.route('/padam_pelanggan/<int:pelanggan_id>', methods=['POST'])
@role_required(['admin', 'sales']) 
def padam_pelanggan(pelanggan_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM pelanggan WHERE id = ?', (pelanggan_id,))
    conn.commit()
    flash('Pelanggan berjaya dipadam!', 'flash-success')
    return redirect(url_for('urus_pelanggan'))

@app.route('/urus_fabrik', methods=['GET', 'POST'])
@role_required(['admin'])
def urus_fabrik():
    conn = get_db_connection()
    if request.method == 'POST':
        nama_fabrik = request.form.get('nama_fabrik')
        if nama_fabrik:
            try:
                conn.execute("INSERT INTO fabrik (nama_fabrik) VALUES (?)", (nama_fabrik,))
                conn.commit()
                flash(f"Fabrik '{nama_fabrik}' berjaya ditambah.", "flash-success")
            except sqlite3.IntegrityError:
                flash(f"Fabrik '{nama_fabrik}' sudah wujud.", "flash-error")
        return redirect(url_for('urus_fabrik'))
    fabriks = conn.execute("SELECT * FROM fabrik ORDER BY nama_fabrik").fetchall()
    return render_template('urus_fabrik.html', fabriks=fabriks)

@app.route('/padam_fabrik/<int:fabrik_id>', methods=['POST'])
@role_required(['admin'])
def padam_fabrik(fabrik_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM harga_saiz WHERE fabrik_id = ?", (fabrik_id,))
    conn.execute("DELETE FROM fabrik WHERE id = ?", (fabrik_id,))
    conn.commit()
    flash("Fabrik dan harga berkaitan telah dipadam.", "flash-success")
    return redirect(url_for('urus_fabrik'))

@app.route('/urus_harga/<int:fabrik_id>', methods=['GET', 'POST'])
@role_required(['admin'])
def urus_harga(fabrik_id):
    conn = get_db_connection()
    fabrik = conn.execute("SELECT * FROM fabrik WHERE id = ?", (fabrik_id,)).fetchone()
    saiz_standard = ['XS', 'S', 'M', 'L', 'XL', '2XL', '3XL', '4XL', '5XL']
    if request.method == 'POST':
        for saiz in saiz_standard:
            harga = request.form.get(f'harga_{saiz}')
            if harga:
                sedia_ada = conn.execute("SELECT id FROM harga_saiz WHERE fabrik_id = ? AND saiz = ?", (fabrik_id, saiz)).fetchone()
                if sedia_ada:
                    conn.execute("UPDATE harga_saiz SET harga = ? WHERE id = ?", (harga, sedia_ada['id']))
                else:
                    conn.execute("INSERT INTO harga_saiz (fabrik_id, saiz, harga) VALUES (?, ?, ?)", (fabrik_id, saiz, harga))
        conn.commit()
        flash(f"Harga untuk fabrik '{fabrik['nama_fabrik']}' telah dikemaskini.", "flash-success")
        return redirect(url_for('urus_fabrik'))
    harga_sedia_ada = conn.execute("SELECT saiz, harga FROM harga_saiz WHERE fabrik_id = ?", (fabrik_id,)).fetchall()
    harga_map = {item['saiz']: item['harga'] for item in harga_sedia_ada}
    return render_template('urus_harga.html', fabrik=fabrik, saiz_standard=saiz_standard, harga_map=harga_map)

@app.route('/tetapan', methods=['GET', 'POST'])
@role_required(['admin'])
def tetapan():
    conn = get_db_connection()
    if request.method == 'POST':
        setting_keys = ['nama_syarikat', 'alamat_syarikat', 'telefon_syarikat', 'email_syarikat', 'target_jualan_bulanan']
        
        for key in setting_keys:
            if key in request.form:
                conn.execute("UPDATE tetapan SET nilai_tetapan = ? WHERE nama_tetapan = ?", 
                             (request.form[key], key))
        
        conn.commit()
        flash('Maklumat syarikat berjaya dikemaskini!', 'flash-success')
        return redirect(url_for('tetapan'))

    settings_rows = conn.execute('SELECT nama_tetapan, nilai_tetapan FROM tetapan').fetchall()
    tetapan_dict = {row['nama_tetapan']: row['nilai_tetapan'] for row in settings_rows}
    
    return render_template('tetapan.html', tetapan=tetapan_dict)

class PDF(FPDF):
    def __init__(self, tetapan, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tetapan = tetapan

    def header(self):
        self.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        self.set_font('DejaVu', '', 14)
        self.cell(0, 5, self.tetapan.get('nama_syarikat', 'NAMA SYARIKAT'), 0, 1, 'L')
        self.set_font('DejaVu', '', 10)
        self.cell(0, 5, self.tetapan.get('alamat_syarikat', 'ALAMAT'), 0, 1, 'L')
        
        telefon = self.tetapan.get('telefon_syarikat', 'TELEFON')
        email = self.tetapan.get('email_syarikat', 'EMEL')
        self.cell(0, 5, f'Tel: {telefon} | Email: {email}', 0, 1, 'L')
        
        self.ln(5)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(8)
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Muka Surat {self.page_no()}/{{nb}}', 0, 0, 'C')

def generate_jobsheet_pdf(pesanan, tetapan):
    pdf = PDF(tetapan, 'P', 'mm', 'A4')
    pdf.add_page()
    pdf.set_font('DejaVu', '', 20); pdf.cell(0, 15, 'JOBSHEET', 0, 1, 'C'); pdf.ln(3)
    pdf.set_font('DejaVu', '', 11)
    harga_display = f"RM {pesanan['harga']:.2f}" if pesanan['harga'] is not None else '-'
    pdf.cell(90, 6, f"ID PESANAN: {pesanan['id']}", 0, 0, 'L')
    pdf.cell(90, 6, f"TARIKH: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
    pdf.cell(90, 6, f"PELANGGAN: {str(pesanan['nama_pelanggan'])}", 0, 0, 'L')
    pdf.cell(90, 6, f"STATUS: {str(pesanan['status']).upper()}", 0, 1, 'R')
    pdf.cell(90, 6, f"FABRIK: {str(pesanan['nama_fabrik'] or '-')}", 0, 0, 'L')
    pdf.cell(90, 6, f"HARGA: {harga_display}", 0, 1, 'R')
    pdf.cell(0, 6, f"DESIGNER: {str(pesanan['designer_username'] or 'Belum ditetapkan')}", 0, 1, 'L')
    pdf.cell(0, 6, f"TOTAL KUANTITI: {str(pesanan['total_kuantiti'] or 0)}", 0, 1, 'L'); pdf.ln(5)
    pdf.set_font('DejaVu', '', 11); pdf.cell(0, 6, 'RINGKASAN SAIZ:', 0, 1, 'L')
    pdf.set_font('DejaVu', '', 10); pdf.multi_cell(0, 5, str(pesanan['saiz'] or '-'), 1, 'L'); pdf.ln(5)
    pdf.set_font('DejaVu', '', 11); pdf.cell(0, 6, 'BUTIRAN LENGKAP:', 0, 1, 'L') 
    pdf.set_font('DejaVu', '', 9)
    pdf.multi_cell(0, 4, str(pesanan['reka_bentuk'] or 'Tiada Butiran'), 1, 'L'); pdf.ln(10)
    pdf_output = pdf.output()
    return io.BytesIO(pdf_output)

def generate_quotation_pdf(pelanggan, fabrik, items, no_quotation, terma_syarat, tetapan):
    pdf = PDF(tetapan, 'P', 'mm', 'A4')
    pdf.add_page()
    pdf.set_font('DejaVu', '', 20)
    pdf.cell(0, 15, 'SEBUT HARGA / QUOTATION', 0, 1, 'C')
    pdf.ln(3)

    pdf.set_font('DejaVu', '', 11)
    pdf.cell(90, 6, f"UNTUK: {pelanggan['nama']}", 0, 0, 'L')
    pdf.cell(90, 6, f"NO. QUOTATION: {no_quotation}", 0, 1, 'R')
    pdf.cell(90, 6, f"TELEFON: {pelanggan['telefon'] or '-'}", 0, 0, 'L')
    pdf.cell(90, 6, f"TARIKH: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
    pdf.ln(5)

    pdf.set_font('DejaVu', '', 11)
    pdf.cell(0, 8, f"PERKARA: Tempahan Baju - Fabrik {fabrik['nama_fabrik']}", 0, 1, 'L')
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font('DejaVu', '', 10)
    pdf.cell(80, 7, 'Saiz', 1, 0, 'C', True)
    pdf.cell(35, 7, 'Harga Seunit (RM)', 1, 0, 'C', True)
    pdf.cell(35, 7, 'Kuantiti', 1, 0, 'C', True)
    pdf.cell(40, 7, 'Jumlah (RM)', 1, 1, 'C', True)

    total_price = 0
    for item in items:
        pdf.cell(80, 6, item['saiz'], 1)
        pdf.cell(35, 6, f"{item['harga']:.2f}", 1, 0, 'R')
        pdf.cell(35, 6, str(item['kuantiti']), 1, 0, 'C')
        subtotal = item['harga'] * item['kuantiti']
        pdf.cell(40, 6, f"{subtotal:.2f}", 1, 1, 'R')
        total_price += subtotal
    
    pdf.set_font('DejaVu', '', 11)
    pdf.cell(150, 8, 'JUMLAH KESELURUHAN', 1, 0, 'R')
    pdf.cell(40, 8, f"{total_price:.2f}", 1, 1, 'R')
    pdf.ln(10)

    pdf.set_font('DejaVu', '', 9)
    pdf.multi_cell(0, 5, terma_syarat, 0, 'L')
    
    pdf_output = pdf.output()
    return io.BytesIO(pdf_output)

@app.route('/jobsheet/<int:pesanan_id>')
@role_required(['admin', 'sales', 'production', 'designer']) 
def jobsheet(pesanan_id):
    try:
        conn = get_db_connection()
        settings_rows = conn.execute('SELECT nama_tetapan, nilai_tetapan FROM tetapan').fetchall()
        tetapan = {row['nama_tetapan']: row['nilai_tetapan'] for row in settings_rows}

        pesanan = conn.execute('SELECT p.*, f.nama_fabrik FROM pesanan p LEFT JOIN fabrik f ON p.fabrik_id = f.id WHERE p.id = ?', (pesanan_id,)).fetchone()
        if not pesanan:
            flash('Pesanan tidak ditemui.', 'flash-error')
            return redirect(url_for('dashboard'))
            
        buffer = generate_jobsheet_pdf(pesanan, tetapan)
        safe_name = "".join(c for c in pesanan['nama_pelanggan'] if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
        return send_file(buffer, download_name=f"JOBSHEET_{pesanan['id']}_{safe_name}.pdf", as_attachment=True)
    except Exception as e:
        return render_template('error.html', error=e)

@app.route('/jobsheet/configure/<int:pesanan_id>', methods=['POST'])
@role_required(['admin', 'sales', 'production', 'designer'])
def configure_jobsheet(pesanan_id):
    try:
        conn = get_db_connection()
        settings_rows = conn.execute('SELECT nama_tetapan, nilai_tetapan FROM tetapan').fetchall()
        tetapan = {row['nama_tetapan']: row['nilai_tetapan'] for row in settings_rows}
        
        fabrik_id = request.form.get('fabrik_id')
        harga = request.form.get('harga') if request.form.get('harga') else None
        if not fabrik_id:
            flash("Sila pilih jenis fabrik.", "flash-error")
            return redirect(url_for('urus_pesanan'))
        conn.execute("UPDATE pesanan SET fabrik_id = ?, harga = ? WHERE id = ?", (fabrik_id, harga, pesanan_id))
        conn.commit()
        pesanan = conn.execute('SELECT p.*, f.nama_fabrik FROM pesanan p LEFT JOIN fabrik f ON p.fabrik_id = f.id WHERE p.id = ?', (pesanan_id,)).fetchone()
        if not pesanan:
            flash('Pesanan tidak ditemui.', 'flash-error')
            return redirect(url_for('urus_pesanan'))
        buffer = generate_jobsheet_pdf(pesanan, tetapan)
        safe_name = "".join(c for c in pesanan['nama_pelanggan'] if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
        return send_file(buffer, download_name=f"JOBSHEET_{pesanan['id']}_{safe_name}.pdf", as_attachment=True)
    except Exception as e:
        return render_template('error.html', error=e)

@app.route('/quotation/<int:pelanggan_id>', methods=['GET', 'POST'])
@role_required(['admin', 'sales']) 
def quotation(pelanggan_id):
    conn = get_db_connection()
    pelanggan = conn.execute('SELECT * FROM pelanggan WHERE id = ?', (pelanggan_id,)).fetchone()
    if not pelanggan:
        flash("Pelanggan tidak ditemui.", "flash-error")
        return redirect(url_for('urus_pelanggan'))

    if request.method == 'POST':
        try:
            settings_rows = conn.execute('SELECT nama_tetapan, nilai_tetapan FROM tetapan').fetchall()
            tetapan = {row['nama_tetapan']: row['nilai_tetapan'] for row in settings_rows}
            
            fabrik_id = request.form.get('fabrik_id')
            if not fabrik_id:
                flash("Sila pilih fabrik terlebih dahulu.", "flash-error")
                return redirect(url_for('urus_pelanggan'))

            fabrik = conn.execute("SELECT * FROM fabrik WHERE id = ?", (fabrik_id,)).fetchone()
            harga_saiz = conn.execute("SELECT saiz, harga FROM harga_saiz WHERE fabrik_id = ?", (fabrik_id,)).fetchall()
            harga_map = {item['saiz']: item['harga'] for item in harga_saiz}
            
            items = []
            for saiz, harga in harga_map.items():
                kuantiti_str = request.form.get(f'qty_{saiz}')
                if kuantiti_str and int(kuantiti_str) > 0:
                    items.append({
                        'saiz': saiz,
                        'harga': harga,
                        'kuantiti': int(kuantiti_str)
                    })
            
            if not items:
                flash("Sila masukkan sekurang-kurangnya satu kuantiti.", "flash-error")
                return redirect(url_for('urus_pelanggan'))

            terma = request.form.get('terma_syarat', '')
            no_quotation = f"QUO-{datetime.now().strftime('%Y%m%d')}-{pelanggan_id}"
            buffer = generate_quotation_pdf(pelanggan, fabrik, items, no_quotation, terma, tetapan)
            
            safe_name = "".join(c for c in pelanggan['nama'] if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
            return send_file(buffer, download_name=f"QUOTATION_{pelanggan_id}_{safe_name}.pdf", as_attachment=True)
            
        except Exception as e:
            flash(f"Ralat semasa menjana PDF: {e}", "flash-error")
            return redirect(url_for('urus_pelanggan'))

    no_quotation = f"QUO-{datetime.now().strftime('%Y%m%d')}-{pelanggan_id}"
    return render_template('cipta_quotation.html', pelanggan=pelanggan, no_quotation=no_quotation)


@app.route('/invoice/<int:pelanggan_id>')
@role_required(['admin', 'sales']) 
def invoice(pelanggan_id):
    flash('Fungsi Invois dinamik belum dibina.', 'flash-info')
    return redirect(url_for('urus_pelanggan'))

if __name__ == '__main__':
    app.run(debug=True)