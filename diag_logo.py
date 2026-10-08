# diag_logo.py — يعرض نسخة logo_pixmap الفعلية في ملفك
src = open('main.py', encoding='utf-8').read()

# ابحث عن الدالة واطبعها كاملة
start = src.find("def logo_pixmap")
if start == -1:
    print("❌ def logo_pixmap غير موجودة أصلاً!")
    # ابحث عن أي logo دالة
    for i, l in enumerate(src.split('\n')):
        if 'logo' in l.lower() and 'def ' in l:
            print(f"  سطر {i+1}: {l.strip()[:80]}")
else:
    # اطبع من بداية الدالة لحد أول def بعد شي 15 سطر
    lines = src[start:].split('\n')[:18]
    print("=== def logo_pixmap كما هي في ملفك ===")
    for i, l in enumerate(lines):
        print(f"{i+1:3}: {l}")
    print("=" * 50)

# فحص إضافي: وين LOGO_FILE معرف
print()
print("=== مواضع LOGO_FILE ===")
for i, l in enumerate(src.split('\n')):
    if 'LOGO_FILE' in l:
        print(f"  سطر {i+1}: {l.strip()[:85]}")