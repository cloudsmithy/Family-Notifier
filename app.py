import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from authlib.integrations.flask_client import OAuth

# --- OIDC Configuration ---
LAZYCAT_BOX_DOMAIN = os.environ.get('LAZYCAT_BOX_DOMAIN')
LAZYCAT_APP_DOMAIN = os.environ.get('LAZYCAT_APP_DOMAIN')

CLIENT_ID      = os.getenv("LAZYCAT_AUTH_OIDC_CLIENT_ID")
CLIENT_SECRET  = os.getenv("LAZYCAT_AUTH_OIDC_CLIENT_SECRET")
AUTH_URI       = os.getenv("LAZYCAT_AUTH_OIDC_AUTH_URI")
TOKEN_URI      = os.getenv("LAZYCAT_AUTH_OIDC_TOKEN_URI")
USERINFO_URI   = os.getenv("LAZYCAT_AUTH_OIDC_USERINFO_URI")
JWKS_URI       = os.getenv("OIDC_JWKS_URI", f"https://{LAZYCAT_BOX_DOMAIN}/sys/oauth/keys")
REDIRECT_URI   = os.getenv("OIDC_REDIRECT_URI", f"https://{LAZYCAT_APP_DOMAIN}/oidc/callback")

required = [CLIENT_ID, CLIENT_SECRET, AUTH_URI, TOKEN_URI, USERINFO_URI, JWKS_URI, REDIRECT_URI]
oidc_configured = all(required)

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'a-very-secret-key') # 生产请改更安全
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=3650)

# Ensure the instance folder exists
try:
    os.makedirs(app.instance_path,exist_ok=True)
except OSError:
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'tasks.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "请先登录以访问此页面。"
login_manager.login_message_category = "info"

# --- Authlib OAuth Initialization ---
if oidc_configured:
    oauth = OAuth(app)
    oidc = oauth.register(
        name="casdoor",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        authorize_url=AUTH_URI,
        access_token_url=TOKEN_URI,
        userinfo_endpoint=USERINFO_URI,
        jwks_uri=JWKS_URI,
        client_kwargs={"scope": "openid profile email"},
        redirect_uri=REDIRECT_URI,
    )

# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=True) # Nullable for OIDC users
    oidc_sub = db.Column(db.String(128), unique=True, nullable=True) # OIDC subject identifier

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    assigner = db.Column(db.String(50), nullable=False)
    assignee = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Task {self.title}>'

class AuditEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    task_title = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('audit_events', lazy=True))

    def __repr__(self):
        return f'<AuditEvent {self.username} {self.action} {self.task_title}>'

# --- Flask-Login Loader ---
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- OIDC Routes ---
@app.route("/oidc/login")
def oidc_login():
    if not oidc_configured:
        flash("OIDC 功能未配置。", "error")
        return redirect(url_for('login'))
    nonce = secrets.token_urlsafe(16)
    resp = oidc.authorize_redirect(redirect_uri=REDIRECT_URI, nonce=nonce)
    resp.set_cookie("oidc_nonce", nonce, max_age=300, httponly=True)
    return resp

@app.route("/oidc/callback")
def oidc_callback():
    if not oidc_configured:
        flash("OIDC 功能未配置。", "error")
        return redirect(url_for('login'))
    try:
        token = oidc.authorize_access_token()
        nonce = request.cookies.get("oidc_nonce")
        claims = oidc.parse_id_token(token, nonce=nonce)

        oidc_sub = claims.get('sub')
        username = claims.get('preferred_username', claims.get('name', oidc_sub))

        user = User.query.filter_by(oidc_sub=oidc_sub).first()
        if not user:
            if User.query.filter_by(username=username).first():
                username = f"{username}_{secrets.token_hex(4)}"
            
            user = User(username=username, oidc_sub=oidc_sub)
            db.session.add(user)
            db.session.commit()
            flash("OIDC 用户创建成功！", "success")

        login_user(user, remember=True)
        return redirect(url_for('home'))

    except Exception as e:
        flash(f"OIDC 登录失败: {e}", "error")
        return redirect(url_for('login'))

# --- Standard Routes ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('用户名已存在。', 'error')
            return redirect(url_for('register'))
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('注册成功！请登录。', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', oidc_enabled=oidc_configured)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect(url_for('home'))
        else:
            flash('用户名或密码无效。', 'error')
    return render_template('login.html', oidc_enabled=oidc_configured)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def home():
    users = User.query.all()
    tasks = Task.query.filter_by(assignee=current_user.username, completed=False).order_by(Task.created_at.desc()).all()
    return render_template('index.html', users=users, current_user=current_user, tasks=tasks)

@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    title = request.form.get('title')
    assignee = request.form.get('assignee')
    if not title or not assignee:
        flash('任务标题和指派对象是必填项！', 'error')
    else:
        new_task = Task(title=title, assigner=current_user.username, assignee=assignee)
        db.session.add(new_task)
        db.session.commit()
        flash('任务已成功分派！', 'success')
    return redirect(url_for('home'))

@app.route('/complete/<int:task_id>')
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.assignee != current_user.username:
        flash('您无权完成此任务。', 'error')
        return redirect(url_for('home'))
    task.completed = True
    task.completed_at = datetime.utcnow()
    audit_event = AuditEvent(user_id=current_user.id, username=current_user.username, action='complete', task_title=task.title)
    db.session.add(audit_event)
    db.session.commit()
    flash(f'任务 "{task.title}" 已标记为完成！', 'success')
    return redirect(url_for('home'))

@app.route('/delete/<int:task_id>')
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.assigner != current_user.username and task.assignee != current_user.username:
        flash('您无权删除此任务。', 'error')
        return redirect(url_for('home'))
    audit_event = AuditEvent(user_id=current_user.id, username=current_user.username, action='delete', task_title=task.title)
    db.session.add(audit_event)
    db.session.delete(task)
    db.session.commit()
    flash(f'任务 "{task.title}" 已被删除。', 'success')
    return redirect(url_for('home'))

@app.route('/history')
@login_required
def history():
    completed_tasks = Task.query.filter_by(assignee=current_user.username, completed=True).order_by(Task.completed_at.desc()).all()
    return render_template('history.html', tasks=completed_tasks)

@app.route('/history/delete', methods=['POST'])
@login_required
def delete_history():
    try:
        num_deleted = Task.query.filter_by(completed=True).delete()
        db.session.commit()
        if num_deleted > 0:
            flash(f'已成功删除 {num_deleted} 条完成记录。', 'success')
        else:
            flash('没有可删除的完成记录。', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'删除历史记录时出错: {e}', 'error')
    return redirect(url_for('history'))

@app.route('/audit')
@login_required
def audit_log():
    events = AuditEvent.query.order_by(AuditEvent.timestamp.desc()).all()
    return render_template('audit.html', events=events)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001, host="0.0.0.0")
