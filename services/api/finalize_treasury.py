import sys, os, sqlite3
api_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, api_dir)
os.chdir(api_dir)
os.environ.setdefault("QUFIN_DATABASE_URL", "sqlite:///./qufin.db")

from app.jobs.check_data import check_macro, format_report
from app.stores.db import session_scope
from datetime import date

today = date.today()
print(f"=== Running check-data (Rule 2 release check) as of {today} ===")
with session_scope() as session:
    checks = check_macro(session, today)
print(format_report(checks))

db = os.path.join(api_dir, "qufin.db")
con = sqlite3.connect(db)
cur = con.cursor()
cur.execute("SELECT id, title, first_period, last_period, vintage_rows FROM macro_series WHERE source='treasury' ORDER BY id")
print("\n=== Treasury series in DB ===")
for r in cur.fetchall():
    print("  ", r)
con.close()
