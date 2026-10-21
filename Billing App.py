import os
import tkinter as tk
from tkinter import ttk, messagebox
from num2words import num2words
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ----------------------------------------------------------------------
# PDF Generation Engine
# ----------------------------------------------------------------------
def generate_pdf_invoice(filepath, bill_data, items):
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    elements = []
    
    PRIMARY_COLOR = colors.HexColor("#0f172a")  # Dark Slate
    ACCENT_COLOR = colors.HexColor("#16a34a")   # Forest Green Accent
    BORDER_COLOR = colors.HexColor("#cbd5e1")   # Soft Grey
    BG_LIGHT = colors.HexColor("#f8fafc")       # Light Blue-Grey

    styles = getSampleStyleSheet()
    
    company_title_style = ParagraphStyle('CompanyTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=16, leading=18, textColor=PRIMARY_COLOR)
    subtitle_style = ParagraphStyle('SubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor("#475569"))
    contact_style = ParagraphStyle('Contact', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor("#334155"))
    doc_title_style = ParagraphStyle('DocTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=16, leading=18, alignment=2, textColor=ACCENT_COLOR)
    
    label_style = ParagraphStyle('MetaLabel', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor("#475569"))
    val_style = ParagraphStyle('MetaVal', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, textColor=PRIMARY_COLOR)
    
    cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=PRIMARY_COLOR)
    cell_normal = ParagraphStyle('CellNormal', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, textColor=PRIMARY_COLOR)
    cell_sub = ParagraphStyle('CellSub', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=7, leading=9, textColor=colors.HexColor("#64748b"))
    
    table_hdr = ParagraphStyle('TblHdr', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.whitesmoke, alignment=1)
    
    # 1. Header Section
    header_data = [
        [
            Paragraph(f"<b>{bill_data['company_name']}</b>", company_title_style),
            Paragraph("<b>GREEN SOURCE INVOICE</b>", doc_title_style)
        ],
        [
            Paragraph(bill_data['company_subtitle'], subtitle_style),
            ""
        ],
        [
            Paragraph(f"{bill_data['company_address']}<br/>Phone: {bill_data['company_phone']} | Email: {bill_data['company_email']}", contact_style),
            ""
        ]
    ]
    header_table = Table(header_data, colWidths=[340, 200])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('SPAN', (0,0), (0,0)),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))

    # 2. Bill To & Order Info Block
    info_data = [
        [
            Paragraph("<b>BILL TO (CUSTOMER)</b>", label_style),
            Paragraph("<b>BILL DETAILS</b>", label_style)
        ],
        [
            Paragraph(f"<b>{bill_data['client_name']}</b><br/>{bill_data['client_dept']}<br/>Attn: {bill_data['client_attn']}", val_style),
            Paragraph(f"<b>Bill No:</b> {bill_data['bill_no']}<br/><b>Date:</b> {bill_data['bill_date']}<br/><b>Payment Terms:</b> {bill_data['payment_terms']}", val_style)
        ],
        [
            Spacer(1, 5), Spacer(1, 5)
        ],
        [
            Paragraph("<b>DELIVERY & ORDER REF</b>", label_style),
            Paragraph("", label_style)
        ],
        [
            Paragraph(f"<b>Order Type:</b> {bill_data['order_type']}<br/><b>Status:</b> {bill_data['status']}", val_style),
            ""
        ]
    ]
    info_table = Table(info_data, colWidths=[330, 210])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#f1f5f9")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))

    # 3. Product Items Table
    item_rows = [
        [
            Paragraph("SL.", table_hdr),
            Paragraph("PRODUCT/SERVICE DESCRIPTION", table_hdr),
            Paragraph("REQ. QTY", table_hdr),
            Paragraph("UNIT", table_hdr),
            Paragraph("UNIT RATE (৳)", table_hdr),
            Paragraph("TOTAL AMOUNT (৳)", table_hdr)
        ]
    ]
    
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

    items_table = Table(item_rows, colWidths=[30, 230, 60, 50, 80, 90])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 15))

    # 4. Totals & Words Section
    net_payable = subtotal + bill_data['vat'] - bill_data['discount']
    
    try:
        words = num2words(net_payable, lang='en').title() + " BDT Only."
    except Exception:
        words = f"{net_payable:,.2f} BDT Only."

    summary_data = [
        [
            Paragraph("<b>TOTAL AMOUNT IN WORDS</b>", label_style),
            Paragraph("Sub Total:", cell_bold),
            Paragraph(f"৳ {subtotal:,.2f}", ParagraphStyle('R', parent=cell_bold, alignment=2))
        ],
        [
            Paragraph(f"<i>{words}</i>", val_style),
            Paragraph("VAT/Tax:", cell_normal),
            Paragraph(f"৳ {bill_data['vat']:,.2f}", ParagraphStyle('R', parent=cell_normal, alignment=2))
        ],
        [
            Paragraph("<br/><b>Terms & Conditions:</b><br/>"
                      "• Goods once sold and received in good condition are not returnable.<br/>"
                      "• Please verify item quantities and fasteners upon physical handover.", cell_sub),
            Paragraph("Discount:", cell_normal),
            Paragraph(f"৳ {bill_data['discount']:,.2f}", ParagraphStyle('R', parent=cell_normal, alignment=2))
        ],
        [
            "",
            Paragraph("<b>Net Payable Total:</b>", cell_bold),
            Paragraph(f"<b>৳ {net_payable:,.2f}</b>", ParagraphStyle('R', parent=cell_bold, alignment=2))
        ]
    ]
    
    summary_table = Table(summary_data, colWidths=[320, 110, 110])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('SPAN', (0,0), (0,1)),
        ('SPAN', (0,2), (0,3)),
        ('LINEBELOW', (1,-1), (2,-1), 1, PRIMARY_COLOR),
        ('GRID', (1,0), (2,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('BACKGROUND', (1,3), (2,3), BG_LIGHT),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 40))

    # 5. Signatures
    sig_data = [
        [
            Paragraph(f"_____________________________<br/><b>Received By (Customer / {bill_data['client_name']})</b>", ParagraphStyle('S1', parent=cell_normal, alignment=1)),
            Paragraph(f"_____________________________<br/><b>Authorized Signature ({bill_data['company_name']})</b>", ParagraphStyle('S2', parent=cell_normal, alignment=1))
        ]
    ]
    sig_table = Table(sig_data, colWidths=[270, 270])
    sig_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    elements.append(sig_table)

    doc.build(elements)


