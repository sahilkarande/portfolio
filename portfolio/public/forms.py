from flask_wtf import FlaskForm
from wtforms import EmailField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional


class ContactForm(FlaskForm):
    fullname = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=160)])
    phone = StringField("Phone", validators=[Optional(), Length(max=40)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(min=5, max=5000)])
    # Honeypot: hidden from humans, bots tend to fill it in.
    website = StringField("Website")
