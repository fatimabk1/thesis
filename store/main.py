from datetime import timedelta
from sqlalchemy import func
from models import Shopper, Lane, Employee, Inventory, Const, Product
from models import (ModelShopper,
                    ModelEmployee,
                    ModelProduct,
                    ModelInventory,
                    ModelCategory,
                    SingleLane,
                    Status,
                    Action,
                    Shift,
                    Day)
from models.Base import provide_session, Session
from models import log, delta
import random


# steps for now, later it will be the constant # of minutes in a day
@provide_session
def simulate_day(day, lanes, session=None):
    steps = 840  # 14 hour day
    open_lanes = Const.MIN_LANES
    Const.CURRENT_SHIFT = Shift.MORNING
    t = log()
    Employee.set_day_schedule(day, session)
    delta("\tset_day_schedule()", t)

    for i, ln in enumerate(lanes):
        if i < Const.MIN_LANES:
            ln.open()

    for t_step in range(steps):
        step_start = log()
        print("------------------------------------------------------------------------------------------------------------------------------------------ {:02}:{:02}"\
              .format(Const.CLOCK.hour, Const.CLOCK.minute))
        if Const.OPEN and t_step % 60 == 0:
            print("creating shoppers...")
            t = log()
            # TODO: num_shoppers = random func in const
            Shopper.create(300, session)
            session.commit()
            delta("\tcreate 300 shoppers", t)

        # -------------------------------------------------- advance shoppers
        shopper_group = session.query(ModelShopper).all()

        # Pull all products and inventory for shoppers
        # selecting a grp this minute
        n = 0
        for s in shopper_group:
            if s.browse_mins == 1:
                n += 1
        print("{} SHOPPERS SELECTING...".format(n))
        prod_lst, inv_lookup = [], {}
        if n != 0:
            print("selecting grp now...")
            prod_lst = Product.select_grp(n)
            # for p in prod_lst:
            #     print("\t prod = ", p)
            print("{} products selected".format(len(prod_lst)))
            print("pulling inv now...")
            t = log()
            inv_lookup = Inventory.pull_inventory(n, session)
            delta("\tInventory.pull_inventory", t)
            assert(len(inv_lookup) == Const.PRODUCT_COUNT)

        if shopper_group:
            print("advancing shoppers...")
            shopper_advance = log()
            for sh in shopper_group:
                # t = log()
                stat = sh.step(prod_lst, inv_lookup, session)
                # delta("\t\tShopper.step(status={})".format(stat), t)
                if (stat is Status.QUEUE_READY or stat is Status.QUEUEING
                        or stat is Status.DONE):

                    if stat is Status.QUEUE_READY:
                        # print("\t\tqueueing shopper...")
                        lid = Lane.queue_shopper(sh.id, lanes, open_lanes)
                        sh.set_lane(lid)
                        sh.set_status(Status.QUEUEING)
                    elif stat is Status.QUEUEING:
                        sh.increment_qtime(session)
                    elif stat is Status.DONE:
                        pass
                        # FIXME: no deletes --> IS_DELETED column
            t = log()
            session.commit()
            delta("\tcommiting shopper steps", t)
            delta("\tadvancing {} shoppers".format(len(shopper_group)), shopper_advance)

        # -------------------------------------------------- advance lanes
        # lanes are open for store hours and post-close lingering shoppers
        if Const.OPEN or shopper_group:
            t = log()
            open_lanes = Lane.manage(lanes, open_lanes, session)  # expand & open -OR- collapse
            delta("\t\tLane.manage()", t)
            if Const.shift_change():
                print("shift change!")
                Lane.shift_change(open_lanes, session)

            # finish closing out lanes that were checking out shoppers when closed
            lane_advance = log()
            for ln in lanes:
                # t = log()
                ln.step(session)
                # delta("\t\tLane.step()", t)
            delta("\tadvancing all lanes", lane_advance)

        # -------------------------------------------------- advance employees
        # collect tasks
        task_collection = log()
        print("\ncollecting tasks...")

        t = log()
        unload_lookup = Inventory.unload_list(session)
        delta("\t\tInventory.unload_list()", t)

        t = log()
        toss_lookup = Inventory.toss_list(session)
        delta("\t\tInventory.toss_list()", t)

        t = log()
        restock_lookup = Inventory.restock_list(session)
        delta("\t\tInventory.restock_list()", t)

        delta("\tcollecting tasks", task_collection)

        # order tasks lists by priority
        print("ordering task lists...")
        todo = []
        if Const.BEFORE:
            todo = [{"type": Const.TASK_UNLOAD,
                     "lookup": unload_lookup},
                    {"type": Const.TASK_RESTOCK,
                     "lookup": restock_lookup},
                    {"type": Const.TASK_TOSS,
                     "lookup": toss_lookup}]
        elif Const.OPEN:
            todo = [{"type": Const.TASK_RESTOCK,
                     "lookup": restock_lookup},
                    {"type": Const.TASK_TOSS,
                     "lookup": toss_lookup},
                    {"type": Const.TASK_UNLOAD,
                     "lookup": unload_lookup}]
        else:
            todo = [{"type": Const.TASK_TOSS,
                     "lookup": toss_lookup},
                    {"type": Const.TASK_RESTOCK,
                     "lookup": restock_lookup},
                    {"type": Const.TASK_UNLOAD,
                     "lookup": unload_lookup}]

        print("collecting employees...")
        employee_advance = log()
        group = session.query(ModelEmployee)\
            .filter(ModelEmployee.action != Action.CASHIER).all()
        emp_count = len(group)
        assert(emp_count > 0)

        todo_index = 0
        # loop through employees
        for emp in group:
            while(todo_index < len(todo) and bool(todo[todo_index]["lookup"]) is False):
                todo_index += 1

            if todo_index >= len(todo):
                break

            task = todo[todo_index]["type"]
            print("Task type: ", task)
            lookup = todo[todo_index]["lookup"]
            emp_q = emp.get_speed(task)
            print("Advancing employee {} with speed {}".format(emp.id, emp_q))

            i = 0
            # loop through tasks in lookup
            while(emp_q != 0):
                i += 1
                if i == 50:
                    exit(1)

                # do task
                t = log()
                emp_q, completed = Inventory.manage_inventory(task, lookup, emp_q)
                delta("\t\t\tInventory.manage_inventory()", t)
                # print("completed: ", completed)

                # update lookup
                for grp_id in completed:
                    del lookup[grp_id]

                if bool(todo[todo_index]["lookup"]) is False:
                    break

            # move on to next todo
            if bool(todo[todo_index]["lookup"]) is False:
                todo_index += 1
                if todo_index > len(todo):
                    break
        delta("\tadvance all employees", employee_advance)

        # -------------------------------------------------- print object statuses
        Const.CLOCK += timedelta(minutes=1)
        delta("\tSIMULATION_STEP(steps={})".format(t_step), step_start)
        print("\n***************************** STATUS ***************************************")
        Shopper.print_active_shoppers(session)
        print("\n")
        # Employee.print_active_employees(session)
        # print("\n")
        Lane.print_active_lanes(lanes)
        # print("\n")
        # Inventory.print_stock_status(session)

    print("Day complete. Good Job!!!")


