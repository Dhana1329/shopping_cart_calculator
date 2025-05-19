
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a secure random string


def init_db():
    if not os.path.exists('database.db'):
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('''
            CREATE TABLE items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                mrp REAL,
                discount REAL,
                quantity INTEGER,
                category TEXT,
                final_price REAL,
                date TEXT,
                user_id INTEGER
            )
        ''')
        c.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

# Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
        except sqlite3.IntegrityError:
            flash('Username already exists. Please choose another.', 'error')
            conn.close()
            return redirect(url_for('signup'))
        conn.close()
        flash('Signup successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html', theme=session.get('theme', 'light'))

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html',theme=session.get('theme', 'light'))

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Protect index with login required
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    # Monthly savings tips (you can customize or fetch from DB later)
    savings_tips = [
        "Buy items in bulk to save money.",
        "Compare prices before purchasing.",
        "Use discount coupons whenever available.",
        "Avoid impulse buying.",
        "Plan your monthly budget and stick to it."
    ]

    if request.method == 'POST':
        name = request.form['name']
        mrp = float(request.form['mrp'])
        discount = float(request.form['discount']) if request.form['discount'] else 0.0
        quantity = int(request.form['quantity'])
        category = request.form['category']
        date = request.form['date']

        price_after_discount = mrp - (mrp * discount / 100)
        final_price = price_after_discount * quantity

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('INSERT INTO items (name, mrp, discount, quantity, category, final_price, date, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                  (name, mrp, discount, quantity, category, final_price, date, user_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM items WHERE user_id = ?', (user_id,))
    items = c.fetchall()
    conn.close()

    total = sum(item[6] for item in items)
    return render_template('index.html',items=items, total=total, username=session.get('username'),savings_tips=savings_tips)

# Edit and delete routes — also check session user_id
@app.route('/delete/<int:item_id>')
def delete_item(item_id):
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM items WHERE id = ? AND user_id = ?', (item_id, user_id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        mrp = float(request.form['mrp'])
        quantity = int(request.form['quantity'])
        discount = float(request.form['discount']) if request.form['discount'] else 0.0
        category = request.form['category']
        date = request.form['date']

        price_after_discount = mrp - (mrp * discount / 100)
        final_price = price_after_discount * quantity

        c.execute('''
            UPDATE items 
            SET name = ?, mrp = ?, discount = ?, quantity = ?, category = ?, final_price = ?, date = ?
            WHERE id = ? AND user_id = ?
        ''', (name, mrp, discount, quantity, category, final_price, date, item_id, user_id))

        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    else:
        c.execute('SELECT * FROM items WHERE id = ? AND user_id = ?', (item_id, user_id))
        item = c.fetchone()
        conn.close()
        if not item:
            flash('Item not found or unauthorized access.', 'error')
            return redirect(url_for('index'))
        return render_template('edit.html', item=item)
@app.route('/toggle-theme', methods=['POST'])
def toggle_theme():
    current_theme = session.get('theme', 'light')
    session['theme'] = 'dark' if current_theme == 'light' else 'light'
    return '', 204  # No content response



if __name__ == '__main__':
    init_db()
    app.run(debug=True)
