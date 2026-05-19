#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DATABASE MODELS FOR WEB DASHBOARD
==================================
SQLAlchemy models for User, Server, License management
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()

# ====================================================================================================
# USER MODEL
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
    
    # API Key for bot integration
    api_key = db.Column(db.String(100), unique=True, nullable=True)
    
    # Relationships
    servers = db.relationship('Server', backref='owner', lazy=True)
    licenses = db.relationship('LicenseKey', backref='creator', lazy=True)
    transactions = db.relationship('PaymentTransaction', backref='user', lazy=True)
    
    def is_premium(self):
        """Check if user has active premium subscription"""
        return self.subscription_plan in ['premium', 'enterprise'] and \
               self.subscription_expires and \
               self.subscription_expires > datetime.utcnow()
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'subscription_plan': self.subscription_plan,
            'subscription_expires': self.subscription_expires.isoformat() if self.subscription_expires else None,
            'created_at': self.created_at.isoformat(),
            'server_count': len(self.servers)
        }

# ====================================================================================================
# SERVER MODEL
# ====================================================================================================

class Server(db.Model):
    __tablename__ = 'servers'
    
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.String(50), unique=True, nullable=False)
    server_name = db.Column(db.String(200), nullable=False)
    server_icon = db.Column(db.String(500), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # License information
    license_key = db.Column(db.String(100), unique=True, nullable=True)
    license_expires = db.Column(db.DateTime, nullable=True)
    features = db.Column(db.Text, default='{}')
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Statistics
    member_count = db.Column(db.Integer, default=0)
    message_count = db.Column(db.Integer, default=0)
    command_count = db.Column(db.Integer, default=0)
    
    def get_features(self):
        """Get features as dictionary"""
        return json.loads(self.features) if self.features else {}
    
    def set_features(self, features_dict):
        """Set features from dictionary"""
        self.features = json.dumps(features_dict)
    
    def is_premium(self):
        """Check if server has active premium license"""
        return self.license_key and self.license_expires and self.license_expires > datetime.utcnow()
    
    def to_dict(self):
        return {
            'id': self.id,
            'server_id': self.server_id,
            'server_name': self.server_name,
            'server_icon': self.server_icon,
            'owner_id': self.owner_id,
            'license_key': self.license_key,
            'license_expires': self.license_expires.isoformat() if self.license_expires else None,
            'is_active': self.is_active,
            'joined_at': self.joined_at.isoformat(),
            'member_count': self.member_count,
            'message_count': self.message_count,
            'is_premium': self.is_premium()
        }

# ====================================================================================================
# LICENSE KEY MODEL
# ====================================================================================================

class LicenseKey(db.Model):
    __tablename__ = 'license_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    plan = db.Column(db.String(50), nullable=False)  # premium, enterprise
    duration_days = db.Column(db.Integer, default=30)
    
    # Creator info
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Usage info
    used_by = db.Column(db.Integer, db.ForeignKey('servers.id'), nullable=True)
    used_at = db.Column(db.DateTime, nullable=True)
    is_used = db.Column(db.Boolean, default=False)
    
    # Expiration
    expires_at = db.Column(db.DateTime, nullable=True)
    
    def is_valid(self):
        """Check if license is valid and not expired"""
        if self.is_used and self.expires_at:
            return self.expires_at > datetime.utcnow()
        return not self.is_used
    
    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'plan': self.plan,
            'duration_days': self.duration_days,
            'created_at': self.created_at.isoformat(),
            'is_used': self.is_used,
            'used_at': self.used_at.isoformat() if self.used_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_valid': self.is_valid()
        }

# ====================================================================================================
# PAYMENT TRANSACTION MODEL
# ====================================================================================================

class PaymentTransaction(db.Model):
    __tablename__ = 'payment_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Payment details
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    plan = db.Column(db.String(50), nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    
    # Transaction info
    transaction_id = db.Column(db.String(100), unique=True)
    payment_method = db.Column(db.String(50))
    payment_details = db.Column(db.Text, nullable=True)
    
    # Status
    status = db.Column(db.String(50), default='pending')  # pending, success, failed, expired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)
    expired_at = db.Column(db.DateTime, nullable=True)
    
    def is_expired(self):
        """Check if transaction has expired"""
        return self.expired_at and self.expired_at < datetime.utcnow()
    
    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'currency': self.currency,
            'plan': self.plan,
            'duration_days': self.duration_days,
            'transaction_id': self.transaction_id,
            'payment_method': self.payment_method,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'paid_at': self.paid_at.isoformat() if self.paid_at else None
        }

# ====================================================================================================
# USAGE STATISTICS MODEL
# ====================================================================================================

class BotUsage(db.Model):
    __tablename__ = 'bot_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.String(50), nullable=False)
    command_name = db.Column(db.String(100))
    user_id = db.Column(db.String(50))
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'server_id': self.server_id,
            'command_name': self.command_name,
            'user_id': self.user_id,
            'recorded_at': self.recorded_at.isoformat()
        }

# ====================================================================================================
# INITIALIZATION
# ====================================================================================================

def init_db(app):
    """Initialize database with app context"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        
        # Create default admin user if not exists
        from werkzeug.security import generate_password_hash
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123'),
                is_admin=True,
                api_key='admin_api_key_12345'
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: admin@example.com / admin123")