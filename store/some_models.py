from SQLAlchemy import Column, Integer, ForeignKey, String, Float, DateTime
from sqlalchemy.orm import relationship
from base import Base



class Revenue(Base):
    __tablename__   = "revenue"
    
    rev_id          = Column(Integer, primary_key=True)
    stamp           = Column(DateTime)
    value           = Column(Float)

    def __repr__(self):
        return "<Revenue(id='{}', timestamp='{}', value={})>"\
            .format(self.rev_id, self.stamp, self.value)

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











