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


# steps for now, later it will be the constant # of minutes in a day
@provide_session
def simulate_day(day, lanes, session=None):
    steps = 840  # 14 hour day
    open_lanes = Const.MIN_LANES
    Const.CURRENT_SHIFT = Shift.MORNING
    Employee.set_day_schedule(day, session)

    for i, ln in enumerate(lanes):
        if i < Const.MIN_LANES:
            ln.open()

    for i in range(steps):
        print("------------------------------------------------------------------------------------------------------------------------------------------ {:02}:{:02}"\
              .format(Const.CLOCK.hour, Const.CLOCK.minute))
        if Const.store_open() and i % 60 == 0:
            print("creating shoppers...")
            # num_shoppers = something based on busyness -- lookup in Const?
            Shopper.create(300, session)

        # -------------------------------------------------- advance shoppers
        # do not admit shoppers after store is closed
        if Const.store_closed():
            late_shoppers = session.query(ModelShopper.id)\
                .filter(ModelShopper.Status == Status.INERT).all()
            for s in late_shoppers:
                session.delete(s)
            session.commit()

        shopper_group = session.query(ModelShopper.id).all()
        shopper_group = [item for sublist in shopper_group for item in sublist]
        if shopper_group:
            print("advancing shoppers...")
            for sid in shopper_group:
                stat = Shopper.step(sid)
                s = None
                if (stat is Status.QUEUE_READY or stat is Status.QUEUEING
                        or stat is Status.DONE):
                    s = session.query(ModelShopper)\
                        .filter(ModelShopper.id == sid).one()
                    assert(s.status == stat)

                    if stat is Status.QUEUE_READY:
                        print("\t\tqueueing shopper...")
                        lid = Lane.queue_shopper(sid, lanes, open_lanes)  # CHECK if we should pass a session
                        s.set_lane(lid)
                        s.set_status(Status.QUEUEING)
                    elif stat is Status.QUEUEING:
                        Shopper.increment_qtime(sid, session)
                    elif stat is Status.DONE:
                        session.delete(s)
                    session.commit()

        # -------------------------------------------------- advance lanes
        # lanes are open for store hours and post-close lingering shoppers
        if Const.store_open() or shopper_group:
            open_lanes = Lane.manage(lanes, open_lanes, session)  # expand & open -OR- collapse
            if Const.shift_change():
                print("shift change!")
                Lane.shift_change(open_lanes, session)

            # finish closing out lanes that were checking out shoppers when closed
            for index, ln in enumerate(lanes):
                if (index >= open_lanes
                        and ln.length == 0
                        and ln.employee is not None):
                    ln.close()  # test if values persist -- may need to pass a session to return employee
                ln.step(session)

        # -------------------------------------------------- advance employees
        # collect tasks
        print("\ncollecting tasks...")
        unload_list = Inventory.unload_list(session)
        print("unload list: ", unload_list)
        toss_list = Inventory.toss_list(session)
        print("toss list: ", toss_list)
        restock_list = Inventory.restock_list(session)
        print("restock list: ", restock_list)

        # order tasks lists by priority
        print("ordering task lists...")
        todo = []
        if Const.store_before():
            todo = [unload_list, restock_list, toss_list]
        elif Const.store_open():
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
                updated_tasks = emp.do_tasks(session)
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

        # -------------------------------------------------- print object statuses
        print("\n***************************** STATUS ***************************************")
        Shopper.print_active_shoppers(session)
        # Employee.print_active_employees(session)
        Lane.print_active_lanes(lanes)
        # Inventory.print_stock_status(session)
        Const.CLOCK += timedelta(minutes=1)

    print("Day complete. Good Job!!!")


# initialze categories, products, and inventory
@provide_session
def initialize(session=None):
    for i in range(Const.CATEGORY_COUNT):
        c = ModelCategory()
        session.add(c)
    session.commit()

    print("creating categories and products...")
    for i in range(Const.CATEGORY_COUNT):
        c = session.query(ModelCategory)\
            .filter(ModelCategory.id == i+1).one()
        for j in range(Const.PRODUCTS_PER_CATEGORY):
            p = ModelProduct()
            p.setup(c.id)
            session.add(p)
            c.count += 1
        session.commit()

    # inital inventory order
    Const.TRUCK_DAYS = 0  # make immediately available
    print("ordering inventory...")
    Inventory.order_inventory(session)
    Const.TRUCK_DAYS = 2
    print("unloading inventory...")
    lst = Inventory.unload_list(session)
    GRP = 0
    QUANTITY = 1
    # ACTION = 2

    # confirm unload lst
    print("beginning to UNLOAD tuples...")
    for tpl in lst:
        print("\t", tpl)
        q, emp_q = Inventory.unload(tpl[GRP], tpl[QUANTITY], 1000000, session)
        # print("q = {}, emp_q = {}".format(q, emp_q))
        vals = session.query(func.sum(ModelInventory.pending_stock),
                             func.sum(ModelInventory.back_stock))\
            .filter(ModelInventory.grp_id == tpl[GRP]).one()
        pending, back = vals[0], vals[1]
        # print("pending = {}, back = {}".format(pending, back))
        prod = session.query(ModelProduct)\
            .filter(ModelProduct.grp_id == tpl[GRP]).one()
        assert(pending == 0)
        assert(back >= tpl[QUANTITY] * prod.get_lot_quantity())

    # initial restock
    print("beginning to RESTOCK tuples...")
    lst = Inventory.restock_list(session)
    for tpl in lst:
        print("\t", tpl)
        Inventory.restock(tpl[GRP], tpl[QUANTITY], 100000, session)
        shelf = session.query(func.sum(ModelInventory.shelved_stock))\
            .filter(ModelInventory.grp_id == tpl[GRP]).one()[0]
        prod = session.query(ModelProduct)\
            .filter(ModelProduct.grp_id == tpl[GRP]).one()
        assert(shelf == prod.get_max_shelved_stock())

    session.commit()
    print("starter inventory completed.")
    # print("starter inventory:")
    # inv_lst = session.query(ModelInventory)\
    #     .order_by(ModelInventory.grp_id)\
    #     .order_by(ModelInventory.sell_by)\
    #     .order_by(ModelInventory.id).all()
    # prev = inv_lst[0].grp_id
    # for inv in inv_lst:
    #     curr = inv.grp_id
    #     if prev != curr:
    #         print("\n")
    #     inv.print()
    #     prev = inv.grp_id


@provide_session
def setup_lanes_and_employees(lanes, session=None):
    # create & schedule employees
    for i in range(Const.NUM_EMPLOYEES):
        Employee.create_employee(session)
    Employee.make_week_schedule(session)

    # create and open minimum lanes
    for i in range(Const.MAX_LANES):
        ln = SingleLane(i)
        lanes.append(ln)
    session.commit()


def run():
    lanes = []
    setup_lanes_and_employees(lanes)
    initialize()
    Inventory.print_stock_status()
    simulate_day(Day.SUNDAY, lanes)

    # for i in range(Const.NUM_DAYS):
    #    # simulate_day(lanes, open_lanes)


if __name__ == '__main__':
    run()
