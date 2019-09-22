# from app import app
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class inventory(db.Model):
	grp_id 			= db.Column(db.Integer, primary_key=True)
	shelved_stock   = db.Column(db.String(60), primary_key=True)
	back_stock		= db.Column(db.String(30), primary_key=True)
	cart_stock		= db.Column(db.Integer)
	exp_date		= db.Column(db.)
