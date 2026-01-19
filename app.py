import pymysql
import pymysql.cursors
import datetime
import os
import io
from flask import Flask, render_template_string, request, redirect, url_for, session, send_file
from fpdf import FPDF


# --- DATABASE CONFIG ---
class Database:
    def __init__(self):
        self.config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'lapor_sih',
            'cursorclass': pymysql.cursors.DictCursor
        }

    def connect(self):
        return pymysql.connect(**self.config)

    def create_tables(self):
        conn = self.connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS laporan (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        nomor_tiket VARCHAR(20) UNIQUE,
                        nama_pelapor VARCHAR(100),
                        judul VARCHAR(255),
                        isi TEXT,
                        lokasi VARCHAR(100),
                        foto VARCHAR(255),
                        status ENUM('Pending', 'Diterima', 'Ditolak', 'Selesai') DEFAULT 'Pending',
                        tanggal_lapor TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            conn.commit()
        finally:
            conn.close()


app = Flask(__name__)
app.secret_key = 'LAPOR_SIH_ULTRA_2026'
db = Database()

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- UI DARK MODE (STRUKTUR ASLI) ---
HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8"><title>Lapor Sih! | Full System</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/admin-lte@3.2/dist/css/adminlte.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        :root { --accent: #6366f1; }
        body { background: #1a1d21; color: white; }
        .glass-card { background: #24282d; border-radius: 15px; padding: 20px; margin-bottom: 20px; border: 1px solid #343a40; }
        .stats-card { background: #24282d; border-radius: 15px; padding: 15px; display: flex; align-items: center; justify-content: space-between; border: 1px solid #343a40; }
        .btn-quantum { background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%); color: white; border: none; border-radius: 10px; padding: 12px; font-weight: bold; width: 100%; }
        #map { height: 350px; border-radius: 15px; width: 100%; border: 1px solid #343a40; }
        .table { color: white; }
        .img-report { width: 50px; height: 50px; object-fit: cover; border-radius: 8px; cursor: pointer; }
    </style>
</head>
<body class="hold-transition">
<div class="wrapper">
    <nav class="main-header navbar navbar-expand navbar-dark bg-dark border-0" style="margin-left:0">
        <ul class="navbar-nav ml-auto">
            {% if session.get('logged_in') %}
                <li class="nav-item"><a href="/cetak_pdf" class="btn btn-success btn-sm rounded-pill px-4 mr-2">CETAK PDF</a></li>
                <li class="nav-item"><a href="/logout" class="btn btn-danger btn-sm rounded-pill px-4">LOGOUT</a></li>
            {% else %}
                <li class="nav-item"><button class="btn btn-primary btn-sm rounded-pill px-4" data-toggle="modal" data-target="#loginModal">ADMIN LOGIN</button></li>
            {% endif %}
        </ul>
    </nav>

    <div class="content-wrapper bg-transparent p-4" style="margin-left: 0 !important;">
        <div class="row mb-4">
            <div class="col-md-3"><div class="stats-card"><div><h3>{{ stats.total }}</h3><p>Incoming</p></div><i class="fas fa-bolt text-warning fa-2x"></i></div></div>
            <div class="col-md-3"><div class="stats-card"><div><h3>{{ stats.diterima }}</h3><p>Validated</p></div><i class="fas fa-check text-primary fa-2x"></i></div></div>
            <div class="col-md-3"><div class="stats-card"><div><h3>{{ stats.ditolak }}</h3><p>Rejected</p></div><i class="fas fa-ban text-danger fa-2x"></i></div></div>
            <div class="col-md-3"><div class="stats-card"><div><h3>{{ stats.selesai }}</h3><p>Completed</p></div><i class="fas fa-flag-checkered text-success fa-2x"></i></div></div>
        </div>

        <div class="row">
            <div class="col-lg-8">
                <div class="glass-card"><div id="map"></div></div>
                <div class="glass-card">
                    <h5>Daftar Laporan</h5>
                    <table class="table mt-3">
                        <thead><tr><th>Foto</th><th>Aduan</th><th>Status</th><th>Aksi</th></tr></thead>
                        <tbody>
                            {% for r in data %}
                            <tr>
                                <td><img src="/static/uploads/{{ r.foto }}" class="img-report" onclick="alert('Isi: {{r.isi}}')"></td>
                                <td><small>{{ r.nomor_tiket }}</small><br><b>{{ r.judul }}</b></td>
                                <td><span class="badge {% if r.status == 'Selesai' %}badge-success{% elif r.status == 'Diterima' %}badge-primary{% elif r.status == 'Ditolak' %}badge-danger{% else %}badge-warning{% endif %}">{{ r.status }}</span></td>
                                <td>
                                    {% if session.get('logged_in') %}
                                        <form action="/update_status/{{ r.id }}" method="POST" class="d-inline">
                                            <button name="status" value="Diterima" class="btn btn-xs btn-primary">Terima</button>
                                            <button name="status" value="Selesai" class="btn btn-xs btn-success">Selesai</button>
                                            <button name="status" value="Ditolak" class="btn btn-xs btn-danger">Tolak</button>
                                        </form>
                                        <a href="/hapus/{{ r.id }}" class="btn btn-xs btn-secondary" onclick="return confirm('Hapus?')">Hapus</a>
                                    {% else %}
                                        <button class="btn btn-xs btn-info" onclick="alert('Tiket: {{r.nomor_tiket}}\\nJudul: {{r.judul}}\\nStatus: {{r.status}}')">Detail</button>
                                        <button class="btn btn-xs btn-warning" onclick="let n = prompt('Edit Judul:', '{{r.judul}}'); if(n) window.location.href='/edit/'+{{r.id}}+'?judul='+n">Edit</button>
                                        <a href="/hapus/{{ r.id }}" class="btn btn-xs btn-danger" onclick="return confirm('Hapus laporan Anda?')">Hapus</a>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
            {% if not session.get('logged_in') %}
            <div class="col-lg-4">
                <div class="glass-card">
                    <h5>Buat Aduan</h5>
                    <form action="/lapor" method="POST" enctype="multipart/form-data">
                        <input type="text" name="nama" class="form-control bg-dark text-white mb-2" placeholder="Nama" required>
                        <input type="text" name="judul" class="form-control bg-dark text-white mb-2" placeholder="Judul" required>
                        <textarea name="isi" class="form-control bg-dark text-white mb-2" rows="3" placeholder="Isi aduan..." required></textarea>
                        <input type="file" name="foto" class="form-control-file mb-2">
                        <input type="hidden" name="lokasi" id="loc">
                        <button type="submit" class="btn-quantum">KIRIM</button>
                    </form>
                </div>
            </div>
            {% endif %}
        </div>
    </div>
</div>

<div class="modal fade" id="loginModal" tabindex="-1"><div class="modal-dialog modal-sm modal-dialog-centered"><div class="modal-content bg-dark p-4">
    <form action="/login" method="POST">
        <input type="text" name="username" class="form-control bg-dark text-white mb-2" placeholder="User">
        <input type="password" name="password" class="form-control bg-dark text-white mb-3" placeholder="Pass">
        <button type="submit" class="btn-quantum">LOGIN</button>
    </form>
</div></div></div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@4.6.1/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
    if (navigator.geolocation) { navigator.geolocation.getCurrentPosition(p => { document.getElementById('loc').value = p.coords.latitude.toFixed(6) + "," + p.coords.longitude.toFixed(6); }); }
    var map = L.map('map').setView([-2.5489, 118.0149], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
    {% for r in data %}{% if r.lokasi %} L.marker([{{ r.lokasi }}]).addTo(map).bindPopup("{{r.judul}}"); {% endif %}{% endfor %}
</script>
</body>
</html>
"""


# --- BACKEND ROUTES ---
@app.route('/')
def index():
    conn = db.connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM laporan ORDER BY id DESC")
            laporan = cursor.fetchall()

            # Statistik Real-time
            cursor.execute("SELECT COUNT(*) as c FROM laporan")
            t = cursor.fetchone()['c']
            cursor.execute("SELECT COUNT(*) as c FROM laporan WHERE status='Diterima'")
            v = cursor.fetchone()['c']
            cursor.execute("SELECT COUNT(*) as c FROM laporan WHERE status='Ditolak'")
            r = cursor.fetchone()['c']
            cursor.execute("SELECT COUNT(*) as c FROM laporan WHERE status='Selesai'")
            s = cursor.fetchone()['c']

            stats = {'total': t, 'diterima': v, 'ditolak': r, 'selesai': s}
            return render_template_string(HTML_LAYOUT, data=laporan, stats=stats)
    finally:
        conn.close()


@app.route('/cetak_pdf')
def cetak_pdf():
    if not session.get('logged_in'): return redirect('/')
    conn = db.connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM laporan ORDER BY id DESC")
            rows = cursor.fetchall()

            # Setup PDF (Fixed Version)
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", 'B', 16)
            pdf.cell(190, 10, "REKAPITULASI LAPORAN ADUAN", align='C', new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)

            pdf.set_font("Helvetica", 'B', 10)
            pdf.cell(10, 10, "ID", 1);
            pdf.cell(40, 10, "Tiket", 1);
            pdf.cell(60, 10, "Judul", 1);
            pdf.cell(30, 10, "Status", 1);
            pdf.cell(50, 10, "Pelapor", 1)
            pdf.ln()

            pdf.set_font("Helvetica", '', 9)
            for r in rows:
                pdf.cell(10, 10, str(r['id']), 1)
                pdf.cell(40, 10, str(r['nomor_tiket']), 1)
                pdf.cell(60, 10, str(r['judul'])[:25], 1)
                pdf.cell(30, 10, str(r['status']), 1)
                pdf.cell(50, 10, str(r['nama_pelapor']), 1)
                pdf.ln()

            output = pdf.output()
            return send_file(io.BytesIO(output), mimetype='application/pdf', as_attachment=True,
                             download_name='rekap_laporan.pdf')
    finally:
        conn.close()


@app.route('/update_status/<int:id>', methods=['POST'])
def update_status(id):
    if not session.get('logged_in'): return redirect('/')
    conn = db.connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE laporan SET status=%s WHERE id=%s", (request.form.get('status'), id))
        conn.commit()
    finally:
        conn.close()
    return redirect('/')


@app.route('/edit/<int:id>')
def edit_laporan(id):
    judul_baru = request.args.get('judul')
    conn = db.connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE laporan SET judul=%s WHERE id=%s", (judul_baru, id))
        conn.commit()
    finally:
        conn.close()
    return redirect('/')


@app.route('/hapus/<int:id>')
def hapus(id):
    conn = db.connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM laporan WHERE id=%s", (id,))
        conn.commit()
    finally:
        conn.close()
    return redirect('/')


@app.route('/lapor', methods=['POST'])
def lapor():
    tiket = f"LP-{datetime.datetime.now().strftime('%Y%m%d-%H%M')}"
    f = request.files.get('foto')
    fname = f"{tiket}_{f.filename}" if f and f.filename != "" else ""
    if f and fname: f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
    conn = db.connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO laporan (nomor_tiket, nama_pelapor, judul, isi, lokasi, foto) VALUES (%s,%s,%s,%s,%s,%s)",
                (tiket, request.form.get('nama'), request.form.get('judul'), request.form.get('isi'),
                 request.form.get('lokasi'), fname))
        conn.commit()
    finally:
        conn.close()
    return redirect('/')


@app.route('/login', methods=['POST'])
def login():
    if request.form.get('username') == "admin" and request.form.get('password') == "admin1":
        session['logged_in'] = True
    return redirect('/')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    db.create_tables()
    app.run(debug=True)