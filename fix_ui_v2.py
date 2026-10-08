# fix_ui_v2.py — 1)Overlay 2)Auto-hide 3)Always show 4)Auto font
#                + 5)جدول صلاحيات محاذى (QTableWidget)
import re, shutil, datetime as dt, py_compile, sys

SRC = "main.py"
try:
    py_compile.compile(SRC, doraise=True)
    print("OK - base clean")
except py_compile.PyCompileError as e:
    print("BROKEN:"); print(e); sys.exit(1)

src = open(SRC, encoding="utf-8").read()
bak = SRC + ".uiv2.bak"
shutil.copy(SRC, bak)
print("Backup:", bak)
fails = []

def class_span(s, name):
    m = re.search(r"^class " + name + r"\b", s, re.M)
    if not m: raise SystemExit("❌ كلاس: " + name)
    m2 = re.compile(r"^\S", re.M).search(s, m.end())
    return m.start(), (m2.start() if m2 else len(s))

def rep(old, new, label, critical=True):
    global src
    if old in src:
        src = src.replace(old, new, 1); print("REPLACED:", label)
    elif new.strip() and new.strip() in src:
        print("OK:", label, "(already)")
    else:
        print(("FAIL " if critical else "WARN ") + label)
        if critical: fails.append(label)

# ==================== 1) Overlay mode ====================
rep('''        def _apply_sidebar():
            wide = s.width() >= 1100
            side.setVisible(wide or s._sidebar_visible)
            menu_btn.setText("✖" if s._sidebar_visible and not wide else "☰")''',
'''        def _apply_sidebar():
            wide = s.width() >= 1100
            if wide:
                side.setVisible(True)
                side raising = False
            menu_btn.setText("✖" if s._sidebar_visible and not wide
                             else "☰")''',
    "overlay: prep", critical=False)  # سيتم استبدالها بالكامل أدناه

# استبدال شامل لمنطق الظهور
m = re.search(r"        # --- سلوك القايمة حسب حجم الشاشة ---\n"
              r".*?QTimer\.singleShot\(150, _apply_sidebar\)\n", src, re.S)
if m:
    NEW_LOGIC = '''        # --- سلوك القايمة حسب حجم الشاشة (Overlay على الصغيرة) ---
        s._drawer_open = False
        side.raise_()   # القايمة دايمًا فوق عند فتحها

        def _apply_sidebar():
            wide = s.width() >= 1100
            if wide:
                # شاشة كبيرة: القايمة ثابتة ظاهرة، والمحتوى بجانبها
                side.setVisible(True)
                s._drawer_open = False
                menu_btn.setText("☰")
            else:
                # شاشة صغيرة: القايمة overlay (فوق المحتوى) أو مخفية
                side.setVisible(s._drawer_open)
                menu_btn.setText("✖" if s._drawer_open else "☰")

        def _toggle_drawer():
            if s.width() >= 1100:
                # على الشاشة الكبيرة نطويها/نظهرها كإدارة
                side.setVisible(not side.isVisible())
                return
            s._drawer_open = not s._drawer_open
            _apply_sidebar()

        s._apply_sidebar = _apply_sidebar
        s._toggle_drawer = _toggle_drawer
        menu_btn.clicked.disconnect()
        menu_btn.clicked.connect(_toggle_drawer)
        def _res(evt, _orig=s.resizeEvent):
            _orig(evt)
            _apply_sidebar()
        s.resizeEvent = _res
        QTimer.singleShot(150, _apply_sidebar)
'''
    src = src[:m.start()] + NEW_LOGIC + src[m.end():]
    print("REPLACED: overlay + responsive logic")
else:
    fails.append("responsive logic")

# عند اختيار عنصر من القايمة على شاشة صغيرة: اقفل الدروار
rep('''        w = s.page(k); s.stack.setCurrentWidget(w)
        s._refresh_page(k)''',
'''        w = s.page(k); s.stack.setCurrentWidget(w)
        s._refresh_page(k)
        try:
            if s.width() < 1100:
                s._drawer_open = False
                s._apply_sidebar()
        except Exception: pass''',
    "auto-hide on navigate")

