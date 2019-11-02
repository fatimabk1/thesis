from sqlalchemy import Column, Integer, ForeignKey, String, Float, DateTime
from sqlalchemy.orm import relationship
from base import Session, Engine, Base

class inventory(Base):
	__tablename__   = "inventory"

	grp_id 			= Column(Integer, ForeignKey("product.grp_id"), ForeignKey("price.grp_id"), primary_key=True)
	shelved_stock   = Column(Integer)
	back_stock		= Column(Integer)
	cart_stock		= Column(Integer)
	exp_date		= Column(DateTime, primary_key=True)

	def __repr__(self):
		return "<Inventory(id='{}', shelved='{}', back={}, cart={}, exp={})>"\
		.format(self.grp_id, self.shelved_stock, self.back_stock, self.cart_stock, self.exp_date)

class product(Base):
	__tablename__   = "product"

	grp_id 			= Column(Integer, primary_key=True)
	brand			= Column(String(200))
	name 			= Column(String(600))
	lot_price		= Column(Float)
	lot_size		= Column(Integer)
	category		= Column(Integer, ForeignKey("category.cat_id"))

	# relationships
	stock = relationship("inventory")
	price = relationship ("price")

	def __repr__(self):
		return "<Product(id='{}', brand='{}', name={}, lot_price={}, lot_size={}, category={})>"\
			.format(self.grp_id, self.brand, self.name, self.lot_price, self.lot_size, self.category)

class category(Base):
	__tablename__   = "category"
	
	cat_id			= Column(Integer, ForeignKey("product.category"), primary_key=True)
	category		= Column(String(50))
	coefficient		= Column(Float)

	def __repr__(self):
		return "<Product(id='{}', category='{}', coefficient={})>"\
			.format(self.cat_id, self.category, self.coefficient)

class price(Base):
	__tablename__   = "price"
	
	grp_id			= Column(Integer, ForeignKey("inventory.grp_id"), ForeignKey("product.grp_id"), primary_key=True)
	price 			= Column(Float)
	start_date		= Column(DateTime)
	end_date		= Column(DateTime)
	qty_max			= Column(Integer)
	# qty_max refers to max qty per person stipulated during a sale

	def __repr__(self):
		return "<Price(product id='{}', price='{}', start={}, end={}, qty_max={})>"\
			.format(self.grp_id, self.price, self.start_date, self.end_date, self.qty_max)

class revenue(Base):
	__tablename__   = "revenue"
	
	rev_id			= Column(Integer, primary_key=True)
	stamp		= Column(DateTime)
	value			= Column(Float)

	def __repr__(self):
		return "<Revenue(id='{}', timestamp='{}', value={})>"\
			.format(self.rev_id, self.stamp, self.value)

class cost(Base):
	__tablename__   = "cost"
	
	cost_id			= Column(Integer, primary_key=True)
	stamp	 		= Column(DateTime)
	value			= Column(Float)
	ctype			= Column(String(30))
	# ctype refers to cost type: labor, stock, or overhead

	def __repr__(self):
		return "<Cost(id='{}', timestamp='{}', value={}, cost type={})>"\
			.format(self.cost_id, self.stamp, self.value, self.ctype)

class employee(Base):
	__tablename__   = "employee"
	
	emp_id			= Column(Integer, primary_key=True)
	role_id 		= Column(Integer, ForeignKey("role.role_id"))

	def __repr__(self):
		return "<Employee(id='{}', role='{}')>"\
			.format(self.emp_id, self.role_id)

class role(Base):
	__tablename__   = "role"
	
	role_id 		= Column(Integer, ForeignKey("employee.role_id"), primary_key=True)
	role 			= Column(String(100))
	hr_salary		= Column(Float)
	max_hrs			= Column(Integer)
	# max_hrs refers to max hours an employee can work per week

	def __repr__(self):
		return "<Role(id='{}', role='{}', wage={}, max_hrs={})>"\
			.format(self.role_id, self.role, self.hr_salary, self.max_hrs)


