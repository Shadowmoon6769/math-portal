from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import logging
import math

# Настраиваем технические логи (будут видны в терминале VS Code и в панели Render)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'edu-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Секретный ключ для регистрации/входа преподавателя
TEACHER_SECRET_KEY = "prof2026"


# ==================== МОДЕЛИ БАЗЫ ДАННЫХ (ТАБЛИЦЫ) ====================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)  # Имя и Фамилия для отображения на сайте
    username = db.Column(db.String(80), unique=True, nullable=False)  # Email для входа
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='student')
    course = db.Column(db.Integer, default=1)


class Homework(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    course = db.Column(db.Integer, nullable=False)
    author = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.String(50), default=lambda: datetime.now().strftime("%d.%m.%Y %H:%M"))


class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.String(50), default=lambda: datetime.now().strftime("%d.%m.%Y %H:%M:%S"))


with app.app_context():
    db.create_all()


def add_log(text):
    logging.info(text)
    new_log = ActivityLog(message=text)
    db.session.add(new_log)
    db.session.commit()


def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return db.session.get(User, user_id)
    return None


def get_current_role():
    user = get_current_user()
    if user:
        return user.role
    return session.get('guest_role', 'student')


# ==================== ОСНОВНЫЕ МАРШРУТЫ ====================

@app.route('/ping')
def ping():
    return "OK", 200


@app.route('/')
def index():
    user = get_current_user()
    role = get_current_role()
    homeworks = []
    if user and user.role == 'student':
        homeworks = Homework.query.filter_by(course=user.course).order_by(Homework.id.desc()).all()
    elif role == 'teacher':
        homeworks = Homework.query.order_by(Homework.id.desc()).all()

    return render_template('index.html', role=role, user=user, homeworks=homeworks)


@app.route('/reference')
def reference():
    return render_template('reference.html', role=get_current_role(), user=get_current_user())