# ==================== 2) Always-show button (اختياري في الإعدادات) ====================
rep('''        s.alock = QSpinBox(); s.alock.setRange(0, 240)''',
'''        s.asb = QCheckBox("☰ " + ("القايمة دائمًا ظاهرة (شاشات صغيرة)"
                                   if LANG == "ar"
                                   else "Always show sidebar on small screens"))
        s.asb.setChecked(SET.get("always_sidebar") == "1")
        g.addRow(s.asb)
        s.alock = QSpinBox(); s.alock.setRange(0, 240)''',
    "always_sidebar setting")

rep('''        for k_, w_ in (("vat", str(s.vat.value())),
                       ("printer_name", s.prt.text().strip()),
                       ("direct_print", "1" if s.dpr.isChecked() else "0"),
                       ("autolock_min", str(s.alock.value()))):''',
'''        for k_, w_ in (("vat", str(s.vat.value())),
                       ("printer_name", s.prt.text().strip()),
                       ("direct_print", "1" if s.dpr.isChecked() else "0"),
                       ("autolock_min", str(s.alock.value())),
                       ("always_sidebar",
                        "1" if s.asb.isChecked() else "0"))):''',
    "save always_sidebar")

rep('''        def _apply_sidebar():
            wide = s.width() >= 1100''',
'''        def _apply_sidebar():
            wide = (s.width() >= 1100
                    or SET.get("always_sidebar") == "1")''',
    "always_sidebar logic hook")

# ==================== 3) Auto font scaling ====================
rep('''def apply_theme(dark=None):''',
'''def _apply_auto_font():
    """يصغّر/يكبّر الخط تلقائيًا حسب عرض النافذة"""
    mw = globals().get("_mw")
    if mw is None: return
    w = mw.width()
    if w < 900:      return 12
    elif w > 1500:   return 14
    return 13

def apply_theme(dark=None):''',
    "auto-font helper")

rep('''    qss = "\\n".join(L)
    for k, v in p.items(): qss = qss.replace("@" + k, v)
    QApplication.instance().setStyleSheet(qss)''',
'''    qss = "\\n".join(L)
    for k, v in p.items(): qss = qss.replace("@" + k, v)
    try:
        _fs = _apply_auto_font()
        qss = qss.replace("font-size:13px", "font-size:%dpx" % _fs)
        qss = qss.replace("font-size:14px", "font-size:%dpx" % (_fs + 1))
    except Exception: pass
    QApplication.instance().setStyleSheet(qss)''',
    "theme applies auto font")

# حدث إعادة تطبيق الثيم عند تغيير حجم النافذة (throttled)
rep('''        def _res(evt, _orig=s.resizeEvent):
            _orig(evt)
            _apply_sidebar()''',
'''        def _res(evt, _orig=s.resizeEvent):
            _orig(evt)
            _apply_sidebar()
            if not hasattr(s, "_font_t"):
                s._font_t = QTimer(s); s._font_t.setSingleShot(True)
                s._font_t.timeout.connect(lambda: apply_theme())
            s._font_t.start(300)''',
    "resize → reapply theme (auto font)")

