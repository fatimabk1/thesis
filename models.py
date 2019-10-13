# from app import app
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class inventory(db.Model):
	__tablename__   = "inventory"

	grp_id 			= db.Column(db.Integer, primary_key=True, ForeignKey("product.grp_id"), ForeignKey("price.grp_id"))
	shelved_stock   = db.Column(db.Integer)
	back_stock		= db.Column(db.Integer)
	cart_stock		= db.Column(db.Integer)
	exp_date		= db.Column(db.Integer, primary_key=True)

class product(db.Model):
	grp_id 			= db.Column(db.Integer, primary_key=True, ForeignKey("inventory.grp_id"), ForeignKey("price.grp_id"))
	brand			= db.Column(db.String(200))
	name 			= db.Column(db.String(600))
	lot_price		= db.Column(db.Float)
	lot_size		= db.Column(db.Integer)
	category		= db.Column(db.Integer, ForeignKey("category.cat_id"))

class category(db.Model):
	cat_id			= db.Column(db.Integer, primary_key, ForeignKey("product.category"))
	category		= db.Column(db.String(50))
	coefficient		= db.Column(db.Float)

class price(db.Model):
	grp_id			= db.Column(db.Integer, primary_key=True, ForeignKey("inventory.grp_id"), ForeignKey("product.grp_id"))
	price 			= db.Column(db.Float)
	start_date		= db.Column(db.DateTime)
	end_date		= db.Column(db.DateTime)
	qty_max			= db.Column(db.Integer)
	# qty_max refers to max qty per person stipulated during a sale

class revenue(db.Model):
	rev_id			= db.Column(db.Integer, primary_key=True)
	stamp		= db.Column(db.DateTime)
	value			= db.Column(db.Float)

class cost(db.Model):
	cost_id			= db.Column(db.Integer, primary_key=True)
	stamp	 		= db.Column(db.DateTime)
	value			= db.Column(db.Float)
	ctype			= db.Column(db.String(30))
	# ctype refers to cost type: labor, stock, or overhead

class employee(db.Model):
	emp_id			= db.Column(db.Integer, primary_key=True)
	role_id 		= db.Column(db.Integer, ForeignKey("role.role_id"))

class role(db.Model):
	role_id 		= db.Column(db.Integer, primary_key=True, ForeignKey("employee.role_id"))
	role 			= db.Column(db.String(100))
	hr_salary		= db.Column(db.Float)
	max_hrs			= db.Column(db.Integer)
	# max_hrs refers to max hours an employee can work per week
