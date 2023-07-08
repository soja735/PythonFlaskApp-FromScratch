from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
# from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, PasswordField, TextAreaField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
# app.config['MYSQL_PASSWORD'] = 'YES'
app.config['MYSQL_DB'] = 'myflaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# init MySQL
mysql = MySQL(app)

# data from file data.py
# Articles = Articles()


# Index
@app.route('/')
def index():
    return render_template('home.html')


# About Us
@app.route('/about')
def about():
    return render_template('about.html')


# Articles
@app.route('/articles')
def articles():
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()

    if result > 0:
        cur.close()
        return render_template('articles.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('articles.html', msg=msg)


# Single Article
@app.route('/article/<string:id>/')
def article(id):
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM articles WHERE id= %s", [id])
    article = cur.fetchone()
    return render_template('article.html', article=article)


class RegisterForm(Form):
    name = StringField('Name', [validators.length(min=1, max=50)])
    username = StringField('Username', [validators.length(min=4, max=25)])
    email = StringField('Email', [validators.length(min=6, max=60)])
    password = PasswordField('Password', [
        validators.data_required(),
        validators.EqualTo('confirm', message='password do not match')
    ])
    confirm = PasswordField('Confirm Password')


# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute Query
        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)",
                    (name, email, username, password))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('Successfully Registered!!!! You can log in', 'success')

        return redirect(url_for('index'))

    return render_template('register.html', form=form)


# Login
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        # Get Formfields
        username = request.form['username']
        password_candidate = request.form['password']

        # create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            data = cur.fetchone()
            password = data['password']

            # Verify password
            if sha256_crypt.verify(password_candidate, password):
                app.logger.info('Password Matched')
                # passed
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                cur.close()
                return redirect(url_for('dashboard'))
            else:
                # app.logger.info('Password Not Matched')
                error = 'Password not matched'
                return render_template('login.html', error=error)
        else:
            # app.logger.info('No user found')
            error = 'No User Found'
            return render_template('login.html', error=error)

    return render_template('login.html')


# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap


# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))


# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():

    cur = mysql.connection.cursor()

    author = session['username']

    result = cur.execute("SELECT * FROM articles WHERE author= %s", [author])
    articles = cur.fetchall()

    if result > 0:
        cur.close()
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('dashboard.html', msg=msg)


class ArticleForm(Form):
    title = StringField('Title', [validators.length(min=5, max=50)])
    body = TextAreaField('Body', [validators.length(min=50)])


# Add Article
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST':
        title = form.title.data
        body = form.body.data

        # create cursor
        cur = mysql.connection.cursor()

        # execute
        cur.execute("INSERT INTO articles(title,body,author) values(%s,%s,%s)", (title, body, session['username']))

        # commit to DB
        mysql.connection.commit()

        # close
        cur.close()
        flash('Article created', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_article.html', form=form)


# Edit Article
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    # create cursor
    cur = mysql.connection.cursor()

    # get the article by id
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    article = cur.fetchone()

    # get form
    form = ArticleForm(request.form)

    # Populate form fields
    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        # create cursor
        cur = mysql.connection.cursor()

        # execute
        cur.execute("UPDATE articles SET title= %s, body= %s WHERE id=%s", (title, body, id))

        # commit to DB
        mysql.connection.commit()

        # close
        cur.close()
        flash('Article Updated', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_article.html', form=form)


# Delete Article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):

    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM articles WHERE id= %s", [id])

    # commit to DB
    mysql.connection.commit()

    # close
    cur.close()

    flash('Article Deleted', 'success')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(debug=True)
