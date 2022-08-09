from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import requests
from flask_bcrypt import Bcrypt
from flask_paginate import Pagination, get_page_parameter

app = Flask(__name__)


bcrypt = Bcrypt()
# Change this to your secret key (can be anything, it's for extra protection)
app.secret_key = 'your secret key'

# Enter your database connection details below
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'pythonlogin'

# Intialize MySQL
mysql = MySQL(app)


@app.route('/')
def index():
    search = False
    q = request.args.get('q')
    if q:
        search = True
    page = request.args.get(get_page_parameter(), type=int, default=1)
    limit=10
    offset = page * limit - limit
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM best_movies')
    movies = cursor.fetchall()
    total = len(movies)

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute('SELECT * FROM best_movies limit %s OFFSET %s', (limit, offset))
    data = cur.fetchall()
    cur.close()

    pagination = Pagination(page=page, total=total, search=search, record_name='movies', per_page=limit)

    return render_template('example.html', movies=data, pagination=pagination)



@app.route('/pythonlogin/', methods=['GET', 'POST'])
def login():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
        # Fetch one record and return result
        account = cursor.fetchone()


        # If account exists in accounts table in out database
        if account:
            if bcrypt.check_password_hash(account['password'], password):
                # Create session data, we can access this data in other routes
                session['loggedin'] = True
                session['id'] = account['id']
                session['username'] = account['username']
                # Redirect to home page
                return redirect(url_for('home'))
            else:
                msg = 'Incorrect username/password!'

        else:
            # Account doesnt exist or username/password incorrect
            msg = 'Incorrect username/password!'
    # Show the login form with message (if any)
    return render_template('login.html', msg=msg)


# http://localhost:5000/python/logout - this will be the logout page
@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('login'))


# http://localhost:5000/pythinlogin/register - this will be the registration page, we need to use both GET and POST requests
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Output message if something goes wrong...
    msg = ''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password'])
        email = request.form['email']

        if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match("^\w+$", username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        elif verify_username(cursor, username):
            msg = 'Account already exists!'
        elif verify_email(cursor, email):
            msg = 'Email already exists!'
        else:
            # Account doesnt exists and the form data is valid, now insert new account into accounts table
            cursor.execute('INSERT INTO accounts VALUES (NULL, %s, %s, %s)', (username, password, email,))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)


def verify_username(cursor, username):
    # Check if account exists using MySQL
    cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
    account = cursor.fetchone()
    if account:
        return True
    else:
        return False


def verify_email(cursor, email):
    cursor.execute('SELECT * FROM accounts WHERE email = %s', (email,))
    check_mail = cursor.fetchone()
    if check_mail:
        return True
    else:
        return False

# http://localhost:5000/pythinlogin/home - this will be the home page, only accessible for loggedin users
@app.route('/home')
def home():
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM best_movies limit 20')
        movies = cursor.fetchall()
        return render_template('example.html', username=session['username'], movies=movies)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

# http://localhost:5000/pythinlogin/profile - this will be the profile page, only accessible for loggedin users
@app.route('/profile')
def profile():
    # Check if user is loggedin
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()
        # Show the profile page with account info
        return render_template('profile.html', account=account)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route('/info_movie/<id>')
def info_movie(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM best_movies WHERE id = %s', (id,))
    movies = cursor.fetchone()
    full_data = get_full_data(str(movies['imdb_id']))
    print(movies['imdb_id'])
    return render_template('info.html', movie=movies, data=full_data)

@app.route('/resultado')
def resultado():
    busqueda = "%" + request.args.get("buscar") + "%"
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM best_movies WHERE fullTitle like %s OR crew LIKE %s', (busqueda, busqueda))
    movies = cursor.fetchall()
    return render_template("resultados.html", movies=movies)




def get_full_data(idmb):
    _id = str(idmb)
    r = requests.get('https://imdb-api.com/en/API/Title/k_96qlv8f3/' + _id)
    print(r.json())
    return r.json()

#get_full_data("tt0110413")







if __name__  == "__main__":
    app.run(debug=True)