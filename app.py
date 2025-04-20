from flask import Flask, send_file, request, render_template, flash
from PIL import Image, ImageFont, ImageDraw
from datetime import datetime
from flask_mail import Mail, Message
from zipfile import ZipFile
import zipfile
from io import BytesIO
import os

import requests

app = Flask(__name__)
app.secret_key = "secret1"

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'edu@instilt.com'
app.config['MAIL_PASSWORD'] = 'Children@123'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

def generate_certificate(name, hours, title_size=110):
    if len(name) > 18:
        title_size = 95  # change this to make the font smaller or bigger if required

    # change when more certificates are added
    if hours > 150:
        hours = 150

    my_img = Image.open(f'static/{hours}cert.png')
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
def index():  # put application's code here
    return render_template("index.html")

@app.route('/generate-pdfs', methods=["POST", "GET"])
def generate_pdfs():
    return render_template("generate-pdfs.html")

@app.route('/send-emails')
def send_emails():
    return render_template("send-emails.html")

@app.route('/generate-hour-pdfs', methods=["POST"])
def gen_pdfs():
    hours = request.form.get("hours")  # Get hours from form data
    if not hours:
        return {"error": "Hours not provided"}, 400

    response = requests.get(f"https://tutor-timings.vercel.app/getRecords{hours}")
    names = []
    if response.status_code == 200:
        json_1 = response.json()
        for x in range(len(json_1)):
            names.append(json_1[x]["name"].strip())
        file_list = []
        for name in names:
            cert = generate_certificate(name, int(hours))
            file_list.append((cert, f"{name} {hours} Hour Certificate.pdf"))

        with ZipFile("Certificates.zip", "w") as zipf:
            for cert, file_name in file_list:
                zipf.writestr(file_name, cert.read())

        return send_file(
            "Certificates.zip",
            as_attachment=True,
            download_name=f"{hours} Hour Certificates.zip",
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
        hours = request.form.get("hours")
        
        emails = request.form.get("email")
        if not names or not hours:
            print("all fields not filled")
            flash("Please fill in all the fields.")
            return render_template("index.html")

        file_list = []
       
        if len(names) > 1:
            for name in names:
                name = name.strip()
                cert = generate_certificate(name, int(hours))
                file_list.append((cert, f"{name} {hours} Hour Certificate.pdf"))
        
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zipf:
                for cert, file_name in file_list:
                    zipf.writestr(file_name, cert.read())
            # print(os.listdir())
            save_dir = "tmp" if os.getenv("VERCEL") is None else "/tmp"
            os.makedirs(save_dir, exist_ok=True)
            with open(f'{save_dir}/Certificates.zip', 'wb') as f:
                f.write(zip_buffer.getvalue())

            return send_file(f"{save_dir}/Certificates.zip", as_attachment=True, download_name="Certificates.zip")
        else:
            cert = generate_certificate(names[0], int(hours))
            return send_file(cert, as_attachment=True, download_name=f"{names[0]} {hours} Hour Certificate.pdf")
    else:
        return render_template("index.html")


@app.route("/send-email", methods=["POST"])
def send_email():
    names = request.json.get("names")
    emails = request.json.get("emails")
    hours = request.json.get("hours")

    if not names or not emails or not hours:
        return {"error": "All fields (names, emails, hours) are required"}, 400

    if len(names) != len(emails):
        return {"error": "The number of names and emails must match"}, 400
    # replace with own email for testing!!!
    # emails = ["ayush@instilt.com"]
    # names = ["test"]
    for name, email in zip(names, emails):
        name = name.strip()
        email = email.strip()
        cert = generate_certificate(name, int(hours))
        try:
            msg = Message(
                'Instilt Volunteer Hour Certificate',
                sender='edu@instilt.com',
                recipients=[email]
            )
            msg.body = f"Hello {name},\n\nPlease find attached your {hours}-hour certificate.\n\nBest regards,\nInstilt Team"
            msg.attach(f"{name} {hours} Hour Certificate.pdf", "application/pdf", cert.read())
            mail.send(msg)

        except Exception as e:
            print(f"Failed to send email to {email}: {e}")
            return {"error": f"Failed to send email to {email}"}, 500

    return {"message": "Emails sent successfully!"}, 200


@app.route('/get-names-emails', methods=["GET"])
def get_names_emails():
    hours = request.args.get("hours")  # Get hours from query parameters
    if not hours:
        return {"error": "Hours not provided"}, 400

    response = requests.get(f"https://tutor-timings.vercel.app/getRecords{hours}")
    if response.status_code == 200:
        json_data = response.json()
        names = [record["name"] for record in json_data]
        emails = [record["email"]["email"] for record in json_data if "email" in record]  # Ensure email exists
        return {"names": names, "emails": emails}, 200
    else:
        print("Error fetching records:", response.status_code)
        print(response.text)
        return {"error": "Failed to fetch records"}, 500
    
if __name__ == '__main__':
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run()