# ==================== РЕГИСТРАЦИЯ, ВХОД И ВЫХОД ====================

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'student')
        course = int(request.form.get('course', 1))
        secret_key = request.form.get('secret_key', '').strip()

        if not full_name or not username or not password:
            error = "Заполните все поля!"
        elif User.query.filter_by(username=username).first():
            error = "Пользователь с таким Email уже существует!"
        elif role == 'teacher' and secret_key != TEACHER_SECRET_KEY:
            error = "Неверный секретный ключ преподавателя!"
        else:
            if role == 'teacher':
                course = 0
            hashed_pw = generate_password_hash(password)
            new_user = User(full_name=full_name, username=username, password=hashed_pw, role=role, course=course)
            db.session.add(new_user)
            db.session.commit()

            session['user_id'] = new_user.id
            add_log(f"Регистрация: {full_name} ({username}, роль: {role}, курс: {course})")
            return redirect(url_for('index'))

    return render_template('register.html', role=get_current_role(), user=get_current_user(), error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            add_log(f"Вход в систему: {user.full_name} ({username})")
            return redirect(url_for('index'))
        else:
            error = "Неверный Email или пароль!"

    return render_template('login.html', role=get_current_role(), user=get_current_user(), error=error)


@app.route('/logout')
def logout():
    user = get_current_user()
    if user:
        add_log(f"Выход из системы: {user.full_name}")
    session.clear()
    return redirect(url_for('index'))


@app.route('/switch_role/student')
def switch_to_student():
    session['guest_role'] = 'student'
    return redirect(request.referrer or url_for('index'))


@app.route('/switch_role/teacher', methods=['GET', 'POST'])
def switch_to_teacher():
    error = None
    if request.method == 'POST':
        entered_key = request.form.get('secret_key')
        if entered_key == TEACHER_SECRET_KEY:
            session['guest_role'] = 'teacher'
            add_log("Гостевой вход в режим преподавателя по ключу")
            return redirect(url_for('teacher_panel'))
        else:
            error = "Неверный секретный ключ!"
            return render_template('teacher_login.html', error=error, role=get_current_role())

    return render_template('teacher_login.html', error=None, role=get_current_role())


# ==================== ПАНЕЛЬ ПРЕПОДАВАТЕЛЯ И СКРЫТЫЕ ЛОГИ АДМИНА ====================

@app.route('/teacher_panel', methods=['GET', 'POST'])
def teacher_panel():
    if get_current_role() != 'teacher':
        return redirect(url_for('index'))

    user = get_current_user()
    author_name = user.full_name if user else "Преподаватель"

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        course = int(request.form.get('course', 1))

        if title and description:
            hw = Homework(title=title, description=description, course=course, author=author_name)
            db.session.add(hw)
            db.session.commit()
            add_log(f"{author_name} добавил ДЗ «{title}» для {course} курса")
            return redirect(url_for('teacher_panel'))

    all_homeworks = Homework.query.order_by(Homework.id.desc()).all()
    return render_template(
        'teacher_panel.html',
        role=get_current_role(),
        user=user,
        homeworks=all_homeworks
    )


@app.route('/delete_homework/<int:hw_id>', methods=['POST'])
def delete_homework(hw_id):
    if get_current_role() != 'teacher':
        return redirect(url_for('index'))
    hw = db.session.get(Homework, hw_id)
    if hw:
        add_log(f"Удалено ДЗ «{hw.title}» ({hw.course} курс)")
        db.session.delete(hw)
        db.session.commit()
    return redirect(url_for('teacher_panel'))


@app.route('/admin_logs')
def admin_logs():
    """Скрытая страница логов только для владельца сайта: /admin_logs?key=prof2026"""
    if request.args.get('key') != TEACHER_SECRET_KEY:
        return "Доступ запрещен. Укажите ?key=секретный_ключ в адресной строке.", 403
    logs = ActivityLog.query.order_by(ActivityLog.id.desc()).limit(100).all()
    lines = [f"[{l.timestamp}] {l.message}" for l in logs]
    return "<pre style='background:#0f172a;color:#38bdf8;padding:20px;min-height:100vh;margin:0;'>" + "\n".join(lines) + "</pre>"


# ==================== КАЛЬКУЛЯТОРЫ С ПОШАГОВЫМ РЕШЕНИЕМ ====================

@app.route('/quadratic', methods=['GET', 'POST'])
def quadratic():
    result = None
    error = None
    steps = []
    if request.method == 'POST':
        try:
            a = float(request.form['a'])
            b = float(request.form['b'])
            c = float(request.form['c'])
            if a == 0:
                error = "Коэффициент 'a' не должен быть равен нулю!"
            else:
                steps.append(f"1. Записываем уравнение: {a}x² + ({b})x + ({c}) = 0")
                d = b**2 - 4*a*c
                steps.append(f"2. Находим дискриминант по формуле D = b² - 4ac: D = ({b})² - 4·({a})·({c}) = {d:.2f}")
                if d > 0:
                    x1 = (-b + math.sqrt(d)) / (2*a)
                    x2 = (-b - math.sqrt(d)) / (2*a)
                    steps.append(f"3. Так как D > 0, находим два корня:")
                    steps.append(f"   x₁ = (-({b}) + √{d:.2f}) / (2·{a}) = {x1:.2f}")
                    steps.append(f"   x₂ = (-({b}) - √{d:.2f}) / (2·{a}) = {x2:.2f}")
                    result = f"Два корня: x1 = {x1:.2f}, x2 = {x2:.2f} (D = {d:.2f})"
                elif d == 0:
                    x = -b / (2*a)
                    steps.append(f"3. Так как D = 0, корень один: x = -({b}) / (2·{a}) = {x:.2f}")
                    result = f"Один корень: x = {x:.2f} (D = 0)"
                else:
                    steps.append("3. Так как D < 0, действительных корней нет.")
                    result = f"Дискриминант отрицательный (D = {d:.2f}). Действительных корней нет."
        except ValueError:
            error = "Пожалуйста, введите корректные числа!"
    return render_template('quadratic.html', result=result, error=error, steps=steps, role=get_current_role(), user=get_current_user())


@app.route('/matrix', methods=['GET', 'POST'])
def matrix():
    result = None
    error = None
    steps = []
    if request.method == 'POST':
        try:
            a11 = float(request.form['a11'])
            a12 = float(request.form['a12'])
            a21 = float(request.form['a21'])
            a22 = float(request.form['a22'])
            main_diag = a11 * a22
            side_diag = a12 * a21
            det = main_diag - side_diag
            steps = [
                f"1. Умножаем элементы главной диагонали: {a11} · {a22} = {main_diag:.2f}",
                f"2. Умножаем элементы побочной диагонали: {a12} · {a21} = {side_diag:.2f}",
                f"3. Вычитаем из главной побочную: {main_diag:.2f} - ({side_diag:.2f}) = {det:.2f}"
            ]
            result = f"Определитель матрицы det(A) = {det:.2f}"
        except ValueError:
            error = "Введите все числовые значения элементов матрицы!"
    return render_template('matrix.html', result=result, error=error, steps=steps, role=get_current_role(), user=get_current_user())


@app.route('/vector', methods=['GET', 'POST'])
def vector():
    result = None
    error = None
    steps = []
    if request.method == 'POST':
        try:
            x1, y1, z1 = float(request.form['x1']), float(request.form['y1']), float(request.form['z1'])
            x2, y2, z2 = float(request.form['x2']), float(request.form['y2']), float(request.form['z2'])

            scalar_prod = x1*x2 + y1*y2 + z1*z2
            len1 = math.sqrt(x1**2 + y1**2 + z1**2)
            len2 = math.sqrt(x2**2 + y2**2 + z2**2)

            if len1 == 0 or len2 == 0:
                error = "Из-за нулевой длины угол не определить."
            else:
                cos_phi = max(-1.0, min(1.0, scalar_prod / (len1 * len2)))
                phi_deg = math.degrees(math.acos(cos_phi))
                steps = [
                    f"1. Скалярное произведение: ({x1}·{x2}) + ({y1}·{y2}) + ({z1}·{z2}) = {scalar_prod:.2f}",
                    f"2. Длина первого вектора |a| = √({x1}² + {y1}² + {z1}²) = {len1:.2f}",
                    f"3. Длина второго вектора |b| = √({x2}² + {y2}² + {z2}²) = {len2:.2f}",
                    f"4. Косинус угла: cos(φ) = {scalar_prod:.2f} / ({len1:.2f} · {len2:.2f}) = {cos_phi:.4f}",
                    f"5. Угол φ = arccos({cos_phi:.4f}) ≈ {phi_deg:.2f}°"
                ]
                result = f"Скалярное произведение: {scalar_prod:.2f} | Угол между векторами: {phi_deg:.2f}°"
        except ValueError:
            error = "Введите координаты векторов!"
    return render_template('vector.html', result=result, error=error, steps=steps, role=get_current_role(), user=get_current_user())


@app.route('/characteristic', methods=['GET', 'POST'])
def characteristic():
    result = None
    error = None
    steps = []
    if request.method == 'POST':
        try:
            p = float(request.form['p'])
            q = float(request.form['q'])
            d = p**2 - 4*q
            steps.append(f"1. Составляем уравнение: k² + ({p})k + ({q}) = 0")
            steps.append(f"2. Дискриминант: D = ({p})² - 4·({q}) = {d:.2f}")
            if d > 0:
                k1 = (-p + math.sqrt(d)) / 2
                k2 = (-p - math.sqrt(d)) / 2
                steps.append(f"3. D > 0 -> два действительных корня: k₁ = {k1:.2f}, k₂ = {k2:.2f}")
                result = f"Действительные корни: k1 = {k1:.2f}, k2 = {k2:.2f}"
            elif d == 0:
                k = -p / 2
                steps.append(f"3. D = 0 -> один корень кратности 2: k = -({p})/2 = {k:.2f}")
                result = f"Корень кратности 2: k1 = k2 = {k:.2f}"
            else:
                real = -p / 2
                imag = math.sqrt(abs(d)) / 2
                steps.append(f"3. D < 0 -> комплексно-сопряженные корни: α = {real:.2f}, β = {imag:.2f}")
                result = f"Комплексные корни: k1 = {real:.2f} + {imag:.2f}i, k2 = {real:.2f} - {imag:.2f}i"
        except ValueError:
            error = "Введите коэффициенты p и q!"
    return render_template('characteristic.html', result=result, error=error, steps=steps, role=get_current_role(), user=get_current_user())


@app.route('/combinatorics', methods=['GET', 'POST'])
def combinatorics():
    result = None
    error = None
    steps = []
    if request.method == 'POST':
        try:
            n = int(request.form['n'])
            k = int(request.form['k'])
            if n < 0 or k < 0 or n < k:
                error = "Условие: n ≥ k ≥ 0 и n, k — целые числа."
            else:
                fact_n = math.factorial(n)
                fact_k = math.factorial(k)
                fact_nk = math.factorial(n - k)
                arrangements = fact_n // fact_nk
                combinations = fact_n // (fact_k * fact_nk)
                steps = [
                    f"1. Вычисляем факториалы: {n}! = {fact_n}, {k}! = {fact_k}, ({n}-{k})! = {fact_nk}",
                    f"2. Размещения A({n},{k}) = {n}! / ({n}-{k})! = {fact_n} / {fact_nk} = {arrangements}",
                    f"3. Сочетания C({n},{k}) = {n}! / ({k}! · ({n}-{k})!) = {combinations}"
                ]
                result = f"Факториал n! = {fact_n} | Сочетания C(n,k) = {combinations} | Размещения A(n,k) = {arrangements}"
        except ValueError:
            error = "Введите целые числа для n и k!"
    return render_template('combinatorics.html', result=result, error=error, steps=steps, role=get_current_role(), user=get_current_user())


if __name__ == '__main__':
    app.run(debug=True, port=8080)
