# -*- coding: utf-8 -*-
# ============================================================================
#  سلة ERP | Silla ERP — Retail ERP + POS  (PySide6 + SQLite, offline)
#  Arabic/English • RTL/LTR • Light/Dark • Full working modules
#  Run:  pip install PySide6 qrcode pillow   →   python main.py
#  Login: admin / 123456
# ============================================================================
import sys, os, sqlite3, hashlib, shutil, json, base64, csv, io, datetime as dt

from PySide6.QtCore import (Qt, QTimer, QSize, QDate, QDateTime, QSizeF, QUrl,
                            QMarginsF, QProcess)
from PySide6.QtGui import (QFont, QColor, QPainter, QPixmap, QImage,
                           QTextDocument, QPageLayout, QPageSize, QBrush)
from PySide6.QtWidgets import *
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog

APP  = " Top Two"
DIR  = os.path.dirname(os.path.abspath(__file__))
DB   = os.path.join(DIR, "retail_erp.db")
LANG = "ar"; CUR_USER = None; SET = {}

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
  type TEXT DEFAULT 'branch');
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT, barcode TEXT UNIQUE,
  name TEXT, name_ar TEXT DEFAULT '', category_id INTEGER, unit TEXT DEFAULT 'pcs',
  cost REAL DEFAULT 0, price REAL DEFAULT 0, min_stock REAL DEFAULT 5,
  icon TEXT DEFAULT '📦', active INTEGER DEFAULT 1);
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
  category TEXT, description TEXT, amount REAL DEFAULT 0, username TEXT);
"""

# ============================== i18n ========================================
AR = {
"Dashboard":"لوحة التحكم","POS Screen":"شاشة الكاشير","Returns":"المرتجعات","Inventory":"المخزون",
"Purchases":"المشتريات","Offers & Discounts":"العروض والخصومات","Work Orders":"أوامر التشغيل",
"Expenses":"المصروفات","Sales & Invoices":"التقارير والفواتير","Quotations":"عروض الأسعار",
"E-Invoicing":"الفوترة الإلكترونية","Branches & Warehouses":"الفروع والمخازن","Customers":"العملاء",
"Suppliers":"الموردون","Appointments":"المواعيد","Commissions":"العمولات","Users":"المستخدمون",
"Settings":"الإعدادات","Shifts":"الورديات","Activity Log":"سجل العمليات",
"Operations":"التنفيذ","Management":"الإدارة","System":"النظام",
"Today's Sales":"مبيعات اليوم","Today's Invoices":"فواتير اليوم","Total Products":"إجمالي المنتجات",
"Low Stock Alerts":"تنبيهات نقص المخزون","Total Customers":"إجمالي العملاء","Cash in Drawer":"نقدية الدرج",
"Sales — last 7 days":"مبيعات آخر 7 أيام","Top products":"أعلى المنتجات مبيعاً",
"Barcode / Product name":"باركود أو اسم المنتج","Search":"بحث","Add":"إضافة","Edit":"تعديل","Delete":"حذف",
"Save":"حفظ","Cancel":"إلغاء","Close":"إغلاق","Confirm":"تأكيد","Yes":"نعم","No":"لا","Print":"طباعة",
"Export CSV":"تصدير CSV","Import CSV":"استيراد CSV","Imported":"تم الاستيراد","Total":"الإجمالي",
"Price":"السعر","Qty":"الكمية","Item":"الصنف","Subtotal":"الإجمالي الفرعي","Discount":"الخصم",
"Tax":"الضريبة","Grand Total":"الإجمالي النهائي","Cash":"نقدي","Card":"بطاقة","Change":"الباقي",
"Hold":"تعليق","Customer":"العميل","Walk-in":"عميل نقدي","Coupon":"كوبون","Clear":"تفريغ",
"Remove":"إزالة","New Sale":"فاتورة جديدة","Held Sales":"الفواتير المعلقة","Resume":"استكمال",
"Pay & Complete":"الدفع وإنهاء الفاتورة","Cart is empty":"السلة فارغة",
"Insufficient payment!":"المبلغ غير كافٍ!","Change due:":"الباقي للعميل:","Payment":"الدفع",
"Cash amount":"مبلغ النقدي","Card amount":"مبلغ البطاقة","Invoice No":"رقم الفاتورة",
"Date":"التاريخ","Status":"الحالة","completed":"مكتملة","returned":"مرتجعة","return":"مرتجع",
"unpaid":"غير مدفوعة","partial":"مدفوعة جزئياً","paid":"مدفوعة","draft":"مسودة","approved":"معتمد",
"rejected":"مرفوض","converted":"محوّلة","open":"مفتوحة","closed":"مغلقة","pending":"قيد الانتظار",
"in-progress":"جاري التنفيذ","done":"منجز","delivered":"تم التسليم","scheduled":"مجدول",
"Return":"مرتجع","Reason":"السبب","Return processed":"تم تسجيل المرتجع","Products":"المنتجات",
"Categories":"الأقسام","Stock by Location":"الأرصدة بالمخازن","Adjust Stock":"تسوية / جرد المخزون",
"Barcode Labels":"طباعة ملصقات الباركود","Product Name":"اسم المنتج","Name (AR)":"الاسم بالعربي",
"Category":"القسم","Unit":"الوحدة","Cost":"التكلفة","Min Stock":"حد الطلب","Active":"نشط",
"Transfer Stock":"تحويل مخزون","From":"من","To":"إلى","Branch":"فرع","Warehouse":"مخزن","Store":"معرض",
"New Purchase":"فاتورة شراء","Supplier":"المورد","Location":"المخزن","Ref No":"رقم المرجع",
"Total Cost":"الإجمالي","Purchase saved":"تم حفظ فاتورة الشراء","Pay Supplier":"دفع للمورد",
"Amount":"المبلغ","Ledger":"كشف الحساب","Balance":"الرصيد","Payment saved":"تم تسجيل الدفعة",
"Receive Payment":"تحصيل دفعة","New Quotation":"عرض سعر جديد","Valid Until":"صالح حتى",
"Approve":"اعتماد","Reject":"رفض","Convert to Invoice":"تحويل إلى فاتورة",
"Quotation saved":"تم حفظ عرض السعر","Quote converted to invoice":"تم التحويل إلى فاتورة",
"Print A4":"طباعة A4","Print Receipt":"طباعة إيصال","E-Invoice JSON":"تصدير JSON",
"E-Invoice XML":"تصدير XML","Tax Invoice":"فاتورة ضريبية","Open Shift":"فتح الوردية",
"Close Shift":"إغلاق الوردية","Opening Cash":"النقدية الافتتاحية","Counted Cash":"النقدية المعدودة",
"Expected":"المتوقع","Difference":"الفرق","Shift opened":"الوردية مفتوحة بالفعل",
"Shift closed":"تم إغلاق الوردية","No open shift!":"لا توجد وردية مفتوحة!",
"Role":"الدور","Permissions":"الصلاحيات","Password":"كلمة المرور","Work Order":"أمر تشغيل",
"Delivery Order":"أمر تسليم","Title":"العنوان","Assign To":"الموظف المسؤول","Due Date":"الاستحقاق",
"Advance Status":"نقل الحالة","Print Delivery Note":"طباعة أمر التسليم","Signature":"التوقيع",
"Received by":"المستلم","Delivered by":"المُسلِّم","New Appointment":"موعد جديد","Today":"اليوم",
"Rules":"القواعد","Computed Commissions":"العمولات المحتسبة","Employee":"الموظف","Basis":"الأساس",
"Percent %":"النسبة %","Fixed":"ثابت","Compute":"احتساب","Mark Paid":"تم الصرف","All":"الكل",
"product":"منتج","category":"قسم","Coupons":"الكوبونات","Offers":"العروض","Type":"النوع",
"percent":"نسبة","fixed":"مبلغ","Value":"القيمة","Min Total":"أدنى فاتورة","Starts":"من تاريخ",
"Ends":"إلى تاريخ","Points":"النقاط","Tier":"الفئة","Bronze":"برونزي","Silver":"فضي","Gold":"ذهبي",
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
}
MOD_AR = {"dashboard":"لوحة التحكم","pos":"الكاشير","sales":"المبيعات","inventory":"المخزون",
"locations":"الفروع والمخازن","purchases":"المشتريات","suppliers":"الموردون","customers":"العملاء",
"quotes":"عروض الأسعار","einvoice":"الفوترة الإلكترونية","offers":"العروض والخصومات",
"shifts":"الورديات","workorders":"أوامر التشغيل","appointments":"المواعيد","commissions":"العمولات",
"expenses":"المصروفات","reports":"التقارير","users":"المستخدمون","settings":"الإعدادات"}

def T(s): return AR.get(s, s) if LANG == "ar" else s
def money(v): return f"{(v or 0):,.2f}"
def nows():  return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def today(): return dt.date.today().isoformat()

# ============================== DB ==========================================
conn = sqlite3.connect(DB, check_same_thread=False)
conn.row_factory = sqlite3.Row
def q(sql, p=()):    return [dict(r) for r in conn.execute(sql, p).fetchall()]
def q1(sql, p=()):
    r = conn.execute(sql, p).fetchone()
    return dict(r) if r else None
def x(sql, p=()):
    cur = conn.execute(sql, p); conn.commit(); return cur.lastrowid

def load_settings():
    global SET
    SET = {r["key"]: r["value"] for r in q("SELECT * FROM settings")}
    d = {"company":"Silla Market","company_ar":"سلة ماركت","tax_no":"300000000000003",
         "phone":"0100000000","address":"Main Street","vat":"15","currency":"EGP",
         "currency_ar":"ج.م","theme":"light","lang":"ar",
         "receipt_footer":"Thank you for shopping with us!",
         "loyalty_earn":"1","loyalty_redeem":"0.1","tier_silver":"1000","tier_gold":"5000",
         "tier_silver_disc":"2","tier_gold_disc":"5"}
    for k, v in d.items(): SET.setdefault(k, v)

def sget(k): return SET.get(k, "")
def cur():   return sget("currency_ar") if LANG == "ar" else sget("currency")

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

# ============================== SEED ========================================
def seed():
    conn.executescript(SCHEMA)
    if q1("SELECT COUNT(*) c FROM users")["c"]:
        conn.commit(); return
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
        for m in ms: x("INSERT INTO role_permissions(role,module,allowed) VALUES(?,?,1)", (role, m))
    cats = ["أطعمة","مشروبات","ألبان","منظفات","عناية شخصية"]
    cids = {c: x("INSERT INTO categories(name) VALUES(?)", (c,)) for c in cats}
    cvals = list(cids.values())
    lids = [x("INSERT INTO locations(name,type) VALUES(?,?)", l) for l in
            [("الفرع الرئيسي","branch"),("المستودع المركزي","warehouse"),("معرض المدينة","store")]]
    prods = [("T001","بيسكويت سادة","Tea Biscuit",0,8,12,52),("T002","بسكويت شوكولاتة","Choco Biscuit",0,10,15,35),
        ("T003","رز مصري 1 كيلو","Rice 1kg",0,28,40,60),("T015","سكر أبيض 1 كيلو","Sugar 1kg",0,22,30,44),
        ("T021","زيت طهي 800 مل","Cooking Oil 800ml",0,48,60,25),("T022","مكرونة 400 جم","Pasta 400g",0,6,9,80),
        ("T030","حليب 1 لتر","Milk 1L",2,26,32,30),("T031","زبادي بلدي","Yogurt Cup",2,4,6,90),
        ("T037","جبنة مثلثات","Cheese Triangles",2,28,35,26),("T040","شامبو 400 مل","Shampoo 400ml",4,38,52,19),
        ("T041","صابون سائل","Liquid Soap",4,20,28,23),("T045","سائل أطباق 650 مل","Dish Soap 650ml",3,17,24,40),
        ("T047","منظف أرضيات 1 لتر","Floor Cleaner 1L",3,15,22,35),("T050","شاي 100 كيس","Tea 100 bags",1,30,42,28),
        ("T051","عصير برتقال 1 لتر","Juice 1L",1,14,20,48),("T052","مياه 1.5 لتر","Water 1.5L",1,4,6,120),
        ("T060","تونة قطع","Tuna Chunks",0,18,25,32),("T061","معجون طماطم","Tomato Paste",0,7,10,56)]
    for bc, arn, en, ci, cost, price, qty in prods:
        pid = x("INSERT INTO products(barcode,name,name_ar,category_id,cost,price,min_stock,icon) "
                "VALUES(?,?,?,?,?,?,5,'🛒')", (bc, en, arn, cvals[ci], cost, price))
        x("INSERT INTO stock(product_id,location_id,qty) VALUES(?,?,?)", (pid, lids[0], qty))
        x("INSERT INTO stock(product_id,location_id,qty) VALUES(?,?,?)", (pid, lids[1], qty // 2))
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
    x("INSERT INTO expenses(ts,category,description,amount,username) VALUES(?,?,?,?,?)",
      (nows(),"إيجار","إيجار المحل",1500,"admin"))
    x("INSERT INTO expenses(ts,category,description,amount,username) VALUES(?,?,?,?,?)",
      (nows(),"كهرباء","فاتورة الكهرباء",350,"admin"))
    x("INSERT INTO work_orders(wo_no,ts,type,title,details,status,due,assigned_to) "
      "VALUES('WO-00001',?, 'work','صيانة ثلاجة العرض','الشبكة غير مبردة','pending',?, 'أمين المخزن')",
      (nows(), today()))
    x("INSERT INTO work_orders(wo_no,ts,type,title,details,status,due,assigned_to) "
      "VALUES('WO-00002',?, 'delivery','توصيل طلبية مطعم النيل','3 صناديق زيت + 5 أكياس رز','done',?, 'محمد الكاشير')",
      (nows(), today()))
    x("INSERT INTO appointments(ts,title,customer_id,status) VALUES(?,?,2,'scheduled')",
      ((dt.datetime.now()+dt.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"), "اجتماع عرض أسعار جملة"))
    import random; random.seed(7)
    ps = q("SELECT * FROM products LIMIT 12")
    for d in range(6, -1, -1):
        day = (dt.date.today() - dt.timedelta(days=d)).strftime("%Y-%m-%d")
        for n in range(random.randint(1, 3)):
            items = random.sample(ps, random.randint(2, 4))
            sub = sum(i["price"] * random.randint(1, 3) for i in items)
            tax = round(sub * 0.15, 2); tot = round(sub + tax, 2)
            sid = x("INSERT INTO sales(invoice_no,ts,username,customer_id,location_id,shift_id,"
                    "subtotal,discount,tax,total,paid_cash,paid_card,change,status) "
                    "VALUES(?,?,?,?,?,NULL,?,0,?,?,0,?,0,'completed')",
                    (inv_no("SL"), f"{day} 1{n}:00:00", "cashier", 1, lids[0], sub, tax, tot, tot))
            for i in items:
                qt = random.randint(1, 3)
                x("INSERT INTO sale_items(sale_id,product_id,name,qty,price,cost,total) VALUES(?,?,?,?,?,?,?)",
                  (sid, i["id"], i["name_ar"] or i["name"], qt, i["price"], i["cost"], qt * i["price"]))
    x("INSERT INTO shifts(username,location_id,opened_at,closed_at,opening_cash,counted_cash,"
      "expected_cash,difference,status) VALUES(?,?,?,?,?,?,?,0,'closed')",
      ("cashier", lids[0], "2025-01-01 09:00:00", "2025-01-01 17:00:00", 200, 540, 540))
    conn.commit()

# ============================== THEME =======================================
PAL = {
 "light": {"bg":"#eef2f8","card":"#ffffff","text":"#0f172a","sub":"#64748b","border":"#e2e8f0",
   "primary":"#2563eb","primaryD":"#1d4ed8","green":"#10b981","greenD":"#059669","red":"#ef4444",
   "amber":"#f59e0b","side":"#0e1a2b","side2":"#16283f","input":"#f8fafc","sel":"#dbeafe"},
 "dark": {"bg":"#0b1220","card":"#121c30","text":"#e6edf7","sub":"#93a4bd","border":"#1e2b45",
   "primary":"#3b82f6","primaryD":"#2563eb","green":"#10b981","greenD":"#059669","red":"#f87171",
   "amber":"#fbbf24","side":"#060d1a","side2":"#132441","input":"#0e1930","sel":"#1e3a8a"},
}
def apply_theme(dark=None):
    if dark is not None:
        SET["theme"] = "dark" if dark else "light"
    p = PAL["dark"] if SET.get("theme") == "dark" else PAL["light"]
    qss = """
