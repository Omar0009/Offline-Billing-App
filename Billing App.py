import hashlib
import os
import sqlite3
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from num2words import num2words
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Matplotlib setup for Tkinter Integration
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

DB_FILE = "billing_data.db"

# ----------------------------------------------------------------------
# Database Controller & Authentication
# ----------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_no TEXT UNIQUE,
            company_name TEXT,
            client_name TEXT,
            client_dept TEXT,
            client_attn TEXT,
            bill_date TEXT,
            payment_terms TEXT,
            order_type TEXT,
            status TEXT,
            discount REAL,
            vat REAL,
            subtotal REAL,
            net_total REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_no TEXT,
            item_desc TEXT,
            item_sub TEXT,
            qty INTEGER,
            unit TEXT,
            rate REAL,
            FOREIGN KEY (bill_no) REFERENCES invoices (bill_no) ON DELETE CASCADE
        )
    ''')
    
    target_pass_hash = hashlib.sha256("GreenSource2007".encode()).hexdigest()
    cursor.execute("SELECT id FROM users WHERE username = ?", ("GreenSource",))
    row = cursor.fetchone()
    
    if row:
        cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (target_pass_hash, "GreenSource"))
    else:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("GreenSource", target_pass_hash))
        
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0] == hash_password(password):
        return True
    return False

def save_invoice_to_db(bill_data, items, subtotal, net_total):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM invoices WHERE bill_no = ?", (bill_data['bill_no'],))
    existing = cursor.fetchone()

    if existing:
        cursor.execute('''
            UPDATE invoices SET 
            company_name=?, client_name=?, client_dept=?, client_attn=?, bill_date=?, 
            payment_terms=?, order_type=?, status=?, discount=?, vat=?, subtotal=?, net_total=?
            WHERE bill_no=?
        ''', (
            bill_data['company_name'], bill_data['client_name'], bill_data['client_dept'], bill_data['client_attn'],
            bill_data['bill_date'], bill_data['payment_terms'], bill_data['order_type'], bill_data['status'],
            bill_data['discount'], bill_data['vat'], subtotal, net_total, bill_data['bill_no']
        ))
        cursor.execute("DELETE FROM invoice_items WHERE bill_no=?", (bill_data['bill_no'],))
    else:
        cursor.execute('''
            INSERT INTO invoices (bill_no, company_name, client_name, client_dept, client_attn, bill_date, payment_terms, order_type, status, discount, vat, subtotal, net_total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            bill_data['bill_no'], bill_data['company_name'], bill_data['client_name'], bill_data['client_dept'],
            bill_data['client_attn'], bill_data['bill_date'], bill_data['payment_terms'], bill_data['order_type'],
            bill_data['status'], bill_data['discount'], bill_data['vat'], subtotal, net_total
        ))

    for desc, sub, qty, unit, rate in items:
        cursor.execute('''
            INSERT INTO invoice_items (bill_no, item_desc, item_sub, qty, unit, rate)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (bill_data['bill_no'], desc, sub, qty, unit, rate))

    conn.commit()
    conn.close()

# ----------------------------------------------------------------------
# Modern A4 Printable PDF Generation Engine
# ----------------------------------------------------------------------
def generate_pdf_invoice(filepath, bill_data, items):
    doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    printable_width = 523.27
    elements = []
    
    PRIMARY_COLOR = colors.HexColor("#0f172a")
    ACCENT_COLOR = colors.HexColor("#059669")
    TEXT_MUTED = colors.HexColor("#475569")
    BORDER_COLOR = colors.HexColor("#cbd5e1")
    BG_LIGHT = colors.HexColor("#f8fafc")
    ROW_ALT = colors.HexColor("#f1f5f9")

    styles = getSampleStyleSheet()
    
    company_title_style = ParagraphStyle('CompTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=18, leading=20, textColor=PRIMARY_COLOR)
    subtitle_style = ParagraphStyle('SubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=11, textColor=TEXT_MUTED)
    contact_style = ParagraphStyle('Contact', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=11, textColor=PRIMARY_COLOR)
    doc_title_style = ParagraphStyle('DocTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=16, leading=18, alignment=2, textColor=ACCENT_COLOR)
    
    label_style = ParagraphStyle('MetaLabel', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=ACCENT_COLOR)
    val_style = ParagraphStyle('MetaVal', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=11, textColor=PRIMARY_COLOR)
    
    cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=PRIMARY_COLOR)
    cell_normal = ParagraphStyle('CellNormal', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, textColor=PRIMARY_COLOR)
    cell_sub = ParagraphStyle('CellSub', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=7, leading=9, textColor=TEXT_MUTED)
    table_hdr = ParagraphStyle('TblHdr', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.whitesmoke, alignment=1)

    accent_bar = Table([[""]], colWidths=[printable_width], rowHeights=[4])
    accent_bar.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), ACCENT_COLOR)]))
    elements.append(accent_bar)
    elements.append(Spacer(1, 10))

    header_data = [
        [Paragraph(f"<b>{bill_data['company_name']}</b>", company_title_style), Paragraph("<b>COMMERCIAL INVOICE</b>", doc_title_style)],
        [Paragraph(bill_data['company_subtitle'], subtitle_style), ""],
        [Paragraph(f"{bill_data['company_address']}<br/>Phone: {bill_data['company_phone']} | Email: {bill_data['company_email']}", contact_style), ""]
    ]
    header_table = Table(header_data, colWidths=[313.27, 210])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('SPAN', (0,0), (0,0))]))
    elements.append(header_table)
    elements.append(Spacer(1, 12))

    info_data = [
        [Paragraph("BILL TO (CUSTOMER)", label_style), Paragraph("INVOICE DETAILS", label_style)],
        [
            Paragraph(f"<b>{bill_data['client_name']}</b><br/>{bill_data['client_dept']}<br/><b>Attention Person:</b> {bill_data['client_attn']}", val_style),
            Paragraph(f"<b>Invoice No:</b> {bill_data['bill_no']}<br/><b>Date:</b> {bill_data['bill_date']}<br/><b>Terms:</b> {bill_data['payment_terms']}", val_style)
        ],
        [Spacer(1, 3), Spacer(1, 3)],
        [Paragraph("DELIVERY & REFERENCE", label_style), ""],
        [Paragraph(f"<b>Order Type:</b> {bill_data['order_type']}<br/><b>Status:</b> {bill_data['status']}", val_style), ""]
    ]
    info_table = Table(info_data, colWidths=[313.27, 210])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, ROW_ALT),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 12))

    item_rows = [[
        Paragraph("SL.", table_hdr),
        Paragraph("ITEM DESCRIPTION / SPECIFICATIONS", table_hdr),
        Paragraph("QTY", table_hdr),
        Paragraph("UNIT", table_hdr),
        Paragraph("RATE (৳)", table_hdr),
        Paragraph("TOTAL (৳)", table_hdr)
    ]]
    
    subtotal = 0.0
    for idx, (desc, sub_desc, qty, unit, rate) in enumerate(items, start=1):
        line_total = qty * rate
        subtotal += line_total
        
        desc_cell = [Paragraph(desc, cell_bold)]
        if sub_desc:
            desc_cell.append(Paragraph(sub_desc, cell_sub))
            
        item_rows.append([
            Paragraph(f"{idx:02d}", ParagraphStyle('C', parent=cell_normal, alignment=1)),
            desc_cell,
            Paragraph(str(qty), ParagraphStyle('C', parent=cell_normal, alignment=1)),
            Paragraph(unit, ParagraphStyle('C', parent=cell_normal, alignment=1)),
            Paragraph(f"{rate:,.2f}", ParagraphStyle('R', parent=cell_normal, alignment=2)),
            Paragraph(f"{line_total:,.2f}", ParagraphStyle('R', parent=cell_bold, alignment=2))
        ])

    items_table = Table(item_rows, colWidths=[30, 243.27, 45, 45, 80, 80])
    t_style = [
        ('BACKGROUND', (0,0), (-1,0), PRIMARY_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 5),
    ]
    for i in range(1, len(item_rows)):
        if i % 2 == 0:
            t_style.append(('BACKGROUND', (0, i), (-1, i), BG_LIGHT))
            
    items_table.setStyle(TableStyle(t_style))
    elements.append(items_table)
    elements.append(Spacer(1, 12))

    net_payable = subtotal + bill_data['vat'] - bill_data['discount']
    try:
        words = num2words(net_payable, lang='en').title() + " BDT Only."
    except Exception:
        words = f"{net_payable:,.2f} BDT Only."

    summary_data = [
        [
            Paragraph("AMOUNT IN WORDS", label_style),
            Paragraph("Sub Total:", cell_bold),
            Paragraph(f"৳ {subtotal:,.2f}", ParagraphStyle('R', parent=cell_bold, alignment=2))
        ],
        [
            Paragraph(f"<i>{words}</i>", val_style),
            Paragraph("VAT / Tax:", cell_normal),
            Paragraph(f"৳ {bill_data['vat']:,.2f}", ParagraphStyle('R', parent=cell_normal, alignment=2))
        ],
        [
            Paragraph("<br/><b>Terms & Conditions:</b><br/>"
                      "• Goods once received in good condition are not returnable.<br/>"
                      "• Please verify items and fasteners upon handover.", cell_sub),
            Paragraph("Discount:", cell_normal),
            Paragraph(f"৳ {bill_data['discount']:,.2f}", ParagraphStyle('R', parent=cell_normal, alignment=2))
        ],
        [
            "",
            Paragraph("<b>Net Payable:</b>", ParagraphStyle('NP', parent=cell_bold, fontSize=9, textColor=ACCENT_COLOR)),
            Paragraph(f"<b>৳ {net_payable:,.2f}</b>", ParagraphStyle('RNP', parent=cell_bold, fontSize=9, alignment=2, textColor=ACCENT_COLOR))
        ]
    ]
    
    summary_table = Table(summary_data, colWidths=[303.27, 110, 110])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('SPAN', (0,0), (0,1)),
        ('SPAN', (0,2), (0,3)),
        ('LINEBELOW', (1,-1), (2,-1), 1, ACCENT_COLOR),
        ('GRID', (1,0), (2,-1), 0.5, BORDER_COLOR),
        ('BACKGROUND', (1,3), (2,3), BG_LIGHT),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 35))

    sig_data = [[
        Paragraph(f"_____________________________<br/><b>Customer Sign ({bill_data['client_name']})</b>", ParagraphStyle('S1', parent=cell_normal, alignment=1)),
        Paragraph(f"_____________________________<br/><b>Authorized Sign ({bill_data['company_name']})</b>", ParagraphStyle('S2', parent=cell_normal, alignment=1))
    ]]
    sig_table = Table(sig_data, colWidths=[261.63, 261.64])
    sig_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    elements.append(sig_table)

    doc.build(elements)
    return subtotal, net_payable

# ----------------------------------------------------------------------
# Modern Clean Login Window
# ----------------------------------------------------------------------
class LoginWindow:
    def __init__(self, root, on_login_success):
        self.root = root
        self.on_login_success = on_login_success
        self.root.title("Green Source - Sign In")
        self.root.geometry("420x330")
        self.root.resizable(False, False)

        init_db()

        card = ttk.Frame(self.root, padding=25)
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="🌿 Green Source", font=("Helvetica", 18, "bold"), foreground="#059669").pack(anchor="center", pady=(0, 2))
        ttk.Label(card, text="Developed By AnonymousSoft", font=("Helvetica", 9, "italic"), foreground="#64748b").pack(anchor="center", pady=(0, 20))

        ttk.Label(card, text="Username:").pack(anchor="w", pady=(5, 2))
        self.login_user = ttk.Entry(card, width=35)
        self.login_user.pack(fill="x", pady=2)

        ttk.Label(card, text="Password:").pack(anchor="w", pady=(10, 2))
        self.login_pass = ttk.Entry(card, width=35, show="•")
        self.login_pass.pack(fill="x", pady=2)

        ttk.Button(card, text="Sign In to Workspace", command=self.handle_login).pack(fill="x", pady=20)

    def handle_login(self):
        user = self.login_user.get().strip()
        pwd = self.login_pass.get().strip()

        if verify_user(user, pwd):
            self.on_login_success(user)
        else:
            messagebox.showerror("Login Error", "Invalid Username or Password.")

# ----------------------------------------------------------------------
# Main Application Dashboard
# ----------------------------------------------------------------------
class GreenSourceBillingApp:
    def __init__(self, root, username, logout_callback):
        self.root = root
        self.username = username
        self.logout_callback = logout_callback

        self.root.title("Green Source Invoice Workspace")
        self.root.geometry("1000x850")

        self.items = []

        top_bar = ttk.Frame(root, padding=10)
        top_bar.pack(fill="x", padx=10)

        ttk.Label(top_bar, text="🌿 Green Source Workspace", font=("Helvetica", 14, "bold"), foreground="#059669").pack(side="left")
        
        user_info_frame = ttk.Frame(top_bar)
        user_info_frame.pack(side="right")
        ttk.Label(user_info_frame, text=f"👤 {self.username}", font=("Helvetica", 10, "bold")).pack(side="left", padx=10)
        ttk.Button(user_info_frame, text="🚪 Log Out", command=self.logout_callback).pack(side="right")

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_generator = ttk.Frame(self.notebook)
        self.tab_history = ttk.Frame(self.notebook)
        self.tab_analytics = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_generator, text="📝 Create Invoice")
        self.notebook.add(self.tab_history, text="📜 Invoice History")
        self.notebook.add(self.tab_analytics, text="📊 Analytics Dashboard")

        self.build_generator_tab()
        self.build_history_tab()
        self.build_analytics_tab()

    # --- TAB 1: GENERATOR ---
    def build_generator_tab(self):
        meta_frame = ttk.LabelFrame(self.tab_generator, text=" Header & Client Details ", padding=10)
        meta_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(meta_frame, text="Company Name:").grid(row=0, column=0, sticky="w")
        self.company_name = ttk.Entry(meta_frame, width=28)
        self.company_name.insert(0, "GREEN SOURCE")
        self.company_name.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(meta_frame, text="Bill No:").grid(row=0, column=2, sticky="w")
        self.bill_no = ttk.Entry(meta_frame, width=25)
        self.bill_no.insert(0, "BILL-GS-20261018-01")
        self.bill_no.grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(meta_frame, text="Client Name:").grid(row=1, column=0, sticky="w")
        self.client_name = ttk.Entry(meta_frame, width=28)
        self.client_name.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(meta_frame, text="Bill Date:").grid(row=1, column=2, sticky="w")
        self.bill_date = ttk.Entry(meta_frame, width=25)
        self.bill_date.insert(0, "October 18, 2026")
        self.bill_date.grid(row=1, column=3, padx=5, pady=2)

        ttk.Label(meta_frame, text="Client Dept:").grid(row=2, column=0, sticky="w")
        self.client_dept = ttk.Entry(meta_frame, width=28)
        self.client_dept.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(meta_frame, text="Attention Person:").grid(row=2, column=2, sticky="w")
        self.client_attn = ttk.Entry(meta_frame, width=25)
        self.client_attn.grid(row=2, column=3, padx=5, pady=2)

        ttk.Label(meta_frame, text="Order Type:").grid(row=3, column=0, sticky="w")
        self.order_type = ttk.Entry(meta_frame, width=28)
        self.order_type.grid(row=3, column=1, padx=5, pady=2)

        ttk.Label(meta_frame, text="Payment Terms:").grid(row=3, column=2, sticky="w")
        self.payment_terms = ttk.Entry(meta_frame, width=25)
        self.payment_terms.insert(0, "Due on Delivery")
        self.payment_terms.grid(row=3, column=3, padx=5, pady=2)

        ttk.Label(meta_frame, text="Invoice Status:").grid(row=4, column=0, sticky="w")
        self.status_cb = ttk.Combobox(meta_frame, width=26, state="readonly", values=[
            "Dispatched / Ready for Handover",
            "Paid",
            "Pending / Unpaid",
            "Draft",
            "Cancelled"
        ])
        self.status_cb.current(0)
        self.status_cb.grid(row=4, column=1, padx=5, pady=2)

        item_frame = ttk.LabelFrame(self.tab_generator, text=" Line Items ", padding=10)
        item_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(item_frame, text="Item Name:").grid(row=0, column=0, sticky="w")
        self.item_desc = ttk.Entry(item_frame, width=22)
        self.item_desc.grid(row=0, column=1, padx=2)

        ttk.Label(item_frame, text="Specs/Details:").grid(row=0, column=2, sticky="w")
        self.item_sub = ttk.Entry(item_frame, width=22)
        self.item_sub.grid(row=0, column=3, padx=2)

        ttk.Label(item_frame, text="Qty:").grid(row=1, column=0, sticky="w")
        self.item_qty = ttk.Entry(item_frame, width=10)
        self.item_qty.grid(row=1, column=1, sticky="w", padx=2)

        ttk.Label(item_frame, text="Unit:").grid(row=1, column=2, sticky="w")
        self.item_unit = ttk.Entry(item_frame, width=10)
        self.item_unit.insert(0, "Nos")
        self.item_unit.grid(row=1, column=3, sticky="w", padx=2)

        ttk.Label(item_frame, text="Unit Rate (৳):").grid(row=1, column=4, sticky="w")
        self.item_rate = ttk.Entry(item_frame, width=10)
        self.item_rate.grid(row=1, column=5, sticky="w", padx=2)

        ttk.Button(item_frame, text="➕ Add Item", command=self.add_item).grid(row=1, column=6, padx=5)

        table_frame = ttk.Frame(self.tab_generator, padding=10)
        table_frame.pack(fill="both", expand=True, padx=10)

        columns = ("#", "Description", "Details", "Qty", "Unit", "Rate", "Total")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=80, anchor="center")
        self.tree.column("Description", width=240, anchor="w")
        self.tree.column("Details", width=240, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        adj_frame = ttk.LabelFrame(self.tab_generator, text=" Adjustments ", padding=10)
        adj_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(adj_frame, text="Discount Amount (৳):").grid(row=0, column=0, sticky="w")
        self.discount_entry = ttk.Entry(adj_frame, width=15)
        self.discount_entry.insert(0, "0.00")
        self.discount_entry.grid(row=0, column=1, padx=5)

        ttk.Label(adj_frame, text="VAT / Tax (৳):").grid(row=0, column=2, sticky="w", padx=(20, 0))
        self.vat_entry = ttk.Entry(adj_frame, width=15)
        self.vat_entry.insert(0, "0.00")
        self.vat_entry.grid(row=0, column=3, padx=5)

        btn_frame = ttk.Frame(self.tab_generator, padding=10)
        btn_frame.pack(fill="x", padx=10)

        ttk.Button(btn_frame, text="❌ Delete Item", command=self.delete_item).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🧹 Clear All", command=self.clear_all_items).pack(side="left", padx=5)
        
        ttk.Button(btn_frame, text="🖨️ Save & Print", command=self.save_and_print_pdf).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="💾 Save & Generate PDF", command=self.create_and_save_pdf).pack(side="right", padx=5)

    def add_item(self):
        desc = self.item_desc.get().strip()
        sub = self.item_sub.get().strip()
        if not desc:
            messagebox.showwarning("Input Error", "Please enter an Item Name.")
            return

        try:
            qty = int(self.item_qty.get().strip())
            rate = float(self.item_rate.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Input", "Quantity and Unit Rate must be numbers.")
            return

        unit = self.item_unit.get().strip() or "Nos"
        self.items.append((desc, sub, qty, unit, rate))
        self.refresh_table()

        self.item_desc.delete(0, tk.END)
        self.item_sub.delete(0, tk.END)
        self.item_qty.delete(0, tk.END)
        self.item_rate.delete(0, tk.END)

    def delete_item(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Select an item from the table to delete.")
            return
        for sel in selected:
            index = int(self.tree.item(sel)['values'][0]) - 1
            if 0 <= index < len(self.items):
                del self.items[index]
        self.refresh_table()

    def clear_all_items(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to clear all items?"):
            self.items.clear()
            self.refresh_table()

    def refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, (desc, sub, qty, unit, rate) in enumerate(self.items, start=1):
            line_total = qty * rate
            self.tree.insert("", "end", values=(idx, desc, sub, qty, unit, f"{rate:,.2f}", f"{line_total:,.2f}"))

    def process_pdf_creation(self):
        if not self.items:
            messagebox.showwarning("Warning", "Add at least one item before generating.")
            return None

        try:
            discount_val = float(self.discount_entry.get().strip() or 0.0)
            vat_val = float(self.vat_entry.get().strip() or 0.0)
        except ValueError:
            messagebox.showerror("Invalid Input", "Discount and VAT must be numeric values.")
            return None

        bill_data = {
            "company_name": self.company_name.get(),
            "company_subtitle": "Solar Energy Engineering, Structures & Hardware Supply",
            "company_address": "Mirpur 11, Pallabi, Dhaka-1216, Bangladesh",
            "company_phone": "+880 167-2550000",
            "company_email": "intaltechnologyltd.bd@gmail.com",
            "client_name": self.client_name.get(),
            "client_dept": self.client_dept.get(),
            "client_attn": self.client_attn.get(),
            "bill_no": self.bill_no.get(),
            "bill_date": self.bill_date.get(),
            "payment_terms": self.payment_terms.get(),
            "order_type": self.order_type.get(),
            "status": self.status_cb.get(),
            "vat": vat_val,
            "discount": discount_val
        }

        output_filename = f"{self.bill_no.get().replace('/', '_')}.pdf"

        try:
            subtotal, net_total = generate_pdf_invoice(output_filename, bill_data, self.items)
            save_invoice_to_db(bill_data, self.items, subtotal, net_total)
            self.load_history()
            self.render_analytics()
            return os.path.abspath(output_filename)
        except PermissionError:
            messagebox.showerror("File Locked Error", f"Cannot write to '{output_filename}'. Please close the open PDF viewer.")
            return None
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate PDF:\n{str(e)}")
            return None

    def create_and_save_pdf(self):
        filepath = self.process_pdf_creation()
        if filepath:
            messagebox.showinfo("Success", f"Invoice saved to database and PDF generated!\nSaved as: {filepath}")

    def save_and_print_pdf(self):
        filepath = self.process_pdf_creation()
        if filepath:
            if sys.platform == "win32":
                os.startfile(filepath)
            elif sys.platform == "darwin":
                subprocess.run(["open", filepath])
            else:
                subprocess.run(["xdg-open", filepath])

    # --- TAB 2: HISTORY ---
    def build_history_tab(self):
        hist_frame = ttk.Frame(self.tab_history, padding=10)
        hist_frame.pack(fill="both", expand=True)

        columns = ("ID", "Bill No", "Client", "Date", "Status", "Discount", "VAT", "Net Total")
        self.hist_tree = ttk.Treeview(hist_frame, columns=columns, show="headings", height=15)
        for col in columns:
            self.hist_tree.heading(col, text=col)
            self.hist_tree.column(col, width=95, anchor="center")
        self.hist_tree.column("Client", width=180, anchor="w")
        self.hist_tree.column("Status", width=140, anchor="center")
        self.hist_tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(hist_frame, orient="vertical", command=self.hist_tree.yview)
        self.hist_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        ctrl_frame = ttk.Frame(self.tab_history, padding=10)
        ctrl_frame.pack(fill="x")

        ttk.Button(ctrl_frame, text="✏️ Edit Invoice", command=self.edit_selected_invoice).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="🗑️ Delete Record", command=self.delete_history_record).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="🔄 Refresh List", command=self.load_history).pack(side="right", padx=5)

        self.load_history()

    def load_history(self):
        for item in self.hist_tree.get_children():
            self.hist_tree.delete(item)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, bill_no, client_name, bill_date, status, discount, vat, net_total FROM invoices ORDER BY id DESC")
        rows = cursor.fetchall()
        for r in rows:
            self.hist_tree.insert("", "end", values=(r[0], r[1], r[2], r[3], r[4], f"৳{r[5]:,.2f}", f"৳{r[6]:,.2f}", f"৳{r[7]:,.2f}"))
        conn.close()

    def edit_selected_invoice(self):
        selected = self.hist_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Select an invoice from the history list to edit.")
            return

        bill_no = self.hist_tree.item(selected[0])['values'][1]
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT company_name, client_name, client_dept, client_attn, bill_no, bill_date, payment_terms, order_type, status, discount, vat FROM invoices WHERE bill_no=?", (bill_no,))
        inv = cursor.fetchone()

        if inv:
            self.company_name.delete(0, tk.END); self.company_name.insert(0, inv[0])
            self.client_name.delete(0, tk.END); self.client_name.insert(0, inv[1])
            self.client_dept.delete(0, tk.END); self.client_dept.insert(0, inv[2])
            self.client_attn.delete(0, tk.END); self.client_attn.insert(0, inv[3])
            self.bill_no.delete(0, tk.END); self.bill_no.insert(0, inv[4])
            self.bill_date.delete(0, tk.END); self.bill_date.insert(0, inv[5])
            self.payment_terms.delete(0, tk.END); self.payment_terms.insert(0, inv[6])
            self.order_type.delete(0, tk.END); self.order_type.insert(0, inv[7])
            self.status_cb.set(inv[8])
            self.discount_entry.delete(0, tk.END); self.discount_entry.insert(0, str(inv[9]))
            self.vat_entry.delete(0, tk.END); self.vat_entry.insert(0, str(inv[10]))

            cursor.execute("SELECT item_desc, item_sub, qty, unit, rate FROM invoice_items WHERE bill_no=?", (bill_no,))
            self.items = cursor.fetchall()
            self.refresh_table()
            
            self.notebook.select(self.tab_generator)
            messagebox.showinfo("Loaded for Editing", f"Invoice {bill_no} loaded into generator! Make changes and click Save.")
        conn.close()

    def delete_history_record(self):
        selected = self.hist_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Select an invoice record to delete.")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to permanently delete this invoice record?"):
            bill_no = self.hist_tree.item(selected[0])['values'][1]
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM invoices WHERE bill_no=?", (bill_no,))
            cursor.execute("DELETE FROM invoice_items WHERE bill_no=?", (bill_no,))
            conn.commit()
            conn.close()
            self.load_history()
            self.render_analytics()

    # --- TAB 3: ANALYTICS ---
    def build_analytics_tab(self):
        self.kpi_frame = ttk.Frame(self.tab_analytics, padding=10)
        self.kpi_frame.pack(fill="x")

        self.chart_frame = ttk.Frame(self.tab_analytics, padding=10)
        self.chart_frame.pack(fill="both", expand=True)
        self.render_analytics()

    def render_analytics(self):
        for widget in self.kpi_frame.winfo_children():
            widget.destroy()
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*), SUM(net_total), AVG(net_total) FROM invoices")
        kpi_row = cursor.fetchone()
        total_count = kpi_row[0] or 0
        total_rev = kpi_row[1] or 0.0
        avg_val = kpi_row[2] or 0.0

        cursor.execute("SELECT status, COUNT(*), SUM(net_total) FROM invoices GROUP BY status")
        status_data = cursor.fetchall()

        cursor.execute("SELECT bill_date, SUM(net_total) FROM invoices GROUP BY bill_date")
        sales_by_date = cursor.fetchall()

        cursor.execute("SELECT item_desc, SUM(qty * rate) FROM invoice_items GROUP BY item_desc ORDER BY SUM(qty * rate) DESC LIMIT 5")
        top_items = cursor.fetchall()
        conn.close()

        # Render KPI Cards
        card1 = ttk.LabelFrame(self.kpi_frame, text=" Total Revenue ", padding=8)
        card1.pack(side="left", expand=True, fill="x", padx=5)
        ttk.Label(card1, text=f"৳ {total_rev:,.2f}", font=("Helvetica", 12, "bold"), foreground="#059669").pack()

        card2 = ttk.LabelFrame(self.kpi_frame, text=" Total Invoices ", padding=8)
        card2.pack(side="left", expand=True, fill="x", padx=5)
        ttk.Label(card2, text=f"{total_count} Issued", font=("Helvetica", 12, "bold"), foreground="#0284c7").pack()

        card3 = ttk.LabelFrame(self.kpi_frame, text=" Avg Invoice Value ", padding=8)
        card3.pack(side="left", expand=True, fill="x", padx=5)
        ttk.Label(card3, text=f"৳ {avg_val:,.2f}", font=("Helvetica", 12, "bold"), foreground="#0f172a").pack()

        # Render Matplotlib Grid
        fig = Figure(figsize=(9, 5.5), dpi=100)
        fig.patch.set_facecolor('#f8fafc')

        # Chart 1: Revenue Line Chart
        ax1 = fig.add_subplot(221)
        ax1.set_facecolor('#ffffff')
        if sales_by_date:
            dates = [r[0] for r in sales_by_date]
            totals = [r[1] for r in sales_by_date]
            ax1.plot(dates, totals, marker='o', color='#10b981', linewidth=2, markersize=4)
            ax1.set_title("Sales Revenue (৳) by Date", fontsize=9, fontweight='bold', color='#0f172a')
            ax1.grid(True, linestyle='--', alpha=0.3)
            ax1.tick_params(colors='#475569', labelsize=7)
        else:
            ax1.text(0.5, 0.5, "No Sales Data", ha='center', va='center', color='#64748b')

        # Chart 2: Invoice Status Distribution (Donut Chart)
        ax2 = fig.add_subplot(222)
        ax2.set_facecolor('#ffffff')
        if status_data:
            labels = [r[0][:15] for r in status_data]
            counts = [r[1] for r in status_data]
            colors_palette = ['#10b981', '#0284c7', '#f59e0b', '#ef4444', '#64748b']
            wedges, texts, autotexts = ax2.pie(
                counts, labels=labels, autopct='%1.0f%%', startangle=90, 
                colors=colors_palette[:len(counts)], textprops={'fontsize': 7}
            )
            ax2.set_title("Status Breakdown", fontsize=9, fontweight='bold', color='#0f172a')
        else:
            ax2.text(0.5, 0.5, "No Status Data", ha='center', va='center', color='#64748b')

        # Chart 3: Top Selling Products
        ax3 = fig.add_subplot(212)
        ax3.set_facecolor('#ffffff')
        if top_items:
            items = [r[0][:22] for r in top_items]
            revs = [r[1] for r in top_items]
            ax3.barh(items, revs, color='#0284c7', height=0.5)
            ax3.set_title("Top 5 Products by Revenue (৳)", fontsize=9, fontweight='bold', color='#0f172a')
            ax3.invert_yaxis()
            ax3.grid(True, linestyle='--', alpha=0.3)
            ax3.tick_params(colors='#475569', labelsize=7)
        else:
            ax3.text(0.5, 0.5, "No Product Sales Data", ha='center', va='center', color='#64748b')

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

# ----------------------------------------------------------------------
# Modern Application Manager & Execution Flow
# ----------------------------------------------------------------------
class ApplicationManager:
    def __init__(self):
        self.root = tk.Tk()
        self.apply_custom_theme()
        self.current_user = None
        self.show_login()

    def apply_custom_theme(self):
        style = ttk.Style()
        style.theme_use('clam')

        BG_MAIN = "#f8fafc"
        DARK_TEXT = "#0f172a"

        self.root.configure(bg=BG_MAIN)
        style.configure(".", background=BG_MAIN, foreground=DARK_TEXT, font=("Helvetica", 9))
        
        style.configure("TButton", font=("Helvetica", 9, "bold"), padding=6, background="#e2e8f0", borderwidth=0)
        style.map("TButton", background=[("active", "#cbd5e1")])

        style.configure("TEntry", padding=4, relief="flat")
        
        style.configure("Treeview", background="#ffffff", fieldbackground="#ffffff", rowheight=24)
        style.configure("Treeview.Heading", font=("Helvetica", 9, "bold"), background="#0f172a", foreground="#ffffff")
        style.map("Treeview.Heading", background=[("active", "#1e293b")])

    def show_login(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        LoginWindow(self.root, self.on_login_success)

    def on_login_success(self, username):
        self.current_user = username
        self.show_main_app()

    def show_main_app(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        GreenSourceBillingApp(self.root, self.current_user, self.show_login)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app_manager = ApplicationManager()
    app_manager.run()
