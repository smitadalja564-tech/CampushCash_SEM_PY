# CampusCash

**Your money. Your goals. Your future.**

CampusCash is a responsive Streamlit student expense manager based on the supplied CustomTkinter application. It uses SQLite for persistence, bcrypt for password hashing, Pandas for reporting, Plotly for charts, and pytest for automated checks.

## Features

- Login and registration with bcrypt password hashes and password validation.
- User-scoped expenses, monthly budgets, categories, and preferences.
- Add, search, filter, edit, and delete transactions.
- Monthly budget tracking with 75%, 90%, and 100% warnings.
- Interactive category, daily, payment-method, and monthly trend charts.
- CSV and Excel exports for the selected date range.
- Custom categories with archive/restore; archived categories remain in historical records.
- INR default and Indian digit grouping.
- Local SQLite database and automated legacy schema migration.

## Requirements and launch

Python 3.11+ is recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Streamlit opens the app in your browser. The default database path is `student_expense.db` in the current working directory. Override it with `CAMPUSCASH_DB=/path/to/file.db` before launching if needed.

## Legacy database migration

The original desktop app uses `users(username,password)`, `expenses`, and `budgets(username,budget)`. On startup, CampusCash inspects the schema. Before changing a detected legacy database, it creates a one-time side-by-side backup named `student_expense.db.pre_campuscash_backup` (or the equivalent path for your configured database). The original database file is not automatically deleted.

- Legacy plaintext passwords are hashed with bcrypt and the legacy `password` column is overwritten with the hash when present. After migration, login uses `password_hash`.
- The old budget table did not store a period. Each legacy budget is migrated to the month the migration runs in (`YYYY-MM`) so that the amount is preserved and reviewable. This is a pragmatic mapping, **not a claim that the old budget was for that month**. Review it in Budgets and adjust the period/value if necessary.
- Expense records are retained. `merchant` and `tags` columns are added if missing.
- The legacy `budgets` table is renamed to `budgets_legacy` to preserve it as a reference. It is not dropped.
- The migration is intended to be repeatable; migrated budgets use `INSERT OR IGNORE`.
- Keep the backup and original file until you have verified the migrated data. For maximum safety, stop the old app and copy the database manually before the first launch.

If migration fails, the app displays a database initialization error. Restore from the backup and inspect the traceback in the terminal; do not delete your only copy.

## Tests

```bash
pytest -q
```

Tests use temporary SQLite databases and do not touch your personal data.

## Responsive UI checklist

Please manually verify in a browser at 1440, 1024, 768, 430, and 375 CSS pixels:

- Sidebar navigation remains accessible (on narrow screens Streamlit's sidebar can be collapsed with its native control).
- Cards reflow into Streamlit columns without horizontal overflow.
- Forms are usable with touch controls.
- Charts fit the available container width.
- Transaction tables are readable; on small screens, use the native sidebar collapse and horizontal table scrolling if needed.
- Download buttons and validation messages remain visible.

Responsive CSS and Streamlit container layouts are implemented, but an actual browser/device test is not claimed by this project generation environment.

## Security and limitations

- All expense reads/updates/deletes include the signed-in username in their database predicates.
- SQL statements use parameters; foreign keys are enabled on each connection.
- This is a local student project, not a hosted multi-tenant banking system. Use HTTPS and a proper deployment/session strategy before exposing it publicly.
- No password recovery, email verification, two-factor authentication, currency conversion, PDF generation, category-specific budgets, or username change is included.
- Display currency can be changed, but the app does **not** convert stored INR amounts.
- A single local SQLite file is suitable for light personal use; concurrent/high-volume deployments should use a managed database.
- Category renaming is intentionally omitted to avoid changing the meaning of historical expense reports; archive/restore is supported.
- The app's report print view is a summary intended for browser printing; CSV and Excel contain the full filtered transaction set.

## Troubleshooting

- **`ModuleNotFoundError`**: activate the virtual environment and run `pip install -r requirements.txt`.
- **Port in use**: run `streamlit run app.py --server.port 8502`.
- **Can't log in after migration**: use the password that was stored in the legacy database before migration. If the old database already had an unknown schema, restore the backup and inspect it before retrying.
- **Database locked**: close duplicate app instances and ensure the database directory is writable.
