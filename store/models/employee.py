import enum
from re import M
from sqlalchemy import Column, Integer, Date, distinct, select
import sys
import random
from datetime import timedelta, date
from tabulate import tabulate
from math import floor
from enum import IntEnum
from models import Base, provide_session, ModelCost, ModelProduct, const
from models import inventory


# a specific job an employee is doing
class Role(IntEnum):
    CASHIER = 0
    RESTOCK = 1
    TOSS = 2
    UNLOAD = 3
    IDLE = 4


# specific times an employee works
class Shift(IntEnum):
    MORNING = 0
    EVENING = 1
    OFF = 2


class Day(IntEnum):
    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THRUSDAY = 4
    FRIDAY = 5
    SATURDAY = 6


class ModelSchedule(Base):
    __tablename__ = "tbl_schedule"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer)
    day = Column(Integer)
    shift = Column(Integer)


def checkout_speed():
    return random.randint(const.CHECKOUT_MIN, const.CHECKOUT_MAX)


def stock_speed():
    return random.randint(const.STOCK_MIN, const.STOCK_MAX)


def unload_speed():
    return random.randint(const.UNLOAD_MIN, const.UNLOAD_MAX)


class ModelEmployee(Base):
    __tablename__ = "tbl_employee"

    id = Column(Integer, primary_key=True)
    shift = Column(Integer)
    role = Column(Integer)
    task = Column(Integer)
    lane = Column(Integer)
    checkout_speed = Column(Integer, default=checkout_speed)  # items-cashier
    stock_speed = Column(Integer, default=stock_speed)  # items-restock, unload
    unload_speed = Column(Integer, default=unload_speed)  # lots-unload
    hourly_wage = Column(Integer)
    time_worked = Column(Integer, default=0)  # minutes

    def print(self):
        print("<Employee_{}: shift={}, role={}, task={}, lane={}, checkout={}"
              .format(self.id, self.shift, self.role,
                      self.task, self.lane, self.checkout_speed),
              "stock={}, unload={}, wage={}, time={}>"
              .format(self.stock_speed, self.unload_speed,
                      self.hourly_wage, self.time_worked))

    def do_task(self, session=None):
        if self.role == Role.UNLOAD:
            inventory.unload(self.task, session)
        elif self.role == Role.TOSS:
            inventory.toss(self.task, self.stock_speed, session)
        elif self.role == Role.RESTOCK:
            inventory.restock(self.task, self.stock_speed, session)
        else:
            pass
        return

    def set_task(self, grp):
        self.task = grp

    def get_task(self):
        return self.task

    def set_role(self, role):
        self.role = role

    def get_role(self):
        return self.role

    def set_role_and_task(self, role, task):
        self.role = role
        self.task = task

    def get_checkout_speed(self):
        return self.checkout_speed

    def get_stock_speed(self):
        return self.stock_speed

    def get_schedule(self, day, session):
        schedule = session.query(ModelSchedule)\
            .filter(ModelSchedule.employee_id == self.id)\
            .filter(ModelSchedule.day == day).one_or_none()
        if schedule:
            return schedule[0].shift
        else:
            return None

    def calculate_wage(self):
        hours = self.time_worked / 60
        minutes = self.time_worked % 60
        wage = round(self.hourly_wage * hours +
                     round(self.hourly_wage * (minutes / 60), 2), 2)
        return wage


# ---------------------------------------------------- internal functions
# unload > toss > restock > idle
def cmp_before(a, b):
    if a.role == b.role:
        return a
    elif a.role == Role.UNLOAD or b.role == Role.UNLOAD:
        if a.role == Role.UNLOAD:
            return a
        else:
            return b
    elif a.role == Role.TOSS or b.role == Role.TOSS:
        if a.role == Role.TOSS:
            return a
        else:
            return b
    elif a.role == Role.RESTOCK or b.role == Role.RESTOCK:
        if a.role == Role.RESTOCK:
            return a
        else:
            return b
    elif a.role == Role.IDLE or b.role == Role.IDLE:
        if a.role == Role.IDLE:
            return a
        else:
            return b
    else:
        sys.exit("ORDERING ERROR: object with Role of CASHIER")


