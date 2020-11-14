import enum
from models.Inventory import ModelInventory
from sqlalchemy import Column, Integer, Date, distinct, select, func
import sys
import random
from datetime import timedelta, date
from tabulate import tabulate
from math import floor
from enum import IntEnum
from models import Base, provide_session, ModelCost, ModelProduct, Const
from models import Inventory


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
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6


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
    return random.randint(const.CHECKOUT_MIN, const.CHECKOUT_MAX)


def stock_speed():
    return random.randint(const.STOCK_MIN, const.STOCK_MAX)


def unload_speed():
    return random.randint(const.UNLOAD_MIN, const.UNLOAD_MAX)


def hourly_wage():
    return float(random.randint(const.WAGE_MIN, const.WAGE_MAX))


class ModelEmployee(Base):
    __tablename__ = "tbl_employee"

    id = Column(Integer, primary_key=True)
    shift = Column(Integer, default=None)
    role = Column(Integer, default=Role.IDLE)
    task = Column(Integer, default=None)
    lane = Column(Integer, default=None)
    checkout_speed = Column(Integer, default=checkout_speed)  # items per min
    stock_speed = Column(Integer, default=stock_speed)  # items per min
    unload_speed = Column(Integer, default=unload_speed)  # lots per min
    hourly_wage = Column(Integer, default=hourly_wage)
    time_worked = Column(Integer, default=0)  # minutes

    def print(self):
        shift = None
        if self.shift == Shift.MORNING:
            shift = "MORNING"
        elif self.shift == Shift.EVENING:
            shift = "EVENING"
        else:
            shift = "OFF"

        role = None
        if self.role == Role.UNLOAD:
            role = "UNLOAD"
        elif self.role == Role.RESTOCK:
            role = "RESTOCK"
        elif self.role == Role.TOSS:
            role = "TOSS"
        elif self.role == Role.CASHIER:
            role = "CASHIER"
        elif self.role == Role.IDLE:
            role = "IDLE"

        print("<Employee_{}: shift={}, role={}, task={}, lane={}, checkout_speed={}"
              .format(self.id, shift, role, self.task,
                      self.lane, self.checkout_speed) +
              ", stock_speed={}, unload={}, wage={:.2f}, time={}>"
              .format(self.stock_speed, self.unload_speed,
                      self.hourly_wage, self.time_worked))

    def do_task(self, session=None):
        prev, curr = None, None
        if self.task is not None:
            product = session.query(ModelProduct)\
                .filter(ModelProduct.grp_id == self.task).one()

            if self.role == Role.UNLOAD:
                prev = session.query(func.sum(ModelInventory.back_stock))\
                    .filter(ModelInventory.grp_id == self.task).one()[0]
                for i in range(self.unload_speed):
                    Inventory.unload(self.task, session)
                curr = session.query(func.sum(ModelInventory.back_stock))\
                    .filter(ModelInventory.grp_id == self.task).one()[0]
                print("\tUNLOAD grp_id={}: prev={}, curr={}".format(self.task, prev, curr))
                assert(curr - prev <= product.get_lot_quantity() * self.unload_speed)
            elif self.role == Role.TOSS:
                prev = session.query(func.sum(ModelInventory.shelved_stock))\
                    .filter(ModelInventory.grp_id == self.task).one()[0]
                Inventory.toss(self.task, self.stock_speed, session)
                curr = session.query(func.sum(ModelInventory.shelved_stock))\
                    .filter(ModelInventory.grp_id == self.task).one()[0]
                print("\tTOSS {}: prev={}, curr={}".format(self.task, prev, curr))
                assert(prev - curr <= self.get_stock_speed())
            elif self.role == Role.RESTOCK:
                prev = session.query(func.sum(ModelInventory.shelved_stock))\
                    .filter(ModelInventory.grp_id == self.task).one()[0]
                Inventory.restock(self.task, self.stock_speed, session)
                curr = session.query(func.sum(ModelInventory.shelved_stock))\
                    .filter(ModelInventory.grp_id == self.task).one()[0]
                print("\tRESTOCK {}: prev={}, curr={}".format(self.task, prev, curr))
                assert(curr - prev <= self.get_stock_speed())
            else:
                sys.exit("FATAL: invalid role assigned a task")

        session.commit()

    def set_task(self, grp):
        self.task = grp

    def get_task(self):
        return self.task

    def set_role(self, role):
        self.role = role

    def get_role(self):
        return self.role

    def set_role_and_task(self, role, assignment):
        if role == Role.CASHIER:
            self.role = role
            self.lane = assignment
            self.task = None
        else:
            self.role = role
            self.task = assignment
            self.lane = None

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

    def calculate_wages(self):
        hours = self.time_worked / 60
        minutes = self.time_worked % 60
        wage = round(self.hourly_wage * hours +
                     round(self.hourly_wage * (minutes / 60), 2), 2)
        return wage

    def increment_time_worked(self):
        self.time_worked += 1


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