* { font-family:'Segoe UI','Tahoma'; font-size:13px; color:@text; }
QWidget { background:@bg; }
QLineEdit,QSpinBox,QDoubleSpinBox,QDateEdit,QDateTimeEdit,QComboBox,QTextEdit,QPlainTextEdit {
  background:@input; border:1px solid @border; border-radius:9px; padding:7px 10px;
  selection-background-color:@primary; color:@text; }
QLineEdit:focus,QDoubleSpinBox:focus,QComboBox:focus { border:1.5px solid @primary; }
QComboBox QAbstractItemView { background:@card; color:@text; border:1px solid @border; }
QPushButton { background:@card; border:1px solid @border; border-radius:9px; padding:8px 14px; color:@text; }
QPushButton:hover { border-color:@primary; }
QPushButton#primary { background:@primary; color:#fff; border:none; font-weight:600; }
QPushButton#success { background:@green; color:#fff; border:none; font-weight:600; }
QPushButton#danger  { background:@red;    color:#fff; border:none; font-weight:600; }
QPushButton#warn    { background:@amber;  color:#fff; border:none; font-weight:600; }
QPushButton#ghost   { background:transparent; }
QTableWidget { background:@card; alternate-background-color:@bg; border:1px solid @border;
  border-radius:12px; gridline-color:@border; }
QHeaderView::section { background:@card; color:@sub; border:none;
  border-bottom:2px solid @border; padding:8px; font-weight:700; }
QTableWidget::item { padding:6px; } QTableWidget::item:selected { background:@sel; color:@text; }
QTabWidget::pane { border:1px solid @border; border-radius:10px; background:@card; }
QTabBar::tab { padding:9px 16px; border-radius:8px; color:@sub; }
QTabBar::tab:selected { background:@primary; color:#fff; }
QLabel#h1 { font-size:21px; font-weight:800; } QLabel#h2 { color:@sub; font-size:12px; }
QLabel#big { font-size:22px; font-weight:800; }
QFrame#card, QFrame#stat { background:@card; border:1px solid @border; border-radius:14px; }
QScrollArea { border:none; background:transparent; }
#side { background:@side; } #side QLabel { color:#93a4bd; font-size:11px; font-weight:700; padding:6px 10px; }
#side QPushButton { background:transparent; color:#dbe4f0; border:none; text-align:left;
  padding:11px 14px; border-radius:10px; font-size:14px; font-weight:600; }
#side QPushButton:hover { background:@side2; }
#side QPushButton:checked { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
  stop:0 @greenD, stop:1 @green); color:#fff; }
