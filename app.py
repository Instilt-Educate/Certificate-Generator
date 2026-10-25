from flask import Flask, send_file, request, render_template, flash, send_from_directory, session, redirect, url_for
from PIL import Image, ImageFont, ImageDraw
from datetime import datetime, timedelta
from zipfile import ZipFile
import zipfile
from io import BytesIO
import dotenv
import os
import re

import requests
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import logging

from markupsafe import escape
from tiers import API_BASE, get_tiers, get_tier, TiersUnavailable

dotenv.load_dotenv('.env')
app = Flask(__name__)
app.secret_key = "secret1"

app.config.update(
    SESSION_COOKIE_HTTPONLY = True,
    SESSION_COOKIE_SECURE = True,
    SESSION_PERMANENT = True,
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)
)

password_selected = os.environ.get("PASSWORD")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)

CERTIFICATE_DIR = os.path.join(app.root_path, 'static', 'certificates')


def generate_certificate(name, tier, title_size=110):
    """Draw `name` and today's date on the template for `tier` (a dict from tiers.get_tier).

    Templates live at static/certificates/<tier key>.png. A missing template is an
    error on purpose: falling back to another tier's image would hand out a
    certificate that names the wrong tier.
    """
    if len(name) > 18:
        title_size = 95  # change this to make the font smaller or bigger if required
    if not re.fullmatch(r'[a-z0-9_]+', tier['key']):
        raise ValueError(f"Unsafe tier key: {tier['key']!r}")
    my_img = Image.open(os.path.join(CERTIFICATE_DIR, f"{tier['key']}.png"))
    my_img = my_img.convert("RGB")
    width, height = my_img.size
    title_font = ImageFont.truetype(r'static/Anglecia-Pro-Display.otf', title_size)
    title_w = title_font.getlength(name)
    image_editable = ImageDraw.Draw(my_img)
    x = (width / 2) - (title_w / 2)
    y = height * 0.35  # change this to move the name text up or down if required
    image_editable.text((x, y), name, (141, 26, 26), font=title_font)

    date_font = ImageFont.truetype(r'static/OpenSans-Light.ttf', 30)
    date_text = datetime.today().strftime('%d/%m/%Y')
    date_x = width * 0.91
    date_y = height * 0.84
    image_editable.text((date_x, date_y), date_text, (0, 0, 0), font=date_font)

    obj = BytesIO()
    my_img.save(obj, format="PDF", resolution=100)
    obj.seek(0)
    return obj


def render_with_tiers(template):
    """Render a page that lists the award tiers (loaded from the API)."""
    try:
        return render_template(template, tiers=get_tiers())
    except TiersUnavailable as e:
        logging.error(f"Could not load award tiers for {template}: {e}")
        return render_template(template, tiers=[],
                               tiers_error="Could not load the award tiers. Please refresh, or reach out to Tech Ops!"), 503


def resolve_tier(key):
    """(tier, None) for an active tier key, otherwise (None, (json_error, status))."""
    try:
        tier = get_tier(key)
    except TiersUnavailable as e:
        logging.error(f"Could not load award tiers: {e}")
        return None, ({"error": "Could not load the award tiers, please try again or reach out to Tech Ops!"}, 503)
    if tier is None:
        return None, ({"error": f"Unknown or inactive tier: {key}"}, 400)
    return tier, None


@app.route('/')
def index():
    if session.get('logged_in'):
        return render_with_tiers("index.html")
    else:
        return redirect(url_for('login'))


@app.route('/generate-pdfs', methods=["POST", "GET"])
def generate_pdfs():
    if session.get('logged_in'):
        return render_with_tiers("generate-pdfs.html")
    else:
        return redirect(url_for('login'))


@app.route('/send-emails')
def send_emails():
    if session.get('logged_in'):
        return render_with_tiers("send-emails.html")
    else:
        return redirect(url_for('login'))
    

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        user_name = request.form.get("name", "").strip()
        user_ip = request.remote_addr
        if password == password_selected and user_name:
            session['logged_in'] = True
            session['user_name'] = user_name
            logging.info(f"LOGIN SUCCESS by '{user_name}' from {user_ip}")
            return redirect(url_for("send_emails"))
        else:
            logging.warning(f"LOGIN FAILURE by '{user_name}' from {user_ip}")
            return render_template("login_error.html")
        
    return render_template("login.html")