# assigns employee to CASHIER role & lane;
# called by a lane object
@provide_session
def get_employee(lid, shift, session=None):
    emps = session.query(ModelEmployee)\
        .filter(ModelEmployee.role != Role.CASHIER)\
        .filter(ModelEmployee.shift == shift).all()
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
@provide_session
def return_employee(eid, session=None):
    e = session.query(ModelEmployee)\
        .filter(ModelEmployee.id == eid).one()
    e.role = Role.IDLE
    e.lane = None
    session.commit()


# returns true for if employee has a CASHIER role and lane lid
def valid_cashier(eid, lid, session=None):
    emp = session.query(ModelEmployee)\
        .filter(ModelEmployee.id == eid).one()
    if emp.role == Role.CASHIER and emp.lane == lid:  # ADD A SHIFT CHECK
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


# sets up all employees with a valid role & task
def prepare_employees(shift, session=None):
    # task to do
    unload_tasks = Inventory.unload_list(session)
    restock_tasks = Inventory.restock_list(session)
    toss_tasks = Inventory.toss_list(session)

    # tasks already assigned
    unload_assigned = session.query(ModelEmployee.task)\
        .filter(ModelEmployee.role == Role.UNLOAD).all()
    restock_assigned = session.query(ModelEmployee.task)\
        .filter(ModelEmployee.role == Role.RESTOCK).all()
    toss_assigned = session.query(ModelEmployee.task)\
        .filter(ModelEmployee.role == Role.TOSS).all()

    # flatten lists
    unload_assigned = [item for sublist in unload_assigned for item in sublist]
    restock_assigned = [item for sublist in restock_assigned for item in sublist]
    toss_assigned = [item for sublist in toss_assigned for item in sublist]

    TODO = 0
    ASSIGNED = 1
    unload = [unload_tasks, unload_assigned]
    restock = [restock_tasks, restock_assigned]
    toss = [toss_tasks, toss_assigned]
    group = session.query(ModelEmployee)\
        .filter(ModelEmployee.shift == shift)\
        .filter(ModelEmployee.role != Role.CASHIER).all()

    # if employee has valid role & task, remove task
    # from TODO and ASSIGNED lists
    ready = []
    for emp in group:
        r = emp.get_role()
        t = emp.get_task()
        print("EMP {}: role = {}, task = {}".format(emp.id, r, t))
        if r == Role.UNLOAD and t in unload[TODO]:
            print("\t\tUNLOAD TODO:", unload_tasks)
            print("\t\tUNLOAD ASSIGNED:", unload_assigned)
            ready.append(emp.id)
            unload[TODO].remove(t)
            unload[ASSIGNED].remove(t)
        elif r == Role.RESTOCK and t in restock[TODO]:
            print("\t\tRESTOCK TODO:", restock_tasks)
            print("\t\tRESTOCK ASSIGNED:", restock_assigned)
            ready.append(emp.id)
            restock[TODO].remove(t)
            restock[ASSIGNED].remove(t)
        elif r == Role.TOSS and t in toss[TODO]:
            print("\t\tTOSS TODO:", toss_tasks)
            print("\t\tTOSS ASSIGNED:", toss_assigned)
            ready.append(emp.id)
            toss[TODO].remove(t)
            toss[ASSIGNED].remove(t)
        else:
            pass  # IDLE or None

    # assign remaining TODO tasks to employees with
    # invalid tasks and/or roles
    for emp in group:
        if emp.id in ready:
            continue

        r = emp.get_role()

        # if role is still available, update employee with new task
        if r == Role.UNLOAD and unload[TODO]:  # is not empty
            print("-------> new task")
            print("\t\tUNLOAD TODO:", unload_tasks)
            print("\t\tUNLOAD ASSIGNED:", unload_assigned)
            emp.set_task(unload[TODO][0])
            unload[TODO].remove(unload[TODO][0])
            print("role: UNLOAD, task: {}".format(emp.get_task()))
        elif r == Role.RESTOCK and restock[TODO]:
            print("-------> new task")
            print("\t\tRESTOCK TODO:", restock_tasks)
            print("\t\tRESTOCK ASSIGNED:", restock_assigned)
            emp.set_task(restock[TODO][0])
            restock[TODO].remove(restock[TODO][0])
            print("role: RESTOCK, task: {}".format(emp.get_task()))
        elif r == Role.TOSS and toss[TODO]:
            print("-------> new task")
            print("\t\tTOSS TODO:", toss_tasks)
            print("\t\tTOSS ASSIGNED:", toss_assigned)
            emp.set_task(toss[TODO][0])
            toss[TODO].remove(toss[TODO][0])
            print("role: TOSS, task: {}".format(emp.get_task()))

        # if role is filled or employee is IDLE
        # assign a new role & task prioritized by time of day
        else:
            print("-------> new role & new task")
            # priority: unload > toss > restock > idle
            if const.store_before(const.CLOCK):
                if unload[TODO]:
                    print("\t\tUNLOAD TODO:", unload_tasks)
                    emp.set_role_and_task(Role.UNLOAD, unload[TODO][0])
                    unload[TODO].remove(unload[TODO][0])
                    print("role: UNLOAD, task: {}".format(emp.get_task()))
                elif toss[TODO]:
                    print("\t\tTOSS TODO:", toss_tasks)
                    emp.set_role_and_task(Role.TOSS, toss[TODO][0])
                    toss[TODO].remove(toss[TODO][0])
                    print("role: TOSS, task: {}".format(emp.get_task()))
                elif restock[TODO]:
                    print("\t\tRESTOCK TODO:", restock_tasks)
                    emp.set_role_and_task(Role.RESTOCK, restock[TODO][0])
                    restock[TODO].remove(restock[TODO][0])
                    print("role: RESTOCK, task: {}".format(emp.get_task()))
                else:
                    emp.set_role_and_task(Role.IDLE, None)
                    print("role: IDLE, task: {}".format(emp.get_task()))

            # priority: restock > toss > unload > idle
            elif const.store_open(const.CLOCK):
                if restock[TODO]:
                    print("\t\tRESTOCK TODO:", restock_tasks)
                    emp.set_role_and_task(Role.RESTOCK, restock[TODO][0])
                    restock[TODO].remove(restock[TODO][0])
                    print("role: RESTOCK, task: {}".format(emp.get_task()))
                elif toss[TODO]:
                    print("\t\tTOSS TODO:", toss_tasks)
                    emp.set_role_and_task(Role.TOSS, toss[TODO][0])
                    toss[TODO].remove(toss[TODO][0])
                    print("role: TOSS, task: {}".format(emp.get_task()))
                elif unload[TODO]:
                    print("\t\tUNLOAD TODO:", unload_tasks)
                    emp.set_role_and_task(Role.UNLOAD, unload[TODO][0])
                    unload[TODO].remove(unload[TODO][0])
                    print("role: UNLOAD, task: {}".format(emp.get_task()))
                else:
                    emp.set_role_and_task(Role.IDLE, None)
                    print("role: IDLE, task: {}".format(emp.get_task()))

            # priority: toss > restock > unload > idle
            elif const.store_closed(const.CLOCK):
                if toss[TODO]:
                    print("\t\tTOSS TODO:", toss_tasks)
                    emp.set_role_and_task(Role.TOSS, toss[TODO][0])
                    toss[TODO].remove(toss[TODO][0])
                    print("role: TOSS, task: {}".format(emp.get_task()))
                elif restock[TODO]:
                    print("\t\tRESTOCK TODO:", restock_tasks)
                    emp.set_role_and_task(Role.RESTOCK, restock[TODO][0])
                    restock[TODO].remove(restock[TODO][0])
                    print("role: RESTOCK, task: {}".format(emp.get_task()))
                elif unload[TODO]:
                    print("\t\tUNLOAD TODO:", unload_tasks)
                    emp.set_role_and_task(Role.UNLOAD, unload[TODO][0])
                    unload[TODO].remove(unload[TODO][0])
                    print("role: UNLOAD, task: {}".format(emp.get_task()))
                else:
                    emp.set_role_and_task(Role.IDLE, None)
                    print("role: IDLE, task: {}".format(emp.get_task()))
    session.commit()
