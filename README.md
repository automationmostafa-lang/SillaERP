سلة ERP — Retail ERP + POS (Arabic/English, RTL/LTR, Light/Dark)
1) Install (Windows)
Install Python 3.10+ → https://python.org (check "Add to PATH")
Open Command Prompt in the project folder and run:pip install -r requirements.txt
Run:python main.py
2) Default Logins
Role	Username	Password
Admin	admin	admin123
Manager	manager	123456
Cashier	cashier	123456
Warehouse Keeper	store	123456
Accountant	account	123456
3) Modules (all working)
Dashboard (cards + 7-day sales chart + top products) • POS (barcode scanner auto-focus,product grid, cart +/-, coupon, loyalty redeem, tier pricing, cash/card/mixed + change,thermal receipt with QR + Code39 barcode, hold/resume, shift required) • Shifts (open/close,cash count, difference report) • Inventory (products, categories, stock per location,adjustments, barcode labels, CSV import/export) • Branches/Warehouses + Stock Transfers •Purchases + Suppliers + payments + ledger • Sales & Returns • Quotations (approve/reject/convert→invoice) • E-Invoicing (ZATCA TLV QR, JSON/XML export, A4 tax invoice) • Users,Roles, granular permissions, Activity log • Work Orders & Delivery Orders (status workflow,printable delivery note with signature) • Appointments (day calendar, linked to work orders) •Commissions (rules + auto calculation + payouts) • Loyalty points, tiers (Bronze/Silver/Gold),Coupons, timed Offers • Expenses • Reports (sales/day, best sellers, P&L, inventory value,employee performance; CSV/Excel export + print) • Settings (company, VAT, currency, receiptfooter, backup/restore DB).

4) Utilities
Export SQL schema: python main.py --dump-schema database_schema.sql
Backup/Restore: Settings → Backup / Restore (copies retail_erp.db)
Barcode scanners: any USB scanner (keyboard-wedge) works in the POS barcode box.
5) Notes
Language (AR/EN) & theme toggles are in the header — applied instantly.
"Excel export" produces .csv (UTF-8 BOM) that opens perfectly in Excel with Arabic.
Printing uses the Windows print dialog (thermal 80mm for receipts, A4 for invoices).