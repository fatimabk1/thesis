# a program to test the product.py file
from models.base import check_session, check_object_status
from datetime import datetime, timedelta
from models.some_models import ModelRevenue, ModelQtime
from sqlalchemy import func
from tabulate import tabulate
import time

from models import ModelShopper, ModelProduct, ModelInventory
from models import const,  shopper, Status, provide_session, Session

# order_inventory, restock_list, select_inv,\
# # toss_list, unload_list, restock, unload, create_pending
from models import cart
from models import inventory


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
    lst = inventory.unload_list(session)
    while lst:
        for grp in lst:
            inventory.unload(grp, session)
        lst = inventory.unload_list(session)
        # print("Remaining Unloads:", lst)

    # initial restock
    lst = inventory.restock_list(session)
    while lst:
        for grp in lst:
            inventory.restock(grp, 1000, session)
            lst = inventory.restock_list(session)
            # print("Remaining Restocks:", lst)

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


if __name__ == "__main__":
    initialize()
    advance_all_shoppers(CLOCK)
    print("Good Job!")
