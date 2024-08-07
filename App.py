from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
from flask_pymongo import PyMongo
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import base64
import smtplib
import ssl
from email.message import EmailMessage

app = Flask(__name__)
app.config['MONGO_URI'] = 'mongodb://localhost:27017/your_database_name'
mongo = PyMongo(app)

client = MongoClient('mongodb://localhost:27017/')
db = client['medicare']
appointments_collection = db['appointments']
medicines_collection = db['medicines']
apiKey = "AIzaSyBynODTZ9IJWUtgawl9PrM--ah1b6LaxMI"

# Create a collection for BP and Sugar entries if it doesn't exist
bp_entries_collection = mongo.db.get_collection('bp_entries')
sugar_entries_collection = mongo.db.get_collection('sugar_entries')

if bp_entries_collection is None:
    # Collection does not exist, create it
    mongo.db.create_collection('bp_entries')
    # Retrieve the collection again
    bp_entries_collection = mongo.db.get_collection('bp_entries')

if sugar_entries_collection is None:
    # Collection does not exist, create it
    mongo.db.create_collection('sugar_entries')
    # Retrieve the collection again
    sugar_entries_collection = mongo.db.get_collection('sugar_entries')

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/index')
def index():
    # Fetch BP and Sugar entries from the MongoDB collections
    bp_entries = list(bp_entries_collection.find())
    sugar_entries = list(sugar_entries_collection.find())
    return render_template('index.html', bp_entries=bp_entries, sugar_entries=sugar_entries)

@app.route('/index2')
def index2():
    # Fetch BP and Sugar entries from the MongoDB collections
    bp_entries = list(bp_entries_collection.find())
    sugar_entries = list(sugar_entries_collection.find())
    return render_template('index2.html', bp_entries=bp_entries, sugar_entries=sugar_entries)

@app.route('/geolocation')
def geolocation():
    return render_template('geolocation.html')

@app.route('/medicines')
def medicine_page():
    # Fetch medicine details from the database
    medicine_details = list(medicines_collection.find())
    return render_template('medicines.html', medicines=medicine_details)

@app.route('/medicine_page')
def medicines_page():
    return render_template('medicine_page.html')

@app.route('/add_medicine', methods=['POST'])
def add_medicine():
    if request.method == 'POST':
        # Extract data from the form
        medicine_name = request.form['medicineName']
        start_date = request.form['startDate']
        end_date = request.form['endDate']
        morning_checkbox = request.form.get('morningCheckbox')
        morning_timing = request.form.get('morningTiming')
        morning_dose = request.form.get('morningDose')
        afternoon_checkbox = request.form.get('afternoonCheckbox')
        afternoon_timing = request.form.get('afternoonTiming')
        afternoon_dose = request.form.get('afternoonDose')
        night_checkbox = request.form.get('nightCheckbox')
        night_timing = request.form.get('nightTiming')
        night_dose = request.form.get('nightDose')

        # Handle file upload
        if 'medicinePicture' in request.files:
            medicine_picture = request.files['medicinePicture']
            # Read the file content
            image_data = medicine_picture.read()
            # Encode the file content in base64
            encoded_image = base64.b64encode(image_data).decode('utf-8')
        else:
            # Default image if no file is uploaded
            encoded_image = None

        # Construct the document to insert into the database
        medicine_doc = {
            'medicine_name': medicine_name,
            'start_date': start_date,
            'end_date': end_date,
            'morning': {
                'checkbox': morning_checkbox,
                'timing': morning_timing,
                'dose': morning_dose
            },
            'afternoon': {
                'checkbox': afternoon_checkbox,
                'timing': afternoon_timing,
                'dose': afternoon_dose
            },
            'night': {
                'checkbox': night_checkbox,
                'timing': night_timing,
                'dose': night_dose
            },
            'medicine_picture': encoded_image  # Add the image data to the document
        }
        # Insert the document into the collection
        medicines_collection.insert_one(medicine_doc)

        return redirect(url_for('medicine_page'))

# Route for the appointments page
@app.route('/appointments')
def appointments():
    # Retrieve appointments from the database
    appointments_list = list(appointments_collection.find())
    return render_template('appointments.html', appointments=appointments_list)

# Route for adding a new appointment
@app.route('/add_appointment', methods=['POST'])
def add_appointment():
    if request.method == 'POST':
        # Get data from the form
        hospital_name = request.form['hospital_name']
        appointment_date = request.form['appointment_date']
        appointment_time = request.form['appointment_time']

        # Create a dictionary for the new appointment
        new_appointment = {
            'hospital_name': hospital_name,
            'appointment_date': appointment_date,
            'appointment_time': appointment_time
        }   

        # Insert the new appointment into the database
        appointments_collection.insert_one(new_appointment)

        # Return a JSON response indicating success
        return jsonify({'message': 'Appointment added successfully'}), 200
    else:
        # If not a POST request, return an error
        return jsonify({'message': 'Invalid request method'}), 405

