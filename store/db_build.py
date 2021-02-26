from datetime import timedelta
from sqlalchemy import func
from sqlalchemy.sql.expression import false

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
            grp_id = i * Const.PRODUCTS_PER_CATEGORY + j
            Const.product_stats[grp_id] = {"shelf": 0,
                                            "back": 0,
                                            "pending": 0}
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

    all_inventory = session.query(ModelInventory)\
        .order_by(ModelInventory.pending_stock).all()
    print("~~~ INVENTORY: CREATED / PENDING")
    all_inventory[0].print()

    Inventory.print_stock_status(session)

    # UNLOADS
    print("collecting unload list...")
    inventory_lookup = Inventory.pull_inventory(session)
    t = log("\t\tpulling unload list")
    lookup = Inventory.unload_list(inventory_lookup)
    delta("\t\tpulling unload list", t)

    print("beginning to unload...")
    start = log()
    Inventory.dispatch(Const.TASK_UNLOAD, lookup, 1000000)
    delta("\tunload all products", start)
    all_inventory = session.query(ModelInventory)\
        .order_by(ModelInventory.back_stock).all()
    print("~~~ INVENTORY: UNLOADED / BACK")
    all_inventory[0].print()

    Inventory.print_stock_status(session)

    t = log()
    session.commit()
    delta("\tcommit unloads", t)
    delta("\t commit + unload all products", start)

    # RESTOCKS
    print("beginning to RESTOCK tuples...")
    t = log()
    lookup = Inventory.restock_list(inventory_lookup)
    delta("\t\trestock_list()", t)

    t = log()
    Inventory.dispatch(Const.TASK_RESTOCK, lookup, 10000000)
    delta("\trestocking all products", t)
    all_inventory = session.query(ModelInventory)\
        .order_by(ModelInventory.shelved_stock).all()
    print("~~~ INVENTORY: RESTOCKED / SHELF - after dispatch()")
    all_inventory[0].print()

    t = log()
    session.commit()
    delta("\tcommitting all products", t)

    print("starter inventory completed.")
    lookup = Inventory.restock_list(inventory_lookup)
    session.commit()
    all_inventory = session.query(ModelInventory)\
        .order_by(ModelInventory.shelved_stock).all()
    print("~~~ INVENTORY: RESTOCKED / SHELF - after session.commit()")
    all_inventory[0].print()

    print("starter inventory:")
    Inventory.print_stock_status(session)

    # for prod in Const.products:
    #     vals = session.query(
    #         func.sum(ModelInventory.shelved_stock))\
    #         .filter(ModelInventory.grp_id == prod.grp_id).one()
    #     # print(vals, vals[0])
    #     assert(vals is not None and vals[0] > 0)


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
    print("store open = {}, shift change = {}"
          .format(Const.StoreStatus.OPEN, Const.StoreStatus.SHIFT_CHANGE))


if __name__ == '__main__':
    run()
