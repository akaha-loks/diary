from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Конфигурация приложения
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///diary.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'  # Убедитесь, что это секретный ключ
db = SQLAlchemy(app)


# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    entries = db.relationship('Entry', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'


# Модель записи дневника
class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Entry {self.title}>'


# Главная страница
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    sort_by = request.args.get('sort_by', 'date')
    query = Entry.query.filter_by(user_id=session['user_id'])
    entries = query.order_by(Entry.title.asc() if sort_by == 'title' else Entry.date_created.desc()).all()

    days_of_week = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    months_of_year = ["Января", "Февраля", "Марта", "Апреля", "Мая", "Июня", "Июля", "Августа", "Сентября", "Октября",
                      "Ноября", "Декабря"]
    now = datetime.now()
    current_date = f"Сегодня: {days_of_week[now.weekday()]}, {now.day} {months_of_year[now.month - 1]} {now.year} года"

    return render_template('index.html', entries=entries, sort_by=sort_by, current_date=current_date)


# Регистрация
@app.route('/registr', methods=['GET', 'POST'])
def registr():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Пользователь с таким именем или почтой уже существует.', 'error')
            return redirect(url_for('registr'))

        try:
            new_user = User(username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash('Регистрация прошла успешно! Войдите в систему.', 'success')
            return redirect(url_for('signin'))
        except Exception as e:
            flash('Ошибка регистрации. Попробуйте снова.', 'error')
            return redirect(url_for('registr'))

    return render_template('registr.html')


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


@app.route('/forgot-password', methods=['GET'])
def forgot_password():
    # Здесь должна быть логика отправки письма с восстановлением пароля.
    # Для упрощения просто выводим флэш-сообщение.
    flash('Проверьте почту для восстановления пароля.', 'error')
    return redirect(url_for('signin'))

# Выход
@app.route('/signout')
def signout():
    session.clear()
    return redirect(url_for('signin'))

# Страница для добавления новой записи
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

# Страница для редактирования записи
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
        entry.date_updated = datetime.utcnow()  # Обновление даты последнего редактирования
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('edit_entry.html', entry=entry)

# Страница для удаления записи
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


# Страница для поиска записей
@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    if query:
        entries = Entry.query.filter(Entry.title.contains(query) | Entry.content.contains(query)).all()
    else:
        entries = []
    return render_template('search_results.html', entries=entries)


# Инициализация базы данных
with app.app_context():
    db.create_all()

# Запуск приложения
if __name__ == '__main__':
    app.run(debug=True)
