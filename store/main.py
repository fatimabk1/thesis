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
        if t_step == 70:
            return

        step_start = log()
        print("------------------------------------------------------------------------------------------------------------------------------------------ {:02}:{:02}"\
              .format(Const.CLOCK.hour, Const.CLOCK.minute))
        if Const.OPEN and t_step % 60 == 0:
            print("creating shoppers...")
            t = log()
            # TODO: num_shoppers = random func in const
            Shopper.create(300, session)
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
        prod_lst, inv_lookup = [], []
        if n != 0:
            print("selecting grp now...")
            prod_lst = Product.select_grp(n)
            print("{} products selected".format(len(prod_lst)))
            print("pulling inv now...")
            t = log()
            inv_lookup = Inventory.pull_inventory(n, session)
            delta("\tInventory.pull_inventory", t)
            # print("hello there!")
            assert(len(inv_lookup) == Const.PRODUCT_COUNT)

        # confirm that inventory changes are committed
        inv_before = session.query(ModelInventory.grp_id,
                                   func.sum(ModelInventory.shelved_stock))\
            .group_by(ModelInventory.grp_id)\
            .order_by(ModelInventory.grp_id).all()
        inv_before = [item for item in inv_before]

        if shopper_group:
            print("advancing shoppers...")
            shopper_advance = log()
            for sh in shopper_group:
                t = log()
                stat = sh.step(prod_lst, inv_lookup, session)
                delta("\t\tShopper.step(status={})".format(stat), t)
                if (stat is Status.QUEUE_READY or stat is Status.QUEUEING
                        or stat is Status.DONE):

                    if stat is Status.QUEUE_READY:
                        print("\t\tqueueing shopper...")
                        lid = Lane.queue_shopper(sh.id, lanes, open_lanes)  # CHECK if we should pass a session
                        sh.set_lane(lid)
                        sh.set_status(Status.QUEUEING)
                    elif stat is Status.QUEUEING:
                        sh.increment_qtime(session)
                    elif stat is Status.DONE:
                        # FIXME: no deletes --> IS_DELETED column
                        session.delete(sh)
            session.commit()

            # confirm that inventory changes were committed
            if n > 0:
                inv_after = session.query(ModelInventory.grp_id,
                                          func.sum(ModelInventory.shelved_stock))\
                    .group_by(ModelInventory.grp_id)\
                    .order_by(ModelInventory.grp_id).all()
                inv_after = [item for item in inv_after]
                count = 0
                print("\n", inv_before)
                print("\n", inv_after)
                for i in range(len(inv_before)):
                    if inv_before[i] > inv_after[i]:
                        count += 1
                assert(count > 0)
                print("\n\n")

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
            for index, ln in enumerate(lanes):
                # if (index >= open_lanes
                #         and ln.length == 0
                #         and ln.employee is not None):
                    # ln.close()  # test if values persist -- may need to pass a session to return employee 
                    # >>> now handled within step
                # t = log()
                ln.step(session)
                # delta("\t\tLane.step()", t)
            delta("\tadvancing all lanes", lane_advance)

        # -------------------------------------------------- advance employees
        # collect tasks
        # START HERE >>>>>>>>>>>>>>>>>> LOGGING
        task_collection = log()
        print("\ncollecting tasks...")
        t = log()
        unload_list = Inventory.unload_list(session)
        delta("\t\tInventory.unload_list()", t)
        print("unload list: ", unload_list)
        t = log()
        toss_list = Inventory.toss_list(session)
        delta("\t\tInventory.toss_list()", t)
        print("toss list: ", toss_list)
        t = log()
        restock_list = Inventory.restock_list(session)
        delta("\t\tInventory.restock_list()", t)
        print("restock list: ", restock_list)
        delta("\tcollecting tasks", task_collection)

        # order tasks lists by priority
        print("ordering task lists...")
        todo = []
        if Const.BEFORE:
            todo = [unload_list, restock_list, toss_list]
        elif Const.OPEN:
            todo = [restock_list, toss_list, unload_list]
        else:
            todo = [toss_list, restock_list, unload_list]
        # todo = [item for sublist in todo for item in sublist]  # flatten into list of tuples

        # tuple access
        GRP = 0
        QUANTITY = 1

        print("collecting employees...")
        group = session.query(ModelEmployee)\
            .filter(ModelEmployee.action != Action.CASHIER).all()
        emp_count = len(group)
        assert(emp_count > 0)

        i = 0
        employee_advance = log()
        emp = group[i]
        for lst in todo:
            if not lst:
                print("\tno tasks in lst")
                continue

            else:
                print("---------------------- EMPLOYEE_{} ------------------------".format(emp.id))
                # print("pre_list: ", lst)

                # assign tasks
                print("assigning tasks...")
                count = 0
                emp_q = emp.stock_speed
                tasks = []
                for tpl in lst:
                    if count < emp_q:
                        tasks.append(tpl)
                        count += tpl[QUANTITY]
                emp.set_tasks(tasks)
                print("\tassigned tasks: ", tasks)

                # do task
                t = log()
                updated_tasks = emp.do_tasks(session)
                delta("\t\temp.do_tasks()", t)
                print("\tupdated tasks: ", updated_tasks)

                # update lst
                for tpl in updated_tasks:
                    index = [i for i, t in enumerate(lst)
                             if t[GRP] == tpl[GRP]][0]
                    if tpl[QUANTITY] == 0:
                        del lst[index]
                    else:
                        vals = list(lst[index])
                        vals[QUANTITY] -= tpl[QUANTITY]
                        lst[index] = (vals)
                # print("post_list: ", lst)

                # get next employee
                i += 1
                if i == emp_count:
                    break
                else:
                    emp = group[i]
        delta("\tadvance all employees", employee_advance)
        # -------------------------------------------------- print object statuses
        Const.CLOCK += timedelta(minutes=1)
        delta("\tSIMULATION_STEP()", step_start)
        print("\n***************************** STATUS ***************************************")
        Shopper.print_active_shoppers(session)
        print("\n")
        # Employee.print_active_employees(session)
        Lane.print_active_lanes(lanes)
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