# ----------------------------------------------------------------------
# Desktop UI Application (Tkinter)
# ----------------------------------------------------------------------
class CommercialBillingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Green Source Invoice Generator")
        self.root.geometry("880x780")

        self.items = []

        # --- Top Form: Metadata ---
        meta_frame = ttk.LabelFrame(root, text=" Header & Client Details ", padding=10)
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

        ttk.Label(meta_frame, text="Attn Person:").grid(row=2, column=2, sticky="w")
        self.client_attn = ttk.Entry(meta_frame, width=25)
        self.client_attn.grid(row=2, column=3, padx=5, pady=2)

        ttk.Label(meta_frame, text="Order Type:").grid(row=3, column=0, sticky="w")
        self.order_type = ttk.Entry(meta_frame, width=28)
        self.order_type.grid(row=3, column=1, padx=5, pady=2)

        ttk.Label(meta_frame, text="Payment Terms:").grid(row=3, column=2, sticky="w")
        self.payment_terms = ttk.Entry(meta_frame, width=25)
        self.payment_terms.insert(0, "Due on Delivery")
        self.payment_terms.grid(row=3, column=3, padx=5, pady=2)

        # --- Middle Form: Add Line Items ---
        item_frame = ttk.LabelFrame(root, text=" Line Items ", padding=10)
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

        add_btn = ttk.Button(item_frame, text="➕ Add Item", command=self.add_item)
        add_btn.grid(row=1, column=6, padx=5)

        # --- Items Table ---
        table_frame = ttk.Frame(root, padding=10)
        table_frame.pack(fill="both", expand=True, padx=10)

        columns = ("#", "Description", "Details", "Qty", "Unit", "Rate", "Total")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=7)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=80, anchor="center")
        self.tree.column("Description", width=220, anchor="w")
        self.tree.column("Details", width=220, anchor="w")
        
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # --- Discount & Tax Adjustments ---
        adj_frame = ttk.LabelFrame(root, text=" Summary Adjustments ", padding=10)
        adj_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(adj_frame, text="Discount Amount (৳):").grid(row=0, column=0, sticky="w")
        self.discount_entry = ttk.Entry(adj_frame, width=15)
        self.discount_entry.insert(0, "0.00")
        self.discount_entry.grid(row=0, column=1, padx=5)

        ttk.Label(adj_frame, text="VAT / Tax (৳):").grid(row=0, column=2, sticky="w", padx=(20, 0))
        self.vat_entry = ttk.Entry(adj_frame, width=15)
        self.vat_entry.insert(0, "0.00")
        self.vat_entry.grid(row=0, column=3, padx=5)

        # --- Bottom Control Buttons ---
        btn_frame = ttk.Frame(root, padding=10)
        btn_frame.pack(fill="x", padx=10)

        del_btn = ttk.Button(btn_frame, text="❌ Delete Selected Item", command=self.delete_item)
        del_btn.pack(side="left", padx=5)

        clear_btn = ttk.Button(btn_frame, text="🧹 Clear All Items", command=self.clear_all_items)
        clear_btn.pack(side="left", padx=5)

        gen_btn = ttk.Button(btn_frame, text="📄 Generate PDF Invoice", command=self.create_pdf)
        gen_btn.pack(side="right", padx=5)

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

        # Clear item entry fields
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

    def create_pdf(self):
        if not self.items:
            messagebox.showwarning("Warning", "Add at least one item before generating.")
            return

        try:
            discount_val = float(self.discount_entry.get().strip() or 0.0)
            vat_val = float(self.vat_entry.get().strip() or 0.0)
        except ValueError:
            messagebox.showerror("Invalid Input", "Discount and VAT must be numeric values.")
            return

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
            "status": "Dispatched / Ready for Handover",
            "vat": vat_val,
            "discount": discount_val
        }

        output_filename = f"{self.bill_no.get().replace('/', '_')}.pdf"

        try:
            generate_pdf_invoice(output_filename, bill_data, self.items)
            messagebox.showinfo(
                "Success", 
                f"Invoice generated successfully!\nSaved as: {os.path.abspath(output_filename)}"
            )
        except PermissionError:
            messagebox.showerror(
                "File Locked Error", 
                f"Cannot write to '{output_filename}'.\n\nPlease close the open PDF file in your viewer/browser and try again."
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate PDF:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = CommercialBillingApp(root)
    root.mainloop()