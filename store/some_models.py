from SQLAlchemy import Column, Integer, ForeignKey, String, Float, DateTime
from sqlalchemy.orm import relationship
from base import Base

class Category(Base):
    __tablename__   = "category"
    
    cat_id          = Column(Integer, ForeignKey("product.category"), primary_key=True)
    category        = Column(String(50))
    coefficient     = Column(Float)

    def __repr__(self):
        return "<Product(id='{}', category='{}', coefficient={})>"\
            .format(self.cat_id, self.category, self.coefficient)

class Price(Base):
    __tablename__   = "price"
    
    grp_id          = Column(Integer, ForeignKey("inventory.grp_id"), ForeignKey("product.grp_id"), primary_key=True)
    price           = Column(Float)
    start_date      = Column(DateTime)
    end_date        = Column(DateTime)
    qty_max         = Column(Integer)
    # qty_max refers to max qty per person stipulated during a sale

    def __repr__(self):
        return "<Price(product id='{}', price='{}', start={}, end={}, qty_max={})>"\
            .format(self.grp_id, self.price, self.start_date, self.end_date, self.qty_max)

class Revenue(Base):
    __tablename__   = "revenue"
    
    rev_id          = Column(Integer, primary_key=True)
    stamp           = Column(DateTime)
    value           = Column(Float)

    def __repr__(self):
        return "<Revenue(id='{}', timestamp='{}', value={})>"\
            .format(self.rev_id, self.stamp, self.value)

class Cost(Base):
    __tablename__   = "cost"
    
    cost_id         = Column(Integer, primary_key=True)
    stamp           = Column(DateTime)
    value           = Column(Float)
    ctype           = Column(String(30))
    # ctype refers to cost type: labor, stock, or overhead

    def __repr__(self):
        return "<Cost(id='{}', timestamp='{}', value={}, cost type={})>"\
            .format(self.cost_id, self.stamp, self.value, self.ctype)

class Employee(Base):
    __tablename__   = "employee"
    
    emp_id          = Column(Integer, primary_key=True)
    role_id         = Column(Integer, ForeignKey("role.role_id"))

    def __repr__(self):
        return "<Employee(id='{}', role='{}')>"\
            .format(self.emp_id, self.role_id)

class Role(Base):
    __tablename__   = "role"
    
    role_id         = Column(Integer, ForeignKey("employee.role_id"), primary_key=True)
    role            = Column(String(100))
    hr_salary       = Column(Float)
    max_hrs         = Column(Integer)
    # max_hrs refers to max hours an employee can work per week

    def __repr__(self):
        return "<Role(id='{}', role='{}', wage={}, max_hrs={})>"\
            .format(self.role_id, self.role, self.hr_salary, self.max_hrs)

class Queuetime(Base):
    __tablename__   = "queuetime"
    
    qt_id           = Column(Integer, primary_key=True)
    queue_num       = Column(Integer)
    stamp           = Column(DateTime)
    q_time          = Column(Integer)
    total_qs        = Column(Integer)

    def __repr__(self):
        return "<queueTtme(id='{}', queue_num='{}', stamp ='{}', q_time='{}', total_qs='{}')>"\
            .format(self.qt_id, self.queue_num, self.stamp, self.q_time, self.total_qs)