# Route for deleting an appointment
@app.route('/delete_appointment', methods=['POST'])
def delete_appointment():
    if request.method == 'POST':
        # Get the ID of the appointment to delete
        appointment_id = request.form['appointment_id']

        # Delete the appointment from the database
        result = appointments_collection.delete_one({'_id': ObjectId(appointment_id)})

        if result.deleted_count == 1:
            return jsonify({'message': 'Appointment deleted successfully'}), 200
        else:
            return jsonify({'message': 'Appointment not found or could not be deleted'}), 400
    else:
        return jsonify({'message': 'Invalid request method'}), 405

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup():
    username = request.form.get('username')
    password = request.form.get('password')

    # In a real application, you would hash the password before storing it.
    # For simplicity, this example uses plain text passwords.
    
    # Check if the username already exists
    if mongo.db.users.find_one({'username': username}):
        alert_message = 'Username already exists. Please choose a different one.'
        return f'<script>alert("{alert_message}"); window.location.replace("/signup");</script>'

    # Add the new user to the database
    mongo.db.users.insert_one({'username': username, 'password': password})

    alert_message = f'Successfully registered {username}!'
    return f'<script>alert("{alert_message}"); window.location.replace("/");</script>'



@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/reminders')
def reminders():
    # Get today's date
    today_date = datetime.now().strftime('%Y-%m-%d')

    # Retrieve appointments data from the database for today
    appointments = list(appointments_collection.find({'appointment_date': today_date}))
    medicines = list(medicines_collection.find())

    # Send email with appointment details
    if appointments:
        subject = 'Today\'s Appointment Reminders'
        body = '\n'.join([f"Hospital: {appointment['hospital_name']}, Date: {appointment['appointment_date']}, Time: {appointment['appointment_time']}" for appointment in appointments])
        send_email(subject, body)

    # Render the reminders page with appointment details
    return render_template('reminders.html', appointments=appointments, medicines=medicines, today_date=today_date)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    # Check if the username and password match a record in the database
    user = mongo.db.users.find_one({'username': username, 'password': password})

    if user:
        return redirect(url_for('index'))
    else:
        alert_message = 'Invalid username or password. Please try again.'
        return f'<script>alert("{alert_message}"); window.location.replace("/login");</script>'


@app.route('/geocode', methods=['GET'])
def geocode_address():
    address = request.args.get('address')
    if address:
        try:
            response = requests.get('https://maps.googleapis.com/maps/api/geocode/json', params={
                'address': address,
                'key': apiKey
            })
            data = response.json()
            if data['status'] == 'OK':
                location = data['results'][0]['geometry']['location']
                latitude = location['lat']
                longitude = location['lng']
                return jsonify({'latitude': latitude, 'longitude': longitude})
            else:
                return jsonify({'error': 'No results found for the address.'}), 404
        except Exception as e:
            return jsonify({'error': 'An error occurred while processing the request.'}), 500
    else:
        return jsonify({'error': 'Address parameter is required.'}), 400
    
@app.route('/add_bp_entry', methods=['POST'])
def add_bp_entry():
    if request.method == 'POST':
        try:
            # Get data from the form
            bp_date = request.form['bpDate']
            bp_reading = request.form['bpReading']

            # Create a dictionary for the new BP entry
            bp_entry = {
                'date': bp_date,
                'bp_reading': bp_reading
            }

            # Add the new BP entry to the MongoDB collection
            bp_entries_collection.insert_one(bp_entry)

            # Send email notification
            subject = "New BP Entry Added"
            body = f"New BP Entry:\nDate: {bp_date}\nBP Reading: {bp_reading}"
            send_email(subject, body)

            # Redirect back to the index page
            
            return redirect(url_for('index2'))

        except Exception as e:
            # Log the exception (consider using a proper logging system in production)
            print(f"Error adding BP entry: {str(e)}")

            # Return an error message
            
            return redirect(url_for('index'))

# Route for adding Sugar entries
@app.route('/add_sugar_entry', methods=['POST'])
def add_sugar_entry():
    if request.method == 'POST':
        try:
            # Get data from the form
            sugar_date = request.form['sugarDate']
            sugar_reading = request.form['sugarReading']

            # Create a dictionary for the new Sugar entry
            sugar_entry = {
                'date': sugar_date,
                'sugar_reading': sugar_reading
            }

            # Add the new Sugar entry to the MongoDB collection
            sugar_entries_collection.insert_one(sugar_entry)

            # Send email notification
            subject = "New Sugar Entry Added"
            body = f"New Sugar Entry:\nDate: {sugar_date}\nSugar Reading: {sugar_reading}"
            send_email(subject, body)

            # Redirect back to the index page
            
            return redirect(url_for('index2'))

        except Exception as e:
            # Log the exception (consider using a proper logging system in production)
            print(f"Error adding Sugar entry: {str(e)}")

            # Return an error message
            
            return redirect(url_for('index2'))

def send_email(subject, body):
    email_sender = 'lavyamehta123@gmail.com'
    email_password = 'cbho ndmh ncvb zmqm'  # Use your email app password here
    email_receiver = 'lavyamehta123@gmail.com'

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = email_sender
    msg['To'] = email_receiver

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
        server.login(email_sender, email_password)
        server.send_message(msg)
        print("Email sent successfully!")
if __name__ == '__main__':
    app.run(debug=True)
