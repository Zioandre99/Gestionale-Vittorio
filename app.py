"""
app.py - Interfaccia grafica del Gestionale Magazzino (Tkinter).
Design semplice, pulito, con una barra laterale per navigare tra le sezioni.
"""

import os
import shutil
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from db import Database
from pdf_export import export_catalog

# ---------------------------------------------------------------------
# Palette colori - stile semplice e funzionale
# ---------------------------------------------------------------------
BG = "#F5F7F6"
SIDEBAR = "#1F3B33"
SIDEBAR_ACTIVE = "#2F6F5E"
ACCENT = "#2F6F5E"
ACCENT_DARK = "#1F3B33"
TEXT_DARK = "#222831"
WHITE = "#FFFFFF"
DANGER = "#C0392B"
WARNING = "#D98E04"
FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_SIDEBAR = ("Segoe UI", 11)


def style_treeview(style):
    style.theme_use("clam")
    style.configure("Treeview", font=FONT, rowheight=28, background=WHITE,
                     fieldbackground=WHITE, foreground=TEXT_DARK, borderwidth=0)
    style.configure("Treeview.Heading", font=FONT_BOLD, background=ACCENT,
                     foreground=WHITE, relief="flat")
    style.map("Treeview.Heading", background=[("active", ACCENT_DARK)])
    style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", WHITE)])
    style.configure("TButton", font=FONT_BOLD, padding=8)
    style.configure("Accent.TButton", background=ACCENT, foreground=WHITE)
    style.map("Accent.TButton", background=[("active", ACCENT_DARK)])
    style.configure("TNotebook", background=BG)


class GestionaleApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestionale Magazzino")
        self.geometry("1180x720")
        self.minsize(980, 620)
        self.configure(bg=BG)

        self.db = Database()

        style = ttk.Style(self)
        style_treeview(style)

        self._build_layout()
        self.show_frame("dashboard")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    def _build_layout(self):
        # Sidebar di navigazione
        sidebar = tk.Frame(self, bg=SIDEBAR, width=210)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="📦 Magazzino", bg=SIDEBAR, fg=WHITE,
                 font=("Segoe UI", 15, "bold"), pady=22).pack(fill="x")

        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "🏠  Dashboard"),
            ("inventory", "🗂️  Prodotti"),
            ("movements", "🔁  Ingressi / Uscite"),
            ("catalog", "📄  Catalogo PDF"),
            ("settings", "⚙️  Impostazioni"),
        ]
        for key, label in nav_items:
            b = tk.Label(sidebar, text=label, bg=SIDEBAR, fg="#D7E4E0",
                         font=FONT_SIDEBAR, anchor="w", padx=22, pady=13, cursor="hand2")
            b.pack(fill="x")
            b.bind("<Button-1>", lambda e, k=key: self.show_frame(k))
            b.bind("<Enter>", lambda e, w=b: w.config(bg=SIDEBAR_ACTIVE))
            b.bind("<Leave>", lambda e, w=b, k=key: w.config(
                bg=SIDEBAR_ACTIVE if self.current_frame_key == k else SIDEBAR))
            self.nav_buttons[key] = b

        self.current_frame_key = None

        # Area contenuti
        self.container = tk.Frame(self, bg=BG)
        self.container.pack(side="left", fill="both", expand=True)

        self.frames = {
            "dashboard": DashboardFrame(self.container, self),
            "inventory": InventoryFrame(self.container, self),
            "movements": MovementsFrame(self.container, self),
            "catalog": CatalogFrame(self.container, self),
            "settings": SettingsFrame(self.container, self),
        }
        for f in self.frames.values():
            f.place(x=0, y=0, relwidth=1, relheight=1)

    def show_frame(self, key):
        for k, b in self.nav_buttons.items():
            b.config(bg=SIDEBAR_ACTIVE if k == key else SIDEBAR)
        self.current_frame_key = key
        frame = self.frames[key]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show()

    def refresh_all(self):
        for f in self.frames.values():
            if hasattr(f, "on_show"):
                f.on_show()

    def _on_close(self):
        if self.db.get_setting("auto_backup", "0") == "1":
            do_backup(self.db, silent=True)
        self.db.close()
        self.destroy()


