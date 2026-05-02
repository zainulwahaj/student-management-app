import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

DB_USER     = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'rootpassword')
DB_HOST     = os.environ.get('DB_HOST', 'localhost')
DB_PORT     = os.environ.get('DB_PORT', '3306')
DB_NAME     = os.environ.get('DB_NAME', 'students_db')

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Student(db.Model):
    __tablename__ = 'students'
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    semester   = db.Column(db.Integer,     nullable=False)
    cgpa       = db.Column(db.Float,       nullable=False)


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ─── Auth ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html')

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash('Invalid username or password.', 'danger')
            return render_template('login.html')

        session['user_id']  = user.id
        session['username'] = user.username
        flash(f'Welcome back, {user.username}!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# ─── Dashboard ───────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    total    = Student.query.count()
    depts    = db.session.query(Student.department, db.func.count()).group_by(Student.department).all()
    avg_cgpa = db.session.query(db.func.avg(Student.cgpa)).scalar() or 0
    return render_template('dashboard.html', total=total, depts=depts, avg_cgpa=round(avg_cgpa, 2))


# ─── Students CRUD ───────────────────────────────────────────────────────────

@app.route('/students')
@login_required
def students():
    query = request.args.get('q', '').strip()
    if query:
        data = Student.query.filter(
            Student.name.ilike(f'%{query}%') | Student.department.ilike(f'%{query}%')
        ).all()
    else:
        data = Student.query.all()
    return render_template('students.html', students=data, query=query)


@app.route('/students/add', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        name       = request.form.get('name', '').strip()
        email      = request.form.get('email', '').strip()
        department = request.form.get('department', '').strip()
        semester   = request.form.get('semester', '').strip()
        cgpa       = request.form.get('cgpa', '').strip()

        if not name or not email or not department or not semester or not cgpa:
            flash('All fields are required.', 'danger')
            return render_template('add_student.html')

        try:
            semester = int(semester)
            cgpa     = float(cgpa)
            if not (0.0 <= cgpa <= 4.0):
                raise ValueError
            if not (1 <= semester <= 8):
                raise ValueError
        except ValueError:
            flash('Invalid semester or CGPA value.', 'danger')
            return render_template('add_student.html')

        if Student.query.filter_by(email=email).first():
            flash('A student with this email already exists.', 'danger')
            return render_template('add_student.html')

        student = Student(name=name, email=email, department=department,
                          semester=semester, cgpa=cgpa)
        db.session.add(student)
        db.session.commit()
        flash('Student added successfully.', 'success')
        return redirect(url_for('students'))

    return render_template('add_student.html')


@app.route('/students/edit/<int:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)

    if request.method == 'POST':
        name       = request.form.get('name', '').strip()
        email      = request.form.get('email', '').strip()
        department = request.form.get('department', '').strip()
        semester   = request.form.get('semester', '').strip()
        cgpa       = request.form.get('cgpa', '').strip()

        if not name or not email or not department or not semester or not cgpa:
            flash('All fields are required.', 'danger')
            return render_template('edit_student.html', student=student)

        try:
            semester = int(semester)
            cgpa     = float(cgpa)
        except ValueError:
            flash('Invalid semester or CGPA value.', 'danger')
            return render_template('edit_student.html', student=student)

        existing = Student.query.filter_by(email=email).first()
        if existing and existing.id != student_id:
            flash('Another student with this email already exists.', 'danger')
            return render_template('edit_student.html', student=student)

        student.name       = name
        student.email      = email
        student.department = department
        student.semester   = semester
        student.cgpa       = cgpa
        db.session.commit()
        flash('Student updated successfully.', 'success')
        return redirect(url_for('students'))

    return render_template('edit_student.html', student=student)


@app.route('/students/delete/<int:student_id>', methods=['POST'])
@login_required
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    flash('Student deleted.', 'success')
    return redirect(url_for('students'))


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=False)
