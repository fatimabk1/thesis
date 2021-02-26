from datetime import timedelta
from sqlalchemy.sql.expression import false
from sqlalchemy import func
from models import Shopper, Lane, Employee, Inventory, Const, Product, Cart
from models import (ModelShopper,
                    ModelEmployee,
                    ModelProduct,
                    ModelInventory,
                    ModelCategory,
                    ModelCart,
                    SingleLane,
                    Status,
                    Action,
                    Shift,
                    Day)
from models.Base import provide_session, Session
from models import log, delta, StoreStatus, Day
import random
from math import floor
import beepy


# steps for now, later it will be the constant # of minutes in a day
@provide_session
def simulate_day(day, lanes, session=None):
    open_lanes = Const.MIN_LANES
    Const.CURRENT_SHIFT = Shift.MORNING

    employee_group = Employee.pull_employees(session)
    for i, ln in enumerate(lanes):
        if i < Const.MIN_LANES:
            ln.open(employee_group)

    # pull inventory
    t = log()
    inv_lookup = Inventory.pull_inventory(session)
    delta("\tInventory.pull_inventory", t, 0)

    for t_step in range(Const.day_steps):

        step_start = log()
        print("------------------------------------------------------------------------------------------------------------------------------------------ {:02}:{:02}"\
              .format(Const.CLOCK.hour, Const.CLOCK.minute))
        if (t_step >= StoreStatus.OPEN
                and t_step < StoreStatus.CLOSED
                and t_step % 60 == 0):
            print("creating shoppers...")
            t = log()
            Shopper.create(Const.SHOPPER_ADD, session)
            session.commit()
            delta("\tcreate {} shoppers".format(Const.SHOPPER_ADD), t, t_step)

        # ------------------------------------------------------------------- advance shoppers
        # pull shoppers
        shopper_group = session.query(ModelShopper)\
            .filter(ModelShopper.deleted == False).all()

        if shopper_group:
            print("advancing shoppers...")
            shopper_advance = log()
            for sh in shopper_group:
                # t = log()
                stat = sh.step(t_step, inv_lookup, session)
                # delta("\t\tShopper.step(status={})".format(stat), t, t_step)
                if stat is Status.QUEUE_READY:
                    # t = log()
                    lid = Lane.queue_shopper(sh.id, lanes, open_lanes)
                    # delta("\t\t\tLane.queue_shopper())", t, t_step)
                    sh.set_lane(lid)
                    sh.set_status(Status.QUEUEING)
                elif stat is Status.QUEUEING:
                    sh.increment_qtime(session)

            delta("\tadvancing shoppers", shopper_advance, t_step)

        # ------------------------------------------------------------------- prepare employees
        # prepare employees to work lanes and inventory jobs
        t = log()
        employee_group = Employee.pull_employees(session)
        delta("Employee.pull_employees()", t, t_step)
        if t_step == StoreStatus.SHIFT_CHANGE:
            print("SHIFT CHANGE")
            Const.CURRENT_SHIFT = Shift.EVENING
            t = log()
            Employee.shift_change(employee_group)
            delta("\t\tEmployee.shift_change()", t, t_step)
            t = log()
            Lane.shift_change(lanes, employee_group)
            delta("\t\tLane.shift_change()", t, t_step)

        # ------------------------------------------------------------------- advance lanes
        # lanes are open for store hours and post-close lingering shoppers
        if ((t_step >= StoreStatus.OPEN
                and t_step < StoreStatus.CLOSED)
                or shopper_group):

            # collect carts and manage lanes
            t = log()
            carts, sid_list = Lane.get_carts_sids(lanes, session)
            delta("\t\tLane.get_carts_sids()", t, t_step)
            t = log()
            open_lanes = Lane.manage(lanes, open_lanes, employee_group, carts)
            delta("\t\tLane.manage()", t, t_step)

            # collect queued shoppers
            queued_shoppers = {}
            for sh in shopper_group:
                if sh.id not in sid_list:
                    continue
                queued_shoppers[sh.id] = sh

            # advance lanes
            lane_advance = log()
            for ln in lanes:
                # t = log()
                ln.step(open_lanes, queued_shoppers, carts, employee_group)
                # delta("\t\tLane.step()", t, t_step)
            # session.commit()
            delta("\tadvancing all lanes", lane_advance, t_step)

        # ------------------------------------------------------------------- advance employees

        print("\ncollecting tasks...")
        task_collection = log()
        todo = None
        if t_step < StoreStatus.OPEN:
            t = log()
            unload_lookup = Inventory.unload_list(inv_lookup)
            delta("\t\tInventory.unload_list()", t, t_step)
            todo = {"type": Const.TASK_UNLOAD, "lookup": unload_lookup}
        elif t_step >= StoreStatus.CLOSED:
            t = log()
            toss_lookup = Inventory.toss_list(inv_lookup)
            delta("\t\tInventory.toss_list()", t, t_step)
            todo = {"type": Const.TASK_TOSS, "lookup": toss_lookup}
        else:
            assert(t_step >= StoreStatus.OPEN
                   and t_step < StoreStatus.CLOSED)
            t = log()
            restock_lookup = Inventory.restock_list(inv_lookup)
            delta("\t\tInventory.restock_list()", t, t_step)
            todo = {"type": Const.TASK_RESTOCK, "lookup": restock_lookup}

        delta("\tcollecting tasks...task_type = {}"
              .format(todo["type"]), task_collection, t_step)

        print("~lookup:")
        for key in todo['lookup']:
            print(key, todo['lookup'][key]['quantity'])
        if bool(todo["lookup"]) is not False:
            employee_advance = log()
            # loop through employees
            for eid in employee_group["available"]:
                emp = employee_group["available"][eid]
                if emp.action == Action.CASHIER:
                    continue
                emp_q = emp.get_speed(todo["type"])
                t = log()
                Inventory.dispatch(todo["type"], todo["lookup"], emp_q)
                delta("\t\t\tInventory.dispatch()", t, t_step)
            delta("\tadvance all employees", employee_advance, t_step)
        session.commit()
        # ------------------------------------------------------------------- print status
        delta("\tSIMULATION_STEP()", step_start)
        print("\n***************************** STATUS [{:02}:{:02}] ***************************************"\
              .format(Const.CLOCK.hour, Const.CLOCK.minute))
        Const.CLOCK += timedelta(minutes=1)
        # Shopper.print_active_shoppers(session)
        # print("\n")
        # Employee.print_active_employees(session)
        # print("\n")
        Lane.print_active_lanes(lanes)
        # print("\n")
        # Inventory.print_stock_status(session)

    print("Day complete. Good Job!!!")