@app.route('/generate-hour-pdfs', methods=["POST"])
def gen_pdfs():
    tier_key = request.form.get("hours")  # This is the tier key
    user_name = session.get('user_name', 'Unknown')
    user_ip = request.remote_addr
    if not tier_key:
        logging.warning(f"PDF GENERATION FAILED (no tier) by '{user_name}'")
        return {"error": "Tier not provided"}, 400
    tier, error = resolve_tier(tier_key)
    if error:
        logging.warning(f"PDF GENERATION FAILED ({error[0]['error']}) by '{user_name}'")
        return error

    response = requests.get(f"{API_BASE}/getRecords", params={"tier": tier["key"]})
    names = []
    if response.status_code == 200:
        json_1 = response.json()
        for x in range(len(json_1)):
            names.append(json_1[x]["name"].strip())
        logging.info(f"PDF GENERATION by '{user_name}' from {user_ip} for tier '{tier['key']}' for names: {names}")
        file_list = []
        for name in names:
            cert = generate_certificate(name, tier)
            file_list.append((cert, f"{name} {tier['name']} Certificate.pdf"))

        save_dir = "tmp" if os.getenv("VERCEL") is None else "/tmp"
        os.makedirs(save_dir, exist_ok=True)
        zip_path = f"{save_dir}/{tier['key']} Certificates.zip"
        with ZipFile(zip_path, "w") as zipf:
            for cert, file_name in file_list:
                zipf.writestr(file_name, cert.read())

        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f"{tier['name']} Certificates.zip",
        )
    else:
        logging.error(f"PDF GENERATION ERROR by '{user_name}': {response.status_code} {response.text}")
        return {"error": "Failed to fetch records, please try again or reach out to Tech Ops!"}, 500


@app.route('/generate-pdf', methods=["POST"])
def gen():
    if request.method == 'POST':
        print(request.form)
        names = request.form.get("name").replace("\r", "").split("\n")
        tier_key = request.form.get("hours")
        emails = request.form.get("email")
        user_name = session.get('user_name', 'Unknown')
        user_ip = request.remote_addr
        if not names or not tier_key:
            print("all fields not filled")
            flash("Please fill in all the fields.")
            return render_with_tiers("index.html")
        tier, error = resolve_tier(tier_key)
        if error:
            logging.warning(f"PDF GENERATION FAILED ({error[0]['error']}) by '{user_name}'")
            flash(error[0]["error"])
            return render_with_tiers("index.html")

        file_list = []
        if len(names) > 1:
            logging.info(f"PDF GENERATION by '{user_name}' from {user_ip} for tier '{tier['key']}' for names: {names}")
            for name in names:
                name = name.strip()
                cert = generate_certificate(name, tier)
                file_list.append((cert, f"{name} {tier['name']} Certificate.pdf"))
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zipf:
                for cert, file_name in file_list:
                    zipf.writestr(file_name, cert.read())
            save_dir = "tmp" if os.getenv("VERCEL") is None else "/tmp"
            os.makedirs(save_dir, exist_ok=True)
            with open(f'{save_dir}/Certificates.zip', 'wb') as f:
                f.write(zip_buffer.getvalue())

            return send_file(f"{save_dir}/Certificates.zip", as_attachment=True, download_name="Certificates.zip")
        else:
            logging.info(f"PDF GENERATION by '{user_name}' for tier '{tier['key']}' for name: {names[0]}")
            cert = generate_certificate(names[0], tier)
            return send_file(cert, as_attachment=True, download_name=f"{names[0]} {tier['name']} Certificate.pdf")
    else:
        return render_with_tiers("index.html")


def build_gmail_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ['GMAIL_REFRESH_TOKEN'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=os.environ['GMAIL_CLIENT_ID'],
        client_secret=os.environ['GMAIL_CLIENT_SECRET'],
        scopes=['https://www.googleapis.com/auth/gmail.send']
    )
    return build('gmail', 'v1', credentials=creds)


# Cache the Gmail API service at startup
gmail_service = build_gmail_service()


