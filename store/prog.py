# a program to test the product.py file
from datetime import timedelta
from sqlalchemy import func
from tabulate import tabulate

from models.base import check_session, check_object_status
from models.some_models import ModelRevenue, ModelQtime
from models.employee import Day, Role, Shift

from models import ModelShopper, ModelProduct, ModelInventory, ModelEmployee
from models import Status, provide_session, Session
from models import cart, inventory, shopper, const, employee


CLOCK = const.CLOCK


@provide_session
def initialize(session=None):
    print("initialize: ", session)
    products = session.query(ModelProduct).all()
    table = []
    for prod in products:
        table.append(prod.setup())
        session.commit()

    # inital inventory order
    inventory.order_inventory(session)
    # lst = inventory.unload_list(session)
    # while lst:
    #     for grp in lst:
    #         inventory.unload(grp, session)
    #     lst = inventory.unload_list(session)
    #     # print("Remaining Unloads:", lst)

    # # initial restock
    # lst = inventory.restock_list(session)
    # while lst:
    #     for grp in lst:
    #         inventory.restock(grp, 1000, session)
    #         lst = inventory.restock_list(session)
    #         # print("Remaining Restocks:", lst)

    session.commit()


@provide_session
def advance_all_shoppers(CLOCK, session=None):
    print("Creating shoppers: ", session)
    for i in range(30):
        s = ModelShopper()
        session.add(s)
    session.commit()
    session.close()

    trip_stats = []

    for i in range(240):
        print("------------------------------------------------------ minute {}".format(i))
        table = []
        headers = ["MIN", "sid", "status", "start", "browse",
                   "quota", "cart", "lane", "qtime", "total"]
        shopper_lst = session.query(ModelShopper).all()
        if not shopper_lst:
            break

        for s in shopper_lst:
            sid = s.id
            stat = shopper.step(sid, CLOCK)
            print(s.print())
            # stat = shopper.step(sid, CLOCK, session)
            table.append(s.__repr__())

            if (stat == Status.QUEUEING or
                    stat == Status.QUEUE_READY or
                    stat == Status.CHECKOUT or
                    stat == Status.DONE):

                s = session.query(ModelShopper)\
                    .filter(ModelShopper.id == sid).one()

                if stat == Status.QUEUE_READY:
                    s.set_lane(3)
                    s.set_status(Status.QUEUEING)

                elif stat == Status.QUEUEING:
                    s.increment_qtime(session)
                    if s.qtime == 10:
                        s.set_status(Status.CHECKOUT)

                elif stat == Status.CHECKOUT:
                    cart.scan_n(sid, 12, session)
                    if cart.get_size(sid, session) == 0:
                        s.set_status(Status.DONE)

                else:
                    assert(stat == Status.DONE)
                    trip_stats.append(
                        {"start": s.cart_count,
                         "duration": i-s.start_min}
                        )
                    session.delete(s)
                    session.commit()
                    break
                session.commit()
            # session.close()
        CLOCK = CLOCK + timedelta(minutes=1)
        for row in table:
            row.insert(0, CLOCK.minute)
        print("\n", tabulate(table, headers=headers))

    rev = session.query(ModelRevenue).all()
    for row in rev:
        row.print()
    qt = session.query(ModelQtime).all()
    for row in qt:
        row.print()

    for item in trip_stats:
        # START: average shopping duration per # of items
        print("{} items - {} minutes".format(item["start"], item["duration"]))

    session.close()


def advance_all_employees(CLOCK):
    # EXECUTE
    session = Session()
    print("\nCREATING EMPLOYEES & BLANK SCHEDULES")
    for i in range(30):
        employee.create_employee(session)
    session.commit()
    session.close()

    # VALIDATE
    session = Session()
    emp_lst = session.query(ModelEmployee).all()
    print("confirming employee list...")
    for emp in emp_lst:
        emp.print()
    print("--------------- SCHEDULE ---------------")
    print("confirming blank schedule...")
    employee.print_full_schedule(session)
    session.commit()
    session.close()

    # EXECUTE
    session = Session()
    print("\nMAKING WEEK SCHEDULE")
    # consider making schedule a separate file
    employee.make_week_schedule(session)
    session.commit()
    session.close

    # VALIDATE
    session = Session()
    print("confirming full schedule...")
    employee.print_full_schedule(session)
    session.commit()
    session.close()

    # EXECUTE
    session = Session()
    day = Day.SUNDAY
    print("\nSET EMPLOYEE'S DAY SCHEDULE")
    employee.set_day_schedule(day, session)
    session.commit()
    session.close()

    # VALIDATE
    print("confirming employee's day schedule..")
    session = Session()
    emp_lst = session.query(ModelEmployee).all()
    for emp in emp_lst:
        emp.print()
    session.commit()
    session.close()

    # 10 time steps
    for i in range(10):
        print("------------------------------------------------------------------------------------------ TIME STEP {}".format(i))

        # EXECUTE
        print("\nPREPARING EMPLOYEE ROLE & TASK")
        session = Session()
        employee.prepare_employees(Shift.MORNING, session)
        session.commit()
        session.close()

        # VALIDATE
        print("\nconfirming employee role & task:")
        session = Session()
        emp_lst = session.query(ModelEmployee)\
            .filter(ModelEmployee.shift == Shift.MORNING).all()
        for emp in emp_lst:
            emp.print()
        session.commit()
        session.close()

        # EXECUTE
        session = Session()
        emp_lst = session.query(ModelEmployee)\
            .filter(ModelEmployee.shift == Shift.MORNING).all()
        print("\nDOING TASKS")
        for emp in emp_lst:
            print("employee {} - confirming task completion...".format(emp.id))
            emp.do_task(session)
            emp.increment_time_worked()
        session.commit()
        session.close()

        # test a CASHIER employee for two cycles
        if i == 5:
            session = Session()
            print("\nSETTING EMP # 12 TO CASHIER")
            emp = session.query(ModelEmployee)\
                .filter(ModelEmployee.id == 12).one()
            emp.set_role_and_task(Role.CASHIER, None)
            session.commit()
            session.close()

        if i == 8:
            session = Session()
            print("\nSETTING EMP # 12 TO IDLE")
            emp = session.query(ModelEmployee)\
                .filter(ModelEmployee.id == 12).one()
            emp.set_role_and_task(Role.IDLE, None)
            session.commit()
            session.close()
        session.commit()
        session.close()
        CLOCK += timedelta(minutes=1)

    session.commit()


if __name__ == "__main__":
    initialize()
    advance_all_employees(const.CLOCK)
    print("\nPaying my amazing employees:")
    session = Session()
    emp_lst = session.query(ModelEmployee).all()
    emp_lst.sort(key=lambda x: x.id)
    for emp in emp_lst:
        print("Employee {}: {:.2f}".format(emp.id, emp.calculate_wages()))
    session.close()
    print("Good Job!")