#head { background:@card; border-bottom:1px solid @border; }
QMessageBox,QDialog { background:@bg; }
QScrollBar:vertical { background:transparent; width:10px; }
QScrollBar::handle:vertical { background:@border; border-radius:5px; }
QCheckBox { spacing:7px; }
"""
    for k, v in p.items(): qss = qss.replace("@" + k, v)
    QApplication.instance().setStyleSheet(qss)

IC = {"dash":"📊","pos":"🧾","sales":"💳","quotes":"📑","einvoice":"⚡","shifts":"🕒",
"inventory":"📦","locations":"🏬","purchases":"🚚","suppliers":"🏭","customers":"👥",
"offers":"🏷️","workorders":"🛠️","appointments":"📅","commissions":"💰","expenses":"🧮",
"reports":"📈","users":"🛡️","settings":"⚙️"}

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
            p.setPen(QColor("#cbd5e1" if SET.get("theme") == "dark" else "#64748b"))
            p.drawText(x0 - 8, bh - bh2 - 6, money(val)[:9])

def stat_card(icon, label, value, color):
    f = QFrame(); f.setObjectName("stat")
    lay = QHBoxLayout(f); lay.setContentsMargins(16, 14, 16, 14)
    ic = QLabel(icon); ic.setStyleSheet(
        f"font-size:26px;background:{color}22;border-radius:12px;padding:10px;")
    vb = QVBoxLayout()
    t = QLabel(T(label)); t.setStyleSheet("color:#64748b;")
    v = QLabel(str(value)); v.setObjectName("big"); v.setStyleSheet(f"color:{color};")
    vb.addWidget(t); vb.addWidget(v); lay.addWidget(ic); lay.addLayout(vb, 1)
    f._v = v
    return f

def export_csv(headers, rows):
    path, _ = QFileDialog.getSaveFileName(None, T("Export CSV"), "export.csv", "CSV (*.csv)")
    if not path: return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(headers); w.writerows(rows)
    QMessageBox.information(None, APP, T("Exported"))

# ---------- Code39 ----------
C39 = {'0':'000110100','1':'100100001','2':'001100001','3':'101100000','4':'000110001',
'5':'100110000','6':'001110000','7':'000100101','8':'100100100','9':'001100100',
'A':'100001001','B':'001001001','C':'101001000','D':'000011001','E':'100011000',
'F':'001011000','G':'000001101','H':'100001100','I':'001001100','J':'000011100',
'K':'100000011','L':'001000011','M':'101000010','N':'000010011','O':'100010010',
'P':'001010010','Q':'000000111','R':'100000110','S':'001000110','T':'000010110',
'U':'110000001','V':'011000001','W':'111000000','X':'010010001','Y':'110010000',
'Z':'011010000','-':'010000101','.':'110000100',' ':'011000100','$':'010101000',
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
        return img.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
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
        printer.setOutputFormat(QPrinter.PdfFormat); printer.setOutputFileName(pdf)
        doc.print_(printer); return
    dlg = QPrintPreviewDialog(printer, parent)
    dlg.paintRequested.connect(lambda pr: doc.print_(pr))
    dlg.exec()

# ============================== TABLE EDITOR ================================
class TableEditor(QWidget):
    def __init__(s, mw, table, cols, fields, search_cols=None, order="id DESC",
                 module=None, ro=False, filters=None, on_change=None):
        super().__init__(); s.mw = mw; s.table = table; s.cols = cols; s.fields = fields
        s.scols = search_cols or [c[0] for c in cols]; s.order = order
        s.module = module or table; s.ro = ro; s.on_change = on_change
        s.fcol = None
        v = QVBoxLayout(s); v.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        s.search = QLineEdit(); s.search.setPlaceholderText("🔍  " + T("Search"))
        s.search.textChanged.connect(s.refresh); top.addWidget(s.search, 1)
        if filters:
            items, s.fcol = filters
            s.fcombo = QComboBox()
            for lab, val in items: s.fcombo.addItem(str(lab), val)
            s.fcombo.currentIndexChanged.connect(s.refresh); top.addWidget(s.fcombo)
        if not ro:
            can = allowed(s.module)
            b1 = QPushButton("➕ " + T("Add")); b1.setObjectName("success")
            b1.clicked.connect(s.add); b1.setEnabled(can); top.addWidget(b1)
            b2 = QPushButton("✏️ " + T("Edit")); b2.clicked.connect(s.edit)
            b2.setEnabled(can); top.addWidget(b2)
            b3 = QPushButton("🗑 " + T("Delete")); b3.setObjectName("danger")
            b3.clicked.connect(s.delete); b3.setEnabled(can); top.addWidget(b3)
        bx = QPushButton("📤 " + T("Export CSV")); bx.clicked.connect(s.export); top.addWidget(bx)
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
        rows = q(f"SELECT {sel} FROM {s.table} {('WHERE ' + w) if w else ''} ORDER BY {s.order}", p)
        hdr = [T(c[1]) for c in s.cols]
        s.tbl.clear(); s.tbl.setColumnCount(len(hdr)); s.tbl.setRowCount(len(rows))
        s.tbl.setHorizontalHeaderLabels(hdr)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        s.ids = [r["id"] for r in rows]
        for i, r in enumerate(rows):
            for j, c in enumerate(s.cols):
                val = r[c[1]]
                if isinstance(val, float): val = money(val)
                it = QTableWidgetItem("" if val is None else str(val))
                it.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, it)
    def sel_id(s):
        r = s.tbl.currentRow()
        return s.ids[r] if 0 <= r < len(s.ids) else None
    def form(s, rec=None):
        d = QDialog(s); d.setWindowTitle(T("Edit") if rec else T("Add"))
        g = QFormLayout(d); g.setSpacing(10); ed = {}
        for col, lab, typ, opts in s.fields:
            if typ == "text":
                w = QLineEdit(str(rec[col]) if rec and rec[col] is not None else "")
            elif typ == "num":
                w = QDoubleSpinBox(); w.setMaximum(10**9); w.setDecimals(2)
                w.setValue(float(rec[col]) if rec else 0)
            elif typ == "int":
                w = QSpinBox(); w.setMaximum(10**6); w.setValue(int(rec[col]) if rec else 0)
            elif typ == "combo":
                items = opts() if callable(opts) else opts
                w = QComboBox()
                for v_, l_ in items: w.addItem(str(l_), v_)
                if rec:
                    ix = w.findData(rec[col])
                    if ix >= 0: w.setCurrentIndex(ix)
            elif typ == "date":
                w = QDateEdit(QDate.currentDate()); w.setCalendarPopup(True)
                if rec and rec[col]:
                    w.setDate(QDate.fromString(str(rec[col])[:10], "yyyy-MM-dd"))
            elif typ == "check":
                w = QCheckBox(); w.setChecked(bool(rec[col]) if rec else True)
            elif typ == "memo":
                w = QTextEdit(str(rec[col]) if rec else ""); w.setFixedHeight(60)
            else:
                w = QLineEdit()
            g.addRow(T(lab), w); ed[col] = (typ, w)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(d.accept); bb.rejected.connect(d.reject); g.addRow(bb)
        return d, ed
    def _val(s, typ, w):
        if typ == "check":  return 1 if w.isChecked() else 0
        if typ == "date":   return w.date().toString("yyyy-MM-dd")
        if typ == "memo":   return w.toPlainText()
        if typ == "combo":  return w.currentData()
        return w.value()
    def add(s):
        extra = {}
        if s.table == "work_orders":
            extra["wo_no"] = f"WO-{q1('SELECT COUNT(*) c FROM work_orders')['c']+1:05d}"
            extra["ts"] = nows()
        d, ed = s.form()
        if d.exec() != QDialog.Accepted: return
        cols = list(extra.keys()); vals = list(extra.values())
        for col, (typ, w) in ed.items():
            v_ = s._val(typ, w)
            if s.table == "users" and col == "password":
                v_ = hashlib.sha256((str(v_) or "123456").encode()).hexdigest()
            cols.append(col); vals.append(v_)
        try:
            x(f"INSERT INTO {s.table}({','.join(cols)}) VALUES({','.join('?'*len(cols))})", vals)
            log(f"add_{s.table}")
        except Exception as e:
            QMessageBox.critical(s, APP, str(e)); return
        s.refresh()
        if s.on_change: s.on_change()
    def edit(s):
        i = s.sel_id()
        if not i: QMessageBox.information(s, APP, T("Nothing selected")); return
        rec = q1(f"SELECT * FROM {s.table} WHERE id=?", (i,))
        d, ed = s.form(rec)
        if d.exec() != QDialog.Accepted: return
        sets = []; vals = []
        for col, (typ, w) in ed.items():
            v_ = s._val(typ, w)
            if s.table == "users" and col == "password":
                if not v_: continue                      # keep old password
                v_ = hashlib.sha256(str(v_).encode()).hexdigest()
            sets.append(f"{col}=?"); vals.append(v_)
        try:
            x(f"UPDATE {s.table} SET {','.join(sets)} WHERE id=?", vals + [i])
            log(f"edit_{s.table}", f"id={i}")
        except Exception as e:
            QMessageBox.critical(s, APP, str(e)); return
        s.refresh()
        if s.on_change: s.on_change()
    def delete(s):
        i = s.sel_id()
        if not i: QMessageBox.information(s, APP, T("Nothing selected")); return
        if s.table == "users":
            rec = q1("SELECT username FROM users WHERE id=?", (i,))
            if rec and (rec["username"] == "admin" or rec["username"] == CUR_USER["username"]):
                QMessageBox.warning(s, APP, "🚫"); return
        if QMessageBox.question(s, APP, T("Are you sure?")) == QMessageBox.Yes:
            x(f"DELETE FROM {s.table} WHERE id=?", (i,)); log(f"del_{s.table}", f"id={i}")
            s.refresh()
            if s.on_change: s.on_change()
    def export(s):
        w, p = s.rows_sql()
        sel = ", ".join(f"{c[0]} AS `{c[1]}`" for c in s.cols)
        rows = q(f"SELECT {sel} FROM {s.table} {('WHERE ' + w) if w else ''} ORDER BY {s.order}", p)
        export_csv([T(c[1]) for c in s.cols],
                   [[r[c[1]] for c in s.cols] for r in rows])

# ============================== LOGIN =======================================
class Login(QDialog):
    def __init__(s):
        super().__init__(); s.setWindowTitle(APP); s.setFixedSize(430, 470)
        if LANG == "ar": s.setLayoutDirection(Qt.RightToLeft)
        v = QVBoxLayout(s); v.setContentsMargins(34, 30, 34, 30)
        logo = QLabel("🛍️"); logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("font-size:52px;")
        t = QLabel(APP); t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("font-size:30px;font-weight:800;color:#10b981;")
        st = QLabel("Retail ERP + POS"); st.setAlignment(Qt.AlignCenter)
        v.addWidget(logo); v.addWidget(t); v.addWidget(st); v.addSpacing(14)
        s.u = QLineEdit(); s.u.setPlaceholderText("👤  " + T("Search")[:0] + "admin")
        s.p = QLineEdit(); s.p.setPlaceholderText("🔒  " + T("Password"))
        s.p.setEchoMode(QLineEdit.Password)
        v.addWidget(s.u); v.addWidget(s.p); v.addSpacing(8)
        b = QPushButton("🔐  Login"); b.setObjectName("success")
        b.setFixedHeight(44); b.clicked.connect(s.try_login); v.addWidget(b)
        v.addStretch(1)
        row = QHBoxLayout()
        lb = QPushButton("🌐 AR/EN"); lb.setObjectName("ghost"); lb.clicked.connect(s.toggle_lang)
        tb = QPushButton("🌙/☀️"); tb.setObjectName("ghost"); tb.clicked.connect(s.toggle_theme)
        row.addWidget(lb); row.addWidget(tb); v.addLayout(row)
        s.p.returnPressed.connect(s.try_login); s.u.returnPressed.connect(s.p.setFocus)
        s.setStyleSheet("QDialog{background:#0e1a2b;} QLabel{color:#e6edf7;}"
                        "QLineEdit{background:#16283f;color:#fff;border:1px solid #2b405e;}"
                        "QPushButton#ghost{color:#e6edf7;border-color:#2b405e;}")
    def toggle_lang(s):
        global LANG
        LANG = "en" if LANG == "ar" else "ar"; SET["lang"] = LANG
        s.done(3)                                   # reopen login in new language
    def toggle_theme(s):
        apply_theme(dark=SET.get("theme") != "dark")
    def try_login(s):
        r = q1("SELECT * FROM users WHERE username=? AND password=? AND active=1",
               (s.u.text().strip(), hashlib.sha256(s.p.text().encode()).hexdigest()))
        if not r:
            QMessageBox.warning(s, APP, "❌ " + T("Nothing selected")[:0] + "Wrong login"); return
        global CUR_USER; CUR_USER = r; s.accept()

# ============================== POS =========================================
class PaymentDialog(QDialog):
    def __init__(s, total):
        super().__init__(); s.total = total; s.ok_paid = False
        s.setWindowTitle("💳 " + T("Payment")); s.setFixedWidth(430)
        v = QVBoxLayout(s)
        tt = QLabel(T("Grand Total") + f":  {money(total)} {cur()}")
        tt.setObjectName("big"); tt.setAlignment(Qt.AlignCenter)
        tt.setStyleSheet("color:#10b981;"); v.addWidget(tt)
        g = QFormLayout()
        s.cash = QDoubleSpinBox(); s.cash.setMaximum(10**7); s.cash.setDecimals(2)
        s.cash.setValue(total)
        s.card = QDoubleSpinBox(); s.card.setMaximum(10**7); s.card.setDecimals(2)
        g.addRow(T("Cash amount"), s.cash); g.addRow(T("Card amount"), s.card)
        v.addLayout(g)
        qv = QHBoxLayout()
        for val in [total, 50, 100, 200, 500]:
            b = QPushButton(money(val)); b.setObjectName("ghost")
            b.clicked.connect(lambda _, v_=val: s.quick(v_)); qv.addWidget(b)
        v.addLayout(qv)
        s.chg = QLabel(T("Change due:") + " 0.00"); s.chg.setObjectName("big")
        s.chg.setAlignment(Qt.AlignCenter); s.chg.setStyleSheet("color:#2563eb;")
        v.addWidget(s.chg)
        s.cash.valueChanged.connect(s.upd); s.card.valueChanged.connect(s.upd)
        ok = QPushButton("✅ " + T("Confirm")); ok.setObjectName("success")
        ok.setFixedHeight(42); ok.clicked.connect(s.accept); v.addWidget(ok)
        s.upd()
    def quick(s, v_):
        s.cash.setValue(v_ if v_ >= s.total else max(0, s.total - s.card.value()))
    def upd(s):
        paid = s.cash.value() + s.card.value()
        s.ok_paid = paid >= s.total - 0.001
        s.chg.setText(T("Change due:") + " " + money(max(0, paid - s.total)) + " " + cur())
    def values(s):
        return (s.cash.value(), s.card.value(),
                max(0.0, s.cash.value() + s.card.value() - s.total))

class POSPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw
        s.items = []; s.customer_id = 1; s.coupon_amt = 0; s.coupon_code = ""; s.points_use = 0
        h = QHBoxLayout(s); h.setContentsMargins(12, 12, 12, 12); h.setSpacing(12)
        pw = QWidget(); pv = QVBoxLayout(pw); pv.setContentsMargins(0, 0, 0, 0)
        sr = QHBoxLayout()
        s.bar = QLineEdit(); s.bar.setPlaceholderText("📷  " + T("Barcode / Product name"))
        s.bar.setFixedHeight(42); s.bar.returnPressed.connect(s.scan); sr.addWidget(s.bar, 1)
        ba = QPushButton("➕ " + T("Add")); ba.setObjectName("primary")
        ba.setFixedHeight(42); ba.clicked.connect(s.scan); sr.addWidget(ba)
        s.loc = QComboBox()
        for l in q("SELECT * FROM locations"): s.loc.addItem("🏬 " + l["name"], l["id"])
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
        s.cust = QComboBox()
        for c in q("SELECT * FROM customers ORDER BY id"):
            s.cust.addItem("👤 " + c["name"] + f" ({T(c['tier'])})", c["id"])
        s.cust.currentIndexChanged.connect(s.cust_changed)
        crow.addWidget(QLabel("👤")); crow.addWidget(s.cust, 1); cv.addLayout(crow)
        s.cart = QTableWidget(0, 4)
        s.cart.setHorizontalHeaderLabels([T("Item"), T("Price"), T("Qty"), T("Total")])
        s.cart.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        s.cart.verticalHeader().setVisible(False)
        cv.addWidget(s.cart, 1)
        ops = QHBoxLayout()
        b1 = QPushButton("➖"); b1.clicked.connect(s.dec); ops.addWidget(b1)
        b2 = QPushButton("➕"); b2.clicked.connect(s.inc); ops.addWidget(b2)
        b3 = QPushButton("❌ " + T("Remove")); b3.setObjectName("danger")
        b3.clicked.connect(s.remove); ops.addWidget(b3)
        cv.addLayout(ops)
        ex = QHBoxLayout()
        s.disc = QDoubleSpinBox(); s.disc.setRange(0, 100); s.disc.setPrefix("% ")
        s.cp = QLineEdit(); s.cp.setPlaceholderText("🎟️ " + T("Coupon"))
        ap = QPushButton(T("Coupon")); ap.setObjectName("primary"); ap.clicked.connect(s.apply_coupon)
        ex.addWidget(s.disc); ex.addWidget(s.cp, 1); ex.addWidget(ap); cv.addLayout(ex)
        pts = QHBoxLayout()
        s.redeem = QSpinBox(); s.redeem.setRange(0, 10**6); s.redeem.setPrefix("⭐ ")
        rb = QPushButton("⭐ " + T("Redeem Points")); rb.setObjectName("warn")
        rb.clicked.connect(s.use_points)
        pts.addWidget(s.redeem); pts.addWidget(rb); pts.addStretch(1); cv.addLayout(pts)
        s.tot = QLabel("0.00"); s.tot.setAlignment(Qt.AlignCenter)
        s.tot.setStyleSheet("background:rgba(16,185,129,.12);border-radius:12px;padding:12px;"
                            "color:#10b981;font-size:22px;font-weight:800;")
        cv.addWidget(s.tot)
        pay = QPushButton("💰 " + T("Pay & Complete")); pay.setObjectName("success")
        pay.setFixedHeight(52); pay.clicked.connect(s.pay); cv.addWidget(pay)
        hld = QPushButton("⏸ " + T("Hold")); hld.clicked.connect(s.hold); cv.addWidget(hld)
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
        rows = q("""SELECT p.*, IFNULL((SELECT SUM(qty) FROM stock WHERE product_id=p.id
                     AND location_id=?),0) tq FROM products p WHERE p.active=1
                     ORDER BY p.id DESC""", (s.loc.currentData(),))
        if term:
            rows = [r for r in rows if term.lower() in
                    (r["name"] + " " + (r["name_ar"] or "") + " " + (r["barcode"] or "")).lower()]
        r = c = 0; MAXC = 5
        for p in rows:
            qty = p["tq"]
            btn = QPushButton(f"{p['icon'] or '📦'}  {disp_name(p)}\n💰 {money(s.prod_price(p))} {cur()}\n📦 {T('Stock:')} {qty:g}")
            btn.setFixedHeight(96); btn.setStyleSheet("text-align:center;font-weight:600;")
            if qty <= 0:
                btn.setEnabled(False)
                btn.setStyleSheet("background:rgba(148,163,184,.25);color:#94a3b8;")
            btn.clicked.connect(lambda _, pid=p["id"]: s.add_product(pid))
            s.grid.addWidget(btn, r, c); c += 1
            if c == MAXC: c = 0; r += 1
        s.grid.setRowStretch(r + 1, 1); s.grid.setColumnStretch(MAXC, 1)
    def scan(s):
        t = s.bar.text().strip()
        if not t: return
        p = q1("SELECT * FROM products WHERE barcode=?", (t,))
        if not p:
            r = q("SELECT * FROM products WHERE name LIKE ? OR name_ar LIKE ? LIMIT 1",
                  (f"%{t}%", f"%{t}%"))
            p = r[0] if r else None
        if not p: QMessageBox.warning(s, APP, "❌"); s.bar.clear(); s.bar.setFocus(); return
        s.add_product(p["id"]); s.bar.clear(); s.bar.setFocus()
    def add_product(s, pid):
        p = q1("SELECT * FROM products WHERE id=?", (pid,))
        st = q1("SELECT IFNULL(SUM(qty),0) tq FROM stock WHERE product_id=? AND location_id=?",
                (pid, s.loc.currentData()))["tq"]
        in_cart = sum(i["qty"] for i in s.items if i["pid"] == pid)
        if in_cart + 1 > st: QMessageBox.warning(s, APP, "📦 " + T("Insufficient payment!")); return
        for i in s.items:
            if i["pid"] == pid: i["qty"] += 1; break
        else:
            s.items.append({"pid": pid, "name": disp_name(p), "price": s.prod_price(p),
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
        s.customer_id = s.cust.currentData(); s.render()
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
        if not c or (c["starts"] and c["starts"] > td) or (c["ends"] and c["ends"] < td):
            QMessageBox.warning(s, APP, "🎟️ " + T("Invalid coupon")); return
        sub = sum(i["price"] * i["qty"] for i in s.items)
        if sub < c["min_total"]:
            QMessageBox.warning(s, APP, "🎟️ ≥ " + money(c["min_total"])); return
        s.coupon_amt = round(sub * c["value"] / 100, 2) if c["type"] == "percent" else c["value"]
        s.coupon_code = code; s.render()
    def use_points(s):
        c = q1("SELECT * FROM customers WHERE id=?", (s.customer_id,))
        pts = s.redeem.value()
        if not c or pts <= 0: return
        if pts > c["points"]: QMessageBox.warning(s, APP, "⭐"); return
        s.points_use = pts; s.render()
    def totals(s):
        sub = sum(i["price"] * i["qty"] for i in s.items)
        d = round(sub * s.disc.value() / 100, 2) + round(sub * s.tier_disc() / 100, 2) \
            + s.coupon_amt + s.points_use * float(SET.get("loyalty_redeem", 0.1))
        d = min(d, sub)
        tax = round((sub - d) * float(SET.get("vat", 15)) / 100, 2)
        return sub, d, tax, round(sub - d + tax, 2)
    def render(s):
        s.cart.setRowCount(len(s.items))
        for i, it in enumerate(s.items):
            for j, val in enumerate([it["name"], money(it["price"]),
                                     f"{it['qty']:g}", money(it["price"] * it["qty"])]):
                c = QTableWidgetItem(val); c.setTextAlignment(Qt.AlignCenter)
                s.cart.setItem(i, j, c)
        sub, d, tax, tot = s.totals()
        s.tot.setText(f"{T('Subtotal')} {money(sub)} | {T('Discount')} -{money(d)} | "
                      f"{T('Tax')} {money(tax)}\n{T('Grand Total')}: {money(tot)} {cur()}")
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
        dl = QPushButton("🗑 " + T("Delete")); dl.setObjectName("danger")
        hb.addWidget(res); hb.addWidget(dl); v.addLayout(hb)
        def do_resume():
            rr = t.currentRow()
            if rr < 0: return
            data = json.loads(rows[rr]["data"])
            s.items = data["items"]; s.disc.setValue(data.get("disc", 0))
            s.coupon_amt = data.get("coupon_amt", 0); s.coupon_code = data.get("coupon", "")
            ix = s.cust.findData(data.get("customer_id", 1))
            if ix >= 0: s.cust.setCurrentIndex(ix)
            x("DELETE FROM held_sales WHERE id=?", (rows[rr]["id"],))
            s.render(); d.accept()
        def do_del():
            rr = t.currentRow()
            if rr >= 0:
                x("DELETE FROM held_sales WHERE id=?", (rows[rr]["id"],)); d.accept()
        res.clicked.connect(do_resume); dl.clicked.connect(do_del)
        d.resize(520, 380); d.exec()
    def pay(s):
        if not s.items: QMessageBox.information(s, APP, T("Cart is empty")); return
        sh = q1("SELECT * FROM shifts WHERE username=? AND status='open' ORDER BY id DESC",
                (CUR_USER["username"],))
        if not sh:
            QMessageBox.warning(s, APP, "🕒 " + T("No open shift!")); s.mw.goto("shifts"); return
        sub, d_, tax, tot = s.totals()
        dlg = PaymentDialog(tot)
        if dlg.exec() != QDialog.Accepted: return
        if not dlg.ok_paid:
            QMessageBox.warning(s, APP, T("Insufficient payment!")); return
        cash, card, change = dlg.values()
        no = inv_no("SL")
        sid = x("INSERT INTO sales(invoice_no,ts,username,customer_id,location_id,shift_id,"
                "subtotal,discount,tax,total,paid_cash,paid_card,change,status,coupon) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'completed',?)",
                (no, nows(), CUR_USER["username"], s.customer_id, s.loc.currentData(),
                 sh["id"], sub, d_, tax, tot, cash, card, change, s.coupon_code))
        for i in s.items:
            x("INSERT INTO sale_items(sale_id,product_id,name,qty,price,cost,total) "
              "VALUES(?,?,?,?,?,?,?)",
              (sid, i["pid"], i["name"], i["qty"], i["price"], i["cost"], i["price"] * i["qty"]))
            move_stock(i["pid"], s.loc.currentData(), -i["qty"], "sale", no)
        if s.coupon_code:
            x("UPDATE coupons SET used=used+1 WHERE UPPER(code)=?", (s.coupon_code,))
        if s.customer_id and s.customer_id > 1:
            earn = int(tot / 100 * float(SET.get("loyalty_earn", 1)))
            if s.points_use > 0:
                x("UPDATE customers SET points=points-? WHERE id=?",
                  (s.points_use, s.customer_id))
                x("INSERT INTO loyalty_txn(ts,customer_id,points,reason,username) "
                  "VALUES(?,?,?,?,?)", (nows(), s.customer_id, -s.points_use,
                                        "redeem " + no, CUR_USER["username"]))
            if earn > 0:
                x("UPDATE customers SET points=points+? WHERE id=?",
                  (earn, s.customer_id))
                x("INSERT INTO loyalty_txn(ts,customer_id,points,reason,username) "
                  "VALUES(?,?,?,?,?)", (nows(), s.customer_id, earn,
                                        "earn " + no, CUR_USER["username"]))
            c = q1("SELECT * FROM customers WHERE id=?", (s.customer_id,))
            spend = q1("SELECT IFNULL(SUM(total),0) v FROM sales WHERE customer_id=? "
                       "AND status='completed'", (c["id"],))["v"]
            tier = ("Gold" if spend >= float(SET.get("tier_gold", 5000))
                    else "Silver" if spend >= float(SET.get("tier_silver", 1000)) else "Bronze")
            if tier != c["tier"]:
                x("UPDATE customers SET tier=? WHERE id=?", (tier, c["id"]))
        for r_ in q("SELECT * FROM commission_rules WHERE active=1 AND basis='sale' "
                    "AND (employee=? OR employee='*')", (CUR_USER["username"],)):
            amt = round(tot * r_["percent"] / 100 + r_["fixed"], 2)
            if amt > 0:
                x("INSERT INTO commissions(ts,employee,sale_id,amount) VALUES(?,?,?,?)",
                  (nows(), CUR_USER["username"], sid, amt))
        log("sale", f"{no} total={tot}")
        s.clear_cart(); s.mw.refresh_dash()
        if QMessageBox.question(s, APP, "🧾 " + T("Print Receipt") + "?") == QMessageBox.Yes:
            print_receipt(sid, s)
        s.bar.setFocus()

# ---------- receipts / invoices --------------------------------------------
def receipt_html(sid):
    sale = q1("SELECT * FROM sales WHERE id=?", (sid,))
    items = q("SELECT * FROM sale_items WHERE sale_id=?", (sid,))
    rows = "".join(
        f"<tr><td>{i['name']}</td><td align=center>{i['qty']:g}</td>"
        f"<td align=right>{money(i['price'])}</td><td align=right>{money(i['total'])}</td></tr>"
        for i in items)
    comp = SET.get("company_ar") if LANG == "ar" else SET.get("company")
    return f"""<div style="text-align:center;font-family:'Segoe UI';">
    <div style="font-size:16px;font-weight:800;">{comp}</div>
    <div style="font-size:10px;">{SET.get('tax_no')} • {SET.get('phone')}</div>
    <div style="font-size:11px;">{T('Receipt')} {sale['invoice_no']} • {sale['ts']}</div>
    <div style="font-size:10px;">{T('Cashier')}: {sale['username']}</div></div>
    <table width="100%" style="font-size:11px;margin-top:6px;" cellpadding=3>{rows}</table>
    <table width="100%" style="font-size:12px;margin-top:6px;" cellpadding=2>
    <tr><td>{T('Subtotal')}</td><td align=right>{money(sale['subtotal'])}</td></tr>
    <tr><td>{T('Discount')}</td><td align=right>-{money(sale['discount'])}</td></tr>
    <tr><td>{T('Tax')}</td><td align=right>{money(sale['tax'])}</td></tr>
    <tr style="font-weight:800;font-size:14px;"><td>{T('Grand Total')} ({cur()})</td>
    <td align=right>{money(sale['total'])}</td></tr>
    <tr><td>{T('Cash')}</td><td align=right>{money(sale['paid_cash'])}</td></tr>
    <tr><td>{T('Card')}</td><td align=right>{money(sale['paid_card'])}</td></tr>
    <tr><td>{T('Change')}</td><td align=right>{money(sale['change'])}</td></tr></table>
    <div align="center"><img src="qr" width="110" height="110"><br>
    <img src="bar" width="190" height="46"><br>
    <span style="font-size:11px;">{sale['invoice_no']}</span></div>
    <div style="text-align:center;font-size:10px;margin-top:4px;">
    {SET.get('receipt_footer','')}</div>"""

def print_receipt(sid, parent=None):
    sale = q1("SELECT * FROM sales WHERE id=?", (sid,))
    qr = qr_image(zatca_qr_payload(sale), 110)
    imgs = {"bar": code39_pixmap(sale["invoice_no"]).toImage(),
            "qr": qr if qr else blank_img(110, 110)}
    do_print(receipt_html(sid), imgs, a4=False, parent=parent)

def a4_invoice_html(sid, tax=True):
    sale = q1("SELECT * FROM sales WHERE id=?", (sid,))
    cust = q1("SELECT * FROM customers WHERE id=?", (sale["customer_id"],)) \
           if sale["customer_id"] else None
    items = q("SELECT * FROM sale_items WHERE sale_id=?", (sid,))
    rows = "".join(
        f"<tr><td align=center>{n+1}</td><td>{i['name']}</td>"
        f"<td align=center>{i['qty']:g}</td><td align=right>{money(i['price'])}</td>"
        f"<td align=right>{money(i['total'])}</td></tr>"
        for n, i in enumerate(items))
    comp = SET.get("company_ar") if LANG == "ar" else SET.get("company")
    head = ""
    if tax:
        head = (f"<tr><th align=right>{T('Seller')}</th><th align=right>{comp} — "
                f"{SET.get('tax_no')}</th></tr>"
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
    <tr><td>{T('Tax')} ({SET.get('vat')}%)</td><td align=right>{money(sale['tax'])}</td></tr>
    <tr style="font-weight:800;font-size:15px;"><td>{T('Grand Total')} ({cur()})</td>
    <td align=right>{money(sale['total'])}</td></tr></table>
    <div style="clear:both;"><img src="qr" width="130" height="130"><br>
    <img src="bar" width="260" height="52"></div>
    <p style="margin-top:60px;font-size:13px;">{T('Received by')}: ..................
    &nbsp;&nbsp; {T('Delivered by')}: ..................</p></div>"""

