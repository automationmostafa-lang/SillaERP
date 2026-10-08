# license_gate.py — التجربة 12 ساعة + التفعيل المربوط بالمازربورد
import os, sys, json, base64, hashlib, hmac, subprocess

LIC_SECRET = "HM-dfhnkxcbnihdgopjbkl-0kvbkgn87=-vmnxknlckvfgb"   # ⚠️ غيّرها لمفتاح عشوائي خاص بك
TRIAL_MINUTES = 12 * 60                        # 12 ساعة استخدام فعلي
APPDATA_DIR = os.path.join(os.environ.get("APPDATA", os.getcwd()), "HyperMarket")

try:
    import winreg
except Exception:
    winreg = None

# ---------- تشويش التخزين ----------
_XK = b"HyperMarket2026"
def _xf(s):
    return base64.b64encode(bytes(b ^ _XK[i % len(_XK)]
                                  for i, b in enumerate(s.encode()))).decode()
def _dx(s):
    try:
        raw = base64.b64decode(s)
        return bytes(b ^ _XK[i % len(_XK)]
                     for i, b in enumerate(raw)).decode()
    except Exception:
        return ""

# ---------- Registry ----------
def _reg_get(name):
    if winreg is None: return None
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\HyperMarket")
        v, _ = winreg.QueryValueEx(k, name); winreg.CloseKey(k)
        return v
    except Exception: return None

def _reg_set(name, val):
    if winreg is None: return
    try:
        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                             r"Software\HyperMarket")
        winreg.SetValueEx(k, name, 0, winreg.REG_SZ, val)
        winreg.CloseKey(k)
    except Exception: pass

# ---------- HWID: بصمة المازربورد ----------
def _wmi(cls, prop):
    try:
        out = subprocess.check_output(
            ["wmic", cls, "get", prop], timeout=15,
            creationflags=0x08000000).decode(errors="ignore")
        lines = [l.strip() for l in out.split("\n") if l.strip()]
        if len(lines) >= 2 and lines[1] \
           and "Serial" not in lines[1] and "UUID" not in lines[1]:
            return lines[1]
    except Exception: pass
    try:
        ps = "(Get-CimInstance " + cls + ")." + prop
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps], timeout=20,
            creationflags=0x08000000).decode(errors="ignore")
        v = out.strip()
        if v and "filled" not in v.lower(): return v
    except Exception: pass
    return ""

def get_hwid():
    """بصمة الجهاز: UUID اللوحة + سيريال المازربورد → كود 16 حرف"""
    parts = []
    u = _wmi("csproduct", "uuid")
    b = _wmi("baseboard", "serialnumber")
    if u: parts.append(u)
    if b: parts.append(b)
    if not parts:
        import platform
        parts.append(platform.node() or "UNKNOWN-PC")
        parts.append("FALLBACK")
    raw = "|".join(parts).upper().strip()
    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

# ---------- السيريال ----------
def verify_serial(serial, hwid):
    if not serial: return False
    expect = hmac.new(LIC_SECRET.encode(),
                      hwid.strip().upper().encode(),
                      hashlib.sha256).hexdigest().upper()[:20]
    user = "".join(ch for ch in serial.upper() if ch.isalnum())
    return hmac.compare_digest(user, expect)

# ---------- التخزين (3 مواقع — الأعلى يفوز) ----------
def _app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def _paths():
    return (os.path.join(APPDATA_DIR, "license.dat"),
            os.path.join(_app_dir(), "license.dat"))

def _state_read():
    cands = []
    p1, p2 = _paths()
    for p in (p1, p2):
        try:
            if os.path.exists(p):
                cands.append(json.loads(
                    _dx(open(p, encoding="utf-8").read().strip())))
        except Exception: pass
    rv = _reg_get("state")
    if rv:
        try: cands.append(json.loads(_dx(rv)))
        except Exception: pass
    best = {"used_min": 0.0, "activated": False, "serial": "", "hwid": ""}
    for c in cands:
        try:
            best["used_min"] = max(best["used_min"],
                                   float(c.get("used_min", 0)))
        except Exception: pass
        if c.get("activated"):
            best["activated"] = True
            best["serial"] = c.get("serial", "")
            best["hwid"] = c.get("hwid", "")
    return best

