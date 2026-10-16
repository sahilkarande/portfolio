# Deploying to PythonAnywhere

Workflow once set up:

```
 VS Code / Claude  ──git push──▶  GitHub (sahilkarande/portfolio)  ──./deploy/deploy.sh──▶  PythonAnywhere
   edit + test locally            review + merge PRs into main          pull, migrate, reload
```

Content (projects, certificates, resume…) is **not** deployed this way — you edit it live in
`/admin`. Git only carries code and design.

Replace `USERNAME` below with your PythonAnywhere username.

---

## First-time setup (≈20 minutes)

### 1. Get the code onto PythonAnywhere
Open **Consoles → Bash** and run:

```bash
cd ~
ls                                     # if an old "portfolio" folder exists: mv portfolio portfolio-old
git clone https://github.com/sahilkarande/portfolio.git
cd portfolio
```

The repo is public, so HTTPS needs no key. *If you make it private*, add an SSH key first:
`ssh-keygen -t ed25519` → `cat ~/.ssh/id_ed25519.pub` → paste into GitHub → Settings → SSH keys,
then clone with `git@github.com:sahilkarande/portfolio.git`.

### 2. Create the MySQL database
**Databases** tab:
1. Set a MySQL password (save it in your password manager).
2. Under *Create a database*, enter `portfolio` → the full name becomes `USERNAME$portfolio`.
3. Note the host shown there: `USERNAME.mysql.pythonanywhere-services.com`.
4. Click the new database to open a MySQL console and run (makes emoji/all scripts safe):
   ```sql
   ALTER DATABASE `USERNAME$portfolio` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

### 3. Create the virtualenv
Back in the Bash console (Python 3.10+ required; 3.12 recommended):

```bash
mkvirtualenv --python=python3.12 portfolio-venv
pip install -r ~/portfolio/requirements.txt
```

### 4. Create `~/portfolio/.env`
```bash
cd ~/portfolio
python3 -c "import secrets; print(secrets.token_hex(32))"     # copy this for SECRET_KEY
nano .env
```
Paste and fill in (keep the **single quotes** — `$` in the DB name must not be expanded):

```ini
FLASK_ENV_NAME=production
SECRET_KEY='paste-the-generated-value'

MYSQL_HOST='USERNAME.mysql.pythonanywhere-services.com'
MYSQL_USER='USERNAME'
MYSQL_PASSWORD='your-mysql-password'
MYSQL_DB='USERNAME$portfolio'

EMAIL_ADDRESS='you@gmail.com'
EMAIL_PASSWORD='your-gmail-app-password'
OWNER_EMAIL='you@gmail.com'
SITE_URL='https://USERNAME.pythonanywhere.com'
```
Save with `Ctrl+O`, `Enter`, `Ctrl+X`. (Your old `.env` on PythonAnywhere has the email values.)

### 5. Build the database
In a new console, first run `workon portfolio-venv`.

```bash
cd ~/portfolio
flask --app app db upgrade          # create tables
flask --app app seed                # load your original content
flask --app app optimize-images     # compress images (~27 MB -> ~2 MB)
flask --app app create-admin        # your admin login
```

### 6. Point the web app at the new code
**Web** tab (edit your existing app, or *Add a new web app → Manual configuration → Python 3.12*):

| Setting | Value |
|---|---|
| Source code | `/home/USERNAME/portfolio` |
| Working directory | `/home/USERNAME/portfolio` |
| Virtualenv | `/home/USERNAME/.virtualenvs/portfolio-venv` |
| Static files | URL `/static/` → Directory `/home/USERNAME/portfolio/static` |
| Force HTTPS | **Enabled** |

Click the **WSGI configuration file** link, replace its entire contents with
[`pythonanywhere_wsgi.py`](pythonanywhere_wsgi.py) (change `USERNAME`), save, then hit **Reload**.

### 7. Check it
- [ ] `https://USERNAME.pythonanywhere.com` loads the new design
- [ ] `/admin` → log in → dashboard shows your content
- [ ] Contact form → message appears in **Admin → Messages** (and email arrives)
- [ ] `/sitemap.xml` and `/robots.txt` use your real domain
- [ ] Open the site in a private window, then check **Admin → Analytics** shows a visit

### 8. Daily backups
**Tasks** tab → daily scheduled task (free accounts get one):

```bash
cd ~/portfolio && ~/.virtualenvs/portfolio-venv/bin/flask --app app backup --keep 14
```
Backups land in `~/backups/` (database dump + uploaded files). Uploads and the database exist
**only on PythonAnywhere** — download a recent backup from the **Files** tab now and then.

### 9. Google Search Console (optional)
Your verification file is served at `https://USERNAME.pythonanywhere.com/googlec2d288ffdefa9086.html`.
After verifying, submit `https://USERNAME.pythonanywhere.com/sitemap.xml` under *Sitemaps*.

---

## Every update after that

**On your computer** (VS Code terminal or ask Claude):
```bash
git checkout -b my-change            # work on a branch
# ...edit, then test:  env/bin/python -m pytest -q
git add -A && git commit -m "Describe the change"
git push -u origin my-change         # open a PR on GitHub, review, Merge
```

**On PythonAnywhere** (Bash console):
```bash
cd ~/portfolio && ./deploy/deploy.sh
```
It backs up, pulls `main`, installs requirements, runs migrations and reloads the site.

---

## Good to know (free plan)
- **Keep it alive:** free web apps are disabled after **1 month** unless you log in and click
  **"Run until 1 month from today"** on the Web tab (PythonAnywhere emails a week before).
- **Disk:** 512 MB total. Images are optimised on upload, and backups keep the last 14.
- **Email:** Gmail SMTP works on free accounts; use a Gmail *app password*, not your real one.
- **Errors:** Web tab → *Error log* (`/var/log/USERNAME.pythonanywhere.com.error.log`).
  A `RuntimeError: Set SECRET_KEY` means `.env` is missing or `FLASK_ENV_NAME` is wrong.
- **Forgot admin password:** `flask --app app create-admin` with the same username resets it.