def print_a4(sid, tax=True, pdf=None, parent=None):
    sale = q1("SELECT * FROM sales WHERE id=?", (sid,))
    qr = qr_image(zatca_qr_payload(sale), 130)
    imgs = {"bar": code39_pixmap(sale["invoice_no"]).toImage(),
            "qr": qr if qr else blank_img(130, 130)}
    do_print(a4_invoice_html(sid, tax), imgs, a4=True, pdf=pdf, parent=parent)

# ============================== PAGES =======================================
class Dashboard(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw
        v = QVBoxLayout(s); v.setContentsMargins(14, 14, 14, 14)
        top = QHBoxLayout()
        s.loc = QComboBox(); s.loc.addItem("🏬 " + T("All"), None)
        for l in q("SELECT * FROM locations"): s.loc.addItem("🏬 " + l["name"], l["id"])
        s.loc.currentIndexChanged.connect(s.refresh)
        top.addWidget(QLabel("🏬 " + T("Branch/Store"))); top.addWidget(s.loc)
        top.addStretch(1); v.addLayout(top)
        g = QGridLayout(); g.setSpacing(12)
        s.c_sale = stat_card("💰", T("Today's Sales"),    "—", "#10b981")
        s.c_inv  = stat_card("🧾", T("Today's Invoices"), "—", "#2563eb")
        s.c_prd  = stat_card("📦", T("Total Products"),   "—", "#6366f1")
        s.c_low  = stat_card("⚠️", T("Low Stock Alerts"), "—", "#ef4444")
        s.c_cus  = stat_card("👥", T("Total Customers"),  "—", "#f59e0b")
        s.c_cash = stat_card("🗄️", T("Cash in Drawer"),  "—", "#0ea5e9")
        for i, c in enumerate([s.c_sale, s.c_inv, s.c_prd]): g.addWidget(c, 0, i)
        for i, c in enumerate([s.c_low, s.c_cus, s.c_cash]): g.addWidget(c, 1, i)
        v.addLayout(g)
        ch = QHBoxLayout(); ch.setSpacing(12)
        s.chart = BarChart(T("Sales — last 7 days"))
        s.top = BarChart(T("Top products"), color="#10b981")
        ch.addWidget(s.chart, 2); ch.addWidget(s.top, 2); v.addLayout(ch, 1)
        s.refresh()
    def drawer(s):
        sh = q1("SELECT * FROM shifts WHERE status='open' ORDER BY id DESC")
        if not sh: return 0.0
        return sh["opening_cash"] + q1(
            "SELECT IFNULL(SUM(paid_cash-change),0) v FROM sales "
            "WHERE shift_id=? AND status='completed'", (sh["id"],))["v"]
    def refresh(s):
        lid = s.loc.currentData()
        w = " AND location_id=?" if lid else ""
        p = (lid,) if lid else ()
        t = q1(f"SELECT IFNULL(SUM(total),0) v, COUNT(*) c FROM sales "
               f"WHERE date(ts)=? AND status='completed'{w}", (today(),) + p)
        s.c_sale._v.setText(f"{money(t['v'])} {cur()}")
        s.c_inv._v.setText(str(t["c"]))
        s.c_prd._v.setText(str(q1("SELECT COUNT(*) c FROM products WHERE active=1")["c"]))
        s.c_low._v.setText(str(low_stock_count()))
        s.c_cus._v.setText(str(q1("SELECT COUNT(*) c FROM customers")["c"]))
        s.c_cash._v.setText(money(s.drawer()))
        days = []
        for i in range(6, -1, -1):
            d = dt.date.today() - dt.timedelta(days=i)
            v_ = q1(f"SELECT IFNULL(SUM(total),0) v FROM sales WHERE date(ts)=? "
                    f"AND status='completed'{w}", (d.isoformat(),) + p)["v"]
            days.append((["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][d.weekday()],
                         round(v_, 2), None))
        s.chart.set_data(days)
        top = q(f"""SELECT si.name, SUM(si.total) v FROM sale_items si
                JOIN sales s ON s.id=si.sale_id WHERE s.status='completed'{w}
                GROUP BY si.name ORDER BY v DESC LIMIT 7""", p)
        colors = ["#10b981","#2563eb","#6366f1","#f59e0b","#ef4444","#0ea5e9","#8b5cf6"]
        s.top.set_data([(r["name"][:12], round(r["v"], 2), colors[i % 7])
                        for i, r in enumerate(top)])

class SalesPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw
        v = QVBoxLayout(s); top = QHBoxLayout()
        s.f = QDateEdit(QDate.currentDate().addDays(-30)); s.f.setCalendarPopup(True)
        s.t = QDateEdit(QDate.currentDate()); s.t.setCalendarPopup(True)
        b = QPushButton("🔍 " + T("Search")); b.setObjectName("primary")
        b.clicked.connect(s.refresh)
        top.addWidget(QLabel("📅")); top.addWidget(s.f)
        top.addWidget(QLabel("📅")); top.addWidget(s.t); top.addWidget(b); top.addStretch(1)
        v.addLayout(top)
        s.tbl = QTableWidget(); s.tbl.setAlternatingRowColors(True)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        v.addWidget(s.tbl, 1)
        bot = QHBoxLayout(); s.ids = []
        for lab, fn, sty in [("👁 " + T("Search")[:0] + "View", s.view, "primary"),
                             ("🧾 " + T("Print Receipt"), lambda: s.pr(False), ""),
                             ("📄 " + T("Print A4"), lambda: s.pr(True), ""),
                             ("⚡ " + T("E-Invoice JSON"), s.exp_json, ""),
                             ("↩️ " + T("Return"), s.ret, "danger"),
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
                    r["cname"] or T("Walk-in"), money(r["total"]), T(r["status"])]
            for j, val in enumerate(vals):
                c = QTableWidgetItem(str(val)); c.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, c)
    def sel(s):
        r = s.tbl.currentRow()
        return s.ids[r] if 0 <= r < len(s.ids) else None
    def view(s):
        i = s.sel()
        if not i: QMessageBox.information(s, APP, T("Nothing selected")); return
        sale = q1("SELECT * FROM sales WHERE id=?", (i,))
        items = q("SELECT * FROM sale_items WHERE sale_id=?", (i,))
        d = QDialog(s); d.setWindowTitle(sale["invoice_no"]); v = QVBoxLayout(d)
        tt = QTableWidget(len(items), 5)
        tt.setHorizontalHeaderLabels([T("Item"), T("Qty"), T("Price"), T("Cost"), T("Total")])
        tt.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tt.verticalHeader().setVisible(False)
        for n, it in enumerate(items):
            for j, val in enumerate([it["name"], f"{it['qty']:g}", money(it["price"]),
                                     money(it["cost"]), money(it["total"])]):
                c = QTableWidgetItem(val); c.setTextAlignment(Qt.AlignCenter)
                tt.setItem(n, j, c)
        v.addWidget(tt)
        lb = QLabel(f"{T('Grand Total')}: {money(sale['total'])} {cur()} — {T(sale['status'])}")
        lb.setObjectName("big"); lb.setAlignment(Qt.AlignCenter); v.addWidget(lb)
        d.resize(560, 420); d.exec()
    def pr(s, a4=True):
        i = s.sel()
        if not i: QMessageBox.information(s, APP, T("Nothing selected")); return
        if a4: print_a4(i, parent=s)
        else:  print_receipt(i, s)
    def exp_json(s):
        i = s.sel()
        if not i: QMessageBox.information(s, APP, T("Nothing selected")); return
        sale = q1("SELECT * FROM sales WHERE id=?", (i,))
        items = q("SELECT * FROM sale_items WHERE sale_id=?", (i,))
        doc = {"invoice_no": sale["invoice_no"], "timestamp": sale["ts"],
               "seller": {"name": SET.get("company"), "vat": SET.get("tax_no")},
               "totals": {"subtotal": sale["subtotal"], "discount": sale["discount"],
                          "vat": sale["tax"], "total": sale["total"]},
               "qr_tlv_base64": zatca_qr_payload(sale),
               "lines": [{"name": it["name"], "qty": it["qty"],
                          "price": it["price"], "total": it["total"]} for it in items]}
        path, _ = QFileDialog.getSaveFileName(s, "JSON", sale["invoice_no"] + ".json")
        if path:
            open(path, "w", encoding="utf-8").write(
                json.dumps(doc, ensure_ascii=False, indent=2))
            log("einvoicing_export", sale["invoice_no"])
    def csv(s):
        f = s.f.date().toString("yyyy-MM-dd")
        t = s.t.date().toString("yyyy-MM-dd") + " 23:59:59"
        rows = q("""SELECT s.*, c.name cname FROM sales s
                 LEFT JOIN customers c ON c.id=s.customer_id WHERE s.ts BETWEEN ? AND ?""", (f, t))
        export_csv([T("Invoice No"), T("Date"), T("Cashier"), T("Customer"),
                    T("Grand Total"), T("Status")],
                   [[r["invoice_no"], r["ts"], r["username"], r["cname"] or "",
                     r["total"], r["status"]] for r in rows])
    def ret(s):
        i = s.sel()
        if not i: QMessageBox.information(s, APP, T("Nothing selected")); return
        sale = q1("SELECT * FROM sales WHERE id=?", (i,))
        if sale["status"] == "returned":
            QMessageBox.information(s, APP, T("Status") + ": " + T("returned")); return
        items = q("SELECT * FROM sale_items WHERE sale_id=?", (i,))
        d = QDialog(s); d.setWindowTitle("↩️ " + T("Return") + " — " + sale["invoice_no"])
        v = QVBoxLayout(d); spins = []
        t = QTableWidget(len(items), 4)
        t.setHorizontalHeaderLabels([T("Item"), T("Qty"), T("Price"), T("Return")])
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.verticalHeader().setVisible(False)
        for n, it in enumerate(items):
            t.setItem(n, 0, QTableWidgetItem(it["name"]))
            t.setItem(n, 1, QTableWidgetItem(f"{it['qty']:g}"))
            t.setItem(n, 2, QTableWidgetItem(money(it["price"])))
            sp = QDoubleSpinBox(); sp.setMaximum(it["qty"]); spins.append(sp)
            t.setCellWidget(n, 3, sp)
        v.addWidget(t)
        rs = QLineEdit(); rs.setPlaceholderText(T("Reason")); v.addWidget(rs)
        ok = QPushButton("✅ " + T("Confirm")); ok.setObjectName("danger"); v.addWidget(ok)
        def do():
            qtys = [sp.value() for sp in spins]
            if not any(qtys): d.reject(); return
            sub = sum(qtys[n] * items[n]["price"] for n in range(len(items)))
            tax = round(sub * float(SET.get("vat", 15)) / 100, 2)
            no = inv_no("RT")
            sid = x("INSERT INTO sales(invoice_no,ts,username,customer_id,location_id,"
                    "shift_id,subtotal,discount,tax,total,paid_cash,paid_card,change,"
                    "status,notes) VALUES(?,?,?,?,?,NULL,?,0,?,?,0,0,0,'return',?)",
                    (no, nows(), CUR_USER["username"], sale["customer_id"],
                     sale["location_id"], -sub, -tax, -(sub + tax), rs.text()))
            for n, it in enumerate(items):
                if qtys[n] > 0:
                    x("INSERT INTO sale_items(sale_id,product_id,name,qty,price,cost,total) "
                      "VALUES(?,?,?,?,?,?,?)",
                      (sid, it["product_id"], it["name"], -qtys[n], it["price"],
                       it["cost"], -qtys[n] * it["price"]))
                    move_stock(it["product_id"], sale["location_id"], qtys[n], "return", no)
            x("UPDATE sales SET status='returned' WHERE id=?", (i,))
            log("return", f"{sale['invoice_no']} → {no}")
            QMessageBox.information(s, APP, T("Return processed"))
            s.refresh(); d.accept()
        ok.clicked.connect(do)
        d.resize(620, 440); d.exec()

class InventoryPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        tb = QTabWidget(); v.addWidget(tb)
        cat_items = [("__all__", T("All"))] + \
            [(c["id"], c["name"]) for c in q("SELECT * FROM categories ORDER BY name")]
        cat_opts = lambda: [(c["id"], c["name"])
                            for c in q("SELECT * FROM categories ORDER BY name")]
        s.prod = TableEditor(mw, "products",
            [("barcode","Code"),("name","Product Name"),("name_ar","Name (AR)"),
             ("price","Price"),("cost","Cost"),("min_stock","Min Stock")],
            [("barcode","Code","text",None),("name","Product Name","text",None),
             ("name_ar","Name (AR)","text",None),("category_id","Category","combo",cat_opts),
             ("unit","Unit","text",None),("cost","Cost","num",None),
             ("price","Price","num",None),("min_stock","Min Stock","num",None),
             ("icon","Icon","text",None),("active","Active","check",None)],
            search_cols=["barcode","name","name_ar"], order="id DESC",
            module="inventory", filters=(cat_items, "category_id"))
        tb.addTab(s.prod, "📦 " + T("Products")); s.prod.refresh()
        bar = QHBoxLayout()
        b1 = QPushButton("🏷️ " + T("Barcode Labels")); b1.setObjectName("primary")
        b1.clicked.connect(s.labels); bar.addWidget(b1)
        b2 = QPushButton("📥 " + T("Import CSV")); b2.clicked.connect(s.import_csv)
        bar.addWidget(b2)
        b3 = QPushButton("⚖️ " + T("Adjust Stock")); b3.setObjectName("warn")
        b3.clicked.connect(s.adjust); bar.addWidget(b3)
        bar.addStretch(1); v.addLayout(bar)
        s.cats = TableEditor(mw, "categories", [("name","Category")],
                             [("name","Category","text",None)], module="inventory")
        tb.addTab(s.cats, "🗂 " + T("Categories")); s.cats.refresh()
        st = QWidget(); sv = QVBoxLayout(st)
        sh = QHBoxLayout(); s.sl = QComboBox()
        for l in q("SELECT * FROM locations"): s.sl.addItem("🏬 " + l["name"], l["id"])
        s.sl.currentIndexChanged.connect(s.load_stock)
        sh.addWidget(QLabel("🏬 " + T("Location"))); sh.addWidget(s.sl)
        sh.addStretch(1); sv.addLayout(sh)
        s.stbl = QTableWidget(); s.stbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.stbl.verticalHeader().setVisible(False); sv.addWidget(s.stbl)
        tb.addTab(st, "📊 " + T("Stock by Location")); s.load_stock()
    def load_stock(s):
        lid = s.sl.currentData()
        rows = q("""SELECT p.barcode,p.name,p.name_ar,IFNULL(st.qty,0) qty,p.min_stock,p.price
                 FROM products p LEFT JOIN stock st ON st.product_id=p.id AND st.location_id=?
                 WHERE p.active=1 ORDER BY p.name""", (lid,))
        hdr = [T("Code"), T("Product Name"), T("Qty"), T("Min Stock"), T("Price"), T("Status")]
        s.stbl.clear(); s.stbl.setColumnCount(6); s.stbl.setRowCount(len(rows))
        s.stbl.setHorizontalHeaderLabels(hdr)
        s.stbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for i, r in enumerate(rows):
            stat = "🔴" if r["qty"] <= 0 else "🟠" if r["qty"] < r["min_stock"] else "🟢"
            for j, val in enumerate([r["barcode"], disp_name(r), f"{r['qty']:g}",
                                     f"{r['min_stock']:g}", money(r["price"]), stat]):
                it = QTableWidgetItem(str(val)); it.setTextAlignment(Qt.AlignCenter)
                s.stbl.setItem(i, j, it)
    def adjust(s):
        d = QDialog(s); d.setWindowTitle("⚖️ " + T("Adjust Stock")); f = QFormLayout(d)
        pc = QComboBox()
        for p in q("SELECT * FROM products WHERE active=1 ORDER BY name"):
            pc.addItem(disp_name(p), p["id"])
        lc = QComboBox()
        for l in q("SELECT * FROM locations"): lc.addItem(l["name"], l["id"])
        curv = QLabel("—"); new = QDoubleSpinBox(); new.setMaximum(10**7)
        rs = QLineEdit(); rs.setPlaceholderText(T("Reason"))
        def upd():
            r = q1("SELECT qty FROM stock WHERE product_id=? AND location_id=?",
                   (pc.currentData(), lc.currentData()))
            curv.setText(f"{r['qty']:g}" if r else "0")
        pc.currentIndexChanged.connect(upd); lc.currentIndexChanged.connect(upd); upd()
        ok = QPushButton("✅ " + T("Save")); ok.setObjectName("warn")
        f.addRow(T("Product"), pc); f.addRow(T("Location"), lc)
        f.addRow(T("Stock:"), curv); f.addRow(T("New Qty"), new)
        f.addRow(T("Reason"), rs); f.addRow(ok)
        def do():
            pid, lid = pc.currentData(), lc.currentData()
            r = q1("SELECT qty FROM stock WHERE product_id=? AND location_id=?", (pid, lid))
            old = r["qty"] if r else 0
            move_stock(pid, lid, new.value() - old, "adjust:" + (rs.text() or "-"))
            log("stock_adjust", f"pid={pid} {old}→{new.value():g}")
            s.load_stock(); d.accept()
        ok.clicked.connect(do); d.exec()
    def labels(s):
        pid = s.prod.sel_id()
        if not pid: QMessageBox.information(s, APP, T("Nothing selected")); return
        p = q1("SELECT * FROM products WHERE id=?", (pid,))
        n = QSpinBox(); n.setRange(1, 100); n.setValue(12)
        d = QDialog(s); f = QFormLayout(d); f.addRow(T("Copies"), n)
        ok = QPushButton("🖨 " + T("Print")); ok.setObjectName("primary"); f.addRow(ok)
        def do():
            imgs = {"bar": code39_pixmap(p["barcode"]).toImage()}
            cell = ("<td width='33%' align=center style='border:1px dashed #999;padding:6px;'>"
                    "<div style='font-size:11px;font-weight:700;'>" + disp_name(p) + "</div>"
                    "<div style='font-size:13px;font-weight:800;'>" + money(p["price"]) +
                    " " + cur() + "</div>"
                    "<img src='bar' width='150' height='42'>"
                    "<div style='font-size:10px;'>" + p["barcode"] + "</div></td>")
            html = "<table width=100% cellpadding=2>"; k = 0
            for i in range(n.value()):
                if k % 3 == 0: html += "<tr>"
                html += cell; k += 1
                if k % 3 == 0: html += "</tr>"
            if k % 3: html += "</tr>"
            do_print(html + "</table>", imgs, a4=True, parent=s); d.accept()
        ok.clicked.connect(do); d.exec()
    def import_csv(s):
        path, _ = QFileDialog.getOpenFileName(s, T("Import CSV"), "", "CSV (*.csv)")
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
                        x("UPDATE products SET name=?,name_ar=?,cost=?,price=?,min_stock=? "
                          "WHERE id=?", (nm, nar, cost, price, mn, ex["id"]))
                    else:
                        pid = x("INSERT INTO products(barcode,name,name_ar,cost,price,"
                                "min_stock) VALUES(?,?,?,?,?,?)", (bc, nm, nar, cost, price, mn))
                        for l in q("SELECT id FROM locations"):
                            x("INSERT INTO stock(product_id,location_id,qty) VALUES(?,?,0)",
                              (pid, l["id"]))
                    n += 1
        except Exception as e:
            QMessageBox.critical(s, APP, str(e)); return
        log("import_csv", f"{n} products"); s.prod.refresh()
        QMessageBox.information(s, APP, f"{T('Imported')}: {n}")

class LocationsPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        type_opts = lambda: [("branch", T("Branch")), ("warehouse", T("Warehouse")),
                             ("store", T("Store"))]
        s.ed = TableEditor(mw, "locations", [("name","Location"),("type","Type")],
            [("name","Location","text",None),("type","Type","combo",type_opts)],
            search_cols=["name"], module="locations", on_change=s.load)
        v.addWidget(s.ed, 1)
        tr = QHBoxLayout(); tr.addStretch(1)
        tb = QPushButton("🔄 " + T("Transfer Stock")); tb.setObjectName("primary")
        tb.clicked.connect(s.transfer); tr.addWidget(tb); v.addLayout(tr)
        lab = QLabel("📊 " + T("Stock by Location")); lab.setObjectName("h1"); v.addWidget(lab)
        s.st = QTableWidget(); s.st.setEditTriggers(QTableWidget.NoEditTriggers)
        s.st.verticalHeader().setVisible(False); v.addWidget(s.st, 1)
        s.load()
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
    def transfer(s):
        d = QDialog(s); d.setWindowTitle("🔄 " + T("Transfer Stock")); f = QFormLayout(d)
        a = QComboBox(); b = QComboBox()
        for l in q("SELECT * FROM locations"):
            a.addItem(l["name"], l["id"]); b.addItem(l["name"], l["id"])
        prod = QComboBox()
        for p in q("SELECT * FROM products WHERE active=1"):
            prod.addItem(disp_name(p), p["id"])
        qt = QDoubleSpinBox(); qt.setMaximum(10**6)
        f.addRow(T("From"), a); f.addRow(T("To"), b)
        f.addRow(T("Product"), prod); f.addRow(T("Qty"), qt)
        ok = QPushButton("✅ " + T("Confirm")); ok.setObjectName("success"); f.addRow(ok)
        def do():
            pid = prod.currentData()
            st = q1("SELECT qty FROM stock WHERE product_id=? AND location_id=?",
                    (pid, a.currentData()))
            if not st or st["qty"] < qt.value():
                QMessageBox.warning(d, APP, "📦 " + T("Insufficient payment!")); return
            move_stock(pid, a.currentData(), -qt.value(), "transfer-out")
            move_stock(pid, b.currentData(), qt.value(), "transfer-in")
            log("transfer", f"prod={pid} {qt.value():g}")
            s.load(); d.accept()
        ok.clicked.connect(do); d.exec()

class PurchasesPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        top = QHBoxLayout()
        nb = QPushButton("🚚 " + T("New Purchase")); nb.setObjectName("primary")
        nb.clicked.connect(s.new_purchase); top.addWidget(nb); top.addStretch(1)
        v.addLayout(top)
        s.tbl = QTableWidget(0, 6)
        s.tbl.setHorizontalHeaderLabels([T("Ref No"), T("Date"), T("Total Cost"),
                                         T("Paid"), T("Status"), T("Supplier")])
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v.addWidget(s.tbl, 1); s.ids = []
        bot = QHBoxLayout()
        pay = QPushButton("💵 " + T("Pay Supplier")); pay.setObjectName("success")
        pay.clicked.connect(s.pay_supp); bot.addWidget(pay)
        led = QPushButton("📖 " + T("Ledger")); led.clicked.connect(s.ledger)
        bot.addWidget(led); bot.addStretch(1); v.addLayout(bot)
        s.refresh()
    def refresh(s):
        rows = q("""SELECT p.*, sp.name sname FROM purchases p
                 LEFT JOIN suppliers sp ON sp.id=p.supplier_id ORDER BY p.id DESC""")
        s.tbl.setRowCount(len(rows)); s.ids = [r["id"] for r in rows]
        for i, r in enumerate(rows):
            for j, val in enumerate([r["ref_no"], r["ts"], money(r["total"]),
                                     money(r["paid"]), T(r["status"]), r["sname"] or ""]):
                it = QTableWidgetItem(str(val)); it.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, it)
    def new_purchase(s):
        d = QDialog(s); d.setWindowTitle("🚚 " + T("New Purchase"))
        d.resize(640, 460); v = QVBoxLayout(d)
        g = QFormLayout()
        sup = QComboBox()
        for sp in q("SELECT * FROM suppliers"): sup.addItem("🏭 " + sp["name"], sp["id"])
        loc = QComboBox()
        for l in q("SELECT * FROM locations"): loc.addItem("🏬 " + l["name"], l["id"])
        g.addRow(T("Supplier"), sup); g.addRow(T("Location"), loc); v.addLayout(g)
        t = QTableWidget(0, 4)
        t.setHorizontalHeaderLabels([T("Product"), T("Qty"), T("Cost"), T("Total")])
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        prods = q("SELECT * FROM products WHERE active=1 ORDER BY name")
        def addrow():
            r = t.rowCount(); t.insertRow(r)
            c = QComboBox()
            for p in prods: c.addItem(disp_name(p), p["id"])
            qs = QDoubleSpinBox(); qs.setMaximum(10**6)
            cs = QDoubleSpinBox(); cs.setMaximum(10**7); cs.setDecimals(2)
            lab = QLabel("0.00"); lab.setAlignment(Qt.AlignCenter)
            upd = lambda *_: lab.setText(money(qs.value() * cs.value()))
            qs.valueChanged.connect(upd); cs.valueChanged.connect(upd)
            t.setCellWidget(r, 0, c); t.setCellWidget(r, 1, qs)
            t.setCellWidget(r, 2, cs); t.setCellWidget(r, 3, lab)
        addrow(); v.addWidget(t, 1)
        ar = QHBoxLayout()
        ab = QPushButton("➕ " + T("Add")); ab.setObjectName("primary")
        ab.clicked.connect(addrow); ar.addWidget(ab)
        rb = QPushButton("➖")
        rb.clicked.connect(lambda: t.rowCount() > 1 and t.removeRow(t.rowCount() - 1))
        ar.addWidget(rb)
        paid = QDoubleSpinBox(); paid.setMaximum(10**7)
        ar.addWidget(QLabel(T("Paid") + " 💵")); ar.addWidget(paid); v.addLayout(ar)
        ok = QPushButton("💾 " + T("Save")); ok.setObjectName("success"); v.addWidget(ok)
        def do():
            rows = [(t.cellWidget(r, 0).currentData(), t.cellWidget(r, 1).value(),
                     t.cellWidget(r, 2).value()) for r in range(t.rowCount())]
            rows = [r for r in rows if r[1] > 0]
            if not rows: d.reject(); return
            no = inv_no("PO"); tot = 0
            pid = x("INSERT INTO purchases(ref_no,ts,supplier_id,location_id,username,"
                    "total,paid,status) VALUES(?,?,?,?,?,0,0,'unpaid')",
                    (no, nows(), sup.currentData(), loc.currentData(), CUR_USER["username"]))
            for p_, qt, cs in rows:
                tot += qt * cs
                x("INSERT INTO purchase_items(purchase_id,product_id,qty,cost,total) "
                  "VALUES(?,?,?,?,?)", (pid, p_, qt, cs, qt * cs))
                x("UPDATE products SET cost=? WHERE id=?", (cs, p_))
                move_stock(p_, loc.currentData(), qt, "purchase", no)
            paidv = min(paid.value(), tot)
            status = "paid" if paidv >= tot - 0.001 else "partial" if paidv > 0 else "unpaid"
            x("UPDATE purchases SET total=?,paid=?,status=? WHERE id=?",
              (tot, paidv, status, pid))
            x("UPDATE suppliers SET balance=balance+? WHERE id=?",
              (tot - paidv, sup.currentData()))
            if paidv > 0:
                x("INSERT INTO payments(ts,party_type,party_id,amount,direction,method,"
                  "username) VALUES(?,?,?,?,?,?,?)",
                  (nows(), "supplier", sup.currentData(), paidv, "out", "cash",
                   CUR_USER["username"]))
            log("purchase", f"{no} total={tot}")
            QMessageBox.information(s, APP, T("Purchase saved"))
            s.refresh(); d.accept()
        ok.clicked.connect(do); d.exec()
    def pay_supp(s):
        c = QComboBox()
        for sp in q("SELECT * FROM suppliers"):
            c.addItem(f"{sp['name']} — {money(sp['balance'])}", sp["id"])
        amt = QDoubleSpinBox(); amt.setMaximum(10**7)
        d = QDialog(s); f = QFormLayout(d)
        f.addRow(T("Supplier"), c); f.addRow(T("Amount"), amt)
        ok = QPushButton("💾 " + T("Save")); ok.setObjectName("success"); f.addRow(ok)
        def do():
            x("INSERT INTO payments(ts,party_type,party_id,amount,direction,method,"
              "username) VALUES(?,?,?,?,?,?,?)",
              (nows(), "supplier", c.currentData(), amt.value(), "out", "cash",
               CUR_USER["username"]))
            x("UPDATE suppliers SET balance=balance-? WHERE id=?",
              (amt.value(), c.currentData()))
            log("supplier_payment", str(amt.value()))
            QMessageBox.information(s, APP, T("Payment saved"))
            s.refresh(); d.accept()
        ok.clicked.connect(do); d.exec()
    def ledger(s):
        c = QComboBox()
        for sp in q("SELECT * FROM suppliers"): c.addItem(sp["name"], sp["id"])
        d = QDialog(s); f = QFormLayout(d); f.addRow(T("Supplier"), c)
        ok = QPushButton("📖 " + T("Ledger")); f.addRow(ok)
        def do():
            sid = c.currentData(); sp = q1("SELECT * FROM suppliers WHERE id=?", (sid,))
            pur = q("SELECT * FROM purchases WHERE supplier_id=? ORDER BY ts DESC", (sid,))
            pays = q("SELECT * FROM payments WHERE party_type='supplier' AND party_id=? "
                     "ORDER BY ts DESC", (sid,))
            txt = (f"<h2>📖 {T('Ledger')} — {sp['name']}</h2><p>{T('Balance')}: "
                   f"<b>{money(sp['balance'])} {cur()}</b></p>"
                   f"<h3>🚚 {T('Purchases')}</h3><table width=100% cellpadding=5 border=1>")
            for p in pur:
                txt += (f"<tr><td>{p['ref_no']}</td><td>{p['ts']}</td>"
                        f"<td align=right>{money(p['total'])}</td>"
                        f"<td align=right>{money(p['paid'])}</td><td>{T(p['status'])}</td></tr>")
            txt += f"</table><h3>💵 {T('Payment')}</h3><table width=100% cellpadding=5 border=1>"
            for p in pays:
                txt += f"<tr><td>{p['ts']}</td><td align=right>{money(p['amount'])}</td></tr>"
            do_print(txt + "</table>", a4=True, parent=s)
        ok.clicked.connect(do); d.exec()

class QuotesPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        top = QHBoxLayout()
        nb = QPushButton("➕ " + T("New Quotation")); nb.setObjectName("primary")
        nb.clicked.connect(s.editor); top.addWidget(nb); top.addStretch(1)
        v.addLayout(top)
        s.tbl = QTableWidget(0, 6)
        s.tbl.setHorizontalHeaderLabels([T("Invoice No"), T("Date"), T("Customer"),
                                         T("Grand Total"), T("Status"), T("Valid Until")])
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v.addWidget(s.tbl, 1); s.ids = []
        bot = QHBoxLayout()
        for lab, fn, sty in [("✅ " + T("Approve"), lambda: s.setst("approved"), "success"),
                             ("❌ " + T("Reject"), lambda: s.setst("rejected"), "danger"),
                             ("🧾 " + T("Convert to Invoice"), s.convert, "primary"),
                             ("📄 " + T("Print A4"), s.printq, "")]:
            b = QPushButton(lab); b.setObjectName(sty); b.clicked.connect(fn)
            bot.addWidget(b)
        bot.addStretch(1); v.addLayout(bot); s.refresh()
    def refresh(s):
        rows = q("""SELECT q.*, c.name cname FROM quotations q
                 LEFT JOIN customers c ON c.id=q.customer_id ORDER BY q.id DESC""")
        s.tbl.setRowCount(len(rows)); s.ids = [r["id"] for r in rows]
        for i, r in enumerate(rows):
            for j, val in enumerate([r["quote_no"], r["ts"], r["cname"] or "",
                                     money(r["total"]), T(r["status"]), r["valid_until"]]):
                it = QTableWidgetItem(str(val)); it.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, it)
    def sel(s):
        r = s.tbl.currentRow()
        return s.ids[r] if 0 <= r < len(s.ids) else None
    def setst(s, st):
        i = s.sel()
        if i:
            x("UPDATE quotations SET status=? WHERE id=?", (st, i))
            log("quote_status", f"{i}→{st}"); s.refresh()
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
                f"<p>{T('Valid Until')}: {qd['valid_until']} — {T(qd['status'])}</p>"
                f"<table width=100% cellpadding=6 border=1>{rows}</table>"
                f"<h3>{T('Grand Total')}: {money(qd['total'])} {cur()}</h3>")
        do_print(html, a4=True, parent=s)
    def editor(s):
        d = QDialog(s); d.setWindowTitle("📑 " + T("New Quotation"))
        d.resize(680, 520); v = QVBoxLayout(d); g = QFormLayout()
        cust = QComboBox()
        for c in q("SELECT * FROM customers"): cust.addItem("👤 " + c["name"], c["id"])
        val = QDateEdit(QDate.currentDate().addDays(14)); val.setCalendarPopup(True)
        terms = QLineEdit(); terms.setPlaceholderText(T("Terms"))
        g.addRow(T("Customer"), cust); g.addRow(T("Valid Until"), val)
        g.addRow(T("Terms"), terms); v.addLayout(g)
        t = QTableWidget(0, 4)
        t.setHorizontalHeaderLabels([T("Product"), T("Qty"), T("Price"), T("Total")])
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        prods = q("SELECT * FROM products WHERE active=1 ORDER BY name")
        def addrow():
            r = t.rowCount(); t.insertRow(r)
            c = QComboBox()
            for p in prods: c.addItem(disp_name(p), p["id"])
            qs = QDoubleSpinBox(); qs.setMaximum(10**6)
            ps = QDoubleSpinBox(); ps.setMaximum(10**7); ps.setDecimals(2)
            lab = QLabel("0.00"); lab.setAlignment(Qt.AlignCenter)
            upd = lambda *_: lab.setText(money(qs.value() * ps.value()))
            qs.valueChanged.connect(upd); ps.valueChanged.connect(upd)
            t.setCellWidget(r, 0, c); t.setCellWidget(r, 1, qs)
            t.setCellWidget(r, 2, ps); t.setCellWidget(r, 3, lab)
        addrow(); v.addWidget(t, 1)
        ar = QHBoxLayout()
        ab = QPushButton("➕ " + T("Add")); ab.setObjectName("primary")
        ab.clicked.connect(addrow); ar.addWidget(ab)
        rb = QPushButton("➖")
        rb.clicked.connect(lambda: t.rowCount() > 1 and t.removeRow(t.rowCount() - 1))
        ar.addWidget(rb); ar.addStretch(1)
        totl = QLabel(T("Grand Total") + ": 0.00"); totl.setObjectName("big")
        ar.addWidget(totl); v.addLayout(ar)
        ok = QPushButton("💾 " + T("Save")); ok.setObjectName("success"); v.addWidget(ok)
        def recalc():
            tt = sum(t.cellWidget(r, 1).value() * t.cellWidget(r, 2).value()
                     for r in range(t.rowCount()))
            totl.setText(T("Grand Total") + ": " + money(tt))
        tm = QTimer(d); tm.timeout.connect(recalc); tm.start(400)
        def do():
            no = inv_no("QT"); sub = 0
            qid = x("INSERT INTO quotations(quote_no,ts,customer_id,valid_until,subtotal,"
                    "discount,tax,total,status,notes) VALUES(?,?,?,?,?,0,0,0,'draft',?)",
                    (no, nows(), cust.currentData(),
                     val.date().toString("yyyy-MM-dd"), terms.text()))
            for r in range(t.rowCount()):
                p_ = t.cellWidget(r, 0).currentData()
                qt = t.cellWidget(r, 1).value(); ps = t.cellWidget(r, 2).value()
                if qt <= 0: continue
                sub += qt * ps
                nm = disp_name(q1("SELECT * FROM products WHERE id=?", (p_,)))
                x("INSERT INTO quote_items(quote_id,product_id,name,qty,price,total) "
                  "VALUES(?,?,?,?,?,?)", (qid, p_, nm, qt, ps, qt * ps))
            vat = round(sub * float(SET.get("vat", 15)) / 100, 2)
            x("UPDATE quotations SET subtotal=?,tax=?,total=? WHERE id=?",
              (sub, vat, round(sub + vat, 2), qid))
            log("quote_new", no)
            QMessageBox.information(s, APP, T("Quotation saved"))
            s.refresh(); d.accept()
        ok.clicked.connect(do); d.exec()
    def convert(s):
        i = s.sel()
        if not i: return
        qd = q1("SELECT * FROM quotations WHERE id=?", (i,))
        if qd["status"] == "converted": return
        its = q("SELECT * FROM quote_items WHERE quote_id=?", (i,))
        no = inv_no("SL")
        sid = x("INSERT INTO sales(invoice_no,ts,username,customer_id,location_id,"
                "shift_id,subtotal,discount,tax,total,paid_cash,paid_card,change,"
                "status,notes) VALUES(?,?,?,?,NULL,NULL,?,0,?,?,0,0,0,'unpaid',?)",
                (no, nows(), CUR_USER["username"], qd["customer_id"],
                 qd["subtotal"], qd["tax"], qd["total"], qd["quote_no"]))
        for it in its:
            x("INSERT INTO sale_items(sale_id,product_id,name,qty,price,cost,total) "
              "VALUES(?,?,?,?,?,0,?)",
              (sid, it["product_id"], it["name"], it["qty"], it["price"],
               it["price"] * it["qty"]))
        if qd["customer_id"]:
            x("UPDATE customers SET balance=balance+? WHERE id=?",
              (qd["total"], qd["customer_id"]))
        x("UPDATE quotations SET status='converted' WHERE id=?", (i,))
        log("quote_convert", f"{qd['quote_no']}→{no}")
        QMessageBox.information(s, APP, T("Quote converted to invoice") + ": " + no)
        s.refresh()