# =======================================================================
# DASHBOARD
# =======================================================================
class DashboardFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app

        tk.Label(self, text="Dashboard", font=FONT_TITLE, bg=BG, fg=TEXT_DARK).pack(
            anchor="w", padx=28, pady=(24, 4))
        tk.Label(self, text="Riepilogo veloce dello stato del magazzino",
                 font=FONT, bg=BG, fg="#607068").pack(anchor="w", padx=28, pady=(0, 16))

        # Cards riepilogo
        cards_row = tk.Frame(self, bg=BG)
        cards_row.pack(fill="x", padx=28)
        self.card_total = self._make_card(cards_row, "Prodotti attivi", "0", ACCENT)
        self.card_low = self._make_card(cards_row, "Da riordinare", "0", DANGER)
        self.card_alerts = self._make_card(cards_row, "Alert prezzo recenti", "0", WARNING)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=28, pady=(20, 20))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # Da riordinare
        left = tk.LabelFrame(body, text=" Prodotti da riordinare ", font=FONT_BOLD,
                              bg=WHITE, fg=TEXT_DARK, bd=1, relief="solid")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.low_tree = ttk.Treeview(left, columns=("code", "name", "qty", "th"),
                                      show="headings", height=10)
        for c, t, w in [("code", "Codice", 80), ("name", "Nome", 200),
                        ("qty", "Q.ta'", 70), ("th", "Soglia", 70)]:
            self.low_tree.heading(c, text=t)
            self.low_tree.column(c, width=w, anchor="center" if c != "name" else "w")
        self.low_tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Alert prezzo
        right = tk.LabelFrame(body, text=" Variazioni prezzo rispetto all'ultimo ordine ",
                               font=FONT_BOLD, bg=WHITE, fg=TEXT_DARK, bd=1, relief="solid")
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.alert_tree = ttk.Treeview(right, columns=("name", "old", "new", "pct", "date"),
                                        show="headings", height=10)
        for c, t, w in [("name", "Prodotto", 150), ("old", "Prezzo prec.", 90),
                        ("new", "Prezzo nuovo", 90), ("pct", "Variazione", 90),
                        ("date", "Data", 90)]:
            self.alert_tree.heading(c, text=t)
            self.alert_tree.column(c, width=w, anchor="center" if c != "name" else "w")
        self.alert_tree.pack(fill="both", expand=True, padx=10, pady=10)

    def _make_card(self, parent, label, value, color):
        card = tk.Frame(parent, bg=WHITE, bd=1, relief="solid")
        card.pack(side="left", fill="x", expand=True, padx=(0, 14), ipady=10)
        tk.Label(card, text=label, font=FONT, bg=WHITE, fg="#607068").pack(anchor="w", padx=16, pady=(10, 0))
        val_lbl = tk.Label(card, text=value, font=("Segoe UI", 22, "bold"), bg=WHITE, fg=color)
        val_lbl.pack(anchor="w", padx=16, pady=(0, 10))
        return val_lbl

    def on_show(self):
        db = self.app.db
        products = db.list_products()
        low = db.low_stock_products()
        alerts = db.recent_price_alerts(limit=30)

        self.card_total.config(text=str(len(products)))
        self.card_low.config(text=str(len(low)))
        self.card_alerts.config(text=str(len(alerts)))

        self.low_tree.delete(*self.low_tree.get_children())
        for p in low:
            self.low_tree.insert("", "end", values=(p["code"] or "-", p["name"],
                                                      fmt_num(p["quantity"]), fmt_num(p["reorder_threshold"])))

        self.alert_tree.delete(*self.alert_tree.get_children())
        for a in alerts:
            arrow = "▲" if a["pct_change"] > 0 else "▼"
            self.alert_tree.insert("", "end", values=(
                a["product_name"], fmt_price(a["old_price"]), fmt_price(a["new_price"]),
                f"{arrow} {abs(a['pct_change']):.1f}%", fmt_date(a["date"])))


