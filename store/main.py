from datetime import datetime, timedelta
from models import Shopper, Lane, Employee, Inventory, Const
from models import (ModelShopper,
                    ModelEmployee,
                    ModelProduct,
                    ModelInventory,
                    SingleLane,
                    Status,
                    Role,
                    Shift,
                    Day)
from models.Base import provide_session, Session
import sys


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
            # create shoppers
            for i in range(30):
                s = ModelShopper()
                session.add(s)
            session.commit()

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
            open_lanes = Lane.manage(lanes, open_lanes)  # expand & open -OR- collapse
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
        Employee.prepare_employees(session)
        group = session.query(ModelEmployee)\
            .filter(ModelEmployee.role != Role.CASHIER,
                    ModelEmployee.role != Role.IDLE).all()
        print("advancing employees...")
        for emp in group:
            emp.do_task(session)

        # -------------------------------------------------- print object statuses
        Shopper.print_active_shoppers(session)
        Employee.print_active_employees(session)
        Lane.print_active_lanes(lanes)
        Const.CLOCK += timedelta(minutes=1)

    print("Day complete. Good Job!!!")


@provide_session
def initialize_products_and_inventory(session=None):
    print("initialize: ", session)
    products = session.query(ModelProduct).all()
    for prod in products:
        prod.setup()
    session.commit()

    # inital inventory order
    Inventory.order_inventory(session)
    lst = Inventory.unload_list(session)
    while lst:
        for grp in lst:
            Inventory.unload(grp, session)
        lst = Inventory.unload_list(session)
        # print("Remaining Unloads:", lst)

    # initial restock
    lst = Inventory.restock_list(session)
    while lst:
        for grp in lst:
            Inventory.restock(grp, 1000, session)
            lst = Inventory.restock_list(session)
            # print("Remaining Restocks:", lst)

    session.commit()


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
    initialize_products_and_inventory()
    # START >>> list inv data for 5 & 3 -- fixing toss
    simulate_day(Day.SUNDAY, lanes)

    # for i in range(Const.NUM_DAYS):
    #    # simulate_day(lanes, open_lanes)


if __name__ == '__main__':
    run()
