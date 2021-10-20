from flask import Flask, request, session, jsonify, make_response, abort
from flask_mysqldb import MySQL
from flask_cors import CORS, cross_origin
import MySQLdb.cursors
import re
import os
from emailservice import EmailService


app = Flask(__name__)
CORS(app)

# Change this to your secret key (can be anything, it's for extra protection)
app.config['SECRET_KEY'] = os.urandom(64)

# CLEARDB_DATABASE_URL: mysql://bcfcddffea3dae:9ff902aa@us-cdbr-east-04.cleardb.com/heroku_b929c3e9bc76e21?reconnect=true

# Enter your database connection details below
app.config['MYSQL_HOST'] = 'us-cdbr-east-04.cleardb.com'
app.config['MYSQL_USER'] = 'bcfcddffea3dae'
app.config['MYSQL_PASSWORD'] = '9ff902aa'
app.config['MYSQL_DB'] = 'heroku_b929c3e9bc76e21'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_SSL'] = False

# Intialize MySQL
mysql = MySQL(app)


@app.route('/')
def index():
    print("Processing")


@app.route('/login', methods=['GET', 'POST'])
@cross_origin(origin='*')
def login():
    req_data = request.get_json(force=True)
    username = req_data['username']
    password = req_data['password']
    # Output message if something goes wrong...
    msg = ''

    # Check if account exists using MySQL
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        'SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password))
    # Fetch one record and return result
    account = cursor.fetchone()
    # If account exists in accounts table in out database
    if account:
        # Create session data, we can access this data in other routes
        session['loggedin'] = True
        session['id'] = account['id']
        session['username'] = account['username']
        session['email'] = account['email']
        print("inside login", session)
        # Generate Response
        resp = make_response(

            jsonify(
                {
                    '_message': 'Logged in successfully!',
                    'FromEmail': session['email'],
                    'isLoggedIn': True
                }
            )
        )
        resp.headers["Set-Cookie"] = session
        return resp
    else:
        # Generate Response
        return make_response(
            jsonify(
                {
                    '_message': 'Invalid Credentials!',
                    'isLoggedIn': False
                }
            )
        )


@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    # Generate Response
    return make_response(
        jsonify(
            {
                '_message': 'Logged out Successfully!',
                'isLoggedIn': False
            }
        )
    )


@app.route('/register', methods=['GET', 'POST'])
def register():
    req_data = request.get_json()
    username = req_data['username']
    password = req_data['password']
    email = req_data['email']

    # Output message if something goes wrong...
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in req_data and 'password' in req_data and 'email' in req_data:
        # Create variables for easy access
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'SELECT * FROM accounts WHERE username = %s', [username])
        account = cursor.fetchone()
        # If account exists show error and validation checks
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            # Account doesnt exists and the form data is valid, now insert new account into accounts table
            try:
                cursor.execute(
                    'INSERT INTO accounts VALUES (NULL, %s, %s, %s)', (username, password, email))
                mysql.connection.commit()
                return make_response(
                    jsonify(
                        {
                            '_message': ('User account %s created successfully!' % username)
                        }
                    )
                )
            except:
                return abort(500)

    else:
        # Form is empty... (no POST data)
        return make_response(
            jsonify(
                {
                    '_message': 'Please fill out the form!'
                }
            )
        )


@app.route('/sendmail', methods=['POST'])
def send_email():
    req_data = request.get_json()
    subject = req_data['subject']
    email_content = req_data['message']
    recipients = tuple(req_data['email'])
    if request.headers.get("email"):
        email = request.headers.get("email")
        print("Email here: ", email)

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute(
        'SELECT username, password FROM accounts WHERE email = %s', [email])
    creds = cursor.fetchone()
    username = creds["username"]
    password = creds["password"]

    mail = EmailService(email, password,
                        (app.config['MAIL_SERVER'], app.config['MAIL_PORT']), use_SSL=app.config['MAIL_USE_SSL'])

    mail.set_message(email_content, subject, username)
    mail.set_recipients(recipients)

    for i in range(3):
        try:
            mail.connect()
            mail.send_all(close_connection=False)

            return make_response(
                jsonify(
                    {
                        '_message': 'Mail sent successfully!'
                    }
                )
            )
        except Exception as err:
            app.config['MAIL_SERVER'] = 'smtp.live.com'
            app.config['MAIL_PORT'] = 587
            if i < 2:  # i is zero indexed
                continue
            else:
                return make_response(
                    jsonify(
                        {
                            '_message': 'Failed to send email due to Exception: ' + err
                        }
                    )
                )


if __name__ == "__main__":
    app.run()
