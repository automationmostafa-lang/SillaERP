# create_shortcut.py — ينشئ شورت كات سطح المكتب بأيقونة احترافية
# شغّله مرة واحدة على جهاز العميل بعد توزيع EXE + logo.png + logo.ico
import os, sys

def create_shortcut():
    try:
        import pythoncom
        from win32com.client import Dispatch
    except ImportError:
        print("installing pywin32 ...")
        os.system(f'"{sys.executable}" -m pip install pywin32')
        import pythoncom
        from win32com.client import Dispatch

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    # للعربي/الويندوز المسماي "سطح المكتب" — خذ من registry:
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer"
            r"\User Shell Folders")
        desktop, _ = winreg.QueryValueEx(k, "Desktop")
        winreg.CloseKey(k)
        desktop = os.path.expandvars(desktop)
    except Exception: pass

    base = os.path.dirname(os.path.abspath(__file__))
    exe = os.path.join(base, "HyperMarket.exe")
    icon = os.path.join(base, "logo.ico")
    if not os.path.exists(exe):
        print("❌ HyperMarket.exe not found beside this script")
        return

    lnk = os.path.join(desktop, "HyperMarket.lnk")
    shell = Dispatch("WScript.Shell")
    sc = shell.CreateShortCut(lnk)
    sc.TargetPath = exe
    sc.WorkingDirectory = base
    sc.IconLocation = icon if os.path.exists(icon) else exe + ",0"
    sc.Description = "هايبر ماركت — نظام المحاسبة والمخازن"
    sc.save()
    print("✅ Desktop shortcut created:", lnk)

if __name__ == "__main__":
    create_shortcut()