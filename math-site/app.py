from flask import Flask, render_template, request, redirect, url_for
import math

app = Flask(__name__)

# Текущая роль (по умолчанию студент)
current_role = 'student'

# Секретный ключ для доступа преподавателей
TEACHER_SECRET_KEY = "prof2026"

@app.route('/')
def index():
    return render_template('index.html', role=current_role)

@app.route('/reference')
def reference():
    return render_template('reference.html', role=current_role)

@app.route('/switch_role/student')
def switch_to_student():
    global current_role
    current_role = 'student'
    return redirect(request.referrer or url_for('index'))

@app.route('/switch_role/teacher', methods=['GET', 'POST'])
def switch_to_teacher():
    global current_role
    error = None
    if request.method == 'POST':
        entered_key = request.form.get('secret_key')
        if entered_key == TEACHER_SECRET_KEY:
            current_role = 'teacher'
            return redirect(url_for('index'))
        else:
            error = "Неверный секретный ключ!"
            return render_template('teacher_login.html', error=error, role=current_role)
    
    return render_template('teacher_login.html', error=None, role=current_role)

@app.route('/login')
def login():
    return render_template('login.html', role=current_role)

@app.route('/register')
def register():
    return render_template('register.html', role=current_role)

@app.route('/teacher_panel')
def teacher_panel():
    if current_role != 'teacher':
        return redirect(url_for('index'))
    return render_template('teacher_panel.html', role=current_role)

# --- КАЛЬКУЛЯТОРЫ ---
@app.route('/quadratic', methods=['GET', 'POST'])
def quadratic():
    result = None
    error = None
    if request.method == 'POST':
        try:
            a = float(request.form['a'])
            b = float(request.form['b'])
            c = float(request.form['c'])
            if a == 0:
                error = "Коэффициент 'a' не должен быть равен нулю!"
            else:
                d = b**2 - 4*a*c
                if d > 0:
                    x1 = (-b + math.sqrt(d)) / (2*a)
                    x2 = (-b - math.sqrt(d)) / (2*a)
                    result = f"Два корня: x1 = {x1:.2f}, x2 = {x2:.2f} (D = {d:.2f})"
                elif d == 0:
                    x = -b / (2*a)
                    result = f"Один корень: x = {x:.2f} (D = 0)"
                else:
                    result = f"Дискриминант отрицательный (D = {d:.2f}). Действительных корней нет."
        except ValueError:
            error = "Пожалуйста, введите корректные числа!"
    return render_template('quadratic.html', result=result, error=error, role=current_role)

@app.route('/matrix', methods=['GET', 'POST'])
def matrix():
    result = None
    error = None
    if request.method == 'POST':
        try:
            a11 = float(request.form['a11'])
            a12 = float(request.form['a12'])
            a21 = float(request.form['a21'])
            a22 = float(request.form['a22'])
            det = (a11 * a22) - (a12 * a21)
            result = f"Определитель матрицы det(A) = {det:.2f}"
        except ValueError:
            error = "Введите все числовые значения элементов матрицы!"
    return render_template('matrix.html', result=result, error=error, role=current_role)

@app.route('/vector', methods=['GET', 'POST'])
def vector():
    result = None
    error = None
    if request.method == 'POST':
        try:
            x1 = float(request.form['x1'])
            y1 = float(request.form['y1'])
            z1 = float(request.form['z1'])
            x2 = float(request.form['x2'])
            y2 = float(request.form['y2'])
            z2 = float(request.form['z2'])
            
            scalar_prod = x1*x2 + y1*y2 + z1*z2
            len1 = math.sqrt(x1**2 + y1**2 + z1**2)
            len2 = math.sqrt(x2**2 + y2**2 + z2**2)
            
            if len1 == 0 or len2 == 0:
                error = "Из-за нулевой длины угол не определить."
            else:
                cos_phi = scalar_prod / (len1 * len2)
                cos_phi = max(-1.0, min(1.0, cos_phi))
                phi_deg = math.degrees(math.acos(cos_phi))
                result = f"Скалярное произведение: {scalar_prod:.2f} | Угол между векторами: {phi_deg:.2f}°"
        except ValueError:
            error = "Введите координаты векторов!"
    return render_template('vector.html', result=result, error=error, role=current_role)

@app.route('/characteristic', methods=['GET', 'POST'])
def characteristic():
    result = None
    error = None
    if request.method == 'POST':
        try:
            p = float(request.form['p'])
            q = float(request.form['q'])
            d = p**2 - 4*q
            if d > 0:
                k1 = (-p + math.sqrt(d)) / 2
                k2 = (-p - math.sqrt(d)) / 2
                result = f"Действительные корни: k1 = {k1:.2f}, k2 = {k2:.2f}"
            elif d == 0:
                k = -p / 2
                result = f"Корень кратности 2: k1 = k2 = {k:.2f}"
            else:
                real = -p / 2
                imag = math.sqrt(abs(d)) / 2
                result = f"Комплексные корни: k1 = {real:.2f} + {imag:.2f}i, k2 = {real:.2f} - {imag:.2f}i"
        except ValueError:
            error = "Введите коэффициенты p и q!"
    return render_template('characteristic.html', result=result, error=error, role=current_role)

@app.route('/combinatorics', methods=['GET', 'POST'])
def combinatorics():
    result = None
    error = None
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
                
                result = f"Факториал n! = {fact_n} | Сочетания C(n,k) = {combinations} | Размещения A(n,k) = {arrangements}"
        except ValueError:
            error = "Введите целые числа для n и k!"
    return render_template('combinatorics.html', result=result, error=error, role=current_role)

if __name__ == '__main__':
    app.run(debug=True, port=8080)