# =======================================================================
# PRODOTTI (Inventario)
# =======================================================================
class InventoryFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=28, pady=(24, 10))
        tk.Label(top, text="Prodotti a magazzino", font=FONT_TITLE, bg=BG, fg=TEXT_DARK).pack(side="left")

        btn_frame = tk.Frame(top, bg=BG)
        btn_frame.pack(side="right")
        ttk.Button(btn_frame, text="+ Nuovo prodotto", style="Accent.TButton",
                   command=self.open_new_product).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Modifica", command=self.open_edit_product).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Elimina", command=self.delete_selected).pack(side="left", padx=4)

        search_row = tk.Frame(self, bg=BG)
        search_row.pack(fill="x", padx=28)
        tk.Label(search_row, text="Cerca:", font=FONT, bg=BG).pack(side="left")
        self.search_var = tk.StringVar()
        entry = tk.Entry(search_row, textvariable=self.search_var, font=FONT, width=30)
        entry.pack(side="left", padx=8)
        entry.bind("<KeyRelease>", lambda e: self.refresh_list())

        table_frame = tk.Frame(self, bg=BG)
        table_frame.pack(fill="both", expand=True, padx=28, pady=16)

        cols = ("code", "name", "category", "qty", "unit", "threshold", "sale_price", "last_price", "supplier")
        headers = ["Codice", "Nome", "Categoria", "Q.ta'", "U.M.", "Soglia riordino",
                   "Prezzo vendita", "Ultimo prezzo acq.", "Fornitore"]
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c, h in zip(cols, headers):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=110, anchor="center")
        self.tree.column("name", width=180, anchor="w")
        self.tree.column("supplier", width=130, anchor="w")
        self.tree.pack(fill="both", expand=True, side="left")

        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.tag_configure("low", foreground=DANGER)

    def on_show(self):
        self.refresh_list()

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        products = self.app.db.list_products(search=self.search_var.get().strip() or None)
        for p in products:
            tag = "low" if p["quantity"] <= p["reorder_threshold"] else ""
            self.tree.insert("", "end", iid=str(p["id"]), values=(
                p["code"] or "-", p["name"], p["category"] or "-",
                fmt_num(p["quantity"]), p["unit"] or "pz", fmt_num(p["reorder_threshold"]),
                fmt_price(p["sale_price"]), fmt_price(p["last_order_price"]), p["supplier"] or "-",
            ), tags=(tag,))

    def _selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def open_new_product(self):
        ProductDialog(self, self.app.db, on_saved=self.after_change)

    def open_edit_product(self):
        pid = self._selected_id()
        if not pid:
            messagebox.showinfo("Modifica prodotto", "Seleziona prima un prodotto dalla lista.")
            return
        ProductDialog(self, self.app.db, product_id=pid, on_saved=self.after_change)

    def delete_selected(self):
        pid = self._selected_id()
        if not pid:
            messagebox.showinfo("Elimina prodotto", "Seleziona prima un prodotto dalla lista.")
            return
        if messagebox.askyesno("Conferma", "Eliminare il prodotto selezionato? Lo storico movimenti sara' conservato."):
            self.app.db.delete_product(pid)
            self.after_change()

    def after_change(self):
        self.refresh_list()
        self.app.refresh_all()


