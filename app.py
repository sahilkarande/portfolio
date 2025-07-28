from flask import Flask, render_template, request, jsonify
import feedparser
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import os

app = Flask(__name__)
load_dotenv()  # Load .env variables

# Main pages
@app.route("/")
def about():
    return render_template("about.html", title="About - Sahil")

@app.route("/resume")
def resume():
    return render_template("resume.html", title="Resume - Sahil")

@app.route("/projects")
def projects():
    return render_template("projects.html", title="Projects - Sahil")

@app.route("/certificates")
def certificates():
    return render_template("certificates.html", title="Certificates - Sahil")

@app.route("/contact")
def contact():
    return render_template("contact.html", title="Contact - Sahil")

@app.route("/blogs")
def blogs():
    feed = feedparser.parse("https://medium.com/feed/@skarande220")
    entries = feed.entries[:6]
    return render_template("blogs.html", entries=entries, title="Blogs - Sahil")

# Contact form backend
@app.route("/send_email", methods=["POST"])
def send_email():
    name = request.form["fullname"]
    email = request.form["email"]
    phone = request.form["phone"]
    message = request.form["message"]

    # Email to you (Sahil)
    msg_to_me = EmailMessage()
    msg_to_me["Subject"] = f"New Contact Form Submission from {name}"
    msg_to_me["From"] = os.getenv("EMAIL_ADDRESS")
    msg_to_me["To"] = os.getenv("OWNER_EMAIL")
    msg_to_me.set_content(f"""
You have received a new message:

Name: {name}
Email: {email}
Phone: {phone}

Message:
{message}
    """)

    # Confirmation to user
    msg_to_user = EmailMessage()
    msg_to_user["Subject"] = "Thanks for contacting me!"
    msg_to_user["From"] = os.getenv("EMAIL_ADDRESS")
    msg_to_user["To"] = email
    msg_to_user.set_content(f"""
Hi {name},

Thank you for reaching out to me. I have received your message and will get back to you soon!

Here's a copy of your message:
{message}

Regards,  
Sahil Karande
""")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_PASSWORD"))
            smtp.send_message(msg_to_me)
            smtp.send_message(msg_to_user)
        return jsonify({"status": "success", "message": "Message sent successfully!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html", title="404 - Not Found"), 404

if __name__ == "__main__":
    app.run(debug=True)
