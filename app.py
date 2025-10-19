from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import feedparser
import smtplib, os
from email.message import EmailMessage
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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

@app.route('/blogs')
def blogs():
    return render_template('blogs.html', title='Blogs - Sahil Karande')

@app.route("/send_email", methods=["POST"])
def send_email():
    try:
        name = request.form["fullname"]
        email = request.form["email"]
        phone = request.form["phone"]
        message_content = request.form["message"]

        # 1️⃣ Email to You (Owner)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"New Contact Form Submission from {name}"
        msg["From"] = os.getenv("EMAIL_ADDRESS")
        msg["To"] = os.getenv("OWNER_EMAIL")

        html_content = f"""
        <html>
          <body style="font-family: Arial, sans-serif; padding: 10px;">
            <h2>📩 New Contact Message</h2>
            <p><strong>Name:</strong> {name}</p>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Phone:</strong> {phone}</p>
            <p><strong>Message:</strong></p>
            <p style="background:#f2f2f2;padding:10px;border-radius:5px;">{message_content}</p>
          </body>
        </html>
        """
        msg.attach(MIMEText(html_content, "html"))

        # 2️⃣ Confirmation Email to User
        confirm = MIMEMultipart("alternative")
        confirm["Subject"] = "🌟 Thank you for reaching out!"
        confirm["From"] = os.getenv("EMAIL_ADDRESS")
        confirm["To"] = email

        user_html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; padding: 10px;">
            <h2>Hi {name},</h2>
            <p>Thank you for contacting me! I have received your message and will get back to you soon.</p>
            <p>If your message is urgent, feel free to reach out directly at <a href="mailto:{os.getenv("EMAIL_ADDRESS")}">{os.getenv("EMAIL_ADDRESS")}</a>.</p>
            <br>
            <p>Regards,</p>
            <p><strong>Sahil Karande</strong></p>
            <p>🌐 <a href="https://sahilkarande.up.railway.app/">Portfolio Website</a></p>
          </body>
        </html>
        """
        confirm.attach(MIMEText(user_html, "html"))

        # Send both
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_PASSWORD"))
            smtp.send_message(msg)
            smtp.send_message(confirm)

        flash("✅ Message sent successfully!", "success")
        return redirect(url_for("contact"))

    except Exception as e:
        print(f"Error sending email: {e}")
        return redirect(url_for("contact", status="success"))


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html", title="404 - Not Found"), 404

if __name__ == "__main__":
    app.run(debug=True)
