import pymysql
import pymysql.cursors
import uuid

class Database:
    def __init__(self):
        self.config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'lapor_sih', # Pastikan ini tetap lapor_sih
            'cursorclass': pymysql.cursors.DictCursor
        }

    def connect(self):
        return pymysql.connect(**self.config)

    def create_tables(self):
        conn = self.connect()
        try:
            with conn.cursor() as cursor:
                # Tabel dengan kolom skala Enterprise
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS laporan (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        nomor_tiket VARCHAR(20) UNIQUE,
                        nama_pelapor VARCHAR(100),
                        kategori VARCHAR(50),
                        judul VARCHAR(255),
                        isi TEXT,
                        status ENUM('Pending', 'Verified', 'In Progress', 'Resolved', 'Rejected') DEFAULT 'Pending',
                        tanggal_lapor TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        update_terakhir TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
            conn.commit()
        finally:
            conn.close()