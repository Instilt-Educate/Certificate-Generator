from flask import Flask, send_file, request, render_template, flash, send_from_directory
from PIL import Image, ImageFont, ImageDraw
from datetime import datetime
from zipfile import ZipFile
import zipfile
from io import BytesIO
import dotenv
import os

import requests
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

dotenv.load_dotenv('.env')
app = Flask(__name__)
app.secret_key = "secret1"


def generate_certificate(name, tier, title_size=110):
    if len(name) > 18:
        title_size = 95  # change this to make the font smaller or bigger if required
    try:
        my_img = Image.open(f'static/{tier.lower()}.png')
    except:
        my_img = Image.open(f'static/bronze.png')
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


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/generate-pdfs', methods=["POST", "GET"])
def generate_pdfs():
    return render_template("generate-pdfs.html")


@app.route('/send-emails')
def send_emails():
    return render_template("send-emails.html")


@app.route('/generate-hour-pdfs', methods=["POST"])
def gen_pdfs():
    tier = request.form.get("hours")  # This is the tier name
    if not tier:
        return {"error": "Tier not provided"}, 400

    response = requests.get(f"https://tutor-timings.vercel.app/getRecords?tier={tier}")
    names = []
    if response.status_code == 200:
        json_1 = response.json()
        for x in range(len(json_1)):
            names.append(json_1[x]["name"].strip())
        file_list = []
        for name in names:
            cert = generate_certificate(name, tier)
            file_list.append((cert, f"{name} {tier.title()} Certificate.pdf"))

        save_dir = "tmp" if os.getenv("VERCEL") is None else "/tmp"
        os.makedirs(save_dir, exist_ok=True)
        with ZipFile(f"{save_dir}/{tier} Certificates.zip", "w") as zipf:
            for cert, file_name in file_list:
                zipf.writestr(file_name, cert.read())

        return send_file(
            f"{save_dir}/{tier} Certificates.zip",
            as_attachment=True,
            download_name=f"{tier.title()} Certificates.zip",
        )
    else:
        print("error in fetching records", response.status_code)
        print(response.text)
        return {"error": "Failed to fetch records, please try again or reach out to Tech Ops!"}, 500


@app.route('/generate-pdf', methods=["POST"])
def gen():
    if request.method == 'POST':
        print(request.form)
        names = request.form.get("name").replace("\r", "").split("\n")
        tier = request.form.get("hours")
        emails = request.form.get("email")
        if not names or not tier:
            print("all fields not filled")
            flash("Please fill in all the fields.")
            return render_template("index.html")

        file_list = []
        if len(names) > 1:
            for name in names:
                name = name.strip()
                cert = generate_certificate(name, tier)
                file_list.append((cert, f"{name} {tier.title()} Certificate.pdf"))
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
            cert = generate_certificate(names[0], tier)
            return send_file(cert, as_attachment=True, download_name=f"{names[0]} {tier.title()} Certificate.pdf")
    else:
        return render_template("index.html")


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


@app.route("/send-email", methods=["POST"])
def send_email():
    names = request.json.get("names")
    emails = request.json.get("emails")
    tier = request.json.get("hours")

    if not names or not emails or not tier:
        return {"error": "All fields (names, emails, hours) are required"}, 400
    if len(names) != len(emails):
        return {"error": "The number of names and emails must match"}, 400

    for name, email in zip(names, emails):
        name = name.strip().title()
        email = email.strip()
        cert = generate_certificate(name, tier)
        cert_bytes = cert.read()
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
              <strong>Bronze</strong> (50-99 hours),
              <strong>Silver</strong> (100-149 hours),
              <strong>Gold</strong> (150–199 hours),
              <strong>Platinum</strong> (200–249 hours),
              and <strong>Diamond</strong> (250+ hours).
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
            f"Hi {name},\nWe hope this email finds you well. Below you will find your volunteer hours certificate as a token of appreciation from us. Your commitment and generosity have made a real difference. Every hour you've given has contributed to something bigger than yourself, leaving a lasting impact on those around you. The Certificate of Achievement is granted based on accumulated volunteer hours, with the following tiers: Bronze (50-99 hours), Silver (100-149 hours), Gold (150-199 hours), Platinum (199-249 hours), and Diamond (250+ hours).\n"
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
                attachment_filename=f"{name} {tier.title()} Certificate.pdf"
            )
        except Exception as e:
            print(f"Failed to send email to {email}: {e}")
            return {"error": f"Failed to send email to {email}"}, 500

    # Issue certificates after all emails sent
    success, result = issue_certificates(names, tier)
    if not success:
        return {"error": f"Emails sent but failed to issue certificates: {result}"}, 500

    return {"message": "Emails sent and certificates issued successfully!"}, 200


def issue_certificates(names, tier):
    url = "https://tutor-timings.vercel.app/issueCertificates"
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
    tier = request.args.get("hours")  # This is the tier name
    if not tier:
        return {"error": "Tier not provided"}, 400

    response = requests.get(f"https://tutor-timings.vercel.app/getRecords?tier={tier}")
    if response.status_code == 200:
        json_data = response.json()
        names = [record["name"] for record in json_data]
        emails = [record["email"] for record in json_data if "email" in record]
        hours = [record.get("hours", "") for record in json_data]
        return {"names": names, "emails": emails, "hours": hours, "tier": tier}, 200
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