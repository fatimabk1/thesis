from models.Inventory import ModelInventory
from sqlalchemy import Column, Integer, Date, distinct, select, func, JSON
import sys
import random
from datetime import timedelta, date
from tabulate import tabulate
from math import floor
from enum import IntEnum
from models import Base, provide_session, ModelCost, ModelProduct, Const, Shift
from models import Inventory
from models.Constants import Day


# a specific job an employee is doing
class Action(IntEnum):
    CASHIER = 0
    OTHER = 1
    OFF = 2


class ModelSchedule(Base):
    __tablename__ = "tbl_schedule"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer)
    day = Column(Integer)
    shift = Column(Integer)

    def repr_list(self):
        shift = None
        if self.shift == Shift.MORNING:
            shift = "MORNING"
        elif self.shift == Shift.EVENING:
            shift = "EVENING"
        else:
            shift = "OFF"

        day = None
        if self.day == Day.SUNDAY:
            day = "SUNDAY"
        elif self.day == Day.MONDAY:
            day = "MONDAY"
        elif self.day == Day.TUESDAY:
            day = "TUESDAY"
        elif self.day == Day.WEDNESDAY:
            day = "WEDNESDAY"
        elif self.day == Day.THURSDAY:
            day = "THURSDAY"
        elif self.day == Day.FRIDAY:
            day = "FRIDAY"
        elif self.day == Day.SATURDAY:
            day = "SATURDAY"

        return [self.id,
                self.employee_id,
                day,
                shift]


def print_employee_week_schedule(eid, session=None):
    table = []
    week = session.query(ModelSchedule)\
        .filter(ModelSchedule.employee_id == eid).all()
    headers = ["id", "eid", "day", "shift"]
    for day in week:
        table.append(day.__repr__())
    print(tabulate(table, headers=headers))


def print_full_schedule(session=None):
    table = []
    schedule = session.query(ModelSchedule)\
        .order_by(ModelSchedule.employee_id)\
        .order_by(ModelSchedule.day).all()
    for s in schedule:
        table.append(s.repr_list())
    headers = ["id", "eid", "day", "shift"]
    print(tabulate(table, headers=headers))


def checkout_speed():
    return random.randint(Const.CHECKOUT_MIN, Const.CHECKOUT_MAX)


def stock_speed():
    return random.randint(Const.STOCK_MIN, Const.STOCK_MAX)


def unload_speed():
    return random.randint(Const.UNLOAD_MIN, Const.UNLOAD_MAX)


def hourly_wage():
    return float(random.randint(Const.WAGE_MIN, Const.WAGE_MAX))


class ModelEmployee(Base):
    __tablename__ = "tbl_employee"

    id = Column(Integer, primary_key=True)
    shift = Column(Integer, default=None)
    group = Column(Integer, default=None)
    action = Column(Integer, default=Action.OTHER)
    lane = Column(Integer, default=None)
    checkout_speed = Column(Integer, default=checkout_speed)  # items per min
    stock_speed = Column(Integer, default=stock_speed)  # items per min
    unload_speed = Column(Integer, default=unload_speed)  # lots per min
    hourly_wage = Column(Integer, default=hourly_wage)
    time_worked = Column(Integer, default=0)  # minute

    def print(self):
        shift = None
        if self.shift == Shift.MORNING:
            shift = "MORNING"
        elif self.shift == Shift.EVENING:
            shift = "EVENING"
        else:
            shift = "OFF"

        print("<Employee_{}: shift={}, action={}, lane={}, checkout_speed={}"
              .format(self.id, shift, self.action,
                      self.lane, self.checkout_speed) +
              ", stock_speed={}, unload_speed={}, wage={:.2f}, time={}>"
              .format(self.stock_speed, self.unload_speed,
                      self.hourly_wage, self.time_worked))

    def get_speed(self, task):
        if task == Const.TASK_CASHIER:
            return self.checkout_speed
        elif task == Const.TASK_RESTOCK or task == Const.TASK_TOSS:
            return self.stock_speed
        elif task == Const.TASK_UNLOAD:
            return self.unload_speed
        else:
            print("ERROR: Employee.get_speed() given an invalid task")
            exit(1)

    def set_cashier(self, lid):
        self.lane = lid
        self.action = Action.CASHIER

    def remove_cashier(self):
        self.lane = None
        self.action = Action.OTHER

    def get_schedule(self, day, session):
        schedule = session.query(ModelSchedule)\
            .filter(ModelSchedule.employee_id == self.id)\
            .filter(ModelSchedule.day == day).one_or_none()
        if schedule:
            return schedule[0].shift
        else:
            return None

    def calculate_wages(self):
        hours = self.time_worked / 60
        minutes = self.time_worked % 60
        wage = round(self.hourly_wage * hours +
                     round(self.hourly_wage * (minutes / 60), 2), 2)
        return wage

    def increment_time_worked(self):
        self.time_worked += 1


