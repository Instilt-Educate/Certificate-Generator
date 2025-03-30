from flask import Flask, send_file, request, render_template, flash
from PIL import Image, ImageFont, ImageDraw
from datetime import datetime
from flask_mail import Mail, Message
from zipfile import ZipFile
import zipfile
from io import BytesIO

import requests

app = Flask(__name__)
app.secret_key = "secret1"

mail = Mail(app)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'edu@instilt.com'
app.config['MAIL_PASSWORD'] = 'Children@123'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

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

@app.route('/generate-pdfs')
def gen_pdfs():  # put application's code here
    return render_template("generate-pdfs.html")

@app.route('/generate-pdfs-50',methods=["POST","GET"])
def pdfs_50():
    response = requests.get("https://tutor-timings.vercel.app/getRecords50")
    names = []

    if response.status_code == 200:
        json_1 = response.json()
        for x in range(len(json_1)):
            names.append(json_1[x]["name"])
        file_list = []
        for name in names:
            cert = generate_certificate(name, 50)
            file_list.append((cert, f"{name} 50 Hour Certificate.pdf"))

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zipf:
            for cert, file_name in file_list:
                zipf.writestr(file_name, cert.read())
        # print(os.listdir())
        with open('/tmp/50 Hour Certificates.zip', 'wb') as f:
            f.write(zip_buffer.getvalue())

        return send_file("/tmp/50 Hour Certificates.zip", as_attachment=True, download_name="50 Hour Certificates.zip")
    else:
        pdfs_50()
    
@app.route('/generate-pdfs-100', methods=["POST","GET"])
def pdfs_100():
    response = requests.get("https://tutor-timings.vercel.app/getRecords100")
    names = []

    if response.status_code == 200:
        json_1 = response.json()
        for x in range(len(json_1)):
            names.append(json_1[x]["name"])
        file_list = []
        for name in names:
            cert = generate_certificate(name, 100)
            file_list.append((cert, f"{name} {100} Hour Certificate.pdf"))
        
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zipf:
            for cert, file_name in file_list:
                zipf.writestr(file_name, cert.read())
        # print(os.listdir())
        with open('/tmp/100 Hour Certificates.zip', 'wb') as f:
            f.write(zip_buffer.getvalue())

        return send_file("/tmp/100 Hour Certificates.zip", as_attachment=True, download_name="100 Hour Certificates.zip")
    else:
        pdfs_100()
    
@app.route('/generate-pdfs-150' ,methods=["POST","GET"])
def pdfs_150():
    response = requests.get("https://tutor-timings.vercel.app/getRecords150")
    names = []

    if response.status_code == 200:
        json_1 = response.json()
        for x in range(len(json_1)):
            names.append(json_1[x]["name"])
        file_list = []
        for name in names:
            cert = generate_certificate(name, 150)
            file_list.append((cert, f"{name} {150} Hour Certificate.pdf"))

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zipf:
            for cert, file_name in file_list:
                zipf.writestr(file_name, cert.read())
        # print(os.listdir())
        with open('/tmp/150 Hour Certificates.zip', 'wb') as f:
            f.write(zip_buffer.getvalue())

        return send_file("/tmp/150 Hour Certificates.zip", as_attachment=True, download_name="150 Hour Certificates.zip")
    else:
        return render_template("generate-pdfs.html")
         

@app.route('/generate-pdf', methods=["POST"])
def gen():
    if request.method == 'POST':
        print(request.form)
        names = request.form.get("name").replace("\r", "").split("\n")
        hours = request.form.get("hours")
        
        emails =request.form.get("email")
        if not names or not hours:
            print("all fields not filled")
            flash("Please fill in all the fields.")
            return render_template("index.html")

        file_list = []
       
        if len(names) > 1:
            for name in names:
                cert = generate_certificate(name, int(hours))
                file_list.append((cert, f"{name} {hours} Hour Certificate.pdf"))
        
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zipf:
                for cert, file_name in file_list:
                    zipf.writestr(file_name, cert.read())
            # print(os.listdir())
            with open('/tmp/Certificates.zip', 'wb') as f:
                f.write(zip_buffer.getvalue())

            return send_file("/tmp/Certificates.zip", as_attachment=True, download_name="Certificates.zip")
        else:
            cert = generate_certificate(names[0], int(hours))
            return send_file(cert, as_attachment=True, download_name=f"{names[0]} {hours} Hour Certificate.pdf")
    else:
        return render_template("index.html")
@app.route("/send_email")
def send_email():
    attachment=request.form.get(attachment)
    emails=request.form.get(emails)
    hours=request.form.get(hours)
    for email in emails:
        msg = Message('Hello', sender = 'edu@instilt.com', recipients = [f'{email}'] )
        msg.body = "Hello, this is the email being sent, you have received {hours}"
        with app.open_resource(attachment) as attachment:
            msg.attach('attachment.pdf', 'application/pdf', attachment.read())
        mail.send(msg)

        return 'Email Sent successfuly!'   
    
if __name__ == '__main__':
    app.run()
