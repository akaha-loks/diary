import requests
from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import re
import pytz
from flask_migrate import Migrate

# Инициализация приложения
app = Flask(__name__)

# Конфигурация приложения
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///diary.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'

# Инициализация базы данных и миграции
db = SQLAlchemy(app)
migrate = Migrate(app, db)

timezone = pytz.timezone('Asia/Bishkek')

# Получаем текущее время с учетом часового пояса
now = datetime.now(timezone)

# Форматируем время, например, как "23:03:10"
current_time = now.strftime('%H:%M:%S')

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    entries = db.relationship('Entry', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

# Модель записи
class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, default=lambda: datetime.now(timezone))  # Используем KGT
    date_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone), onupdate=lambda: datetime.now(timezone))  # Обновляем с учетом часовой зоны
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Entry {self.title}>'


# Главная страница
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    query = request.args.get('query', '').strip().lower()
    user_id = session['user_id']

    all_entries = Entry.query.filter_by(user_id=user_id).order_by(Entry.date_created.desc()).all()

    if query:
        entries = [entry for entry in all_entries if query in entry.title.lower()]
    else:
        entries = all_entries

    days_of_week = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    months_of_year = ["Января", "Февраля", "Марта", "Апреля", "Мая", "Июня", "Июля", "Августа", "Сентября", "Октября", "Ноября", "Декабря"]

    # Настроим правильный часовой пояс для Бишкека
    timezone = pytz.timezone('Asia/Bishkek')
    now = datetime.now(timezone)

    current_date = f"Сегодня: {days_of_week[now.weekday()]}, {now.day} {months_of_year[now.month - 1]} {now.year} года"

    return render_template('index.html', entries=entries, current_date=current_date, query=query)


# Регистрация
import requests

@app.route('/registr', methods=['GET', 'POST'])
def registr():
    if request.method == 'POST':
        # reCAPTCHA token
        recaptcha_response = request.form.get('g-recaptcha-response')
        secret_key = '6LcmFpoqAAAAALCaeTAF4G6Hyp5HSvVx7qHRsPEx'  # Ваш секретный ключ

        # Проверка reCAPTCHA
        verify_url = 'https://www.google.com/recaptcha/api/siteverify'
        data = {'secret': secret_key, 'response': recaptcha_response}
        response = requests.post(verify_url, data=data).json()

        if not response.get('success'):
            flash('Ошибка проверки CAPTCHA. Попробуйте снова.', 'error')
            return redirect(url_for('registr'))

        # Логика регистрации пользователя
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')

        if not re.match(r'^[a-zA-Z0-9_.+-]+@gmail\.com$', email):
            flash('Почтовый адрес должен быть в формате @gmail.com', 'error')
            return redirect(url_for('registr'))

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Пользователь с таким именем или почтой уже существует.', 'error')
            return redirect(url_for('registr'))

        try:
            new_user = User(username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash('Регистрация прошла успешно! Войдите в систему.', 'success')
            return redirect(url_for('signin'))
        except:
            flash('Ошибка регистрации. Попробуйте снова.', 'error')
            return redirect(url_for('registr'))

    return render_template('registr.html')


# Авторизация
@app.route('/sign-in', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']

        user = User.query.filter((User.username == login) | (User.email == login)).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        else:
            flash('Некорректный логин, почта или пароль.', 'error')

    return render_template('sign-in.html')

# Выход
@app.route('/signout')
def signout():
    session.clear()
    return redirect(url_for('signin'))

# Добавление записи
@app.route('/add-entry', methods=['GET', 'POST'])
def add_entry():
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        new_entry = Entry(title=title, content=content, user_id=session['user_id'])
        try:
            db.session.add(new_entry)
            db.session.commit()
            return redirect(url_for('index'))
        except:
            return "There was an issue adding your entry."

    return render_template('add_entry.html')

# Редактирование записи
@app.route('/edit-entry/<int:id>', methods=['GET', 'POST'])
def edit_entry(id):
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    entry = Entry.query.get_or_404(id)
    if entry.user_id != session['user_id']:
        return "You do not have permission to edit this entry."

    if request.method == 'POST':
        entry.title = request.form['title']
        entry.content = request.form['content']
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('edit_entry.html', entry=entry)

# Удаление записи
@app.route('/delete-entry/<int:id>')
def delete_entry(id):
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    entry = Entry.query.get_or_404(id)
    if entry.user_id != session['user_id']:
        return "You do not have permission to delete this entry."

    try:
        db.session.delete(entry)
        db.session.commit()
        return redirect(url_for('index'))
    except:
        return "There was an issue deleting the entry."

@app.route('/view-entry/<int:entry_id>')
def view_entry(entry_id):
    entry = Entry.query.get(entry_id)  # Получаем запись по ID
    if entry:
        return render_template('view_entry.html', entry=entry)
    else:
        flash('Запись не найдена!', 'danger')
        return redirect(url_for('index'))


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    # Логика для восстановления пароля
    return render_template('forgot-password.html')


# Инициализация базы данных
with app.app_context():
    db.create_all()

# Запуск приложения
if __name__ == '__main__':
    app.run(debug=True)