# restock > toss > idle
def cmp_open(a, b):
    if a.role == b.role:
        return a
    elif a.role == Role.RESTOCK or b.role == Role.RESTOCK:
        if a.role == Role.RESTOCK:
            return a
        else:
            return b
    elif a.role == Role.TOSS or b.role == Role.TOSS:
        if a.role == Role.TOSS:
            return a
        else:
            return b
    elif a.role == Role.IDLE or b.role == Role.IDLE:
        if a.role == Role.IDLE:
            return a
        else:
            return b
    else:
        sys.exit("ORDERING ERROR: object with Role of CASHIER")


# toss > restock > idle
def cmp_closed(a, b):
    if a.role == b.role:
        return a
    elif a.role == Role.TOSS or b.role == Role.TOSS:
        if a.role == Role.TOSS:
            return a
        else:
            return b
    elif a.role == Role.RESTOCK or b.role == Role.RESTOCK:
        if a.role == Role.RESTOCK:
            return a
        else:
            return b
    elif a.role == Role.IDLE or b.role == Role.IDLE:
        if a.role == Role.IDLE:
            return a
        else:
            return b
    else:
        sys.exit("ORDERING ERROR: object with Role of CASHIER")


# ---------------------------------------------------- external functions
# assigns employee to CASHIER role & lane;
# called by a lane object
def get_employee(lid, session=None):
    emps = session.query(ModelEmployee)\
        .filter(ModelEmployee.role == Role.RESTOCK,
                ModelEmployee.role == Role.TOSS,
                ModelEmployee.role == Role.IDLE).all()
    if emps:
        # sort employees by task importance
        if const.store_before(const.CLOCK):
            emps.sort(cmp_before)
        elif const.store_open(const.CLOCK):
            emps.sort(cmp_open)
        else:
            emps.sort(cmp_closed)

        # choose employee doing least important task
        e = emps.pop()
        e.role = Role.CASHIER
        e.task = None
        e.lane = lid
        session.commit()
        return e.id


# assign employee a new role & removes lane
def return_employee(eid, session=None):
    e = session.query(ModelEmployee)\
        .filter(ModelEmployee.id == eid).one()
    e.role = Role.IDLE
    e.lane = None
    session.commit()


# swap out emp w/eid for another employee to CASHIER
def swap_employee(eid, lid, session=None):
    return_employee(eid, session)
    emp = get_employee(lid, session)
    return emp


# sets schedule for all employees, each works 6 days a week
def make_schedule(session=None):
    employees = session.query(ModelEmployee).all()
    count = len(employees)
    off_count = floor(count / 7)
    morning_count = round((count - off_count) / 2)
    evening_count = count - off_count - morning_count

    schedule_off = []
    day = Shift.SUNDAY
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


# set shifts for employee for day according to schedule
def set_schedule(day, session=None):
    employees = session.query(ModelEmployee).all()
    for emp in employees:
        emp.shift = session.query(ModelSchedule)\
            .filter(ModelSchedule.employee_id == emp.id)\
            .filter(ModelSchedule.day == day).one().shift
    session.commit()