@provide_session
def setup_lanes_and_employees(lanes, session=None):
    # create & schedule employees
    t = log()
    Employee.create_employees(Const.NUM_EMPLOYEES, session)
    delta("\tcreate {} employees:".format(Const.NUM_EMPLOYEES), t)

    # create and open minimum lanes
    t = log()
    for i in range(Const.MAX_LANES):
        ln = SingleLane(i)
        lanes.append(ln)
    session.commit()
    delta("\tcreate {} lanes:".format(Const.MAX_LANES), t)


@provide_session
def pull_data(session=None):
    # initialize Const.categories
    cats = session.query(ModelCategory)\
        .order_by(ModelCategory.id).all()
    lst = []
    for c in cats:
        lst.append(c)
    Const.categories = lst

    # initialize Const.products
    prods = session.query(ModelProduct)\
        .order_by(ModelProduct.grp_id).all()
    lst = []
    for index, p in enumerate(prods):
        lst.append(p)
    Const.products = lst

    # initialize Const.product_stats
    all_inventory = session.query(ModelInventory).all()
    for prod in Const.products:
        inv_lst = [inv for inv in all_inventory
                   if inv.deleted is False
                   and inv.grp_id == prod.grp_id]
        shelf = sum(inv.shelved_stock for inv in inv_lst)
        back = sum(inv.back_stock for inv in inv_lst)
        pending = sum(inv.pending_stock for inv in inv_lst)
        Const.product_stats[prod.grp_id - 1] = {"shelf": shelf,
                                            "back": back,
                                            "pending": pending}

def simulate(session):
    pull_data(session)
    random.seed(0)
    lanes = []
    Inventory.print_stock_status()

    # setup employees
    schedule = [Shift.OFF, Shift.MORNING, Shift.MORNING,
                Shift.MORNING, Shift.EVENING, Shift.EVENING, Shift.EVENING]
    t = log()
    setup_lanes_and_employees(lanes, session)
    delta("setup_lanes_and_employees()", t)

    # simulate year
    curr_month = Const.CLOCK.month
    curr_year = Const.CLOCK.year
    for i in range(52):
        for day in Const.days:
            # set employee schedule
            t = log()
            Employee.set_day_schedule(schedule, session)
            delta("\tset_day_schedule()", t)
            t = log()
            simulate_day(day, lanes)
            delta("simulate_day()", t)
            Const.print_tracking()
            beepy.beep(sound=2)

            # update master schedule
            shift = schedule.pop()
            schedule.append(shift)

            # update clock for next day
            Const.CLOCK += timedelta(days=1)
            Const.CLOCK = Const.CLOCK.replace(hour=10, minute=0)
            print("\n\nA successful day! :)")
            exit(0)

        # order inventory
        print("Weekly order inventory")
        Inventory.order_inventory(session)

        if Const.CLOCK.month != curr_month:
            # TODO: monthly stats collection
            curr_month = Const.CLOCK.month
        if Const.CLOCK.year != curr_year:
            # TODO: yearly stats collection
            curr_year = Const.CLOCK.year
    # TODO: print stats to report


if __name__ == '__main__':
    session = Session()
    simulate(session)
