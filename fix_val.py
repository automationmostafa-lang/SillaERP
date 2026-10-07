# fix_val.py — الإصلاح الجذري: _val ناقصها فرع text (QLineEdit.text)
import shutil, datetime as dt, py_compile, sys

SRC = "main.py"
try:
    py_compile.compile(SRC, doraise=True)
    print("OK - base clean")
except py_compile.PyCompileError as e:
    print("BROKEN:"); print(e); sys.exit(1)

src = open(SRC, encoding="utf-8").read()
bak = "main_backup_val_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S") + ".py"
shutil.copy(SRC, bak)
print("Backup:", bak)
fails = []

def rep(old, new, label, critical=True):
    global src
    if old in src:
        src = src.replace(old, new, 1); print("REPLACED:", label)
    elif new.strip() and new.strip() in src:
        print("OK:", label, "(already)")
    else:
        print(("FAIL " if critical else "WARN ") + label)
        if critical: fails.append(label)

# ---------- 1) الإصلاح الجذري: فرع text في _val ----------
rep('''    def _val(s, typ, w):
        if typ == "check":  return 1 if w.isChecked() else 0
        if typ == "date":   return w.date().toString("yyyy-MM-dd")
        if typ == "memo":   return w.toPlainText()
        if typ == "combo":  return w.currentData()
        return w.value()''',
'''    def _val(s, typ, w):
        if typ == "check":  return 1 if w.isChecked() else 0
        if typ == "date":   return w.date().toString("yyyy-MM-dd")
        if typ == "memo":   return w.toPlainText()
        if typ == "combo":  return w.currentData()
        if typ == "text":   return w.text()
        return w.value()''',
    "ROOT CAUSE: _val text branch")

# ---------- 2) الكومبوبوكس: لا يفسد القيمة لو مش موجود في القائمة ----------
rep('''                editable_combo(w)
                if rec:
                    ix = w.findData(rec[col])
                    if ix >= 0: w.setCurrentIndex(ix)''',
'''                editable_combo(w)
                if rec:
                    ix = w.findData(rec[col])
                    if ix >= 0:
                        w.setCurrentIndex(ix)
                    elif rec[col] is not None:
                        w.addItem(str(rec[col]), rec[col])
                        w.setCurrentIndex(w.count() - 1)''',
    "combo: preserve unknown current value")

# ---------- 3) شبكة أمان: أي خطأ تجميع قيم يظهر فورًا (لا صمت) ----------
rep('''        cols = list(extra.keys()); vals = list(extra.values())
        for col, (typ, w) in ed.items():
            v_ = s._val(typ, w)
            if s.table == "users" and col == "password":
                v_ = hashlib.sha256((str(v_) or "123456").encode()).hexdigest()
            cols.append(col); vals.append(v_)''',
'''        cols = list(extra.keys()); vals = list(extra.values())
        try:
            for col, (typ, w) in ed.items():
                v_ = s._val(typ, w)
                if s.table == "users" and col == "password":
                    v_ = hashlib.sha256(
                        (str(v_) or "123456").encode()).hexdigest()
                cols.append(col); vals.append(v_)
        except Exception as e:
            QMessageBox.critical(s, APP, "❌ " + str(e)); return''',
    "add: no silent errors")

rep('''        sets = []; vals = []
        for col, (typ, w) in ed.items():
            v_ = s._val(typ, w)
            if s.table == "users" and col == "password":
                if not v_: continue
                v_ = hashlib.sha256(str(v_).encode()).hexdigest()
            sets.append(f"{col}=?"); vals.append(v_)''',
'''        sets = []; vals = []
        try:
            for col, (typ, w) in ed.items():
                v_ = s._val(typ, w)
                if s.table == "users" and col == "password":
                    if not v_: continue
                    v_ = hashlib.sha256(str(v_).encode()).hexdigest()
                sets.append(f"{col}=?"); vals.append(v_)
        except Exception as e:
            QMessageBox.critical(s, APP, "❌ " + str(e)); return''',
    "edit: no silent errors")

if fails:
    shutil.copy(bak, SRC)
    print("\nFAILED:", fails); print("Restored — send output"); sys.exit(1)

open(SRC, "w", encoding="utf-8").write(src)
print("Saved to main.py")

# فحص ذاتي
src2 = open(SRC, encoding="utf-8").read()
ok = 'if typ == "text":   return w.text()' in src2
print(("SELF-CHECK: YES — text branch present" if ok
       else "SELF-CHECK: NO — restored"))
if not ok:
    shutil.copy(bak, SRC); sys.exit(1)

try:
    py_compile.compile(SRC, doraise=True)
    print("COMPILE: OK  ->  run: python main.py")
except py_compile.PyCompileError as e:
    shutil.copy(bak, SRC)
    print("COMPILE FAILED — restored. Full error:"); print(e)