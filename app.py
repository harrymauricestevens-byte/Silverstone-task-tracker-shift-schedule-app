from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime
import csv
import io
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    role = db.Column(db.String(30), nullable=False)  # 'engineer' or 'manager'


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)
    date = db.Column(db.Date, nullable=False)
    role = db.Column(db.String(80), nullable=True)
    shift = db.Column(db.String(80), nullable=True)


# create database tables immediately (avoid removed Flask hooks in newer Flask)
with app.app_context():
    db.create_all()


def current_user():
    username = session.get('username')
    if not username:
        return None
    return User.query.filter_by(username=username).first()


@app.route('/')
def index():
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        role = request.form.get('role', 'engineer')
        if not username:
            flash('Enter a username')
            return redirect(url_for('login'))
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, role=role)
            db.session.add(user)
            db.session.commit()
        session['username'] = user.username
        return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    qdate = request.args.get('date')
    if qdate:
        try:
            sel_date = datetime.strptime(qdate, '%Y-%m-%d').date()
        except ValueError:
            sel_date = date.today()
    else:
        sel_date = date.today()

    # show all users' assignments for selected date
    users = User.query.order_by(User.username).all()
    assignments = Assignment.query.filter_by(date=sel_date).all()
    tasks = Task.query.order_by(Task.title).all()

    # build mapping user_id -> list of assignments
    by_user = {u.id: [] for u in users}
    for a in assignments:
        by_user.setdefault(a.user_id, []).append(a)

    return render_template('dashboard.html', user=user, sel_date=sel_date, users=users, assignments=by_user, tasks=tasks)


@app.route('/create_task', methods=['POST'])
def create_task():
    user = current_user()
    if not user or user.role != 'manager':
        flash('Only managers can create tasks')
        return redirect(url_for('dashboard'))
    title = request.form.get('title')
    description = request.form.get('description')
    if not title:
        flash('Task title required')
        return redirect(url_for('dashboard'))
    t = Task(title=title, description=description)
    db.session.add(t)
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    user = current_user()
    if not user or user.role != 'manager':
        flash('Only managers can edit tasks')
        return redirect(url_for('dashboard'))
    t = Task.query.get_or_404(task_id)
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        if not title:
            flash('Title required')
            return redirect(url_for('edit_task', task_id=task_id))
        t.title = title
        t.description = description
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('edit_task.html', user=user, task=t)


@app.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    user = current_user()
    if not user or user.role != 'manager':
        flash('Only managers can delete tasks')
        return redirect(url_for('dashboard'))
    t = Task.query.get_or_404(task_id)
    # remove references in assignments
    Assignment.query.filter_by(task_id=t.id).update({"task_id": None})
    db.session.delete(t)
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route('/assign', methods=['POST'])
def assign():
    user = current_user()
    if not user or user.role != 'manager':
        flash('Only managers can assign')
        return redirect(url_for('dashboard'))
    assignee = request.form.get('assignee')
    task_id = request.form.get('task_id') or None
    role = request.form.get('role') or None
    shift = request.form.get('shift') or None
    date_str = request.form.get('date')
    try:
        a_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        a_date = date.today()
    user_obj = User.query.get(int(assignee))
    if not user_obj:
        flash('Assignee not found')
        return redirect(url_for('dashboard'))
    task_obj = Task.query.get(int(task_id)) if task_id else None
    assignment = Assignment(user_id=user_obj.id, task_id=task_obj.id if task_obj else None, date=a_date, role=role, shift=shift)
    db.session.add(assignment)
    db.session.commit()
    return redirect(url_for('dashboard', date=a_date.isoformat()))


@app.route('/edit_assignment/<int:assignment_id>', methods=['GET', 'POST'])
def edit_assignment(assignment_id):
    user = current_user()
    if not user or user.role != 'manager':
        flash('Only managers can edit assignments')
        return redirect(url_for('dashboard'))
    a = Assignment.query.get_or_404(assignment_id)
    users = User.query.order_by(User.username).all()
    tasks = Task.query.order_by(Task.title).all()
    if request.method == 'POST':
        assignee = request.form.get('assignee')
        task_id = request.form.get('task_id') or None
        role = request.form.get('role') or None
        shift = request.form.get('shift') or None
        date_str = request.form.get('date')
        try:
            a_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception:
            a_date = a.date
        a.user_id = int(assignee)
        a.task_id = int(task_id) if task_id else None
        a.role = role
        a.shift = shift
        a.date = a_date
        db.session.commit()
        return redirect(url_for('dashboard', date=a_date.isoformat()))
    return render_template('edit_assignment.html', user=user, assignment=a, users=users, tasks=tasks)


@app.route('/delete_assignment/<int:assignment_id>', methods=['POST'])
def delete_assignment(assignment_id):
    user = current_user()
    if not user or user.role != 'manager':
        flash('Only managers can delete assignments')
        return redirect(url_for('dashboard'))
    a = Assignment.query.get_or_404(assignment_id)
    a_date = a.date
    db.session.delete(a)
    db.session.commit()
    return redirect(url_for('dashboard', date=a_date.isoformat()))


@app.route('/export_csv')
def export_csv():
    user = current_user()
    if not user:
        return redirect(url_for('login'))

    # support month=YYYY-MM or start,end dates
    month = request.args.get('month')
    start = request.args.get('start')
    end = request.args.get('end')
    rows = []
    if month:
        try:
            year, mon = month.split('-')
            y = int(year); m = int(mon)
            # compute first and last day naive
            from calendar import monthrange
            first = date(y, m, 1)
            last = date(y, m, monthrange(y, m)[1])
        except Exception:
            first = date.today()
            last = date.today()
    elif start and end:
        try:
            first = datetime.strptime(start, '%Y-%m-%d').date()
            last = datetime.strptime(end, '%Y-%m-%d').date()
        except Exception:
            first = date.today(); last = date.today()
    else:
        first = date.today(); last = date.today()

    assignments = Assignment.query.filter(Assignment.date >= first, Assignment.date <= last).order_by(Assignment.date).all()
    # CSV header: date, engineer, task, role, shift
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['date', 'engineer', 'task', 'role', 'shift'])
    for a in assignments:
        user_obj = User.query.get(a.user_id)
        task_obj = Task.query.get(a.task_id) if a.task_id else None
        writer.writerow([a.date.isoformat(), user_obj.username if user_obj else '', task_obj.title if task_obj else '', a.role or '', a.shift or ''])

    mem = output.getvalue()
    from flask import Response
    resp = Response(mem, mimetype='text/csv')
    resp.headers['Content-Disposition'] = f'attachment; filename=assignments_{first.isoformat()}_to_{last.isoformat()}.csv'
    return resp


if __name__ == '__main__':
    app.run(debug=True)