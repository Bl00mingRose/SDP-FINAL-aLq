import os
import json
import random
from datetime import datetime

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.ensemble import RandomForestClassifier
import numpy as np

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password      = db.Column(db.String(200), nullable=False)
    performances  = db.relationship('UserPerformance', backref='user', lazy=True)

class UserPerformance(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic     = db.Column(db.String(100), nullable=False)
    score     = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Load questions.json
def load_questions():
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'questions.json'))
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for topic, qs in data.items():
                for q in qs:
                    q['id'] = int(q.get('id', 0))
                    q.setdefault('explanation', '')
            return data
    except Exception as e:
        app.logger.error(f'Could not load questions.json: {e}')
        return {}

questions = load_questions()

# Build dummy ML model
def build_model():
    X = np.random.rand(100, 5)
    y = np.random.randint(2, size=100)
    model = RandomForestClassifier()
    model.fit(X, y)
    return model

ml_model = build_model()

# Routes
@app.route('/')
def home():
    return redirect(url_for('dashboard')) if 'username' in session else redirect(url_for('login'))

@app.route('/signup', methods=['GET','POST'])
def signup():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        u  = request.form['username'].strip()
        p  = request.form['password']
        cp = request.form['confirm_password']
        if not u or not p:
            flash('Username and password required.', 'error')
        elif p != cp:
            flash('Passwords do not match.', 'error')
        elif User.query.filter_by(username=u).first():
            flash('Username already taken.', 'error')
        else:
            hashed = generate_password_hash(p)
            db.session.add(User(username=u, password=hashed))
            db.session.commit()
            flash('Account created! Please log in.', 'info')
            return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        u = request.form['username'].strip()
        p = request.form['password']
        user = User.query.filter_by(username=u).first()
        if user and check_password_hash(user.password, p):
            session['username'] = u
            flash('Logged in successfully.', 'info')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session['username']).first()
    perfs = UserPerformance.query.filter_by(user_id=user.id).order_by(UserPerformance.timestamp).all()
    performances = [{'topic': p.topic, 'score': p.score} for p in perfs]

    # Recommendation logic
    low = [t['topic'] for t in performances if t['score'] < 50]
    recommendation = low[0] if low else (random.choice(list(questions.keys())) if questions else None)

    # All available quiz topics
    all_topics = list(questions.keys())

    return render_template('dashboard.html',
                           username=user.username,
                           recommendation=recommendation,
                           performances=performances,
                           topics=all_topics)

@app.route('/quiz/random')
def random_quiz():
    """Mixed-topic quiz: sample across all questions."""
    if 'username' not in session:
        return redirect(url_for('login'))
    pool = [q for qs in questions.values() for q in qs]
    if not pool:
        flash('No questions available for a mixed quiz.', 'warn')
        return redirect(url_for('dashboard'))
    quiz_questions = random.sample(pool, min(10, len(pool)))
    return render_template('quiz.html',
                           topic='Mixed Topics',
                           questions=quiz_questions)

@app.route('/quiz/<topic>')
def quiz(topic):
    if 'username' not in session:
        return redirect(url_for('login'))
    if topic not in questions or not questions[topic]:
        flash(f'No questions for "{topic}".', 'warn')
        return redirect(url_for('dashboard'))
    qs = random.sample(questions[topic], min(len(questions[topic]), 10))
    return render_template('quiz.html', topic=topic, questions=qs)

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session['username']).first()
    topic = request.form.get('topic','')
    correct = total = 0
    wrong = []

    for key, val in request.form.items():
        if key.startswith('q_'):
            total += 1
            qid = int(key.split('_',1)[1])
            q = next((qq for qq in questions.get(topic,[]) if qq['id'] == qid), None)
            if q:
                if str(q['correct_answer']) == val:
                    correct += 1
                else:
                    wrong.append({
                        'text': q['text'],
                        'options': q['options'],
                        'selected': int(val),
                        'correct': q['correct_answer'],
                        'explanation': q.get('explanation', '')
                    })

    score = (correct / total) * 100 if total else 0.0
    db.session.add(UserPerformance(user_id=user.id, topic=topic, score=score))
    db.session.commit()

    # Retrain dummy model
    global ml_model
    ml_model = build_model()

    return render_template('quiz_result.html',
                           topic=topic,
                           score=score,
                           correct=correct,
                           total=total,
                           wrong_questions=wrong)

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