def send_gmail_api_email(to, subject, html_body, body, attachment_bytes=None, attachment_filename=None):
    # Use the cached gmail_service
    global gmail_service

    if attachment_bytes and attachment_filename:
        message = MIMEMultipart()
        message['to'] = to
        message['from'] = "edu@instilt.com"
        message['subject'] = subject

        # Attach body
        message.attach(MIMEText(html_body, 'html'))
        # message.attach(MIMEText(body, 'plain'))

        # Attach PDF
        part = MIMEApplication(attachment_bytes, Name=attachment_filename)
        part['Content-Disposition'] = f'attachment; filename="{attachment_filename}"'
        message.attach(part)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    else:
        msg = MIMEText(body)
        msg['to'] = to
        msg['from'] = "edu@instilt.com"
        msg['subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))
        msg.attach(MIMEText(body, 'plain'))
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    gmail_service.users().messages().send(userId='me', body={'raw': raw}).execute()


def describe_tiers(tier_list):
    """The tiers as a sentence fragment for the email body: (html, plain text)."""
    def join(parts):
        return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + ", and " + parts[-1]
    html = join([f"<strong>{escape(t['name'])}</strong> ({t['hours_range']})" for t in tier_list])
    text = join([f"{t['name']} ({t['hours_range']})" for t in tier_list])
    return html, text


@app.route("/send-email", methods=["POST"])
def send_email():
    names = request.json.get("names")
    emails = request.json.get("emails")
    tier_key = request.json.get("hours")
    user_name = session.get('user_name', 'Unknown')
    user_ip = request.remote_addr

    if not names or not emails or not tier_key:
        logging.warning(f"EMAIL SEND FAILED (missing fields) by '{user_name}'")
        return {"error": "All fields (names, emails, hours) are required"}, 400
    if len(names) != len(emails):
        logging.warning(f"EMAIL SEND FAILED (count mismatch) by '{user_name}'")
        return {"error": "The number of names and emails must match"}, 400
    tier, error = resolve_tier(tier_key)
    if error:
        logging.warning(f"EMAIL SEND FAILED ({error[0]['error']}) by '{user_name}'")
        return error

    logging.info(f"EMAIL SEND by '{user_name}' from {user_ip} for tier '{tier['key']}' to: {list(zip(names, emails))}")

    # Build every certificate before sending anything, so a problem with the
    # template can't leave a half-sent batch.
    try:
        outgoing = []
        for name, email in zip(names, emails):
            name = name.strip().title()
            outgoing.append((name, email.strip(), generate_certificate(name, tier).read()))
        tier_list_html, tier_list_text = describe_tiers(get_tiers())
    except (OSError, ValueError, TiersUnavailable) as e:
        logging.error(f"EMAIL SEND FAILED (could not build certificates) by '{user_name}': {e}")
        return {"error": "Could not generate the certificates, nothing was sent. Please reach out to Tech Ops!"}, 500

    for name, email, cert_bytes in outgoing:
        subject = 'Instilt Volunteer Hour Certificate'

        html_body = f"""
        <html>
          <body>
            <p>Hi {name},</p>
            <p>
              We hope this email finds you well. Below you will find your volunteer
              hours certificate as a token of appreciation from us. Your commitment
              and generosity have made a real difference. Every hour you&#39;ve given
              has contributed to something bigger than yourself, leaving a lasting
              impact on those around you.
            </p>
            <p>
              The Certificate of Achievement is granted based on accumulated
              volunteer hours, with the following tiers:
              {tier_list_html}.
            </p>
            <p>Thank you for sharing your time, kindness, and energy.</p>
            <p>
              Best regards,<br/>
              Instilt Educate<br/>
            </p>
          </body>
        </html>
        """

        fallback_body = (
            f"Hi {name},\nWe hope this email finds you well. Below you will find your volunteer hours certificate as a token of appreciation from us. Your commitment and generosity have made a real difference. Every hour you've given has contributed to something bigger than yourself, leaving a lasting impact on those around you. The Certificate of Achievement is granted based on accumulated volunteer hours, with the following tiers: {tier_list_text}.\n"
            "Thank you for sharing your time, kindness, and energy.\n\n"
            "Best\n"
            "Instilt Educate"
        )
        try:
            send_gmail_api_email(
                to=email,
                subject=subject,
                html_body=html_body,
                body=fallback_body,
                attachment_bytes=cert_bytes,
                attachment_filename=f"{name} {tier['name']} Certificate.pdf"
            )
        except Exception as e:
            logging.error(f"Failed to send email to {email}: {e}")
            return {"error": f"Failed to send email to {email}"}, 500

    # Issue certificates after all emails sent
    success, result = issue_certificates(names, tier["key"])
    if not success:
        logging.error(f"Emails sent but failed to issue certificates for {names}: {result}")
        return {"error": f"Emails sent but failed to issue certificates: {result}"}, 500

    logging.info(f"Emails sent and certificates issued for: {names}")
    return {"message": "Emails sent and certificates issued successfully!"}, 200


def issue_certificates(names, tier):
    url = f"{API_BASE}/issueCertificates"
    payload = {"names": names, "tier": tier}
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return True, response.json()
        else:
            print(f"Failed to issue certificates: {response.status_code}", response.text)
            return False, response.text
    except Exception as e:
        print(f"Exception while issuing certificates: {e}")
        return False, str(e)


@app.route('/get-names-emails', methods=["GET"])
def get_names_emails():
    tier_key = request.args.get("hours")  # This is the tier key
    if not tier_key:
        return {"error": "Tier not provided"}, 400
    tier, error = resolve_tier(tier_key)
    if error:
        return error

    response = requests.get(f"{API_BASE}/getRecords", params={"tier": tier["key"]})
    if response.status_code == 200:
        json_data = response.json()
        names = [record["name"] for record in json_data]
        emails = [record["email"] for record in json_data if "email" in record]
        hours = [record.get("hours", "") for record in json_data]
        return {"names": names, "emails": emails, "hours": hours, "tier": tier["key"]}, 200
    else:
        print("Error fetching records:", response.status_code)
        print(response.text)
        return {"error": "Failed to fetch records"}, 500


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


if __name__ == '__main__':
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run()