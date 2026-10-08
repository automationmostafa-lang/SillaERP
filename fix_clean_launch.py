# fix_clean_launch.py — نسخة نظيفة: مواقع أساسية فقط + مستخدم admin
import shutil, py_compile, sys

SRC = "main.py"
try:
    py_compile.compile(SRC, doraise=True)
    print("OK - base clean")
except py_compile.PyCompileError as e:
    print("BROKEN:"); print(e); sys.exit(1)

src = open(SRC, encoding="utf-8").read()
bak = SRC + ".clean.bak"
shutil.copy(SRC, bak)
print("Backup:", bak)
fails = []

def rep(old, new, label):
    global src
    if old in src:
        src = src.replace(old, new, 1); print("REPLACED:", label)
    elif new.strip() and new.strip() in src:
        print("OK:", label, "(already)")
    else:
        fails.append(label); print("FAIL:", label)

# 1) seed_system_only ينشئ المواقع الأساسية + الباكاب
rep('''def seed_system_only():
    h = lambda p: hashlib.sha256(p.encode()).hexdigest()
    x("INSERT INTO users(username,password,full_name,role,created_at) "
      "VALUES('admin',?,'System Admin','admin',?)", (h("123456"), nows()))
    for k, v in {"company":"Hyper Market","company_ar":"هايبر ماركت","vat":"15",
                 "currency":"EGP","currency_ar":"ج.م","theme":"light","lang":"ar",
                 "receipt_footer":"Thank you for shopping with us!"}.items():
        x("INSERT INTO settings(key,value) VALUES(?,?)", (k, v))
    conn.commit()''',
'''def seed_system_only():
    h = lambda p: hashlib.sha256(p.encode()).hexdigest()
    x("INSERT INTO users(username,password,full_name,role,created_at) "
      "VALUES('admin',?,'System Admin','admin',?)", (h("123456"), nows()))
    for k, v in {"company":"Hyper Market","company_ar":"هايبر ماركت","vat":"15",
                 "currency":"EGP","currency_ar":"ج.م","theme":"light","lang":"ar",
                 "receipt_footer":"Thank you for shopping with us!"}.items():
        x("INSERT INTO settings(key,value) VALUES(?,?)", (k, v))
    # المواقع الأساسية — المحل والمخزن الرئيسي فقط
    _l1 = x("INSERT INTO locations(name,type) VALUES('المحل','branch')")
    _l2 = x("INSERT INTO locations(name,type) VALUES('المخزن الرئيسي','warehouse')")
    x("UPDATE locations SET supply_from=? WHERE id=?", (_l2, _l1))
    # ربط كل دور بصلاحياته الأساسية (يحفظ العميل خطوة)
    MODS = list(MOD_AR.keys())
    for m in MODS:
        x("INSERT INTO role_permissions(role,module,allowed) "
          "VALUES('admin',?,1)", (m,))
    conn.commit()''',
    "seed_system_only: locations + permissions")

# 2) تأكيد إن EMPTY_START = True (للتوزيع)
rep("EMPTY_START = False", "EMPTY_START = True", "EMPTY_START=True for release")

if fails:
    shutil.copy(bak, SRC)
    print("\\nFAILED:", fails); print("Restored — send output")
    sys.exit(1)

open(SRC, "w", encoding="utf-8").write(src)
print("Saved to main.py")
try:
    py_compile.compile(SRC, doraise=True)
    print("COMPILE: OK")
except py_compile.PyCompileError as e:
    shutil.copy(bak, SRC)
    print("COMPILE FAILED — restored:"); print(e)