class EInvoicePage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        sp = QSplitter()
        left = QWidget(); lv = QVBoxLayout(left)
        s.tbl = QTableWidget(0, 3)
        s.tbl.setHorizontalHeaderLabels([T("Invoice No"), T("Date"), T("Grand Total")])
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
                             ("🖨 " + T("Tax Invoice"), s.printx, "success")]:
            b = QPushButton(lab); b.setObjectName(sty); b.clicked.connect(fn)
            bot.addWidget(b)
        bot.addStretch(1); v.addLayout(bot)
        s.tbl.currentRowChanged.connect(s.show_qr); s.rows = []; s.refresh()
    def refresh(s):
        rows = q("SELECT * FROM sales WHERE status IN ('completed','unpaid') "
                 "ORDER BY id DESC LIMIT 200")
        s.rows = [r["id"] for r in rows]; s.tbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, val in enumerate([r["invoice_no"], r["ts"], money(r["total"])]):
                it = QTableWidgetItem(str(val)); it.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, it)
    def cur_sale(s):
        r = s.tbl.currentRow()
        return q1("SELECT * FROM sales WHERE id=?", (s.rows[r],)) \
               if 0 <= r < len(s.rows) else None
    def show_qr(s, *_):
        sale = s.cur_sale()
        if not sale: return
        p = zatca_qr_payload(sale); s.tlv.setPlainText(p)
        img = qr_image(p, 200)
        if img: s.qr.setPixmap(QPixmap.fromImage(img))
    def json(s):
        sale = s.cur_sale()
        if not sale: QMessageBox.information(s, APP, T("Nothing selected")); return
        items = q("SELECT * FROM sale_items WHERE sale_id=?", (sale["id"],))
        doc = {"invoice": sale["invoice_no"], "timestamp": sale["ts"],
               "seller": {"name_ar": SET.get("company_ar"), "vat": SET.get("tax_no")},
               "totals": {k: sale[k] for k in ("subtotal", "discount", "tax", "total")},
               "qr": zatca_qr_payload(sale), "lines": [dict(it) for it in items]}
        path, _ = QFileDialog.getSaveFileName(s, "JSON", sale["invoice_no"] + ".json")
        if path:
            open(path, "w", encoding="utf-8").write(
                json.dumps(doc, ensure_ascii=False, indent=2))
            QMessageBox.information(s, APP, T("Exported"))
    def xml(s):
        sale = s.cur_sale()
        if not sale: QMessageBox.information(s, APP, T("Nothing selected")); return
        items = q("SELECT * FROM sale_items WHERE sale_id=?", (sale["id"],))
        x_ = [f"<Invoice no='{sale['invoice_no']}' ts='{sale['ts']}' "
              f"currency='{SET.get('currency')}'>",
              f"<Seller name='{SET.get('company')}' vat='{SET.get('tax_no')}'/>"]
        for it in items:
            x_.append(f"<Line name='{it['name']}' qty='{it['qty']}' "
                      f"price='{it['price']}' total='{it['total']}'/>")
        x_.append(f"<Totals subtotal='{sale['subtotal']}' discount='{sale['discount']}' "
                  f"vat='{sale['tax']}' total='{sale['total']}'/>")
        x_.append(f"<QR base64='{zatca_qr_payload(sale)}'/></Invoice>")
        path, _ = QFileDialog.getSaveFileName(s, "XML", sale["invoice_no"] + ".xml")
        if path:
            open(path, "w", encoding="utf-8").write("\n".join(x_))
            QMessageBox.information(s, APP, T("Exported"))
    def printx(s):
        sale = s.cur_sale()
        if sale: print_a4(sale["id"], tax=True, parent=s)

class PartiesPage(QWidget):
    def __init__(s, mw, kind="customers"):
        super().__init__(); s.mw = mw; s.kind = kind; v = QVBoxLayout(s)
        if kind == "customers":
            tier_opts = lambda: [("Bronze", T("Bronze")), ("Silver", T("Silver")),
                                 ("Gold", T("Gold"))]
            s.ed = TableEditor(mw, "customers",
                [("name","Customer"),("phone","Phone"),("tier","Tier"),
                 ("points","Points"),("balance","Balance")],
                [("name","Customer","text",None),("phone","Phone","text",None),
                 ("tier","Tier","combo",tier_opts),("points","Points","num",None),
                 ("balance","Balance","num",None),("notes","Notes","memo",None)],
                search_cols=["name","phone"], module=kind)
        else:
            s.ed = TableEditor(mw, "suppliers",
                [("name","Supplier"),("phone","Phone"),("balance","Balance")],
                [("name","Supplier","text",None),("phone","Phone","text",None),
                 ("balance","Balance","num",None),("notes","Notes","memo",None)],
                search_cols=["name","phone"], module=kind)
        v.addWidget(s.ed, 1); s.ed.refresh()
        bot = QHBoxLayout()
        b1 = QPushButton("💵 " + (T("Receive Payment") if kind == "customers"
                                  else T("Pay Supplier")))
        b1.setObjectName("success"); b1.clicked.connect(s.pay); bot.addWidget(b1)
        b2 = QPushButton("📖 " + T("Ledger")); b2.setObjectName("primary")
        b2.clicked.connect(s.ledger); bot.addWidget(b2)
        bot.addStretch(1); v.addLayout(bot)
    def pay(s):
        c = QComboBox()
        for r in q(f"SELECT * FROM {s.kind}"): c.addItem(r["name"], r["id"])
        amt = QDoubleSpinBox(); amt.setMaximum(10**7)
        d = QDialog(s); f = QFormLayout(d)
        f.addRow(T("Customer") if s.kind == "customers" else T("Supplier"), c)
        f.addRow(T("Amount"), amt)
        ok = QPushButton("💾 " + T("Save")); ok.setObjectName("success"); f.addRow(ok)
        def do():
            dr = "in" if s.kind == "customers" else "out"
            x("INSERT INTO payments(ts,party_type,party_id,amount,direction,method,"
              "username) VALUES(?,?,?,?,?,?,?)",
              (nows(), s.kind, c.currentData(), amt.value(), dr, "cash",
               CUR_USER["username"]))
            x(f"UPDATE {s.kind} SET balance=balance-? WHERE id=?",
              (amt.value(), c.currentData()))
            log(f"{s.kind}_payment", str(amt.value()))
            QMessageBox.information(s, APP, T("Payment saved"))
            s.ed.refresh(); d.accept()
        ok.clicked.connect(do); d.exec()
    def ledger(s):
        i = s.ed.sel_id()
        if not i: QMessageBox.information(s, APP, T("Nothing selected")); return
        r = q1(f"SELECT * FROM {s.kind} WHERE id=?", (i,))
        pays = q("SELECT * FROM payments WHERE party_type=? AND party_id=? "
                 "ORDER BY ts DESC", (s.kind, r["id"]))
        if s.kind == "customers":
            docs = q("SELECT invoice_no,ts,total,status FROM sales WHERE customer_id=? "
                     "ORDER BY ts DESC LIMIT 30", (r["id"],))
        else:
            docs = q("SELECT ref_no invoice_no,ts,total,status FROM purchases "
                     "WHERE supplier_id=? ORDER BY ts DESC LIMIT 30", (r["id"],))
        html = (f"<h2>📖 {T('Ledger')} — {r['name']}</h2><p>{T('Balance')}: "
                f"<b>{money(r['balance'])} {cur()}</b></p>"
                f"<h3>{T('Invoice No')}</h3><table width=100% cellpadding=5 border=1>")
        for d_ in docs:
            html += (f"<tr><td>{d_['invoice_no']}</td><td>{d_['ts']}</td>"
                     f"<td align=right>{money(d_['total'])}</td>"
                     f"<td>{T(d_['status'])}</td></tr>")
        html += f"</table><h3>{T('Payment')}</h3><table width=100% cellpadding=5 border=1>"
        for p in pays:
            html += (f"<tr><td>{p['ts']}</td>"
                     f"<td align=right>{money(p['amount'])} ({p['direction']})</td></tr>")
        do_print(html + "</table>", a4=True, parent=s)

class OffersPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        tb = QTabWidget(); v.addWidget(tb)
        f = QWidget(); fv = QFormLayout(f)
        s.w = {}
        for key, lab in [("loyalty_earn","Earn"),("loyalty_redeem","Points"),
                         ("tier_silver","Silver"),("tier_gold","Gold"),
                         ("tier_silver_disc","Percent %"),("tier_gold_disc","Percent %")]:
            sp = QDoubleSpinBox(); sp.setMaximum(10**6); sp.setDecimals(2)
            sp.setValue(float(SET.get(key, 0))); s.w[key] = sp
            fv.addRow("⭐ " + T(lab) + " — " + key, sp)
        b = QPushButton("💾 " + T("Save")); b.setObjectName("success")
        b.clicked.connect(s.save); fv.addRow(b)
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
            [("scope","Type","combo",sc_opts),("target","Product","text",None),
             ("percent","Percent %","num",None),("starts","Starts","date",None),
             ("ends","Ends","date",None),("active","Active","check",None)],
            module="offers")
        tb.addTab(s.of, "🏷️ " + T("Offers")); s.of.refresh()
    def save(s):
        for k, w in s.w.items():
            x("INSERT INTO settings(key,value) VALUES(?,?) "
              "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, str(w.value())))
        load_settings(); log("loyalty_settings")
        QMessageBox.information(s, APP, T("Saved"))

class ShiftsPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        card = QFrame(); card.setObjectName("card"); c = QHBoxLayout(card)
        s.stat = QLabel(); s.stat.setObjectName("h1"); c.addWidget(s.stat); c.addStretch(1)
        b1 = QPushButton("🔓 " + T("Open Shift")); b1.setObjectName("success")
        b1.clicked.connect(s.open_shift); c.addWidget(b1)
        b2 = QPushButton("🔒 " + T("Close Shift")); b2.setObjectName("danger")
        b2.clicked.connect(s.close_shift); c.addWidget(b2)
        v.addWidget(card)
        s.tbl = QTableWidget(0, 8)
        s.tbl.setHorizontalHeaderLabels([T("Cashier"), T("Date"), T("Opening Cash"),
            T("Counted Cash"), T("Expected"), T("Difference"), T("Status"), T("Notes")])
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
                    money(r["difference"] or 0), T(r["status"]), r["notes"] or ""]
            for j, val in enumerate(vals):
                it = QTableWidgetItem(str(val)); it.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, it)
    def open_shift(s):
        if q1("SELECT * FROM shifts WHERE status='open' AND username=?",
              (CUR_USER["username"],)):
            QMessageBox.information(s, APP, T("Shift opened")); return
        amt = QDoubleSpinBox(); amt.setMaximum(10**7)
        d = QDialog(s); f = QFormLayout(d); f.addRow(T("Opening Cash"), amt)
        ok = QPushButton("✅ " + T("Open Shift")); ok.setObjectName("success"); f.addRow(ok)
        def do():
            lid = q1("SELECT id FROM locations LIMIT 1")["id"]
            x("INSERT INTO shifts(username,location_id,opened_at,opening_cash,status) "
              "VALUES(?,?,?,?,'open')", (CUR_USER["username"], lid, nows(), amt.value()))
            log("shift_open"); s.refresh(); d.accept()
        ok.clicked.connect(do); d.exec()
    def close_shift(s):
        sh = q1("SELECT * FROM shifts WHERE status='open' AND username=? "
                "ORDER BY id DESC", (CUR_USER["username"],))
        if not sh: QMessageBox.warning(s, APP, T("No open shift!")); return
        exp = sh["opening_cash"] + q1(
            "SELECT IFNULL(SUM(paid_cash-change),0) v FROM sales "
            "WHERE shift_id=? AND status='completed'", (sh["id"],))["v"]
        cnt = QDoubleSpinBox(); cnt.setMaximum(10**7); cnt.setValue(exp)
        d = QDialog(s); f = QFormLayout(d)
        f.addRow(T("Expected"), QLabel(money(exp) + " " + cur()))
        f.addRow(T("Counted Cash"), cnt)
        ok = QPushButton("🔒 " + T("Close Shift")); ok.setObjectName("danger"); f.addRow(ok)
        def do():
            diff = cnt.value() - exp
            x("UPDATE shifts SET closed_at=?,counted_cash=?,expected_cash=?,"
              "difference=?,status='closed' WHERE id=?",
              (nows(), cnt.value(), exp, diff, sh["id"]))
            log("shift_close", f"diff={diff}")
            sales = q("SELECT invoice_no,total,status FROM sales WHERE shift_id=?",
                      (sh["id"],))
            html = (f"<h1>🕒 {T('Shift Report')} — {CUR_USER['username']}</h1>"
                    f"<p>{sh['opened_at']} → {nows()}</p>"
                    f"<p>{T('Opening Cash')}: {money(sh['opening_cash'])} • "
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

class WorkOrdersPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        tb = QTabWidget(); v.addWidget(tb)
        cust_opts = lambda: [(c["id"], c["name"]) for c in q("SELECT * FROM customers")]
        user_opts = lambda: [(u["username"], u["full_name"])
                             for u in q("SELECT * FROM users WHERE active=1")]
        status_opts = lambda: [(x_, T(x_)) for x_ in
                               ["pending", "in-progress", "done", "delivered"]]
        s.work = TableEditor(mw, "work_orders",
            [("wo_no","Invoice No"),("title","Title"),("type","Type"),
             ("assigned_to","Assign To"),("status","Status"),("due","Due Date")],
            [("type","Type","combo",[("work", T("Work Order")),
                                     ("delivery", T("Delivery Order"))]),
             ("title","Title","text",None),("customer_id","Customer","combo",cust_opts),
             ("assigned_to","Assign To","combo",user_opts),
             ("details","Notes","memo",None),("status","Status","combo",status_opts),
             ("due","Due Date","date",None)],
            search_cols=["wo_no","title"], module="workorders")
        tb.addTab(s.work, "🛠 " + T("Work Orders")); s.work.refresh()
        dv = QWidget(); dvv = QVBoxLayout(dv)
        bot = QHBoxLayout()
        b1 = QPushButton("➡️ " + T("Advance Status")); b1.setObjectName("primary")
        b1.clicked.connect(s.advance); bot.addWidget(b1)
        b2 = QPushButton("🖨 " + T("Print Delivery Note")); b2.setObjectName("success")
        b2.clicked.connect(s.print_dn); bot.addWidget(b2)
        bot.addStretch(1); dvv.addLayout(bot)
        s.tbl = QTableWidget(0, 6)
        s.tbl.setHorizontalHeaderLabels([T("Invoice No"), T("Title"), T("Customer"),
            T("Assign To"), T("Status"), T("Due Date")])
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        dvv.addWidget(s.tbl, 1)
        tb.addTab(dv, "🚚 " + T("Delivery Orders")); s.ids = []; s.load_deliveries()
    def load_deliveries(s):
        rows = q("""SELECT w.*, c.name cname FROM work_orders w
                 LEFT JOIN customers c ON c.id=w.customer_id
                 WHERE w.type='delivery' ORDER BY w.id DESC""")
        s.tbl.setRowCount(len(rows)); s.ids = [r["id"] for r in rows]
        for i, r in enumerate(rows):
            for j, val in enumerate([r["wo_no"], r["title"], r["cname"] or "",
                                     r["assigned_to"], T(r["status"]), r["due"]]):
                it = QTableWidgetItem(str(val)); it.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, it)
    def advance(s):
        r = s.tbl.currentRow()
        if r < 0: return
        order = ["pending", "in-progress", "done", "delivered"]
        w = q1("SELECT * FROM work_orders WHERE id=?", (s.ids[r],))
        nx = order[min(order.index(w["status"]) + 1, 3)]
        x("UPDATE work_orders SET status=? WHERE id=?", (nx, w["id"]))
        log("workorder_status", f"{w['wo_no']}→{nx}"); s.load_deliveries()
    def print_dn(s):
        r = s.tbl.currentRow()
        if r < 0: return
        w = q1("SELECT * FROM work_orders WHERE id=?", (s.ids[r],))
        c = q1("SELECT name FROM customers WHERE id=?", (w["customer_id"],)) \
            if w["customer_id"] else None
        html = (f"<h1>🚚 {T('Delivery Note')} — {w['wo_no']}</h1>"
                "<table width=100% cellpadding=6 border=1>"
                f"<tr><th align=right>{T('Customer')}</th>"
                f"<th>{c['name'] if c else T('Walk-in')}</th></tr>"
                f"<tr><th align=right>{T('Title')}</th><th>{w['title']}</th></tr>"
                f"<tr><th align=right>{T('Notes')}</th><th>{w['details']}</th></tr>"
                f"<tr><th align=right>{T('Due Date')}</th><th>{w['due']}</th></tr></table>"
                f"<p style='margin-top:50px;'>{T('Delivered by')}: ..................</p>"
                f"<p>{T('Received by')}: ..................</p>"
                f"<p>{T('Signature')}: ..................</p>")
        do_print(html, a4=True, parent=s)

class AppointmentsPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        top = QHBoxLayout()
        s.day = QDateEdit(QDate.currentDate()); s.day.setCalendarPopup(True)
        s.day.dateChanged.connect(s.load)
        pv = QPushButton("◀"); nx = QPushButton("▶")
        td = QPushButton("📅 " + T("Today")); td.setObjectName("primary")
        pv.clicked.connect(lambda: s.day.setDate(s.day.date().addDays(-1)))
        nx.clicked.connect(lambda: s.day.setDate(s.day.date().addDays(1)))
        td.clicked.connect(lambda: s.day.setDate(QDate.currentDate()))
        nb = QPushButton("➕ " + T("New Appointment")); nb.setObjectName("success")
        nb.clicked.connect(s.add)
        for w in (pv, s.day, nx, td): top.addWidget(w)
        top.addStretch(1); top.addWidget(nb); v.addLayout(top)
        s.tbl = QTableWidget(0, 5)
        s.tbl.setHorizontalHeaderLabels([T("Date"), T("Title"), T("Customer"),
                                         T("Work Order"), T("Status")])
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v.addWidget(s.tbl, 1); s.ids = []
        dn = QPushButton("✅ " + T("Done")); dn.setObjectName("success")
        dn.clicked.connect(s.done); v.addWidget(dn); s.load()
    def load(s, *_):
        d = s.day.date().toString("yyyy-MM-dd")
        rows = q("""SELECT a.*, c.name cname, w.title wtitle FROM appointments a
                 LEFT JOIN customers c ON c.id=a.customer_id
                 LEFT JOIN work_orders w ON w.id=a.work_order_id
                 WHERE a.ts LIKE ? ORDER BY a.ts""", (d + "%",))
        s.tbl.setRowCount(len(rows)); s.ids = [r["id"] for r in rows]
        for i, r in enumerate(rows):
            for j, val in enumerate([r["ts"][11:16] if r["ts"] else "", r["title"],
                                     r["cname"] or "", r["wtitle"] or "", T(r["status"])]):
                it = QTableWidgetItem(str(val)); it.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, it)
    def add(s):
        d = QDialog(s); f = QFormLayout(d)
        ts = QDateTimeEdit(QDateTime.currentDateTime()); ts.setCalendarPopup(True)
        ti = QLineEdit(); cu = QComboBox(); cu.addItem(T("Walk-in"), None)
        for c in q("SELECT * FROM customers"): cu.addItem(c["name"], c["id"])
        wo = QComboBox(); wo.addItem("—", None)
        for w in q("SELECT * FROM work_orders"):
            wo.addItem(w["wo_no"] + " " + w["title"], w["id"])
        f.addRow(T("Date"), ts); f.addRow(T("Title"), ti)
        f.addRow(T("Customer"), cu); f.addRow(T("Work Order"), wo)
        ok = QPushButton("💾 " + T("Save")); ok.setObjectName("success"); f.addRow(ok)
        def do():
            x("INSERT INTO appointments(ts,title,customer_id,work_order_id,status) "
              "VALUES(?,?,?,?,'scheduled')",
              (ts.dateTime().toString("yyyy-MM-dd HH:mm"), ti.text(),
               cu.currentData(), wo.currentData()))
            log("appointment_new"); s.load(); d.accept()
        ok.clicked.connect(do); d.exec()
    def done(s):
        r = s.tbl.currentRow()
        if r >= 0:
            x("UPDATE appointments SET status='done' WHERE id=?", (s.ids[r],)); s.load()

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
            [("employee","Employee","combo",user_opts),("basis","Basis","combo",basis_opts),
             ("target","Product","text",None),("percent","Percent %","num",None),
             ("fixed","Fixed","num",None),("active","Active","check",None)],
            module="commissions")
        tb.addTab(s.rules, "📐 " + T("Rules")); s.rules.refresh()
        cw = QWidget(); cv = QVBoxLayout(cw)
        top = QHBoxLayout()
        s.f = QDateEdit(QDate.currentDate().addDays(-30)); s.f.setCalendarPopup(True)
        s.t = QDateEdit(QDate.currentDate()); s.t.setCalendarPopup(True)
        cb = QPushButton("🧮 " + T("Compute")); cb.setObjectName("primary")
        cb.clicked.connect(s.compute)
        top.addWidget(QLabel("📅")); top.addWidget(s.f)
        top.addWidget(QLabel("📅")); top.addWidget(s.t); top.addWidget(cb)
        top.addStretch(1); cv.addLayout(top)
        s.tbl = QTableWidget(0, 4)
        s.tbl.setHorizontalHeaderLabels([T("Date"), T("Employee"),
                                         T("Invoice No"), T("Amount")])
        s.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        s.tbl.verticalHeader().setVisible(False)
        s.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        cv.addWidget(s.tbl, 1)
        pb = QPushButton("💵 " + T("Mark Paid")); pb.setObjectName("success")
        pb.clicked.connect(s.mark_paid); cv.addWidget(pb)
        tb.addTab(cw, "💰 " + T("Computed Commissions")); s.load()
    def load(s):
        rows = q("""SELECT c.*, s.invoice_no FROM commissions c
                 LEFT JOIN sales s ON s.id=c.sale_id ORDER BY c.id DESC LIMIT 200""")
        s.tbl.setRowCount(len(rows)); s.ids = [r["id"] for r in rows]
        for i, r in enumerate(rows):
            val = (r["ts"], r["employee"], r["invoice_no"] or "—",
                   money(r["amount"]) + (" ✅" if r["paid"] else ""))
            for j, v_ in enumerate(val):
                it = QTableWidgetItem(str(v_)); it.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, it)
    def compute(s):
        f = s.f.date().toString("yyyy-MM-dd")
        t = s.t.date().toString("yyyy-MM-dd") + " 23:59:59"
        n = 0
        sales = q("SELECT * FROM sales WHERE ts BETWEEN ? AND ? AND status='completed'",
                  (f, t))
        rules = q("SELECT * FROM commission_rules WHERE active=1")
        for sa in sales:
            for ru in rules:
                emp = sa["username"] if ru["employee"] == "*" else ru["employee"]
                if ru["employee"] not in ("*", sa["username"]): continue
                if q1("SELECT id FROM commissions WHERE sale_id=? AND employee=?",
                      (sa["id"], emp)): continue
                amt = 0.0
                if ru["basis"] == "sale":
                    amt = sa["total"] * ru["percent"] / 100 + ru["fixed"]
                else:
                    items = q("SELECT * FROM sale_items WHERE sale_id=?", (sa["id"],))
                    for it in items:
                        hit = False
                        if ru["basis"] == "product":
                            hit = bool(ru["target"]) and ru["target"] in it["name"]
                        elif ru["basis"] == "category":
                            p = q1("SELECT category_id FROM products WHERE id=?",
                                   (it["product_id"],))
                            cn = q1("SELECT name FROM categories WHERE id=?",
                                    (p["category_id"],)) if p and p["category_id"] else None
                            hit = bool(cn) and ru["target"] == cn["name"]
                        if hit: amt += it["total"] * ru["percent"] / 100 + ru["fixed"]
                if amt > 0:
                    x("INSERT INTO commissions(ts,employee,sale_id,amount) "
                      "VALUES(?,?,?,?)", (nows(), emp, sa["id"], round(amt, 2))); n += 1
        log("commission_compute", f"n={n}")
        QMessageBox.information(s, APP, f"🧮 {n}")
        s.load()
    def mark_paid(s):
        r = s.tbl.currentRow()
        if r >= 0:
            x("UPDATE commissions SET paid=1 WHERE id=?", (s.ids[r],)); s.load()

class ExpensesPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        s.ed = TableEditor(mw, "expenses",
            [("ts","Date"),("category","Category name"),
             ("description","Description"),("amount","Amount spent")],
            [("category","Category name","text",None),
             ("description","Description","text",None),
             ("amount","Amount spent","num",None)],
            search_cols=["category","description"], order="ts DESC", module="expenses")
        v.addWidget(s.ed, 1); s.ed.refresh()

class UsersPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        tb = QTabWidget(); v.addWidget(tb)
        role_opts = lambda: [("admin","admin"),("manager","manager"),
                             ("cashier","cashier"),("store","store"),("account","account")]
        s.us = TableEditor(mw, "users",
            [("username","Search"),("full_name","Full Name"),
             ("role","Role"),("active","Active")],
            [("username","Search","text",None),("password","Password","text",None),
             ("full_name","Full Name","text",None),("role","Role","combo",role_opts),
             ("active","Active","check",None)],
            search_cols=["username","full_name"], module="users")
        tb.addTab(s.us, "👤 " + T("Users")); s.us.refresh()
        pv = QWidget(); pg = QGridLayout(pv)
        s.MODS = list(MOD_AR.keys())
        roles = ["admin", "manager", "cashier", "store", "account"]; s.checks = {}
        for j, r in enumerate(roles): pg.addWidget(QLabel("🛡 " + r), 0, j + 1)
        for i, m in enumerate(s.MODS):
            pg.addWidget(QLabel(MOD_AR[m] if LANG == "ar" else m), i + 1, 0)
            for j, r in enumerate(roles):
                cr = q1("SELECT allowed FROM role_permissions WHERE role=? AND module=?",
                        (r, m))
                cb = QCheckBox(); cb.setChecked(bool(cr and cr["allowed"]))
                if r == "admin":
                    cb.setChecked(True); cb.setEnabled(False)
                s.checks[(r, m)] = cb; pg.addWidget(cb, i + 1, j + 1)
        b = QPushButton("💾 " + T("Save") + " " + T("Permissions"))
        b.setObjectName("success"); b.clicked.connect(s.save_perms)
        pg.addWidget(b, len(s.MODS) + 1, 0, 1, 6)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(pv)
        wrap = QWidget(); wv = QVBoxLayout(wrap); wv.addWidget(sc)
        tb.addTab(wrap, "🛡 " + T("Permissions"))
        s.log = TableEditor(mw, "activity_log",
            [("ts","Date"),("username","Search"),("action","Module"),("details","Notes")],
            [], ro=True, search_cols=["username","action","details"], order="id DESC")
        tb.addTab(s.log, "📜 " + T("Activity Log")); s.log.refresh()
    def save_perms(s):
        for (r, m), cb in s.checks.items():
            if r == "admin": continue
            x("INSERT INTO role_permissions(role,module,allowed) VALUES(?,?,?) "
              "ON CONFLICT(role,module) DO UPDATE SET allowed=excluded.allowed",
              (r, m, 1 if cb.isChecked() else 0))
        log("permissions_save"); QMessageBox.information(s, APP, T("Saved"))

class ReportsPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        top = QHBoxLayout()
        s.kind = QComboBox()
        for k in ["Sales by Day", "Best Sellers", "Profit & Loss",
                  "Inventory Valuation", "Employee Performance"]:
            s.kind.addItem("📈 " + T(k), k)
        s.f = QDateEdit(QDate.currentDate().addDays(-30)); s.f.setCalendarPopup(True)
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
        s.summ = QLabel(""); s.summ.setObjectName("h1"); s.summ.setAlignment(Qt.AlignCenter)
        v.addWidget(s.summ)
        s.headers = []; s.rows = []
    def run(s):
        f = s.f.date().toString("yyyy-MM-dd")
        t = s.t.date().toString("yyyy-MM-dd") + " 23:59:59"
        kind = s.kind.currentData(); s.headers = []; s.rows = []
        if kind == "Sales by Day":
            rows = q("""SELECT date(ts) d, COUNT(*) n, SUM(total) tot, SUM(tax) tax,
                     AVG(total) avg FROM sales WHERE ts BETWEEN ? AND ?
                     AND status='completed' GROUP BY date(ts) ORDER BY d DESC""", (f, t))
            s.headers = [T("Date"), T("Invoice No")[:0] + "Count", T("Grand Total"),
                         T("Tax"), T("Amount")]
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
        elif kind == "Profit & Loss":
            sa = q1("SELECT IFNULL(SUM(total),0) t, IFNULL(SUM(tax),0) x FROM sales "
                    "WHERE ts BETWEEN ? AND ? AND status='completed'", (f, t))
            co = q1("""SELECT IFNULL(SUM(si.qty*si.cost),0) v FROM sale_items si
                    JOIN sales s ON s.id=si.sale_id WHERE s.ts BETWEEN ? AND ?
                    AND s.status='completed'""", (f, t))
            ex = q1("SELECT IFNULL(SUM(amount),0) v FROM expenses WHERE ts BETWEEN ? AND ?",
                    (f, t))
            gross = sa["t"] - sa["x"] - co["v"]; net = gross - ex["v"]
            s.headers = [T("Description"), T("Amount")]
            s.rows = [[T("Sales"), money(sa["t"])], [T("Tax"), money(sa["x"])],
                      [T("Cost"), money(co["v"])], [T("Gross Profit"), money(gross)],
                      [T("Expenses"), money(ex["v"])], [T("Net Profit"), money(net)]]
            s.summ.setText(f"💵 {T('Net Profit')}: {money(net)} {cur()}")
        elif kind == "Inventory Valuation":
            rows = q("""SELECT p.barcode,p.name,p.name_ar,p.cost,p.price,
                     IFNULL((SELECT SUM(qty) FROM stock WHERE product_id=p.id),0) qty
                     FROM products p WHERE p.active=1 ORDER BY qty*p.cost DESC""")
            s.headers = [T("Code"), T("Product Name"), T("Qty"), T("Cost"),
                         T("Price"), T("Value")]
            s.rows = [[r["barcode"], disp_name(r), f"{r['qty']:g}", money(r["cost"]),
                       money(r["price"]), money(r["qty"] * r["cost"])] for r in rows]
            s.summ.setText(f"📦 {T('Inventory Valuation')}: "
                           f"{money(sum(r['qty']*r['cost'] for r in rows))} {cur()}")
        else:
            rows = q("""SELECT username, COUNT(*) n, SUM(total) tot FROM sales
                     WHERE ts BETWEEN ? AND ? AND status='completed'
                     GROUP BY username ORDER BY tot DESC""", (f, t))
            s.headers = [T("Employee"), T("Qty"), T("Grand Total")]
            s.rows = [[r["username"], r["n"], money(r["tot"])] for r in rows]
            s.summ.setText("")
        s.tbl.clear(); s.tbl.setColumnCount(len(s.headers))
        s.tbl.setRowCount(len(s.rows)); s.tbl.setHorizontalHeaderLabels(s.headers)
        for i, r in enumerate(s.rows):
            for j, val in enumerate(r):
                it = QTableWidgetItem(str(val)); it.setTextAlignment(Qt.AlignCenter)
                s.tbl.setItem(i, j, it)
    def csv(s): export_csv(s.headers, s.rows)
    def _html(s):
        html = (f"<h1>📈 {s.kind.currentText()}</h1><p>"
                f"{s.f.date().toString('yyyy-MM-dd')} → "
                f"{s.t.date().toString('yyyy-MM-dd')}</p>"
                "<table width=100% cellpadding=6 border=1><tr>"
                + "".join(f"<th>{h}</th>" for h in s.headers) + "</tr>")
        for r in s.rows:
            html += "<tr>" + "".join(f"<td align=center>{c}</td>" for c in r) + "</tr>"
        return html + "</table><h3>" + s.summ.text() + "</h3>"
    def print_rep(s):
        if not s.rows: QMessageBox.information(s, APP, T("Nothing selected")); return
        do_print(s._html(), a4=True, parent=s)
    def pdf(s):
        if not s.rows: QMessageBox.information(s, APP, T("Nothing selected")); return
        path, _ = QFileDialog.getSaveFileName(s, "PDF",
            f"{s.kind.currentData()}_{today()}.pdf", "PDF (*.pdf)")
        if not path: return
        do_print(s._html(), a4=True, pdf=path)
        QMessageBox.information(s, APP, T("Exported"))

class SettingsPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        card = QFrame(); card.setObjectName("card"); g = QFormLayout(card)
        s.f = {}
        for key, lab in [("company","Company Name"),("company_ar","Company Name (AR)"),
                         ("tax_no","Tax Number"),("phone","Phone"),("address","Address"),
                         ("currency","Currency"),("currency_ar","Currency (AR)"),
                         ("receipt_footer","Receipt Footer")]:
            w = QLineEdit(SET.get(key, "")); s.f[key] = w; g.addRow(T(lab), w)
        s.vat = QDoubleSpinBox(); s.vat.setMaximum(100)
        s.vat.setValue(float(SET.get("vat", 15))); g.addRow(T("VAT %"), s.vat)
        b = QPushButton("💾 " + T("Save")); b.setObjectName("success")
        b.clicked.connect(s.save); g.addRow(b)
        v.addWidget(card)
        card2 = QFrame(); card2.setObjectName("card"); h = QHBoxLayout(card2)
        bk = QPushButton("💾 " + T("Backup Database")); bk.setObjectName("primary")
        bk.clicked.connect(s.backup); h.addWidget(bk)
        rs = QPushButton("♻️ " + T("Restore Database")); rs.setObjectName("danger")
        rs.clicked.connect(s.restore); h.addWidget(rs)
        h.addStretch(1); v.addWidget(card2); v.addStretch(1)
    def save(s):
        for k, w in s.f.items():
            x("INSERT INTO settings(key,value) VALUES(?,?) "
              "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, w.text()))
        x("INSERT INTO settings(key,value) VALUES('vat',?) "
          "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(s.vat.value()),))
        load_settings(); log("settings_save")
        QMessageBox.information(s, APP, T("Saved"))
    def backup(s):
        path, _ = QFileDialog.getSaveFileName(s, T("Backup Database"),
            f"backup_{today()}.db", "DB (*.db)")
        if not path: return
        conn.commit(); shutil.copy(DB, path); log("backup", path)
        QMessageBox.information(s, APP, T("Backup saved"))
    def restore(s):
        path, _ = QFileDialog.getOpenFileName(s, T("Restore Database"), DIR, "DB (*.db)")
        if not path: return
        if QMessageBox.question(s, APP, T("Are you sure?")) == QMessageBox.Yes:
            conn.commit(); conn.close(); shutil.copy(path, DB)
            QMessageBox.information(s, APP, T("Restored — restart required"))
            QProcess.startDetached(sys.executable, [os.path.abspath(__file__)])
            QApplication.quit()

# ============================== MAIN WINDOW =================================
NAV = [("Operations", ["dash","pos","sales","quotes","einvoice","shifts"]),
       ("Management", ["inventory","locations","purchases","suppliers","customers",
                       "offers","workorders","appointments","commissions","expenses",
                       "reports"]),
       ("System", ["users","settings"])]
PAGES = {
 "dash": ("Dashboard","نظرة عامة على أداء المتجر","Dashboard overview"),
 "pos": ("POS Screen","بيع سريع بالباركود أو البحث","Fast selling"),
 "sales": ("Sales & Invoices","الفواتير والمرتجعات","Invoices & returns"),
 "quotes": ("Quotations","عروض أسعار قابلة للتحويل","Quotations"),
 "einvoice": ("E-Invoicing","فوترة إلكترونية مع QR","E-invoicing with QR"),
 "shifts": ("Shifts","جرد الورديات والفرق النقدية","Shift inventory"),
 "inventory": ("Inventory","الأصناف والأقسام والأرصدة","Products & stock"),
 "locations": ("Branches & Warehouses","الفروع والمخازن والتحويلات","Branches & transfers"),
 "purchases": ("Purchases","المشتريات والموردون","Purchases & suppliers"),
 "suppliers": ("Suppliers","الموردون والمدفوعات","Suppliers"),
 "customers": ("Customers","العملاء والنقاط والحسابات","Customers"),
 "offers": ("Offers & Discounts","العروض والكوبونات والنقاطي","Offers & loyalty"),
 "workorders": ("Work Orders","أوامر التشغيل والتسليم","Work & delivery"),
 "appointments": ("Appointments","مواعيد مرتبطة بأوامر التشغيل","Appointments"),
 "commissions": ("Commissions","عمولات الموظفين","Commissions"),
 "expenses": ("Expenses","مصروفات الإدارة","Expenses"),
 "reports": ("Reports","تقارير شاملة وتصدير","Reports"),
 "users": ("Users","المستخدمون والصلاحيات","Users & permissions"),
 "settings": ("Settings","إعدادات النظام","Settings")}

class MainWindow(QMainWindow):
    def __init__(s):
        super().__init__(); s.setWindowTitle("🏪 " + APP)
        s.resize(1450, 880)
        root = QWidget(); h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)
        side = QFrame(); side.setObjectName("side"); side.setFixedWidth(250)
        sv = QVBoxLayout(side); sv.setContentsMargins(10, 16, 10, 10); sv.setSpacing(2)
        lg = QHBoxLayout()
        logo = QLabel("🛒")
        logo.setStyleSheet("font-size:34px;background:#fff;border-radius:16px;padding:8px;")
        lt = QLabel("Top Two" if LANG == "ar" else "Top Two")
        lt.setStyleSheet("color:#fff;font-size:24px;font-weight:800;")
        lb = QLabel("Eng:Moustafa Hesham"); lb.setStyleSheet("color:#10b981;font-weight:700;")
        lg.addWidget(logo)
        ltb = QVBoxLayout(); ltb.addWidget(lt); ltb.addWidget(lb); lg.addLayout(ltb)
        lg.addStretch(1); sv.addLayout(lg); sv.addSpacing(10)
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
        ub = QFrame(); ub.setStyleSheet("background:#16283f;border-radius:12px;")
        ul = QVBoxLayout(ub)
        un = QLabel("👤 " + CUR_USER["full_name"])
        un.setStyleSheet("color:#fff;font-weight:700;")
        ur = QLabel(CUR_USER["role"]); ur.setStyleSheet("color:#93a4bd;")
        lo = QPushButton("🚪 Logout")
        lo.setStyleSheet("color:#f87171;background:transparent;border:none;font-weight:700;")
        lo.clicked.connect(s.logout)
        ul.addWidget(un); ul.addWidget(ur); ul.addWidget(lo); sv.addWidget(ub)
        main = QWidget(); mv = QVBoxLayout(main)
        mv.setContentsMargins(0, 0, 0, 0); mv.setSpacing(0)
        head = QFrame(); head.setObjectName("head"); head.setFixedHeight(76)
        hh = QHBoxLayout(head); hh.setContentsMargins(18, 8, 18, 8)
        tbv = QVBoxLayout()
        s.title = QLabel(""); s.title.setObjectName("h1")
        s.sub = QLabel(""); s.sub.setObjectName("h2")
        tbv.addWidget(s.title); tbv.addWidget(s.sub); hh.addLayout(tbv); hh.addStretch(1)
        s.clock = QLabel(""); hh.addWidget(s.clock)
        lang = QPushButton("🌐 " + ("EN" if LANG == "ar" else "ع"))
        lang.setObjectName("ghost"); lang.clicked.connect(s.toggle_lang); hh.addWidget(lang)
        thm = QPushButton("🌙/☀️"); thm.setObjectName("ghost")
        thm.clicked.connect(s.toggle_theme); hh.addWidget(thm)
        mv.addWidget(head)
        s.stack = QStackedWidget(); mv.addWidget(s.stack, 1)
        h.addWidget(side); h.addWidget(main, 1); s.setCentralWidget(root)
        t = QTimer(s); t.timeout.connect(s.tick); t.start(1000); s.tick()
        s.pages = {}; s.goto("dash")
    def tick(s):
        n = dt.datetime.now()
        dn = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        adn = ["الإثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت","الأحد"]
        if LANG == "ar":
            txt = f"{adn[n.weekday()]}، {n.day:02d}/{n.month:02d}/{n.year}  |  " \
                  f"{n.strftime('%I:%M:%S %p')}"
        else:
            txt = f"{dn[n.weekday()]}, {n.day:02d} {n.strftime('%B %Y')}  |  " \
                  f"{n.strftime('%I:%M:%S %p')}"
        s.clock.setText("📅  " + txt)
    def page(s, k):
        if k in s.pages: return s.pages[k]
        makers = {
            "dash": Dashboard, "pos": POSPage, "sales": SalesPage,
            "quotes": QuotesPage, "einvoice": EInvoicePage, "shifts": ShiftsPage,
            "inventory": InventoryPage, "locations": LocationsPage,
            "purchases": PurchasesPage, "offers": OffersPage,
            "workorders": WorkOrdersPage, "appointments": AppointmentsPage,
            "commissions": CommissionsPage, "expenses": ExpensesPage,
            "reports": ReportsPage, "users": UsersPage, "settings": SettingsPage}
        if k == "suppliers":
            w = PartiesPage(s, "suppliers")
        elif k == "customers":
            w = PartiesPage(s, "customers")
        else:
            w = makers[k](s)
        s.pages[k] = w; s.stack.addWidget(w); return w
    def goto(s, k):
        if k not in s.navs:
            QMessageBox.warning(s, APP, "🚫 " + T("No permission")); return
        for kk, b in s.navs.items(): b.setChecked(kk == k)
        w = s.page(k); s.stack.setCurrentWidget(w)
        s.title.setText(("🏠  " if k == "dash" else "") + T(PAGES[k][0]))
        s.sub.setText(PAGES[k][1] if LANG == "ar" else PAGES[k][2])
    def refresh_dash(s):
        if "dash" in s.pages: s.pages["dash"].refresh()
    def toggle_theme(s):
        apply_theme(dark=SET.get("theme") != "dark")
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

# ============================== MAIN ========================================
def main():
    global LANG
    if "--dump-schema" in sys.argv:
        ix = sys.argv.index("--dump-schema")
        out = sys.argv[ix + 1] if len(sys.argv) > ix + 1 else "database_schema.sql"
        open(out, "w", encoding="utf-8").write(SCHEMA)
        print("schema →", out); return
    seed(); load_settings()
    LANG = SET.get("lang", "ar")
    app = QApplication(sys.argv); app.setFont(QFont("Segoe UI", 10))
    app.setQuitOnLastWindowClosed(False)
    from PySide6.QtGui import QIcon
    app.setWindowIcon(QIcon(os.path.join(DIR, "logo.png")))
    apply_theme()
    while True:
        dlg = Login()
        if dlg.exec() == QDialog.Accepted and CUR_USER: break
    log("login")
    notes = []
    low = low_stock_count()
    aps = q1("SELECT COUNT(*) c FROM appointments WHERE ts LIKE ?",
             (today() + "%",))["c"]
    if low: notes.append(f"⚠️ {T('Low Stock Alerts')}: {low}")
    if aps: notes.append(f"📅 {T('Appointments today')}: {aps}")
    w = MainWindow(); globals()["_mw"] = w
    if LANG == "ar": w.setLayoutDirection(Qt.RightToLeft)
    w.showMaximized()
    app.setQuitOnLastWindowClosed(True)
    if notes: QMessageBox.information(w, APP, "\n".join(notes))
    sys.exit(app.exec())

if __name__ == "__main__":
    main()