@provide_session
def setup_lanes_and_employees(lanes, session=None):
    # create & schedule employees
    t = log("\tcreate {} employees:".format(Const.NUM_EMPLOYEES))
    for i in range(Const.NUM_EMPLOYEES):
        Employee.create_employee(session)
    delta("\tcreate {} employees:".format(Const.NUM_EMPLOYEES), t)

    t = log("\tmake_week_schedule()")
    Employee.make_week_schedule(session)
    delta("\tmake_week_schedule()", t)

    # create and open minimum lanes
    t = log("\tcreate {} lanes:".format(Const.MAX_LANES))
    for i in range(Const.MAX_LANES):
        ln = SingleLane(i)
        lanes.append(ln)
    session.commit()
    delta("\tcreate {} lanes:".format(Const.MAX_LANES), t)


@provide_session
def pull_data(session=None):
    cats = session.query(ModelCategory)\
        .order_by(ModelCategory.id).all()
    lst = []
    for c in cats:
        lst.append(c)
    Const.categories = lst

    prods = session.query(ModelProduct)\
        .order_by(ModelProduct.grp_id).all()
    lst = []
    for p in prods:
        lst.append(p)
    Const.products = lst


def run():
    pull_data()
    random.seed(0)
    lanes = []
    t = log()
    setup_lanes_and_employees(lanes)
    delta("setup_lanes_and_employees()", t)
    Inventory.print_stock_status()
    t = log()

    simulate_day(Day.SUNDAY, lanes)
    delta("simulate_day()", t)

    # for i in range(Const.NUM_DAYS):
    #    # simulate_day(lanes, open_lanes)


if __name__ == '__main__':
    run()
