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

    # UNLOADS
    print("collecting unload list...")
    t = log("\t\tpulling unload list")
    lookup = Inventory.unload_list(session)
    delta("\t\tpulling unload list", t)
    print("beginning to unload...")
    start = log("\tunload all products")
    Inventory.manage_inventory(Const.TASK_UNLOAD, lookup, 1000000)
    t = log()
    session.commit()
    delta("\commit unloads", t)
    delta("\tunload all products", start)

    # RESTOCKS
    print("beginning to RESTOCK tuples...")
    t = log("\t\trestock_list()")
    lookup = Inventory.restock_list(session)
    delta("\t\trestock_list()", t)
    start = log("\trestocking all products")
    Inventory.manage_inventory(Const.TASK_RESTOCK, lookup, 10000000)
    delta("\trestocking all products", start)
    t = log("\tcommiting all restocks")
    session.commit()
    delta("\tcommitting all products", t)
    print("starter inventory completed.")

    print("starter inventory:")
    for prod in Const.products:
        vals = session.query(
            func.sum(ModelInventory.shelved_stock))\
            .filter(ModelInventory.grp_id == prod.grp_id).one()
        assert(vals is not None and vals[0] > 0)


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
