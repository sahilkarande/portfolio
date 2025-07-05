from flask import Flask, render_template
import feedparser

app = Flask(__name__)

@app.route("/")
def about():
    return render_template("about.html", title="About - Sahil")

@app.route("/resume")
def resume():
    return render_template("resume.html", title="Resume - Sahil")

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html", title="404 - Not Found"), 404

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
    feed = feedparser.parse("https://medium.com/feed/@skarande220")  # Replace with your username
    entries = feed.entries[:6]  # Show latest 6 posts
    return render_template("blogs.html", entries=entries, title="Blogs - Sahil")
if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0')
