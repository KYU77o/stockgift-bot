from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy with pool_pre_ping=True so that it handles
# dropped connections found in some cloud environments (like Render/Neon) gracefully.
db = SQLAlchemy(engine_options={"pool_pre_ping": True})

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    line_user_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.line_user_id}>'

class Stock(db.Model):
    __tablename__ = 'stocks'
    
    stock_id = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    gift_name = db.Column(db.String(200))
    meeting_date = db.Column(db.Date, nullable=False)
    vote_start_date = db.Column(db.Date)
    last_buy_date = db.Column(db.Date)
    gift_year = db.Column(db.Integer)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Stock {self.stock_id} {self.name}>'
