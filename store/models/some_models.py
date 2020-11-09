from sqlalchemy import Column, Integer, Float, DateTime
from models import Base


class ModelRevenue(Base):
    __tablename__ = "tbl_revenue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stamp = Column(DateTime)
    value = Column(Float)

    def __repr__(self):
        return ["id",
                "stamp",
                "value"]

    def print(self):
        print("<Revenue_{}: timestamp='{}', value={}>"
              .format(self.id, self.stamp, self.value))


class ModelQtime(Base):
    __tablename__ = "tbl_qtime"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lane = Column(Integer)
    stamp = Column(DateTime)
    time = Column(Integer)

    def __repr__(self):
        return ["id",
                "lane",
                "stamp",
                "time"]

    def print(self):
        print("<Qtime_{}: queue_num={}, stamp ={}, time={}>"
              .format(self.id, self.lane, self.stamp, self.time))

# class Employee(Base):
#     __tablename__   = "employee"

#     emp_id          = Column(Integer, primary_key=True)
#     role_id         = Column(Integer, ForeignKey("role.role_id"))

#     def __repr__(self):
#         return "<Employee(id='{}', role='{}')>"\
#             .format(self.emp_id, self.role_id)

# class Role(Base):
#     __tablename__   = "role"

#     role_id         = Column(Integer, ForeignKey("employee.role_id"),
#                              primary_key=True)
#     role            = Column(String(100))
#     hr_salary       = Column(Float)
#     max_hrs         = Column(Integer)
#     # max_hrs refers to max hours an employee can work per week

#     def __repr__(self):
#         return "<Role(id='{}', role='{}', wage={}, max_hrs={})>"\
#             .format(self.role_id, self.role, self.hr_salary, self.max_hrs)
