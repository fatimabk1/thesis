# a program to test the product.py file
from models.base import provide_session
from datetime import date
from models.constants import CLOCK
from sqlalchemy import func
from models.product import ModelProduct
from models.inventory import ModelInventory, available_shelf_space,\
    order_inventory, restock_list, select, toss, available_back_space,\
    toss_list, unload_list, restock, unload, create_pending


# -------------------------------------------- Product
@provide_session
def print_product(grp_id, session=None):
    r = session.execute(
        "SELECT * FROM tbl_product WHERE grp_id=:p",
        {"p": grp_id})
    for row in r:
        keys = row.keys()
        vals = row.values()
        x = len(keys)
        for i in range(x):
            row = [keys[i], vals[i]]
            if row[0] is None:
                row[0] = "None"
            if row[1] is None:
                row[1] = "None"
            print("|||", "{: <20} {: <20} ".format(*row))


@provide_session
def test_product(session=None):
    products = session.query(ModelProduct).all()
    if products is None:
        print("nooooo prudcts lmaooo")
        exit(1)
    for prod in products:
        print("--------------------------------------------------")
        prod.setup()
        print_product(prod.grp_id)
        print("Possible Sell-By dates, today = ", CLOCK)
        print("\t", prod.generate_sell_by())
        print("\t", prod.generate_sell_by())
        print("\t", prod.generate_sell_by())
        print("\t", prod.generate_sell_by())
        print("\t", prod.generate_sell_by())
        print("\t", prod.generate_sell_by())
        print("sublot_q: ", prod.get_sublot_quantity())
        print("current price: ", prod.get_price())
        prod.set_sale()
        print("sale price: ", prod.get_price())
        prod.set_regular()
        print("regular price: ", prod.get_price())
        print("pop: ", prod.get_popularity())
        print("pop∆: ", prod.get_popularity_delta())
        print("None threshold: ", prod.threshold)
        prod.set_threshold()
        print("None-set threshold: ", prod.threshold)
        print("\t~~~DONZO~~~")
        exit(1)


@provide_session
def initialize(session=None):
    products = session.query(ModelProduct).all()
    for prod in products:
        prod.setup()


# -------------------------------------------- Inventory
@provide_session
def test_inventory(session=None):
    initialize()

    # select()
    inv_id = select(1)
    assert(inv_id == 4), "fail: select()"
    session.commit()

    # decrement_n() --------------------------------------------
    inv = session.query(ModelInventory)\
        .filter(ModelInventory.id == inv_id).one()
    before = inv.shelved_stock
    inv.decrement_n(1)
    after = inv.shelved_stock
    assert(before == after + 1), "fail: decrement_n()"

    # toss_list()   --------------------------------------------
    lst = toss_list()
    print("toss list: ", lst)
    assert(len(lst) == 1 and lst[0] == 3), "fail: toss_list()"

    # toss()        --------------------------------------------
    before = session.query(func.count(ModelInventory.id))\
        .filter(ModelInventory.grp_id == 3).one()
    toss(3, 33)
    after = session.query(func.count(ModelInventory.id))\
        .filter(ModelInventory.grp_id == 3).one()

    # create_pending() ------------------------------------------
    before = session.query(func.count(ModelInventory.id))\
        .filter(ModelInventory.grp_id == 5)\
        .filter(ModelInventory.pending > 0).one()
    create_pending(5, 6)
    after = session.query(func.count(ModelInventory.id))\
        .filter(ModelInventory.grp_id == 5)\
        .filter(ModelInventory.pending > 0).one()
    lst = session.query(ModelInventory)\
        .filter(ModelInventory.grp_id == 5).all()
    print("\nPending Test, grp 5 with 6 pending entries")
    for row in lst:
        print("\t", row._repr_())
    assert(before[0] == 0 and after[0] == 6), "fail: create_pending()"

    # order_inventory()
    order_inventory()
    order_lst = session.query(ModelInventory)\
        .filter(ModelInventory.pending > 0)\
        .order_by(ModelInventory.id).all()
    print("\nOrdered Inventory:")
    for row in order_lst:
        print("\t", row._repr_())

    # restock_list()
    restock_lst = restock_list()
    restock_lst.sort()
    print("\nRestock list: ", restock_lst)

    # unload_list()
    unload_lst = unload_list()
    unload_lst.sort()
    print("\nUnload list aka PENDING available today: ", unload_lst)
    for grp in unload_lst:
        inv = session.query(ModelInventory)\
            .filter(ModelInventory.grp_id == grp)\
            .filter(ModelInventory.pending > 0)\
            .order_by(ModelInventory.id).all()
        for entry in inv:
            print("\t", entry._repr_())

    # unload()
    # START: unload is not working
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    for grp in unload_lst:
        unload(grp)
        inv = session.query(ModelInventory)\
            .filter(ModelInventory.grp_id == grp)\
            .filter(ModelInventory.available == today)\
            .order_by(ModelInventory.id).all()
        print("\nUnloaded Inventory")
        for entry in inv:
            print("\t", entry._repr_())
        exit(1)

    # restock()
    # print("\nRestocked Inventory")
    # print("\tBEFORE---")
    # for grp in restock_lst:
    #     inv = session.query(ModelInventory)\
    #         .filter(ModelInventory.grp_id == grp)\
    #         .order_by(ModelInventory.id).all()
    #     print("\ngrp_id = ", grp)
    #     for entry in inv:
    #         print("\t", entry._repr_())
    # print("\tAFTER---")
    # for grp in restock_lst:
    #     print("\ngrp_id = ", grp)
    #     restock(grp, 50)


# -------------------------------------------- Cart


# -------------------------------------------- Shopper


if __name__ == "__main__":
    test_inventory()
