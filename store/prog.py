# a program to test the product.py file
from datetime import date, datetime, timedelta
from models.shopper import ModelPreference, ModelShopper
from models.inventory import available_back_space
from sqlalchemy import func
from models import const, ModelProduct, ModelInventory, ModelShopper,\
    order_inventory, restock_list, select_inv,\
    toss_list, unload_list, restock, unload, create_pending,\
    provide_session, Status
from models import cart

CLOCK = const.CLOCK


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

    # select_inv()
    inv_id = select_inv(1)
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
    # before = session.query(func.count(ModelInventory.id))\
    #     .filter(ModelInventory.grp_id == 3).one()
    # toss(3, 33)
    # after = session.query(func.count(ModelInventory.id))\
    #     .filter(ModelInventory.grp_id == 3).one()

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
    emptyl = []
    for each in lst:
        emptyl.append(each.id)
    print("\nPending Test, grp 5 with 6 pending entries")
    lst = emptyl.sort()
    print(lst)
    assert(before[0] == 0 and after[0] == 6), "fail: create_pending()"

    # order_inventory()
    order_inventory()
    lst = session.query(ModelInventory)\
        .filter(ModelInventory.pending > 0)\
        .order_by(ModelInventory.id).all()
    order_lst = []
    for each in lst:
        order_lst.append(each.id)
    order_lst.sort()
    print("\nOrdered Inventory:", order_lst)

    # restock_list()
    restock_lst = restock_list()
    restock_lst.sort()
    print("\nRestock list: ", restock_lst)

    # unload_list()
    unload_lst = unload_list()
    unload_lst.sort()
    print("\nUnload list aka PENDING available today: ", unload_lst)

    # unload()
    # START: unload is not working
    # today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    for grp in unload_lst:
        # space = available_back_space(grp)
        unload(grp)
        # product = session.query(ModelProduct)\
        #     .filter(ModelProduct.grp_id == grp).one()
        # inv_lst = session.query(ModelInventory.id)\
        #     .filter(ModelInventory.grp_id == grp)\
        #     .filter(ModelInventory.available == today)\
        #     .order_by(ModelInventory.id).all()
        # lst = []
        # for row in inv_lst:
        #     lst.append(row[0])
        # inv_lst = lst
        # print("\nUnloaded %d -- space=%d, max=%d, lot_q=%d" % (
        #     grp, space, product.max_back_stock, product.lot_quantity))
        # all_grp = session.query(ModelInventory)\
        #     .filter(ModelInventory.grp_id == grp)\
        #     .order_by(ModelInventory.id).all()
        # for inv in all_grp:
        #     if inv.id in inv_lst:
        #         print("\t", inv._repr_(), "-- NEW")
        #     else:
        #         print("\t", inv._repr_())

    # restock()
    print("\nRestocked Inventory")
    for grp in restock_lst:
        inv = session.query(ModelInventory)\
            .filter(ModelInventory.grp_id == grp)\
            .order_by(ModelInventory.id).all()
        restock(grp, 200)


# -------------------------------------------- Shopper & Cart
@provide_session
def test_shopper_cart(session=None):
    initialize()
    print("SHOPPER CREATE:")
    # create & __repr__
    for i in range(50):
        s = ModelShopper()
        session.add(s)
        print("\t", s.__repr__())
    session.commit()

    # set_status() & get_status()
    print("\nSET & GET STATUS:")
    group = session.query(ModelShopper).all()
    for shopper in group:
        assert(shopper.get_status() == Status.INERT)
        shopper.set_status(Status.SHOPPING)
    session.commit()
    group = session.query(ModelShopper).all()
    for shopper in group:
        assert(shopper.get_status() == Status.SHOPPING)
        print("\tstatus: ", shopper.__repr__())

    # reset_browse
    print("\nBROWSE_RESET:")
    sid = group[0].id
    group[0].reset_browse()
    session.commit()
    s = session.query(ModelShopper)\
        .filter(ModelShopper.id == sid).one()
    print("\treset: ", s.__repr__())
    s.reset_browse()
    session.commit()
    s = session.query(ModelShopper)\
        .filter(ModelShopper.id == sid).one()
    print("\treset: ", s.__repr__())
    s.reset_browse()
    session.commit()
    s = session.query(ModelShopper)\
        .filter(ModelShopper.id == sid).one()
    print("\treset: ", s.__repr__()) 

    # roll
    group = session.query(ModelShopper).all()
    for shopper in group:
        # confirm that roll works
        pref = shopper.roll(1, session)
        reg = pref.regular_roll
        sale = pref.sale_roll
        session.commit()
        pref_db = session.query(ModelPreference)\
            .filter(ModelPreference.id == pref.id).one()
        assert(reg == pref_db.regular_roll and sale == pref_db.sale_roll)

        # confirm that re-rolling does not change preference
        shopper.roll(1, session)
        session.commit()
        pref_db = session.query(ModelPreference)\
            .filter(ModelPreference.id == pref.id).one()
        assert(reg == pref_db.regular_roll and sale == pref_db.sale_roll)

    # select_grp
    group = session.query(ModelShopper).all()
    for shopper in group:
        for i in range(30):
            shopper.select_grp()
        session.commit()
        cart.print_cart(shopper.id, session)

    # scan_n
    group = session.query(ModelShopper).all()
    for shopper in group:
        cart.scan_n(shopper.id, 12, session)
        session.commit()
        cart.print_cart(shopper.id, session)

    # advance
    const.CLOCK = datetime(2019, 9, 15, 10, 0)
    for i in range(120):
        group = session.query(ModelShopper).all() 
        for shopper in group:
            shopper.advance(session)
            print("\t", shopper.__repr__())
            stat = shopper.get_status()
            if stat is Status.QUEUEING or stat is Status.CHECKOUT:
                shopper.set_status(Status.DONE)
            if stat is Status.DONE:
                session.delete(shopper)
        session.commit()
        const.CLOCK = const.CLOCK + timedelta(minutes=1)


if __name__ == "__main__":
    test_shopper_cart()
