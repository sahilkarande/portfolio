#!/usr/bin/env bash
# Update the live site on PythonAnywhere: pull from GitHub, install packages,
# run database migrations, then reload the web app.
#
#   cd ~/portfolio && ./deploy/deploy.sh
#
# Override defaults with env vars, e.g.  VENV=~/.virtualenvs/other ./deploy/deploy.sh
set -euo pipefail

cd "$(dirname "$0")/.."
VENV="${VENV:-$HOME/.virtualenvs/portfolio-venv}"
DOMAIN="${DOMAIN:-${USER}.pythonanywhere.com}"
WSGI_FILE="${WSGI_FILE:-/var/www/$(echo "$DOMAIN" | tr '.' '_' | tr '[:upper:]' '[:lower:]')_wsgi.py}"
BRANCH="${BRANCH:-main}"

step() { printf '\n\033[1;31m▸ %s\033[0m\n' "$1"; }

[ -f .env ] || { echo "Missing .env — see deploy/DEPLOY.md step 4."; exit 1; }
[ -x "$VENV/bin/python" ] || { echo "Virtualenv not found at $VENV — see deploy/DEPLOY.md step 3."; exit 1; }

step "Backing up database + uploads"
"$VENV/bin/flask" --app app backup --keep 14 || echo "(backup failed — continuing)"

step "Pulling latest code ($BRANCH)"
git fetch --quiet origin "$BRANCH"
git merge --ff-only "origin/$BRANCH"
git log -1 --format='  now at %h  %s  (%cr)'

step "Installing requirements"
"$VENV/bin/pip" install --quiet --disable-pip-version-check -r requirements.txt

step "Applying database migrations"
"$VENV/bin/flask" --app app db upgrade

step "Reloading web app"
if [ -f "$WSGI_FILE" ]; then
  touch "$WSGI_FILE"   # touching the WSGI file makes PythonAnywhere reload the site
  echo "  reloaded https://$DOMAIN"
else
  echo "  WSGI file not found at $WSGI_FILE — reload from the Web tab instead."
fi
