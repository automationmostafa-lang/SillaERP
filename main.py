# -*- coding: utf-8 -*-
# ============================================================================
#  HyperMarket ERP + POS  |  هايبر ماركت
#  PySide6 + SQLite — Offline • AR/EN • RTL/LTR • Light/Dark
#  by: ENG/Mostafa Hesham
# ============================================================================
import sys, os, sqlite3, hashlib, shutil, json, base64, csv, io, datetime as dt

from PySide6.QtCore import (Qt, QTimer, QSize, QDate, QDateTime, QSizeF, QUrl,
                            QMarginsF, QProcess)
from PySide6.QtGui import (QFont, QColor, QPainter, QPixmap, QImage, QIcon,
                           QTextDocument, QPageLayout, QPageSize, QBrush)
from PySide6.QtWidgets import *
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog, QPrinterInfo
from license_gate import license_gate, license_start_meter

DIR  = os.path.dirname(os.path.abspath(__file__))
DB   = os.path.join(DIR, "retail_erp.db")
LOGO_FILE = os.path.join(DIR, "logo.png")
RESET_PASSWORD = "admin2026"
EMPTY_START = False
BRAND_AR = "هايبر ماركت"
BRAND_EN = "Hyper Market"
APP = BRAND_AR
LANG = "ar"; CUR_USER = None; SET = {}

def sync_app_name():
    global APP
    APP = BRAND_AR if LANG == "ar" else BRAND_EN

def brand_by():
    return ("برمجة: م/ مصطفى هشام" if LANG == "ar"
            else "by: ENG/Mostafa Hesham")

def logo_pixmap(size=64):
    try:
        if os.path.exists(LOGO_FILE):
            pm = QPixmap(LOGO_FILE)
            if not pm.isNull():
                return pm.scaled(size, size, Qt.KeepAspectRatio,
                                 Qt.SmoothTransformation)
    except Exception:
        pass
    return None

# ============================== SCHEMA ======================================
SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE,
  password TEXT, full_name TEXT, role TEXT, active INTEGER DEFAULT 1, created_at TEXT);
CREATE TABLE IF NOT EXISTS role_permissions(role TEXT, module TEXT, allowed INTEGER DEFAULT 1,
  PRIMARY KEY(role,module));
CREATE TABLE IF NOT EXISTS activity_log(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT,
  username TEXT, action TEXT, details TEXT);
CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT);
CREATE TABLE IF NOT EXISTS locations(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT,
  type TEXT DEFAULT 'branch', supply_from INTEGER);
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT, barcode TEXT UNIQUE,
  name TEXT, name_ar TEXT DEFAULT '', category_id INTEGER, unit TEXT DEFAULT 'pcs',
  cost REAL DEFAULT 0, price REAL DEFAULT 0, min_stock REAL DEFAULT 5,
  icon TEXT DEFAULT '📦', active INTEGER DEFAULT 1, expiry TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS stock(product_id INTEGER, location_id INTEGER, qty REAL DEFAULT 0,
  PRIMARY KEY(product_id,location_id));
CREATE TABLE IF NOT EXISTS stock_moves(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT,
  product_id INTEGER, location_id INTEGER, qty REAL, reason TEXT, ref TEXT, username TEXT);
CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT,
  phone TEXT DEFAULT '', tier TEXT DEFAULT 'Bronze', points REAL DEFAULT 0,
  balance REAL DEFAULT 0, notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS suppliers(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT,
  phone TEXT DEFAULT '', balance REAL DEFAULT 0, notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS shifts(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT,
  location_id INTEGER, opened_at TEXT, closed_at TEXT, opening_cash REAL DEFAULT 0,
  counted_cash REAL, expected_cash REAL, difference REAL, status TEXT DEFAULT 'open',
  notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_no TEXT UNIQUE,
  ts TEXT, username TEXT, customer_id INTEGER, location_id INTEGER, shift_id INTEGER,
  subtotal REAL, discount REAL, tax REAL, total REAL, paid_cash REAL DEFAULT 0,
  paid_card REAL DEFAULT 0, change REAL DEFAULT 0, status TEXT DEFAULT 'completed',
  coupon TEXT, notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS sale_items(id INTEGER PRIMARY KEY AUTOINCREMENT, sale_id INTEGER,
  product_id INTEGER, name TEXT, qty REAL, price REAL, cost REAL DEFAULT 0, total REAL);
CREATE TABLE IF NOT EXISTS purchases(id INTEGER PRIMARY KEY AUTOINCREMENT, ref_no TEXT, ts TEXT,
  supplier_id INTEGER, location_id INTEGER, username TEXT, total REAL DEFAULT 0,
  paid REAL DEFAULT 0, status TEXT DEFAULT 'unpaid');
CREATE TABLE IF NOT EXISTS purchase_items(id INTEGER PRIMARY KEY AUTOINCREMENT,
  purchase_id INTEGER, product_id INTEGER, name TEXT, qty REAL, cost REAL, total REAL);
CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT,
  party_type TEXT, party_id INTEGER, amount REAL, direction TEXT,
  method TEXT DEFAULT 'cash', note TEXT DEFAULT '', username TEXT);
CREATE TABLE IF NOT EXISTS quotations(id INTEGER PRIMARY KEY AUTOINCREMENT, quote_no TEXT UNIQUE,
  ts TEXT, customer_id INTEGER, valid_until TEXT, subtotal REAL, discount REAL,
  tax REAL, total REAL, status TEXT DEFAULT 'draft', notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS quote_items(id INTEGER PRIMARY KEY AUTOINCREMENT, quote_id INTEGER,
  product_id INTEGER, name TEXT, qty REAL, price REAL, total REAL);
CREATE TABLE IF NOT EXISTS held_sales(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT,
  username TEXT, label TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS work_orders(id INTEGER PRIMARY KEY AUTOINCREMENT, wo_no TEXT UNIQUE,
  ts TEXT, type TEXT DEFAULT 'work', customer_id INTEGER, assigned_to TEXT DEFAULT '',
  title TEXT, details TEXT DEFAULT '', status TEXT DEFAULT 'pending', due TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS appointments(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT,
  title TEXT, customer_id INTEGER, work_order_id INTEGER, status TEXT DEFAULT 'scheduled',
  notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS commission_rules(id INTEGER PRIMARY KEY AUTOINCREMENT,
  employee TEXT DEFAULT '*', basis TEXT DEFAULT 'sale', target TEXT DEFAULT '',
  percent REAL DEFAULT 0, fixed REAL DEFAULT 0, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS commissions(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT,
  employee TEXT, sale_id INTEGER, amount REAL, paid INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS coupons(id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE,
  type TEXT DEFAULT 'percent', value REAL DEFAULT 0, min_total REAL DEFAULT 0,
  starts TEXT DEFAULT '', ends TEXT DEFAULT '', active INTEGER DEFAULT 1, used INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS offers(id INTEGER PRIMARY KEY AUTOINCREMENT, scope TEXT DEFAULT 'product',
  target TEXT, percent REAL DEFAULT 0, starts TEXT DEFAULT '', ends TEXT DEFAULT '',
  active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS loyalty_txn(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT,
  customer_id INTEGER, points REAL, reason TEXT, username TEXT);
CREATE TABLE IF NOT EXISTS expenses(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT,
  category TEXT, description TEXT, amount REAL DEFAULT 0,
  account TEXT DEFAULT 'drawer', username TEXT);
CREATE TABLE IF NOT EXISTS treasury(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT,
  account TEXT, direction TEXT, amount REAL, reason TEXT, ref TEXT, username TEXT);
CREATE TABLE IF NOT EXISTS transfers(id INTEGER PRIMARY KEY AUTOINCREMENT, ref_no TEXT,
  ts TEXT, from_loc INTEGER, to_loc INTEGER, status TEXT DEFAULT 'in-transit',
  username TEXT, note TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS transfer_items(id INTEGER PRIMARY KEY AUTOINCREMENT,
  transfer_id INTEGER, product_id INTEGER, qty REAL);
CREATE TABLE IF NOT EXISTS trash(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT,
  username TEXT, tbl TEXT, rid INTEGER, data TEXT);
CREATE TABLE IF NOT EXISTS supplier_prices(id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT, supplier_id INTEGER, product_id INTEGER, cost REAL);
"""

# ============================== i18n ========================================
AR = {
"Dashboard":"لوحة التحكم","POS Screen":"شاشة الكاشير","Inventory":"المخزون",
"Purchases":"المشتريات","Offers & Discounts":"العروض والخصومات","Work Orders":"أوامر التشغيل",
"Expenses":"المصروفات","Sales & Invoices":"المبيعات والفواتير","Quotations":"عروض الأسعار",
"E-Invoicing":"الفوترة الإلكترونية","Branches & Warehouses":"الفروع والمخازن","Customers":"العملاء",
"Suppliers":"الموردون","Appointments":"المواعيد","Commissions":"العمولات","Users":"المستخدمون",
"Settings":"الإعدادات","Shifts":"الورديات","Activity Log":"سجل العمليات",
"Operations":"التنفيذ","Management":"الإدارة","System":"النظام","Reports":"التقارير",
"Today's Sales":"مبيعات اليوم","Today's Invoices":"فواتير اليوم","Total Products":"إجمالي المنتجات",
"Low Stock Alerts":"تنبيهات نقص المخزون","Total Customers":"إجمالي العملاء","Cash in Drawer":"نقدية الدرج",
"Sales — last 7 days":"مبيعات آخر 7 أيام","Top products":"أعلى المنتجات مبيعاً",
"Barcode / Product name":"باركود أو اسم المنتج","Search":"بحث","Add":"إضافة","Edit":"تعديل","Delete":"حذف",
"Save":"حفظ","Confirm":"تأكيد","Print":"طباعة","Export CSV":"تصدير CSV","Import CSV":"استيراد CSV",
"Imported":"تم الاستيراد","Total":"الإجمالي","Price":"السعر","Qty":"الكمية","Item":"الصنف",
"Subtotal":"الإجمالي الفرعي","Discount":"الخصم","Tax":"الضريبة","Grand Total":"الإجمالي النهائي",
"Cash":"نقدي","Card":"بطاقة","Change":"الباقي","Hold":"تعليق","Customer":"العميل",
"Walk-in":"عميل نقدي","Coupon":"كوبون","Clear":"تفريغ","Remove":"إزالة","New Sale":"فاتورة جديدة",
"Held Sales":"الفواتير المعلقة","Resume":"استكمال","Pay & Complete":"الدفع وإنهاء الفاتورة",
"Cart is empty":"السلة فارغة","Insufficient payment!":"المبلغ غير كافٍ أو الرصيد لا يكفي!",
"Change due:":"الباقي للعميل:","Payment":"الدفع","Cash amount":"مبلغ النقدي","Card amount":"مبلغ البطاقة",
"Invoice No":"رقم الفاتورة","Date":"التاريخ","Status":"الحالة","completed":"مكتملة","returned":"مرتجعة",
"return":"مرتجع","unpaid":"غير مدفوعة","partial":"مدفوعة جزئياً","paid":"مدفوعة","draft":"مسودة",
"approved":"معتمد","rejected":"مرفوض","converted":"محوّلة","open":"مفتوحة","closed":"مغلقة",
"pending":"قيد الانتظار","in-progress":"جاري التنفيذ","done":"منجز","delivered":"تم التسليم",
"scheduled":"مجدول","Return":"مرتجع","Reason":"السبب","Return processed":"تم تسجيل المرتجع",
"Products":"المنتجات","Categories":"الأقسام","Stock by Location":"الأرصدة بالمخازن",
"Adjust Stock":"تسوية / جرد المخزون","Barcode Labels":"طباعة ملصقات الباركود","Product Name":"اسم المنتج",
"Name (AR)":"الاسم بالعربي","Category":"القسم","Unit":"الوحدة","Cost":"التكلفة","Min Stock":"حد الطلب",
"Active":"نشط","Transfer Stock":"تحويل مخزون","From":"من","To":"إلى","Branch":"فرع",
"Warehouse":"مخزن","Store":"معرض","New Purchase":"فاتورة شراء","Supplier":"المورد","Location":"المخزن",
"Ref No":"رقم المرجع","Total Cost":"الإجمالي","Purchase saved":"تم حفظ فاتورة الشراء",
"Pay Supplier":"دفع للمورد","Amount":"المبلغ","Ledger":"كشف الحساب","Balance":"الرصيد",
"Payment saved":"تم تسجيل الدفعة","Receive Payment":"تحصيل دفعة","New Quotation":"عرض سعر جديد",
"Valid Until":"صالح حتى","Approve":"اعتماد","Reject":"رفض","Convert to Invoice":"تحويل إلى فاتورة",
"Quotation saved":"تم حفظ عرض السعر","Quote converted to invoice":"تم التحويل إلى فاتورة",
"Print A4":"طباعة A4","Print Receipt":"طباعة إيصال","E-Invoice JSON":"تصدير JSON",
"E-Invoice XML":"تصدير XML","Tax Invoice":"فاتورة ضريبية","Open Shift":"فتح الوردية",
"Close Shift":"إغلاق الوردية","Opening Cash":"النقدية الافتتاحية","Counted Cash":"النقدية المعدودة",
"Expected":"المتوقع","Difference":"الفرق","Shift opened":"الوردية مفتوحة بالفعل",
"Shift closed":"تم إغلاق الوردية","No open shift!":"لا توجد وردية مفتوحة!","Role":"الدور",
"Permissions":"الصلاحيات","Password":"كلمة المرور","Work Order":"أمر تشغيل","Delivery Order":"أمر تسليم",
"Title":"العنوان","Assign To":"الموظف المسؤول","Due Date":"الاستحقاق","Advance Status":"نقل الحالة",
"Print Delivery Note":"طباعة أمر التسليم","Signature":"التوقيع","Received by":"المستلم",
"Delivered by":"المُسلِّم","New Appointment":"موعد جديد","Today":"اليوم","Rules":"القواعد",
"Computed Commissions":"العمولات المحتسبة","Employee":"الموظف","Basis":"الأساس","Percent %":"النسبة %",
"Fixed":"ثابت","Compute":"احتساب","Mark Paid":"تم الصرف","All":"الكل","product":"منتج",
"category":"قسم","Coupons":"الكوبونات","Offers":"العروض","Type":"النوع","percent":"نسبة",
"fixed":"مبلغ","Value":"القيمة","Min Total":"أدنى فاتورة","Starts":"من تاريخ","Ends":"إلى تاريخ",
"Points":"النقاط","Tier":"الفئة","Bronze":"برونزي","Silver":"فضي","Gold":"ذهبي",
"Redeem Points":"استبدال نقاط","Category name":"اسم المصروف","Description":"الوصف",
"Amount spent":"المبلغ","Sales by Day":"المبيعات اليومية","Best Sellers":"الأكثر مبيعاً",
"Profit & Loss":"الأرباح والخسائر","Inventory Valuation":"تقييم المخزون",
"Employee Performance":"أداء الموظفين","Generate":"عرض","Net Profit":"صافي الربح",
"Gross Profit":"إجمالي الربح","Company Name":"اسم الشركة","Company Name (AR)":"اسم الشركة بالعربي",
"Tax Number":"الرقم الضريبي","Phone":"الهاتف","Address":"العنوان","VAT %":"الضريبة %",
"Currency":"العملة","Currency (AR)":"العملة بالعربي","Receipt Footer":"تذييل الإيصال",
"Backup Database":"نسخة احتياطية","Restore Database":"استعادة نسخة",
"Backup saved":"تم حفظ النسخة الاحتياطية","Restored — restart required":"تمت الاستعادة — أعد التشغيل",
"Saved":"تم الحفظ","Are you sure?":"هل أنت متأكد؟","Nothing selected":"لم يتم التحديد",
"Exported":"تم التصدير","Cashier":"الكاشير","Branch/Store":"الفرع","Receipt":"إيصال",
"Delivery Note":"إذن تسليم","Shift Report":"تقرير الوردية","Product":"المنتج","Seller":"البائع",
"Buyer":"المشتري","Terms":"الشروط","Full Name":"الاسم الكامل","No permission":"لا توجد صلاحية",
"Appointments today":"مواعيد اليوم","New Qty":"الكمية الجديدة","Copies":"عدد النسخ",
"Invalid coupon":"كوبون غير صالح","Code":"الكود","Stock:":"الرصيد:",
"Wrong username or password":"اسم المستخدم أو كلمة المرور خطأ","Count":"العدد","View":"عرض",
"Username":"اسم المستخدم","Details":"التفاصيل","Module":"الوحدة","Notes":"ملاحظات",
"off":"مطفأة","Cash & Treasury":"الدرج والخزنة","Drawer":"الدرج","Vault":"الخزنة الرئيسية",
"Pay Owner":"توريد لصاحب الماركت","Deposit Vault":"إيداع في الصندوق",
"Account":"الحساب","In":"داخل","Out":"خارج","Cash Flow":"حركة الخزنة والدرج",
"Factory Reset":"إعادة ضبط المصنع","Special password":"كلمة المرور الخاصة",
"Wrong special password":"كلمة المرور الخاصة خطأ","New Transfer":"أمر تحويل جديد",
"Receive":"استلام","Cancel Transfer":"إلغاء التحويل","Transfers":"التحويلات",
"in-transit":"في الطريق","cancelled":"ملغي","received":"مستلم","Supply From":"يُورد من",
"Stock Moves":"حركات المخزن","Expiry":"الصلاحية","All Locations":"الكل",
"Expires soon":"صلاحية تقترب","Expired":"منتهي","Products in category":"منتجات القسم",
"Items count":"عدد الأصناف","Stock value":"قيمة المخزون","Shopping list":"قائمة شراء مقترحة",
"Suggested":"المقترح","Est. cost":"قيمة تقريبية","Profit by Product":"أرباح لكل منتج",
"All above minimum":"كل المنتجات فوق حد الطلب","Direct print":"طباعة مباشرة بدون معاينة",
"Printer name":"اسم الطابعة","Auto-lock minutes":"قفل تلقائي بعد خمول (دقايق، 0=معطل)",
"Damaged goods":"بضاعة تالفة (لا تعود للبيع)","Debts report":"تقرير الديون",
"Customer debts":"ديون العملاء","Supplier debts":"مستحقات الموردين",
"Last purchase prices":"آخر أسعار الشراء للمورد","Stuck shift found":"وردية عالقة",
"Admin password":"باسورد الأدمن","Trash":"سلة المحذوفات","Restore":"استرجاع",
"Purge":"حذف نهائي","Empty Trash":"تفريغ السلة","Wrong admin password":"باسورد الأدمن خطأ",
"Only admin":"الحذف للأدمن فقط — بعد إدخال باسورده","Line discount %":"خصم الصنف %",
"Stocktake":"جرد","Counted":"الفعلي المعدود","Diff":"الفرق","Ledger qty":"الرصيد الدفتري",
"Apply & Settle":"اعتماد التسوية","Counted items":"أصناف معدودة",
"Settle value":"قيمة التسوية","Nothing to settle":"مفيش فروق — كل حاجة مطابقة",
}
MOD_AR = {"dashboard":"لوحة التحكم","pos":"الكاشير","sales":"المبيعات","inventory":"المخزون",
"locations":"الفروع والمخازن","purchases":"المشتريات","suppliers":"الموردون","customers":"العملاء",
"quotes":"عروض الأسعار","einvoice":"الفوترة الإلكترونية","offers":"العروض والخصومات",
"shifts":"الورديات","workorders":"أوامر التشغيل","appointments":"المواعيد","commissions":"العمولات",
"expenses":"المصروفات","reports":"التقارير","users":"المستخدمون","settings":"الإعدادات",
"cash":"الدرج والخزنة","trash":"سلة المحذوفات"}

def T(s): return AR.get(s, s) if LANG == "ar" else s
def money(v): return f"{(v or 0):,.2f}"
def nows():  return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def today(): return dt.date.today().isoformat()

# ============================== DB ==========================================
conn = sqlite3.connect(DB, check_same_thread=False)
conn.row_factory = sqlite3.Row
def q(sql, p=()):
    return [dict(r) for r in conn.execute(sql, p).fetchall()]
def q1(sql, p=()):
    r = conn.execute(sql, p).fetchone()
    return dict(r) if r else None
def x(sql, p=()):
    cur = conn.execute(sql, p); conn.commit(); return cur.lastrowid

def load_settings():
    global SET
    SET = {r["key"]: r["value"] for r in q("SELECT * FROM settings")}
    d = {"company":"Hyper Market","company_ar":"هايبر ماركت","tax_no":"300000000000003",
         "phone":"0100000000","address":"Main Street","vat":"15","currency":"EGP",
         "currency_ar":"ج.م","theme":"light","lang":"ar",
         "receipt_footer":"Thank you for shopping with us!",
         "loyalty_earn":"1","loyalty_redeem":"0.1","tier_silver":"1000","tier_gold":"5000",
         "tier_silver_disc":"2","tier_gold_disc":"5"}
    for k, v in d.items(): SET.setdefault(k, v)

def cur(): return SET.get("currency_ar","ج.م") if LANG=="ar" else SET.get("currency","EGP")

def log(action, details=""):
    if CUR_USER:
        x("INSERT INTO activity_log(ts,username,action,details) VALUES(?,?,?,?)",
          (nows(), CUR_USER["username"], action, details))

def allowed(module):
    if module == "dash": module = "dashboard"
    if not CUR_USER or CUR_USER["role"] == "admin": return True
    r = q1("SELECT allowed FROM role_permissions WHERE role=? AND module=?",
           (CUR_USER["role"], module))
    return bool(r and r["allowed"])

def disp_name(p):
    return (p.get("name_ar") or p["name"]) if LANG == "ar" else p["name"]

def inv_no(prefix):
    d = dt.date.today().strftime("%Y%m%d")
    cfg = {"SL": ("sales","invoice_no"), "RT": ("sales","invoice_no"),
           "PO": ("purchases","ref_no"), "QT": ("quotations","quote_no")}
    tbl, col = cfg.get(prefix, ("sales","invoice_no"))
    n = q1(f"SELECT COUNT(*) c FROM {tbl} WHERE {col} LIKE ?", (f"{prefix}-{d}%",))["c"]
    return f"{prefix}-{d}-{n+1:05d}"

def move_stock(pid, loc, qty, reason, ref=""):
    x("INSERT OR IGNORE INTO stock(product_id,location_id,qty) VALUES(?,?,0)", (pid, loc))
    x("UPDATE stock SET qty=qty+? WHERE product_id=? AND location_id=?", (qty, pid, loc))
    x("INSERT INTO stock_moves(ts,product_id,location_id,qty,reason,ref,username) VALUES(?,?,?,?,?,?,?)",
      (nows(), pid, loc, qty, reason, ref, CUR_USER["username"] if CUR_USER else "system"))

def low_stock_count():
    return q1("""SELECT COUNT(*) c FROM products p WHERE p.active=1 AND
      (SELECT IFNULL(SUM(qty),0) FROM stock WHERE product_id=p.id) < p.min_stock""")["c"]

def is_admin():
    return bool(CUR_USER and CUR_USER["role"] == "admin")

# ===================== HELPERS: TRASH + SEARCH + COMPLETERS =================
def admin_password_check(parent):
    """🔐 بوابة الحذف: أدمن + باسورد حساب الأدمن نفسه"""
    if not is_admin():
        QMessageBox.warning(parent, APP, "🚫 " + T("Only admin")); return False
    ap = q1("SELECT password FROM users WHERE role='admin' ORDER BY id LIMIT 1")
    target = ap["password"] if ap else ""
    for _ in range(3):
        d = QDialog(parent); d.setWindowTitle("🔐 " + T("Delete"))
        d.setMinimumWidth(420)
        v = QVBoxLayout(d); v.setSpacing(10)
        warn = QLabel("⚠️ " + ("سيتم النقل إلى سلة المحذوفات — يلزم باسورد الأدمن"
                               if LANG == "ar" else
                               "Will move to Trash — admin password required"))
        warn.setStyleSheet("color:#b91c1c;font-weight:700;")
        v.addWidget(warn)
        pw = QLineEdit(); pw.setEchoMode(QLineEdit.Password)
        pw.setMinimumHeight(40); pw.setPlaceholderText("🔑 " + T("Admin password"))
        v.addWidget(pw)
        ok = QPushButton("🔓 " + T("Confirm")); ok.setObjectName("danger")
        ok.setMinimumHeight(42); v.addWidget(ok)
        ok.clicked.connect(d.accept); pw.returnPressed.connect(d.accept)
        if d.exec() != QDialog.Accepted: return False
        if hashlib.sha256(pw.text().encode()).hexdigest() == target:
            return True
        QMessageBox.warning(parent, APP, "❌ " + T("Wrong admin password"))
    return False

def trash_put(tbl, rid):
    """📦 حفظ نسخة كاملة في السلة قبل الحذف"""
    row = q1(f"SELECT * FROM {tbl} WHERE id=?", (rid,))
    if not row: return
    data = dict(row)
    if tbl == "sales":
        data["_items"] = q("SELECT * FROM sale_items WHERE sale_id=?", (rid,))
    elif tbl == "purchases":
        data["_items"] = q("SELECT * FROM purchase_items WHERE purchase_id=?", (rid,))
    elif tbl == "quotations":
        data["_items"] = q("SELECT * FROM quote_items WHERE quote_id=?", (rid,))
    x("INSERT INTO trash(ts,username,tbl,rid,data) VALUES(?,?,?,?,?)",
      (nows(), CUR_USER["username"] if CUR_USER else "system",
       tbl, rid, json.dumps(data, ensure_ascii=False, default=str)))

def trash_restore(trash_id):
    """♻️ استرجاع من السلة + إصلاح التبعيات"""
    rec = q1("SELECT * FROM trash WHERE id=?", (trash_id,))
    if not rec: return None
    tbl, rid = rec["tbl"], rec["rid"]
    if q1(f"SELECT id FROM {tbl} WHERE id=?", (rid,)):
        x("DELETE FROM trash WHERE id=?", (trash_id,)); return rid
    data = json.loads(rec["data"])
    items = data.pop("_items", [])
    cols = list(data.keys()); vals = [data[c] for c in cols]
    x(f"INSERT INTO {tbl}({','.join(cols)}) VALUES({','.join('?'*len(cols))})", vals)
    if tbl == "sales":
        sale = q1("SELECT * FROM sales WHERE id=?", (rid,))
        for it in items:
            x("INSERT INTO sale_items(sale_id,product_id,name,qty,price,cost,total) "
              "VALUES(?,?,?,?,?,?,?)",
              (rid, it.get("product_id"), it.get("name"), it.get("qty", 0),
               it.get("price", 0), it.get("cost", 0), it.get("total", 0)))
            if it.get("product_id") and sale:
                move_stock(it["product_id"], sale["location_id"],
                           -abs(it.get("qty", 0)), "restore-sale",
                           sale["invoice_no"])
        if sale:
            net = max(0.0, (sale["paid_cash"] or 0) - (sale["change"] or 0)) \
                  + (sale["paid_card"] or 0)
            if net > 0:
                for _acc in ("drawer", "vault"):
                    x("INSERT INTO treasury(ts,account,direction,amount,reason,"
                      "ref,username) VALUES(?,?,?,?,?,?,?)",
                      (nows(), _acc, "in", net,
                       "استرجاع فاتورة " + str(sale["invoice_no"]),
                       str(sale["invoice_no"]),
                       CUR_USER["username"] if CUR_USER else "system"))
    elif tbl == "purchases":
        pur = q1("SELECT * FROM purchases WHERE id=?", (rid,))
        for it in items:
            x("INSERT INTO purchase_items(purchase_id,product_id,name,qty,cost,"
              "total) VALUES(?,?,?,?,?,?)",
              (rid, it.get("product_id"), it.get("name"), it.get("qty", 0),
               it.get("cost", 0), it.get("total", 0)))
            if it.get("product_id") and pur:
                move_stock(it["product_id"], pur["location_id"],
                           abs(it.get("qty", 0)), "restore-purchase",
                           pur["ref_no"])
        if pur and (pur["paid"] or 0) > 0:
            x("INSERT INTO treasury(ts,account,direction,amount,reason,ref,"
              "username) VALUES(?,?,?,?,?,?,?)",
              (nows(), "drawer", "out", pur["paid"],
               "استرجاع شراء " + str(pur["ref_no"]), str(pur["ref_no"]),
               CUR_USER["username"] if CUR_USER else "system"))
    elif tbl == "quotations":
        for it in items:
            x("INSERT INTO quote_items(quote_id,product_id,name,qty,price,total) "
              "VALUES(?,?,?,?,?,?)",
              (rid, it.get("product_id"), it.get("name"), it.get("qty", 0),
               it.get("price", 0), it.get("total", 0)))
    elif tbl == "products":
        for l in q("SELECT id FROM locations"):
            x("INSERT OR IGNORE INTO stock(product_id,location_id,qty) "
              "VALUES(?,?,0)", (rid, l["id"]))
    x("DELETE FROM trash WHERE id=?", (trash_id,))
    return rid

def admin_delete(parent, tbl, ids, table, after=None):
    """🗑 حذف → سلة المحذوفات (أدمن + باسورد الأدمن)"""
    if not admin_password_check(parent): return
    r = tbl.currentRow()
    if not (0 <= r < len(ids)):
        QMessageBox.information(parent, APP, T("Nothing selected")); return
    rid = ids[r]
    trash_put(table, rid)
    try:
        if table == "sales":
            sale = q1("SELECT * FROM sales WHERE id=?", (rid,))
            if sale:
                for it in q("SELECT * FROM sale_items WHERE sale_id=?", (rid,)):
                    if it["product_id"]:
                        move_stock(it["product_id"], sale["location_id"],
                                   it["qty"], "trash-del-sale")
                x("DELETE FROM treasury WHERE ref=?", (sale["invoice_no"],))
            x("DELETE FROM sale_items WHERE sale_id=?", (rid,))
        elif table == "purchases":
            pv_ = q1("SELECT ref_no FROM purchases WHERE id=?", (rid,))
            if pv_ and pv_["ref_no"]:
                x("DELETE FROM treasury WHERE ref=?", (pv_["ref_no"],))
            x("DELETE FROM purchase_items WHERE purchase_id=?", (rid,))
        elif table == "quotations":
            x("DELETE FROM quote_items WHERE quote_id=?", (rid,))
        elif table == "work_orders":
            x("UPDATE appointments SET work_order_id=NULL WHERE work_order_id=?",
              (rid,))
        x(f"DELETE FROM {table} WHERE id=?", (rid,))
        log("trash_move", f"{table}#{rid}")
    except Exception as e:
        QMessageBox.critical(parent, APP, str(e)); return
    if after: after()
    mw = getattr(parent, "mw", None)
    if mw:
        try: mw.broadcast_all()
        except Exception: pass

def add_completer(edit, values):
    """قائمة منسدلة ذكية: أي حرف/رقم في أي مكان بالكلمة"""
    vals = sorted({str(v).strip() for v in values if v not in (None, "")})
    if not vals or edit is None: return
    c = QCompleter(vals)
    c.setCaseSensitivity(Qt.CaseInsensitive)
    c.setFilterMode(Qt.MatchContains)
    try:
        c.popup().setMinimumWidth(420); c.setMaxVisibleItems(15)
    except Exception: pass
    edit.setCompleter(c)

def editable_combo(combo):
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.NoInsert)
    combo.setMinimumHeight(32)
    try: combo.view().setMinimumWidth(420)
    except Exception: pass
    comp = combo.completer()
    if comp:
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        try: comp.popup().setMinimumWidth(420)
        except Exception: pass

def make_search():
    e = QLineEdit(); e.setPlaceholderText("🔍 " + T("Search"))
    e.setClearButtonEnabled(True)
    return e

def wire_search(edit, tbl):
    if edit is None or tbl is None: return
    try:
        vals = set()
        for i in range(tbl.rowCount()):
            for j in range(tbl.columnCount()):
                it = tbl.item(i, j)
                if it and it.text(): vals.add(it.text())
        add_completer(edit, list(vals))
        def apply(*_):
            t = edit.text().strip().lower()
            for i in range(tbl.rowCount()):
                hit = (not t)
                if not hit:
                    for j in range(tbl.columnCount()):
                        it = tbl.item(i, j)
                        if it and t in it.text().lower(): hit = True; break
                tbl.setRowHidden(i, not hit)
        try: edit.textChanged.disconnect()
        except Exception: pass
        edit.textChanged.connect(apply); apply()
    except Exception:
        pass

def export_csv(headers, rows):
    path, _ = QFileDialog.getSaveFileName(None, T("Export CSV"),
                                          "export.csv", "CSV (*.csv)")
    if not path: return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(headers); w.writerows(rows)
    QMessageBox.information(None, APP, T("Exported"))

# ============================== SEED / MIGRATE ==============================
def seed_system_only():
    h = lambda p: hashlib.sha256(p.encode()).hexdigest()
    x("INSERT INTO users(username,password,full_name,role,created_at) "
      "VALUES('admin',?,'System Admin','admin',?)", (h("123456"), nows()))
    for k, v in {"company":"Hyper Market","company_ar":"هايبر ماركت","vat":"15",
                 "currency":"EGP","currency_ar":"ج.م","theme":"light","lang":"ar",
                 "receipt_footer":"Thank you for shopping with us!"}.items():
        x("INSERT INTO settings(key,value) VALUES(?,?)", (k, v))
    conn.commit()

def migrate():
    conn.executescript(SCHEMA)
    try: x("ALTER TABLE products ADD COLUMN expiry TEXT DEFAULT ''")
    except Exception: pass
    try: x("ALTER TABLE locations ADD COLUMN supply_from INTEGER")
    except Exception: pass
    try: x("ALTER TABLE expenses ADD COLUMN account TEXT DEFAULT 'drawer'")
    except Exception: pass
    try: x("UPDATE settings SET value='Hyper Market' WHERE key='company' "
           "AND value IN ('Silla Market','My Market','سلة ماركت')")
    except Exception: pass
    try: x("UPDATE settings SET value='هايبر ماركت' WHERE key='company_ar' "
           "AND value IN ('سلة ماركت','سوقي','My Market')")
    except Exception: pass
    conn.commit()

def seed():
    conn.executescript(SCHEMA)
    if q1("SELECT COUNT(*) c FROM users")["c"]:
        conn.commit(); return
    if EMPTY_START:
        seed_system_only(); return
    h = lambda p: hashlib.sha256(p.encode()).hexdigest()
    for u, r, f in [("admin","123456","System Admin"),("manager","123456","مدير النظام"),
                    ("cashier","123456","محمد الكاشير"),("store","123456","أمين المخزن"),
                    ("account","123456","الحسابات")]:
        x("INSERT INTO users(username,password,full_name,role,created_at) VALUES(?,?,?,?,?)",
          (u, h(r), f, u, nows()))
    MODS = list(MOD_AR.keys())
    ALLD = {"admin": MODS, "manager": [m for m in MODS if m != "users"],
            "cashier": ["pos","sales","shifts","customers","offers","dashboard"],
            "store": ["inventory","locations","purchases","workorders","dashboard","reports"],
            "account": ["sales","purchases","expenses","quotes","einvoice","commissions",
                        "reports","customers","suppliers","dashboard"]}
    for role, ms in ALLD.items():
        for m in ms: x("INSERT INTO role_permissions(role,module,allowed) VALUES(?,?,1)",
                       (role, m))
    cats = ["أطعمة","مشروبات","ألبان","منظفات","عناية شخصية"]
    cids = {c: x("INSERT INTO categories(name) VALUES(?)", (c,)) for c in cats}
    cvals = list(cids.values())
    lids = [x("INSERT INTO locations(name,type) VALUES(?,?)", l) for l in
            [("المحل","branch"),("المخزن الرئيسي","warehouse")]]
    prods = [("T001","بيسكويت سادة","Tea Biscuit",0,8,12,52),
             ("T002","بسكويت شوكولاتة","Choco Biscuit",0,10,15,35),
             ("T003","رز مصري 1 كيلو","Rice 1kg",0,28,40,60),
             ("T015","سكر أبيض 1 كيلو","Sugar 1kg",0,22,30,44),
             ("T021","زيت طهي 800 مل","Cooking Oil 800ml",0,48,60,25),
             ("T022","مكرونة 400 جم","Pasta 400g",0,6,9,80),
             ("T030","حليب 1 لتر","Milk 1L",2,26,32,30),
             ("T031","زبادي بلدي","Yogurt Cup",2,4,6,90),
             ("T037","جبنة مثلثات","Cheese Triangles",2,28,35,26),
             ("T040","شامبو 400 مل","Shampoo 400ml",4,38,52,19),
             ("T041","صابون سائل","Liquid Soap",4,20,28,23),
             ("T045","سائل أطباق 650 مل","Dish Soap 650ml",3,17,24,40),
             ("T047","منظف أرضيات 1 لتر","Floor Cleaner 1L",3,15,22,35),
             ("T050","شاي 100 كيس","Tea 100 bags",1,30,42,28),
             ("T051","عصير برتقال 1 لتر","Juice 1L",1,14,20,48),
             ("T052","مياه 1.5 لتر","Water 1.5L",1,4,6,120),
             ("T060","تونة قطع","Tuna Chunks",0,18,25,32),
             ("T061","معجون طماطم","Tomato Paste",0,7,10,56)]
    for bc, arn, en, ci, cost, price, qty in prods:
        pid = x("INSERT INTO products(barcode,name,name_ar,category_id,cost,price,"
                "min_stock,icon) VALUES(?,?,?,?,?,?,5,'🛒')",
                (bc, en, arn, cvals[ci], cost, price))
        x("INSERT INTO stock(product_id,location_id,qty) VALUES(?,?,?)",
          (pid, lids[0], qty))
        x("INSERT INTO stock(product_id,location_id,qty) VALUES(?,?,?)",
          (pid, lids[1], qty // 2))
    x("INSERT INTO customers(name,phone,tier,points) VALUES('عميل نقدي','','Bronze',0)")
    x("INSERT INTO customers(name,phone,tier,points) VALUES('أحمد محمد','0101112233','Silver',120)")
    x("INSERT INTO customers(name,phone,tier,points) VALUES('فاطمة علي','0109988776','Gold',540)")
    x("INSERT INTO suppliers(name,phone,balance) VALUES('شركة النيل للتوزيع','0123456789',0)")
    x("INSERT INTO suppliers(name,phone,balance) VALUES('مؤسسة الأمل للتجارة','0127788990',0)")
    x("INSERT INTO coupons(code,type,value,min_total,starts,ends) "
      "VALUES('WELCOME10','percent',10,100,'2025-01-01','2030-12-31')")
    x("INSERT INTO offers(scope,target,percent,starts,ends) "
      "VALUES('product','بيسكويت',10,'2025-01-01','2030-12-31')")
    x("INSERT INTO commission_rules(employee,basis,percent) VALUES('*','sale',2)")
    x("INSERT INTO expenses(ts,category,description,amount,account,username) "
      "VALUES(?,?,?,?,?,'admin')", (nows(),"إيجار","إيجار المحل",1500,"drawer"))
    x("INSERT INTO treasury(ts,account,direction,amount,reason,ref,username) "
      "VALUES(?,?,?,?,?,?,?)",
      (nows(), "drawer", "in", 2000, "رصيد افتتاحي", "OPEN-INIT", "admin"))
    x("INSERT INTO treasury(ts,account,direction,amount,reason,ref,username) "
      "VALUES(?,?,?,?,?,?,?)",
      (nows(), "vault", "in", 5000, "رصيد افتتاحي", "OPEN-INIT", "admin"))
    x("INSERT INTO treasury(ts,account,direction,amount,reason,ref,username) "
      "VALUES(?,?,?,?,?,?,?)",
      (nows(), "drawer", "out", 1500, "إيجار المحل", "EXP-1", "admin"))
    x("INSERT INTO work_orders(wo_no,ts,type,title,details,status,due,assigned_to) "
      "VALUES('WO-00001',?,'work','صيانة ثلاجة العرض','الشبكة غير مبردة','pending',?, 'أمين المخزن')",
      (nows(), today()))
    x("INSERT INTO work_orders(wo_no,ts,type,title,details,status,due,assigned_to) "
      "VALUES('WO-00002',?,'delivery','توصيل طلبية مطعم النيل','3 صناديق زيت + 5 أكياس رز','done',?, 'محمد الكاشير')",
      (nows(), today()))
    x("INSERT INTO appointments(ts,title,customer_id,status) VALUES(?,?,2,'scheduled')",
      ((dt.datetime.now()+dt.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"),
       "اجتماع عرض أسعار جملة"))
    import random; random.seed(7)
    ps = q("SELECT * FROM products LIMIT 12")
    for d in range(6, -1, -1):
        day = (dt.date.today() - dt.timedelta(days=d)).strftime("%Y-%m-%d")
        for n in range(random.randint(1, 3)):
            items = random.sample(ps, random.randint(2, 4))
            sub = sum(i["price"] * random.randint(1, 3) for i in items)
            tax = round(sub * 0.15, 2); tot = round(sub + tax, 2)
            sid = x("INSERT INTO sales(invoice_no,ts,username,customer_id,location_id,"
                    "shift_id,subtotal,discount,tax,total,paid_cash,paid_card,change,status) "
                    "VALUES(?,?,?,?,?,NULL,?,0,?,?,0,?,0,'completed')",
                    (inv_no("SL"), f"{day} 1{n}:00:00", "cashier", 1, lids[0],
                     sub, tax, tot, tot))
            for i in items:
                qt = random.randint(1, 3)
                x("INSERT INTO sale_items(sale_id,product_id,name,qty,price,cost,total) "
                  "VALUES(?,?,?,?,?,?,?)",
                  (sid, i["id"], i["name_ar"] or i["name"], qt, i["price"],
                   i["cost"], qt * i["price"]))
    x("INSERT INTO shifts(username,location_id,opened_at,closed_at,opening_cash,"
      "counted_cash,expected_cash,difference,status) VALUES(?,?,?,?,?,?,?,0,'closed')",
      ("cashier", lids[0], "2025-01-01 09:00:00", "2025-01-01 17:00:00",
       200, 540, 540))
    conn.commit()

# ============================== THEME =======================================
PAL = {
 "light": {"bg":"#eef2f8","card":"#ffffff","text":"#0f172a","sub":"#64748b",
   "border":"#e2e8f0","primary":"#2563eb","primaryD":"#1d4ed8","green":"#10b981",
   "greenD":"#059669","red":"#ef4444","amber":"#f59e0b","side":"#ffffff",
   "side2":"#f1f5f9","input":"#f8fafc","sel":"#dbeafe"},
 "dark": {"bg":"#0b1220","card":"#121c30","text":"#e6edf7","sub":"#93a4bd",
   "border":"#1e2b45","primary":"#3b82f6","primaryD":"#2563eb","green":"#10b981",
   "greenD":"#059669","red":"#f87171","amber":"#fbbf24","side":"#060d1a",
   "side2":"#132441","input":"#0e1930","sel":"#1e3a8a"},
}
def apply_theme(dark=None):
    if dark is not None:
        SET["theme"] = "dark" if dark else "light"
    p = PAL["dark"] if SET.get("theme") == "dark" else PAL["light"]
    dm = SET.get("theme") == "dark"
    if dm:
        side_css = "background:@side;"
        side_lbl = "#8ea3bd"; side_txt = "#dbe4f0"; side_hover = "@side2"
        side_on = ("qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                   "stop:0 @greenD,stop:1 @green)")
        side_on_c = "#ffffff"
    else:
        side_css = "background:#ffffff;border-right:1px solid @border;"
        side_lbl = "#8a94a6"; side_txt = "#1e293b"; side_hover = "#f1f5f9"
        side_on = "@sel"; side_on_c = "@primary"
    L = []
    L.append("* { font-family:Segoe UI,Tahoma; font-size:13px; color:@text; }")
    L.append("QWidget { background:@bg; }")
    L.append("QLineEdit,QSpinBox,QDoubleSpinBox,QDateEdit,QDateTimeEdit,"
             "QComboBox,QTextEdit,QPlainTextEdit { background:@input; "
             "border:1px solid @border; border-radius:9px; padding:6px 12px; "
             "min-height:30px; font-size:14px; selection-background-color:@primary; "
             "color:@text; }")
    L.append("QLineEdit:focus,QDoubleSpinBox:focus,QComboBox:focus,"
             "QDateEdit:focus { border:1.5px solid @primary; }")
    L.append("QComboBox::drop-down { width:34px; border:none; }")
    L.append("QComboBox QAbstractItemView,QListView { background:@card; "
             "color:@text; border:1px solid @border; "
             "selection-background-color:@sel; selection-color:@text; "
             "outline:none; font-size:14px; }")
    L.append("QComboBox QAbstractItemView::item,QListView::item "
             "{ min-height:34px; padding:4px 10px; }")
    L.append("QSpinBox::up-button,QDoubleSpinBox::up-button,"
             "QDateTimeEdit::up-button,QSpinBox::down-button,"
             "QDoubleSpinBox::down-button,QDateTimeEdit::down-button "
             "{ width:26px; }")
    L.append("QPushButton { background:@card; border:1px solid @border; "
             "border-radius:9px; padding:9px 16px; min-height:24px; color:@text; }")
    L.append("QPushButton:hover { border-color:@primary; }")
    L.append("QPushButton#primary { background:@primary; color:#fff; "
             "border:none; font-weight:600; }")
    L.append("QPushButton#success { background:@green; color:#fff; "
             "border:none; font-weight:600; }")
    L.append("QPushButton#danger { background:@red; color:#fff; "
             "border:none; font-weight:600; }")
    L.append("QPushButton#warn { background:@amber; color:#fff; "
             "border:none; font-weight:600; }")
    L.append("QPushButton#ghost { background:transparent; }")
    L.append("QTableWidget { background:@card; alternate-background-color:@bg; "
             "border:1px solid @border; border-radius:12px; "
             "gridline-color:@border; font-size:13px; }")
    L.append("QHeaderView::section { background:@card; color:@sub; "
             "border:none; border-bottom:2px solid @border; padding:11px 8px; "
             "font-weight:700; font-size:13px; }")
    L.append("QTableWidget::item { padding:8px; }")
    L.append("QTableWidget::item:selected { background:@sel; color:@text; }")
    L.append("QTabWidget::pane { border:1px solid @border; border-radius:10px; "
             "background:@card; }")
    L.append("QTabBar::tab { padding:11px 18px; border-radius:8px; "
             "color:@sub; font-size:13px; }")
    L.append("QTabBar::tab:selected { background:@primary; color:#fff; }")
    L.append("QLabel#h1 { font-size:21px; font-weight:800; } "
             "QLabel#h2 { color:@sub; font-size:12px; }")
    L.append("QLabel#big { font-size:22px; font-weight:800; }")
    L.append("QFrame#card, QFrame#stat { background:@card; "
             "border:1px solid @border; border-radius:14px; }")
    L.append("QScrollArea { border:none; background:transparent; }")
    L.append("QMessageBox,QDialog { background:@bg; }")
    L.append("QScrollBar:vertical { background:transparent; width:12px; }")
    L.append("QScrollBar::handle:vertical { background:@border; "
             "border-radius:6px; min-height:30px; }")
    L.append("QCheckBox { spacing:8px; font-size:14px; }")
    L.append("QCheckBox::indicator { width:20px; height:20px; "
             "border:2px solid @border; border-radius:6px; background:@input; }")
    L.append("QCheckBox::indicator:checked { background:@green; "
             "border-color:@green; }")
    L.append("#side { " + side_css + " }")
    L.append("#side QLabel { color:" + side_lbl + "; font-size:11px; "
             "font-weight:800; padding:8px 12px 4px 10px; }")
    L.append("#side QPushButton { background:transparent; color:" + side_txt +
             "; border:none; text-align:left; padding:12px 16px; "
             "border-radius:10px; font-size:14px; font-weight:600; }")
    L.append("#side QPushButton:hover { background:" + side_hover + "; }")
    L.append("#side QPushButton:checked { background:" + side_on +
             "; color:" + side_on_c + "; font-weight:700; }")
    L.append("#head { background:@card; border-bottom:1px solid @border; }")
    qss = "\n".join(L)
    for k, v in p.items(): qss = qss.replace("@" + k, v)
    QApplication.instance().setStyleSheet(qss)

IC = {"dash":"📊","pos":"🧾","sales":"💳","quotes":"📑","einvoice":"⚡","shifts":"🕒",
"inventory":"📦","locations":"🏬","purchases":"🚚","suppliers":"🏭","customers":"👥",
"offers":"🏷️","workorders":"🛠️","appointments":"📅","commissions":"💰","expenses":"🧮",
"reports":"📈","users":"🛡️","settings":"⚙️","cash":"🏦","trash":"🗑️"}

# ============================== SMALL WIDGETS ===============================
class BarChart(QWidget):
    def __init__(s, title="", data=None, color="#2563eb"):
        super().__init__(); s.title = title; s.data = data or []; s.color = color
        s.setMinimumHeight(210)
    def set_data(s, d): s.data = d; s.update()
    def paintEvent(s, _):
        p = QPainter(s); p.setRenderHint(QPainter.Antialiasing)
        w, h = s.width(), s.height()
        p.setPen(QColor("#94a3b8"))
        p.setFont(QFont("Segoe UI", 11, 700)); p.drawText(14, 22, s.title)
        d = s.data; top = max([v for _, v, _ in d] or [1]) or 1
        bx, bw, bh, bt = 14, 34, h - 46, h - 64
        p.setFont(QFont("Segoe UI", 8))
        for i, (lab, val, c) in enumerate(d):
            x0 = bx + i * (bw + 12); bh2 = int((val / top) * bt)
            p.setBrush(QColor(c or s.color)); p.setPen(Qt.NoPen)
            p.drawRoundedRect(x0, bh - bh2, bw, bh2, 5, 5)
            p.setPen(QColor("#94a3b8")); p.drawText(x0 - 6, bh + 16, lab)
            p.setPen(QColor("#cbd5e1" if SET.get("theme") == "dark"
                            else "#64748b"))
            p.drawText(x0 - 8, bh - bh2 - 6, money(val)[:9])

def stat_card(icon, label, value, color):
    f = QFrame(); f.setObjectName("stat")
    lay = QHBoxLayout(f); lay.setContentsMargins(16, 14, 16, 14)
    c = QColor(color)
    ic = QLabel(icon)
    ic.setStyleSheet("font-size:26px;background:rgba(%d,%d,%d,40);"
                     "border-radius:12px;padding:10px;"
                     % (c.red(), c.green(), c.blue()))
    vb = QVBoxLayout()
    t = QLabel(label); t.setStyleSheet("color:#64748b;")
    v = QLabel(str(value)); v.setObjectName("big")
    v.setStyleSheet(f"color:{color};")
    vb.addWidget(t); vb.addWidget(v); lay.addWidget(ic); lay.addLayout(vb, 1)
    f._v = v
    return f

# ---------- Code39 + QR + printing ----------
C39 = {'0':'000110100','1':'100100001','2':'001100001','3':'101100000',
'4':'000110001','5':'100110000','6':'001110000','7':'000100101',
'8':'100100100','9':'001100100','A':'100001001','B':'001001001',
'C':'101001000','D':'000011001','E':'100011000','F':'001011000',
'G':'000001101','H':'100001100','I':'001001100','J':'000011100',
'K':'100000011','L':'001000011','M':'101000010','N':'000010011',
'O':'100010010','P':'001010010','Q':'000000111','R':'100000110',
'S':'001000110','T':'000010110','U':'110000001','V':'011000001',
'W':'111000000','X':'010010001','Y':'110010000','Z':'011010000',
'-':'010000101','.':'110000100',' ':'011000100','$':'010101000',
'/':'010100010','+':'010001010','%':'000101010','*':'010010100'}
def code39_pixmap(text, h=56, scale=2):
    t = "*" + str(text).upper() + "*"; bars = []
    for ch in t:
        pat = C39.get(ch, '100100001')
        for i, b in enumerate(pat): bars.append((i % 2 == 0, 3 if b == '1' else 1))
    wpx = sum((w + 1) for _, w in bars) * scale
    pm = QPixmap(wpx, h); pm.fill(Qt.white)
    p = QPainter(pm); p.setBrush(QColor("black")); p.setPen(Qt.NoPen)
    xx = 0
    for isbar, w in bars:
        if isbar: p.drawRect(xx, 0, w * scale, h)
        xx += (w + 1) * scale
    p.end(); return pm

def blank_img(w, h):
    img = QImage(w, h, QImage.Format_RGB32); img.fill(Qt.white); return img

def qr_image(payload, size=140):
    try:
        import qrcode
        buf = io.BytesIO(); qrcode.make(payload).save(buf, format="PNG"); buf.seek(0)
        img = QImage.fromData(buf.read())
        return img.scaled(size, size, Qt.KeepAspectRatio,
                          Qt.SmoothTransformation)
    except Exception:
        return None

def zatca_qr_payload(sale):
    def tlv(tag, val):
        b = str(val).encode("utf-8")
        return bytes([tag, len(b)]) + b
    tv = (tlv(1, SET.get("company_ar") or SET.get("company"))
        + tlv(2, SET.get("tax_no", ""))
        + tlv(3, sale["ts"].replace(" ", "T"))
        + tlv(4, f"{sale['total']:.2f}")
        + tlv(5, f"{sale['tax']:.2f}"))
    return base64.b64encode(tv).decode()

def direct_print(html, images=None, a4=False):
    """🖨 إرسال للطابعة مباشرة — بدون معاينة"""
    pr = QPrinter(QPrinter.HighResolution)
    try:
        names = [p_.printerName() for p_ in QPrinterInfo.availablePrinters()]
        want = SET.get("printer_name", "").strip()
        if want and want in names:
            pr.setPrinterName(want)
        elif names:
            dp = QPrinterInfo.defaultPrinter()
            if dp and dp.printerName():
                pr.setPrinterName(dp.printerName())
    except Exception: pass
    if a4:
        pr.setPageSize(QPageSize(QPageSize.A4))
    else:
        pr.setPageSize(QPageSize(QSizeF(79.5, 297), QPageSize.Millimeter))
        pr.setPageMargins(QMarginsF(3, 4, 3, 4), QPageLayout.Millimeter)
    doc = QTextDocument()
    for name, img in (images or {}).items():
        doc.addResource(QTextDocument.ImageResource, QUrl(name), img)
    doc.setHtml(html)
    doc.setPageSize(QSizeF(pr.pageRect(QPageLayout.Point).size()))
    doc.print_(pr)

def do_print(html, images=None, a4=True, pdf=None, parent=None):
    printer = QPrinter(QPrinter.HighResolution)
    if a4:
        printer.setPageSize(QPageSize(QPageSize.A4))
        printer.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Millimeter)
    else:
        printer.setPageSize(QPageSize(QSizeF(79.5, 297), QPageSize.Millimeter))
        printer.setPageMargins(QMarginsF(3, 4, 3, 4), QPageLayout.Millimeter)
    doc = QTextDocument()
    for name, img in (images or {}).items():
        doc.addResource(QTextDocument.ImageResource, QUrl(name), img)
    doc.setHtml(html)
    doc.setPageSize(QSizeF(printer.pageRect(QPageLayout.Point).size()))
    if pdf:
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(pdf)
        doc.print_(printer); return
    dlg = QPrintPreviewDialog(printer, parent)
    dlg.paintRequested.connect(lambda pr: doc.print_(pr))
    dlg.exec()

# ============================== TABLE EDITOR ================================
class TableEditor(QWidget):
    """جدول CRUD عام — الحفظ مؤكد برسالة ✅ والصف محدد"""
    def __init__(s, mw, table, cols, fields, search_cols=None, order="id DESC",
                 module=None, ro=False, filters=None, on_change=None):
        super().__init__(); s.mw = mw; s.table = table; s.cols = cols
        s.fields = fields
        s.scols = search_cols or [c[0] for c in cols]; s.order = order
        s.module = module or table; s.ro = ro; s.on_change = on_change
        s.fcol = None
        v = QVBoxLayout(s); v.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        s.search = make_search()
        s.search.textChanged.connect(s.refresh); top.addWidget(s.search, 1)
        if filters:
            items, s.fcol = filters
            s.fcombo = QComboBox()
            for lab, val in items: s.fcombo.addItem(str(lab), val)
            s.fcombo.currentIndexChanged.connect(s.refresh)
            top.addWidget(s.fcombo)
        if not ro:
            can = allowed(s.module)
            b1 = QPushButton("➕ " + T("Add")); b1.setObjectName("success")
            b1.clicked.connect(s.add); b1.setEnabled(can or is_admin())
            top.addWidget(b1)
            b2 = QPushButton("✏️ " + T("Edit")); b2.clicked.connect(s.edit)
            b2.setEnabled(can or is_admin()); top.addWidget(b2)
            b3 = QPushButton("🗑 " + T("Delete")); b3.setObjectName("danger")
            b3.clicked.connect(s.delete)
            b3.setEnabled(can or is_admin()); top.addWidget(b3)
        bx = QPushButton("📤 " + T("Export CSV")); bx.clicked.connect(s.export)
        top.addWidget(bx)
        v.addLayout(top)
        s.tbl = QTableWidget(); s.tbl.setAlternatingRowColors(True)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tbl.doubleClicked.connect(lambda *_: s.edit() if not s.ro else None)
        v.addWidget(s.tbl, 1); s.ids = []
    def rows_sql(s):
        w = ""; p = []
        t = s.search.text().strip()
        if t:
            w = "(" + " OR ".join(f"{c} LIKE ?" for c in s.scols) + ")"
            p = [f"%{t}%"] * len(s.scols)
        if s.fcol:
            val = s.fcombo.currentData()
            if val not in (None, "__all__"):
                w = (w + " AND " if w else "") + f"{s.fcol}=?"; p.append(val)
        return w, p
    def refresh(s):
        w, p = s.rows_sql()
        sel = ", ".join(f"{c[0]} AS `{c[1]}`" for c in s.cols) + ", id"
        rows = q(f"SELECT {sel} FROM {s.table} "
                 f"{('WHERE ' + w) if w else ''} ORDER BY {s.order}", p)
        hdr = [T(c[1]) for c in s.cols]
        s.tbl.clear(); s.tbl.setColumnCount(len(hdr)); s.tbl.setRowCount(len(rows))
        s.tbl.setHorizontalHeaderLabels(hdr)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        s.ids = [r["id"] for r in rows]
        for i, r in enumerate(rows):
            for j, c in enumerate(s.cols):
                val = r[c[1]]
                if s.table == "locations" and c[0] == "supply_from" and val:
                    nm = q1("SELECT name FROM locations WHERE id=?", (val,))
                    val = nm["name"] if nm else val
                if isinstance(val, float): val = money(val)
                it = QTableWidgetItem("" if val is None else str(val))
                it.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, it)
        wire_search(s.search, s.tbl)
    def sel_id(s):
        r = s.tbl.currentRow()
        return s.ids[r] if 0 <= r < len(s.ids) else None
    def form(s, rec=None):
        d = QDialog(s); d.setWindowTitle(T("Edit") if rec else T("Add"))
        d.setMinimumWidth(560)
        g = QFormLayout(d); g.setSpacing(12); ed = {}
        for col, lab, typ, opts in s.fields:
            if typ == "text":
                w = QLineEdit(str(rec[col])
                              if rec and rec[col] is not None else "")
                if col != "password":
                    try:
                        vals = [r[0] for r in conn.execute(
                            f"SELECT DISTINCT {col} FROM {s.table} "
                            f"WHERE {col} IS NOT NULL AND {col} != '' "
                            f"LIMIT 300").fetchall()]
                        add_completer(w, vals)
                    except Exception: pass
            elif typ == "num":
                w = QDoubleSpinBox(); w.setMaximum(10**9); w.setDecimals(2)
                w.setValue(float(rec[col]) if rec else 0)
                w.setAlignment(Qt.AlignCenter)
            elif typ == "int":
                w = QSpinBox(); w.setMaximum(10**6)
                w.setValue(int(rec[col]) if rec else 0)
                w.setAlignment(Qt.AlignCenter)
            elif typ == "combo":
                items = opts() if callable(opts) else opts
                w = QComboBox()
                for v_, l_ in items: w.addItem(str(l_), v_)
                editable_combo(w)
                if rec:
                    ix = w.findData(rec[col])
                    if ix >= 0:
                        w.setCurrentIndex(ix)
                    elif rec[col] is not None:
                        w.addItem(str(rec[col]), rec[col])
                        w.setCurrentIndex(w.count() - 1)
            elif typ == "date":
                w = QDateEdit(QDate.currentDate()); w.setCalendarPopup(True)
                if rec and rec[col]:
                    w.setDate(QDate.fromString(str(rec[col])[:10], "yyyy-MM-dd"))
            elif typ == "check":
                w = QCheckBox(); w.setChecked(bool(rec[col]) if rec else True)
            elif typ == "memo":
                w = QTextEdit(str(rec[col]) if rec else ""); w.setFixedHeight(70)
            else:
                w = QLineEdit()
            g.addRow(T(lab), w); ed[col] = (typ, w)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
        g.addRow(bb)
        return d, ed
    def _val(s, typ, w):
        if typ == "check":  return 1 if w.isChecked() else 0
        if typ == "date":   return w.date().toString("yyyy-MM-dd")
        if typ == "memo":   return w.toPlainText()
        if typ == "combo":  return w.currentData()
        if typ == "text":   return w.text()
        return w.value()
    def add(s):
        extra = {}
        if s.table == "work_orders":
            extra["wo_no"] = "WO-%05d" % (q1("SELECT COUNT(*) c FROM work_orders")["c"] + 1)
            extra["ts"] = nows()
        d, ed = s.form()
        if d.exec() != QDialog.Accepted: return
        cols = list(extra.keys()); vals = list(extra.values())
        try:
            for col, (typ, w) in ed.items():
                v_ = s._val(typ, w)
                if s.table == "users" and col == "password":
                    v_ = hashlib.sha256(
                        (str(v_) or "123456").encode()).hexdigest()
                cols.append(col); vals.append(v_)
        except Exception as e:
            QMessageBox.critical(s, APP, "❌ " + str(e)); return
        try:
            new_id = x(f"INSERT INTO {s.table}({','.join(cols)}) "
                       f"VALUES({','.join('?'*len(cols))})", vals)
            log(f"add_{s.table}")
        except Exception as e:
            QMessageBox.critical(s, APP, "❌ " + str(e)); return
        s.search.clear(); s.refresh()
        try:
            if new_id and new_id in s.ids:
                s.tbl.selectRow(s.ids.index(new_id))
        except Exception: pass
        QMessageBox.information(s, APP, "✅ " + T("Saved"))
        if s.on_change: s.on_change()
    def edit(s):
        i = s.sel_id()
        if not i:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        rec = q1(f"SELECT * FROM {s.table} WHERE id=?", (i,))
        d, ed = s.form(rec)
        if d.exec() != QDialog.Accepted: return
        sets = []; vals = []
        try:
            for col, (typ, w) in ed.items():
                v_ = s._val(typ, w)
                if s.table == "users" and col == "password":
                    if not v_: continue
                    v_ = hashlib.sha256(str(v_).encode()).hexdigest()
                sets.append(f"{col}=?"); vals.append(v_)
        except Exception as e:
            QMessageBox.critical(s, APP, "❌ " + str(e)); return
        try:
            x(f"UPDATE {s.table} SET {','.join(sets)} WHERE id=?", vals + [i])
            log(f"edit_{s.table}", f"id={i}")
        except Exception as e:
            QMessageBox.critical(s, APP, "❌ " + str(e)); return
        s.search.clear(); s.refresh()
        try:
            if i in s.ids: s.tbl.selectRow(s.ids.index(i))
        except Exception: pass
        QMessageBox.information(s, APP, "✅ " + T("Saved"))
        if s.on_change: s.on_change()
    def delete(s):
        if not (allowed(s.module) or is_admin()):
            QMessageBox.warning(s, APP, "🚫 " + T("No permission")); return
        i = s.sel_id()
        if not i:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        if s.table == "users":
            rec = q1("SELECT username FROM users WHERE id=?", (i,))
            if rec and (rec["username"] == "admin"
                        or rec["username"] == CUR_USER["username"]):
                QMessageBox.warning(s, APP, "🚫"); return
        if s.table == "locations":
            st_ = q1("SELECT IFNULL(SUM(ABS(qty)),0) v FROM stock "
                     "WHERE location_id=?", (i,))["v"]
            if st_ > 0:
                QMessageBox.warning(s, APP, "📦 " + (
                    "لا يمكن حذف موقع عليه رصيد — صفّره أولًا"
                    if LANG == "ar" else "Location has stock.")); return
            tr_ = q1("SELECT COUNT(*) c FROM transfers "
                     "WHERE from_loc=? OR to_loc=?", (i, i))["c"]
            if tr_:
                QMessageBox.warning(s, APP, "🔄 " + (
                    "عليه تحويلات مسجلة" if LANG == "ar"
                    else "Has transfers")); return
        if not admin_password_check(s): return
        if QMessageBox.question(s, APP, T("Are you sure?")) == QMessageBox.Yes:
            trash_put(s.table, i)
            if s.table == "locations":
                x("DELETE FROM stock WHERE location_id=?", (i,))
                x("UPDATE locations SET supply_from=NULL WHERE supply_from=?",
                  (i,))
            x(f"DELETE FROM {s.table} WHERE id=?", (i,))
            log(f"del_{s.table}", f"id={i}")
            s.refresh()
            if s.on_change: s.on_change()
    def export(s):
        w, p = s.rows_sql()
        sel = ", ".join(f"{c[0]} AS `{c[1]}`" for c in s.cols)
        rows = q(f"SELECT {sel} FROM {s.table} "
                 f"{('WHERE ' + w) if w else ''} ORDER BY {s.order}", p)
        export_csv([T(c[1]) for c in s.cols],
                   [[r[c[1]] for c in s.cols] for r in rows])

# ============================== LOGIN =======================================
class Login(QDialog):
    def __init__(s):
        super().__init__(); sync_app_name()
        s.setWindowTitle(APP); s.setFixedSize(460, 600)
        if LANG == "ar": s.setLayoutDirection(Qt.RightToLeft)
        s.setObjectName("loginRoot")
        v = QVBoxLayout(s); v.setContentsMargins(36, 34, 36, 26); v.setSpacing(10)
        card = QFrame(); card.setObjectName("brandCard")
        cv = QVBoxLayout(card); cv.setContentsMargins(10, 18, 10, 16); cv.setSpacing(4)
        pm = logo_pixmap(120)
        logo = QLabel(); logo.setAlignment(Qt.AlignCenter)
        if pm: logo.setPixmap(pm)
        else:
            logo.setText("🛒"); logo.setStyleSheet("font-size:64px; "
                                                   "background:transparent;")
        cv.addWidget(logo)
        t = QLabel(APP); t.setAlignment(Qt.AlignCenter)
        if LANG == "ar":
            t.setStyleSheet("font-family:Cairo,Segoe UI; font-size:38px; "
                            "font-weight:900; color:#7ef0c0; "
                            "background:transparent;")
        else:
            t.setStyleSheet("font-family:Segoe UI,Verdana; font-size:34px; "
                            "font-weight:800; font-style:italic; color:#7ef0c0; "
                            "background:transparent; letter-spacing:1.5px;")
        cv.addWidget(t)
        v.addWidget(card); v.addSpacing(12)
        s.u = QLineEdit(); s.u.setPlaceholderText("👤  " + T("Username"))
        s.u.setMinimumHeight(46)
        try:
            add_completer(s.u, [r["username"] for r in q("SELECT username FROM users")])
        except Exception: pass
        s.p = QLineEdit(); s.p.setPlaceholderText("🔒  " + T("Password"))
        s.p.setEchoMode(QLineEdit.Password); s.p.setMinimumHeight(46)
        v.addWidget(s.u); v.addWidget(s.p); v.addSpacing(6)
        b = QPushButton("🔐  " + ("تسجيل الدخول" if LANG == "ar" else "Login"))
        b.setObjectName("success"); b.setFixedHeight(50)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(s.try_login); v.addWidget(b)
        v.addSpacing(8)
        row = QHBoxLayout()
        lb = QPushButton("🌐 " + ("English" if LANG == "ar" else "العربية"))
        lb.setObjectName("ghost"); lb.setCursor(Qt.PointingHandCursor)
        lb.clicked.connect(s.toggle_lang)
        tb = QPushButton("🌙" if SET.get("theme") == "dark" else "☀️")
        tb.setObjectName("ghost"); tb.setCursor(Qt.PointingHandCursor)
        tb.clicked.connect(s.toggle_theme)
        row.addWidget(lb); row.addStretch(1); row.addWidget(tb)
        v.addLayout(row); v.addStretch(1)
        by = QLabel(brand_by()); by.setAlignment(Qt.AlignCenter)
        if LANG == "ar":
            by.setStyleSheet("font-family:Cairo,Segoe UI; color:#8fb3d9; "
                             "font-size:13px; font-weight:700; "
                             "background:transparent;")
        else:
            by.setStyleSheet("font-family:Segoe UI; color:#8fb3d9; "
                             "font-size:13px; font-weight:700; "
                             "background:transparent; letter-spacing:0.5px;")
        v.addWidget(by)
        s.p.returnPressed.connect(s.try_login)
        s.u.returnPressed.connect(s.p.setFocus)
        s.setStyleSheet(
            "#loginRoot { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            " stop:0 #0b1626, stop:1 #101f35); }"
            "#brandCard { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            " stop:0 rgba(30,58,95,220), stop:1 rgba(22,40,63,220));"
            " border:1px solid rgba(126,240,192,50); border-radius:20px; }"
            "QLabel { color:#e6edf7; background:transparent; }"
            "QLineEdit { background:rgba(255,255,255,14); color:#ffffff;"
            " border:1px solid rgba(255,255,255,45); border-radius:12px;"
            " padding:8px 14px; font-size:14px; }"
            "QLineEdit:focus { border:1.5px solid #10b981; }"
            "QPushButton#success { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            " stop:0 #0d9f6e, stop:1 #10b981); color:#fff; border:none;"
            " border-radius:12px; font-size:15px; font-weight:800; }"
            "QPushButton#success:hover { background:#0d9f6e; }"
            "QPushButton#ghost { background:transparent; color:#9db3cf;"
            " border:1px solid rgba(255,255,255,35); border-radius:10px;"
            " padding:6px 14px; }"
            "QPushButton#ghost:hover { border-color:#10b981; color:#e6edf7; }")
    def toggle_lang(s):
        global LANG
        LANG = "en" if LANG == "ar" else "ar"; SET["lang"] = LANG
        s.done(3)
    def toggle_theme(s):
        apply_theme(dark=SET.get("theme") != "dark")
    def try_login(s):
        r = q1("SELECT * FROM users WHERE username=? AND password=? AND active=1",
               (s.u.text().strip(),
                hashlib.sha256(s.p.text().encode()).hexdigest()))
        if not r:
            QMessageBox.warning(s, APP,
                                "❌ " + T("Wrong username or password")); return
        global CUR_USER; CUR_USER = r; s.accept()
        # ============================== POS =========================================
def product_create_dialog(parent, barcode=""):
    """🆕 نافذة الصنف الجديد: باركود/اسم/تكلفة/سعر بيع/صلاحية/قسم/كمية"""
    d = QDialog(parent); d.setWindowTitle("🆕 " + T("Product"))
    d.setMinimumWidth(520); f = QFormLayout(d); f.setSpacing(12)
    bc = QLineEdit(barcode); bc.setMinimumHeight(40)
    na = QLineEdit(); na.setMinimumHeight(40)
    na.setPlaceholderText("اسم المنتج بالعربي" if LANG == "ar" else "Product name")
    ne = QLineEdit(); ne.setMinimumHeight(40)
    cost = QDoubleSpinBox(); cost.setMaximum(10**7); cost.setDecimals(2)
    cost.setMinimumHeight(40); cost.setAlignment(Qt.AlignCenter)
    price = QDoubleSpinBox(); price.setMaximum(10**7); price.setDecimals(2)
    price.setMinimumHeight(40); price.setAlignment(Qt.AlignCenter)
    exp = QDateEdit(QDate.currentDate().addYears(1)); exp.setCalendarPopup(True)
    exp.setMinimumHeight(40)
    cat = QComboBox(); cat.setMinimumHeight(40); cat.addItem("—", None)
    for cc in q("SELECT * FROM categories ORDER BY name"):
        cat.addItem("🗂 " + cc["name"], cc["id"])
    editable_combo(cat)
    qty = QSpinBox(); qty.setRange(1, 10**6); qty.setValue(1)
    qty.setMinimumHeight(40); qty.setAlignment(Qt.AlignCenter)
    f.addRow("📷 " + T("Code"), bc)
    f.addRow("🏷 " + T("Name (AR)") + " *", na)
    f.addRow("🏷 Name (EN)", ne)
    f.addRow("💵 " + T("Cost") + " *", cost)
    f.addRow("💰 " + ("سعر البيع *" if LANG == "ar" else "Selling price *"), price)
    f.addRow("📅 " + T("Expiry"), exp)
    f.addRow("🗂 " + T("Category"), cat)
    f.addRow(T("Qty"), qty)
    ok = QPushButton("✅ " + T("Save")); ok.setObjectName("success")
    ok.setMinimumHeight(44); f.addRow(ok)
    def do():
        if not na.text().strip():
            QMessageBox.warning(d, APP, "🏷 اكتب اسم المنتج"); na.setFocus(); return
        if price.value() <= 0:
            QMessageBox.warning(d, APP, "💰 أدخل سعر البيع"); price.setFocus(); return
        d.accept()
    ok.clicked.connect(do); na.returnPressed.connect(do)
    bc.returnPressed.connect(na.setFocus)
    if d.exec() != QDialog.Accepted: return None
    bcv = bc.text().strip()
    if not bcv:
        bcv = "P" + str(int(dt.datetime.now().timestamp() * 1000) % 10**9)
    if q1("SELECT id FROM products WHERE barcode=?", (bcv,)):
        QMessageBox.information(parent, APP, "⚠️ الكود مسجل لمنتج آخر"); return None
    pid = x("INSERT INTO products(barcode,name,name_ar,cost,price,active,icon,"
            "expiry,category_id) VALUES(?,?,?,?,?,1,'🛒',?,?)",
            (bcv, ne.text().strip() or na.text().strip(),
             na.text().strip(), cost.value(), price.value(),
             exp.date().toString("yyyy-MM-dd"), cat.currentData()))
    log("product_new", bcv)
    _cn = q1("SELECT name FROM categories WHERE id=?", (cat.currentData(),))
    return {"pid": pid, "qty": qty.value(), "cost": cost.value(),
            "cat": (_cn["name"] if _cn else None)}

class PaymentDialog(QDialog):
    def __init__(s, total):
        super().__init__(); s.total = total; s.ok_paid = False
        s.setWindowTitle("💳 " + T("Payment")); s.setFixedWidth(460)
        v = QVBoxLayout(s)
        tt = QLabel(T("Grand Total") + f":  {money(total)} {cur()}")
        tt.setObjectName("big"); tt.setAlignment(Qt.AlignCenter)
        tt.setStyleSheet("color:#10b981;"); v.addWidget(tt)
        g = QFormLayout()
        s.cash = QDoubleSpinBox(); s.cash.setMaximum(10**7); s.cash.setDecimals(2)
        s.cash.setValue(total); s.cash.setAlignment(Qt.AlignCenter)
        s.cash.setMinimumHeight(40)
        s.card = QDoubleSpinBox(); s.card.setMaximum(10**7); s.card.setDecimals(2)
        s.card.setAlignment(Qt.AlignCenter); s.card.setMinimumHeight(40)
        g.addRow(T("Cash amount"), s.cash); g.addRow(T("Card amount"), s.card)
        v.addLayout(g)
        qv = QHBoxLayout()
        for val in [total, 50, 100, 200, 500]:
            b = QPushButton(money(val)); b.setObjectName("ghost")
            b.setMinimumHeight(38)
            b.clicked.connect(lambda _, v_=val: s.quick(v_)); qv.addWidget(b)
        v.addLayout(qv)
        s.chg = QLabel(T("Change due:") + " 0.00"); s.chg.setObjectName("big")
        s.chg.setAlignment(Qt.AlignCenter); s.chg.setStyleSheet("color:#2563eb;")
        v.addWidget(s.chg)
        s.cash.valueChanged.connect(s.upd); s.card.valueChanged.connect(s.upd)
        ok = QPushButton("✅ " + T("Confirm")); ok.setObjectName("success")
        ok.setFixedHeight(46); ok.clicked.connect(s.accept); v.addWidget(ok)
        s.upd()
    def quick(s, v_):
        s.cash.setValue(v_ if v_ >= s.total else max(0, s.total - s.card.value()))
    def upd(s):
        paid = s.cash.value() + s.card.value()
        s.ok_paid = paid >= s.total - 0.001
        s.chg.setText(T("Change due:") + " " +
                      money(max(0, paid - s.total)) + " " + cur())
    def values(s):
        return (s.cash.value(), s.card.value(),
                max(0.0, s.cash.value() + s.card.value() - s.total))

class POSPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw
        s.items = []; s.customer_id = 1; s.coupon_amt = 0
        s.coupon_code = ""; s.points_use = 0; s.tax_on = False
        h = QHBoxLayout(s); h.setContentsMargins(12, 12, 12, 12); h.setSpacing(12)
        pw = QWidget(); pv = QVBoxLayout(pw); pv.setContentsMargins(0, 0, 0, 0)
        sr = QHBoxLayout()
        s.bar = QLineEdit(); s.bar.setPlaceholderText("📷  " +
                                                      T("Barcode / Product name"))
        s.bar.setFixedHeight(46); s.bar.returnPressed.connect(s.scan)
        sr.addWidget(s.bar, 1)
        ba = QPushButton("➕ " + T("Add")); ba.setObjectName("primary")
        ba.setFixedHeight(46); ba.clicked.connect(s.scan); sr.addWidget(ba)
        s.loc = QComboBox(); s.loc.setMinimumHeight(38)
        for l in q("SELECT * FROM locations WHERE type IN ('branch','store') "
                   "ORDER BY id"):
            s.loc.addItem(("🏬 " if l["type"] == "branch" else "🏪 ")
                          + l["name"], l["id"])
        s.loc.currentIndexChanged.connect(lambda *_: s.build_grid())
        sr.addWidget(s.loc); pv.addLayout(sr)
        s.grid = QGridLayout(); s.grid.setSpacing(10)
        s.inner = QWidget(); s.inner.setLayout(s.grid)
        sg = QScrollArea(); sg.setWidgetResizable(True); sg.setWidget(s.inner)
        pv.addWidget(sg, 1); h.addWidget(pw, 3)
        cw = QWidget(); cv = QVBoxLayout(cw); cv.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        nb = QPushButton("🆕 " + T("New Sale")); nb.setObjectName("success")
        nb.clicked.connect(s.clear_cart); top.addWidget(nb)
        hb = QPushButton("⏸ " + T("Held Sales")); hb.clicked.connect(s.held_dialog)
        top.addWidget(hb)
        cb = QPushButton("🗑 " + T("Clear")); cb.setObjectName("danger")
        cb.clicked.connect(s.clear_cart); top.addWidget(cb)
        cv.addLayout(top)
        crow = QHBoxLayout()
        s.cust = QComboBox(); s.cust.setMinimumHeight(38)
        for c in q("SELECT * FROM customers ORDER BY id"):
            s.cust.addItem("👤 " + c["name"] + f" ({T(c['tier'])})", c["id"])
        editable_combo(s.cust)
        s.cust.currentIndexChanged.connect(s.cust_changed)
        crow.addWidget(QLabel("👤")); crow.addWidget(s.cust, 1); cv.addLayout(crow)
        s.cart = QTableWidget(0, 5)
        s.cart.setHorizontalHeaderLabels([T("Item"), T("Price"), T("Qty"),
                                          T("Line discount %"), T("Total")])
        s.cart.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        s.cart.verticalHeader().setVisible(False)
        s.cart.setEditTriggers(QTableWidget.NoEditTriggers)
        s.cart.verticalHeader().setDefaultSectionSize(48)
        s._building = False
        cv.addWidget(s.cart, 1)
        ops = QHBoxLayout()
        b1 = QPushButton("➖"); b1.setMinimumHeight(36); b1.clicked.connect(s.dec)
        b2 = QPushButton("➕"); b2.setMinimumHeight(36); b2.clicked.connect(s.inc)
        b3 = QPushButton("❌ " + T("Remove")); b3.setObjectName("danger")
        b3.setMinimumHeight(36); b3.clicked.connect(s.remove)
        for b_ in (b1, b2, b3): ops.addWidget(b_)
        cv.addLayout(ops)
        ex = QHBoxLayout()
        s.disc = QDoubleSpinBox(); s.disc.setRange(0, 100); s.disc.setPrefix("% ")
        s.disc.setMinimumHeight(36)
        s.cp = QLineEdit(); s.cp.setPlaceholderText("🎟️ " + T("Coupon"))
        s.cp.setMinimumHeight(36)
        ap = QPushButton(T("Coupon")); ap.setObjectName("primary")
        ap.setMinimumHeight(36); ap.clicked.connect(s.apply_coupon)
        ex.addWidget(s.disc); ex.addWidget(s.cp, 1); ex.addWidget(ap)
        cv.addLayout(ex)
        tx = QHBoxLayout()
        s.tax_btn = QPushButton("🧾 " + T("Tax") + ": " + T("off"))
        s.tax_btn.setCheckable(True); s.tax_btn.setMinimumHeight(40)
        s.tax_btn.clicked.connect(s.toggle_tax)
        tx.addWidget(s.tax_btn, 1); cv.addLayout(tx)
        pts = QHBoxLayout()
        s.redeem = QSpinBox(); s.redeem.setRange(0, 10**6)
        s.redeem.setPrefix("⭐ "); s.redeem.setMinimumHeight(36)
        rb = QPushButton("⭐ " + T("Redeem Points")); rb.setObjectName("warn")
        rb.setMinimumHeight(36); rb.clicked.connect(s.use_points)
        pts.addWidget(s.redeem); pts.addWidget(rb); pts.addStretch(1)
        cv.addLayout(pts)
        s.tot = QLabel("0.00"); s.tot.setAlignment(Qt.AlignCenter)
        s.tot.setStyleSheet("background:rgba(16,185,129,.12);border-radius:12px;"
                            "padding:14px; color:#10b981; font-size:22px; "
                            "font-weight:800;")
        cv.addWidget(s.tot)
        pay = QPushButton("💰 " + T("Pay & Complete")); pay.setObjectName("success")
        pay.setFixedHeight(54); pay.clicked.connect(s.pay); cv.addWidget(pay)
        hld = QPushButton("⏸ " + T("Hold")); hld.setMinimumHeight(40)
        hld.clicked.connect(s.hold); cv.addWidget(hld)
        h.addWidget(cw, 2)
        s.build_grid(); QTimer.singleShot(300, s.bar.setFocus)
    def prod_price(s, p):
        td = today()
        for o in q("SELECT * FROM offers WHERE active=1 AND starts<=? AND ends>=?",
                   (td, td)):
            nm = (p["name_ar"] or "") + " " + p["name"]
            if o["scope"] == "product" and o["target"] in nm:
                return round(p["price"] * (1 - o["percent"] / 100), 2)
        return p["price"]
    def build_grid(s, term=""):
        while s.grid.count():
            it = s.grid.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        rows = q("""SELECT p.*,
                     IFNULL((SELECT SUM(qty) FROM stock WHERE product_id=p.id
                     AND location_id=?),0) tq,
                     IFNULL((SELECT SUM(qty) FROM stock WHERE product_id=p.id),0) ttq
                     FROM products p WHERE p.active=1
                     ORDER BY p.id DESC""", (s.loc.currentData(),))
        if term:
            rows = [r for r in rows if term.lower() in
                    (r["name"] + " " + (r["name_ar"] or "") + " "
                     + (r["barcode"] or "")).lower()]
        r = c = 0; MAXC = 5
        for p in rows:
            qty = p["tq"]
            extra = (f"\n🏬 {T('Stock:')} {p['ttq']:g}"
                     if qty <= 0 and p["ttq"] > 0 else "")
            exp_badge = ""
            if p.get("expiry"):
                try:
                    ed_ = dt.date.fromisoformat(p["expiry"])
                    lf_ = (ed_ - dt.date.today()).days
                    if lf_ < 0: exp_badge = "\n🔴 منتهي الصلاحية"
                    elif lf_ <= 7: exp_badge = f"\n🟠 باقي {lf_} يوم"
                except Exception: pass
            btn = QPushButton(f"{p['icon'] or '📦'}  {disp_name(p)}\n💰 "
                              f"{money(s.prod_price(p))} {cur()}\n📍 "
                              f"{T('Stock:')} {qty:g}{extra}{exp_badge}")
            btn.setFixedHeight(118 if (extra or exp_badge) else 104)
            btn.setStyleSheet("text-align:center;font-weight:600;font-size:14px;")
            if qty <= 0 or exp_badge.startswith("\n🔴"):
                btn.setEnabled(False)
                btn.setStyleSheet("background:rgba(148,163,184,.25);"
                                  "color:#94a3b8;")
            btn.clicked.connect(lambda _, pid=p["id"]: s.add_product(pid))
            s.grid.addWidget(btn, r, c); c += 1
            if c == MAXC: c = 0; r += 1
        s.grid.setRowStretch(r + 1, 1); s.grid.setColumnStretch(MAXC, 1)
        add_completer(s.bar, [f"{r['barcode']} | {disp_name(r)}" for r in rows])
    def scan(s):
        t = s.bar.text().strip()
        if not t: return
        if " | " in t: t = t.split(" | ")[0].strip()
        p = q1("SELECT * FROM products WHERE barcode=?", (t,))
        if not p:
            r = q("SELECT * FROM products WHERE name LIKE ? OR name_ar LIKE ? "
                  "LIMIT 1", (f"%{t}%", f"%{t}%"))
            p = r[0] if r else None
        if not p:
            QMessageBox.warning(s, APP, "❌"); s.bar.clear(); s.bar.setFocus()
            return
        s.add_product(p["id"]); s.bar.clear(); s.bar.setFocus()
    def add_product(s, pid):
        _lid = s.loc.currentData()
        _lt = q1("SELECT type FROM locations WHERE id=?", (_lid,)) if _lid else None
        if _lt is None or _lt["type"] == "warehouse":
            QMessageBox.warning(s, APP, "🏭 " + (
                "البيع من المخزن الرئيسي ممنوع — حوّل البضاعة للمحل أولًا"
                if LANG == "ar" else
                "Selling from warehouse is blocked."))
            return
        p = q1("SELECT * FROM products WHERE id=?", (pid,))
        if p.get("expiry"):
            try:
                ed_ = dt.date.fromisoformat(p["expiry"])
                lf_ = (ed_ - dt.date.today()).days
                if lf_ < 0:
                    QMessageBox.warning(s, APP, "🚫 " + disp_name(p) + " — " +
                        ("منتهي الصلاحية! لا يمكن بيعه"
                         if LANG == "ar" else "EXPIRED! Cannot sell"))
                    return
                if lf_ <= 7:
                    QMessageBox.warning(s, APP, "🟠 " + disp_name(p) + " — " +
                        (f"الصلاحية باقي {lf_} يوم"
                         if LANG == "ar" else f"expires in {lf_} days"))
            except Exception: pass
        st = q1("SELECT IFNULL(SUM(qty),0) tq FROM stock "
                "WHERE product_id=? AND location_id=?",
                (pid, _lid))["tq"]
        in_cart = sum(i["qty"] for i in s.items if i["pid"] == pid)
        if in_cart + 1 > st:
            tt_ = q1("SELECT IFNULL(SUM(qty),0) v FROM stock WHERE product_id=?",
                     (pid,))["v"]
            msg = "📦 " + T("Insufficient payment!") + f"  (📍 {st:g}"
            msg += f"  |  🏬 {tt_:g})" if tt_ > st else ")"
            QMessageBox.warning(s, APP, msg); return
        for i in s.items:
            if i["pid"] == pid: i["qty"] += 1; break
        else:
            s.items.append({"pid": pid, "name": disp_name(p),
                            "price": s.prod_price(p),
                            "cost": p["cost"], "qty": 1})
        s.render()
    def inc(s):
        r = s.cart.currentRow()
        if r >= 0: s.items[r]["qty"] += 1; s.render()
    def dec(s):
        r = s.cart.currentRow()
        if r >= 0:
            s.items[r]["qty"] -= 1
            if s.items[r]["qty"] <= 0: s.items.pop(r)
            s.render()
    def remove(s):
        r = s.cart.currentRow()
        if r >= 0: s.items.pop(r); s.render()
    def clear_cart(s):
        s.items = []; s.coupon_amt = 0; s.coupon_code = ""
        s.disc.setValue(0); s.redeem.setValue(0); s.points_use = 0; s.render()
    def cust_changed(s, *_):
        d = s.cust.currentData()
        s.customer_id = d if d else 1
        s.render()
    def tier_disc(s):
        c = q1("SELECT tier FROM customers WHERE id=?", (s.customer_id,))
        tier = c["tier"] if c else "Bronze"
        if tier == "Gold":   return float(SET.get("tier_gold_disc", 5))
        if tier == "Silver": return float(SET.get("tier_silver_disc", 2))
        return 0
    def apply_coupon(s):
        code = s.cp.text().strip().upper()
        if not code: return
        c = q1("SELECT * FROM coupons WHERE UPPER(code)=? AND active=1", (code,))
        td = today()
        if not c or (c["starts"] and c["starts"] > td) or \
           (c["ends"] and c["ends"] < td):
            QMessageBox.warning(s, APP, "🎟️ " + T("Invalid coupon")); return
        sub = sum(i["price"] * i["qty"] for i in s.items)
        if sub < c["min_total"]:
            QMessageBox.warning(s, APP, "🎟️ ≥ " + money(c["min_total"])); return
        s.coupon_amt = (round(sub * c["value"] / 100, 2)
                        if c["type"] == "percent" else c["value"])
        s.coupon_code = code; s.render()
    def use_points(s):
        c = q1("SELECT * FROM customers WHERE id=?", (s.customer_id,))
        pts = s.redeem.value()
        if not c or pts <= 0: return
        if pts > c["points"]: QMessageBox.warning(s, APP, "⭐"); return
        s.points_use = pts; s.render()
    def totals(s):
        line_disc = sum(i.get("ldisc", 0) * i["price"] * i["qty"] / 100
                        for i in s.items)
        sub = sum(i["price"] * i["qty"] for i in s.items)
        d = min(round(sub * s.disc.value() / 100, 2)
                + round(sub * s.tier_disc() / 100, 2)
                + s.coupon_amt
                + s.points_use * float(SET.get("loyalty_redeem", 0.1))
                + line_disc, sub)
        tax = (round((sub - d) * float(SET.get("vat", 15)) / 100, 2)
               if getattr(s, "tax_on", False) else 0.0)
        return sub, d, tax, round(sub - d + tax, 2)
    def toggle_tax(s):
        s.tax_on = s.tax_btn.isChecked()
        if s.tax_on:
            s.tax_btn.setText(f"🧾 {T('Tax')} {SET.get('vat','15')}% ✅")
            s.tax_btn.setStyleSheet("background:#f59e0b;color:#fff;"
                                    "font-weight:800;border:none;")
        else:
            s.tax_btn.setText("🧾 " + T("Tax") + ": " + T("off"))
            s.tax_btn.setStyleSheet("")
        s.update_totals()
    def render(s):
        s._building = True
        s.cart.setRowCount(len(s.items))
        for i, it in enumerate(s.items):
            nm = QTableWidgetItem(it["name"])
            nm.setTextAlignment(Qt.AlignCenter)
            s.cart.setItem(i, 0, nm)
            pw = QDoubleSpinBox(); pw.setMaximum(10**7); pw.setDecimals(2)
            pw.setValue(it["price"]); pw.setMinimumHeight(40)
            pw.setAlignment(Qt.AlignCenter)
            pw.valueChanged.connect(lambda val, ix=i: s._edit_price(ix, val))
            s.cart.setCellWidget(i, 1, pw)
            qw = QDoubleSpinBox(); qw.setMaximum(10**6); qw.setDecimals(2)
            qw.setValue(it["qty"]); qw.setMinimumHeight(40)
            qw.setAlignment(Qt.AlignCenter)
            qw.valueChanged.connect(lambda val, ix=i: s._edit_qty(ix, val))
            s.cart.setCellWidget(i, 2, qw)
            ds = QSpinBox(); ds.setRange(0, 100); ds.setSuffix("%")
            ds.setValue(int(it.get("ldisc", 0))); ds.setMinimumHeight(36)
            ds.setAlignment(Qt.AlignCenter)
            ds.valueChanged.connect(lambda val, ix=i: s._edit_ldisc(ix, val))
            s.cart.setCellWidget(i, 3, ds)
            tt = QTableWidgetItem(money(it["price"]
                  * (1 - it.get("ldisc", 0) / 100) * it["qty"]))
            tt.setTextAlignment(Qt.AlignCenter)
            s.cart.setItem(i, 4, tt)
        s._building = False
        s.update_totals()
    def _edit_qty(s, ix, val):
        if s._building or ix >= len(s.items): return
        s.items[ix]["qty"] = val
        it = s.items[ix]
        tt = s.cart.item(ix, 4)
        if tt: tt.setText(money(it["price"]
              * (1 - it.get("ldisc", 0) / 100) * val))
        s.update_totals()
    def _edit_price(s, ix, val):
        if s._building or ix >= len(s.items): return
        s.items[ix]["price"] = val
        it = s.items[ix]
        tt = s.cart.item(ix, 4)
        if tt: tt.setText(money(val
              * (1 - it.get("ldisc", 0) / 100) * it["qty"]))
        s.update_totals()
    def _edit_ldisc(s, ix, val):
        if s._building or ix >= len(s.items): return
        s.items[ix]["ldisc"] = val
        it = s.items[ix]
        tt = s.cart.item(ix, 4)
        if tt: tt.setText(money(it["price"] * (1 - val / 100) * it["qty"]))
        s.update_totals()
    def update_totals(s):
        sub, d, tax, tot = s.totals()
        s.tot.setText(f"{T('Subtotal')} {money(sub)} | {T('Discount')} "
                      f"-{money(d)} | {T('Tax')} {money(tax)}\n"
                      f"{T('Grand Total')}: {money(tot)} {cur()}")
    def hold(s):
        if not s.items: return
        x("INSERT INTO held_sales(ts,username,label,data) VALUES(?,?,?,?)",
          (nows(), CUR_USER["username"], s.cust.currentText(),
           json.dumps({"items": s.items, "customer_id": s.customer_id,
                       "disc": s.disc.value(), "coupon": s.coupon_code,
                       "coupon_amt": s.coupon_amt})))
        log("hold_sale"); s.clear_cart()
    def held_dialog(s):
        rows = q("SELECT * FROM held_sales ORDER BY id DESC")
        d = QDialog(s); d.setWindowTitle("⏸ " + T("Held Sales"))
        d.setMinimumWidth(560)
        v = QVBoxLayout(d); t = QTableWidget(len(rows), 3)
        t.setHorizontalHeaderLabels([T("Date"), T("Customer"), T("Total")])
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.verticalHeader().setVisible(False)
        for i, r in enumerate(rows):
            data = json.loads(r["data"])
            tot = sum(i_["price"] * i_["qty"] for i_ in data["items"])
            for j, val in enumerate([r["ts"], r["label"], money(tot)]):
                c = QTableWidgetItem(val); c.setTextAlignment(Qt.AlignCenter)
                t.setItem(i, j, c)
        v.addWidget(t)
        hb = QHBoxLayout()
        res = QPushButton("▶ " + T("Resume")); res.setObjectName("success")
        res.setMinimumHeight(40)
        dl = QPushButton("🗑 " + T("Delete")); dl.setObjectName("danger")
        dl.setMinimumHeight(40)
        hb.addWidget(res); hb.addWidget(dl); v.addLayout(hb)
        def do_resume():
            rr = t.currentRow()
            if rr < 0: return
            data = json.loads(rows[rr]["data"])
            s.items = data["items"]; s.disc.setValue(data.get("disc", 0))
            s.coupon_amt = data.get("coupon_amt", 0)
            s.coupon_code = data.get("coupon", "")
            ix = s.cust.findData(data.get("customer_id", 1))
            if ix >= 0: s.cust.setCurrentIndex(ix)
            x("DELETE FROM held_sales WHERE id=?", (rows[rr]["id"],))
            s.render(); d.accept()
        def do_del():
            rr = t.currentRow()
            if rr >= 0:
                x("DELETE FROM held_sales WHERE id=?", (rows[rr]["id"],))
                d.accept()
        res.clicked.connect(do_resume); dl.clicked.connect(do_del)
        d.resize(580, 420); d.exec()
    def pay(s):
        if not s.items:
            QMessageBox.information(s, APP, T("Cart is empty")); return
        sh = q1("SELECT * FROM shifts WHERE username=? AND status='open' "
                "ORDER BY id DESC", (CUR_USER["username"],))
        if not sh:
            QMessageBox.warning(s, APP, "🕒 " + T("No open shift!"))
            s.mw.goto("shifts"); return
        for i in s.items:
            st_ = q1("SELECT IFNULL(SUM(qty),0) tq FROM stock WHERE "
                     "product_id=? AND location_id=?",
                     (i["pid"], s.loc.currentData()))["tq"]
            if i["qty"] > st_:
                QMessageBox.warning(s, APP, "📦 " + i["name"] + " — " +
                    ("الرصيد اتغير! المتاح الآن: " if LANG == "ar"
                     else "Stock changed! Available: ") + f"{st_:g}")
                s.render(); return
        sub, d_, tax, tot = s.totals()
        dlg = PaymentDialog(tot)
        if dlg.exec() != QDialog.Accepted: return
        if not dlg.ok_paid:
            QMessageBox.warning(s, APP, T("Insufficient payment!")); return
        cash, card, change = dlg.values()
        no = inv_no("SL")
        sid = x("INSERT INTO sales(invoice_no,ts,username,customer_id,"
                "location_id,shift_id,subtotal,discount,tax,total,paid_cash,"
                "paid_card,change,status,coupon) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'completed',?)",
                (no, nows(), CUR_USER["username"], s.customer_id,
                 s.loc.currentData(), sh["id"], sub, d_, tax, tot,
                 cash, card, change, s.coupon_code))
        for i in s.items:
            eff_price = round(i["price"]
                              * (1 - i.get("ldisc", 0) / 100), 2)
            x("INSERT INTO sale_items(sale_id,product_id,name,qty,price,cost,"
              "total) VALUES(?,?,?,?,?,?,?)",
              (sid, i["pid"], i["name"], i["qty"], eff_price, i["cost"],
               eff_price * i["qty"]))
            move_stock(i["pid"], s.loc.currentData(), -i["qty"], "sale", no)
        if s.coupon_code:
            x("UPDATE coupons SET used=used+1 WHERE UPPER(code)=?",
              (s.coupon_code,))
        total_in = max(0.0, cash - change) + card
        if total_in > 0:
            _rs = ("مبيعات " if LANG == "ar" else "Sale ") + no
            for _acc in ("drawer", "vault"):
                x("INSERT INTO treasury(ts,account,direction,amount,reason,"
                  "ref,username) VALUES(?,?,?,?,?,?,?)",
                  (nows(), _acc, "in", total_in, _rs, no,
                   CUR_USER["username"]))
        if s.customer_id and s.customer_id > 1:
            earn = int(tot / 100 * float(SET.get("loyalty_earn", 1)))
            if s.points_use > 0:
                x("UPDATE customers SET points=points-? WHERE id=?",
                  (s.points_use, s.customer_id))
                x("INSERT INTO loyalty_txn(ts,customer_id,points,reason,"
                  "username) VALUES(?,?,?,?,?)",
                  (nows(), s.customer_id, -s.points_use, "redeem " + no,
                   CUR_USER["username"]))
            if earn > 0:
                x("UPDATE customers SET points=points+? WHERE id=?",
                  (earn, s.customer_id))
                x("INSERT INTO loyalty_txn(ts,customer_id,points,reason,"
                  "username) VALUES(?,?,?,?,?)",
                  (nows(), s.customer_id, earn, "earn " + no,
                   CUR_USER["username"]))
            c = q1("SELECT * FROM customers WHERE id=?", (s.customer_id,))
            spend = q1("SELECT IFNULL(SUM(total),0) v FROM sales "
                       "WHERE customer_id=? AND status='completed'",
                       (c["id"],))["v"]
            tier = ("Gold" if spend >= float(SET.get("tier_gold", 5000))
                    else "Silver"
                    if spend >= float(SET.get("tier_silver", 1000))
                    else "Bronze")
            if tier != c["tier"]:
                x("UPDATE customers SET tier=? WHERE id=?", (tier, c["id"]))
        for r_ in q("SELECT * FROM commission_rules WHERE active=1 "
                    "AND basis='sale' AND (employee=? OR employee='*')",
                    (CUR_USER["username"],)):
            amt = round(tot * r_["percent"] / 100 + r_["fixed"], 2)
            if amt > 0:
                x("INSERT INTO commissions(ts,employee,sale_id,amount) "
                  "VALUES(?,?,?,?)", (nows(), CUR_USER["username"], sid, amt))
        log("sale", f"{no} total={tot}")
        s.clear_cart(); s.mw.broadcast_all()
        if SET.get("direct_print") == "1":
            try:
                sale_ = q1("SELECT * FROM sales WHERE id=?", (sid,))
                qr_ = qr_image(zatca_qr_payload(sale_), 110)
                imgs_ = {"bar": code39_pixmap(sale_["invoice_no"]).toImage(),
                         "qr": qr_ if qr_ else blank_img(110, 110)}
                direct_print(receipt_html(sid), imgs_, a4=False)
            except Exception as e_:
                QMessageBox.warning(s, APP, "🖨 " + str(e_))
        elif QMessageBox.question(s, APP,
                "🧾 " + T("Print Receipt") + "?") == QMessageBox.Yes:
            print_receipt(sid, s)
        s.bar.setFocus()

# ---------- receipts / invoices --------------------------------------------
def receipt_html(sid):
    sale = q1("SELECT * FROM sales WHERE id=?", (sid,))
    items = q("SELECT * FROM sale_items WHERE sale_id=?", (sid,))
    rows = "".join(
        f"<tr><td>{i['name']}</td><td align=center>{i['qty']:g}</td>"
        f"<td align=right>{money(i['price'])}</td>"
        f"<td align=right>{money(i['total'])}</td></tr>" for i in items)
    comp = SET.get("company_ar") if LANG == "ar" else SET.get("company")
    tax_row = (f"<tr><td>{T('Tax')}</td>"
               f"<td align=right>{money(sale['tax'])}</td></tr>"
               if sale["tax"] else "")
    return f"""<div style="text-align:center;font-family:'Segoe UI';">
    <div style="font-size:16px;font-weight:800;">{comp}</div>
    <div style="font-size:10px;">{SET.get('tax_no')} • {SET.get('phone')}</div>
    <div style="font-size:11px;">{T('Receipt')} {sale['invoice_no']} • {sale['ts']}</div>
    <div style="font-size:10px;">{T('Cashier')}: {sale['username']}</div></div>
    <table width="100%" style="font-size:11px;margin-top:6px;" cellpadding=3>{rows}</table>
    <table width="100%" style="font-size:12px;margin-top:6px;" cellpadding=2>
    <tr><td>{T('Subtotal')}</td><td align=right>{money(sale['subtotal'])}</td></tr>
    <tr><td>{T('Discount')}</td><td align=right>-{money(sale['discount'])}</td></tr>
    {tax_row}
    <tr style="font-weight:800;font-size:14px;"><td>{T('Grand Total')} ({cur()})</td>
    <td align=right>{money(sale['total'])}</td></tr>
    <tr><td>{T('Cash')}</td><td align=right>{money(sale['paid_cash'])}</td></tr>
    <tr><td>{T('Card')}</td><td align=right>{money(sale['paid_card'])}</td></tr>
    <tr><td>{T('Change')}</td><td align=right>{money(sale['change'])}</td></tr></table>
    <div align="center"><img src="qr" width="110" height="110"><br>
    <img src="bar" width="190" height="46"><br>
    <span style="font-size:11px;">{sale['invoice_no']}</span></div>
    <div style="text-align:center;font-size:10px;margin-top:4px;">
    {SET.get('receipt_footer','')}</div>
    <div style="text-align:center;font-size:9px;color:#666;">
    by: ENG/Mostafa Hesham</div>"""

def print_receipt(sid, parent=None):
    sale = q1("SELECT * FROM sales WHERE id=?", (sid,))
    qr = qr_image(zatca_qr_payload(sale), 110)
    imgs = {"bar": code39_pixmap(sale["invoice_no"]).toImage(),
            "qr": qr if qr else blank_img(110, 110)}
    do_print(receipt_html(sid), imgs, a4=False, parent=parent)

def a4_invoice_html(sid, tax=True):
    sale = q1("SELECT * FROM sales WHERE id=?", (sid,))
    cust = (q1("SELECT * FROM customers WHERE id=?", (sale["customer_id"],))
            if sale["customer_id"] else None)
    items = q("SELECT * FROM sale_items WHERE sale_id=?", (sid,))
    rows = "".join(
        f"<tr><td align=center>{n+1}</td><td>{i['name']}</td>"
        f"<td align=center>{i['qty']:g}</td>"
        f"<td align=right>{money(i['price'])}</td>"
        f"<td align=right>{money(i['total'])}</td></tr>"
        for n, i in enumerate(items))
    comp = SET.get("company_ar") if LANG == "ar" else SET.get("company")
    tax_row = (f"<tr><td>{T('Tax')} ({SET.get('vat')}%)</td>"
               f"<td align=right>{money(sale['tax'])}</td></tr>"
               if sale["tax"] else "")
    head = ""
    if tax:
        head = (f"<tr><th align=right>{T('Seller')}</th>"
                f"<th align=right>{comp} — {SET.get('tax_no')}</th></tr>"
                f"<tr><th align=right>{T('Buyer')}</th><th align=right>"
                f"{cust['name'] if cust else T('Walk-in')}</th></tr>")
    return f"""<div style="font-family:'Segoe UI';">
    <h1 style="color:#0e1a2b;">{T('Tax Invoice') if tax else T('Receipt')} — {sale['invoice_no']}</h1>
    <table width="100%" cellpadding=6 style="font-size:13px;">{head}
    <tr><th align=right>{T('Date')}</th>
    <th align=right>{sale['ts']} — {T('Cashier')}: {sale['username']}</th></tr></table>
    <table width="100%" cellpadding=6 style="font-size:13px;margin-top:12px;border:1px solid #333;">
    <tr style="background:#0e1a2b;color:#fff;"><th>#</th><th align=left>{T('Item')}</th>
    <th>{T('Qty')}</th><th align=right>{T('Price')}</th><th align=right>{T('Total')}</th></tr>
    {rows}</table>
    <table width="45%" align="right" cellpadding=5 style="font-size:13px;margin-top:10px;">
    <tr><td>{T('Subtotal')}</td><td align=right>{money(sale['subtotal'])}</td></tr>
    <tr><td>{T('Discount')}</td><td align=right>-{money(sale['discount'])}</td></tr>
    {tax_row}
    <tr style="font-weight:800;font-size:15px;"><td>{T('Grand Total')} ({cur()})</td>
    <td align=right>{money(sale['total'])}</td></tr></table>
    <div style="clear:both;"><img src="qr" width="130" height="130"><br>
    <img src="bar" width="260" height="52"></div>
    <p style="margin-top:60px;font-size:13px;">{T('Received by')}: ..................
    &nbsp;&nbsp; {T('Delivered by')}: ..................</p>
    <p style="text-align:center;font-size:10px;color:#666;">by: ENG/Mostafa Hesham</p></div>"""

def print_a4(sid, tax=True, pdf=None, parent=None):
    sale = q1("SELECT * FROM sales WHERE id=?", (sid,))
    qr = qr_image(zatca_qr_payload(sale), 130)
    imgs = {"bar": code39_pixmap(sale["invoice_no"]).toImage(),
            "qr": qr if qr else blank_img(130, 130)}
    do_print(a4_invoice_html(sid, tax), imgs, a4=True, pdf=pdf, parent=parent)

# ============================== DASHBOARD ===================================
class Dashboard(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw
        v = QVBoxLayout(s); v.setContentsMargins(14, 14, 14, 14)
        top = QHBoxLayout()
        s.loc = QComboBox(); s.loc.addItem("🏬 " + T("All"), None)
        s.loc.setMinimumHeight(36)
        for l in q("SELECT * FROM locations"):
            s.loc.addItem("🏬 " + l["name"], l["id"])
        s.loc.currentIndexChanged.connect(s.refresh)
        top.addWidget(QLabel("🏬 " + T("Branch/Store")))
        top.addWidget(s.loc); top.addStretch(1); v.addLayout(top)
        g = QGridLayout(); g.setSpacing(12)
        s.c_sale = stat_card("💰", T("Today's Sales"), "—", "#10b981")
        s.c_inv  = stat_card("🧾", T("Today's Invoices"), "—", "#2563eb")
        s.c_prd  = stat_card("📦", T("Total Products"), "—", "#6366f1")
        s.c_low  = stat_card("⚠️", T("Low Stock Alerts"), "—", "#ef4444")
        s.c_cus  = stat_card("👥", T("Total Customers"), "—", "#f59e0b")
        s.c_cash = stat_card("🧰", T("Cash in Drawer"), "—", "#0ea5e9")
        for i, c in enumerate([s.c_sale, s.c_inv, s.c_prd]): g.addWidget(c, 0, i)
        for i, c in enumerate([s.c_low, s.c_cus, s.c_cash]): g.addWidget(c, 1, i)
        v.addLayout(g)
        ch = QHBoxLayout(); ch.setSpacing(12)
        s.chart = BarChart(T("Sales — last 7 days"))
        s.top = BarChart(T("Top products"), color="#10b981")
        ch.addWidget(s.chart, 2); ch.addWidget(s.top, 2); v.addLayout(ch, 1)
        s.refresh()
    def drawer(s):
        return q1("SELECT IFNULL(SUM(CASE WHEN direction='in' THEN amount "
                  "ELSE -amount END),0) v FROM treasury "
                  "WHERE account='drawer'")["v"]
    def refresh(s):
        lid = s.loc.currentData()
        w = " AND location_id=?" if lid else ""
        p = (lid,) if lid else ()
        t = q1(f"SELECT IFNULL(SUM(total),0) v, COUNT(*) c FROM sales "
               f"WHERE date(ts)=? AND status='completed'{w}", (today(),) + p)
        s.c_sale._v.setText(f"{money(t['v'])} {cur()}")
        s.c_inv._v.setText(str(t["c"]))
        s.c_prd._v.setText(str(q1("SELECT COUNT(*) c FROM products "
                                  "WHERE active=1")["c"]))
        s.c_low._v.setText(str(low_stock_count()))
        s.c_cus._v.setText(str(q1("SELECT COUNT(*) c FROM customers")["c"]))
        s.c_cash._v.setText(money(s.drawer()) + " " + cur())
        days = []
        for i in range(6, -1, -1):
            d = dt.date.today() - dt.timedelta(days=i)
            v_ = q1(f"SELECT IFNULL(SUM(total),0) v FROM sales WHERE date(ts)=? "
                    f"AND status='completed'{w}", (d.isoformat(),) + p)["v"]
            days.append((["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
                         [d.weekday()], round(v_, 2), None))
        s.chart.set_data(days)
        top = q(f"""SELECT si.name, SUM(si.total) v FROM sale_items si
                JOIN sales s ON s.id=si.sale_id WHERE s.status='completed'{w}
                GROUP BY si.name ORDER BY v DESC LIMIT 7""", p)
        colors = ["#10b981","#2563eb","#6366f1","#f59e0b","#ef4444",
                  "#0ea5e9","#8b5cf6"]
        s.top.set_data([(r["name"][:12], round(r["v"], 2), colors[i % 7])
                        for i, r in enumerate(top)])

# ============================== SALES =======================================
class SalesPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw
        v = QVBoxLayout(s); top = QHBoxLayout()
        s.f = QDateEdit(QDate.currentDate().addDays(-30))
        s.f.setCalendarPopup(True)
        s.t = QDateEdit(QDate.currentDate()); s.t.setCalendarPopup(True)
        b = QPushButton("🔍 " + T("Search")); b.setObjectName("primary")
        b.clicked.connect(s.refresh)
        top.addWidget(QLabel("📅")); top.addWidget(s.f)
        top.addWidget(QLabel("📅")); top.addWidget(s.t); top.addWidget(b)
        s.q = make_search(); top.addWidget(s.q); top.addStretch(1)
        v.addLayout(top)
        s.tbl = QTableWidget(); s.tbl.setAlternatingRowColors(True)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        v.addWidget(s.tbl, 1)
        bot = QHBoxLayout(); s.ids = []
        for lab, fn, sty in [("👁 " + T("View"), s.view, "primary"),
                             ("🧾 " + T("Print Receipt"), lambda: s.pr(False), ""),
                             ("📄 " + T("Print A4"), lambda: s.pr(True), ""),
                             ("⚡ " + T("E-Invoice JSON"), s.exp_json, ""),
                             ("↩️ " + T("Return"), s.ret, "danger"),
                             ("🗑 " + T("Delete"), s.del_sale, "danger"),
                             ("📤 " + T("Export CSV"), s.csv, "ghost")]:
            bb = QPushButton(lab); bb.setObjectName(sty); bb.clicked.connect(fn)
            bot.addWidget(bb)
        bot.addStretch(1); v.addLayout(bot); s.refresh()
    def refresh(s):
        f = s.f.date().toString("yyyy-MM-dd")
        t = s.t.date().toString("yyyy-MM-dd") + " 23:59:59"
        rows = q("""SELECT s.*, c.name cname FROM sales s
                 LEFT JOIN customers c ON c.id=s.customer_id
                 WHERE s.ts BETWEEN ? AND ? ORDER BY s.id DESC""", (f, t))
        hdr = [T("Invoice No"), T("Date"), T("Cashier"), T("Customer"),
               T("Grand Total"), T("Status")]
        s.tbl.clear(); s.tbl.setColumnCount(6); s.tbl.setRowCount(len(rows))
        s.tbl.setHorizontalHeaderLabels(hdr)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        s.ids = [r["id"] for r in rows]
        for i, r in enumerate(rows):
            vals = [r["invoice_no"], r["ts"], r["username"],
                    r["cname"] or T("Walk-in"), money(r["total"]),
                    T(r["status"])]
            for j, val in enumerate(vals):
                c = QTableWidgetItem(str(val)); c.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, c)
        wire_search(s.q, s.tbl)
    def sel(s):
        r = s.tbl.currentRow()
        return s.ids[r] if 0 <= r < len(s.ids) else None
    def del_sale(s):
        admin_delete(s, s.tbl, s.ids, "sales", after=s.refresh)
    def view(s):
        i = s.sel()
        if not i:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        sale = q1("SELECT * FROM sales WHERE id=?", (i,))
        items = q("SELECT * FROM sale_items WHERE sale_id=?", (i,))
        d = QDialog(s); d.setWindowTitle(sale["invoice_no"])
        d.setMinimumWidth(640)
        v = QVBoxLayout(d)
        tt = QTableWidget(len(items), 5)
        tt.setHorizontalHeaderLabels([T("Item"), T("Qty"), T("Price"),
                                      T("Cost"), T("Total")])
        tt.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tt.verticalHeader().setVisible(False)
        for n, it in enumerate(items):
            for j, val in enumerate([it["name"], f"{it['qty']:g}",
                    money(it["price"]), money(it["cost"]), money(it["total"])]):
                c = QTableWidgetItem(val); c.setTextAlignment(Qt.AlignCenter)
                tt.setItem(n, j, c)
        v.addWidget(tt)
        lb = QLabel(f"{T('Grand Total')}: {money(sale['total'])} {cur()} — "
                    f"{T(sale['status'])}")
        lb.setObjectName("big"); lb.setAlignment(Qt.AlignCenter)
        v.addWidget(lb)
        d.resize(660, 460); d.exec()
    def pr(s, a4=True):
        i = s.sel()
        if not i:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        if a4: print_a4(i, parent=s)
        else:  print_receipt(i, s)
    def exp_json(s):
        i = s.sel()
        if not i:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        sale = q1("SELECT * FROM sales WHERE id=?", (i,))
        items = q("SELECT * FROM sale_items WHERE sale_id=?", (i,))
        doc = {"invoice_no": sale["invoice_no"], "timestamp": sale["ts"],
               "seller": {"name": SET.get("company"),
                          "vat": SET.get("tax_no")},
               "totals": {"subtotal": sale["subtotal"],
                          "discount": sale["discount"],
                          "vat": sale["tax"], "total": sale["total"]},
               "qr_tlv_base64": zatca_qr_payload(sale),
               "lines": [{"name": it["name"], "qty": it["qty"],
                          "price": it["price"], "total": it["total"]}
                         for it in items]}
        path, _ = QFileDialog.getSaveFileName(s, "JSON",
                                              sale["invoice_no"] + ".json")
        if path:
            open(path, "w", encoding="utf-8").write(
                json.dumps(doc, ensure_ascii=False, indent=2))
            log("einvoicing_export", sale["invoice_no"])
    def csv(s):
        f = s.f.date().toString("yyyy-MM-dd")
        t = s.t.date().toString("yyyy-MM-dd") + " 23:59:59"
        rows = q("""SELECT s.*, c.name cname FROM sales s
                 LEFT JOIN customers c ON c.id=s.customer_id
                 WHERE s.ts BETWEEN ? AND ?""", (f, t))
        export_csv([T("Invoice No"), T("Date"), T("Cashier"), T("Customer"),
                    T("Grand Total"), T("Status")],
                   [[r["invoice_no"], r["ts"], r["username"], r["cname"] or "",
                     r["total"], r["status"]] for r in rows])
    def ret(s):
        i = s.sel()
        if not i:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        sale = q1("SELECT * FROM sales WHERE id=?", (i,))
        if sale["status"] == "returned":
            QMessageBox.information(s, APP,
                                    T("Status") + ": " + T("returned")); return
        items = q("SELECT * FROM sale_items WHERE sale_id=?", (i,))
        d = QDialog(s)
        d.setWindowTitle("↩️ " + T("Return") + " — " + sale["invoice_no"])
        d.setMinimumWidth(660)
        v = QVBoxLayout(d); spins = []
        t = QTableWidget(len(items), 4)
        t.setHorizontalHeaderLabels([T("Item"), T("Qty"), T("Price"),
                                     T("Return")])
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(48)
        for n, it in enumerate(items):
            t.setItem(n, 0, QTableWidgetItem(it["name"]))
            t.setItem(n, 1, QTableWidgetItem(f"{it['qty']:g}"))
            t.setItem(n, 2, QTableWidgetItem(money(it["price"])))
            sp = QDoubleSpinBox(); sp.setMaximum(it["qty"])
            sp.setMinimumHeight(38); sp.setAlignment(Qt.AlignCenter)
            spins.append(sp); t.setCellWidget(n, 3, sp)
        v.addWidget(t)
        rs = QLineEdit(); rs.setPlaceholderText(T("Reason"))
        rs.setMinimumHeight(38); v.addWidget(rs)
        rtax = QCheckBox("🧾 " + T("Tax") + f" ({SET.get('vat','15')}%)")
        racc = QComboBox(); racc.setMinimumHeight(38)
        racc.addItem("🧰 " + T("Drawer") + " / " + T("Cash"), "drawer")
        racc.addItem("🏦 " + T("Vault") + " / " + T("Card"), "vault")
        dmg = QCheckBox("⚠️ " + T("Damaged goods"))
        v.addWidget(rtax); v.addWidget(racc); v.addWidget(dmg)
        ok = QPushButton("✅ " + T("Confirm")); ok.setObjectName("danger")
        ok.setMinimumHeight(42); v.addWidget(ok)
        def do():
            qtys = [sp.value() for sp in spins]
            if not any(qtys): d.reject(); return
            sub = sum(qtys[n] * items[n]["price"] for n in range(len(items)))
            tax = (round(sub * float(SET.get("vat", 15)) / 100, 2)
                   if rtax.isChecked() else 0.0)
            refund = round(sub + tax, 2)
            b_ = q1("SELECT IFNULL(SUM(CASE WHEN direction='in' THEN amount "
                    "ELSE -amount END),0) v FROM treasury WHERE account=?",
                    (racc.currentData(),))["v"]
            if refund > b_ + 0.001:
                QMessageBox.warning(d, APP,
                    ("🧰 " if racc.currentData() == "drawer" else "🏦 ")
                    + T("Insufficient payment!")); return
            no = inv_no("RT")
            sid = x("INSERT INTO sales(invoice_no,ts,username,customer_id,"
                    "location_id,shift_id,subtotal,discount,tax,total,"
                    "paid_cash,paid_card,change,status,notes) "
                    "VALUES(?,?,?,?,?,NULL,?,0,?,?,0,0,0,'return',?)",
                    (no, nows(), CUR_USER["username"], sale["customer_id"],
                     sale["location_id"], -sub, -tax, -(sub + tax), rs.text()))
            for n, it in enumerate(items):
                if qtys[n] > 0:
                    x("INSERT INTO sale_items(sale_id,product_id,name,qty,"
                      "price,cost,total) VALUES(?,?,?,?,?,?,?)",
                      (sid, it["product_id"], it["name"], -qtys[n],
                       it["price"], it["cost"], -qtys[n] * it["price"]))
                    if dmg.isChecked():
                        x("INSERT INTO stock_moves(ts,product_id,location_id,"
                          "qty,reason,ref,username) VALUES(?,?,?,?,?,?,?)",
                          (nows(), it["product_id"], sale["location_id"], 0,
                           "damaged:" + no, no, CUR_USER["username"]))
                    else:
                        move_stock(it["product_id"], sale["location_id"],
                                   qtys[n], "return", no)
            x("UPDATE sales SET status='returned' WHERE id=?", (i,))
            if refund > 0:
                x("INSERT INTO treasury(ts,account,direction,amount,reason,"
                  "ref,username) VALUES(?,?,?,?,?,?,?)",
                  (nows(), racc.currentData(), "out", refund,
                   "مرتجع " + sale["invoice_no"], no, CUR_USER["username"]))
            log("return", f"{sale['invoice_no']} → {no}")
            QMessageBox.information(s, APP, T("Return processed"))
            s.refresh()
            try: s.mw.broadcast_all()
            except Exception: pass
            d.accept()
        ok.clicked.connect(do)
        d.resize(680, 500); d.exec()

# ============================== INVENTORY ===================================
class InventoryPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        s.tb = QTabWidget(); v.addWidget(s.tb)
        st = QWidget(); sv = QVBoxLayout(st)
        fr = QHBoxLayout()
        s.sq = make_search(); fr.addWidget(s.sq, 1)
        s.sfl = QComboBox(); s.sfl.setMinimumHeight(38)
        s.sfl.addItem("🌐 " + T("All Locations"), None)
        for l in q("SELECT * FROM locations ORDER BY CASE WHEN type='warehouse' "
                   "THEN 0 ELSE 1 END, id"):
            s.sfl.addItem(("🏭 " if l["type"] == "warehouse" else "🏬 ")
                          + l["name"], l["id"])
        s.sfl.currentIndexChanged.connect(s.load_stock)
        fr.addWidget(QLabel("🏬")); fr.addWidget(s.sfl)
        s.cfl = QComboBox(); s.cfl.setMinimumHeight(38)
        fr.addWidget(QLabel("🗂")); fr.addWidget(s.cfl)
        s.cfl.currentIndexChanged.connect(s.load_stock)
        sv.addLayout(fr)
        btns = QHBoxLayout()
        for lab, fn, sty in [
                ("➕ " + T("Product"), s.add_prod, "success"),
                ("✏️ " + T("Edit"), s.edit_selected, "primary"),
                ("📋 " + T("Stocktake"), s.stocktake, "warn"),
                ("⚖️ " + T("Adjust Stock"), s.adjust, ""),
                ("🏷️ " + T("Barcode Labels"), s.labels, ""),
                ("📥 " + T("Import CSV"), s.import_csv, ""),
                ("🛒 " + T("Shopping list"), s.shopping_list, "primary"),
                ("🗑 " + T("Delete"), s.del_prod, "danger")]:
            bt = QPushButton(lab); bt.setObjectName(sty); bt.setMinimumHeight(40)
            bt.clicked.connect(fn); btns.addWidget(bt)
        btns.addStretch(1); sv.addLayout(btns)
        s.stbl = QTableWidget(); s.stbl.setAlternatingRowColors(True)
        s.stbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.stbl.verticalHeader().setVisible(False)
        s.stbl.setSelectionBehavior(QTableWidget.SelectRows)
        s.stbl.doubleClicked.connect(s._dbl_guard)
        sv.addWidget(s.stbl)
        s.tb.addTab(st, "📊 " + T("Stock by Location"))
        # ===== 🗂 الأقسام =====
        ct = QWidget(); cv2 = QVBoxLayout(ct); cv2.setContentsMargins(0,0,0,0)
        ch = QHBoxLayout()
        lab_t = QLabel("🗂 " + T("Categories") + " ← " +
                       ("دبل-كليك لعرض المنتجات" if LANG == "ar"
                        else "double-click to open"))
        lab_t.setStyleSheet("font-weight:700;color:#64748b;")
        ch.addWidget(lab_t); ch.addStretch(1)
        cadd = QPushButton("➕ " + T("Add")); cadd.setObjectName("success")
        cadd.setMinimumHeight(38)
        def cat_add():
            nm, okk = QInputDialog.getText(ct, "➕ " + T("Categories"),
                ("اسم القسم:" if LANG == "ar" else "Category name:"))
            if okk and nm.strip():
                if q1("SELECT id FROM categories WHERE name=?", (nm.strip(),)):
                    QMessageBox.information(ct, APP, "⚠️"); return
                x("INSERT INTO categories(name) VALUES(?)", (nm.strip(),))
                log("category_new", nm.strip()); s.load_cats()
        cadd.clicked.connect(cat_add); ch.addWidget(cadd)
        cdel = QPushButton("🗑 " + T("Delete")); cdel.setObjectName("danger")
        cdel.setMinimumHeight(38)
        def cat_del():
            if getattr(s, "_cur_cat", None) is None:
                QMessageBox.information(ct, APP, T("Nothing selected")); return
            cid = s._cur_cat
            n_ = q1("SELECT COUNT(*) c FROM products WHERE category_id=?",
                    (cid,))["c"]
            if n_:
                QMessageBox.warning(ct, APP, "⚠️ " + (
                    f"القسم فيه {n_:g} منتج — انقلها أولاً"
                    if LANG == "ar" else f"Has {n_:g} products")); return
            if not admin_password_check(s): return
            if QMessageBox.question(ct, APP, T("Are you sure?")) == QMessageBox.Yes:
                x("DELETE FROM categories WHERE id=?", (cid,))
                log("category_del", str(cid)); s._cur_cat = None; s.load_cats()
        cdel.clicked.connect(cat_del); ch.addWidget(cdel)
        cv2.addLayout(ch)
        split = QSplitter()
        s.ctbl = QTableWidget(0, 3)
        s.ctbl.setHorizontalHeaderLabels([T("Category"), T("Items count"),
                                          T("Stock value")])
        s.ctbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.ctbl.verticalHeader().setVisible(False)
        s.ctbl.setSelectionBehavior(QTableWidget.SelectRows)
        s.ctbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        s.ctbl.setAlternatingRowColors(True)
        s.ctbl.itemDoubleClicked.connect(s._cat_clicked)
        s.ctbl.itemClicked.connect(s._cat_clicked)
        split.addWidget(s.ctbl)
        right = QWidget(); rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv2 = QHBoxLayout()
        s.cat_lbl = QLabel("—"); s.cat_lbl.setStyleSheet(
            "font-weight:800;font-size:16px;color:#2563eb;")
        rv2.addWidget(s.cat_lbl); rv2.addStretch(1)
        bx2 = QPushButton("📤 " + T("Export CSV"))
        bx2.clicked.connect(s.export_cat); rv2.addWidget(bx2)
        rv.addLayout(rv2)
        s.ptbl = QTableWidget(0, 6)
        s.ptbl.setHorizontalHeaderLabels([T("Product Name"), T("Code"),
            T("Price"), T("Cost"), T("Total"), T("Expiry")])
        s.ptbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.ptbl.verticalHeader().setVisible(False)
        s.ptbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        s.ptbl.setAlternatingRowColors(True)
        s.pq = make_search(); rv.addWidget(s.pq)
        rv.addWidget(s.ptbl, 1)
        split.addWidget(right)
        split.setSizes([320, 780])
        cv2.addWidget(split, 1)
        s.tb.addTab(ct, "🗂 " + T("Categories"))
        # ===== 📜 الحركات =====
        mv = QWidget(); mvv = QVBoxLayout(mv)
        s.mq = make_search(); mvv.addWidget(s.mq)
        s.mtbl = QTableWidget(0, 7)
        s.mtbl.setHorizontalHeaderLabels([T("Date"), T("Product"),
            T("Location"), T("Qty"), T("Reason"), T("Ref No"), T("Username")])
        s.mtbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.mtbl.verticalHeader().setVisible(False)
        s.mtbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        mvv.addWidget(s.mtbl)
        s.tb.addTab(mv, "📜 " + T("Stock Moves"))
        s._fill_cat_filter()
        s.ensure_rows(); s.load_stock(); s.load_moves(); s.load_cats()
        s.tb.currentChanged.connect(s._tab_changed)
    def refresh(s):
        for fn in (s.load_stock, s.load_cats, s.load_moves):
            try: fn()
            except Exception: pass
    def _tab_changed(s, ix):
        try:
            txt = s.tb.tabText(ix)
            if txt.startswith("📊"): s.load_stock()
            elif txt.startswith("🗂"): s.load_cats()
            elif txt.startswith("📜"): s.load_moves()
        except Exception: pass
    def _fill_cat_filter(s, *_):
        if not hasattr(s, "cfl"): return
        cur = s.cfl.currentData()
        s.cfl.blockSignals(True); s.cfl.clear()
        s.cfl.addItem("🗂 " + T("All"), None)
        for cc in q("SELECT * FROM categories ORDER BY name"):
            s.cfl.addItem("🗂 " + cc["name"], cc["id"])
        if cur:
            ix = s.cfl.findData(cur)
            if ix >= 0: s.cfl.setCurrentIndex(ix)
        s.cfl.blockSignals(False)
    def ensure_rows(s, *_):
        x("INSERT OR IGNORE INTO stock(product_id,location_id,qty) "
          "SELECT p.id, l.id, 0 FROM products p, locations l")
    def shopping_list(s):
        rows = q("""SELECT p.*, IFNULL((SELECT SUM(qty) FROM stock
                 WHERE product_id=p.id),0) tot FROM products p
                 WHERE active=1 ORDER BY name""")
        need = [(p, max(p["min_stock"] * 2 - p["tot"], 1))
                for p in rows if p["tot"] < p["min_stock"]]
        if not need:
            QMessageBox.information(s, APP, "✅ " + T("All above minimum"))
            return
        d = QDialog(s); d.setWindowTitle("🛒 " + T("Shopping list"))
        d.resize(760, 560); v = QVBoxLayout(d)
        t = QTableWidget(len(need), 6)
        t.setHorizontalHeaderLabels([T("Product Name"), T("Code"),
            T("Min Stock"), T("Total"), T("Suggested"), T("Est. cost")])
        t.verticalHeader().setDefaultSectionSize(46)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        tot_val = 0.0
        for i, (p, sug) in enumerate(need):
            tot_val += sug * p["cost"]
            for j, val in enumerate([disp_name(p), p["barcode"],
                    f"{p['min_stock']:g}", f"{p['tot']:g}", f"{sug:g}",
                    money(sug * p["cost"])]):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignCenter)
                t.setItem(i, j, it)
        v.addWidget(t, 1)
        lab = QLabel("💰 " + T("Est. cost") + ": " + money(tot_val)
                     + " " + cur())
        lab.setObjectName("big"); v.addWidget(lab)
        hb = QHBoxLayout()
        ex = QPushButton("📤 " + T("Export CSV")); ex.setObjectName("primary")
        ex.clicked.connect(lambda: export_csv(
            [T("Product Name"), T("Code"), T("Min Stock"), T("Total"),
             T("Suggested"), T("Est. cost")],
            [[disp_name(p), p["barcode"], p["min_stock"], p["tot"], sug,
              sug * p["cost"]] for p, sug in need]))
        cl = QPushButton(T("Close")); cl.clicked.connect(d.accept)
        hb.addWidget(ex); hb.addWidget(cl); hb.addStretch(1); v.addLayout(hb)
        d.exec()

    def _rows_now(s):
        lid = s.sfl.currentData() if hasattr(s, "sfl") else None
        locs = q("SELECT * FROM locations ORDER BY CASE WHEN type='warehouse' "
                 "THEN 0 ELSE 1 END, id")
        prods = q("SELECT * FROM products WHERE active=1 ORDER BY name")
        sk = {}
        for r in q("SELECT product_id, location_id, qty FROM stock"):
            sk[(r["product_id"], r["location_id"])] = r["qty"]
        cflt = s.cfl.currentData() if hasattr(s, "cfl") else None
        rows = []
        for p in prods:
            if cflt and p["category_id"] != cflt: continue
            tot = sum(sk.get((p["id"], l["id"]), 0) for l in locs)
            if lid is None: rows.append((p, tot))
            elif sk.get((p["id"], lid), 0) > 0: rows.append((p, tot))
        return rows
    def load_stock(s):
        lid = s.sfl.currentData() if hasattr(s, "sfl") else None
        locs = q("SELECT * FROM locations ORDER BY CASE WHEN type='warehouse' "
                 "THEN 0 ELSE 1 END, id")
        rows = s._rows_now()
        hdr = [T("Product Name"), T("Code"), T("Price"), T("Cost"),
               T("Min Stock"), T("Expiry"), T("Total")] + \
              [l["name"] for l in locs]
        s.stbl.clear(); s.stbl.setColumnCount(len(hdr))
        s.stbl.setRowCount(len(rows)); s.stbl.setHorizontalHeaderLabels(hdr)
        s.stbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tdy = dt.date.today()
        for i, (p, tot) in enumerate(rows):
            exp = (dt.date.fromisoformat(p["expiry"])
                   if p.get("expiry") else None)
            badge = ""
            if exp and exp < tdy: badge = "🔴"
            elif exp and (exp - tdy).days <= 7: badge = "🟠"
            tot_b = "🔴" if tot <= 0 else "🟠" if tot < p["min_stock"] else "🟢"
            per = {}
            for r in q("SELECT location_id, qty FROM stock WHERE product_id=?",
                       (p["id"],)):
                per[r["location_id"]] = r["qty"]
            vals = [disp_name(p), p["barcode"], money(p["price"]),
                    money(p["cost"]), f"{p['min_stock']:g}",
                    (badge + " " if badge else "") + (p["expiry"] or "—"),
                    f"{tot_b} {tot:g}"]
            vals += [f"{per.get(l['id'], 0):g}" for l in locs]
            for j, val in enumerate(vals):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignCenter)
                if badge and j == 5:
                    it.setForeground(QBrush(QColor(
                        "#ef4444" if badge == "🔴" else "#f59e0b")))
                if j == 6 and tot <= 0:
                    it.setForeground(QBrush(QColor("#ef4444")))
                s.stbl.setItem(i, j, it)
        wire_search(s.sq, s.stbl)
    def _dbl_guard(s, row, col):
        try:
            if 1 <= col <= 5: s.edit_selected()
        except Exception: pass
    def edit_selected(s):
        rows = s._rows_now()
        r = s.stbl.currentRow()
        if not (0 <= r < len(rows)):
            QMessageBox.information(s, APP, T("Nothing selected")); return
        p, _ = rows[r]
        d = QDialog(s); d.setWindowTitle("✏️ " + disp_name(p))
        d.setMinimumWidth(560)
        f = QFormLayout(d); f.setSpacing(12)
        na = QLineEdit(p["name_ar"] or ""); na.setMinimumHeight(38)
        ne = QLineEdit(p["name"] or ""); ne.setMinimumHeight(38)
        bc = QLineEdit(p["barcode"] or ""); bc.setMinimumHeight(38)
        cat = QComboBox(); cat.setMinimumHeight(38); cat.addItem("—", None)
        for cc in q("SELECT * FROM categories ORDER BY name"):
            cat.addItem("🗂 " + cc["name"], cc["id"])
        if p.get("category_id"):
            ix = cat.findData(p["category_id"])
            if ix >= 0: cat.setCurrentIndex(ix)
        price = QDoubleSpinBox(); price.setMaximum(10**7); price.setDecimals(2)
        price.setValue(float(p["price"] or 0))
        price.setMinimumHeight(38); price.setAlignment(Qt.AlignCenter)
        cost = QDoubleSpinBox(); cost.setMaximum(10**7); cost.setDecimals(2)
        cost.setValue(float(p["cost"] or 0))
        cost.setMinimumHeight(38); cost.setAlignment(Qt.AlignCenter)
        mn = QDoubleSpinBox(); mn.setMaximum(10**6); mn.setDecimals(0)
        mn.setValue(float(p["min_stock"] or 0))
        mn.setMinimumHeight(38); mn.setAlignment(Qt.AlignCenter)
        exp = QDateEdit(QDate.currentDate().addYears(1))
        exp.setCalendarPopup(True); exp.setMinimumHeight(38)
        if p.get("expiry"):
            try: exp.setDate(QDate.fromString(p["expiry"], "yyyy-MM-dd"))
            except Exception: pass
        f.addRow("🏷 " + T("Name (AR)"), na)
        f.addRow("🏷 Name (EN)", ne)
        f.addRow("📷 " + T("Code"), bc)
        f.addRow("🗂 " + T("Category"), cat)
        f.addRow("💰 " + T("Price"), price)
        f.addRow("💵 " + T("Cost"), cost)
        f.addRow("⚠️ " + T("Min Stock"), mn)
        f.addRow("📅 " + T("Expiry"), exp)
        hb = QHBoxLayout()
        ok = QPushButton("💾 " + T("Save")); ok.setObjectName("success")
        ok.setMinimumHeight(44)
        ca = QPushButton(T("Cancel")); ca.setMinimumHeight(42)
        hb.addWidget(ok); hb.addWidget(ca); f.addRow(hb)
        ca.clicked.connect(d.reject)
        def do():
            bcv = bc.text().strip()
            if bcv and q1("SELECT id FROM products WHERE barcode=? AND id!=?",
                          (bcv, p["id"])):
                QMessageBox.warning(d, APP, "⚠️"); return
            x("UPDATE products SET name_ar=?,name=?,barcode=?,category_id=?,"
              "price=?,cost=?,min_stock=?,expiry=? WHERE id=?",
              (na.text().strip(), ne.text().strip() or na.text().strip(),
               bcv, cat.currentData(), price.value(), cost.value(),
               mn.value(), exp.date().toString("yyyy-MM-dd"), p["id"]))
            log("product_edit", f"pid={p['id']}")
            s.load_stock(); s.load_cats(); s._fill_cat_filter()
            if hasattr(s, "mw"): s.mw.broadcast_all()
            QMessageBox.information(d, APP, "✅ " + T("Saved"))
            d.accept()
        ok.clicked.connect(do); d.exec()
    def add_prod(s):
        res = product_create_dialog(s)
        if not res: return
        lid = s.sfl.currentData()
        if lid is None:
            wh = q1("SELECT id FROM locations WHERE type='warehouse' "
                    "ORDER BY id LIMIT 1")
            lid = wh["id"] if wh else None
            if lid is None:
                l0 = q1("SELECT id FROM locations ORDER BY id LIMIT 1")
                lid = l0["id"] if l0 else None
        if lid:
            move_stock(res["pid"], lid, res["qty"], "opening", "OPEN")
        s._fill_cat_filter(); s.load_stock(); s.load_moves()
        if hasattr(s, "mw"): s.mw.broadcast_all()
    def del_prod(s):
        if not (allowed("inventory") or is_admin()):
            QMessageBox.warning(s, APP, "🚫 " + T("No permission")); return
        rows = s._rows_now(); r = s.stbl.currentRow()
        if not (0 <= r < len(rows)):
            QMessageBox.information(s, APP, T("Nothing selected")); return
        p = rows[r][0]
        sold = q1("SELECT COUNT(*) c FROM sale_items WHERE product_id=?",
                  (p["id"],))["c"]
        msg = T("Are you sure?") + " — " + disp_name(p)
        if sold:
            msg += "\n⚠️ " + (f"له {sold:g} حركة بيع — فواتير القديم هتفضل محفوظة"
                              if LANG == "ar" else "has sales history")
        if not admin_password_check(s): return
        if QMessageBox.question(s, APP, msg) != QMessageBox.Yes: return
        trash_put("products", p["id"])
        x("DELETE FROM stock WHERE product_id=?", (p["id"],))
        x("DELETE FROM products WHERE id=?", (p["id"],))
        log("product_del", f"pid={p['id']}")
        s.load_stock(); s.load_cats(); s._fill_cat_filter()
        if hasattr(s, "mw"): s.mw.broadcast_all()
    def stocktake(s):
        """📋 نافذة جرد — فلتر داخلي + قيمة تسوية لحظية"""
        locs = q("SELECT * FROM locations ORDER BY CASE WHEN type='warehouse' "
                 "THEN 0 ELSE 1 END, id")
        d = QDialog(s); d.setWindowTitle("📋 " + T("Stocktake"))
        d.resize(1000, 680); v = QVBoxLayout(d)
        fr = QHBoxLayout()
        fr.addWidget(QLabel("🏬 " + T("Location") + ":"))
        flt = QComboBox(); flt.setMinimumHeight(40)
        flt.addItem("🌐 " + T("All Locations"), None)
        for l in locs:
            flt.addItem(("🏭 " if l["type"] == "warehouse" else "🏬 ")
                        + l["name"], l["id"])
        flt.setMinimumWidth(220)
        fr.addWidget(flt); fr.addStretch(1)
        hint = QLabel("✏️ " + ("اكتب الفعلي — الفرق والقيمة يتحدثوا تلقائيًا"
                               if LANG == "ar" else "Type counted — live diff"))
        hint.setStyleSheet("color:#64748b;"); fr.addWidget(hint)
        v.addLayout(fr)
        t = QTableWidget(0, 6)
        t.setHorizontalHeaderLabels([T("Product Name"), T("Code"),
            T("Ledger qty"), T("Counted"), T("Diff"), T("Expiry")])
        t.verticalHeader().setDefaultSectionSize(46)
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for col, wdt in ((1, 110), (2, 110), (3, 110), (4, 110), (5, 130)):
            hh.setSectionResizeMode(col, QHeaderView.Fixed)
            t.setColumnWidth(col, wdt)
        t.setAlternatingRowColors(True)
        v.addWidget(t, 1)
        bar = QFrame(); bar.setObjectName("card")
        bb = QHBoxLayout(bar)
        cnt_lbl = QLabel("📊 " + T("Counted items") + ": 0")
        cnt_lbl.setStyleSheet("font-weight:700;")
        val_lbl = QLabel("💰 " + T("Settle value") + ": 0.00 " + cur())
        val_lbl.setStyleSheet("font-weight:800;font-size:16px;")
        bb.addWidget(cnt_lbl); bb.addStretch(1); bb.addWidget(val_lbl)
        v.addWidget(bar)
        hb2 = QHBoxLayout()
        ok = QPushButton("💾 " + T("Apply & Settle"))
        ok.setObjectName("success"); ok.setMinimumHeight(46)
        ca = QPushButton(T("Cancel")); ca.setMinimumHeight(42)
        hb2.addWidget(ok); hb2.addWidget(ca); hb2.addStretch(1)
        v.addLayout(hb2)
        state = {"lid": None, "rows": [], "spins": {}, "exps": {}}
        def fill():
            lid = flt.currentData()
            state["lid"] = lid
            sk = {}
            for r in q("SELECT product_id, location_id, qty FROM stock"):
                sk[(r["product_id"], r["location_id"])] = r["qty"]
            prods = q("SELECT * FROM products WHERE active=1 ORDER BY name")
            rows = []
            for p in prods:
                if lid is None:
                    tot = sum(sk.get((p["id"], l["id"]), 0) for l in locs)
                    rows.append((p, tot))
                else:
                    rows.append((p, sk.get((p["id"], lid), 0)))
            state["rows"] = rows
            state["spins"] = {}; state["exps"] = {}
            t.setRowCount(len(rows))
            for i, (p, book) in enumerate(rows):
                t.setItem(i, 0, QTableWidgetItem(disp_name(p)))
                t.setItem(i, 1, QTableWidgetItem(p["barcode"] or ""))
                bi = QTableWidgetItem(f"{book:g}")
                bi.setTextAlignment(Qt.AlignCenter); t.setItem(i, 2, bi)
                sp = QDoubleSpinBox(); sp.setMaximum(10**7)
                sp.setMinimumHeight(36); sp.setAlignment(Qt.AlignCenter)
                sp.setSpecialValueText(" ")
                t.setCellWidget(i, 3, sp); state["spins"][i] = sp
                di = QTableWidgetItem("—")
                di.setTextAlignment(Qt.AlignCenter); t.setItem(i, 4, di)
                ew = QDateEdit(); ew.setCalendarPopup(True)
                ew.setMinimumHeight(36); ew.setSpecialValueText("—")
                ew.setMinimumDate(QDate(2000, 1, 1))
                if p.get("expiry"):
                    try:
                        ew.setDate(QDate.fromString(p["expiry"], "yyyy-MM-dd"))
                    except Exception: pass
                else:
                    ew.setDate(QDate(2000, 1, 1))
                t.setCellWidget(i, 5, ew); state["exps"][i] = ew
            for i, sp in state["spins"].items():
                sp.valueChanged.connect(calc)
        def calc(*_):
            n = 0; val = 0.0
            for i, (p, book) in enumerate(state["rows"]):
                w = state["spins"].get(i)
                if w is None or w.text().strip() == "":
                    di = t.item(i, 4)
                    if di: di.setText("—")
                    continue
                df = round(w.value() - book, 2)
                di = t.item(i, 4)
                if di:
                    di.setText(("🟢 +" if df > 0 else "🔴 " if df < 0
                                else "✅ ") + f"{df:g}")
                    di.setForeground(QBrush(QColor(
                        "#10b981" if df > 0
                        else "#ef4444" if df < 0 else "#10b981")))
                n += 1; val += p["cost"] * df
            cnt_lbl.setText("📊 " + T("Counted items") + f": {n:g}")
            val_lbl.setText("💰 " + T("Settle value") + ": "
                            + ("−" if val < 0 else "+")
                            + money(abs(val)) + " " + cur())
        def settle():
            lid = state["lid"]
            diffs = []
            for i, (p, book) in enumerate(state["rows"]):
                w = state["spins"].get(i)
                if w is None or w.text().strip() == "": continue
                df = round(w.value() - book, 2)
                if abs(df) > 0.0001: diffs.append((i, p, df))
            if not diffs:
                QMessageBox.information(d, APP, "📋 " + T("Nothing to settle"))
                return
            total_val = sum(p["cost"] * df_ for _, p, df_ in diffs)
            neg = sum(1 for _, _, df_ in diffs if df_ < 0)
            where = next((l["name"] for l in locs if l["id"] == lid),
                         T("All"))
            if lid is None:
                QMessageBox.warning(d, APP, "🏬 " +
                    ("اختر المخزن أو المحل للاعتماد — الجرد بيتم في مكان محدد"
                     if LANG == "ar" else "Pick a location to settle"))
                return
            msg = ("📋 نتيجة الجرد — " + where + "\n\n" if LANG == "ar"
                   else "Result — " + where + "\n\n")
            msg += (f"الأصناف المعدّلة: {len(diffs):g}\n"
                    f"عجز: {neg:g} | زيادة: {len(diffs)-neg:g}\n"
                    "💰 " + T("Settle value") + ": "
                    + ("−" if total_val < 0 else "+")
                    + money(abs(total_val)) + " " + cur() + "\n\n"
                    + ("تأكيد اعتماد التسوية؟" if LANG == "ar" else "Apply?"))
            if QMessageBox.question(d, APP, msg) != QMessageBox.Yes: return
            ref = "ST-" + str(int(dt.datetime.now().timestamp() * 1000) % 10**8)
            for i, p, df_ in diffs:
                move_stock(p["id"], lid, df_, "stocktake", ref)
                ew = state["exps"].get(i)
                if ew and ew.date() > QDate(2000, 1, 1):
                    x("UPDATE products SET expiry=? WHERE id=?",
                      (ew.date().toString("yyyy-MM-dd"), p["id"]))
            log("stocktake", f"ref={ref} items={len(diffs):g} "
                             f"val={total_val:.2f}")
            s.load_stock(); s.load_moves()
            try: s.mw.broadcast_all()
            except Exception: pass
            QMessageBox.information(d, APP, "✅ " + ref + "\n💰 "
                                    + T("Settle value") + ": "
                                    + ("−" if total_val < 0 else "+")
                                    + money(abs(total_val)) + " " + cur())
            fill()
        ok.clicked.connect(settle)
        flt.currentIndexChanged.connect(lambda *_: fill())
        fill()
        d.exec()
    def adjust(s):
        d = QDialog(s); d.setWindowTitle("⚖️ " + T("Adjust Stock"))
        d.setMinimumWidth(520)
        f = QFormLayout(d); f.setSpacing(12)
        pc = QComboBox()
        for p in q("SELECT * FROM products WHERE active=1 ORDER BY name"):
            pc.addItem(disp_name(p), p["id"])
        editable_combo(pc)
        lc = QComboBox()
        for l in q("SELECT * FROM locations"): lc.addItem(l["name"], l["id"])
        editable_combo(lc)
        curv = QLabel("—"); new = QDoubleSpinBox(); new.setMaximum(10**7)
        new.setMinimumHeight(38); new.setAlignment(Qt.AlignCenter)
        rs = QLineEdit(); rs.setPlaceholderText(T("Reason"))
        rs.setMinimumHeight(38)
        def upd():
            r = q1("SELECT qty FROM stock WHERE product_id=? AND location_id=?",
                   (pc.currentData(), lc.currentData()))
            curv.setText(f"{r['qty']:g}" if r else "0")
        pc.currentIndexChanged.connect(upd)
        lc.currentIndexChanged.connect(upd); upd()
        ok = QPushButton("✅ " + T("Save")); ok.setObjectName("warn")
        ok.setMinimumHeight(42)
        f.addRow(T("Product"), pc); f.addRow(T("Location"), lc)
        f.addRow(T("Stock:"), curv); f.addRow(T("New Qty"), new)
        f.addRow(T("Reason"), rs); f.addRow(ok)
        def do():
            pid, lid = pc.currentData(), lc.currentData()
            if pid is None or lid is None: return
            r = q1("SELECT qty FROM stock WHERE product_id=? AND location_id=?",
                   (pid, lid))
            old = r["qty"] if r else 0
            move_stock(pid, lid, new.value() - old,
                       "adjust:" + (rs.text() or "-"))
            log("stock_adjust", f"pid={pid} {old}→{new.value():g}")
            s.load_stock(); s.load_moves()
            if hasattr(s, "mw"): s.mw.broadcast_all()
            d.accept()
        ok.clicked.connect(do); d.exec()
    def labels(s):
        rows = s._rows_now(); r = s.stbl.currentRow()
        if not (0 <= r < len(rows)):
            QMessageBox.information(s, APP, T("Nothing selected")); return
        p = rows[r][0]
        n = QSpinBox(); n.setRange(1, 100); n.setValue(12); n.setMinimumHeight(38)
        d = QDialog(s); f = QFormLayout(d); f.addRow(T("Copies"), n)
        ok = QPushButton("🖨 " + T("Print")); ok.setObjectName("primary")
        ok.setMinimumHeight(42); f.addRow(ok)
        def do():
            imgs = {"bar": code39_pixmap(p["barcode"]).toImage()}
            cell = ("<td width='33%' align=center style='border:1px dashed #999;"
                    "padding:6px;'>"
                    "<div style='font-size:11px;font-weight:700;'>"
                    + disp_name(p) + "</div>"
                    "<div style='font-size:13px;font-weight:800;'>"
                    + money(p["price"]) + " " + cur() + "</div>"
                    "<img src='bar' width='150' height='42'>"
                    "<div style='font-size:10px;'>" + str(p["barcode"])
                    + "</div></td>")
            html = "<table width=100% cellpadding=2>"; k = 0
            for i in range(n.value()):
                if k % 3 == 0: html += "<tr>"
                html += cell; k += 1
                if k % 3 == 0: html += "</tr>"
            if k % 3: html += "</tr>"
            do_print(html + "</table>", imgs, a4=True, parent=s); d.accept()
        ok.clicked.connect(do); d.exec()
    def import_csv(s):
        path, _ = QFileDialog.getOpenFileName(s, T("Import CSV"), "",
                                              "CSV (*.csv)")
        if not path: return
        n = 0
        try:
            with open(path, encoding="utf-8-sig") as fh:
                for row in csv.DictReader(fh):
                    bc = (row.get("barcode") or row.get("Code") or "").strip()
                    if not bc: continue
                    nm = row.get("name") or row.get("Product Name") or bc
                    nar = row.get("name_ar") or ""
                    cost = float(row.get("cost") or 0)
                    price = float(row.get("price") or 0)
                    mn = float(row.get("min_stock") or 5)
                    ex = q1("SELECT id FROM products WHERE barcode=?", (bc,))
                    if ex:
                        x("UPDATE products SET name=?,name_ar=?,cost=?,price=?,"
                          "min_stock=? WHERE id=?",
                          (nm, nar, cost, price, mn, ex["id"]))
                    else:
                        x("INSERT INTO products(barcode,name,name_ar,cost,"
                          "price,min_stock) VALUES(?,?,?,?,?,?)",
                          (bc, nm, nar, cost, price, mn))
                    n += 1
        except Exception as e:
            QMessageBox.critical(s, APP, str(e)); return
        s.ensure_rows(); log("import_csv", f"{n} products")
        s.load_stock(); s._fill_cat_filter()
        QMessageBox.information(s, APP, f"{T('Imported')}: {n}")
    def load_moves(s):
        rows = q("""SELECT m.*, p.name pname, p.name_ar par, l.name lname
                 FROM stock_moves m LEFT JOIN products p ON p.id=m.product_id
                 LEFT JOIN locations l ON l.id=m.location_id
                 ORDER BY m.id DESC LIMIT 500""")
        s.mtbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            nm = ((r["par"] or r["pname"] or "—") if LANG == "ar"
                  else (r["pname"] or "—"))
            vals = [r["ts"], nm, r["lname"] or "—", f"{r['qty']:g}",
                    r["reason"] or "", r["ref"] or "", r["username"] or ""]
            for j, val in enumerate(vals):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignCenter)
                if j == 3:
                    it.setForeground(QBrush(QColor(
                        "#10b981" if r["qty"] > 0 else "#ef4444")))
                s.mtbl.setItem(i, j, it)
        wire_search(s.mq, s.mtbl)
    def load_cats(s):
        rows = q("""SELECT c.id, c.name, COUNT(p.id) n,
                    IFNULL(SUM((SELECT IFNULL(SUM(qty),0) FROM stock st
                                WHERE st.product_id=p.id) * p.cost),0) v
                    FROM categories c LEFT JOIN products p
                    ON p.category_id=c.id AND p.active=1
                    GROUP BY c.id ORDER BY c.name""")
        s.cids = [r["id"] for r in rows]
        s.ctbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, val in enumerate([r["name"], f"{r['n']:g}", money(r["v"])]):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignCenter)
                if getattr(s, "_cur_cat", None) == r["id"]:
                    it.setForeground(QBrush(QColor("#2563eb")))
                s.ctbl.setItem(i, j, it)
        s._cur_cat = getattr(s, "_cur_cat", None)
        if s._cur_cat in s.cids:
            s.ctbl.selectRow(s.cids.index(s._cur_cat))
        else:
            s._cur_cat = None
            s.ptbl.setRowCount(0); s.cat_lbl.setText("—")
    def _cat_clicked(s, it=None, _col=None):
        r_ = s.ctbl.currentRow()
        if not (0 <= r_ < len(s.cids)): return
        s._cur_cat = s.cids[r_]
        s.load_cats()
        cn = q1("SELECT name FROM categories WHERE id=?", (s._cur_cat,))
        prods = q("SELECT * FROM products WHERE active=1 AND category_id=? "
                  "ORDER BY name", (s._cur_cat,))
        sk = {}
        for r in q("SELECT product_id, SUM(qty) qt FROM stock GROUP BY product_id"):
            sk[r["product_id"]] = r["qt"]
        s.cat_lbl.setText("🗂 " + (cn["name"] if cn else "")
                          + f"  ({len(prods):g})")
        s.ptbl.setRowCount(len(prods))
        for i, p in enumerate(prods):
            tot = sk.get(p["id"], 0)
            for j, val in enumerate([disp_name(p), p["barcode"],
                    money(p["price"]), money(p["cost"]), f"{tot:g}",
                    p["expiry"] or "—"]):
                c2 = QTableWidgetItem(str(val))
                c2.setTextAlignment(Qt.AlignCenter)
                if j == 4:
                    c2.setForeground(QBrush(QColor(
                        "#ef4444" if tot <= 0 else "#10b981")))
                s.ptbl.setItem(i, j, c2)
        wire_search(s.pq, s.ptbl)
    def export_cat(s):
        rows = []
        for i in range(s.ptbl.rowCount()):
            rows.append([s.ptbl.item(i, j).text() if s.ptbl.item(i, j) else ""
                         for j in range(s.ptbl.columnCount())])
        export_csv([T("Product Name"), T("Code"), T("Price"), T("Cost"),
                    T("Total"), T("Expiry")], rows)
        # ============================== PURCHASES ====================================
class PurchasesPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        top = QHBoxLayout()
        nb = QPushButton("🚚 " + T("New Purchase")); nb.setObjectName("primary")
        nb.clicked.connect(s.new_purchase); top.addWidget(nb)
        s.q = make_search(); top.addWidget(s.q)
        top.addStretch(1); v.addLayout(top)
        s.tbl = QTableWidget(0, 7)
        s.tbl.setHorizontalHeaderLabels([T("Ref No"), T("Date"), T("Supplier"),
            T("Total Cost"), T("Paid"), T("Balance"), T("Status")])
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v.addWidget(s.tbl, 1); s.ids = []
        bot = QHBoxLayout()
        pb = QPushButton("💵 " + T("Pay Supplier")); pb.setObjectName("success")
        pb.clicked.connect(s.pay_supp); bot.addWidget(pb)
        lb = QPushButton("📖 " + T("Ledger")); lb.setObjectName("primary")
        lb.clicked.connect(s.ledger); bot.addWidget(lb)
        spp = QPushButton("🏷 " + T("Last purchase prices"))
        spp.clicked.connect(s.sup_prices); bot.addWidget(spp)
        db = QPushButton("🗑 " + T("Delete")); db.setObjectName("danger")
        db.clicked.connect(s.del_purchase); bot.addWidget(db)
        bot.addStretch(1); v.addLayout(bot)
        s.refresh()
    def refresh(s):
        rows = q("SELECT p.*, sp.name sname FROM purchases p LEFT JOIN suppliers sp "
                 "ON sp.id=p.supplier_id ORDER BY p.id DESC")
        s.tbl.setRowCount(len(rows)); s.ids = [r["id"] for r in rows]
        for i, r in enumerate(rows):
            bal = (r["total"] or 0) - (r["paid"] or 0)
            vals = [r["ref_no"], r["ts"], r["sname"] or "—", money(r["total"]),
                    money(r["paid"]), money(bal), T(r["status"])]
            for j, val in enumerate(vals):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignCenter)
                if j == 5 and bal > 0:
                    it.setForeground(QBrush(QColor("#ef4444")))
                s.tbl.setItem(i, j, it)
        wire_search(s.q, s.tbl)
    def del_purchase(s):
        admin_delete(s, s.tbl, s.ids, "purchases", after=s.refresh)
    def new_purchase(s):
        if not q1("SELECT id FROM suppliers LIMIT 1"):
            QMessageBox.warning(s, APP, "🏭 أضف مورًد أولًا من شاشة الموردين")
            return
        d = QDialog(s); d.setWindowTitle("🚚 " + T("New Purchase"))
        d.resize(900, 660); v = QVBoxLayout(d)
        g = QFormLayout(); g.setSpacing(10)
        sup = QComboBox()
        for sp in q("SELECT * FROM suppliers ORDER BY id"):
            sup.addItem("🏭 " + sp["name"], sp["id"])
        editable_combo(sup); sup.setMinimumHeight(38)
        sb = QPushButton("➕"); sb.setMinimumHeight(38); sb.setFixedWidth(44)
        def quick_supplier():
            nm, okk = QInputDialog.getText(d, "🏭 " + T("Supplier"),
                ("اسم المورد الجديد:" if LANG == "ar" else "New supplier:"))
            if okk and nm.strip():
                if q1("SELECT id FROM suppliers WHERE name=?", (nm.strip(),)):
                    QMessageBox.information(d, APP, "⚠️"); return
                sidx = x("INSERT INTO suppliers(name) VALUES(?)", (nm.strip(),))
                sup.addItem("🏭 " + nm.strip(), sidx)
                sup.setCurrentIndex(sup.findData(sidx))
                log("supplier_new", nm.strip())
        sb.clicked.connect(quick_supplier)
        srow = QHBoxLayout(); srow.addWidget(sup, 1); srow.addWidget(sb)
        loc = QComboBox()
        for l in q("SELECT * FROM locations ORDER BY CASE WHEN type='warehouse' "
                   "THEN 0 ELSE 1 END, id"):
            loc.addItem(("🏭 " if l["type"] == "warehouse" else "🏬 ")
                        + l["name"], l["id"])
        editable_combo(loc); loc.setMinimumHeight(38)
        g.addRow(T("Supplier"), srow); g.addRow(T("Location"), loc)
        v.addLayout(g)
        t = QTableWidget(0, 7)
        t.setHorizontalHeaderLabels([T("Product"), "📷 " + T("Code"),
                                     T("Qty"), T("Cost"), T("Total"),
                                     "📅 " + T("Expiry"), "🗂 " + T("Category")])
        t.verticalHeader().setDefaultSectionSize(52)
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for col, wdt in ((1, 150), (2, 80), (3, 120), (4, 120), (5, 140), (6, 120)):
            hh.setSectionResizeMode(col, QHeaderView.Fixed)
            t.setColumnWidth(col, wdt)
        prods = q("SELECT * FROM products WHERE active=1 ORDER BY name")
        def mkrow():
            r = t.rowCount(); t.insertRow(r)
            c = QComboBox()
            for p in prods: c.addItem(disp_name(p), p["id"])
            editable_combo(c); c.setMinimumHeight(40); c.setMinimumWidth(200)
            c.view().setMinimumWidth(440)
            c.setCurrentIndex(-1)
            bc = QLineEdit(); bc.setPlaceholderText("📷 " + T("Code"))
            bc.setMinimumHeight(40)
            qs = QDoubleSpinBox(); qs.setMaximum(10**6); qs.setMinimumHeight(40)
            qs.setAlignment(Qt.AlignCenter)
            cs = QDoubleSpinBox(); cs.setMaximum(10**7); cs.setDecimals(2)
            cs.setMinimumHeight(40); cs.setAlignment(Qt.AlignCenter)
            lab = QLabel("0.00"); lab.setAlignment(Qt.AlignCenter)
            lab.setStyleSheet("font-weight:800;font-size:14px;")
            clab = QLabel("—"); clab.setAlignment(Qt.AlignCenter)
            def sel(pid):
                if c.findData(pid) < 0:
                    pr = q1("SELECT * FROM products WHERE id=?", (pid,))
                    if pr: c.addItem(disp_name(pr), pid)
                ix = c.findData(pid)
                if ix >= 0: c.setCurrentIndex(ix)
                row = q1("SELECT c2.name FROM categories c2 "
                         "JOIN products p2 ON p2.category_id=c2.id "
                         "WHERE p2.id=?", (pid,))
                clab.setText(("🗂 " + row["name"]) if row else "—")
            def on_scan():
                v_ = bc.text().strip()
                if not v_: return
                p = q1("SELECT * FROM products WHERE barcode=?", (v_,))
                if p:
                    sel(p["id"])
                elif QMessageBox.question(d, APP, "❓ '" + v_ + "' " + (
                        "غير موجود — إضافة كمنتج جديد؟"
                        if LANG == "ar" else "not found. Add as new product?")
                        ) == QMessageBox.Yes:
                    res = product_create_dialog(d, v_)
                    if res:
                        sel(res["pid"])
                        qs.setValue(res["qty"])
                        cs.setValue(res["cost"])
                        if res.get("cat"): clab.setText("🗂 " + res["cat"])
                        bc.clear()
            def on_type(tx):
                p = q1("SELECT * FROM products WHERE barcode=?", (tx.strip(),))
                if p: sel(p["id"])
            bc.returnPressed.connect(on_scan)
            bc.textChanged.connect(on_type)
            upd = lambda *_: lab.setText(money(qs.value() * cs.value()))
            qs.valueChanged.connect(upd); cs.valueChanged.connect(upd)
            t.setCellWidget(r, 0, c); t.setCellWidget(r, 1, bc)
            t.setCellWidget(r, 2, qs); t.setCellWidget(r, 3, cs)
            t.setCellWidget(r, 4, lab); t.setCellWidget(r, 6, clab)
        def add_new():
            res = product_create_dialog(d)
            if res:
                mkrow()
                r = t.rowCount() - 1
                c = t.cellWidget(r, 0)
                if c.findData(res["pid"]) < 0:
                    pr = q1("SELECT * FROM products WHERE id=?", (res["pid"],))
                    if pr: c.addItem(disp_name(pr), res["pid"])
                ix = c.findData(res["pid"])
                if ix >= 0: c.setCurrentIndex(ix)
                t.cellWidget(r, 2).setValue(res["qty"])
                t.cellWidget(r, 3).setValue(res["cost"])
                if res.get("cat"):
                    t.cellWidget(r, 6).setText("🗂 " + res["cat"])
        mkrow(); v.addWidget(t, 1)
        ar = QHBoxLayout()
        ab = QPushButton("➕ " + T("Add")); ab.setObjectName("primary")
        ab.setMinimumHeight(40); ab.clicked.connect(mkrow); ar.addWidget(ab)
        nb2 = QPushButton("🆕 " + T("Product")); nb2.setObjectName("warn")
        nb2.setMinimumHeight(40); nb2.clicked.connect(add_new); ar.addWidget(nb2)
        rb = QPushButton("➖"); rb.setMinimumHeight(40)
        def delrow():
            r_ = t.currentRow() if t.currentRow() >= 0 else t.rowCount() - 1
            if r_ >= 0 and t.rowCount() > 1: t.removeRow(r_)
        rb.clicked.connect(delrow); ar.addWidget(rb); ar.addStretch(1)
        ttl = QLabel(T("Total Cost") + ": 0.00 " + cur())
        ttl.setObjectName("big"); ar.addWidget(ttl); v.addLayout(ar)
        paid = QDoubleSpinBox(); paid.setMaximum(10**7)
        paid.setMinimumHeight(38); paid.setAlignment(Qt.AlignCenter)
        pacc = QComboBox(); pacc.setMinimumHeight(38)
        pacc.addItem("🧰 " + T("Drawer"), "drawer")
        pacc.addItem("🏦 " + T("Vault"), "vault")
        fr2 = QHBoxLayout()
        fr2.addWidget(QLabel(T("Paid") + " 💵")); fr2.addWidget(paid)
        fr2.addWidget(pacc); v.addLayout(fr2)
        ok = QPushButton("💾 " + T("Save")); ok.setObjectName("success")
        ok.setMinimumHeight(46); v.addWidget(ok)
        def recalc():
            tt = sum(t.cellWidget(r, 2).value() * t.cellWidget(r, 3).value()
                     for r in range(t.rowCount()))
            ttl.setText(T("Total Cost") + ": " + money(tt) + " " + cur())
        tm = QTimer(d); tm.timeout.connect(recalc); tm.start(400)
        def do():
            if sup.currentData() is None and sup.currentText().strip():
                nmv = sup.currentText().strip()
                if QMessageBox.question(d, APP, "🏭 '" + nmv + "' " + (
                        "غير موجود — إضافته كمورد جديد؟"
                        if LANG == "ar" else "Add as new supplier?")
                        ) == QMessageBox.Yes:
                    sidx = x("INSERT INTO suppliers(name) VALUES(?)", (nmv,))
                    sup.addItem("🏭 " + nmv, sidx)
                    sup.setCurrentIndex(sup.findData(sidx))
                    log("supplier_new", nmv)
            if sup.currentData() is None:
                QMessageBox.warning(d, APP, "🏭 اختر مورًد"); return
            if loc.currentData() is None:
                QMessageBox.warning(d, APP, "🏬 اختر المخزن"); return
            rws = []
            for r in range(t.rowCount()):
                pid_ = t.cellWidget(r, 0).currentData()
                qt = t.cellWidget(r, 2).value()
                cs = t.cellWidget(r, 3).value()
                if pid_ and qt > 0: rws.append((pid_, qt, cs))
            if not rws:
                QMessageBox.warning(d, APP, "⚠️ " + (
                    "مفيش أصناف — اضرب باركود واضغط Enter أو استخدم 🆕 صنف جديد"
                    if LANG == "ar" else "No items.")); return
            if paid.value() > 0:
                _acc = pacc.currentData()
                b_ = q1("SELECT IFNULL(SUM(CASE WHEN direction='in' THEN amount "
                        "ELSE -amount END),0) v FROM treasury WHERE account=?",
                        (_acc,))["v"]
                if paid.value() > b_ + 0.001:
                    QMessageBox.warning(d, APP, ("🧰 " if _acc == "drawer"
                        else "🏦 ") + T("Insufficient payment!")); return
            no = inv_no("PO"); tot = 0.0
            pidx = x("INSERT INTO purchases(ref_no,ts,supplier_id,location_id,"
                     "username,total,paid,status) VALUES(?,?,?,?,?,0,0,'unpaid')",
                     (no, nows(), sup.currentData(), loc.currentData(),
                      CUR_USER["username"]))
            try:
                for p_, qt, cs in rws:
                    tot += qt * cs
                    pr = q1("SELECT * FROM products WHERE id=?", (p_,))
                    x("INSERT INTO purchase_items(purchase_id,product_id,name,"
                      "qty,cost,total) VALUES(?,?,?,?,?,?)",
                      (pidx, p_, disp_name(pr), qt, cs, qt * cs))
                    x("UPDATE products SET cost=? WHERE id=?", (cs, p_))
                    x("INSERT INTO supplier_prices(ts,supplier_id,product_id,"
                      "cost) VALUES(?,?,?,?)",
                      (nows(), sup.currentData(), p_, cs))
                    move_stock(p_, loc.currentData(), qt, "purchase", no)
                paidv = min(paid.value(), tot)
                stt = ("paid" if paidv >= tot - 0.001
                       else "partial" if paidv > 0 else "unpaid")
                x("UPDATE purchases SET total=?,paid=?,status=? WHERE id=?",
                  (tot, paidv, stt, pidx))
                x("UPDATE suppliers SET balance=balance+? WHERE id=?",
                  (tot - paidv, sup.currentData()))
                if paidv > 0:
                    x("INSERT INTO payments(ts,party_type,party_id,amount,"
                      "direction,method,username) VALUES(?,?,?,?,?,?,?)",
                      (nows(), "supplier", sup.currentData(), paidv, "out",
                       "cash", CUR_USER["username"]))
                    x("INSERT INTO treasury(ts,account,direction,amount,reason,"
                      "ref,username) VALUES(?,?,?,?,?,?,?)",
                      (nows(), pacc.currentData(), "out", paidv,
                       "شراء بضاعة " + no, no, CUR_USER["username"]))
                log("purchase", f"{no} total={tot}")
            except Exception as e:
                conn.rollback()
                QMessageBox.critical(d, APP, "❌ " + str(e)); return
            QMessageBox.information(d, APP, "✅ " + no + " — " + money(tot)
                                    + " " + cur())
            s.refresh(); s.mw.broadcast_all(); d.accept()
        ok.clicked.connect(do); d.exec()
    def pay_supp(s):
        c = QComboBox()
        for sp in q("SELECT * FROM suppliers"):
            c.addItem(f"{sp['name']} — {money(sp['balance'])}", sp["id"])
        editable_combo(c)
        amt = QDoubleSpinBox(); amt.setMaximum(10**7); amt.setMinimumHeight(38)
        amt.setAlignment(Qt.AlignCenter)
        acc = QComboBox(); acc.setMinimumHeight(38)
        acc.addItem("🧰 " + T("Drawer"), "drawer")
        acc.addItem("🏦 " + T("Vault"), "vault")
        d = QDialog(s); f = QFormLayout(d); f.setSpacing(12)
        f.addRow(T("Supplier"), c); f.addRow(T("Amount"), amt)
        f.addRow(T("Account"), acc)
        ok = QPushButton("💾 " + T("Save")); ok.setObjectName("success")
        ok.setMinimumHeight(42); f.addRow(ok)
        def do():
            a_ = amt.value()
            if a_ <= 0 or c.currentData() is None: return
            b_ = q1("SELECT IFNULL(SUM(CASE WHEN direction='in' THEN amount "
                    "ELSE -amount END),0) v FROM treasury WHERE account=?",
                    (acc.currentData(),))["v"]
            if a_ > b_ + 0.001:
                QMessageBox.warning(s, APP, T("Insufficient payment!")); return
            x("INSERT INTO payments(ts,party_type,party_id,amount,direction,"
              "method,username) VALUES(?,?,?,?,?,?,?)",
              (nows(), "supplier", c.currentData(), a_, "out", "cash",
               CUR_USER["username"]))
            x("INSERT INTO treasury(ts,account,direction,amount,reason,ref,"
              "username) VALUES(?,?,?,?,?,?,?)",
              (nows(), acc.currentData(), "out", a_, "دفع للمورد",
               "PAY-SUP", CUR_USER["username"]))
            x("UPDATE suppliers SET balance=balance-? WHERE id=?",
              (a_, c.currentData()))
            log("supplier_payment", str(a_))
            QMessageBox.information(s, APP, T("Payment saved"))
            s.refresh()
            try: s.mw.broadcast_all()
            except Exception: pass
            d.accept()
        ok.clicked.connect(do); d.exec()
    def ledger(s):
        c = QComboBox()
        for sp in q("SELECT * FROM suppliers ORDER BY name"):
            c.addItem(sp["name"], sp["id"])
        editable_combo(c)
        d0 = QDialog(s); d0.setWindowTitle("📖 " + T("Ledger"))
        d0.setMinimumWidth(480); f = QFormLayout(d0)
        f.addRow(T("Supplier"), c)
        ok = QPushButton("📖 " + T("Ledger")); ok.setMinimumHeight(40)
        f.addRow(ok)
        def go():
            sid = c.currentData()
            if sid is None: return
            sp = q1("SELECT * FROM suppliers WHERE id=?", (sid,))
            pur = q("""SELECT p.*, (SELECT COUNT(*) FROM purchase_items pi
                       WHERE pi.purchase_id=p.id) n FROM purchases p
                       WHERE supplier_id=? AND total>0 ORDER BY p.id DESC""", (sid,))
            pays = q("SELECT * FROM payments WHERE party_type='supplier' AND "
                     "party_id=? ORDER BY ts DESC", (sid,))
            bal = q1("SELECT IFNULL(SUM(total-paid),0) v FROM purchases "
                     "WHERE supplier_id=?", (sid,))["v"]
            d = QDialog(s); d.setWindowTitle("📖 " + sp["name"])
            d.resize(720, 560); v = QVBoxLayout(d)
            head = QLabel(f"🏭 {sp['name']}   |   💰 {T('Balance')}: "
                          f"{money(bal)} {cur()}")
            head.setStyleSheet("font-weight:800;font-size:16px;color:#b91c1c;"
                               "background:rgba(239,68,68,.08);padding:10px;"
                               "border-radius:10px;")
            v.addWidget(head)
            v.addWidget(QLabel("🚚 " + T("Purchases")))
            t = QTableWidget(len(pur), 6)
            t.setHorizontalHeaderLabels([T("Ref No"), T("Date"), T("Items"),
                T("Total Cost"), T("Paid"), T("Status")])
            t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            t.verticalHeader().setVisible(False)
            t.setEditTriggers(QTableWidget.NoEditTriggers)
            for i, p in enumerate(pur):
                for j, val in enumerate([p["ref_no"], p["ts"], f"{p['n']:g}",
                        money(p["total"]), money(p["paid"]), T(p["status"])]):
                    it = QTableWidgetItem(str(val))
                    it.setTextAlignment(Qt.AlignCenter); t.setItem(i, j, it)
            v.addWidget(t, 2)
            v.addWidget(QLabel("💵 " + T("Payment")))
            t2 = QTableWidget(len(pays), 2)
            t2.setHorizontalHeaderLabels([T("Date"), T("Amount")])
            t2.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            t2.verticalHeader().setVisible(False)
            t2.setEditTriggers(QTableWidget.NoEditTriggers)
            t2.setMaximumHeight(180)
            for i, p in enumerate(pays):
                t2.setItem(i, 0, QTableWidgetItem(p["ts"]))
                t2.setItem(i, 1, QTableWidgetItem(money(p["amount"])))
            v.addWidget(t2, 1)
            hb = QHBoxLayout()
            pr = QPushButton("🖨 " + T("Print")); pr.setObjectName("primary")
            def dop():
                html = (f"<h2>📖 {T('Ledger')} — {sp['name']}</h2>"
                        f"<p>{T('Balance')}: <b>{money(bal)} {cur()}</b></p>"
                        "<table width=100% cellpadding=6 border=1>")
                for p in pur:
                    html += (f"<tr><td>{p['ref_no']}</td><td>{p['ts']}</td>"
                             f"<td align=center>{p['n']:g}</td>"
                             f"<td align=right>{money(p['total'])}</td>"
                             f"<td align=right>{money(p['paid'])}</td>"
                             f"<td>{T(p['status'])}</td></tr>")
                do_print(html + "</table>", a4=True, parent=s)
            pr.clicked.connect(dop)
            cl = QPushButton(T("Close")); cl.clicked.connect(d.accept)
            hb.addWidget(pr); hb.addWidget(cl); hb.addStretch(1); v.addLayout(hb)
            d0.accept(); d.exec()
        ok.clicked.connect(go); d0.exec()
    def sup_prices(s):
        c = QComboBox()
        for sp in q("SELECT * FROM suppliers ORDER BY name"):
            c.addItem(sp["name"], sp["id"])
        editable_combo(c)
        d0 = QDialog(s); d0.setMinimumWidth(480)
        f = QFormLayout(d0); f.addRow(T("Supplier"), c)
        ok = QPushButton("🏷 " + T("Last purchase prices"))
        ok.setMinimumHeight(40); f.addRow(ok)
        def go():
            sid = c.currentData()
            if sid is None: return
            rows = q("""SELECT p.name pname, p.name_ar par, pr.cost, pr.ts
                     FROM supplier_prices pr JOIN products p
                     ON p.id=pr.product_id WHERE pr.supplier_id=?
                     AND pr.id IN (SELECT MAX(id) FROM supplier_prices
                     WHERE supplier_id=? GROUP BY product_id)
                     ORDER BY pr.ts DESC""", (sid, sid))
            d = QDialog(s); d.setWindowTitle("🏷 " + T("Last purchase prices"))
            d.resize(680, 540); v = QVBoxLayout(d)
            t = QTableWidget(len(rows), 3)
            t.setHorizontalHeaderLabels([T("Product"), T("Cost"), T("Date")])
            t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            t.verticalHeader().setVisible(False)
            t.setEditTriggers(QTableWidget.NoEditTriggers)
            for i, r in enumerate(rows):
                nm = (r["par"] or r["pname"]) if LANG == "ar" else r["pname"]
                for j, val in enumerate([nm, money(r["cost"]), r["ts"]]):
                    it = QTableWidgetItem(str(val))
                    it.setTextAlignment(Qt.AlignCenter)
                    t.setItem(i, j, it)
            v.addWidget(t, 1)
            cl = QPushButton(T("Close")); cl.clicked.connect(d.accept)
            v.addWidget(cl)
            d0.accept(); d.exec()
        ok.clicked.connect(go); d0.exec()

# ============================== LOCATIONS ====================================
class LocationsPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        tb = QTabWidget(); v.addWidget(tb)
        type_opts = lambda: [("branch", T("Branch")), ("warehouse", T("Warehouse")),
                             ("store", T("Store"))]
        wh_opts = lambda: [(None, "—")] + \
            [(l["id"], l["name"]) for l in
             q("SELECT * FROM locations WHERE type='warehouse' ORDER BY id")]
        s.ed = TableEditor(mw, "locations",
            [("name","Location"),("type","Type"),("supply_from","Supply From")],
            [("name","Location","text",None),("type","Type","combo",type_opts),
             ("supply_from","Supply From","combo",wh_opts)],
            search_cols=["name"], module="locations", on_change=s.load)
        tb.addTab(s.ed, "🏬 " + T("Branches & Warehouses")); s.ed.refresh()
        tv = QWidget(); tvv = QVBoxLayout(tv)
        btns = QHBoxLayout()
        nb = QPushButton("🔄 " + T("New Transfer")); nb.setObjectName("primary")
        nb.clicked.connect(s.new_transfer)
        rb = QPushButton("📥 " + T("Receive")); rb.setObjectName("success")
        rb.clicked.connect(s.receive)
        cb = QPushButton("🚫 " + T("Cancel Transfer")); cb.setObjectName("warn")
        cb.clicked.connect(s.cancel_tr)
        dq = QPushButton("🗑 " + T("Delete")); dq.setObjectName("danger")
        dq.clicked.connect(s.del_tr)
        s.q = make_search()
        for w_ in (nb, rb, cb, dq): btns.addWidget(w_)
        btns.addWidget(s.q); btns.addStretch(1); tvv.addLayout(btns)
        s.tr = QTableWidget(0, 7)
        s.tr.setHorizontalHeaderLabels([T("Ref No"), T("Date"), T("From"),
            T("To"), T("Count"), T("Status"), T("Username")])
        s.tr.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tr.verticalHeader().setVisible(False)
        s.tr.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tvv.addWidget(s.tr, 1)
        tb.addTab(tv, "🔄 " + T("Transfers")); s.tr_ids = []; s.load_tr()
        st = QWidget(); sv = QVBoxLayout(st)
        lab = QLabel("📊 " + T("Stock by Location")); lab.setObjectName("h1")
        sv.addWidget(lab)
        s.st = QTableWidget(); s.st.setEditTriggers(QTableWidget.NoEditTriggers)
        s.st.verticalHeader().setVisible(False); sv.addWidget(s.st)
        tb.addTab(st, "📊 " + T("Stock by Location")); s.load()
    def _lname(s, lid):
        r = q1("SELECT name FROM locations WHERE id=?", (lid,))
        return r["name"] if r else "—"
    def load(s, *_):
        locs = q("SELECT * FROM locations")
        prods = q("SELECT * FROM products WHERE active=1 ORDER BY name")
        hdr = [T("Product Name")] + [l["name"] for l in locs]
        s.st.clear(); s.st.setColumnCount(len(hdr)); s.st.setRowCount(len(prods))
        s.st.setHorizontalHeaderLabels(hdr)
        s.st.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for i, p in enumerate(prods):
            s.st.setItem(i, 0, QTableWidgetItem(disp_name(p)))
            for j, l in enumerate(locs):
                r = q1("SELECT qty FROM stock WHERE product_id=? AND location_id=?",
                       (p["id"], l["id"]))
                it = QTableWidgetItem(f"{r['qty']:g}" if r else "0")
                it.setTextAlignment(Qt.AlignCenter)
                it.setForeground(QBrush(QColor(
                    "#ef4444" if (r and r["qty"] <= 0) else "#10b981")))
                s.st.setItem(i, j + 1, it)
    def load_tr(s):
        rows = q("""SELECT t.*,
                 (SELECT COUNT(*) FROM transfer_items ti WHERE ti.transfer_id=t.id) n
                 FROM transfers t ORDER BY t.id DESC LIMIT 300""")
        s.tr.setRowCount(len(rows)); s.tr_ids = [r["id"] for r in rows]
        ic_ = {"in-transit":"🚚 ","received":"✅ ","cancelled":"🚫 "}
        for i, r in enumerate(rows):
            vals = [r["ref_no"], r["ts"], s._lname(r["from_loc"]),
                    s._lname(r["to_loc"]), f"{r['n']:g}",
                    ic_.get(r["status"], "") + T(r["status"]),
                    r["username"] or ""]
            for j, val in enumerate(vals):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignCenter)
                if j == 5:
                    it.setForeground(QBrush(QColor(
                        "#f59e0b" if r["status"] == "in-transit"
                        else "#10b981" if r["status"] == "received"
                        else "#94a3b8")))
                s.tr.setItem(i, j, it)
        wire_search(s.q, s.tr)
    def _tr_row(s):
        r = s.tr.currentRow()
        return s.tr_ids[r] if 0 <= r < len(s.tr_ids) else None
    def new_transfer(s):
        d = QDialog(s); d.setWindowTitle("🔄 " + T("New Transfer"))
        d.setMinimumWidth(700)
        v = QVBoxLayout(d); g = QFormLayout(); g.setSpacing(10)
        a = QComboBox(); b = QComboBox()
        for l in q("SELECT * FROM locations ORDER BY id"):
            a.addItem("🏬 " + l["name"], l["id"])
            b.addItem("🏬 " + l["name"], l["id"])
        editable_combo(a); editable_combo(b)
        def auto_from(*_):
            row = q1("SELECT supply_from FROM locations WHERE id=?",
                     (b.currentData(),))
            if row and row["supply_from"]:
                ix = a.findData(row["supply_from"])
                if ix >= 0 and a.currentData() != b.currentData():
                    a.setCurrentIndex(ix)
        b.currentIndexChanged.connect(auto_from); auto_from()
        note = QLineEdit(); note.setPlaceholderText(T("Reason"))
        note.setMinimumHeight(38)
        g.addRow(T("From") + " 📤", a); g.addRow(T("To") + " 📥", b)
        g.addRow(T("Reason"), note); v.addLayout(g)
        t = QTableWidget(0, 3)
        t.setHorizontalHeaderLabels([T("Product"), T("Qty"), T("Stock:")])
        t.verticalHeader().setDefaultSectionSize(48)
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for col, wdt in ((1, 130), (2, 130)):
            hh.setSectionResizeMode(col, QHeaderView.Fixed)
            t.setColumnWidth(col, wdt)
        prods = q("SELECT * FROM products WHERE active=1 ORDER BY name")
        def addrow():
            r = t.rowCount(); t.insertRow(r)
            c = QComboBox()
            for p in prods: c.addItem(disp_name(p), p["id"])
            editable_combo(c); c.setMinimumHeight(38)
            qs = QDoubleSpinBox(); qs.setMaximum(10**6); qs.setMinimumHeight(38)
            qs.setAlignment(Qt.AlignCenter)
            lab = QLabel("—"); lab.setAlignment(Qt.AlignCenter)
            def upd(*_):
                rr = q1("SELECT qty FROM stock WHERE product_id=? AND "
                        "location_id=?", (c.currentData(), a.currentData()))
                lab.setText(f"{rr['qty']:g}" if rr else "0")
            c.currentIndexChanged.connect(upd)
            a.currentIndexChanged.connect(upd); upd()
            t.setCellWidget(r, 0, c); t.setCellWidget(r, 1, qs)
            t.setCellWidget(r, 2, lab)
        addrow(); v.addWidget(t, 1)
        ar = QHBoxLayout()
        ab = QPushButton("➕ " + T("Add")); ab.setObjectName("primary")
        ab.setMinimumHeight(40); ab.clicked.connect(addrow); ar.addWidget(ab)
        rb2 = QPushButton("➖"); rb2.setMinimumHeight(40)
        rb2.clicked.connect(lambda: t.rowCount() > 1
                            and t.removeRow(t.rowCount() - 1))
        ar.addWidget(rb2); ar.addStretch(1)
        ok = QPushButton("✅ " + T("Confirm")); ok.setObjectName("success")
        ok.setMinimumHeight(44); v.addWidget(ok)
        def do():
            fr, to = a.currentData(), b.currentData()
            if fr is None or to is None or fr == to:
                QMessageBox.warning(d, APP, "⚠️"); return
            items = []
            for r in range(t.rowCount()):
                pid = t.cellWidget(r, 0).currentData()
                qt = t.cellWidget(r, 1).value()
                if pid and qt > 0: items.append((pid, qt))
            if not items: d.reject(); return
            for pid, qt in items:
                rr = q1("SELECT qty FROM stock WHERE product_id=? AND "
                        "location_id=?", (pid, fr))
                if not rr or rr["qty"] < qt:
                    QMessageBox.warning(d, APP,
                                        "📦 " + T("Insufficient payment!"))
                    return
            ref = "TR-" + str(int(dt.datetime.now().timestamp()
                               * 1000) % 100000000)
            tid = x("INSERT INTO transfers(ref_no,ts,from_loc,to_loc,status,"
                    "username,note) VALUES(?,?,?,?,'in-transit',?,?)",
                    (ref, nows(), fr, to, CUR_USER["username"], note.text()))
            for pid, qt in items:
                x("INSERT INTO transfer_items(transfer_id,product_id,qty) "
                  "VALUES(?,?,?)", (tid, pid, qt))
                move_stock(pid, fr, -qt, "transfer-out", ref)
            log("transfer_new", ref)
            s.load_tr(); s.load(); d.accept()
        ok.clicked.connect(do); d.exec()
    def receive(s):
        tid = s._tr_row()
        if tid is None:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        tr = q1("SELECT * FROM transfers WHERE id=?", (tid,))
        if tr["status"] != "in-transit":
            QMessageBox.information(s, APP,
                                    T("Status") + ": " + T(tr["status"]))
            return
        for it in q("SELECT * FROM transfer_items WHERE transfer_id=?", (tid,)):
            move_stock(it["product_id"], tr["to_loc"], it["qty"],
                       "transfer-in", tr["ref_no"])
        x("UPDATE transfers SET status='received' WHERE id=?", (tid,))
        log("transfer_receive", tr["ref_no"])
        s.load_tr(); s.load()
        s.mw.broadcast_all()
    def cancel_tr(s):
        tid = s._tr_row()
        if tid is None:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        tr = q1("SELECT * FROM transfers WHERE id=?", (tid,))
        if tr["status"] != "in-transit": return
        for it in q("SELECT * FROM transfer_items WHERE transfer_id=?", (tid,)):
            move_stock(it["product_id"], tr["from_loc"], it["qty"],
                       "transfer-cancel", tr["ref_no"])
        x("UPDATE transfers SET status='cancelled' WHERE id=?", (tid,))
        log("transfer_cancel", tr["ref_no"])
        s.load_tr(); s.load()
    def del_tr(s):
        if not is_admin():
            QMessageBox.warning(s, APP, "🚫 " + T("No permission")); return
        tid = s._tr_row()
        if tid is None:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        tr = q1("SELECT * FROM transfers WHERE id=?", (tid,))
        if tr["status"] == "in-transit":
            QMessageBox.warning(s, APP, "🚚 " + (
                "لا يمكن حذف تحويل في الطريق — استلمه أو ألغه أولاً"
                if LANG == "ar" else "Receive or cancel it first."))
            return
        if QMessageBox.question(s, APP, T("Are you sure?")) == QMessageBox.Yes:
            x("DELETE FROM transfer_items WHERE transfer_id=?", (tid,))
            x("DELETE FROM transfers WHERE id=?", (tid,))
            log("transfer_del", tr["ref_no"]); s.load_tr()

# ============================== EXPENSES =====================================
class ExpensesPage(QWidget):
    """🧮 المصروفات — تُخصم من الدرج أو الخزنة + فحص رصيد قبل التنفيذ"""
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        top = QHBoxLayout()
        nb = QPushButton("➕ " + T("Add")); nb.setObjectName("success")
        nb.setMinimumHeight(42); nb.clicked.connect(s.add); top.addWidget(nb)
        s.q = make_search(); top.addWidget(s.q); top.addStretch(1)
        v.addLayout(top)
        s.tbl = QTableWidget(0, 6)
        s.tbl.setHorizontalHeaderLabels([T("Date"), T("Category name"),
            T("Description"), T("Amount spent"), T("Account"), T("Username")])
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v.addWidget(s.tbl, 1)
        bot = QHBoxLayout()
        eb = QPushButton("✏️ " + T("Edit")); eb.clicked.connect(s.edit)
        bot.addWidget(eb)
        db = QPushButton("🗑 " + T("Delete")); db.setObjectName("danger")
        db.clicked.connect(s.delete); bot.addWidget(db)
        bx = QPushButton("📤 " + T("Export CSV")); bx.clicked.connect(s.export)
        bot.addWidget(bx); bot.addStretch(1); v.addLayout(bot)
        s.ids = []; s.refresh()
    def _bal(s, acc):
        return q1("SELECT IFNULL(SUM(CASE WHEN direction='in' THEN amount "
                  "ELSE -amount END),0) v FROM treasury WHERE account=?",
                  (acc,))["v"]
    def _acc(s, a):
        return T("Drawer") if a == "drawer" else T("Vault")
    def refresh(s):
        rows = q("SELECT * FROM expenses ORDER BY id DESC LIMIT 500")
        s.tbl.setRowCount(len(rows)); s.ids = [r["id"] for r in rows]
        for i, r in enumerate(rows):
            vals = [r["ts"], r["category"], r["description"], money(r["amount"]),
                    s._acc(r.get("account", "drawer")), r["username"] or ""]
            for j, val in enumerate(vals):
                it = QTableWidgetItem(str(val or ""))
                it.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, it)
        wire_search(s.q, s.tbl)
    def sel_id(s):
        r = s.tbl.currentRow()
        return s.ids[r] if 0 <= r < len(s.ids) else None
    def _form(s, rec=None):
        d = QDialog(s); d.setMinimumWidth(520)
        f = QFormLayout(d); f.setSpacing(12)
        cat = QLineEdit(rec["category"] if rec else ""); cat.setMinimumHeight(38)
        desc = QLineEdit(rec["description"] if rec else "")
        desc.setMinimumHeight(38)
        amt = QDoubleSpinBox(); amt.setMaximum(10**7); amt.setMinimumHeight(38)
        amt.setAlignment(Qt.AlignCenter)
        if rec: amt.setValue(rec["amount"])
        acc = QComboBox(); acc.setMinimumHeight(38)
        acc.addItem("🧰 " + T("Drawer"), "drawer")
        acc.addItem("🏦 " + T("Vault"), "vault")
        if rec:
            ix = acc.findData(rec.get("account", "drawer"))
            if ix >= 0: acc.setCurrentIndex(ix)
        f.addRow(T("Category name"), cat); f.addRow(T("Description"), desc)
        f.addRow(T("Amount spent"), amt); f.addRow(T("Account"), acc)
        ok = QPushButton("💾 " + T("Save")); ok.setObjectName("success")
        ok.setMinimumHeight(42); f.addRow(ok)
        return d, cat, desc, amt, acc, ok
    def _trow(s, acc, amount, reason, ref):
        x("INSERT INTO treasury(ts,account,direction,amount,reason,ref,"
          "username) VALUES(?,?,?,?,?,?,?)",
          (nows(), acc, "out", amount, reason, ref, CUR_USER["username"]))
    def _chk(s, acc, need, dlg, extra=0.0):
        b_ = s._bal(acc) + extra
        if need > b_ + 0.001:
            if LANG == "ar":
                msg = s._acc(acc) + " — الرصيد لا يكفي! المتاح: "
            else:
                msg = s._acc(acc) + " - INSUFFICIENT! Available: "
            QMessageBox.warning(dlg, APP, msg + money(b_) + " " + cur())
            return False
        return True
    def add(s):
        if not (allowed("expenses") or is_admin()):
            QMessageBox.warning(s, APP, "🚫 " + T("No permission")); return
        d, cat, desc, amt, acc, ok = s._form()
        def do():
            if amt.value() <= 0 or not cat.text().strip(): return
            if not s._chk(acc.currentData(), amt.value(), d): return
            eid = x("INSERT INTO expenses(ts,category,description,amount,"
                    "account,username) VALUES(?,?,?,?,?,?)",
                    (nows(), cat.text().strip(), desc.text().strip(),
                     amt.value(), acc.currentData(), CUR_USER["username"]))
            s._trow(acc.currentData(), amt.value(),
                    (cat.text().strip() + " " + desc.text().strip()).strip(),
                    "EXP-" + str(eid))
            log("expense", f"{amt.value()} {acc.currentData()}")
            s.refresh()
            try: s.mw.broadcast_all()
            except Exception: pass
            if LANG == "ar":
                done = "✅ تم — رصيد " + s._acc(acc.currentData()) + ": "
            else:
                done = "OK " + s._acc(acc.currentData()) + ": "
            QMessageBox.information(s, APP,
                done + money(s._bal(acc.currentData())) + " " + cur())
            d.accept()
        ok.clicked.connect(do); d.exec()
    def edit(s):
        i = s.sel_id()
        if not i:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        rec = q1("SELECT * FROM expenses WHERE id=?", (i,))
        d, cat, desc, amt, acc, ok = s._form(rec)
        def do():
            old_mv = q1("SELECT amount FROM treasury WHERE ref=?",
                        ("EXP-" + str(i),))
            old_amt = old_mv["amount"] if old_mv else 0.0
            if amt.value() <= 0 or not cat.text().strip(): return
            if not s._chk(acc.currentData(), amt.value(), d, extra=old_amt):
                return
            x("UPDATE expenses SET category=?,description=?,amount=?,account=? "
              "WHERE id=?",
              (cat.text().strip(), desc.text().strip(), amt.value(),
               acc.currentData(), i))
            x("DELETE FROM treasury WHERE ref=?", ("EXP-" + str(i),))
            s._trow(acc.currentData(), amt.value(),
                    (cat.text().strip() + " " + desc.text().strip()).strip(),
                    "EXP-" + str(i))
            log("expense_edit", "#" + str(i))
            s.refresh()
            try: s.mw.broadcast_all()
            except Exception: pass
            QMessageBox.information(s, APP, "✅ " + T("Saved"))
            d.accept()
        ok.clicked.connect(do); d.exec()
    def delete(s):
        if not (allowed("expenses") or is_admin()):
            QMessageBox.warning(s, APP, "🚫 " + T("No permission")); return
        i = s.sel_id()
        if not i:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        if not admin_password_check(s): return
        if QMessageBox.question(s, APP, T("Are you sure?")) == QMessageBox.Yes:
            trash_put("expenses", i)
            x("DELETE FROM treasury WHERE ref=?", ("EXP-" + str(i),))
            x("DELETE FROM expenses WHERE id=?", (i,))
            log("expense_del", "#" + str(i)); s.refresh()
            try: s.mw.broadcast_all()
            except Exception: pass
    def export(s):
        rows = q("SELECT * FROM expenses ORDER BY id DESC LIMIT 2000")
        export_csv([T("Date"), T("Category name"), T("Description"),
                    T("Amount spent"), T("Account"), T("Username")],
                   [[r["ts"], r["category"], r["description"], r["amount"],
                     r.get("account", "drawer"), r["username"]] for r in rows])

# ============================== CASH & TREASURY ==============================
class CashPage(QWidget):
    """🧰 الدرج = النقدية المتاحة • 🏦 الخزنة = الرصيد الرئيسي"""
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        v.setContentsMargins(12, 12, 12, 12)
        _ar = LANG == "ar"
        hint = QLabel("🔗 " + (
            "الدرج 🧰 والخزنة 🏦 يبدآن من صفر ويزيدان معًا مع كل مبيعات وإيداعات — "
            "والفرق بينهما = المصاريف والمشتريات والسحوبات اللي دفعتها من حساب معين"
            if _ar else
            "Drawer and Vault grow together with every sale and deposit — "
            "they differ only by expenses/withdrawals paid from a chosen account."))
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#64748b;font-weight:600;")
        v.addWidget(hint)
        g = QHBoxLayout(); g.setSpacing(12)
        s.c_draw  = stat_card("🧰", T("Drawer"), "—", "#10b981")
        s.c_vault = stat_card("🏦", T("Vault"), "—", "#2563eb")
        s.c_owner = stat_card("👤", T("Pay Owner"), "—", "#f59e0b")
        for c in (s.c_draw, s.c_vault, s.c_owner): g.addWidget(c)
        v.addLayout(g)
        btns = QHBoxLayout()
        L = lambda a_, e_: a_ if _ar else e_
        for lab, fn, sty in [
                ("➕ " + L("إيداع في الصندوق", "Deposit"), s.deposit, "success"),
                ("👤 " + T("Pay Owner"), s.pay_owner, "danger"),
                ("🧹 " + L("تصفير سجل الصندوق — أدمن", "Reset — admin"),
                 s.reset_all, "warn")]:
            b = QPushButton(lab); b.setObjectName(sty); b.setMinimumHeight(42)
            b.clicked.connect(fn); btns.addWidget(b)
        v.addLayout(btns)
        s.q = make_search(); v.addWidget(s.q)
        s.tbl = QTableWidget(0, 7)
        s.tbl.setHorizontalHeaderLabels([T("Date"), T("Account"),
            T("In") + "/" + T("Out"), T("Description"), T("Ref"),
            T("Username"), T("Amount")])
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v.addWidget(s.tbl, 1)
        bx = QPushButton("📤 " + T("Export CSV")); bx.clicked.connect(s.export)
        v.addWidget(bx, 0, Qt.AlignLeft)
        s.refresh()
    def _bal(s, acc):
        return q1("SELECT IFNULL(SUM(CASE WHEN direction='in' THEN amount "
                  "ELSE -amount END),0) v FROM treasury WHERE account=?",
                  (acc,))["v"]
    def _owner_paid(s):
        return q1("SELECT IFNULL(SUM(amount),0) v FROM treasury "
                  "WHERE direction='out' AND ref LIKE 'OWNER%'")["v"]
    def _add(s, acc, direction, amount, reason, ref):
        x("INSERT INTO treasury(ts,account,direction,amount,reason,ref,"
          "username) VALUES(?,?,?,?,?,?,?)",
          (nows(), acc, direction, amount, reason, ref, CUR_USER["username"]))
    def _ref(s, p):
        return p + "-" + str(int(dt.datetime.now().timestamp()
                              * 1000) % 100000000)
    def _ask(s, title, with_acc=False):
        d = QDialog(s); d.setWindowTitle(title); d.setMinimumWidth(480)
        f = QFormLayout(d); f.setSpacing(12)
        amt = QDoubleSpinBox(); amt.setMaximum(10**7); amt.setMinimumHeight(40)
        amt.setAlignment(Qt.AlignCenter)
        rs = QLineEdit(); rs.setMinimumHeight(38)
        f.addRow(T("Amount"), amt); f.addRow(T("Reason"), rs)
        acc = None
        if with_acc:
            acc = QComboBox(); acc.setMinimumHeight(38)
            acc.addItem("🧰 " + T("Drawer"), "drawer")
            acc.addItem("🏦 " + T("Vault"), "vault")
            f.addRow(T("Account"), acc)
        ok = QPushButton("✅ " + T("Confirm")); ok.setObjectName("success")
        ok.setMinimumHeight(42); f.addRow(ok)
        return d, amt, rs, acc, ok
    def _reason(s, base, rs):
        return base + (" - " + rs.text() if rs.text() else "")
    def deposit(s):
        _ar = LANG == "ar"
        d, amt, rs, _, ok = s._ask("➕ " + (_ar and "إيداع في الصندوق"
                                            or "Deposit"))
        def do():
            a = amt.value()
            if a <= 0: return
            r = s._ref("DEP")
            txt = s._reason("إيداع" if _ar else "Deposit", rs)
            s._add("drawer", "in", a, txt, r)
            s._add("vault", "in", a, txt, r)
            log("cash_deposit", str(a)); s.refresh()
            try: s.mw.broadcast_all()
            except Exception: pass
            d.accept()
        ok.clicked.connect(do); d.exec()
    def pay_owner(s):
        d, amt, rs, acc, ok = s._ask("👤 " + T("Pay Owner"), with_acc=True)
        def do():
            a = amt.value()
            if a <= 0: return
            b_ = q1("SELECT IFNULL(SUM(CASE WHEN direction='in' THEN amount "
                    "ELSE -amount END),0) v FROM treasury WHERE account=?",
                    (acc.currentData(),))["v"]
            if a > b_ + 0.001:
                QMessageBox.warning(s, APP,
                    ("🧰 " if acc.currentData() == "drawer" else "🏦 ")
                    + T("Insufficient payment!")); return
            s._add(acc.currentData(), "out", a,
                   s._reason(T("Pay Owner"), rs), s._ref("OWNER"))
            log("cash_owner", str(a)); s.refresh()
            try: s.mw.broadcast_all()
            except Exception: pass
            d.accept()
        ok.clicked.connect(do); d.exec()
    def reset_all(s):
        if not is_admin():
            QMessageBox.warning(s, APP, "🚫 " + T("No permission")); return
        if QMessageBox.question(s, APP, "🧹 " + T("Are you sure?")) \
                != QMessageBox.Yes: return
        x("DELETE FROM treasury"); log("treasury_reset"); s.refresh()
    def refresh(s):
        s.c_draw._v.setText(money(s._bal("drawer")) + " " + cur())
        s.c_vault._v.setText(money(s._bal("vault")) + " " + cur())
        s.c_owner._v.setText(money(s._owner_paid()) + " " + cur())
        rows = q("SELECT * FROM treasury ORDER BY id DESC LIMIT 500")
        s.tbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            acc = T("Drawer") if r["account"] == "drawer" else T("Vault")
            dirn = ("⬅️ " + T("In")) if r["direction"] == "in" \
                   else ("➡️ " + T("Out"))
            vals = [r["ts"], acc, dirn, r["reason"] or "", r["ref"] or "",
                    r["username"] or "", money(r["amount"])]
            for j, val in enumerate(vals):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignCenter)
                if j == 2:
                    it.setForeground(QBrush(QColor(
                        "#10b981" if r["direction"] == "in" else "#ef4444")))
                s.tbl.setItem(i, j, it)
        wire_search(s.q, s.tbl)
    def export(s):
        rows = q("SELECT * FROM treasury ORDER BY id DESC LIMIT 5000")
        export_csv([T("Date"), T("Account"), T("In") + "/" + T("Out"),
                    T("Description"), T("Ref"), T("Username"), T("Amount")],
                   [[r["ts"], r["account"], r["direction"], r["reason"],
                     r["ref"], r["username"], r["amount"]] for r in rows])
        # ============================== QUOTATIONS ===================================
class QuotesPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        top = QHBoxLayout()
        nb = QPushButton("➕ " + T("New Quotation")); nb.setObjectName("primary")
        nb.clicked.connect(s.editor); top.addWidget(nb)
        s.q = make_search(); top.addWidget(s.q)
        top.addStretch(1); v.addLayout(top)
        s.tbl = QTableWidget(0, 6)
        s.tbl.setHorizontalHeaderLabels([T("Invoice No"), T("Date"),
            T("Customer"), T("Grand Total"), T("Status"), T("Valid Until")])
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v.addWidget(s.tbl, 1); s.ids = []
        bot = QHBoxLayout()
        for lab, fn, sty in [("✅ " + T("Approve"),
                              lambda: s.setst("approved"), "success"),
                             ("❌ " + T("Reject"),
                              lambda: s.setst("rejected"), "danger"),
                             ("🧾 " + T("Convert to Invoice"), s.convert, "primary"),
                             ("📄 " + T("Print A4"), s.printq, ""),
                             ("🗑 " + T("Delete"), s.del_quote, "danger")]:
            b = QPushButton(lab); b.setObjectName(sty); b.clicked.connect(fn)
            bot.addWidget(b)
        bot.addStretch(1); v.addLayout(bot); s.refresh()
    def refresh(s):
        rows = q("SELECT q.*, c.name cname FROM quotations q LEFT JOIN customers c "
                 "ON c.id=q.customer_id ORDER BY q.id DESC")
        s.tbl.setRowCount(len(rows)); s.ids = [r["id"] for r in rows]
        for i, r in enumerate(rows):
            for j, val in enumerate([r["quote_no"], r["ts"], r["cname"] or "",
                    money(r["total"]), T(r["status"]), r["valid_until"]]):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignCenter); s.tbl.setItem(i, j, it)
        wire_search(s.q, s.tbl)
    def del_quote(s):
        admin_delete(s, s.tbl, s.ids, "quotations", after=s.refresh)
    def sel(s):
        r = s.tbl.currentRow()
        return s.ids[r] if 0 <= r < len(s.ids) else None
    def setst(s, st):
        i = s.sel()
        if i:
            x("UPDATE quotations SET status=? WHERE id=?", (st, i))
            log("quote_status", str(i)); s.refresh()
    def printq(s):
        i = s.sel()
        if not i: return
        qd = q1("SELECT * FROM quotations WHERE id=?", (i,))
        its = q("SELECT * FROM quote_items WHERE quote_id=?", (i,))
        rows = "".join(
            f"<tr><td>{it['name']}</td><td align=center>{it['qty']:g}</td>"
            f"<td align=right>{money(it['price'])}</td>"
            f"<td align=right>{money(it['total'])}</td></tr>" for it in its)
        html = (f"<h1>📑 {T('Quotations')} — {qd['quote_no']}</h1>"
                f"<p>{T('Valid Until')}: {qd['valid_until']} — "
                f"{T(qd['status'])}</p>"
                f"<table width=100% cellpadding=6 border=1>{rows}</table>"
                f"<h3>{T('Grand Total')}: {money(qd['total'])} {cur()}</h3>")
        do_print(html, a4=True, parent=s)
    def editor(s):
        d = QDialog(s); d.setWindowTitle("📑 " + T("New Quotation"))
        d.resize(820, 620); v = QVBoxLayout(d); g = QFormLayout(); g.setSpacing(10)
        cust = QComboBox()
        for c in q("SELECT * FROM customers"):
            cust.addItem("👤 " + c["name"], c["id"])
        editable_combo(cust); cust.setMinimumHeight(38)
        val = QDateEdit(QDate.currentDate().addDays(14))
        val.setCalendarPopup(True); val.setMinimumHeight(38)
        terms = QLineEdit(); terms.setPlaceholderText(T("Terms"))
        terms.setMinimumHeight(38)
        g.addRow(T("Customer"), cust); g.addRow(T("Valid Until"), val)
        g.addRow(T("Terms"), terms); v.addLayout(g)
        t = QTableWidget(0, 4)
        t.setHorizontalHeaderLabels([T("Product"), T("Qty"), T("Price"),
                                     T("Total")])
        t.verticalHeader().setDefaultSectionSize(52)
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for col, wdt in ((1, 140), (2, 170), (3, 180)):
            hh.setSectionResizeMode(col, QHeaderView.Fixed)
            t.setColumnWidth(col, wdt)
        prods = q("SELECT * FROM products WHERE active=1 ORDER BY name")
        def addrow():
            r = t.rowCount(); t.insertRow(r)
            c = QComboBox()
            for p in prods: c.addItem(disp_name(p), p["id"])
            editable_combo(c); c.setMinimumHeight(40)
            c.setMinimumWidth(220); c.view().setMinimumWidth(440)
            c.setCurrentIndex(-1)
            qs = QDoubleSpinBox(); qs.setMaximum(10**6); qs.setMinimumHeight(40)
            qs.setAlignment(Qt.AlignCenter)
            ps = QDoubleSpinBox(); ps.setMaximum(10**7); ps.setDecimals(2)
            ps.setMinimumHeight(40); ps.setAlignment(Qt.AlignCenter)
            lab = QLabel("0.00"); lab.setAlignment(Qt.AlignCenter)
            lab.setStyleSheet("font-weight:800;font-size:14px;")
            upd = lambda *_: lab.setText(money(qs.value() * ps.value()))
            qs.valueChanged.connect(upd); ps.valueChanged.connect(upd)
            t.setCellWidget(r, 0, c); t.setCellWidget(r, 1, qs)
            t.setCellWidget(r, 2, ps); t.setCellWidget(r, 3, lab)
        addrow(); v.addWidget(t, 1)
        ar = QHBoxLayout()
        ab = QPushButton("➕ " + T("Add")); ab.setObjectName("primary")
        ab.setMinimumHeight(40); ab.clicked.connect(addrow); ar.addWidget(ab)
        rb = QPushButton("➖"); rb.setMinimumHeight(40)
        rb.clicked.connect(lambda: t.rowCount() > 1
                           and t.removeRow(t.rowCount() - 1))
        ar.addWidget(rb); ar.addStretch(1)
        totl = QLabel(T("Grand Total") + ": 0.00"); totl.setObjectName("big")
        ar.addWidget(totl); v.addLayout(ar)
        ok = QPushButton("💾 " + T("Save")); ok.setObjectName("success")
        ok.setMinimumHeight(46); v.addWidget(ok)
        def recalc():
            try:
                tt = sum(t.cellWidget(r, 1).value() * t.cellWidget(r, 2).value()
                         for r in range(t.rowCount()))
                totl.setText(T("Grand Total") + ": " + money(tt))
            except Exception: pass
        tm = QTimer(d); tm.timeout.connect(recalc); tm.start(400)
        def do():
            if cust.currentData() is None:
                QMessageBox.warning(d, APP, "👤 اختر عميل"); return
            no = inv_no("QT"); sub = 0
            qid = x("INSERT INTO quotations(quote_no,ts,customer_id,"
                    "valid_until,subtotal,discount,tax,total,status,notes) "
                    "VALUES(?,?,?,?,?,0,0,0,'draft',?)",
                    (no, nows(), cust.currentData(),
                     val.date().toString("yyyy-MM-dd"), terms.text()))
            for r in range(t.rowCount()):
                p_ = t.cellWidget(r, 0).currentData()
                qt = t.cellWidget(r, 1).value()
                ps = t.cellWidget(r, 2).value()
                if not p_ or qt <= 0: continue
                sub += qt * ps
                nm = disp_name(q1("SELECT * FROM products WHERE id=?", (p_,)))
                x("INSERT INTO quote_items(quote_id,product_id,name,qty,price,"
                  "total) VALUES(?,?,?,?,?,?)", (qid, p_, nm, qt, ps, qt * ps))
            vat = (round(sub * float(SET.get("vat", 15)) / 100, 2)
                   if taxchk.isChecked() else 0.0)
            x("UPDATE quotations SET subtotal=?,tax=?,total=? WHERE id=?",
              (sub, vat, round(sub + vat, 2), qid))
            log("quote_new", no)
            QMessageBox.information(d, APP, "✅ " + T("Quotation saved"))
            s.refresh(); d.accept()
        ok.clicked.connect(do); d.exec()
    def convert(s):
        i = s.sel()
        if not i: return
        qd = q1("SELECT * FROM quotations WHERE id=?", (i,))
        if qd["status"] == "converted": return
        its = q("SELECT * FROM quote_items WHERE quote_id=?", (i,))
        no = inv_no("SL")
        sid = x("INSERT INTO sales(invoice_no,ts,username,customer_id,"
                "location_id,shift_id,subtotal,discount,tax,total,paid_cash,"
                "paid_card,change,status,notes) "
                "VALUES(?,?,?,?,NULL,NULL,?,0,?,?,0,0,0,'unpaid',?)",
                (no, nows(), CUR_USER["username"], qd["customer_id"],
                 qd["subtotal"], qd["tax"], qd["total"], qd["quote_no"]))
        for it in its:
            x("INSERT INTO sale_items(sale_id,product_id,name,qty,price,cost,"
              "total) VALUES(?,?,?,?,?,0,?)",
              (sid, it["product_id"], it["name"], it["qty"], it["price"],
               it["price"] * it["qty"]))
        if qd["customer_id"]:
            x("UPDATE customers SET balance=balance+? WHERE id=?",
              (qd["total"], qd["customer_id"]))
        x("UPDATE quotations SET status='converted' WHERE id=?", (i,))
        log("quote_convert", f"{qd['quote_no']}→{no}")
        QMessageBox.information(s, APP,
            T("Quote converted to invoice") + ": " + no)
        s.refresh()

# ============================== E-INVOICING ==================================
class EInvoicePage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        sp = QSplitter()
        left = QWidget(); lv = QVBoxLayout(left)
        s.q = make_search(); lv.addWidget(s.q)
        s.tbl = QTableWidget(0, 3)
        s.tbl.setHorizontalHeaderLabels([T("Invoice No"), T("Date"),
                                         T("Grand Total")])
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lv.addWidget(s.tbl); sp.addWidget(left)
        right = QWidget(); rv = QVBoxLayout(right)
        s.qr = QLabel("⚡"); s.qr.setAlignment(Qt.AlignCenter)
        s.qr.setMinimumHeight(220)
        s.tlv = QPlainTextEdit(); s.tlv.setReadOnly(True)
        rv.addWidget(s.qr, 1); rv.addWidget(s.tlv, 1); sp.addWidget(right)
        sp.setSizes([500, 320]); v.addWidget(sp, 1)
        bot = QHBoxLayout()
        for lab, fn, sty in [("⚡ " + T("E-Invoice JSON"), s.json, "primary"),
                             ("📄 " + T("E-Invoice XML"), s.xml, ""),
                             ("🖨 " + T("Tax Invoice"), s.printx, "success"),
                             ("🗑 " + T("Delete"), s.del_sale, "danger")]:
            b = QPushButton(lab); b.setObjectName(sty); b.clicked.connect(fn)
            bot.addWidget(b)
        bot.addStretch(1); v.addLayout(bot)
        s.tbl.currentCellChanged.connect(s.show_qr)
        s.rows = []; s.refresh()
    def refresh(s):
        rows = q("SELECT * FROM sales WHERE status IN ('completed','unpaid') "
                 "ORDER BY id DESC LIMIT 200")
        s.rows = [r["id"] for r in rows]; s.tbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, val in enumerate([r["invoice_no"], r["ts"],
                                     money(r["total"])]):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, it)
        wire_search(s.q, s.tbl)
    def del_sale(s):
        admin_delete(s, s.tbl, s.rows, "sales", after=s.refresh)
    def cur_sale(s):
        r = s.tbl.currentRow()
        return (q1("SELECT * FROM sales WHERE id=?", (s.rows[r],))
                if 0 <= r < len(s.rows) else None)
    def show_qr(s, *_):
        sale = s.cur_sale()
        if not sale: return
        p = zatca_qr_payload(sale); s.tlv.setPlainText(p)
        img = qr_image(p, 200)
        if img: s.qr.setPixmap(QPixmap.fromImage(img))
    def json(s):
        sale = s.cur_sale()
        if not sale:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        items = q("SELECT * FROM sale_items WHERE sale_id=?", (sale["id"],))
        doc = {"invoice": sale["invoice_no"], "timestamp": sale["ts"],
               "seller": {"name_ar": SET.get("company_ar"),
                          "vat": SET.get("tax_no")},
               "totals": {k: sale[k] for k in
                          ("subtotal", "discount", "tax", "total")},
               "qr": zatca_qr_payload(sale),
               "lines": [dict(it) for it in items]}
        path, _ = QFileDialog.getSaveFileName(s, "JSON",
                                              sale["invoice_no"] + ".json")
        if path:
            open(path, "w", encoding="utf-8").write(
                json.dumps(doc, ensure_ascii=False, indent=2))
            QMessageBox.information(s, APP, T("Exported"))
    def xml(s):
        sale = s.cur_sale()
        if not sale:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        items = q("SELECT * FROM sale_items WHERE sale_id=?", (sale["id"],))
        x_ = [f"<Invoice no='{sale['invoice_no']}' ts='{sale['ts']}' "
              f"currency='{SET.get('currency')}'>",
              f"<Seller name='{SET.get('company')}' "
              f"vat='{SET.get('tax_no')}'/>"]
        for it in items:
            x_.append(f"<Line name='{it['name']}' qty='{it['qty']}' "
                      f"price='{it['price']}' total='{it['total']}'/>")
        x_.append(f"<Totals subtotal='{sale['subtotal']}' "
                  f"discount='{sale['discount']}' vat='{sale['tax']}' "
                  f"total='{sale['total']}'/>")
        x_.append(f"<QR base64='{zatca_qr_payload(sale)}'/></Invoice>")
        path, _ = QFileDialog.getSaveFileName(s, "XML",
                                              sale["invoice_no"] + ".xml")
        if path:
            open(path, "w", encoding="utf-8").write("\n".join(x_))
            QMessageBox.information(s, APP, T("Exported"))
    def printx(s):
        sale = s.cur_sale()
        if sale: print_a4(sale["id"], tax=True, parent=s)

# ============================== PARTIES ======================================
class PartiesPage(QWidget):
    def __init__(s, mw, kind="customers"):
        super().__init__(); s.mw = mw; s.kind = kind; v = QVBoxLayout(s)
        if kind == "customers":
            tier_opts = lambda: [("Bronze", T("Bronze")),
                                 ("Silver", T("Silver")), ("Gold", T("Gold"))]
            s.ed = TableEditor(mw, "customers",
                [("name","Customer"),("phone","Phone"),("tier","Tier"),
                 ("points","Points"),("balance","Balance")],
                [("name","Customer","text",None),
                 ("phone","Phone","text",None),
                 ("tier","Tier","combo",tier_opts),
                 ("points","Points","num",None),
                 ("balance","Balance","num",None),
                 ("notes","Notes","memo",None)],
                search_cols=["name","phone"], module=kind)
        else:
            s.ed = TableEditor(mw, "suppliers",
                [("name","Supplier"),("phone","Phone"),("balance","Balance")],
                [("name","Supplier","text",None),
                 ("phone","Phone","text",None),
                 ("balance","Balance","num",None),
                 ("notes","Notes","memo",None)],
                search_cols=["name","phone"], module=kind)
        v.addWidget(s.ed, 1); s.ed.refresh()
        bot = QHBoxLayout()
        b1 = QPushButton("💵 " + (T("Receive Payment")
                                  if kind == "customers"
                                  else T("Pay Supplier")))
        b1.setObjectName("success"); b1.clicked.connect(s.pay); bot.addWidget(b1)
        b2 = QPushButton("📖 " + T("Ledger")); b2.setObjectName("primary")
        b2.clicked.connect(s.ledger); bot.addWidget(b2)
        bot.addStretch(1); v.addLayout(bot)
    def pay(s):
        c = QComboBox()
        for r in q(f"SELECT * FROM {s.kind}"): c.addItem(r["name"], r["id"])
        editable_combo(c)
        amt = QDoubleSpinBox(); amt.setMaximum(10**7); amt.setMinimumHeight(38)
        amt.setAlignment(Qt.AlignCenter)
        acc = QComboBox(); acc.setMinimumHeight(38)
        acc.addItem("🧰 " + T("Drawer"), "drawer")
        acc.addItem("🏦 " + T("Vault"), "vault")
        d = QDialog(s); f = QFormLayout(d); f.setSpacing(12)
        f.addRow(T("Customer") if s.kind == "customers"
                 else T("Supplier"), c)
        f.addRow(T("Amount"), amt); f.addRow(T("Account"), acc)
        ok = QPushButton("💾 " + T("Save")); ok.setObjectName("success")
        ok.setMinimumHeight(42); f.addRow(ok)
        def do():
            a_ = amt.value()
            if a_ <= 0 or c.currentData() is None: return
            dr = "in" if s.kind == "customers" else "out"
            if dr == "out":
                b_ = q1("SELECT IFNULL(SUM(CASE WHEN direction='in' THEN amount "
                        "ELSE -amount END),0) v FROM treasury WHERE account=?",
                        (acc.currentData(),))["v"]
                if a_ > b_ + 0.001:
                    QMessageBox.warning(s, APP, T("Insufficient payment!"))
                    return
                x("INSERT INTO treasury(ts,account,direction,amount,reason,"
                  "ref,username) VALUES(?,?,?,?,?,?,?)",
                  (nows(), acc.currentData(), "out", a_,
                   "دفعة " + (c.currentText() or ""), "PAY",
                   CUR_USER["username"]))
            else:
                for _acc in ("drawer", "vault"):
                    x("INSERT INTO treasury(ts,account,direction,amount,"
                      "reason,ref,username) VALUES(?,?,?,?,?,?,?)",
                      (nows(), _acc, "in", a_,
                       "دفعة " + (c.currentText() or ""), "PAY",
                       CUR_USER["username"]))
            x("INSERT INTO payments(ts,party_type,party_id,amount,direction,"
              "method,username) VALUES(?,?,?,?,?,?,?)",
              (nows(), s.kind, c.currentData(), a_, dr, "cash",
               CUR_USER["username"]))
            x(f"UPDATE {s.kind} SET balance=balance-? WHERE id=?",
              (a_, c.currentData()))
            log(f"{s.kind}_payment", str(a_))
            QMessageBox.information(s, APP, T("Payment saved"))
            s.ed.refresh()
            try: s.mw.broadcast_all()
            except Exception: pass
            d.accept()
        ok.clicked.connect(do); d.exec()
    def ledger(s):
        i = s.ed.sel_id()
        if not i:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        r = q1(f"SELECT * FROM {s.kind} WHERE id=?", (i,))
        pays = q("SELECT * FROM payments WHERE party_type=? AND party_id=? "
                 "ORDER BY ts DESC", (s.kind, r["id"]))
        if s.kind == "customers":
            docs = q("SELECT invoice_no, ts, total, status FROM sales "
                     "WHERE customer_id=? ORDER BY id DESC LIMIT 200", (i,))
            extra = f" • ⭐ {r.get('points', 0):g} {T('Points')}"
        else:
            docs = q("""SELECT p.ref_no invoice_no, p.ts, p.total, p.status,
                        (SELECT COUNT(*) FROM purchase_items pi
                         WHERE pi.purchase_id=p.id) n FROM purchases p
                        WHERE supplier_id=? ORDER BY p.id DESC LIMIT 200""", (i,))
            extra = ""
        d = QDialog(s); d.setWindowTitle("📖 " + r["name"])
        d.resize(720, 560); v = QVBoxLayout(d)
        head = QLabel(("👤" if s.kind == "customers" else "🏭") + " "
                      + r["name"] + "   |   💰 " + T("Balance") + ": "
                      + money(r["balance"]) + " " + cur() + extra)
        head.setStyleSheet("font-weight:800;font-size:16px;color:#b91c1c;"
                           "background:rgba(239,68,68,.08);padding:10px;"
                           "border-radius:10px;")
        v.addWidget(head)
        v.addWidget(QLabel("🧾 " + T("Invoices")))
        t = QTableWidget(len(docs), 4)
        t.setHorizontalHeaderLabels([T("Invoice No"), T("Date"),
                                     T("Grand Total"), T("Status")])
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        for i2, p in enumerate(docs):
            for j, val in enumerate([p["invoice_no"], p["ts"],
                                     money(p["total"]), T(p["status"])]):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignCenter); t.setItem(i2, j, it)
        v.addWidget(t, 2)
        v.addWidget(QLabel("💵 " + T("Payment")))
        t2 = QTableWidget(len(pays), 2)
        t2.setHorizontalHeaderLabels([T("Date"), T("Amount")])
        t2.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t2.verticalHeader().setVisible(False)
        t2.setEditTriggers(QTableWidget.NoEditTriggers)
        t2.setMaximumHeight(180)
        for i2, p in enumerate(pays):
            t2.setItem(i2, 0, QTableWidgetItem(p["ts"]))
            t2.setItem(i2, 1, QTableWidgetItem(money(p["amount"])))
        v.addWidget(t2, 1)
        hb = QHBoxLayout()
        pr = QPushButton("🖨 " + T("Print")); pr.setObjectName("primary")
        def dop():
            html = (f"<h2>📖 {T('Ledger')} — {r['name']}</h2>"
                    f"<p>{T('Balance')}: <b>{money(r['balance'])} {cur()}</b>"
                    f"{extra}</p>"
                    "<table width=100% cellpadding=6 border=1>")
            for p in docs:
                html += (f"<tr><td>{p['invoice_no']}</td><td>{p['ts']}</td>"
                         f"<td align=right>{money(p['total'])}</td>"
                         f"<td>{T(p['status'])}</td></tr>")
            html += "</table><h3>💵 " + T("Payment") + "</h3>"
            html += "<table width=100% cellpadding=6 border=1>"
            for p in pays:
                html += (f"<tr><td>{p['ts']}</td>"
                         f"<td align=right>{money(p['amount'])}</td></tr>")
            do_print(html + "</table>", a4=True, parent=s)
        pr.clicked.connect(dop)
        cl = QPushButton(T("Close")); cl.clicked.connect(d.accept)
        hb.addWidget(pr); hb.addWidget(cl); hb.addStretch(1); v.addLayout(hb)
        d.exec()

# ============================== OFFERS =======================================
class OffersPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        tb = QTabWidget(); v.addWidget(tb)
        f = QWidget(); fv = QFormLayout(f); fv.setSpacing(12)
        s.w = {}
        for key, lab in [("loyalty_earn","Earn"),("loyalty_redeem","Points"),
                         ("tier_silver","Silver"),("tier_gold","Gold"),
                         ("tier_silver_disc","Percent %"),
                         ("tier_gold_disc","Percent %")]:
            sp = QDoubleSpinBox(); sp.setMaximum(10**6); sp.setDecimals(2)
            sp.setValue(float(SET.get(key, 0))); sp.setMinimumHeight(38)
            s.w[key] = sp
            fv.addRow("⭐ " + T(lab) + " — " + key, sp)
        b = QPushButton("💾 " + T("Save")); b.setObjectName("success")
        b.setMinimumHeight(42); b.clicked.connect(s.save); fv.addRow(b)
        tb.addTab(f, "🎁 " + T("Points"))
        cp_opts = lambda: [("percent", T("percent")), ("fixed", T("fixed"))]
        s.cp = TableEditor(mw, "coupons",
            [("code","Code"),("type","Type"),("value","Value"),
             ("min_total","Min Total"),("used","Points"),("active","Active")],
            [("code","Code","text",None),("type","Type","combo",cp_opts),
             ("value","Value","num",None),("min_total","Min Total","num",None),
             ("starts","Starts","date",None),("ends","Ends","date",None),
             ("active","Active","check",None)], module="offers")
        tb.addTab(s.cp, "🎟️ " + T("Coupons")); s.cp.refresh()
        sc_opts = lambda: [("product", T("product")), ("category", T("category"))]
        s.of = TableEditor(mw, "offers",
            [("scope","Type"),("target","Product"),("percent","Percent %"),
             ("starts","Starts"),("ends","Ends"),("active","Active")],
            [("scope","Type","combo",sc_opts),
             ("target","Product","text",None),
             ("percent","Percent %","num",None),
             ("starts","Starts","date",None),("ends","Ends","date",None),
             ("active","Active","check",None)], module="offers")
        tb.addTab(s.of, "🏷️ " + T("Offers")); s.of.refresh()
    def save(s):
        for k, w in s.w.items():
            x("INSERT INTO settings(key,value) VALUES(?,?) "
              "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
              (k, str(w.value())))
        load_settings(); log("loyalty_settings")
        QMessageBox.information(s, APP, T("Saved"))

# ============================== SHIFTS =======================================
class ShiftsPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        card = QFrame(); card.setObjectName("card"); c = QHBoxLayout(card)
        s.stat = QLabel(); s.stat.setObjectName("h1"); c.addWidget(s.stat)
        c.addStretch(1)
        b1 = QPushButton("🔓 " + T("Open Shift")); b1.setObjectName("success")
        b1.clicked.connect(s.open_shift); c.addWidget(b1)
        b2 = QPushButton("🔒 " + T("Close Shift")); b2.setObjectName("danger")
        b2.clicked.connect(s.close_shift); c.addWidget(b2)
        s.q = make_search(); c.addWidget(s.q)
        b3 = QPushButton("🗑 " + T("Delete")); b3.setObjectName("danger")
        b3.clicked.connect(s.del_shift); c.addWidget(b3)
        v.addWidget(card)
        s.tbl = QTableWidget(0, 8)
        s.tbl.setHorizontalHeaderLabels([T("Cashier"), T("Date"),
            T("Opening Cash"), T("Counted Cash"), T("Expected"),
            T("Difference"), T("Status"), T("Notes")])
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v.addWidget(s.tbl, 1); s.ids = []; s.refresh()
    def refresh(s):
        rows = q("SELECT * FROM shifts ORDER BY id DESC LIMIT 100")
        s.tbl.setRowCount(len(rows)); s.ids = [r["id"] for r in rows]
        op = q1("SELECT * FROM shifts WHERE status='open' AND username=? "
                "ORDER BY id DESC", (CUR_USER["username"],))
        s.stat.setText(("🟢 " + T("open") + " — " + CUR_USER["username"])
                       if op else "🔴 " + T("closed"))
        for i, r in enumerate(rows):
            vals = [r["username"], r["opened_at"], money(r["opening_cash"]),
                    money(r["counted_cash"] or 0), money(r["expected_cash"] or 0),
                    money(r["difference"] or 0), T(r["status"]),
                    r["notes"] or ""]
            for j, val in enumerate(vals):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, it)
        wire_search(s.q, s.tbl)
    def del_shift(s):
        admin_delete(s, s.tbl, s.ids, "shifts", after=s.refresh)
    def open_shift(s):
        if q1("SELECT * FROM shifts WHERE status='open' AND username=?",
              (CUR_USER["username"],)):
            QMessageBox.information(s, APP, T("Shift opened")); return
        amt = QDoubleSpinBox(); amt.setMaximum(10**7); amt.setMinimumHeight(38)
        amt.setAlignment(Qt.AlignCenter)
        d = QDialog(s); f = QFormLayout(d)
        f.addRow(T("Opening Cash") + " 🧰", amt)
        ok = QPushButton("✅ " + T("Open Shift")); ok.setObjectName("success")
        ok.setMinimumHeight(42); f.addRow(ok)
        def do():
            lid = q1("SELECT id FROM locations LIMIT 1")["id"]
            x("INSERT INTO shifts(username,location_id,opened_at,opening_cash,"
              "status) VALUES(?,?,?,?,'open')",
              (CUR_USER["username"], lid, nows(), amt.value()))
            cur_ = q1("SELECT IFNULL(SUM(CASE WHEN direction='in' THEN amount "
                      "ELSE -amount END),0) v FROM treasury "
                      "WHERE account='drawer'")["v"]
            adj_ = round(float(amt.value()) - cur_, 2)
            if abs(adj_) > 0.001:
                x("INSERT INTO treasury(ts,account,direction,amount,reason,"
                  "ref,username) VALUES(?,?,?,?,?,?,?)",
                  (nows(), "drawer", "in" if adj_ > 0 else "out", abs(adj_),
                   "افتتاح وردية",
                   "OPEN-" + str(int(dt.datetime.now().timestamp()
                                  * 1000) % 10**8),
                   CUR_USER["username"]))
            log("shift_open"); s.refresh()
            try: s.mw.broadcast_all()
            except Exception: pass
            d.accept()
        ok.clicked.connect(do); d.exec()
    def close_shift(s):
        sh = q1("SELECT * FROM shifts WHERE status='open' AND username=? "
                "ORDER BY id DESC", (CUR_USER["username"],))
        if not sh:
            QMessageBox.warning(s, APP, T("No open shift!")); return
        cash_in = q1("SELECT IFNULL(SUM(paid_cash-change),0) v FROM sales "
                     "WHERE shift_id=? AND status='completed'",
                     (sh["id"],))["v"]
        outs = q1("SELECT IFNULL(SUM(amount),0) v FROM treasury "
                  "WHERE account='drawer' AND direction='out' "
                  "AND ref NOT LIKE 'OPEN-%' AND ts>=?",
                  (sh["opened_at"],))["v"]
        exp = sh["opening_cash"] + cash_in - outs
        cnt = QDoubleSpinBox(); cnt.setMaximum(10**7); cnt.setValue(exp)
        cnt.setMinimumHeight(38); cnt.setAlignment(Qt.AlignCenter)
        d = QDialog(s); f = QFormLayout(d)
        f.addRow(T("Expected"), QLabel(
            f"{money(exp)} {cur()}  (افتتاحي {money(sh['opening_cash'])}"
            f" + كاش {money(cash_in)} − مصاريف {money(outs)})"))
        f.addRow(T("Counted Cash"), cnt)
        ok = QPushButton("🔒 " + T("Close Shift")); ok.setObjectName("danger")
        ok.setMinimumHeight(42); f.addRow(ok)
        def do():
            diff = cnt.value() - exp
            x("UPDATE shifts SET closed_at=?,counted_cash=?,expected_cash=?,"
              "difference=?,status='closed' WHERE id=?",
              (nows(), cnt.value(), exp, diff, sh["id"]))
            log("shift_close", f"diff={diff}")
            sales = q("SELECT invoice_no,total,status FROM sales "
                      "WHERE shift_id=?", (sh["id"],))
            html = (f"<h1>🕒 {T('Shift Report')} — {CUR_USER['username']}</h1>"
                    f"<p>{sh['opened_at']} → {nows()}</p>"
                    f"<p>{T('Opening Cash')}: {money(sh['opening_cash'])} + "
                    f"مبيعات كاش: {money(cash_in)} − مصاريف من الدرج: "
                    f"{money(outs)}<br>"
                    f"{T('Expected')}: {money(exp)} • "
                    f"{T('Counted Cash')}: {money(cnt.value())} • "
                    f"<b>{T('Difference')}: {money(diff)}</b></p>"
                    "<table width=100% cellpadding=5 border=1>")
            for r in sales:
                html += (f"<tr><td>{r['invoice_no']}</td>"
                         f"<td align=right>{money(r['total'])}</td>"
                         f"<td>{T(r['status'])}</td></tr>")
            do_print(html + "</table>", a4=True, parent=s)
            QMessageBox.information(s, APP, T("Shift closed"))
            s.refresh(); d.accept()
        ok.clicked.connect(do); d.exec()

# ============================== WORK ORDERS ==================================
class WorkOrdersPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        tb = QTabWidget(); v.addWidget(tb)
        cust_opts = lambda: [(c["id"], c["name"])
                             for c in q("SELECT * FROM customers")]
        user_opts = lambda: [(u["username"], u["full_name"])
                             for u in q("SELECT * FROM users WHERE active=1")]
        status_opts = lambda: [(x_, T(x_)) for x_ in
                               ["pending", "in-progress", "done", "delivered"]]
        s.work = TableEditor(mw, "work_orders",
            [("wo_no","Invoice No"),("title","Title"),("type","Type"),
             ("assigned_to","Assign To"),("status","Status"),
             ("due","Due Date")],
            [("type","Type","combo",[("work", T("Work Order")),
                                     ("delivery", T("Delivery Order"))]),
             ("title","Title","text",None),
             ("customer_id","Customer","combo",cust_opts),
             ("assigned_to","Assign To","combo",user_opts),
             ("details","Notes","memo",None),
             ("status","Status","combo",status_opts),
             ("due","Due Date","date",None)],
            search_cols=["wo_no","title"], module="workorders")
        tb.addTab(s.work, "🛠 " + T("Work Orders")); s.work.refresh()
        dv = QWidget(); dvv = QVBoxLayout(dv)
        bot = QHBoxLayout()
        b1 = QPushButton("➡️ " + T("Advance Status"))
        b1.setObjectName("primary"); b1.clicked.connect(s.advance)
        bot.addWidget(b1)
        b2 = QPushButton("🖨 " + T("Print Delivery Note"))
        b2.setObjectName("success"); b2.clicked.connect(s.print_dn)
        bot.addWidget(b2)
        b3 = QPushButton("🗑 " + T("Delete")); b3.setObjectName("danger")
        b3.clicked.connect(s.del_wo); bot.addWidget(b3)
        s.q = make_search(); bot.addWidget(s.q)
        bot.addStretch(1); dvv.addLayout(bot)
        s.tbl = QTableWidget(0, 6)
        s.tbl.setHorizontalHeaderLabels([T("Invoice No"), T("Title"),
            T("Customer"), T("Assign To"), T("Status"), T("Due Date")])
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        dvv.addWidget(s.tbl, 1)
        tb.addTab(dv, "🚚 " + T("Delivery Orders"))
        s.ids = []; s.load_deliveries()
    def load_deliveries(s):
        rows = q("""SELECT w.*, c.name cname FROM work_orders w
                 LEFT JOIN customers c ON c.id=w.customer_id
                 WHERE w.type='delivery' ORDER BY w.id DESC""")
        s.tbl.setRowCount(len(rows)); s.ids = [r["id"] for r in rows]
        for i, r in enumerate(rows):
            for j, val in enumerate([r["wo_no"], r["title"],
                    r["cname"] or "", r["assigned_to"], T(r["status"]),
                    r["due"]]):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, it)
        wire_search(s.q, s.tbl)
    def del_wo(s):
        admin_delete(s, s.tbl, s.ids, "work_orders", after=s.load_deliveries)
    def advance(s):
        r = s.tbl.currentRow()
        if r < 0: return
        order = ["pending", "in-progress", "done", "delivered"]
        w = q1("SELECT * FROM work_orders WHERE id=?", (s.ids[r],))
        nx = order[min(order.index(w["status"]) + 1, 3)]
        x("UPDATE work_orders SET status=? WHERE id=?", (nx, w["id"]))
        log("workorder_status", f"{w['wo_no']}→{nx}")
        s.load_deliveries()
    def print_dn(s):
        r = s.tbl.currentRow()
        if r < 0: return
        w = q1("SELECT * FROM work_orders WHERE id=?", (s.ids[r],))
        c = (q1("SELECT name FROM customers WHERE id=?", (w["customer_id"],))
             if w["customer_id"] else None)
        html = (f"<h1>🚚 {T('Delivery Note')} — {w['wo_no']}</h1>"
                "<table width=100% cellpadding=6 border=1>"
                f"<tr><th align=right>{T('Customer')}</th>"
                f"<th>{c['name'] if c else T('Walk-in')}</th></tr>"
                f"<tr><th align=right>{T('Title')}</th>"
                f"<th>{w['title']}</th></tr>"
                f"<tr><th align=right>{T('Notes')}</th>"
                f"<th>{w['details']}</th></tr>"
                f"<tr><th align=right>{T('Due Date')}</th>"
                f"<th>{w['due']}</th></tr></table>"
                f"<p style='margin-top:50px;'>{T('Delivered by')}: "
                f"..................</p>"
                f"<p>{T('Received by')}: ..................</p>"
                f"<p>{T('Signature')}: ..................</p>")
        do_print(html, a4=True, parent=s)

# ============================== APPOINTMENTS =================================
class AppointmentsPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        top = QHBoxLayout()
        s.day = QDateEdit(QDate.currentDate()); s.day.setCalendarPopup(True)
        s.day.setMinimumHeight(36); s.day.dateChanged.connect(s.load)
        pv = QPushButton("◀"); nx = QPushButton("▶")
        td = QPushButton("📅 " + T("Today")); td.setObjectName("primary")
        pv.clicked.connect(lambda: s.day.setDate(s.day.date().addDays(-1)))
        nx.clicked.connect(lambda: s.day.setDate(s.day.date().addDays(1)))
        td.clicked.connect(lambda: s.day.setDate(QDate.currentDate()))
        nb = QPushButton("➕ " + T("New Appointment"))
        nb.setObjectName("success"); nb.clicked.connect(s.add)
        for w in (pv, s.day, nx, td): top.addWidget(w)
        top.addStretch(1); top.addWidget(nb)
        s.q = make_search(); top.addWidget(s.q); v.addLayout(top)
        s.tbl = QTableWidget(0, 5)
        s.tbl.setHorizontalHeaderLabels([T("Date"), T("Title"),
            T("Customer"), T("Work Order"), T("Status")])
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v.addWidget(s.tbl, 1); s.ids = []
        act = QHBoxLayout()
        dn = QPushButton("✅ " + T("Done")); dn.setObjectName("success")
        dn.clicked.connect(s.done)
        dl = QPushButton("🗑 " + T("Delete")); dl.setObjectName("danger")
        dl.clicked.connect(s.del_appt)
        act.addWidget(dn); act.addWidget(dl); act.addStretch(1)
        v.addLayout(act); s.load()
    def load(s, *_):
        d = s.day.date().toString("yyyy-MM-dd")
        rows = q("""SELECT a.*, c.name cname, w.title wtitle FROM appointments a
                 LEFT JOIN customers c ON c.id=a.customer_id
                 LEFT JOIN work_orders w ON w.id=a.work_order_id
                 WHERE a.ts LIKE ? ORDER BY a.ts""", (d + "%",))
        s.tbl.setRowCount(len(rows)); s.ids = [r["id"] for r in rows]
        for i, r in enumerate(rows):
            for j, val in enumerate([r["ts"][11:16] if r["ts"] else "",
                    r["title"], r["cname"] or "", r["wtitle"] or "",
                    T(r["status"])]):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, it)
        wire_search(s.q, s.tbl)
    def del_appt(s):
        admin_delete(s, s.tbl, s.ids, "appointments", after=s.load)
    def add(s):
        d = QDialog(s); d.setMinimumWidth(520)
        f = QFormLayout(d); f.setSpacing(12)
        ts = QDateTimeEdit(QDateTime.currentDateTime())
        ts.setCalendarPopup(True); ts.setMinimumHeight(38)
        ti = QLineEdit(); ti.setMinimumHeight(38)
        cu = QComboBox(); cu.addItem(T("Walk-in"), None)
        for c in q("SELECT * FROM customers"): cu.addItem(c["name"], c["id"])
        editable_combo(cu)
        wo = QComboBox(); wo.addItem("—", None)
        for w in q("SELECT * FROM work_orders"):
            wo.addItem(w["wo_no"] + " " + w["title"], w["id"])
        editable_combo(wo)
        f.addRow(T("Date"), ts); f.addRow(T("Title"), ti)
        f.addRow(T("Customer"), cu); f.addRow(T("Work Order"), wo)
        ok = QPushButton("💾 " + T("Save")); ok.setObjectName("success")
        ok.setMinimumHeight(42); f.addRow(ok)
        def do():
            x("INSERT INTO appointments(ts,title,customer_id,work_order_id,"
              "status) VALUES(?,?,?,?,'scheduled')",
              (ts.dateTime().toString("yyyy-MM-dd HH:mm"), ti.text(),
               cu.currentData(), wo.currentData()))
            log("appointment_new"); s.load(); d.accept()
        ok.clicked.connect(do); d.exec()
    def done(s):
        r = s.tbl.currentRow()
        if r >= 0:
            x("UPDATE appointments SET status='done' WHERE id=?",
              (s.ids[r],)); s.load()

# ============================== COMMISSIONS ==================================
class CommissionsPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        tb = QTabWidget(); v.addWidget(tb)
        basis_opts = lambda: [("sale", T("Sales")), ("product", T("product")),
                              ("category", T("category"))]
        user_opts = lambda: [("*", T("All"))] + \
            [(u["username"], u["full_name"])
             for u in q("SELECT * FROM users WHERE active=1")]
        s.rules = TableEditor(mw, "commission_rules",
            [("employee","Employee"),("basis","Basis"),("target","Product"),
             ("percent","Percent %"),("fixed","Fixed"),("active","Active")],
            [("employee","Employee","combo",user_opts),
             ("basis","Basis","combo",basis_opts),
             ("target","Product","text",None),
             ("percent","Percent %","num",None),
             ("fixed","Fixed","num",None),("active","Active","check",None)],
            module="commissions")
        tb.addTab(s.rules, "📐 " + T("Rules")); s.rules.refresh()
        cw = QWidget(); cv = QVBoxLayout(cw)
        top = QHBoxLayout()
        s.f = QDateEdit(QDate.currentDate().addDays(-30))
        s.f.setCalendarPopup(True)
        s.t = QDateEdit(QDate.currentDate()); s.t.setCalendarPopup(True)
        cb = QPushButton("🧮 " + T("Compute")); cb.setObjectName("primary")
        cb.clicked.connect(s.compute)
        top.addWidget(QLabel("📅")); top.addWidget(s.f)
        top.addWidget(QLabel("📅")); top.addWidget(s.t); top.addWidget(cb)
        s.q = make_search(); top.addWidget(s.q)
        top.addStretch(1); cv.addLayout(top)
        s.tbl = QTableWidget(0, 4)
        s.tbl.setHorizontalHeaderLabels([T("Date"), T("Employee"),
                                         T("Invoice No"), T("Amount")])
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        cv.addWidget(s.tbl, 1)
        act = QHBoxLayout()
        pb = QPushButton("💵 " + T("Mark Paid")); pb.setObjectName("success")
        pb.clicked.connect(s.mark_paid)
        db = QPushButton("🗑 " + T("Delete")); db.setObjectName("danger")
        db.clicked.connect(s.del_comm)
        act.addWidget(pb); act.addWidget(db); act.addStretch(1)
        cv.addLayout(act)
        tb.addTab(cw, "💰 " + T("Computed Commissions")); s.load()
    def load(s):
        rows = q("""SELECT c.*, s.invoice_no FROM commissions c
                 LEFT JOIN sales s ON s.id=c.sale_id
                 ORDER BY c.id DESC LIMIT 200""")
        s.tbl.setRowCount(len(rows)); s.ids = [r["id"] for r in rows]
        for i, r in enumerate(rows):
            val = (r["ts"], r["employee"], r["invoice_no"] or "—",
                   money(r["amount"]) + (" ✅" if r["paid"] else ""))
            for j, v_ in enumerate(val):
                it = QTableWidgetItem(str(v_))
                it.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, it)
        wire_search(s.q, s.tbl)
    def del_comm(s):
        admin_delete(s, s.tbl, s.ids, "commissions", after=s.load)
    def compute(s):
        f = s.f.date().toString("yyyy-MM-dd")
        t = s.t.date().toString("yyyy-MM-dd") + " 23:59:59"
        n = 0
        sales = q("SELECT * FROM sales WHERE ts BETWEEN ? AND ? "
                  "AND status='completed'", (f, t))
        rules = q("SELECT * FROM commission_rules WHERE active=1")
        for sa in sales:
            for ru in rules:
                emp = sa["username"] if ru["employee"] == "*" \
                      else ru["employee"]
                if ru["employee"] not in ("*", sa["username"]): continue
                if q1("SELECT id FROM commissions WHERE sale_id=? AND "
                      "employee=?", (sa["id"], emp)): continue
                amt = 0.0
                if ru["basis"] == "sale":
                    amt = sa["total"] * ru["percent"] / 100 + ru["fixed"]
                else:
                    items = q("SELECT * FROM sale_items WHERE sale_id=?",
                              (sa["id"],))
                    for it in items:
                        hit = False
                        if ru["basis"] == "product":
                            hit = bool(ru["target"]) and \
                                  ru["target"] in it["name"]
                        elif ru["basis"] == "category":
                            p = q1("SELECT category_id FROM products "
                                   "WHERE id=?", (it["product_id"],))
                            cn = (q1("SELECT name FROM categories WHERE id=?",
                                     (p["category_id"],))
                                  if p and p["category_id"] else None)
                            hit = bool(cn) and ru["target"] == cn["name"]
                        if hit:
                            amt += it["total"] * ru["percent"] / 100 + ru["fixed"]
                if amt > 0:
                    x("INSERT INTO commissions(ts,employee,sale_id,amount) "
                      "VALUES(?,?,?,?)",
                      (nows(), emp, sa["id"], round(amt, 2))); n += 1
        log("commission_compute", f"n={n}")
        QMessageBox.information(s, APP, "🧮 " + str(n)); s.load()
    def mark_paid(s):
        r = s.tbl.currentRow()
        if r >= 0:
            x("UPDATE commissions SET paid=1 WHERE id=?",
              (s.ids[r],)); s.load()

# ============================== USERS ========================================
class UsersPage(QWidget):
    """👤 المستخدمون: إضافة/باسورد/تعديل/تعطيل — شاشة مخصصة تفاعلية"""
    ROLES = [("admin", "🛡 مدير النظام"), ("manager", "👔 مدير"),
             ("cashier", "🧾 كاشير"), ("store", "📦 أمين مخزن"),
             ("account", "🧮 محاسب")]
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        tb = QTabWidget(); v.addWidget(tb)
        uw = QWidget(); uv = QVBoxLayout(uw)
        top = QHBoxLayout()
        nb = QPushButton("➕ " + T("Add") + " " + T("Username"))
        nb.setObjectName("success"); nb.setMinimumHeight(42)
        nb.clicked.connect(s.add_user); top.addWidget(nb)
        ep = QPushButton("🔑 " + T("New Password")); ep.setObjectName("primary")
        ep.setMinimumHeight(42); ep.clicked.connect(s.change_pass)
        top.addWidget(ep)
        ea = QPushButton("✏️ " + T("Edit")); ea.setMinimumHeight(42)
        ea.clicked.connect(s.edit_user); top.addWidget(ea)
        ta = QPushButton("🚫 " + T("Active") + "/" + "🚫")
        ta.setMinimumHeight(42); ta.clicked.connect(s.toggle_active)
        top.addWidget(ta)
        dl = QPushButton("🗑 " + T("Delete")); dl.setObjectName("danger")
        dl.setMinimumHeight(42); dl.clicked.connect(s.del_user)
        top.addWidget(dl)
        top.addStretch(1); uv.addLayout(top)
        s.tbl = QTableWidget(0, 5)
        s.tbl.setHorizontalHeaderLabels([T("Username"), T("Full Name"),
            T("Role"), T("Status"), T("Date")])
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        s.tbl.setAlternatingRowColors(True)
        s.tbl.doubleClicked.connect(lambda *_: s.edit_user())
        uv.addWidget(s.tbl, 1)
        tb.addTab(uw, "👤 " + T("Users"))
        pv = QWidget(); pg = QGridLayout(pv)
        s.MODS = list(MOD_AR.keys())
        roles = ["admin", "manager", "cashier", "store", "account"]
        s.checks = {}
        for j, r in enumerate(roles): pg.addWidget(QLabel("🛡 " + r), 0, j + 1)
        for i, m in enumerate(s.MODS):
            pg.addWidget(QLabel(MOD_AR[m] if LANG == "ar" else m), i + 1, 0)
            for j, r in enumerate(roles):
                cr = q1("SELECT allowed FROM role_permissions WHERE role=? "
                        "AND module=?", (r, m))
                cb = QCheckBox(); cb.setChecked(bool(cr and cr["allowed"]))
                if r == "admin":
                    cb.setChecked(True); cb.setEnabled(False)
                s.checks[(r, m)] = cb; pg.addWidget(cb, i + 1, j + 1)
        pb = QPushButton("💾 " + T("Save") + " " + T("Permissions"))
        pb.setObjectName("success"); pb.setMinimumHeight(42)
        pb.clicked.connect(s.save_perms)
        pg.addWidget(pb, len(s.MODS) + 1, 0, 1, 6)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(pv)
        wrap = QWidget(); wv = QVBoxLayout(wrap); wv.addWidget(sc)
        tb.addTab(wrap, "🛡 " + T("Permissions"))
        logw = QWidget(); lv2 = QVBoxLayout(logw)
        clr = QPushButton("🧹 " + T("Activity Log") + " — admin")
        clr.setObjectName("danger"); clr.clicked.connect(s.clear_log)
        lv2.addWidget(clr)
        s.log = TableEditor(mw, "activity_log",
            [("ts","Date"),("username","Username"),("action","Module"),
             ("details","Details")], [], ro=True,
            search_cols=["username","action","details"], order="id DESC")
        lv2.addWidget(s.log)
        tb.addTab(logw, "📜 " + T("Activity Log")); s.log.refresh()
        s.load()
    def _cur(s):
        r = s.tbl.currentRow()
        return (s.rows[r] if hasattr(s, "rows") and 0 <= r < len(s.rows)
                else None)
    def load(s, keep=None):
        rows = q("SELECT * FROM users ORDER BY id")
        s.rows = rows
        s.tbl.setRowCount(len(rows))
        role_map = dict(s.ROLES)
        for i, r in enumerate(rows):
            status = ("🟢 " + T("Active") if r["active"]
                      else "🔴 " + ("معطل" if LANG == "ar" else "disabled"))
            for j, val in enumerate([r["username"], r["full_name"] or "",
                    role_map.get(r["role"], r["role"]), status,
                    (r["created_at"] or "")[:19]]):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignCenter)
                if j == 3 and not r["active"]:
                    it.setForeground(QBrush(QColor("#ef4444")))
                s.tbl.setItem(i, j, it)
        if keep is not None:
            for i, r in enumerate(s.rows):
                if r["id"] == keep: s.tbl.selectRow(i); break
    def _role_dialog(s, cur_role=None, cur_name="", cur_user=""):
        d = QDialog(s); d.setMinimumWidth(500)
        f = QFormLayout(d); f.setSpacing(12)
        un = QLineEdit(cur_user); un.setMinimumHeight(40)
        fn = QLineEdit(cur_name); fn.setMinimumHeight(40)
        rl = QComboBox(); rl.setMinimumHeight(40)
        for rv, rl_ in s.ROLES: rl.addItem(rl_, rv)
        if cur_role:
            ix = rl.findData(cur_role)
            if ix >= 0: rl.setCurrentIndex(ix)
        pw = QLineEdit(); pw.setEchoMode(QLineEdit.Password)
        pw.setMinimumHeight(40)
        if cur_role: pw.setPlaceholderText(
            "سيبه فاضي للاحتفاظ بالقديم" if LANG == "ar"
            else "Leave blank to keep old")
        f.addRow("👤 " + T("Username"), un)
        f.addRow("🏷 " + T("Full Name"), fn)
        f.addRow("🛡 " + T("Role"), rl)
        f.addRow("🔑 " + T("Password"), pw)
        hb = QHBoxLayout()
        ok = QPushButton("💾 " + T("Save")); ok.setObjectName("success")
        ok.setMinimumHeight(44)
        ca = QPushButton(T("Cancel")); ca.setMinimumHeight(42)
        hb.addWidget(ok); hb.addWidget(ca); f.addRow(hb)
        ca.clicked.connect(d.reject)
        d.execed = [False]
        def do():
            if not un.text().strip():
                QMessageBox.warning(d, APP, "👤 اكتب اسم المستخدم"); return
            d.execed[0] = True; d.accept()
        ok.clicked.connect(do); un.returnPressed.connect(do)
        d.exec()
        return (d.execed[0], un.text().strip(), fn.text().strip(),
                rl.currentData(), pw.text())
    def add_user(s):
        if not (allowed("users") or is_admin()):
            QMessageBox.warning(s, APP, "🚫 " + T("No permission")); return
        okd, un, fn, role, pw = s._role_dialog()
        if not okd: return
        if q1("SELECT id FROM users WHERE username=?", (un,)):
            QMessageBox.warning(s, APP, "⚠️ اسم المستخدم موجود بالفعل"); return
        if not pw:
            QMessageBox.warning(s, APP, "🔑 اكتب باسورد للمستخدم الجديد"); return
        x("INSERT INTO users(username,password,full_name,role,active,"
          "created_at) VALUES(?,?,?,?,1,?)",
          (un, hashlib.sha256(pw.encode()).hexdigest(), fn or un,
           role or "cashier", nows()))
        log("user_add", un); s.load()
        s.tbl.selectRow(s.tbl.rowCount() - 1)
        QMessageBox.information(s, APP, "✅ تمت إضافة المستخدم: " + un)
    def change_pass(s):
        u = s._cur()
        if not u:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        d = QDialog(s); d.setMinimumWidth(440)
        f = QFormLayout(d); f.setSpacing(12)
        lb = QLabel("👤 " + u["username"] + " — " + (u["full_name"] or ""))
        lb.setStyleSheet("font-weight:800;font-size:15px;")
        p1 = QLineEdit(); p1.setEchoMode(QLineEdit.Password)
        p1.setMinimumHeight(40)
        p2 = QLineEdit(); p2.setEchoMode(QLineEdit.Password)
        p2.setMinimumHeight(40)
        f.addRow(lb); f.addRow("🔑 " + T("New Password"), p1)
        f.addRow("🔁 " + ("تأكيد الباسورد" if LANG == "ar" else "Confirm"), p2)
        hb = QHBoxLayout()
        ok = QPushButton("💾 " + T("Save")); ok.setObjectName("success")
        ok.setMinimumHeight(44)
        ca = QPushButton(T("Cancel")); ca.setMinimumHeight(42)
        hb.addWidget(ok); hb.addWidget(ca); f.addRow(hb)
        ca.clicked.connect(d.reject)
        d.ok = [False]
        def do():
            if not p1.text():
                QMessageBox.warning(d, APP, "🔑 اكتب الباسورد الجديد"); return
            if p1.text() != p2.text():
                QMessageBox.warning(d, APP, "⚠️ الباسورد غير متطابق"); return
            d.ok[0] = True; d.accept()
        ok.clicked.connect(do); p2.returnPressed.connect(do)
        d.exec()
        if not d.ok[0]: return
        x("UPDATE users SET password=? WHERE id=?",
          (hashlib.sha256(p1.text().encode()).hexdigest(), u["id"]))
        log("user_password", u["username"])
        QMessageBox.information(s, APP, "✅ " + T("User updated")
                                + " — 🔑 " + u["username"])
    def edit_user(s):
        u = s._cur()
        if not u:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        okd, un, fn, role, pw = s._role_dialog(
            cur_role=u["role"], cur_name=u["full_name"] or "",
            cur_user=u["username"])
        if not okd: return
        if un != u["username"] and q1("SELECT id FROM users WHERE username=?",
                                      (un,)):
            QMessageBox.warning(s, APP, "⚠️ اسم المستخدم موجود بالفعل"); return
        if un == "admin" and u["username"] == "admin" and role != "admin":
            QMessageBox.warning(s, APP, "🚫 admin يبقى admin"); return
        x("UPDATE users SET username=?,full_name=?,role=? WHERE id=?",
          (un, fn or un, role or u["role"], u["id"]))
        if pw:
            x("UPDATE users SET password=? WHERE id=?",
              (hashlib.sha256(pw.encode()).hexdigest(), u["id"]))
        log("user_edit", un); s.load(keep=u["id"])
        QMessageBox.information(s, APP, "✅ " + T("User updated") + ": " + un)
    def toggle_active(s):
        u = s._cur()
        if not u:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        if u["username"] == "admin" and u["active"]:
            QMessageBox.warning(s, APP, "🚫 لا تعطيل للادمن الرئيسي"); return
        nv = 0 if u["active"] else 1
        if nv == 0 and u["username"] == CUR_USER["username"]:
            QMessageBox.warning(s, APP, "🚫 متعطلش نفسك"); return
        x("UPDATE users SET active=? WHERE id=?", (nv, u["id"]))
        log("user_toggle", f"{u['username']}→{nv}"); s.load(keep=u["id"])
    def del_user(s):
        if not (allowed("users") or is_admin()):
            QMessageBox.warning(s, APP, "🚫 " + T("No permission")); return
        u = s._cur()
        if not u:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        if u["username"] == "admin":
            QMessageBox.warning(s, APP, "🚫 مفيش حذف للادمن الرئيسي"); return
        if u["username"] == CUR_USER["username"]:
            QMessageBox.warning(s, APP, "🚫 متحذفش نفسك"); return
        if not admin_password_check(s): return
        if QMessageBox.question(s, APP, T("Are you sure?") + " — "
                                + u["username"]) != QMessageBox.Yes: return
        trash_put("users", u["id"])
        x("DELETE FROM users WHERE id=?", (u["id"],))
        log("user_del", u["username"]); s.load()
    def clear_log(s):
        if not is_admin():
            QMessageBox.warning(s, APP, "🚫 " + T("No permission")); return
        if QMessageBox.question(s, APP, T("Are you sure?")) == QMessageBox.Yes:
            x("DELETE FROM activity_log"); log("log_cleared"); s.log.refresh()
    def save_perms(s):
        for (r, m), cb in s.checks.items():
            if r == "admin": continue
            x("INSERT INTO role_permissions(role,module,allowed) VALUES(?,?,?) "
              "ON CONFLICT(role,module) DO UPDATE SET allowed=excluded.allowed",
              (r, m, 1 if cb.isChecked() else 0))
        log("permissions_save")
        QMessageBox.information(s, APP, "✅ " + T("Saved"))

# ============================== REPORTS ======================================
class ReportsPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        top = QHBoxLayout()
        s.kind = QComboBox(); s.kind.setMinimumHeight(36)
        for k in ["Sales by Day", "Best Sellers", "Profit by Product",
                  "Profit & Loss", "Inventory Valuation",
                  "Employee Performance", "Cash Flow", "Debts report"]:
            s.kind.addItem("📈 " + T(k), k)
        s.f = QDateEdit(QDate.currentDate().addDays(-30))
        s.f.setCalendarPopup(True)
        s.t = QDateEdit(QDate.currentDate()); s.t.setCalendarPopup(True)
        g = QPushButton("🔍 " + T("Generate")); g.setObjectName("primary")
        g.clicked.connect(s.run)
        e = QPushButton("📤 " + T("Export CSV")); e.clicked.connect(s.csv)
        pr = QPushButton("🖨 " + T("Print")); pr.setObjectName("success")
        pr.clicked.connect(s.print_rep)
        pdfb = QPushButton("📄 PDF"); pdfb.setObjectName("warn")
        pdfb.clicked.connect(s.pdf)
        for w in (s.kind, s.f, s.t, g, e, pr, pdfb): top.addWidget(w)
        v.addLayout(top)
        s.tbl = QTableWidget(); s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v.addWidget(s.tbl, 1)
        s.summ = QLabel(""); s.summ.setObjectName("h1")
        s.summ.setAlignment(Qt.AlignCenter); v.addWidget(s.summ)
        s.headers = []; s.rows = []
    def run(s):
        f = s.f.date().toString("yyyy-MM-dd")
        t = s.t.date().toString("yyyy-MM-dd") + " 23:59:59"
        kind = s.kind.currentData(); s.headers = []; s.rows = []
        if kind == "Sales by Day":
            rows = q("""SELECT date(ts) d, COUNT(*) n, SUM(total) tot,
                     SUM(tax) tax, AVG(total) avg FROM sales WHERE ts BETWEEN ?
                     AND ? AND status='completed' GROUP BY date(ts)
                     ORDER BY d DESC""", (f, t))
            s.headers = [T("Date"), T("Count"), T("Grand Total"), T("Tax"),
                         T("Amount")]
            s.rows = [[r["d"], r["n"], money(r["tot"]), money(r["tax"]),
                       money(r["avg"])] for r in rows]
            s.summ.setText(f"💰 {T('Grand Total')}: "
                           f"{money(sum(r['tot'] for r in rows))} {cur()}")
        elif kind == "Best Sellers":
            rows = q("""SELECT si.name, SUM(si.qty) qt, SUM(si.total) tot
                     FROM sale_items si JOIN sales s ON s.id=si.sale_id
                     WHERE s.ts BETWEEN ? AND ? AND s.status='completed'
                     GROUP BY si.name ORDER BY tot DESC LIMIT 50""", (f, t))
            s.headers = [T("Product"), T("Qty"), T("Grand Total")]
            s.rows = [[r["name"], f"{r['qt']:g}", money(r["tot"])] for r in rows]
            s.summ.setText("")
        elif kind == "Profit by Product":
            rows = q("""SELECT si.name nm, SUM(si.qty) qt, SUM(si.total) rev,
                     SUM(si.qty*si.cost) cst FROM sale_items si
                     JOIN sales s ON s.id=si.sale_id WHERE s.ts BETWEEN ? AND ?
                     AND s.status='completed' GROUP BY si.name
                     ORDER BY (SUM(si.total)-SUM(si.qty*si.cost)) DESC""", (f, t))
            s.headers = [T("Product"), T("Qty"), T("Grand Total"), T("Cost"),
                         T("Net Profit")]
            s.rows = [[r["nm"], f"{r['qt']:g}", money(r["rev"]),
                       money(r["cst"]), money(r["rev"] - r["cst"])]
                      for r in rows]
            s.summ.setText("💵 " + T("Net Profit") + ": "
                           + money(sum(r["rev"] - r["cst"] for r in rows))
                           + " " + cur())
        elif kind == "Profit & Loss":
            sa = q1("SELECT IFNULL(SUM(total),0) t, IFNULL(SUM(tax),0) x "
                    "FROM sales WHERE ts BETWEEN ? AND ? AND status='completed'",
                    (f, t))
            co = q1("""SELECT IFNULL(SUM(si.qty*si.cost),0) v FROM sale_items si
                    JOIN sales s ON s.id=si.sale_id WHERE s.ts BETWEEN ? AND ?
                    AND s.status='completed'""", (f, t))
            ex = q1("SELECT IFNULL(SUM(amount),0) v FROM expenses "
                    "WHERE ts BETWEEN ? AND ?", (f, t))
            gross = sa["t"] - sa["x"] - co["v"]; net = gross - ex["v"]
            s.headers = [T("Description"), T("Amount")]
            s.rows = [[T("Sales"), money(sa["t"])], [T("Tax"), money(sa["x"])],
                      [T("Cost"), money(co["v"])],
                      [T("Gross Profit"), money(gross)],
                      [T("Expenses"), money(ex["v"])],
                      [T("Net Profit"), money(net)]]
            s.summ.setText(f"💵 {T('Net Profit')}: {money(net)} {cur()}")
        elif kind == "Inventory Valuation":
            rows = q("""SELECT p.barcode,p.name,p.name_ar,p.cost,p.price,
                     IFNULL((SELECT SUM(qty) FROM stock WHERE product_id=p.id),0)
                     qty FROM products p WHERE p.active=1
                     ORDER BY qty*p.cost DESC""")
            s.headers = [T("Code"), T("Product Name"), T("Qty"), T("Cost"),
                         T("Price"), T("Value")]
            s.rows = [[r["barcode"], disp_name(r), f"{r['qty']:g}",
                       money(r["cost"]), money(r["price"]),
                       money(r["qty"] * r["cost"])] for r in rows]
            s.summ.setText(f"📦 {T('Inventory Valuation')}: "
                           f"{money(sum(r['qty']*r['cost'] for r in rows))} "
                           f"{cur()}")
        elif kind == "Employee Performance":
            rows = q("""SELECT username, COUNT(*) n, SUM(total) tot FROM sales
                     WHERE ts BETWEEN ? AND ? AND status='completed'
                     GROUP BY username ORDER BY tot DESC""", (f, t))
            s.headers = [T("Employee"), T("Count"), T("Grand Total")]
            s.rows = [[r["username"], r["n"], money(r["tot"])] for r in rows]
            s.summ.setText("")
        elif kind == "Cash Flow":
            rows = q("SELECT * FROM treasury WHERE ts BETWEEN ? AND ? "
                     "ORDER BY id DESC", (f, t))
            s.headers = [T("Date"), T("Account"), T("In") + "/" + T("Out"),
                         T("Description"), T("Ref"), T("Username"), T("Amount")]
            s.rows = [[r["ts"],
                       T("Drawer") if r["account"] == "drawer" else T("Vault"),
                       T("In") if r["direction"] == "in" else T("Out"),
                       r["reason"] or "", r["ref"] or "", r["username"] or "",
                       money(r["amount"])] for r in rows]
            db_ = q1("SELECT IFNULL(SUM(CASE WHEN direction='in' THEN amount "
                     "ELSE -amount END),0) v FROM treasury "
                     "WHERE account='drawer'")["v"]
            vb_ = q1("SELECT IFNULL(SUM(CASE WHEN direction='in' THEN amount "
                     "ELSE -amount END),0) v FROM treasury "
                     "WHERE account='vault'")["v"]
            s.summ.setText(f"🧰 {T('Drawer')}: {money(db_)} {cur()}   |   "
                           f"🏦 {T('Vault')}: {money(vb_)} {cur()}")
        elif kind == "Debts report":
            rows_c = q("SELECT name, phone, balance FROM customers "
                       "WHERE balance>0.001 ORDER BY balance DESC")
            rows_s = q("SELECT name, phone, balance FROM suppliers "
                       "WHERE balance>0.001 ORDER BY balance DESC")
            s.headers = [T("Type"), T("Product Name"), T("Phone"), T("Balance")]
            s.rows = ([[T("Customer debts"), r["name"], r["phone"] or "—",
                        money(r["balance"])] for r in rows_c]
                      + [[T("Supplier debts"), r["name"], r["phone"] or "—",
                          money(r["balance"])] for r in rows_s])
            tot_ = (sum(r["balance"] for r in rows_c)
                    + sum(r["balance"] for r in rows_s))
            s.summ.setText("💰 " + T("Debts report") + ": "
                           + money(tot_) + " " + cur())
        s.tbl.clear(); s.tbl.setColumnCount(len(s.headers))
        s.tbl.setRowCount(len(s.rows))
        s.tbl.setHorizontalHeaderLabels(s.headers)
        for i, r in enumerate(s.rows):
            for j, val in enumerate(r):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, it)
    def csv(s): export_csv(s.headers, s.rows)
    def _html(s):
        html = (f"<h1>📈 {s.kind.currentText()}</h1><p>"
                f"{s.f.date().toString('yyyy-MM-dd')} → "
                f"{s.t.date().toString('yyyy-MM-dd')}</p>"
                "<table width=100% cellpadding=6 border=1><tr>"
                + "".join(f"<th>{h}</th>" for h in s.headers) + "</tr>")
        for r in s.rows:
            html += "<tr>" + "".join(
                f"<td align=center>{c}</td>" for c in r) + "</tr>"
        return html + "</table><h3>" + s.summ.text() + "</h3>"
    def print_rep(s):
        if not s.rows:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        do_print(s._html(), a4=True, parent=s)
    def pdf(s):
        if not s.rows:
            QMessageBox.information(s, APP, T("Nothing selected")); return
        path, _ = QFileDialog.getSaveFileName(s, "PDF",
            f"{s.kind.currentData()}_{today()}.pdf", "PDF (*.pdf)")
        if not path: return
        do_print(s._html(), a4=True, pdf=path)
        QMessageBox.information(s, APP, T("Exported"))

# ============================== SETTINGS =====================================
class SettingsPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        card = QFrame(); card.setObjectName("card")
        g = QFormLayout(card); g.setSpacing(12)
        s.f = {}
        for key, lab in [("company","Company Name"),
                         ("company_ar","Company Name (AR)"),
                         ("tax_no","Tax Number"),("phone","Phone"),
                         ("address","Address"),("currency","Currency"),
                         ("currency_ar","Currency (AR)"),
                         ("receipt_footer","Receipt Footer")]:
            w = QLineEdit(SET.get(key, "")); s.f[key] = w; g.addRow(T(lab), w)
        s.vat = QDoubleSpinBox(); s.vat.setMaximum(100)
        s.vat.setValue(float(SET.get("vat", 15))); g.addRow(T("VAT %"), s.vat)
        s.prt = QLineEdit(SET.get("printer_name", ""))
        s.prt.setPlaceholderText(T("Printer name")); s.prt.setMinimumHeight(38)
        g.addRow("🖨 " + T("Printer name"), s.prt)
        s.dpr = QCheckBox(T("Direct print"))
        s.dpr.setChecked(SET.get("direct_print") == "1")
        g.addRow(s.dpr)
        s.alock = QSpinBox(); s.alock.setRange(0, 240)
        s.alock.setValue(int(float(SET.get("autolock_min", 0))))
        s.alock.setMinimumHeight(38); s.alock.setAlignment(Qt.AlignCenter)
        g.addRow("🔒 " + T("Auto-lock minutes"), s.alock)
        b = QPushButton("💾 " + T("Save")); b.setObjectName("success")
        b.setMinimumHeight(42); b.clicked.connect(s.save); g.addRow(b)
        v.addWidget(card)
        card2 = QFrame(); card2.setObjectName("card"); h = QHBoxLayout(card2)
        bk = QPushButton("💾 " + T("Backup Database"))
        bk.setObjectName("primary"); bk.clicked.connect(s.backup)
        h.addWidget(bk)
        rs = QPushButton("♻️ " + T("Restore Database"))
        rs.setObjectName("danger"); rs.clicked.connect(s.restore)
        h.addWidget(rs)
        h.addStretch(1); v.addWidget(card2)
        card3 = QFrame(); card3.setObjectName("card"); h3 = QHBoxLayout(card3)
        fr = QPushButton("🔴 " + T("Factory Reset") + " — admin")
        fr.setObjectName("danger"); fr.setMinimumHeight(48)
        fr.clicked.connect(s.factory_reset); h3.addWidget(fr)
        h3.addStretch(1); v.addWidget(card3); v.addStretch(1)
    def save(s):
        for k, w in s.f.items():
            x("INSERT INTO settings(key,value) VALUES(?,?) "
              "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, w.text()))
        for k_, w_ in (("vat", str(s.vat.value())),
                       ("printer_name", s.prt.text().strip()),
                       ("direct_print", "1" if s.dpr.isChecked() else "0"),
                       ("autolock_min", str(s.alock.value()))):
            x("INSERT INTO settings(key,value) VALUES(?,?) "
              "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k_, w_))
        load_settings(); log("settings_save")
        QMessageBox.information(s, APP, T("Saved"))
    def backup(s):
        path, _ = QFileDialog.getSaveFileName(s, T("Backup Database"),
            f"backup_{today()}.db", "DB (*.db)")
        if not path: return
        conn.commit(); shutil.copy(DB, path); log("backup", path)
        QMessageBox.information(s, APP, T("Backup saved"))
    def restore(s):
        path, _ = QFileDialog.getOpenFileName(s, T("Restore Database"), DIR,
                                              "DB (*.db)")
        if not path: return
        if QMessageBox.question(s, APP, T("Are you sure?")) == QMessageBox.Yes:
            conn.commit(); conn.close(); shutil.copy(path, DB)
            QMessageBox.information(s, APP, T("Restored — restart required"))
            QProcess.startDetached(sys.executable,
                                   [os.path.abspath(__file__)])
            QApplication.quit()
    def factory_reset(s):
        _ar = LANG == "ar"
        if not is_admin():
            QMessageBox.warning(s, APP, "🚫 " + T("No permission")); return
        d = QDialog(s); d.setWindowTitle("🔴 " + T("Factory Reset"))
        d.setMinimumWidth(500)
        v = QVBoxLayout(d); v.setSpacing(12)
        warn = QLabel("⚠️ " + (
            "عملية خطيرة! سيتم مسح كل البيانات نهائيًا: الفواتير، المنتجات، "
            "العملاء، الموردين، المصروفات، سجل الصندوق، والمستخدمين — "
            "وسيعود البرنامج كأنه جديد تمامًا. لا يمكن التراجع!" if _ar else
            "DANGER! ALL data will be permanently erased. Cannot be undone!"))
        warn.setWordWrap(True)
        warn.setStyleSheet("color:#ef4444;font-weight:800;font-size:14px;"
                           "background:rgba(239,68,68,.08);border-radius:10px;"
                           "padding:12px;")
        v.addWidget(warn)
        f = QFormLayout()
        pw = QLineEdit(); pw.setEchoMode(QLineEdit.Password)
        pw.setMinimumHeight(42); pw.setPlaceholderText("🔑 " +
                                                       T("Special password"))
        f.addRow("🔑 " + T("Special password"), pw)
        v.addLayout(f)
        hb = QHBoxLayout()
        ok = QPushButton("🔴 " + T("Factory Reset")); ok.setObjectName("danger")
        ok.setMinimumHeight(46)
        ca = QPushButton(T("Cancel")); ca.setMinimumHeight(42)
        hb.addWidget(ok); hb.addWidget(ca); v.addLayout(hb)
        ca.clicked.connect(d.reject)
        def go():
            if pw.text() != RESET_PASSWORD:
                QMessageBox.warning(d, APP, "❌ " +
                                    T("Wrong special password"))
                pw.clear(); return
            d.accept()
        ok.clicked.connect(go); pw.returnPressed.connect(go)
        if d.exec() != QDialog.Accepted: return
        if QMessageBox.question(s, APP, "⚠️ " + (
                "تأكيد أخير: مسح كل شيء والبدء من جديد؟"
                if _ar else "Final confirm: erase everything?")) \
                != QMessageBox.Yes: return
        if QMessageBox.question(s, APP, "💾 " + (
                "حفظ نسخة احتياطية قبل المسح؟ (مُستحسن)" if _ar
                else "Save a backup first?")) == QMessageBox.Yes:
            path, _ = QFileDialog.getSaveFileName(s, T("Backup Database"),
                "backup_before_reset_" + today() + ".db", "DB (*.db)")
            if path:
                conn.commit(); shutil.copy(DB, path)
        conn.commit(); conn.close()
        for f_ in (DB, DB + "-wal", DB + "-shm"):
            try: os.remove(f_)
            except Exception: pass
        QProcess.startDetached(sys.executable, [os.path.abspath(__file__)])
        QApplication.quit()

# ============================== TRASH ========================================
class TrashPage(QWidget):
    """♻️ سلة المحذوفات — أدمن فقط"""
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        top = QHBoxLayout()
        top.addWidget(QLabel("♻️ " + T("Trash")))
        top.addStretch(1)
        rs = QPushButton("♻️ " + T("Restore")); rs.setObjectName("success")
        rs.setMinimumHeight(42); rs.clicked.connect(s.restore)
        top.addWidget(rs)
        pg = QPushButton("🔥 " + T("Purge")); pg.setObjectName("danger")
        pg.setMinimumHeight(42); pg.clicked.connect(s.purge); top.addWidget(pg)
        em = QPushButton("🧹 " + T("Empty Trash")); em.setObjectName("warn")
        em.setMinimumHeight(42); em.clicked.connect(s.empty); top.addWidget(em)
        v.addLayout(top)
        s.q = make_search(); v.addWidget(s.q)
        s.tbl = QTableWidget(0, 5)
        s.tbl.setHorizontalHeaderLabels([T("Date"), T("Username"),
            T("Type"), "ID", T("Details")])
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v.addWidget(s.tbl, 1)
        s.ids = []; s.refresh()
    def _type_name(s, tbl):
        return {"sales": "🧾 " + T("Sales & Invoices"),
                "purchases": "🚚 " + T("Purchases"),
                "quotations": "📑 " + T("Quotations"),
                "products": "📦 " + T("Product"),
                "customers": "👤 " + T("Customers"),
                "suppliers": "🏭 " + T("Suppliers"),
                "expenses": "🧮 " + T("Expenses"),
                "transfers": "🔄 " + T("Transfers"),
                "locations": "🏬 " + T("Location"),
                "users": "👤 " + T("Users"),
                "appointments": "📅 " + T("Appointments"),
                "shifts": "🕒 " + T("Shifts"),
                "work_orders": "🛠 " + T("Work Orders"),
                "categories": "🗂 " + T("Categories")}.get(tbl, tbl)
    def _details(s, rec):
        try: d = json.loads(rec["data"])
        except Exception: return str(rec["rid"])
        for k in ("invoice_no", "ref_no", "quote_no", "name",
                  "full_name", "title", "category"):
            if d.get(k):
                v_ = str(d[k])
                if rec["tbl"] in ("sales", "purchases", "quotations") \
                        and d.get("total") is not None:
                    v_ += " — " + money(d.get("total", 0))
                return v_
        return str(rec["rid"])
    def refresh(s):
        rows = q("SELECT * FROM trash ORDER BY id DESC LIMIT 500")
        s.tbl.setRowCount(len(rows)); s.ids = [r["id"] for r in rows]
        for i, r in enumerate(rows):
            vals = [r["ts"], r["username"], s._type_name(r["tbl"]),
                    str(r["rid"]), s._details(r)]
            for j, val in enumerate(vals):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, it)
        wire_search(s.q, s.tbl)
    def restore(s):
        if not is_admin():
            QMessageBox.warning(s, APP, "🚫 " + T("No permission")); return
        r = s.tbl.currentRow()
        if not (0 <= r < len(s.ids)):
            QMessageBox.information(s, APP, T("Nothing selected")); return
        rid = trash_restore(s.ids[r])
        if rid:
            log("trash_restore", str(rid))
            QMessageBox.information(s, APP, "♻️ " + T("Saved"))
            s.refresh()
            try: s.mw.broadcast_all()
            except Exception: pass
    def purge(s):
        if not is_admin(): return
        r = s.tbl.currentRow()
        if not (0 <= r < len(s.ids)):
            QMessageBox.information(s, APP, T("Nothing selected")); return
        if not admin_password_check(s): return
        if QMessageBox.question(s, APP, "🔥 " + T("Are you sure?")) \
                != QMessageBox.Yes: return
        x("DELETE FROM trash WHERE id=?", (s.ids[r],))
        log("trash_purge", str(s.ids[r])); s.refresh()
    def empty(s):
        if not is_admin(): return
        if not admin_password_check(s): return
        if QMessageBox.question(s, APP, "🧹 " + T("Are you sure?") + " — "
                                + T("Empty Trash") + "?") \
                != QMessageBox.Yes: return
        x("DELETE FROM trash"); log("trash_empty"); s.refresh()

# ============================== MAIN WINDOW ==================================
NAV = [("Operations", ["dash","pos","sales","quotes","einvoice","shifts","cash"]),
       ("Management", ["inventory","locations","purchases","suppliers",
                       "customers","offers","workorders","appointments",
                       "commissions","expenses","reports"]),
       ("System", ["users","settings","trash"])]
PAGES = {
 "dash": ("Dashboard","نظرة عامة على أداء المتجر","Dashboard overview"),
 "pos": ("POS Screen","بيع سريع بالباركود أو البحث","Fast selling"),
 "sales": ("Sales & Invoices","الفواتير والمرتجعات","Invoices & returns"),
 "quotes": ("Quotations","عروض أسعار قابلة للتحويل","Quotations"),
 "einvoice": ("E-Invoicing","فوترة إلكترونية مع QR","E-invoicing with QR"),
 "shifts": ("Shifts","جرد الورديات والفرق النقدية","Shift inventory"),
 "inventory": ("Inventory","الأصناف والأقسام والأرصدة","Products & stock"),
 "locations": ("Branches & Warehouses","الفروع والمخازن والتحويلات",
               "Branches & transfers"),
 "purchases": ("Purchases","المشتريات والموردون","Purchases & suppliers"),
 "suppliers": ("Suppliers","الموردون والمدفوعات","Suppliers"),
 "customers": ("Customers","العملاء والنقاط والحسابات","Customers"),
 "offers": ("Offers & Discounts","العروض والكوبونات والنقاطي",
            "Offers & loyalty"),
 "workorders": ("Work Orders","أوامر التشغيل والتسليم","Work & delivery"),
 "appointments": ("Appointments","مواعيد مرتبطة بأوامر التشغيل",
                  "Appointments"),
 "commissions": ("Commissions","عمولات الموظفين","Commissions"),
 "expenses": ("Expenses","مصروفات من الدرج أو الخزنة","Expenses"),
 "reports": ("Reports","تقارير شاملة وتصدير","Reports"),
 "users": ("Users","المستخدمون والصلاحيات","Users & permissions"),
 "settings": ("Settings","إعدادات النظام","Settings"),
 "cash": ("Cash & Treasury","الدرج والخزنة والمعاملات","Drawer & vault"),
 "trash": ("Trash","سلة المحذوفات والاسترجاع","Trash & restore")}

class MainWindow(QMainWindow):
    def eventFilter(s, obj, ev):
        try:
            if ev.type() in (ev.Type.MouseMove, ev.Type.MouseButtonPress,
                             ev.Type.KeyPress, ev.Type.Wheel):
                s._idle = 0
        except Exception: pass
        return False
    def __init__(s):
        super().__init__(); sync_app_name()
        s.setWindowTitle(APP); s.resize(1450, 880)
        try:
            if os.path.exists(LOGO_FILE): s.setWindowIcon(QIcon(LOGO_FILE))
        except Exception: pass
        root = QWidget(); h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)
        side = QFrame(); side.setObjectName("side"); side.setFixedWidth(250)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(10, 16, 10, 10); sv.setSpacing(2)
        lg = QHBoxLayout()
        logo = QLabel(); logo.setAlignment(Qt.AlignCenter)
        _pm = logo_pixmap(56)
        if _pm: logo.setPixmap(_pm)
        else:
            logo.setText("🛒"); logo.setStyleSheet("font-size:34px;")
        logo.setStyleSheet(logo.styleSheet() + "background:"
            + ("#16283f;" if SET.get("theme") == "dark" else "#f8fafc;")
            + "border-radius:16px;padding:6px;")
        lt = QLabel(APP)
        if LANG == "ar":
            lt.setStyleSheet("font-family:Cairo,Segoe UI;font-size:20px;"
                             "font-weight:900;color:"
                             + ("#ffffff;" if SET.get("theme") == "dark"
                                else "#0f172a;"))
        else:
            lt.setStyleSheet("font-family:Segoe UI,Verdana;font-size:17px;"
                             "font-weight:800;font-style:italic;color:"
                             + ("#ffffff;" if SET.get("theme") == "dark"
                                else "#0f172a;")
                             + ";letter-spacing:1px;")
        lb = QLabel(brand_by())
        lb.setStyleSheet("font-family:Segoe UI;font-size:10px;"
                         "font-weight:700;color:"
                         + ("#5b7290;" if SET.get("theme") == "dark"
                            else "#8a94a6;"))
        lb.setWordWrap(True)
        lg.addWidget(logo)
        ltb = QVBoxLayout(); ltb.addWidget(lt); ltb.addWidget(lb)
        lg.addLayout(ltb); lg.addStretch(1)
        sv.addLayout(lg); sv.addSpacing(10)
        s.navs = {}
        for group, keys in NAV:
            gl = QLabel(T(group)); sv.addWidget(gl)
            for k in keys:
                if not allowed(k): continue
                b = QPushButton(f"  {IC.get(k,'•')}  {T(PAGES[k][0])}")
                b.setCheckable(True); b.setCursor(Qt.PointingHandCursor)
                b.clicked.connect(lambda _, k_=k: s.goto(k_))
                sv.addWidget(b); s.navs[k] = b
        sv.addStretch(1)
        ub = QFrame()
        ub.setStyleSheet("border-radius:12px;"
            + ("background:#16283f;" if SET.get("theme") == "dark"
               else "background:#f1f5f9;border:1px solid #e2e8f0;"))
        ul = QVBoxLayout(ub)
        un = QLabel("👤 " + CUR_USER["full_name"])
        un.setStyleSheet("font-weight:700;color:"
                         + ("#ffffff;" if SET.get("theme") == "dark"
                            else "#0f172a;"))
        ur = QLabel(CUR_USER["role"])
        ur.setStyleSheet("color:" + ("#93a4bd;" if SET.get("theme") == "dark"
                                     else "#64748b;"))
        lo = QPushButton("🚪 Logout")
        lo.setStyleSheet(("color:#f87171;" if SET.get("theme") == "dark"
                          else "color:#dc2626;")
                         + "background:transparent;border:none;"
                           "font-weight:700;")
        lo.clicked.connect(s.logout)
        ul.addWidget(un); ul.addWidget(ur); ul.addWidget(lo)
        sv.addWidget(ub)
        main = QWidget(); mv = QVBoxLayout(main)
        mv.setContentsMargins(0, 0, 0, 0); mv.setSpacing(0)
        head = QFrame(); head.setObjectName("head"); head.setFixedHeight(76)
        hh = QHBoxLayout(head); hh.setContentsMargins(18, 8, 18, 8)
        tbv = QVBoxLayout()
        s.title = QLabel(""); s.title.setObjectName("h1")
        s.sub = QLabel(""); s.sub.setObjectName("h2")
        tbv.addWidget(s.title); tbv.addWidget(s.sub)
        hh.addLayout(tbv); hh.addStretch(1)
        s.clock = QLabel(""); hh.addWidget(s.clock)
        lang = QPushButton("🌐 " + ("EN" if LANG == "ar" else "ع"))
        lang.setObjectName("ghost"); lang.clicked.connect(s.toggle_lang)
        hh.addWidget(lang)
        thm = QPushButton("☀️" if SET.get("theme") == "dark" else "🌙")
        thm.setObjectName("ghost"); thm.clicked.connect(s.toggle_theme)
        hh.addWidget(thm)
        mv.addWidget(head)
        s.stack = QStackedWidget(); mv.addWidget(s.stack, 1)
        h.addWidget(side); h.addWidget(main, 1); s.setCentralWidget(root)
        t = QTimer(s); t.timeout.connect(s.tick); t.start(1000); s.tick()
        # قفل خمول
        try:
            s._idle = 0
            def _idle_tick():
                lim = int(float(SET.get("autolock_min", 0)))
                if lim <= 0: return
                s._idle += 1
                if s._idle >= lim * 60:
                    s._idle = 0
                    log("autolock")
                    global CUR_USER
                    CUR_USER = None
                    dlg2 = Login()
                    res = dlg2.exec()
                    if res != QDialog.Accepted or not CUR_USER:
                        QApplication.quit(); return
                    w2 = MainWindow(); globals()["_mw"] = w2
                    if LANG == "ar": w2.setLayoutDirection(Qt.RightToLeft)
                    w2.showMaximized(); s.close()
            s._idle_timer = QTimer(s)
            s._idle_timer.timeout.connect(_idle_tick)
            s._idle_timer.start(1000)
        except Exception: pass
        s.pages = {}; s.goto("dash")
    def tick(s):
        n = dt.datetime.now()
        dn = ["Monday","Tuesday","Wednesday","Thursday","Friday",
              "Saturday","Sunday"]
        adn = ["الإثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت",
               "الأحد"]
        if LANG == "ar":
            txt = (f"{adn[n.weekday()]}، {n.day:02d}/{n.month:02d}/{n.year}"
                   f"  |  {n.strftime('%I:%M:%S %p')}")
        else:
            txt = (f"{dn[n.weekday()]}, {n.day:02d} {n.strftime('%B %Y')}"
                   f"  |  {n.strftime('%I:%M:%S %p')}")
        s.clock.setText("📅  " + txt)
    def _refresh_page(s, k):
        w = s.pages.get(k)
        if not w: return
        try:
            if hasattr(w, "refresh"): w.refresh()
        except Exception: pass
        try:
            if k == "pos": w.build_grid()
            elif k == "inventory":
                w.load_stock(); w.load_moves(); w.load_cats()
            elif k == "locations":
                if hasattr(w, "load"): w.load()
                if hasattr(w, "load_tr"): w.load_tr()
        except Exception: pass
    def broadcast_all(s):
        for k in list(s.pages.keys()):
            try: s._refresh_page(k)
            except Exception: pass
    def page(s, k):
        if k in s.pages: return s.pages[k]
        try:
            makers = {
                "dash": Dashboard, "pos": POSPage, "sales": SalesPage,
                "quotes": QuotesPage, "einvoice": EInvoicePage,
                "shifts": ShiftsPage, "inventory": InventoryPage,
                "locations": LocationsPage, "purchases": PurchasesPage,
                "offers": OffersPage, "workorders": WorkOrdersPage,
                "appointments": AppointmentsPage,
                "commissions": CommissionsPage, "expenses": ExpensesPage,
                "reports": ReportsPage, "users": UsersPage,
                "settings": SettingsPage, "cash": CashPage,
                "trash": TrashPage}
            if k == "suppliers":   w = PartiesPage(s, "suppliers")
            elif k == "customers": w = PartiesPage(s, "customers")
            else:                  w = makers[k](s)
        except Exception:
            import traceback
            w = QWidget(); ev = QVBoxLayout(w)
            ev.addWidget(QLabel("⚠️ خطأ في فتح هذه الشاشة — نص الخطأ:"))
            box = QPlainTextEdit(traceback.format_exc())
            box.setReadOnly(True); ev.addWidget(box)
        s.pages[k] = w; s.stack.addWidget(w); return w
    def goto(s, k):
        if k not in s.navs:
            QMessageBox.warning(s, APP, "🚫 " + T("No permission")); return
        for kk, b in s.navs.items(): b.setChecked(kk == k)
        w = s.page(k); s.stack.setCurrentWidget(w)
        s._refresh_page(k)
        s.title.setText(("🏠  " if k == "dash" else "") + T(PAGES[k][0]))
        s.sub.setText(PAGES[k][1] if LANG == "ar" else PAGES[k][2])
    def refresh_dash(s):
        if "dash" in s.pages: s.pages["dash"].refresh()
    def toggle_theme(s):
        apply_theme(dark=SET.get("theme") != "dark")
        w = MainWindow(); globals()["_mw"] = w
        if LANG == "ar": w.setLayoutDirection(Qt.RightToLeft)
        w.showMaximized(); s.close()
    def toggle_lang(s):
        global LANG
        LANG = "en" if LANG == "ar" else "ar"; SET["lang"] = LANG
        log("lang", LANG)
        w = MainWindow(); globals()["_mw"] = w
        if LANG == "ar": w.setLayoutDirection(Qt.RightToLeft)
        w.showMaximized(); s.close()
    def logout(s):
        log("logout")
        global CUR_USER; CUR_USER = None
        dlg = Login()
        if dlg.exec() == QDialog.Accepted and CUR_USER:
            log("login")
            w = MainWindow(); globals()["_mw"] = w
            if LANG == "ar": w.setLayoutDirection(Qt.RightToLeft)
            w.showMaximized()
        else:
            QApplication.quit(); return
        s.close()

# ============================== MAIN =========================================
def main():
    global LANG
    if "--dump-schema" in sys.argv:
        ix = sys.argv.index("--dump-schema")
        out = (sys.argv[ix + 1] if len(sys.argv) > ix + 1
               else "database_schema.sql")
        open(out, "w", encoding="utf-8").write(SCHEMA)
        print("schema →", out); return
    seed(); migrate(); load_settings()
    # نسخة احتياطية تلقائية يومية (آخر 10)
    try:
        abk = os.path.join(DIR, "backup_auto_" + today() + ".db")
        if not os.path.exists(abk) and os.path.exists(DB):
            shutil.copy(DB, abk)
            for f_ in os.listdir(DIR):
                if f_.startswith("backup_auto_") and f_.endswith(".db"):
                    d_ = f_[12:-3]
                    try:
                        if (dt.date.today()
                                - dt.date.fromisoformat(d_)).days > 10:
                            os.remove(os.path.join(DIR, f_))
                    except Exception: pass
    except Exception: pass
    LANG = SET.get("lang", "ar")
    app = QApplication(sys.argv); app.setFont(QFont("Segoe UI", 10))
    try:
        if os.path.exists(LOGO_FILE): app.setWindowIcon(QIcon(LOGO_FILE))
    except Exception: pass
    sync_app_name()
    apply_theme()
    if not license_gate(APP):
        conn.close(); sys.exit(0)
    try:
        _tw_init = QTableWidget.__init__
        def _tw_big(self, *a, **k):
            _tw_init(self, *a, **k)
            try: self.verticalHeader().setDefaultSectionSize(44)
            except Exception: pass
        QTableWidget.__init__ = _tw_big
    except Exception: pass
    dlg = Login()
    result = dlg.exec()
    if result != QDialog.Accepted or not CUR_USER:
        log("exit_login", "user closed login window")
        conn.commit(); conn.close()
        sys.exit(0)
    log("login")
    notes = []
    stuck = q1("SELECT * FROM shifts WHERE status='open' "
               "AND date(opened_at)<? ORDER BY id DESC", (today(),))
    if stuck:
        if QMessageBox.question(None, APP,
            "🔓 " + T("Stuck shift found") + ": " + stuck["username"]
            + " @ " + str(stuck["opened_at"]) + "\n"
            + ("إغلاقها الآن وتسوية النقدية؟" if LANG == "ar"
               else "Close it now and settle cash?")
            ) == QMessageBox.Yes:
            cash_in = q1("SELECT IFNULL(SUM(paid_cash-change),0) v FROM sales "
                         "WHERE shift_id=? AND status='completed'",
                         (stuck["id"],))["v"]
            outs = q1("SELECT IFNULL(SUM(amount),0) v FROM treasury "
                      "WHERE account='drawer' AND direction='out' "
                      "AND ref NOT LIKE 'OPEN-%' AND ts>=?",
                      (stuck["opened_at"],))["v"]
            exp = (stuck["opening_cash"] or 0) + cash_in - outs
            x("UPDATE shifts SET closed_at=?,counted_cash=?,expected_cash=?,"
              "difference=0,status='closed' WHERE id=?",
              (nows(), exp, exp, stuck["id"]))
            log("shift_stuck_close", "id=" + str(stuck["id"]))
            notes.append("✅ " + T("Close Shift") + ": " + stuck["username"])
    low = low_stock_count()
    if low: notes.append(f"⚠️ {T('Low Stock Alerts')}: {low}")
    tdy = dt.date.today()
    for r in q("SELECT name,name_ar,expiry FROM products WHERE expiry!='' "
               "AND expiry IS NOT NULL"):
        try: ed = dt.date.fromisoformat(r["expiry"])
        except Exception: continue
        left = (ed - tdy).days
        if left < 0:
            notes.append(f"🔴 {r['name_ar'] or r['name']} — {T('Expired')}")
        elif left <= 7:
            notes.append(f"🟠 {r['name_ar'] or r['name']} — "
                         f"{left} يوم ({T('Expires soon')})")
    aps = q1("SELECT COUNT(*) c FROM appointments WHERE ts LIKE ?",
             (today() + "%",))["c"]
    if aps: notes.append(f"📅 {T('Appointments today')}: {aps}")
    w = MainWindow(); globals()["_mw"] = w
    if LANG == "ar": w.setLayoutDirection(Qt.RightToLeft)
    w.showMaximized()
    license_start_meter(APP, w)
    if notes: QMessageBox.information(w, APP, "\n".join(notes))
    sys.exit(app.exec())

if __name__ == "__main__":
    main()