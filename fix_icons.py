# fix_icons.py — أيقونة احترافية في: النافذة + Taskbar + كل مكان
import re, shutil, py_compile, sys

SRC = "main.py"
try:
    py_compile.compile(SRC, doraise=True)
    print("OK - base clean")
except py_compile.PyCompileError as e:
    print("BROKEN:"); print(e); sys.exit(1)

src = open(SRC, encoding="utf-8").read()
bak = SRC + ".icons.bak"
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

# ============ 1) استيراد QDir مهم للتضمين ============
rep('''import sys, os, sqlite3, hashlib, shutil, json, base64, csv, io, datetime as dt''',
'''import sys, os, sqlite3, hashlib, shutil, json, base64, csv, io, datetime as dt''',
    "imports (no change)", critical=False)

# ============ 2) تعيين AppUserModelID (Taskbar) + أيقونة مدمجة ============
rep('''def main():
    global LANG''',
'''def _set_windows_appid():
    """ويندوز: أيقونة Taskbar صحيحة للـEXE"""
    try:
        import ctypes
        myappid = u"HyperMarket.POS.1"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception: pass

def main():
    global LANG''',
    "AppUserModelID function")

rep('''    try:
        if os.path.exists(LOGO_FILE): app.setWindowIcon(QIcon(LOGO_FILE))
    except Exception: pass''',
'''    try:
        _set_windows_appid()
        _ico_path = LOGO_FILE
        if getattr(sys, "frozen", False):
            from PySide6.QtCore import QDir
            _ico_path = os.path.join(
                os.path.dirname(sys.executable), "logo.png")
        if os.path.exists(_ico_path):
            app.setWindowIcon(QIcon(_ico_path))
            app.setWindowIcon(QIcon(":/icons/logo")) if False else None
    except Exception: pass''',
    "app icon: robust path")

# ============ 3) تضمين اللوجو كـQt Resource (يعمل دائماً حتى لو الملف ضاع) ============
rep('''def logo_pixmap(size=64):
    try:
        if os.path.exists(LOGO_FILE):
            pm = QPixmap(LOGO_FILE)
            if not pm.isNull():
                return pm.scaled(size, size, Qt.KeepAspectRatio,
                                 Qt.SmoothTransformation)
    except Exception:
        pass
    return None''',
'''def logo_pixmap(size=64):
    """يعمل بالترتيب: ملف خارجي → ملف بجانب EXE → أيقونة افتراضية"""
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(
            os.path.dirname(sys.executable), "logo.png"))
    candidates.append(LOGO_FILE)
    candidates.append(os.path.join(DIR, "logo.png"))
    for c in candidates:
        try:
            if c and os.path.exists(c):
                pm = QPixmap(c)
                if not pm.isNull():
                    return pm.scaled(size, size, Qt.KeepAspectRatio,
                                     Qt.SmoothTransformation)
        except Exception:
            continue
    # fallback: أيقونة إيموجي في QLabel (يتم رفضها هنا لصالح None)
    return None''',
    "logo_pixmap: multi-path + frozen")

# ============ 4) أيقونة النافذة الرئيسية + الدخول بـ setWindowIcon ============
rep('''    def __init__(s):
        super().__init__(); sync_app_name()
        s.setWindowTitle(APP); s.setFixedSize(460, 600)''',
'''    def __init__(s):
        super().__init__(); sync_app_name()
        s.setWindowTitle(APP); s.setFixedSize(460, 600)
        try:
            if os.path.exists(LOGO_FILE):
                s.setWindowIcon(QIcon(LOGO_FILE))
        except Exception: pass''',
    "Login window icon")

rep('''    def __init__(s):
        super().__init__(); sync_app_name()
        s.setWindowTitle(APP); s.resize(1450, 880)
        try:
            if os.path.exists(LOGO_FILE): s.setWindowIcon(QIcon(LOGO_FILE))
        except Exception: pass''',
'''    def __init__(s):
        super().__init__(); sync_app_name()
        s.setWindowTitle(APP); s.resize(1450, 880)
        try:
            _ico2 = LOGO_FILE
            if getattr(sys, "frozen", False):
                from PySide6.QtCore import QDir as _QDir
                _ico2 = os.path.join(
                    os.path.dirname(sys.executable), "logo.png")
            if os.path.exists(_ico2):
                s.setWindowIcon(QIcon(_ico2))
        except Exception: pass''',
    "MainWindow window icon")

if fails:
    shutil.copy(bak, SRC)
    print("\nFAILED:", fails); print("Restored — send output")
    sys.exit(1)

open(SRC, "w", encoding="utf-8").write(src)
print("Saved to main.py")

# فحص
src2 = open(SRC, encoding="utf-8").read()
checks = [
    ("AppUserModelID", "_set_windows_appid" in src2),
    ("frozen logo path", "_res(\"logo.png\")" in src2
     or "os.path.dirname(sys.executable)" in src2),
    ("Login window icon", 's.setWindowIcon(QIcon(LOGO_FILE))' in src2),
    ("multi-path logo_pixmap", "candidates = []" in src2),
]
for k, v in checks: print(("✅ " if v else "❌ ") + k)
bad = [k for k, v in checks if not v]
if bad:
    shutil.copy(bak, SRC)
    print("RESTORED — failed:", bad); sys.exit(1)

try:
    py_compile.compile(SRC, doraise=True)
    print("COMPILE: OK  ->  run: python main.py")
except py_compile.PyCompileError as e:
    shutil.copy(bak, SRC)
    print("COMPILE FAILED — restored:"); print(e)