def _state_write(st):
    data = _xf(json.dumps(st))
    p1, p2 = _paths()
    try:
        os.makedirs(os.path.dirname(p1), exist_ok=True)
        open(p1, "w", encoding="utf-8").write(data)
    except Exception: pass
    try: open(p2, "w", encoding="utf-8").write(data)
    except Exception: pass
    _reg_set("state", data)

# ---------- شاشة التفعيل ----------
def _run_dialog(app_title, hwid, remain_min):
    """ترجع: 'activated' أو 'trial' أو 'exit'"""
    from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit,
                                   QPushButton, QHBoxLayout, QFrame)
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication
    res = {"mode": "exit"}
    _ar = True
    try:
        import __main__
        _ar = getattr(__main__, "LANG", "ar") == "ar"
    except Exception: pass

    d = QDialog(); d.setWindowTitle(app_title + (" — التفعيل" if _ar
                                                 else " — Activation"))
    d.setFixedWidth(560)
    v = QVBoxLayout(d); v.setContentsMargins(28, 24, 28, 20); v.setSpacing(12)
    card = QFrame()
    card.setStyleSheet("background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                       "stop:0 #0b1626, stop:1 #101f35);"
                       "border:1px solid rgba(126,240,192,50);"
                       "border-radius:16px;")
    cv = QVBoxLayout(card); cv.setContentsMargins(18, 16, 18, 16)
    t = QLabel(("🔐 تفعيل " if _ar else "🔐 Activate ") + app_title)
    t.setAlignment(Qt.AlignCenter)
    t.setStyleSheet("font-size:22px;font-weight:900;color:#7ef0c0;"
                    "background:transparent;")
    cv.addWidget(t)
    if remain_min > 0:
        h, m = int(remain_min // 60), int(remain_min % 60)
        info = QLabel(f"⏳ " + (f"نسخة تجريبية — متبقي {h} ساعة و {m} دقيقة"
                                if _ar else f"Trial — {h}h {m}m left"))
        info.setStyleSheet("color:#fbbf24;font-weight:700;font-size:13px;"
                           "background:transparent;")
    else:
        info = QLabel("⏰ " + ("انتهت فترة التجربة — التفعيل مطلوب"
                               if _ar else "Trial ended — activation required"))
        info.setStyleSheet("color:#f87171;font-weight:800;font-size:14px;"
                           "background:transparent;")
    info.setAlignment(Qt.AlignCenter); cv.addWidget(info)
    v.addWidget(card)

    lbl = QLabel("📡 " + ("كود جهازك (Hardware ID) — انسخه وأرسله للمطور"
                          " للحصول على السيريال" if _ar else
                          "Your Hardware ID — send it to the vendor"))
    lbl.setWordWrap(True); lbl.setStyleSheet("font-weight:700;")
    v.addWidget(lbl)
    hw = QLineEdit(hwid); hw.setReadOnly(True)
    hw.setFont(QFont("Consolas", 13)); hw.setMinimumHeight(40)
    hw.setAlignment(Qt.AlignCenter)
    hw.setStyleSheet("background:#0e1930;color:#7ef0c0;")
    v.addWidget(hw)
    hb1 = QHBoxLayout()
    cp = QPushButton("📋 " + ("نسخ الكود" if _ar else "Copy"))
    cp.setObjectName("primary"); cp.setMinimumHeight(38)
    def docp():
        QApplication.clipboard().setText(hwid)
        cp.setText("✅ " + ("تم النسخ" if _ar else "Copied"))
    cp.clicked.connect(docp); hb1.addWidget(cp); hb1.addStretch(1)
    v.addLayout(hb1)

    v.addWidget(QLabel("🔑 " + ("سيريال التفعيل:" if _ar
                               else "Activation serial:")))
    se = QLineEdit(); se.setFont(QFont("Consolas", 13))
    se.setMinimumHeight(42); se.setAlignment(Qt.AlignCenter)
    se.setPlaceholderText("XXXXX-XXXXX-XXXXX-XXXXX")
    v.addWidget(se)
    msg = QLabel(""); msg.setAlignment(Qt.AlignCenter)
    msg.setWordWrap(True); v.addWidget(msg)

    hb = QHBoxLayout()
    ab = QPushButton("🔓 " + ("تفعيل" if _ar else "Activate"))
    ab.setObjectName("success"); ab.setMinimumHeight(46)
    if remain_min > 0:
        co = QPushButton("▶ " + ("متابعة (نسخة تجريبية)" if _ar
                                 else "Continue (trial)"))
        co.setObjectName("ghost"); co.setMinimumHeight(46)
        co.clicked.connect(lambda: (res.__setitem__("mode", "trial"),
                                    d.accept()))
        hb.addWidget(co)
    cl = QPushButton("✖ " + ("خروج" if _ar else "Exit"))
    cl.setObjectName("danger"); cl.setMinimumHeight(46)
    cl.clicked.connect(d.reject)
    hb.addWidget(ab); hb.addWidget(cl); v.addLayout(hb)

    def activate():
        serial = se.text().strip()
        if verify_serial(serial, hwid):
            st = _state_read()
            st["activated"] = True
            st["serial"] = serial
            st["hwid"] = hwid
            _state_write(st)
            res["mode"] = "activated"
            msg.setText("🎉 " + ("تم التفعيل بنجاح! نسخة كاملة مرتبطة بهذا"
                        " الجهاز" if _ar else "Activated successfully!"))
            msg.setStyleSheet("color:#10b981;font-weight:800;")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1200, d.accept)
        else:
            msg.setText("❌ " + ("سيريال غير صالح لهذا الجهاز"
                        if _ar else "Invalid serial for this machine"))
            msg.setStyleSheet("color:#f87171;font-weight:700;")
    ab.clicked.connect(activate); se.returnPressed.connect(activate)
    d.exec()
    return res["mode"]

