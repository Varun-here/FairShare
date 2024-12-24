from flask import Flask, render_template, request, jsonify, session, url_for, redirect
import traceback
import mysql.connector
import re

app = Flask(__name__)

mydb = mysql.connector.connect(
  host = "localhost",
  user = "root",
  password = "",
  database = "InvoiceDB"
)

mycursor = mydb.cursor()

@app.route('/register', methods =['GET', 'POST'])
def register():
    msg = ''  # Initialize with empty string
    print(f"Request method: {request.method}")  # Debug print
    
    if request.method == 'POST':
        if 'username' in request.form and 'password' in request.form and 'email' in request.form:
            username = request.form['username']
            password = request.form['password']
            email = request.form['email']
            
            try:
                # Create new cursors for each operation
                check_cursor = mydb.cursor()
                check_cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
                username_check = check_cursor.fetchone()
                check_cursor.close()
                print(f"Username check result: {username_check}")  # Debug print
                
                if username_check:
                    msg = 'Username already exists !'
                else:
                    check_cursor = mydb.cursor()
                    check_cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
                    email_check = check_cursor.fetchone()
                    check_cursor.close()
                    print(f"Email check result: {email_check}")  # Debug print
                    
                    if email_check:
                        msg = 'Email already exists!'
                    elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
                        msg = 'Invalid email address!'
                    elif not re.match(r'[A-Za-z0-9]+', username):
                        msg = 'Username must contain only characters and numbers!'
                    elif not username or not password or not email:
                        msg = 'Please fill out the form!'
                    else:
                        insert_cursor = mydb.cursor()
                        insert_cursor.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)', 
                                            (username, email, password))
                        mydb.commit()
                        insert_cursor.close()
                        msg = 'You have successfully registered !'
                
            except mysql.connector.Error as err:
                print(f"Database error: {err}")  # Debug print
                msg = 'Database error occurred!'
                mydb.rollback()
                
    else:  # GET request
        msg = ''  # Ensure empty message for GET requests
        
    print(f"Final message: {msg}")  # Debug print
    return render_template('register.html', msg = msg)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # For GET requests, just render the template
    if request.method == 'GET':
        return render_template('login.html', msg='')
    
    # Only process login for actual POST requests with form data
    msg = ''
    if request.method == 'POST' and request.form.get('username') and request.form.get('password'):
        username = request.form['username']
        password = request.form['password']
        
        try:
            check_cursor = mydb.cursor()
            check_cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            username_present = check_cursor.fetchone()
            check_cursor.close()
            
            if username_present:
                check_cursor = mydb.cursor()
                check_cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
                pass_check = check_cursor.fetchone()
                check_cursor.close()
                
                if pass_check:
                    return redirect(url_for('index'))
                else:
                    msg = "Incorrect password!"
            else:
                msg = "Username not found!"
                
        except mysql.connector.Error as err:
            msg = 'Database error occurred!'
            mydb.rollback()
    
    return render_template('login.html', msg=msg)

@app.route('/')
def index():
    mycursor.execute("SELECT * FROM InvoiceDetails where InvoiceID='140'")
    data = mycursor.fetchall()

    mycursor.execute("SELECT * FROM Invoice where InvoiceID='140'")
    meta_data = mycursor.fetchall()

    headers = ("","Item name", "Quantity", "Price")

    return render_template('display_table.html', title='FairShare', headings = headers, data = data, meta_data = meta_data)

@app.route('/api/bills/store', methods=['POST'])
def receive_api_data():
    try:
        print("Received request data:", request.get_data())
        
        data = request.get_json()
        if not data:
            print("No JSON data received")
            return jsonify({
                'success': False,
                'error': 'No data received'
            }), 400

        print("Parsed JSON data:", data)
        
        user_splits = {}
        for item in data['items']:
            for split in item['splits']:
                user_id = split['userId']
                if user_id not in user_splits:
                    user_splits[user_id] = 0
                user_splits[user_id] += split['splitAmount']
        
        splits_list = [(user, amount) for user, amount in user_splits.items()]
        
        session['bill_data'] = {
            'items': data['items'],
            'splits': splits_list
        }
        
        return jsonify({
            'success': True,
            'redirect_url': url_for('bill_summary')
        })
        
    except Exception as e:
        print("Error in receive_api_data:", str(e))
        print("Traceback:", traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

app.secret_key = 'FairShare'

@app.route('/bill-summary')
def bill_summary():
    try:
        # Get bill data from session
        bill_data = session.get('bill_data', {})
        
        # Fetch original invoice data
        mycursor.execute("SELECT * FROM Invoice WHERE InvoiceID = '140'")
        invoice_data = mycursor.fetchall()
        
        return render_template('bill_summary.html',
                               splits=bill_data.get('splits', []),
                             items=bill_data.get('items', []),
                             invoice=invoice_data[0],
                             title='Bill Summary')
    except Exception as e:
        print("Error in bill_summary:", str(e))
        print("Traceback:", traceback.format_exc())
        return "An error occurred loading the summary", 500
    
@app.route('/group-list')
def group_list():
    mycursor.execute("SELECT group_id FROM user_groups WHERE user_id = '1'")
    group_list = mycursor.fetchall()

    parsed_group = []
    for i in group_list:
        parsed_group.append(i[0])
    return render_template('group_list.html',blocks = parsed_group)