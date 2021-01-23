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


# initialze categories, products, and inventory
@provide_session
def initialize(session=None):
    categories = []
    print("creating categories...")
    t = log("\tcreate {} categories:".format(Const.CATEGORY_COUNT))
    for i in range(Const.CATEGORY_COUNT):
        c = ModelCategory()
        session.add(c)
        categories.append(c)
    session.commit()
    delta("\tcreate {} categories:".format(Const.CATEGORY_COUNT), t)

    print("creating products...")
    start = log("\tLOOP_creating all products")
    for i in range(Const.CATEGORY_COUNT):
        c = categories[i]
        for j in range(Const.PRODUCTS_PER_CATEGORY):
            p = ModelProduct()
            p.setup(c.id)
            session.add(p)
            c.count += 1
    delta("\tLOOP_creating all products", start)
    t = log("\tcommiting products + products")
    session.commit()
    delta("\tcommitting products + categories", t)

    pull_data(session)

    # inital inventory order
    Const.TRUCK_DAYS = 0  # make immediately available
    print("ordering inventory...")
    t = log("\t\tordering inventory")
    Inventory.order_inventory(session)
    Const.TRUCK_DAYS = 2
    delta("\t\tordering inventory", t)
    print("collecting unload list...")
    t = log("\t\tpulling unload list")
    lst = Inventory.unload_list(session)
    delta("\t\tpulling unload list", t)
    GRP = 0
    QUANTITY = 1
    # ACTION = 2

    # confirm unload lst
    print("beginning to unload...")
    start = log("\tunload all products")
    for tpl in lst:
        print("\t", tpl)
        t = log("\t\tunload " + str(tpl))
        q, emp_q = Inventory.unload(tpl[GRP], tpl[QUANTITY], 1000000, session)
        delta("\t\tunload" + str(tpl), t)
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
    delta("\tunload all products", start)

    # initial restock
    print("beginning to RESTOCK tuples...")
    t = log("\t\trestock_list()")
    lst = Inventory.restock_list(session)
    delta("\t\trestock_list()", t)
    start = log("\trestocking all products")
    for tpl in lst:
        print("\t", tpl)
        t = log("\t\trestock" + str(tpl))
        Inventory.restock(tpl[GRP], tpl[QUANTITY], 100000, session)
        delta("\t\trestock" + str(tpl), t)
        shelf = session.query(func.sum(ModelInventory.shelved_stock))\
            .filter(ModelInventory.grp_id == tpl[GRP]).one()[0]
        prod = session.query(ModelProduct)\
            .filter(ModelProduct.grp_id == tpl[GRP]).one()
        assert(shelf == prod.get_max_shelved_stock())
    delta("\trestocking all products", start)
    t = log("\tcommiting all restocks")
    session.commit()
    delta("\tcommitting all products", t)
    print("starter inventory completed.")

    print("starter inventory:")
    inv_lst = session.query(ModelInventory)\
        .order_by(ModelInventory.grp_id)\
        .order_by(ModelInventory.sell_by)\
        .order_by(ModelInventory.id).all()
    prev = inv_lst[0].grp_id
    for inv in inv_lst:
        curr = inv.grp_id
        if prev != curr:
            print("\n")
        inv.print()
        prev = inv.grp_id


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
    random.seed(0)
    t = log("initialize()")
    initialize()
    delta("initialize()", t)


if __name__ == '__main__':
    run()