# ---------- البوابة الرئيسية ----------
def license_gate(app_title="HyperMarket"):
    """True = مسموح بالدخول | False = أغلق البرنامج"""
    hwid = get_hwid()
    st = _state_read()
    if st.get("activated") and st.get("hwid") == hwid \
       and verify_serial(st.get("serial", ""), hwid):
        return True                      # مفعّل وصالح على هذا الجهاز
    used = float(st.get("used_min", 0))
    remain = TRIAL_MINUTES - used
    mode = _run_dialog(app_title, hwid, remain)
    if mode == "activated":
        return True
    if mode == "trial" and remain > 0:
        return True
    return False                          # انتهت ورفض التفعيل → إغلاق

# ---------- عداد الدقائق أثناء التشغيل ----------
def license_start_meter(app_title="HyperMarket", mainwin=None):
    from PySide6.QtCore import QTimer
    def tick():
        st = _state_read()
        st["used_min"] = float(st.get("used_min", 0)) + 1.0
        if st.get("activated"):
            st["serial"] = st.get("serial", "")
            st["hwid"] = st.get("hwid", "")
        _state_write(st)
        try:
            mw = mainwin
            if mw is not None and not st.get("activated"):
                rm = TRIAL_MINUTES - st["used_min"]
                h, m = int(max(0, rm) // 60), int(max(0, rm) % 60)
                mw.setWindowTitle(f"{app_title} — DEMO {h:02d}:{m:02d}")
        except Exception: pass
    tm = QTimer(); tm.timeout.connect(tick); tm.start(60000)
    tick()
    return tm