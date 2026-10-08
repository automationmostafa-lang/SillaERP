# fix_drawer.py — القايمة الجانبية قابلة للطي (Drawer) للشاشات الصغيرة
import re, shutil, datetime as dt, py_compile, sys

SRC = "main.py"
try:
    py_compile.compile(SRC, doraise=True)
    print("OK - base clean")
except py_compile.PyCompileError as e:
    print("BROKEN:"); print(e); sys.exit(1)

src = open(SRC, encoding="utf-8").read()
bak = SRC + ".drawer.bak"
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

# ============ 1) sidebar يبقى QToolButton حاوي داخل QScrollArea ============
rep('''        side = QFrame(); side.setObjectName("side"); side.setFixedWidth(250)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(10, 16, 10, 10); sv.setSpacing(2)''',
'''        side = QFrame(); side.setObjectName("side"); side.setFixedWidth(250)
        sv0 = QVBoxLayout(side); sv0.setContentsMargins(0, 0, 0, 0)
        side_scroll = QScrollArea(); side_scroll.setWidgetResizable(True)
        side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        side_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        side_inner = QWidget(); side_inner.setObjectName("sideInner")
        sv = QVBoxLayout(side_inner)
        sv.setContentsMargins(10, 16, 10, 10); sv.setSpacing(2)
        side_scroll.setWidget(side_inner)
        sv0.addWidget(side_scroll)''',
    "sidebar scrollable")

# CSS: scroll area شفاف + inner بلون السايدبار
rep('''    L.append("#head { background:@card; border-bottom:1px solid @border; }")''',
'''    L.append("#head { background:@card; border-bottom:1px solid @border; }")
    L.append("#side QScrollArea, #side #sideInner { background:transparent; }"
             )''',
    "sidebar scroll CSS")

# ============ 2) الهيدر: زرار ☰ لفتح/قفل القايمة ============
rep('''        lang = QPushButton("🌐 " + ("EN" if LANG == "ar" else "ع"))
        lang.setObjectName("ghost"); lang.clicked.connect(s.toggle_lang)
        hh.addWidget(lang)''',
'''        menu_btn = QPushButton("☰")
        menu_btn.setObjectName("ghost")
        menu_btn.setFixedSize(42, 40)
        menu_btn.setStyleSheet("font-size:20px; font-weight:900;")
        menu_btn.setToolTip(("القائمة" if LANG == "ar" else "Menu") +
                            " (Ctrl+M)")
        menu_btn.clicked.connect(s.toggle_sidebar)
        hh.addWidget(menu_btn)
        lang = QPushButton("🌐 " + ("EN" if LANG == "ar" else "ع"))
        lang.setObjectName("ghost"); lang.clicked.connect(s.toggle_lang)
        hh.addWidget(lang)''',
    "header: menu button")

# ============ 3) منطق فتح/قفل + اختفاء تلقائي حسب عرض الشاشة ============
rep('''        s.pages = {}; s.goto("dash")''',
'''        # --- سلوك القايمة حسب حجم الشاشة ---
        s._sidebar_visible = True
        def _apply_sidebar():
            wide = s.width() >= 1100
            side.setVisible(wide or s._sidebar_visible)
            menu_btn.setText("✖" if s._sidebar_visible and not wide else "☰")
        s._apply_sidebar = _apply_sidebar
        def resizeEvent(evt, _orig=s.resizeEvent):
            _orig(evt)
            _apply_sidebar()
        s.resizeEvent = resizeEvent
        menu_btn.clicked.disconnect()
        menu_btn.clicked.connect(s.toggle_sidebar)
        QTimer.singleShot(150, _apply_sidebar)
        s.pages = {}; s.goto("dash")''',
    "responsive sidebar logic")

# ============ 4) دالة toggle_sidebar ============
rep('''    def tick(s):''',
'''    def toggle_sidebar(s):
        s._sidebar_visible = not s._sidebar_visible
        s._apply_sidebar()

    def tick(s):''',
    "toggle_sidebar method")

if fails:
    shutil.copy(bak, SRC)
    print("\nFAILED:", fails); print("Restored — send output")
    sys.exit(1)

open(SRC, "w", encoding="utf-8").write(src)
print("Saved to main.py")

# فحص ذاتي
src2 = open(SRC, encoding="utf-8").read()
checks = [
    ("sidebar scrollable",  "side_scroll = QScrollArea" in src2),
    ("menu button",         'menu_btn = QPushButton("☰")' in src2),
    ("toggle method",       "def toggle_sidebar(s):" in src2),
    ("responsive logic",    "_apply_sidebar" in src2 and
                            "s.width() >= 1100" in src2),
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
    print("COMPILE FAILED — restored:"); print(e)