# ==================== 4) جدول الصلاحيات المحاذى (QTableWidget) ====================
rep('''        pv = QWidget(); pg = QGridLayout(pv)
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
        tb.addTab(wrap, "🛡 " + T("Permissions"))''',
'''        # جدول صلاحيات محاذى: QTableWidget — كل checkbox تحت عموده تمامًا
        s.ROLE_LIST = ["admin", "manager", "cashier", "store", "account"]
        s.MODS = list(MOD_AR.keys())
        wrap = QWidget(); wv = QVBoxLayout(wrap); wv.setContentsMargins(8,8,8,8)
        s.perm_tbl = QTableWidget(len(s.MODS), 6)
        s.perm_tbl.setHorizontalHeaderLabels(
            [T("Module")] + ["🛡 " + r for r in s.ROLE_LIST])
        s.perm_tbl.verticalHeader().setVisible(False)
        s.perm_tbl.verticalHeader().setDefaultSectionSize(46)
        s.perm_tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 6):
            s.perm_tbl.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.Stretch)
        s.perm_tbl.setAlternatingRowColors(True)
        s.checks = {}
        for i, m in enumerate(s.MODS):
            it0 = QTableWidgetItem(MOD_AR[m] if LANG == "ar" else m)
            it0.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            s.perm_tbl.setItem(i, 0, it0)
            for j, r in enumerate(s.ROLE_LIST):
                cr = q1("SELECT allowed FROM role_permissions WHERE role=? "
                        "AND module=?", (r, m))
                cb = QCheckBox(); cb.setChecked(bool(cr and cr["allowed"]))
                if r == "admin":
                    cb.setChecked(True); cb.setEnabled(False)
                s.checks[(r, m)] = cb
                wrap_cb = QWidget()
                hl = QHBoxLayout(wrap_cb); hl.setContentsMargins(0,0,0,0)
                hl.addWidget(cb, 0, Qt.AlignCenter)
                s.perm_tbl.setCellWidget(i, j + 1, wrap_cb)
        pb = QPushButton("💾 " + T("Save") + " " + T("Permissions"))
        pb.setObjectName("success"); pb.setMinimumHeight(44)
        pb.clicked.connect(s.save_perms)
        wv.addWidget(s.perm_tbl, 1)
        wv.addWidget(pb)
        tb.addTab(wrap, "🛡 " + T("Permissions"))''',
    "permissions: aligned QTableWidget")

rep('''    def save_perms(s):
        for (r, m), cb in s.checks.items():''',
'''    def save_perms(s):
        for (r, m), cb in s.checks.items():
            if r == "admin": continue''',
    "save_perms skip admin (dup-safe)")

rep('''            x("INSERT INTO role_permissions(role,module,allowed) VALUES(?,?,?) "
              "ON CONFLICT(role,module) DO UPDATE SET allowed=excluded.allowed",
              (r, m, 1 if cb.isChecked() else 0))
        log("permissions_save")
        QMessageBox.information(s, APP, "✅ " + T("Saved"))''',
'''            x("INSERT INTO role_permissions(role,module,allowed) VALUES(?,?,?) "
              "ON CONFLICT(role,module) DO UPDATE SET allowed=excluded.allowed",
              (r, m, 1 if cb.isChecked() else 0))
        log("permissions_save")
        QMessageBox.information(s, APP, "✅ " + T("Saved"))
        if hasattr(s, "mw") and hasattr(s.mw, "broadcast_all"):
            s.mw.broadcast_all()''',
    "save_perms broadcast")

if fails:
    shutil.copy(bak, SRC)
    print("\nFAILED:", fails); print("Restored — send output")
    sys.exit(1)

open(SRC, "w", encoding="utf-8").write(src)
print("Saved to main.py")

# فحص ذاتي
src2 = open(SRC, encoding="utf-8").read()
checks = [
    ("overlay drawer",      "_drawer_open" in src2 and "side.raise_()" in src2),
    ("auto-hide nav",       "auto-hide on navigate" in src2 or
                            "_drawer_open = False" in src2.split("def tick")[0]),
    ("always_sidebar",      "always_sidebar" in src2),
    ("auto font",           "_apply_auto_font" in src2),
    ("perm table",          "s.perm_tbl = QTableWidget" in src2),
    ("perm aligned cells",  "wrap_cb" in src2),
]
bad = [k for k, v in checks if not v]
for k, v in checks: print(("✅ " if v else "❌ ") + k)
if bad:
    shutil.copy(bak, SRC)
    print("RESTORED — failed:", bad); sys.exit(1)

try:
    py_compile.compile(SRC, doraise=True)
    print("COMPILE: OK  ->  run: python main.py")
except py_compile.PyCompileError as e:
    shutil.copy(bak, SRC)
    print("COMPILE FAILED — restored. Full error:"); print(e)