class ProductDialog(tk.Toplevel):
    def __init__(self, parent, db, product_id=None, on_saved=None):
        super().__init__(parent)
        self.db = db
        self.product_id = product_id
        self.on_saved = on_saved
        self.title("Modifica prodotto" if product_id else "Nuovo prodotto")
        self.configure(bg=WHITE, padx=20, pady=20)
        self.resizable(False, False)
        self.grab_set()

        fields = [
            ("code", "Codice articolo"), ("name", "Nome *"), ("category", "Categoria"),
            ("unit", "Unita' di misura (pz, kg, lt...)"), ("quantity", "Quantita' attuale"),
            ("reorder_threshold", "Soglia riordino"), ("sale_price", "Prezzo di vendita (€)"),
            ("supplier", "Fornitore"), ("notes", "Note"),
        ]
        self.vars = {}
        for i, (key, label) in enumerate(fields):
            tk.Label(self, text=label, font=FONT, bg=WHITE, fg=TEXT_DARK).grid(
                row=i, column=0, sticky="w", pady=5)
            var = tk.StringVar()
            tk.Entry(self, textvariable=var, font=FONT, width=32).grid(row=i, column=1, pady=5, padx=(10, 0))
            self.vars[key] = var

        if product_id:
            p = db.get_product(product_id)
            for key in self.vars:
                val = p[key]
                self.vars[key].set("" if val is None else str(val))

        btn_row = tk.Frame(self, bg=WHITE)
        btn_row.grid(row=len(fields), column=0, columnspan=2, pady=(16, 0), sticky="e")
        ttk.Button(btn_row, text="Annulla", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btn_row, text="Salva", style="Accent.TButton", command=self.save).pack(side="right", padx=4)

    def save(self):
        name = self.vars["name"].get().strip()
        if not name:
            messagebox.showerror("Errore", "Il nome del prodotto e' obbligatorio.")
            return
        try:
            data = {
                "code": self.vars["code"].get().strip() or None,
                "name": name,
                "category": self.vars["category"].get().strip() or None,
                "unit": self.vars["unit"].get().strip() or "pz",
                "quantity": float(self.vars["quantity"].get() or 0),
                "reorder_threshold": float(self.vars["reorder_threshold"].get() or 0),
                "sale_price": float(self.vars["sale_price"].get() or 0),
                "supplier": self.vars["supplier"].get().strip() or None,
                "notes": self.vars["notes"].get().strip() or None,
                "last_order_price": None,
                "last_order_date": None,
            }
        except ValueError:
            messagebox.showerror("Errore", "Quantita', soglia e prezzo devono essere numeri validi.")
            return

        try:
            if self.product_id:
                self.db.update_product(self.product_id, data)
            else:
                self.db.add_product(data)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare: {e}")
            return

        if self.on_saved:
            self.on_saved()
        self.destroy()