# ---------------------------------------------------- external functions
def create_employees(n, session=None):
    assert(n % 7 == 0)
    group_size = n / 7
    group = 0
    # print("group = 0")
    for i in range(n):
        if i != 0 and i % group_size == 0:
            group += 1
            # print("group = ", group)
        emp = ModelEmployee()
        emp.group = group
        session.add(emp)


def pull_employees(session):
    emps = session.query(ModelEmployee).all()
    assert(emps is not None)
    # for emp in emps:
    #     emp.print()

    employees = {"available": {}, "cashiers": {}, "unavailable": {}}
    for emp in emps:
        if emp.shift == Const.CURRENT_SHIFT:
            if emp.action == Action.CASHIER:
                employees["cashiers"][emp.id] = emp
            else:
                employees["available"][emp.id] = emp
        else:
            employees["unavailable"][emp.id] = emp

    # print("AVAILABLE EMPLOYEES:")
    # s = ""
    # for eid in employees["available"]:
    #     s = s + str(eid) + ", "
    # print(s)
    # print("CASHIER EMPLOYEES:")
    # s = ""
    # for eid in employees["cashiers"]:
    #     s = s + str(eid) + ", "
    # print(s)
    # print("UNAVAILABLE EMPLOYEES:")
    # s = ""
    # for eid in employees["unavailable"]:
    #     s = s + str(eid) + ", "
    # print(s)
    # print("\n^pull employees")
    return employees


def shift_change(emp_group):
    print("AVAILABLE EMPLOYEES:", list(emp_group["available"].keys()).sort())
    print("CAHSIER EMPLOYEES:", list(emp_group["cashiers"].keys()).sort())
    print("UNAVAILABLE EMPLOYEES:", list(emp_group["unavailable"].keys()).sort())
    print("---")

    employees = (list(emp_group["available"].values())
                 + list(emp_group["cashiers"].values())
                 + list(emp_group["unavailable"].values()))
    emp_group["available"] = {}
    emp_group["cashiers"] = {}
    emp_group["unavailable"] = {}
    for emp in employees:
        if emp.shift != Const.CURRENT_SHIFT:
            emp_group["unavailable"][emp.id] = emp
        else:
            emp_group["available"][emp.id] = emp

    print("AVAILABLE EMPLOYEES:", list(emp_group["available"].keys()).sort())
    print("CAHSIER EMPLOYEES:", list(emp_group["cashiers"].keys()).sort())
    print("UNAVAILABLE EMPLOYEES:", list(emp_group["unavailable"].keys()).sort())
    print("\n")
    print("\n^Employee.shift_change()")


# set all employee's shifts for that day according to schedule
def set_day_schedule(schedule, session):
    print(schedule)
    employees = session.query(ModelEmployee).all()
    assert(employees is not None)
    for emp in employees:
        print("\temp{}.group = {}".format(emp.id, emp.group))
        emp.shift = schedule[emp.group]
    session.commit()


def print_active_employees(session):
    print("\t--- ACTIVE EMPLOYEES --- ")
    emps = session.query(ModelEmployee)\
        .filter(ModelEmployee.shift == Const.CURRENT_SHIFT)\
        .filter(ModelEmployee.action != Action.OTHER)\
        .order_by(ModelEmployee.action).all()
    for e in emps:
        e.print()
