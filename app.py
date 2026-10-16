"""Entry point.

Local:   flask --app app run --debug   (or: python app.py)
WSGI:    from app import app as application   (PythonAnywhere)
"""
from portfolio import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