# =======================================================================
# MOVIMENTI (Ingressi / Uscite)
# =======================================================================
class MovementsFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=28, pady=(24, 10))
        tk.Label(top, text="Ingressi e Uscite merce", font=FONT_TITLE, bg=BG, fg=TEXT_DARK).pack(side="left")

        form = tk.LabelFrame(self, text=" Registra movimento ", font=FONT_BOLD, bg=WHITE,
                              fg=TEXT_DARK, bd=1, relief="solid")
        form.pack(fill="x", padx=28, pady=10)

        row = tk.Frame(form, bg=WHITE)
        row.pack(fill="x", padx=14, pady=14)

        tk.Label(row, text="Prodotto:", font=FONT, bg=WHITE).grid(row=0, column=0, sticky="w")
        self.product_var = tk.StringVar()
        self.product_combo = ttk.Combobox(row, textvariable=self.product_var, width=32, state="readonly")
        self.product_combo.grid(row=0, column=1, padx=8)

        tk.Label(row, text="Tipo:", font=FONT, bg=WHITE).grid(row=0, column=2, sticky="w", padx=(20, 0))
        self.type_var = tk.StringVar(value="carico")
        type_combo = ttk.Combobox(row, textvariable=self.type_var, width=18, state="readonly",
                                   values=["carico (ingresso)", "scarico (uscita)"])
        type_combo.current(0)
        type_combo.grid(row=0, column=3, padx=8)

        tk.Label(row, text="Quantita':", font=FONT, bg=WHITE).grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.qty_var = tk.StringVar()
        tk.Entry(row, textvariable=self.qty_var, width=15).grid(row=1, column=1, sticky="w", pady=(10, 0), padx=8)

        tk.Label(row, text="Prezzo unitario acquisto (€, solo ingresso):", font=FONT, bg=WHITE).grid(
            row=1, column=2, sticky="w", pady=(10, 0), padx=(20, 0))
        self.price_var = tk.StringVar()
        tk.Entry(row, textvariable=self.price_var, width=15).grid(row=1, column=3, sticky="w", pady=(10, 0), padx=8)

        tk.Label(row, text="Data (AAAA-MM-GG):", font=FONT, bg=WHITE).grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.date_var = tk.StringVar(value=datetime.date.today().isoformat())
        tk.Entry(row, textvariable=self.date_var, width=15).grid(row=2, column=1, sticky="w", pady=(10, 0), padx=8)

        tk.Label(row, text="Nota:", font=FONT, bg=WHITE).grid(row=2, column=2, sticky="w", pady=(10, 0), padx=(20, 0))
        self.note_var = tk.StringVar()
        tk.Entry(row, textvariable=self.note_var, width=30).grid(row=2, column=3, sticky="w", pady=(10, 0), padx=8)

        ttk.Button(row, text="Registra movimento", style="Accent.TButton",
                   command=self.register_movement).grid(row=3, column=3, sticky="e", pady=(14, 0))

        hist_frame = tk.LabelFrame(self, text=" Storico movimenti ", font=FONT_BOLD, bg=WHITE,
                                    fg=TEXT_DARK, bd=1, relief="solid")
        hist_frame.pack(fill="both", expand=True, padx=28, pady=(6, 24))
        cols = ("date", "product", "type", "qty", "price", "note")
        self.hist_tree = ttk.Treeview(hist_frame, columns=cols, show="headings")
        for c, h, w in [("date", "Data", 90), ("product", "Prodotto", 200), ("type", "Tipo", 90),
                        ("qty", "Q.ta'", 70), ("price", "Prezzo unit.", 90), ("note", "Nota", 220)]:
            self.hist_tree.heading(c, text=h)
            self.hist_tree.column(c, width=w, anchor="center" if c not in ("product", "note") else "w")
        self.hist_tree.pack(fill="both", expand=True, padx=10, pady=10)

        self._products_cache = []

    def on_show(self):
        self._products_cache = self.app.db.list_products()
        self.product_combo["values"] = [f'{p["id"]} - {p["name"]}' for p in self._products_cache]
        self.refresh_history()

    def refresh_history(self):
        self.hist_tree.delete(*self.hist_tree.get_children())
        for m in self.app.db.list_movements():
            self.hist_tree.insert("", "end", values=(
                fmt_date(m["date"]), f'{m["product_name"]} ({m["product_code"] or "-"})',
                "Ingresso" if m["type"] == "carico" else "Uscita",
                fmt_num(m["quantity"]), fmt_price(m["unit_price"]) if m["unit_price"] else "-",
                m["note"] or "",
            ))

    def register_movement(self):
        sel = self.product_var.get()
        if not sel:
            messagebox.showinfo("Movimento", "Seleziona un prodotto.")
            return
        product_id = int(sel.split(" - ")[0])
        mtype = "carico" if self.type_var.get().startswith("carico") else "scarico"

        try:
            qty = float(self.qty_var.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Errore", "Inserisci una quantita' numerica maggiore di zero.")
            return

        price = None
        if self.price_var.get().strip():
            try:
                price = float(self.price_var.get())
            except ValueError:
                messagebox.showerror("Errore", "Il prezzo unitario deve essere un numero.")
                return

        date = self.date_var.get().strip() or datetime.date.today().isoformat()

        try:
            alert = self.app.db.add_movement(
                product_id, mtype, qty, unit_price=price, date=date, note=self.note_var.get().strip()
            )
        except Exception as e:
            messagebox.showerror("Errore", str(e))
            return

        if alert.get("alert"):
            direction = "aumentato" if alert["pct"] > 0 else "diminuito"
            messagebox.showwarning(
                "Variazione di prezzo rilevata",
                f"Il prezzo di acquisto e' {direction} del {abs(alert['pct']):.1f}%\n"
                f"rispetto all'ultimo ordine (da €{alert['old']:.2f} a €{alert['new']:.2f})."
            )

        self.qty_var.set("")
        self.price_var.set("")
        self.note_var.set("")
        self.refresh_history()
        self.app.refresh_all()


# =======================================================================
# CATALOGO PDF
# =======================================================================
class CatalogFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app

        tk.Label(self, text="Esporta catalogo per il cliente", font=FONT_TITLE, bg=BG, fg=TEXT_DARK).pack(
            anchor="w", padx=28, pady=(24, 4))
        tk.Label(self, text="Genera un PDF con i prodotti attivi, raggruppati per categoria e con il prezzo di vendita.",
                 font=FONT, bg=BG, fg="#607068").pack(anchor="w", padx=28, pady=(0, 20))

        box = tk.LabelFrame(self, text=" Opzioni esportazione ", font=FONT_BOLD, bg=WHITE,
                             fg=TEXT_DARK, bd=1, relief="solid")
        box.pack(fill="x", padx=28)

        row = tk.Frame(box, bg=WHITE)
        row.pack(fill="x", padx=16, pady=16)

        self.show_code_var = tk.BooleanVar(value=True)
        tk.Checkbutton(row, text="Includi codice articolo", variable=self.show_code_var,
                       bg=WHITE, font=FONT).grid(row=0, column=0, sticky="w", columnspan=2)

        tk.Label(row, text="Categoria (vuoto = tutte):", font=FONT, bg=WHITE).grid(
            row=1, column=0, sticky="w", pady=(12, 0))
        self.cat_var = tk.StringVar()
        self.cat_combo = ttk.Combobox(row, textvariable=self.cat_var, width=25, state="readonly")
        self.cat_combo.grid(row=1, column=1, sticky="w", pady=(12, 0), padx=8)

        ttk.Button(box, text="📄  Genera catalogo PDF", style="Accent.TButton",
                   command=self.generate).pack(anchor="w", padx=16, pady=(4, 16))

        self.status_lbl = tk.Label(self, text="", font=FONT, bg=BG, fg=ACCENT)
        self.status_lbl.pack(anchor="w", padx=28, pady=8)

    def on_show(self):
        cats = [""] + self.app.db.categories()
        self.cat_combo["values"] = cats

    def generate(self):
        products = self.app.db.list_products()
        cat_filter = self.cat_var.get().strip()
        if cat_filter:
            products = [p for p in products if (p["category"] or "") == cat_filter]
        if not products:
            messagebox.showinfo("Catalogo", "Nessun prodotto da esportare con i filtri scelti.")
            return

        default_name = f"catalogo_{datetime.date.today().isoformat()}.pdf"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf", initialfile=default_name,
            filetypes=[("File PDF", "*.pdf")], title="Salva catalogo come...",
        )
        if not filepath:
            return

        company = self.app.db.get_setting("azienda_nome", "")
        try:
            export_catalog(products, filepath, company_name=company, show_code=self.show_code_var.get())
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la generazione del PDF:\n{e}")
            return

        self.status_lbl.config(text=f"✔ Catalogo salvato in: {filepath}")
        messagebox.showinfo("Fatto", "Catalogo PDF generato con successo!")


