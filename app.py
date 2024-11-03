from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import boto3
from botocore.exceptions import ClientError
import os
from jose import jwt
import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Replace with a secure key for production
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://username:password@rds-endpoint:3306/database_name'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# AWS Cognito configuration
COGNITO_USER_POOL_ID = 'your_user_pool_id'
COGNITO_APP_CLIENT_ID = 'your_app_client_id'
COGNITO_DOMAIN = 'your_cognito_domain'  # e.g. 'yourapp.auth.us-east-1.amazoncognito.com'
REGION = 'your_region'

# Database Model
class Reservation(db.Model):
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=False)
    concert_id = db.Column(db.String(100), nullable=False)
    seats = db.Column(db.Integer, nullable=False)
    reservation_date = db.Column(db.DateTime, default=datetime.now())

    def __repr__(self):
        return f'<Reservation {self.id} - User {self.user_id}>'

# Home Route (Redirect to Cognito Login)
@app.route('/')
def index():
    return redirect(f'https://{COGNITO_DOMAIN}/login?client_id={COGNITO_APP_CLIENT_ID}&response_type=token&redirect_uri={url_for("cognito_callback", _external=True)}')

# Cognito Callback Route
@app.route('/cognito/callback')
def cognito_callback():
    access_token = request.args.get('access_token')

    if access_token:
        session['access_token'] = access_token  # Store token in session
        
        # Decode the token to get the user ID
        decoded_token = jwt.decode(access_token, options={"verify_signature": False})
        session['user_id'] = decoded_token['sub']  # Store user ID in session

        return redirect(url_for('dashboard'))
    else:
        return "Error: No access token provided", 400

# Dashboard Route
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))  # Redirect to login if not authenticated

    return render_template('dashboard.html', user_id=session['user_id'])

# Reserve Route
@app.route('/reserve', methods=['POST'])
def reserve():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    concert_id = request.form['concert_id']
    seats = request.form['seats']

    # Create a new reservation
    new_reservation = Reservation(user_id=session['user_id'], concert_id=concert_id, seats=seats)
    
    db.session.add(new_reservation)
    db.session.commit()
    
    return redirect(url_for('dashboard'))

# Logout Route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('access_token', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    db.create_all()  # Create the database tables if they don't exist
    app.run(host='0.0.0.0', port=5000, debug=True)