# sets up all employees with a valid role & task
def prepare_employees(session=None):
    # task to do
    unload_tasks = inventory.unload_list()
    restock_tasks = inventory.restock_list()
    toss_tasks = inventory.toss_list()

    # tasks already assigned
    unload_assigned = session.query(ModelEmployee.task)\
        .filter(ModelEmployee.role == Role.UNLOAD).all()
    restock_assigned = session.query(ModelEmployee.task)\
        .filter(ModelEmployee.role == Role.RESTOCK).all()
    toss_assigned = session.query(ModelEmployee.task)\
        .filter(ModelEmployee.role == Role.TOSS).all()

    TODO = 0
    ASSIGNED = 1
    unload = [unload_tasks, unload_assigned]
    restock = [restock_tasks, restock_assigned]
    toss = [toss_tasks, toss_assigned]
    group = session.query(ModelEmployee)\
        .filter(ModelEmployee.role != Role.CASHIER).all()

    # if employee has valid role & task, remove task
    # from TODO and ASSIGNED lists
    ready = []
    for emp in group:
        r = emp.get_role()
        t = emp.get_task()
        if r == Role.UNLOAD and t in unload[TODO]:
            ready.append(emp.id)
            unload[TODO].remove(t)
            unload[ASSIGNED].remove(t)
        elif r == Role.RESTOCK and t in restock[TODO]:
            ready.append(emp.id)
            restock[TODO].remove(t)
            restock[ASSIGNED].remove(t)
        elif r == Role.TOSS and t in toss[TODO]:
            ready.append(emp.id)
            toss[TODO].remove(t)
            toss[ASSIGNED].remove(t)
        else:
            assert(r == Role.IDLE)
            pass  # IDLE

    # assign remaining TODO tasks to employees with
    # invalid tasks and/or roles
    for emp in group:
        if emp.id in ready:
            continue

        r = emp.get_role()

        # if role is still available, update employee with new task
        if r == Role.UNLOAD and unload[TODO]:  # is not empty
            emp.set_task(unload[TODO][0])
            unload[TODO].remove(unload[TODO][0])
        elif r == Role.RESTOCK and restock[TODO]:
            emp.set_task(restock[TODO][0])
            restock[TODO].remove(restock[TODO][0])
        elif r == Role.TOSS and toss[TODO]:
            emp.set_task(toss[TODO][0])
            toss[TODO].remove(toss[TODO][0])

        # if role is filled or employee is IDLE
        # assign a new role & task prioritized by time of day
        else:
            # priority: unload > toss > restock > idle
            if const.store_before(const.CLOCK):
                if unload[TODO]:
                    emp.set_role_and_task(Role.UNLOAD, unload[TODO][0])
                    unload[TODO].remove(unload[TODO][0])
                elif toss[TODO]:
                    emp.set_role_and_task(Role.TOSS, toss[TODO][0])
                    toss[TODO].remove(toss[TODO][0])
                elif restock[TODO]:
                    emp.set_role_and_task(Role.RESTOCK, restock[TODO][0])
                    restock[TODO].remove(restock[TODO][0])
                else:
                    emp.set_role_and_task(Role.IDLE, None)

            # priority: restock > toss > unload > idle
            elif const.store_open(const.CLOCK):
                if restock[TODO]:
                    emp.set_role_and_task(Role.RESTOCK, restock[TODO][0])
                    restock[TODO].remove(restock[TODO][0])
                elif toss[TODO]:
                    emp.set_role_and_task(Role.TOSS, toss[TODO][0])
                    toss[TODO].remove(toss[TODO][0])
                elif unload[TODO]:
                    emp.set_role_and_task(Role.UNLOAD, unload[TODO][0])
                    unload[TODO].remove(unload[TODO][0])
                else:
                    emp.set_role_and_task(Role.IDLE, None)

            # priority: toss > restock > unload > idle
            elif const.store_closed(const.CLOCK):
                if toss[TODO]:
                    emp.set_role_and_task(Role.TOSS, toss[TODO][0])
                    toss[TODO].remove(toss[TODO][0])
                elif restock[TODO]:
                    emp.set_role_and_task(Role.RESTOCK, restock[TODO][0])
                    restock[TODO].remove(restock[TODO][0])
                elif unload[TODO]:
                    emp.set_role_and_task(Role.UNLOAD, unload[TODO][0])
                    unload[TODO].remove(unload[TODO][0])
                else:
                    emp.set_role_and_task(Role.IDLE, None)
    session.commit()