# =======================================================================
# IMPOSTAZIONI (incluso backup / Google Drive)
# =======================================================================
class SettingsFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app

        tk.Label(self, text="Impostazioni", font=FONT_TITLE, bg=BG, fg=TEXT_DARK).pack(
            anchor="w", padx=28, pady=(24, 16))

        general = tk.LabelFrame(self, text=" Generali ", font=FONT_BOLD, bg=WHITE,
                                 fg=TEXT_DARK, bd=1, relief="solid")
        general.pack(fill="x", padx=28, pady=8)
        g_row = tk.Frame(general, bg=WHITE)
        g_row.pack(fill="x", padx=16, pady=14)

        tk.Label(g_row, text="Nome attivita' (mostrato sul catalogo):", font=FONT, bg=WHITE).grid(
            row=0, column=0, sticky="w")
        self.company_var = tk.StringVar()
        tk.Entry(g_row, textvariable=self.company_var, width=35).grid(row=0, column=1, padx=8)

        tk.Label(g_row, text="Soglia % variazione prezzo per notifica:", font=FONT, bg=WHITE).grid(
            row=1, column=0, sticky="w", pady=(10, 0))
        self.threshold_var = tk.StringVar()
        tk.Entry(g_row, textvariable=self.threshold_var, width=10).grid(
            row=1, column=1, sticky="w", padx=8, pady=(10, 0))

        ttk.Button(general, text="Salva impostazioni generali", style="Accent.TButton",
                   command=self.save_general).pack(anchor="w", padx=16, pady=(0, 14))

        backup = tk.LabelFrame(self, text=" Backup e Google Drive ", font=FONT_BOLD, bg=WHITE,
                                fg=TEXT_DARK, bd=1, relief="solid")
        backup.pack(fill="x", padx=28, pady=8)

        tk.Label(backup, justify="left", bg=WHITE, font=FONT, fg="#607068", wraplength=760, text=(
            "Il database del magazzino viene sempre salvato in locale (file magazzino.db accanto al programma).\n"
            "Per avere anche una copia su Google Drive, installa l'app 'Google Drive per desktop', poi seleziona "
            "qui sotto la cartella sincronizzata con Drive (es. G:\\Il mio Drive\\Gestionale): ad ogni backup verra' "
            "copiato li' un file aggiornato, che Google Drive sincronizzera' automaticamente online."
        )).pack(anchor="w", padx=16, pady=(14, 10))

        b_row = tk.Frame(backup, bg=WHITE)
        b_row.pack(fill="x", padx=16, pady=(0, 10))
        tk.Label(b_row, text="Cartella di backup (es. cartella Google Drive):", font=FONT, bg=WHITE).grid(
            row=0, column=0, sticky="w")
        self.folder_var = tk.StringVar()
        tk.Entry(b_row, textvariable=self.folder_var, width=50).grid(row=0, column=1, padx=8)
        ttk.Button(b_row, text="Sfoglia...", command=self.browse_folder).grid(row=0, column=2, padx=4)

        self.auto_backup_var = tk.BooleanVar()
        tk.Checkbutton(backup, text="Esegui backup automatico ogni volta che chiudo il programma",
                       variable=self.auto_backup_var, bg=WHITE, font=FONT).pack(anchor="w", padx=16, pady=(0, 10))

        btn_row2 = tk.Frame(backup, bg=WHITE)
        btn_row2.pack(anchor="w", padx=16, pady=(0, 16))
        ttk.Button(btn_row2, text="Salva impostazioni backup", command=self.save_backup_settings).pack(
            side="left", padx=(0, 8))
        ttk.Button(btn_row2, text="💾  Esegui backup ora", style="Accent.TButton",
                   command=self.run_backup_now).pack(side="left")

        self.status_lbl = tk.Label(self, text="", font=FONT, bg=BG, fg=ACCENT)
        self.status_lbl.pack(anchor="w", padx=28, pady=8)

    def on_show(self):
        db = self.app.db
        self.company_var.set(db.get_setting("azienda_nome", ""))
        self.threshold_var.set(db.get_setting("price_alert_threshold", "10"))
        self.folder_var.set(db.get_setting("backup_folder", ""))
        self.auto_backup_var.set(db.get_setting("auto_backup", "0") == "1")

    def save_general(self):
        try:
            float(self.threshold_var.get())
        except ValueError:
            messagebox.showerror("Errore", "La soglia deve essere un numero (es. 10 per 10%).")
            return
        self.app.db.set_setting("azienda_nome", self.company_var.get().strip())
        self.app.db.set_setting("price_alert_threshold", self.threshold_var.get().strip())
        self.status_lbl.config(text="✔ Impostazioni generali salvate.")

    def browse_folder(self):
        folder = filedialog.askdirectory(title="Seleziona la cartella di backup / Google Drive")
        if folder:
            self.folder_var.set(folder)

    def save_backup_settings(self):
        self.app.db.set_setting("backup_folder", self.folder_var.get().strip())
        self.app.db.set_setting("auto_backup", "1" if self.auto_backup_var.get() else "0")
        self.status_lbl.config(text="✔ Impostazioni di backup salvate.")

    def run_backup_now(self):
        self.save_backup_settings()
        ok, msg = do_backup(self.app.db)
        self.status_lbl.config(text=msg, fg=ACCENT if ok else DANGER)
        if ok:
            messagebox.showinfo("Backup", msg)
        else:
            messagebox.showerror("Backup", msg)


# =======================================================================
# Utility
# =======================================================================
def do_backup(db, silent=False):
    folder = db.get_setting("backup_folder", "")
    if not folder:
        return False, "Nessuna cartella di backup impostata."
    if not os.path.isdir(folder):
        return False, f"La cartella '{folder}' non esiste piu'."
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(folder, f"magazzino_backup_{ts}.db")
    try:
        shutil.copy2(db.path, dest)
        return True, f"✔ Backup completato: {dest}"
    except Exception as e:
        return False, f"Backup fallito: {e}"


def fmt_num(v):
    if v is None:
        return "-"
    v = float(v)
    return str(int(v)) if v == int(v) else f"{v:g}"


def fmt_price(v):
    if v is None:
        return "-"
    return f"€ {float(v):.2f}"


def fmt_date(v):
    try:
        return datetime.date.fromisoformat(v).strftime("%d/%m/%Y")
    except Exception:
        return v or "-"
