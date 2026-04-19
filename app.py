import os
import io
import secrets
import string
from datetime import datetime, timedelta
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    send_file,
)
from werkzeug.security import generate_password_hash, check_password_hash
from models import get_db, close_db, init_db, query_db
from utils import login_required, role_required, validate_registration

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'replace_this_with_a_secure_random_key')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

@app.teardown_appcontext
def teardown(exception):
    close_db(exception)

try:
    with app.app_context():
        init_db()
except Exception as e:
    print(f"WARNING: Could not initialize database on startup: {e}")

@app.route('/')
def home():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            user = query_db('SELECT * FROM users WHERE email = ?', (email,), one=True)
            if user and check_password_hash(user['password'], password):
                session.clear()
                session['user_id'] = user['id']
                session['name'] = user['name']
                session['role'] = user['role']
                flash('Welcome back, {}!'.format(user['name']), 'success')
                return redirect(url_for('dashboard'))
            flash('Invalid email or password.', 'danger')
        except Exception as e:
            print(f"ERROR in login: {e}")
            flash('An error occurred during login. Please try again.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    classes = query_db('SELECT * FROM classes ORDER BY name')
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        college = request.form.get('college', '').strip()
        role = request.form.get('role')
        class_id = request.form.get('class_id')
        class_ids = request.form.getlist('class_ids')
        errors = validate_registration(name, email, password, college, role, class_id, class_ids)
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html', classes=classes)
        hashed = generate_password_hash(password)
        now = datetime.utcnow().isoformat()
        db = get_db()
        try:
            cursor = db.execute(
                'INSERT INTO users (name, email, password, college, role, class_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (name, email, hashed, college, role, class_id if role == 'student' else None, now),
            )
            user_id = cursor.lastrowid
            if role == 'teacher':
                for cid in class_ids:
                    db.execute('INSERT OR IGNORE INTO teacher_classes (teacher_id, class_id) VALUES (?, ?)', (user_id, cid))
            db.commit()
            flash('Account created successfully. Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception:
            db.rollback()
            flash('Email already registered or invalid form data.', 'danger')
    return render_template('register.html', classes=classes)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = query_db('SELECT * FROM users WHERE email = ?', (email,), one=True)
        if user:
            token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
            expires = datetime.utcnow() + timedelta(hours=1)
            db = get_db()
            db.execute('INSERT INTO reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)', (user['id'], token, expires.isoformat()))
            db.commit()
            flash('Password reset link generated. Use this token to reset: {}'.format(token), 'info')
            # In production, send email here
        else:
            flash('Email not found.', 'danger')
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset_token = query_db('SELECT * FROM reset_tokens WHERE token = ? AND expires_at > ?', (token, datetime.utcnow().isoformat()), one=True)
    if not reset_token:
        flash('Invalid or expired token.', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        password = request.form.get('password', '')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('reset_password.html')
        hashed = generate_password_hash(password)
        db = get_db()
        db.execute('UPDATE users SET password = ? WHERE id = ?', (hashed, reset_token['user_id']))
        db.execute('DELETE FROM reset_tokens WHERE id = ?', (reset_token['id'],))
        db.commit()
        flash('Password reset successfully. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user = query_db('SELECT * FROM users WHERE id = ?', (session['user_id'],), one=True)
    if user['role'] == 'teacher':
        classes = query_db(
            'SELECT c.id, c.name, COUNT(u.id) AS student_count, AVG(m.score) AS avg_score '
            'FROM classes c '
            'LEFT JOIN teacher_classes tc ON tc.class_id = c.id '
            'LEFT JOIN users u ON u.class_id = c.id '
            'LEFT JOIN marks m ON m.user_id = u.id '
            'WHERE tc.teacher_id = ? '
            'GROUP BY c.id '
            'ORDER BY c.name',
            (user['id'],)
        )
        students = query_db(
            "SELECT u.id, u.name, u.class_id, c.name AS class_name "
            "FROM users u "
            "JOIN classes c ON c.id = u.class_id "
            "WHERE u.role = 'student' AND u.class_id IN ("
            "SELECT class_id FROM teacher_classes WHERE teacher_id = ?) "
            "ORDER BY c.name, u.name",
            (user['id'],)
        )
        return render_template('teacher_dashboard.html', user=user, classes=classes, students=students)

    study_data = query_db('SELECT * FROM study_sessions WHERE user_id = ? ORDER BY start_time DESC', (user['id'],))
    marks = query_db('SELECT * FROM marks WHERE user_id = ? ORDER BY exam_date DESC', (user['id'],))
    total_seconds = sum(row['duration'] for row in study_data)
    today = datetime.utcnow().date()
    today_seconds = sum(
        row['duration']
        for row in study_data
        if datetime.fromisoformat(row['start_time']).date() == today
    )
    total_hours = round(total_seconds / 3600, 1)
    today_hours = round(today_seconds / 3600, 1)
    total_marks = sum(row['score'] for row in marks)
    average_mark = round(total_marks / len(marks), 1) if marks else 0
    grade = calculate_grade(average_mark)
    goal_progress = min(100, int(total_hours * 4))
    strong_subjects, weak_subjects = subject_strength_breakdown(marks)
    study_chart = build_study_time_series(study_data)
    performance_chart = build_performance_data(marks)
    leaderboard = query_db(
        'SELECT u.id, u.name, u.college, IFNULL(SUM(p.points), 0) AS total_points '
        'FROM users u LEFT JOIN points p ON p.user_id = u.id '
        'WHERE u.role = \'student\' '
        'GROUP BY u.id ORDER BY total_points DESC LIMIT 5'
    )
    rank = calculate_student_rank(user['id'])
    prediction = calculate_prediction(marks)
    feedbacks = query_db(
        'SELECT r.*, t.name AS teacher_name, c.name AS class_name FROM reviews r '
        'LEFT JOIN users t ON t.id = r.teacher_id '
        'LEFT JOIN classes c ON c.id = r.class_id '
        'WHERE r.student_id = ? ORDER BY r.created_at DESC LIMIT 5',
        (user['id'],)
    )
    return render_template(
        'student_dashboard.html',
        user=user,
        total_hours=total_hours,
        today_hours=today_hours,
        average_mark=average_mark,
        grade=grade,
        goal_progress=goal_progress,
        strong_subjects=strong_subjects,
        weak_subjects=weak_subjects,
        study_labels=study_chart['labels'],
        study_values=study_chart['values'],
        performance_labels=performance_chart['subjects'],
        performance_values=performance_chart['scores'],
        pie_labels=performance_chart['subjects'],
        pie_values=performance_chart['scores'],
        leaderboard=leaderboard,
        rank=rank,
        prediction=prediction,
        feedbacks=feedbacks,
        marks=marks,
    )

@app.route('/class/<int:class_id>')
@login_required
def class_detail(class_id):
    user = query_db('SELECT * FROM users WHERE id = ?', (session['user_id'],), one=True)
    if user['role'] != 'teacher':
        flash('Only teachers can access class details.', 'danger')
        return redirect(url_for('dashboard'))
    authorized = query_db('SELECT * FROM teacher_classes WHERE teacher_id = ? AND class_id = ?', (user['id'], class_id), one=True)
    if not authorized:
        flash('You are not assigned to that class.', 'danger')
        return redirect(url_for('dashboard'))
    class_info = query_db('SELECT * FROM classes WHERE id = ?', (class_id,), one=True)
    students = query_db(
        'SELECT u.id, u.name, u.email, u.college, IFNULL(SUM(s.duration), 0) AS study_seconds, '
        'IFNULL(AVG(m.score), 0) AS avg_score '
        'FROM users u '
        'LEFT JOIN study_sessions s ON s.user_id = u.id '
        'LEFT JOIN marks m ON m.user_id = u.id '
        'WHERE u.class_id = ? '
        'GROUP BY u.id ORDER BY avg_score DESC',
        (class_id,),
    )
    students = [dict(row) for row in students]
    for student in students:
        student['study_hours'] = round(student['study_seconds'] / 3600, 1)
    return render_template('class_detail.html', user=user, class_info=class_info, students=students)

@app.route('/session', methods=['POST'])
@login_required
def session_event():
    data = request.get_json() or {}
    action = data.get('action')
    user_id = session['user_id']
    db = get_db()
    if action == 'start':
        now = datetime.utcnow().isoformat()
        cursor = db.execute(
            'INSERT INTO study_sessions (user_id, start_time, created_at) VALUES (?, ?, ?)',
            (user_id, now, now),
        )
        db.commit()
        session['active_session'] = cursor.lastrowid
        return jsonify(status='started')
    if action == 'stop':
        session_id = session.pop('active_session', None)
        if not session_id:
            return jsonify(status='error', message='No active session found.'), 400
        duration = int(data.get('duration', 0))
        focused = int(data.get('focused', 0))
        tab_switches = int(data.get('tab_switches', 0))
        now = datetime.utcnow().isoformat()
        db.execute(
            'UPDATE study_sessions SET end_time = ?, duration = ?, focused = ?, tab_switches = ? WHERE id = ?',
            (now, duration, focused, tab_switches, session_id),
        )
        if duration > 0:
            points = duration // 360
            db.execute(
                'INSERT INTO points (user_id, points, reason, created_at) VALUES (?, ?, ?, ?)',
                (user_id, points, 'Study session earned points', now),
            )
        db.commit()
        return jsonify(status='stopped', earned_points=points)
    return jsonify(status='error', message='Invalid action.'), 400

@app.route('/add_marks', methods=['POST'])
@login_required
def add_marks():
    subject = request.form.get('subject', '').strip()
    score = request.form.get('score', '0')
    max_score = request.form.get('max_score', '100')
    exam_date = request.form.get('exam_date', datetime.utcnow().date().isoformat())
    if not subject or not score.isdigit():
        flash('Subject and numeric score are required.', 'danger')
        return redirect(url_for('dashboard'))
    score = int(score)
    max_score = int(max_score) if max_score.isdigit() else 100
    db = get_db()
    now = datetime.utcnow().isoformat()
    db.execute(
        'INSERT INTO marks (user_id, subject, score, max_score, exam_date) VALUES (?, ?, ?, ?, ?)',
        (session['user_id'], subject, score, max_score, exam_date),
    )
    db.commit()
    flash('Marks successfully added.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/feedback', methods=['POST'])
@login_required
def feedback():
    student_id = request.form.get('student_id')
    class_id = request.form.get('class_id')
    feedback_text = request.form.get('feedback', '').strip()
    if session['role'] != 'teacher':
        flash('Only teachers can submit reviews.', 'danger')
        return redirect(url_for('dashboard'))
    if not student_id or not feedback_text:
        flash('Student and feedback text are required.', 'danger')
        return redirect(url_for('dashboard'))
    db = get_db()
    now = datetime.utcnow().isoformat()
    db.execute(
        'INSERT INTO reviews (teacher_id, student_id, class_id, feedback, created_at) VALUES (?, ?, ?, ?, ?)',
        (session['user_id'], student_id, class_id if class_id else None, feedback_text, now),
    )
    db.commit()
    flash('Feedback submitted successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/report')
@login_required
def report():
    user = query_db('SELECT * FROM users WHERE id = ?', (session['user_id'],), one=True)
    total_study = query_db('SELECT IFNULL(SUM(duration), 0) AS total_seconds FROM study_sessions WHERE user_id = ?', (user['id'],), one=True)
    total_points = query_db('SELECT IFNULL(SUM(points), 0) AS total_points FROM points WHERE user_id = ?', (user['id'],), one=True)
    marks = query_db('SELECT * FROM marks WHERE user_id = ?', (user['id'],))
    total_marks = sum(row['score'] for row in marks)
    average_mark = round(total_marks / len(marks), 1) if marks else 0
    return render_template(
        'report.html',
        user=user,
        total_hours=round(total_study['total_seconds'] / 3600, 1),
        total_points=total_points['total_points'],
        marks=marks,
        average_mark=average_mark,
    )

@app.route('/download_report')
@login_required
def download_report():
    user = query_db('SELECT * FROM users WHERE id = ?', (session['user_id'],), one=True)
    total_study = query_db('SELECT IFNULL(SUM(duration), 0) AS total_seconds FROM study_sessions WHERE user_id = ?', (user['id'],), one=True)
    marks = query_db('SELECT * FROM marks WHERE user_id = ?', (user['id'],))
    content = [
        f'EduTrack AI Report for {user["name"]}',
        f'Role: {user["role"].title()}',
        f'College: {user["college"]}',
        f'Total Study Hours: {round(total_study["total_seconds"] / 3600, 1)}',
        f'Average Marks: {round(sum(row["score"] for row in marks) / len(marks), 1) if marks else 0}',
        '---',
        'Subject Results:',
    ]
    for row in marks:
        content.append(f'{row["subject"]}: {row["score"]}/{row["max_score"]} on {row["exam_date"]}')
    content_text = '\n'.join(content)
    buffer = io.BytesIO(content_text.encode('utf-8'))
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name='edutrack_report_{}.txt'.format(user['id']),
        mimetype='text/plain',
    )

def calculate_grade(average):
    if average >= 90:
        return 'A+'
    if average >= 80:
        return 'A'
    if average >= 70:
        return 'B+'
    if average >= 60:
        return 'B'
    return 'C'

def subject_strength_breakdown(marks):
    if not marks:
        return [], []
    subject_scores = {}
    for mark in marks:
        subject_scores.setdefault(mark['subject'], []).append(mark['score'])
    subject_averages = {subject: sum(scores) / len(scores) for subject, scores in subject_scores.items()}
    sorted_subjects = sorted(subject_averages.items(), key=lambda item: item[1], reverse=True)
    strong = [subject for subject, score in sorted_subjects[:3]]
    weak = [subject for subject, score in sorted_subjects[-3:]]
    return strong, weak

def build_study_time_series(study_data):
    labels = []
    values = []
    today = datetime.utcnow().date()
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        labels.append(day.strftime('%b %d'))
        day_seconds = sum(
            row['duration']
            for row in study_data
            if datetime.fromisoformat(row['start_time']).date() == day
        )
        values.append(round(day_seconds / 3600, 1))
    return {'labels': labels, 'values': values}

def build_performance_data(marks):
    subjects = []
    scores = []
    if not marks:
        return {'subjects': ['No Data'], 'scores': [0]}
    subject_totals = {}
    subject_counts = {}
    for row in marks:
        subject_totals[row['subject']] = subject_totals.get(row['subject'], 0) + row['score']
        subject_counts[row['subject']] = subject_counts.get(row['subject'], 0) + 1
    for subject, total in subject_totals.items():
        subjects.append(subject)
        scores.append(round(total / subject_counts[subject], 1))
    return {'subjects': subjects, 'scores': scores}

def calculate_student_rank(user_id):
    rows = query_db(
        'SELECT u.id, u.name, IFNULL(SUM(p.points), 0) AS total_points '
        'FROM users u LEFT JOIN points p ON p.user_id = u.id '
        'GROUP BY u.id ORDER BY total_points DESC'
    )
    sorted_ids = [row['id'] for row in rows]
    return sorted_ids.index(user_id) + 1 if user_id in sorted_ids else len(sorted_ids) + 1

def calculate_prediction(marks):
    scores = [row['score'] for row in reversed(marks)]
    if len(scores) < 2:
        return {'value': None, 'explanation': 'Add at least two exam scores to generate a prediction.'}
    x = list(range(1, len(scores) + 1))
    n = len(x)
    x_mean = sum(x) / n
    y_mean = sum(scores) / n
    numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, scores))
    denominator = sum((xi - x_mean) ** 2 for xi in x)
    slope = numerator / denominator if denominator else 0
    intercept = y_mean - slope * x_mean
    next_index = n + 1
    prediction = min(max(round(intercept + slope * next_index, 1), 0), 100)
    explanation = 'Linear trend estimated from {} exams, predicting your next score.'.format(n)
    return {'value': prediction, 'explanation': explanation}

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_DEBUG', '0') == '1',
    )
