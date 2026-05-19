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
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://botuser:botpassword@postgres:5432/botdb')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'

API_URL = os.getenv('API_URL', 'http://api:8000')

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
    
    subscription_plan = db.Column(db.String(50), default='free')
    subscription_expires = db.Column(db.DateTime, nullable=True)
    api_key = db.Column(db.String(100), unique=True, nullable=True)
    
    servers = db.relationship('Server', backref='owner', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_premium(self):
        return self.subscription_plan in ['premium', 'enterprise'] and \
               self.subscription_expires and self.subscription_expires > datetime.utcnow()

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
    member_count = db.Column(db.Integer, default=0)
    message_count = db.Column(db.Integer, default=0)

class LicenseKey(db.Model):
    __tablename__ = 'license_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    plan = db.Column(db.String(50), nullable=False)
    duration_days = db.Column(db.Integer, default=30)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_by = db.Column(db.Integer, db.ForeignKey('servers.id'), nullable=True)
    used_at = db.Column(db.DateTime, nullable=True)
    is_used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=True)

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
            'Invite Tracker Basic',
            'Leveling System Basic',
            '1 Giveaway/month',
            'Up to 100 members'
        ]
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
            '✅ Unlimited Giveaways',
            '✅ Custom Commands',
            '✅ Welcome Messages',
            '✅ Level Roles',
            '✅ Export Statistics',
            '✅ Priority Support'
        ]
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
            '✅ Multi-Server License'
        ]
    }
}

# ====================================================================================================
# AUTHENTICATION
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
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
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
# DASHBOARD
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
    return render_template('dashboard_billing.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html', plans=PLANS)

@app.route('/checkout/<plan_name>')
@login_required
def checkout(plan_name):
    if plan_name not in PLANS or plan_name == 'free':
        flash('Invalid plan selected', 'danger')
        return redirect(url_for('pricing'))
    
    plan = PLANS[plan_name]
    return render_template('checkout.html', plan=plan)

# ====================================================================================================
# API ROUTES
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
    
    # Update user subscription
    current_user.subscription_plan = license.plan
    current_user.subscription_expires = license.expires_at
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'plan': license.plan,
        'expires': license.expires_at.isoformat()
    })

@app.route('/api/servers')
@login_required
def get_servers():
    servers = Server.query.filter_by(owner_id=current_user.id).all()
    return jsonify([{
        'id': s.id,
        'server_id': s.server_id,
        'name': s.server_name,
        'icon': s.server_icon,
        'license_key': s.license_key,
        'expires': s.license_expires.isoformat() if s.license_expires else None,
        'member_count': s.member_count,
        'message_count': s.message_count
    } for s in servers])

@app.route('/api/stats')
@login_required
def get_stats():
    servers = Server.query.filter_by(owner_id=current_user.id).all()
    total_servers = len(servers)
    premium_servers = len([s for s in servers if s.license_key])
    
    return jsonify({
        'total_servers': total_servers,
        'premium_servers': premium_servers,
        'total_messages': sum(s.message_count for s in servers),
        'total_users': sum(s.member_count for s in servers)
    })

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
    servers = Server.query.all()
    
    return render_template('admin.html', users=users, licenses=licenses, servers=servers)

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
                is_admin=True,
                api_key='admin_api_key_12345'
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            print(f"✅ Admin account created: {admin_email} / {admin_password}")
    
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
