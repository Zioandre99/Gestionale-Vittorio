"""
db.py - Livello di accesso ai dati (SQLite) per il Gestionale Magazzino.
Tutta la logica di lettura/scrittura sul database vive qui, cosi' l'interfaccia
grafica (app.py) resta semplice e si occupa solo di presentare i dati.
"""

import sqlite3
import os
import sys
import datetime


def get_app_dir():
    """Cartella dove viene salvato il database (accanto all'eseguibile/script)."""
    if getattr(sys, "frozen", False):
        # Eseguibile creato con PyInstaller
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DB_PATH = os.path.join(get_app_dir(), "magazzino.db")


class Database:
    def __init__(self, path=DB_PATH):
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()
        self._seed_settings()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _create_tables(self):
        c = self.conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                name TEXT NOT NULL,
                category TEXT,
                unit TEXT DEFAULT 'pz',
                quantity REAL NOT NULL DEFAULT 0,
                reorder_threshold REAL NOT NULL DEFAULT 0,
                sale_price REAL DEFAULT 0,
                last_order_price REAL,
                last_order_date TEXT,
                supplier TEXT,
                notes TEXT,
                active INTEGER NOT NULL DEFAULT 1
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('carico','scarico')),
                quantity REAL NOT NULL,
                unit_price REAL,
                date TEXT NOT NULL,
                note TEXT,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                old_price REAL,
                new_price REAL,
                pct_change REAL,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        self.conn.commit()

    def _seed_settings(self):
        defaults = {
            "azienda_nome": "La mia attivita'",
            "price_alert_threshold": "10",   # percentuale
            "backup_folder": "",
            "auto_backup": "0",
        }
        c = self.conn.cursor()
        for k, v in defaults.items():
            c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        self.conn.commit()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    def get_setting(self, key, default=None):
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        self.conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------
    def list_products(self, search=None, only_active=True):
        q = "SELECT * FROM products"
        conds = []
        params = []
        if only_active:
            conds.append("active=1")
        if search:
            conds.append("(name LIKE ? OR code LIKE ? OR category LIKE ?)")
            like = f"%{search}%"
            params += [like, like, like]
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY name COLLATE NOCASE ASC"
        return self.conn.execute(q, params).fetchall()

    def get_product(self, product_id):
        return self.conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()

    def add_product(self, data):
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO products
            (code, name, category, unit, quantity, reorder_threshold,
             sale_price, last_order_price, last_order_date, supplier, notes)
            VALUES (:code, :name, :category, :unit, :quantity, :reorder_threshold,
                    :sale_price, :last_order_price, :last_order_date, :supplier, :notes)
        """, data)
        self.conn.commit()
        return c.lastrowid

    def update_product(self, product_id, data):
        data = dict(data)
        data["id"] = product_id
        self.conn.execute("""
            UPDATE products SET
                code=:code, name=:name, category=:category, unit=:unit,
                quantity=:quantity, reorder_threshold=:reorder_threshold,
                sale_price=:sale_price, supplier=:supplier, notes=:notes
            WHERE id=:id
        """, data)
        self.conn.commit()

    def delete_product(self, product_id):
        # soft delete cosi' lo storico movimenti resta coerente
        self.conn.execute("UPDATE products SET active=0 WHERE id=?", (product_id,))
        self.conn.commit()

    def low_stock_products(self):
        return self.conn.execute(
            "SELECT * FROM products WHERE active=1 AND quantity <= reorder_threshold "
            "ORDER BY (quantity - reorder_threshold) ASC"
        ).fetchall()

    def categories(self):
        rows = self.conn.execute(
            "SELECT DISTINCT category FROM products WHERE active=1 AND category IS NOT NULL AND category<>''"
        ).fetchall()
        return sorted([r["category"] for r in rows])

    # ------------------------------------------------------------------
    # Movements (Ingressi / Uscite)
    # ------------------------------------------------------------------
    def add_movement(self, product_id, mtype, quantity, unit_price=None, date=None, note=""):
        """
        mtype: 'carico' (ingresso merce) o 'scarico' (uscita merce)
        Ritorna un dict con eventuale alert prezzo: {'alert': bool, 'pct': float, 'old':..,'new':..}
        """
        date = date or datetime.date.today().isoformat()
        product = self.get_product(product_id)
        if product is None:
            raise ValueError("Prodotto non trovato")

        alert_info = {"alert": False}

        if mtype == "carico":
            new_qty = product["quantity"] + quantity
            # Gestione confronto prezzo rispetto all'ultimo ordine
            if unit_price is not None:
                old_price = product["last_order_price"]
                if old_price:
                    pct = (unit_price - old_price) / old_price * 100.0
                    threshold = float(self.get_setting("price_alert_threshold", "10"))
                    if abs(pct) >= threshold:
                        alert_info = {"alert": True, "pct": pct, "old": old_price, "new": unit_price}
                        self.conn.execute("""
                            INSERT INTO price_alerts (product_id, date, old_price, new_price, pct_change)
                            VALUES (?, ?, ?, ?, ?)
                        """, (product_id, date, old_price, unit_price, pct))
                self.conn.execute(
                    "UPDATE products SET last_order_price=?, last_order_date=? WHERE id=?",
                    (unit_price, date, product_id),
                )
            self.conn.execute("UPDATE products SET quantity=? WHERE id=?", (new_qty, product_id))

        elif mtype == "scarico":
            new_qty = product["quantity"] - quantity
            self.conn.execute("UPDATE products SET quantity=? WHERE id=?", (new_qty, product_id))
        else:
            raise ValueError("Tipo movimento non valido")

        self.conn.execute("""
            INSERT INTO movements (product_id, type, quantity, unit_price, date, note)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (product_id, mtype, quantity, unit_price, date, note))
        self.conn.commit()
        return alert_info

    def list_movements(self, product_id=None, limit=200):
        q = """
            SELECT m.*, p.name as product_name, p.code as product_code
            FROM movements m JOIN products p ON p.id = m.product_id
        """
        params = []
        if product_id:
            q += " WHERE m.product_id=?"
            params.append(product_id)
        q += " ORDER BY m.date DESC, m.id DESC LIMIT ?"
        params.append(limit)
        return self.conn.execute(q, params).fetchall()

    def recent_price_alerts(self, limit=50):
        return self.conn.execute("""
            SELECT a.*, p.name as product_name, p.code as product_code
            FROM price_alerts a JOIN products p ON p.id = a.product_id
            ORDER BY a.date DESC, a.id DESC LIMIT ?
        """, (limit,)).fetchall()

    def close(self):
        self.conn.close()
