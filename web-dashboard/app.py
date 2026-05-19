#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'

API_URL = os.getenv('API_URL', 'http://localhost:8000')

# ====================================================================================================
# DATABASE MODELS
# ====================================================================================================

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Subscription
    subscription_plan = db.Column(db.String(50), default='free')
    subscription_expires = db.Column(db.DateTime, nullable=True)
    
    # API Key
    api_key = db.Column(db.String(100), unique=True, nullable=True)
    
    # Relations
    servers = db.relationship('Server', backref='owner', lazy=True)
    licenses = db.relationship('LicenseKey', backref='creator', lazy=True)
    transactions = db.relationship('PaymentTransaction', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_premium(self):
        return self.subscription_plan in ['premium', 'enterprise'] and self.subscription_expires > datetime.utcnow()

class Server(db.Model):
    __tablename__ = 'servers'
    
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.String(50), unique=True, nullable=False)
    server_name = db.Column(db.String(200), nullable=False)
    server_icon = db.Column(db.String(500), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    license_key = db.Column(db.String(100), unique=True, nullable=True)
    license_expires = db.Column(db.DateTime, nullable=True)
    features = db.Column(db.Text, default='{}')
    
    is_active = db.Column(db.Boolean, default=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Statistics
    member_count = db.Column(db.Integer, default=0)
    message_count = db.Column(db.Integer, default=0)
    
    def get_features(self):
        return json.loads(self.features) if self.features else {}

class LicenseKey(db.Model):
    __tablename__ = 'license_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    plan = db.Column(db.String(50), nullable=False)  # premium, enterprise
    duration_days = db.Column(db.Integer, default=30)
    
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    used_by = db.Column(db.Integer, db.ForeignKey('servers.id'), nullable=True)
    used_at = db.Column(db.DateTime, nullable=True)
    is_used = db.Column(db.Boolean, default=False)
    
    expires_at = db.Column(db.DateTime, nullable=True)

class PaymentTransaction(db.Model):
    __tablename__ = 'payment_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    plan = db.Column(db.String(50), nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    
    transaction_id = db.Column(db.String(100), unique=True)
    payment_method = db.Column(db.String(50))
    payment_details = db.Column(db.Text, nullable=True)
    
    status = db.Column(db.String(50), default='pending')  # pending, success, failed, expired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)
    expired_at = db.Column(db.DateTime, nullable=True)

class BotUsage(db.Model):
    __tablename__ = 'bot_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.String(50), nullable=False)
    command_name = db.Column(db.String(100))
    user_id = db.Column(db.String(50))
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

# ====================================================================================================
# PRICING PLANS
# ====================================================================================================

PLANS = {
    'free': {
        'name': 'Free',
        'price': 0,
        'price_idr': 0,
        'duration': 0,
        'features': [
            'Invite Tracker Basic (50 invites)',
            'Leveling System Basic',
            'Giveaway 1 round/month',
            'Up to 100 members',
            'Basic Support'
        ],
        'limits': {
            'max_members': 100,
            'max_giveaways': 1,
            'max_invites': 50,
            'custom_commands': False,
            'voice_xp': False,
            'level_roles': False
        }
    },
    'premium': {
        'name': 'Premium',
        'price': 9.99,
        'price_idr': 149000,
        'duration': 30,
        'features': [
            '✅ Unlimited Invite Tracking',
            '✅ Advanced Leveling System',
            '✅ Voice XP Bonus',
            '✅ Unlimited Giveaway Rounds',
            '✅ Custom Commands',
            '✅ Weekly Auto Leaderboard',
            '✅ Priority Support',
            '✅ No Member Limit',
            '✅ Level Roles',
            '✅ Welcome Messages'
        ],
        'limits': {
            'max_members': 0,
            'max_giveaways': 0,
            'max_invites': 0,
            'custom_commands': True,
            'voice_xp': True,
            'level_roles': True
        }
    },
    'enterprise': {
        'name': 'Enterprise',
        'price': 49.99,
        'price_idr': 749000,
        'duration': 30,
        'features': [
            '✅ All Premium Features',
            '✅ Dedicated Support 24/7',
            '✅ Custom Bot Development',
            '✅ API Access',
            '✅ White Label Option',
            '✅ Multiple Server License',
            '✅ Analytics Dashboard',
            '✅ Auto Backup & Restore',
            '✅ Custom Integrations'
        ],
        'limits': {
            'max_members': 0,
            'max_giveaways': 0,
            'max_invites': 0,
            'custom_commands': True,
            'voice_xp': True,
            'level_roles': True,
            'multi_server': True
        }
    }
}

# ====================================================================================================
# AUTHENTICATION ROUTES
# ====================================================================================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html', plans=PLANS)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'danger')
            return render_template('register.html')
        
        user = User(
            username=username,
            email=email,
            api_key=secrets.token_urlsafe(32)
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        flash('Registration successful!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

# ====================================================================================================
# DASHBOARD ROUTES
# ====================================================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    servers = Server.query.filter_by(owner_id=current_user.id).all()
    return render_template('dashboard.html', user=current_user, servers=servers, plans=PLANS)

@app.route('/dashboard/servers')
@login_required
def dashboard_servers():
    servers = Server.query.filter_by(owner_id=current_user.id).all()
    return render_template('dashboard_servers.html', servers=servers)

@app.route('/dashboard/billing')
@login_required
def dashboard_billing():
    transactions = PaymentTransaction.query.filter_by(user_id=current_user.id).order_by(PaymentTransaction.created_at.desc()).all()
    return render_template('dashboard_billing.html', transactions=transactions, plans=PLANS)

@app.route('/pricing')
def pricing():
    return render_template('pricing.html', plans=PLANS)

# ====================================================================================================
# API ROUTES (Internal)
# ====================================================================================================

@app.route('/api/add-server', methods=['POST'])
@login_required
def add_server():
    data = request.json
    server_id = data.get('server_id')
    server_name = data.get('server_name')
    server_icon = data.get('server_icon')
    
    existing = Server.query.filter_by(server_id=server_id).first()
    if existing:
        return jsonify({'success': False, 'error': 'Server already registered'})
    
    server = Server(
        server_id=server_id,
        server_name=server_name,
        server_icon=server_icon,
        owner_id=current_user.id
    )
    
    db.session.add(server)
    db.session.commit()
    
    return jsonify({'success': True, 'server': {
        'id': server.id,
        'name': server.server_name,
        'server_id': server.server_id
    }})

@app.route('/api/activate-license', methods=['POST'])
@login_required
def activate_license():
    data = request.json
    server_id = data.get('server_id')
    license_key = data.get('license_key')
    
    # Find license
    license = LicenseKey.query.filter_by(key=license_key, is_used=False).first()
    if not license:
        return jsonify({'success': False, 'error': 'Invalid license key'})
    
    # Find server
    server = Server.query.filter_by(id=server_id, owner_id=current_user.id).first()
    if not server:
        return jsonify({'success': False, 'error': 'Server not found'})
    
    # Activate license
    license.is_used = True
    license.used_by = server.id
    license.used_at = datetime.utcnow()
    license.expires_at = datetime.utcnow() + timedelta(days=license.duration_days)
    
    server.license_key = license_key
    server.license_expires = license.expires_at
    server.features = json.dumps(PLANS[license.plan]['limits'])
    
    # Update user subscription
    user = current_user
    user.subscription_plan = license.plan
    user.subscription_expires = license.expires_at
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'plan': license.plan,
        'expires': license.expires_at.isoformat(),
        'features': PLANS[license.plan]['features']
    })

@app.route('/api/server-stats/<int:server_id>')
@login_required
def server_stats(server_id):
    server = Server.query.filter_by(id=server_id, owner_id=current_user.id).first()
    if not server:
        return jsonify({'error': 'Server not found'}), 404
    
    usage = BotUsage.query.filter_by(server_id=server.server_id).order_by(BotUsage.recorded_at.desc()).limit(50).all()
    
    return jsonify({
        'server': {
            'name': server.server_name,
            'license': server.license_key,
            'expires': server.license_expires.isoformat() if server.license_expires else None,
            'features': server.get_features()
        },
        'usage': [{
            'date': u.recorded_at.strftime('%Y-%m-%d %H:%M'),
            'command': u.command_name,
            'user': u.user_id
        } for u in usage]
    })

# ====================================================================================================
# PAYMENT ROUTES
# ====================================================================================================

@app.route('/checkout/<plan_name>')
@login_required
def checkout(plan_name):
    if plan_name not in PLANS or plan_name == 'free':
        flash('Invalid plan selected', 'danger')
        return redirect(url_for('pricing'))
    
    plan = PLANS[plan_name]
    return render_template('checkout.html', plan=plan)

@app.route('/api/create-payment', methods=['POST'])
@login_required
def create_payment():
    data = request.json
    plan_name = data.get('plan')
    payment_method = data.get('payment_method', 'midtrans')
    
    if plan_name not in PLANS or plan_name == 'free':
        return jsonify({'success': False, 'error': 'Invalid plan'})
    
    plan = PLANS[plan_name]
    transaction_id = secrets.token_urlsafe(16)
    
    # Create transaction record
    transaction = PaymentTransaction(
        user_id=current_user.id,
        amount=plan['price'],
        plan=plan_name,
        duration_days=plan['duration'],
        transaction_id=transaction_id,
        payment_method=payment_method,
        expired_at=datetime.utcnow() + timedelta(hours=24)
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    # Integrate with Midtrans
    if payment_method == 'midtrans':
        return create_midtrans_payment(transaction, plan)
    elif payment_method == 'xendit':
        return create_xendit_payment(transaction, plan)
    
    return jsonify({'success': False, 'error': 'Invalid payment method'})

def create_midtrans_payment(transaction, plan):
    import hashlib
    
    order_id = f"ORDER-{transaction.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    gross_amount = plan['price_idr'] if 'price_idr' in plan else plan['price'] * 15000
    
    # Midtrans configuration
    server_key = os.getenv('MIDTRANS_SERVER_KEY')
    client_key = os.getenv('MIDTRANS_CLIENT_KEY')
    
    # Prepare payment data
    payment_data = {
        'transaction_details': {
            'order_id': order_id,
            'gross_amount': gross_amount
        },
        'credit_card': {
            'secure': True
        },
        'customer_details': {
            'first_name': current_user.username,
            'email': current_user.email
        }
    }
    
    # Generate signature
    signature = hashlib.sha512(f"{order_id}{gross_amount}{server_key}".encode()).hexdigest()
    
    return jsonify({
        'success': True,
        'payment_url': f"https://app.sandbox.midtrans.com/snap/v2/transactions",
        'order_id': order_id,
        'amount': gross_amount,
        'signature': signature
    })

def create_xendit_payment(transaction, plan):
    amount = plan['price_idr'] if 'price_idr' in plan else plan['price'] * 15000
    
    # Xendit configuration
    secret_key = os.getenv('XENDIT_SECRET_KEY')
    
    return jsonify({
        'success': True,
        'payment_url': f"https://checkout.xendit.co/v2/invoice",
        'amount': amount,
        'external_id': f"INV-{transaction.id}"
    })

@app.route('/api/payment-callback', methods=['POST'])
def payment_callback():
    data = request.json
    order_id = data.get('order_id')
    transaction_id = data.get('transaction_id')
    status = data.get('status')
    
    transaction = PaymentTransaction.query.filter_by(transaction_id=transaction_id).first()
    if not transaction:
        return jsonify({'success': False}), 404
    
    if status == 'success':
        transaction.status = 'success'
        transaction.paid_at = datetime.utcnow()
        
        # Generate license key
        license_key = secrets.token_urlsafe(32)
        
        new_license = LicenseKey(
            key=license_key,
            plan=transaction.plan,
            duration_days=transaction.duration_days,
            created_by=transaction.user_id
        )
        
        db.session.add(new_license)
        db.session.commit()
        
        # Send email to user
        send_license_email(transaction.user.email, license_key, transaction.plan)
        
        return jsonify({'success': True, 'license_key': license_key})
    
    transaction.status = 'failed'
    db.session.commit()
    
    return jsonify({'success': False})

def send_license_email(user_email, license_key, plan):
    """Send license key via email"""
    import smtplib
    from email.mime.text import MIMEText
    
    subject = f"Your {plan.upper()} License Key - Family Game Store Bot"
    body = f"""
    Thank you for purchasing {plan.upper()} plan!
    
    Your License Key: {license_key}
    
    How to activate:
    1. Invite the bot to your server
    2. Use command: !activate {license_key}
    3. Enjoy premium features!
    
    Need help? Contact support@familygamestore.com
    """
    
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = os.getenv('SMTP_USER')
        msg['To'] = user_email
        
        server = smtplib.SMTP(os.getenv('SMTP_HOST'), int(os.getenv('SMTP_PORT')))
        server.starttls()
        server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Email error: {e}")

# ====================================================================================================
# ADMIN ROUTES
# ====================================================================================================

@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    licenses = LicenseKey.query.all()
    transactions = PaymentTransaction.query.all()
    servers = Server.query.all()
    
    return render_template('admin.html', 
                          users=users, 
                          licenses=licenses, 
                          transactions=transactions,
                          servers=servers)

@app.route('/api/admin/generate-license', methods=['POST'])
@login_required
def admin_generate_license():
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.json
    plan = data.get('plan', 'premium')
    duration = data.get('duration', 30)
    
    license_key = secrets.token_urlsafe(32)
    
    new_license = LicenseKey(
        key=license_key,
        plan=plan,
        duration_days=duration,
        created_by=current_user.id
    )
    
    db.session.add(new_license)
    db.session.commit()
    
    return jsonify({'success': True, 'license_key': license_key})

@app.route('/api/admin/user/<int:user_id>', methods=['DELETE'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'success': True})

# ====================================================================================================
# TEMPLATE CONTEXT PROCESSOR
# ====================================================================================================

@app.context_processor
def utility_processor():
    return {
        'now': datetime.utcnow(),
        'PLANS': PLANS
    }

# ====================================================================================================
# RUN APP
# ====================================================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create admin account if not exists
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
        
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin = User(
                username='admin',
                email=admin_email,
                is_admin=True
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            print(f"Admin account created: {admin_email}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)