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
    RESTOCK = 1
    TOSS = 2
    UNLOAD = 3
    IDLE = 4
    NON_CASHIER = 5


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
    action = Column(Integer, default=Action.IDLE)
    tasks = Column(JSON, default=None)
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
                      self.hourly_wage, self.time_worked) +
              "\n\ttasks={}".format(self.tasks))

    # def do_tasks(self, session=None):
    #     assert(self.tasks is not None)

    #     GRP = 0
    #     QUANTITY = 1
    #     ACTION = 2
    #     emp_q = None

    #     for i, tpl in enumerate(self.tasks):
    #         if tpl[ACTION] == Action.UNLOAD:
    #             emp_q = self.unload_speed
    #         else:
    #             emp_q = self.stock_speed

    #         # execute task
    #         q = 0
    #         if tpl[ACTION] == "RESTOCK":
    #             q, emp_q = Inventory.restock(tpl[GRP], tpl[QUANTITY], emp_q, session)
    #             print("\tRESTOCK: q = {}, emp_q = {}".format(q, emp_q))
    #         elif tpl[ACTION] == "TOSS":
    #             q, emp_q = Inventory.toss(tpl[GRP], tpl[QUANTITY], emp_q, session)
    #             print("\tTOSS: q = {}, emp_q = {}".format(q, emp_q))
    #         elif tpl[ACTION] == "UNLOAD":
    #             emp_q = self.unload_speed
    #             q, emp_q = Inventory.unload(tpl[GRP], tpl[QUANTITY], emp_q, session)
    #             print("\tUNLOAD: q = {}, emp_q = {}".format(q, emp_q))
    #         else:
    #             print("tpl[ACTION] = ", tpl[ACTION])
    #             exit(2)

    #         # update task status
    #         t = (tpl[GRP], q, tpl[ACTION])
    #         self.tasks[i] = t
    #         # prev = curr

    #         if emp_q == 0:
    #             break
    #     session.commit()
    #     ret = self.tasks
    #     self.tasks = None
    #     return ret

    def set_tasks(self, tasks):
        self.tasks = tasks
        self.action = Action.NON_CASHIER

    def get_tasks(self):
        return self.tasks

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
def create_employee(session=None):
    emp = ModelEmployee()
    session.add(emp)
    session.commit()

    day = Day.SUNDAY
    for i in range(7):
        s = ModelSchedule(
            employee_id=emp.id,
            day=day,
            shift=None
        )
        session.add(s)
        day += 1
    session.commit()


# assigns employee to CASHIER action & lane;
# called by a lane object
@provide_session
def request_employee(lid, session=None):
    emps = session.query(ModelEmployee)\
        .filter(ModelEmployee.action != Action.CASHIER)\
        .filter(ModelEmployee.shift == Const.CURRENT_SHIFT).all()
    if emps:
        e = emps.pop()
        e.action = Action.CASHIER
        e.tasks = None
        e.lane = lid
        session.commit()
        return e.id, e.checkout_speed
    else:
        sys.exit(
            "request_employee() Fatal: No available employees with shift {}"
            .format(Const.CURRENT_SHIFT))


# assign employee a new action & removes lane
@provide_session
def return_employee(eid, session=None):
    e = session.query(ModelEmployee)\
        .filter(ModelEmployee.id == eid).one()
    e.action = Action.IDLE
    e.lane = None
    session.commit()


# returns true for if employee has a CASHIER action and lane lid
@provide_session
def valid_cashier(eid, lid, session=None):
    emp = session.query(ModelEmployee)\
        .filter(ModelEmployee.id == eid).one()
    if emp.action == Action.CASHIER and emp.lane == lid:
        return True
    else:
        return False


# sets schedule for all employees, each works 6 days a week
def make_week_schedule(session=None):
    employees = session.query(ModelEmployee).all()
    count = len(employees)
    off_count = floor(count / 7)
    morning_count = round((count - off_count) / 2)
    evening_count = count - off_count - morning_count

    schedule_off = []
    day = Day.SUNDAY
    for i in range(7):
        oc = off_count
        mc = morning_count
        ec = evening_count
        for index, emp in enumerate(employees):
            schedule = session.query(ModelSchedule)\
                .filter(ModelSchedule.employee_id == emp.id)\
                .filter(ModelSchedule.day == day).one()

            # fill quota of OFF employees for today
            if oc != 0 and emp.id not in schedule_off:
                schedule.shift = Shift.OFF
                schedule_off.append(emp.id)
                oc -= 1

            else:
                if mc != 0:
                    schedule.shift = Shift.MORNING
                    mc -= 1
                elif ec != 0:
                    schedule.shift = Shift.EVENING
                    ec -= 1
        day += 1

    session.commit()


# set all employee's shifts for that day according to schedule
def set_day_schedule(day, session=None):
    employees = session.query(ModelEmployee).all()
    for emp in employees:
        emp.shift = session.query(ModelSchedule)\
            .filter(ModelSchedule.employee_id == emp.id)\
            .filter(ModelSchedule.day == day).one().shift
    session.commit()


def print_active_employees(session=None):
    print("\t--- ACTIVE EMPLOYEES --- ")
    emps = session.query(ModelEmployee)\
        .filter(ModelEmployee.shift == Const.CURRENT_SHIFT)\
        .filter(ModelEmployee.action != Action.IDLE)\
        .order_by(ModelEmployee.action).all()
    for e in emps:
        e.print()
