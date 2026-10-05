class InventoryPage(QWidget):
    def __init__(s, mw):
        super().__init__(); s.mw = mw; v = QVBoxLayout(s)
        tb = QTabWidget(); v.addWidget(tb)
        cat_items = [("__all__", T("All"))] + [(c["id"], c["name"]) for c in q("SELECT * FROM categories ORDER BY name")]
        cat_opts  = lambda: [(c["id"], c["name"]) for c in q("SELECT * FROM categories ORDER BY name")]
        s.prod = TableEditor(mw, "products",
            [("barcode","Code"),("name","Product Name"),("name_ar","Name (AR)"),("price","Price"),("cost","Cost"),("min_stock","Min Stock")],
            [("barcode","Code","text",None),("name","Product Name","text",None),("name_ar","Name (AR)","text",None),
             ("category_id","Category","combo",cat_opts),("unit","Unit","text",None),("cost","Cost","num",None),
             ("price","Price","num",None),("min_stock","Min Stock","num",None),("icon","Icon","text",None),
             ("active","Active","check",None)],
            search_cols=["barcode","name","name_ar"], order="id DESC", module="inventory",
            filters=(cat_items, "category_id"))
        tb.addTab(s.prod, "📦 " + T("Products")); s.prod.refresh()
        bar = QHBoxLayout()
        b1 = QPushButton("🏷️ " + T("Barcode Labels")); b1.setObjectName("primary"); b1.clicked.connect(s.labels)
        b2 = QPushButton("📥 " + T("Import CSV")); b2.clicked.connect(s.import_csv)
        b3 = QPushButton("⚖️ " + T("Adjust Stock")); b3.setObjectName("warn"); b3.clicked.connect(s.adjust)
        bar.addWidget(b1); bar.addWidget(b2); bar.addWidget(b3); bar.addStretch(1)
        v.addLayout(bar)
        s.cats = TableEditor(mw, "categories", [("name","Category")], [("name","Category","text",None)], module="inventory")
        tb.addTab(s.cats, "🗂 " + T("Categories")); s.cats.refresh()
        st = QWidget(); sv = QVBoxLayout(st)
        sh = QHBoxLayout(); s.sl = QComboBox()
        for l in q("SELECT * FROM locations"): s.sl.addItem("🏬 " + l["name"], l["id"])
        s.sl.currentIndexChanged.connect(s.load_stock)
        sh.addWidget(QLabel("🏬 " + T("Location"))); sh.addWidget(s.sl); sh.addStretch(1); sv.addLayout(sh)
        s.stbl = QTableWidget(); s.stbl.setEditTriggers(QTableWidget.NoEditTriggers); s.stbl.verticalHeader().setVisible(False)
        sv.addWidget(s.stbl); tb.addTab(st, "📊 " + T("Stock by Location")); s.load_stock()
    def load_stock(s):
        lid = s.sl.currentData()
        rows = q("""SELECT p.barcode,p.name,p.name_ar,IFNULL(st.qty,0) qty,p.min_stock,p.price FROM products p
                    LEFT JOIN stock st ON st.product_id=p.id AND st.location_id=? WHERE p.active=1 ORDER BY p.name""", (lid,))
        hdr = [T("Code"), T("Product Name"), T("Qty"), T("Min Stock"), T("Price"), T("Status")]
        s.stbl.clear(); s.stbl.setColumnCount(6); s.stbl.setRowCount(len(rows)); s.stbl.setHorizontalHeaderLabels(hdr)
        s.stbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for i, r in enumerate(rows):
            stat = "🔴" if r["qty"] <= 0 else "🟠" if r["qty"] < r["min_stock"] else "🟢"
            for j, val in enumerate([r["barcode"], disp_name(r), f"{r['qty']:g}", f"{r['min_stock']:g}", money(r["price"]), stat]):
                it = QTableWidgetItem(str(val)); it.setTextAlignment(Qt.AlignCenter); s.stbl.setItem(i, j, it)
    def adjust(s):
        d = QDialog(s); d.setWindowTitle("⚖️ " + T("Adjust Stock")); f = QFormLayout(d)
        pc = QComboBox()
        for p in q("SELECT * FROM products WHERE active=1 ORDER BY name"): pc.addItem(disp_name(p), p["id"])
        lc = QComboBox()
        for l in q("SELECT * FROM locations"): lc.addItem(l["name"], l["id"])
        cur = QLabel("—"); new = QDoubleSpinBox(); new.setMaximum(10**7)
        rs = QLineEdit(); rs.setPlaceholderText(T("Reason"))
        def upd():
            r = q1("SELECT qty FROM stock WHERE product_id=? AND location_id=?", (pc.currentData(), lc.currentData()))
            cur.setText(f"{r['qty']:g}" if r else "0")
        pc.currentIndexChanged.connect(upd); lc.currentIndexChanged.connect(upd); upd()
        ok = QPushButton("✅ " + T("Save")); ok.setObjectName("warn")
        f.addRow(T("Product"), pc); f.addRow(T("Location"), lc); f.addRow(T("Stock:"), cur)
        f.addRow(T("New Qty"), new); f.addRow(T("Reason"), rs); f.addRow(ok)
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
                    "<div style='font-size:13px;font-weight:800;'>" + money(p["price"]) + " " + cur() + "</div>"
                    "<img src='bar' width='150' height='42'><div style='font-size:10px;'>" + p["barcode"] + "</div></td>")
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
                    nm  = row.get("name") or row.get("Product Name") or bc
                    nar = row.get("name_ar") or ""
                    cost  = float(row.get("cost") or 0); price = float(row.get("price") or 0)
                    mn    = float(row.get("min_stock") or 5)
                    ex = q1("SELECT id FROM products WHERE barcode=?", (bc,))
                    if ex:
                        x("UPDATE products SET name=?,name_ar=?,cost=?,price=?,min_stock=? WHERE id=?",
                          (nm, nar, cost, price, mn, ex["id"]))
                    else:
                        pid = x("INSERT INTO products(barcode,name,name_ar,cost,price,min_stock) VALUES(?,?,?,?,?,?)",
                                (bc, nm, nar, cost, price, mn))
                        for l in q("SELECT id FROM locations"):
                            x("INSERT INTO stock(product_id,location_id,qty) VALUES(?,?,0)", (pid, l["id"]))
                    n += 1
        except Exception as e:
            QMessageBox.critical(s, APP, str(e)); return
        log("import_csv", f"{n} products"); s.prod.refresh()
        QMessageBox.information(s, APP, f"{T('Imported')}: {n}")