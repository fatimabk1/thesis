from sqlalchemy import Column, Integer, Date, distinct, select
import sys
from enum import IntEnum
from datetime import timedelta, date
from sqlalchemy.sql import func
from math import floor
from models import Base, provide_session, ModelCost, ModelProduct, Const
from models import delta, log

CLOCK = Const.CLOCK  # CHECK that this changes across minutes


class StockType(IntEnum):
    PENDING = 0
    BACK = 1
    SHELF = 2
    CART = 3


class ModelInventory(Base):
    __tablename__ = "tbl_inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grp_id = Column(Integer, default=None)
    cart_stock = Column(Integer, default=None)
    shelved_stock = Column(Integer, default=None)
    back_stock = Column(Integer, default=None)
    pending_stock = Column(Integer, default=None)
    available = Column(Date, default=None)  # truck -> back storage
    sell_by = Column(Date, default=None)

    def print(self):
        print("<inv_{}: grp={}, cart={}, shelved={}, back={}, pending={}, available={}, sell_by{}>"
              .format((self.id), self.grp_id, self.cart_stock,
                      self.shelved_stock, self.back_stock, self.pending_stock,
                      self.available, self.sell_by))

    def __repr__(self):
        return("<inv_{}: grp={}, cart={}, shelved={}, back={}, pending={}, available={}, sell_by{}>"
              .format((self.id), self.grp_id, self.cart_stock,
                      self.shelved_stock, self.back_stock, self.pending_stock,
                      self.available, self.sell_by))

    def decrement(self, type, n):
        if type == StockType.PENDING:
            self.pending_stock -= n
        elif type == StockType.BACK:
            self.back_stock -= n
        elif type == StockType.SHELF:
            self.shelved_stock -= n
        else:
            assert(type == StockType.CART)
            self.cart_stock -= n

        # FIXME: no deletions --> IS_DELETED
        if (self.cart_stock == 0 and self.shelved_stock == 0
                and self.back_stock == 0 and self.pending_stock == 0):
            pass

    def increment(self, type, n):
        if type == StockType.PENDING:
            self.pending_stock += n
        elif type == StockType.BACK:
            self.back_stock += n
        elif type == StockType.SHELF:
            self.shelved_stock += n
        else:
            assert(type == StockType.CART)
            self.cart_stock += n


# ------------------------------------------- Inventory-Affiliated Functions

# returns a grp_id indexed list of inventories[n]
@provide_session
def pull_inventory(n, session=None):  # FIX
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    t = log()

    all_qualified_inventory = session.query(ModelInventory)\
        .filter(ModelInventory.shelved_stock > 0)\
        .filter(ModelInventory.sell_by >= today)\
        .order_by(ModelInventory.grp_id,
                  ModelInventory.sell_by,
                  ModelInventory.shelved_stock,
                  ModelInventory.back_stock).all()

    if all_qualified_inventory is None:
        return []

    lst = []
    sublist = []
    prev_grp = all_qualified_inventory[0].grp_id

    for inv in all_qualified_inventory:
        grp = inv.grp_id

        if grp == prev_grp:
            if len(sublist) < n:
                sublist.append(inv)
            else:
                continue
        else:
            lst.append(sublist)
            prev_grp = grp
            sublist = []
            sublist.append(inv)
    lst.append(sublist)

    # for i in range(len(lst)):
    #     print("\lst[{}]".format(i + 1))
    #     sublist = lst[i]
    #     for inv in sublist:
    #         print("\t"+inv.__repr__())

    delta("\t\t\t\t\tinv_lst query, limit({})".format(n), t)
    return lst


# Returns the max number of items that can be added to shelves.
def available_shelf_space(grp_id, session=None):
    product = Const.products[grp_id - 1]

    max_shelved = product.get_max_shelved_stock()
    current_shelved = session.query(func.sum(ModelInventory.shelved_stock))\
        .filter(ModelInventory.grp_id == grp_id).first()[0]
    if current_shelved is None:
        return max_shelved
    else:
        return max_shelved - current_shelved


# Returns the max number of items that can be added to back storage
def available_back_space(grp_id, session=None):
    product = Const.products[grp_id - 1]
    back_stock = session.query(func.sum(ModelInventory.back_stock))\
        .filter(ModelInventory.grp_id == grp_id).first()[0]
    max_back_stock = product.get_max_back_stock()
    if back_stock is None:
        return max_back_stock
    else:
        return max_back_stock - back_stock


# creates a set of pending inventory entries for ordered stock
def create_pending(product, sublots, session=None):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    for i in range(sublots):
        sell = product.get_sell_by()
        inv = ModelInventory(
            grp_id=product.grp_id,
            cart_stock=0,
            shelved_stock=0,
            back_stock=0,
            pending_stock=product.get_sublot_quantity(),
            available=(today + timedelta(days=Const.TRUCK_DAYS)),
            sell_by=sell
        )
        session.add(inv)
    session.commit()


def order_inventory(session=None):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    order_cost = 0

    start = log("\t\tLOOP_order inventory all products")
    for prod in Const.products:
        start_one = log("\t\tone_product")
        print("\tordering inventory --> grp ", prod.grp_id)
        t = log("\t\t\tback_space()")
        back_space = available_back_space(prod.grp_id, session)
        delta("\t\t\tback_space()", t)
        back_stock = prod.max_back_stock - back_space
        if back_space > prod.order_threshold:
            amount = (prod.order_amount
                      or (prod.order_threshold * 1.5 - back_stock))
            t = log("\t\t\torder()")
            money = order(prod, amount, session)
            delta("\t\t\torder()", t)
            order_cost += money
            c = ModelCost(stamp=today, value=order_cost, ctype="stock")
            session.add(c)
        delta("\t\tone_product", start_one)
    delta("\t\tLOOP_order inventory all products", start)
    t = log("\t\tcommiting inventory")
    session.commit()
    delta("\t\tcommitting inventory", t)


def order(product, quantity, session=None):
    lot_q = product.get_lot_quantity()
    num_lots = int(floor(quantity / lot_q))
    assert(num_lots >= 2)
    sublots = int(num_lots * product.get_num_sublots())
    t = log("\t\t\t\tcreate_pending()")
    create_pending(product, sublots, session)
    delta("\t\t\t\tcreate_pending()", t)
    return product.lot_price * num_lots


# returns updated q and emp_q
def restock(grp, q, emp_q, session=None):
    '''
    q is total quantity that needs to be restocked for grp
    emp_q is max amount that an employee can restock in one time step
    returns updated q, the remaining quantity for task completion
    returns updated emp_q, remaining quantity employee can restock
    '''
    product = session.query(ModelProduct)\
        .filter(ModelProduct.grp_id == grp).one()
    inv_list = session.query(ModelInventory)\
        .filter(ModelInventory.grp_id == grp)\
        .filter(ModelInventory.shelved_stock < product.get_sublot_quantity())\
        .filter(ModelInventory.back_stock > 0)\
        .order_by(ModelInventory.sell_by)\
        .order_by(ModelInventory.id).all()

    # pre_value = session.query(func.sum(ModelInventory.shelved_stock))\
    #     .filter(ModelInventory.grp_id == grp).one()[0]

    for inv in inv_list:
        amt = min(inv.back_stock, emp_q, q)
        inv.increment(StockType.SHELF, amt, session)
        inv.decrement(StockType.BACK, amt, session)
        q -= amt
        emp_q -= amt
        if emp_q == 0 or q == 0:  # employee or task finished
            break
    session.commit()

    # post_value = session.query(func.sum(ModelInventory.shelved_stock))\
    #     .filter(ModelInventory.grp_id == grp).one()[0]
    # print("pre shelved = {}, post shelved ={}, max_shelf = {}"
    #       .format(pre_value, post_value, product.get_max_shelved_stock()))
    # print("\tq = {}, emp_q = {}".format(q, emp_q))
    return q, emp_q


# returns updated q and emp_q
def toss(grp, q, emp_q, session=None):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)

    # toss inventory for a grp
    inv_list = session.query(ModelInventory)\
        .filter(ModelInventory.grp_id == grp)\
        .filter(ModelInventory.sell_by <= today)\
        .order_by(ModelInventory.sell_by.asc()).all()
    assert(inv_list[0] is not None), "toss(): nonexistent inventory"

    # toss inventory in record inv
    for inv in inv_list:
        inv.print()
        # toss expired shelved stock
        amt = min(emp_q, q, inv.shelved_stock)
        inv.decrement(StockType.SHELF, amt, session)
        emp_q -= amt
        q -= amt
        # toss expired back stock
        amt = min(emp_q, q, inv.back_stock)
        inv.decrement(StockType.BACK, amt, session)
        emp_q -= amt
        q -= amt
        # toss expired pending stock
        amt = min(emp_q, q, inv.pending_stock)
        inv.decrement(StockType.PENDING, amt, session)
        emp_q -= amt
        q -= amt

        if emp_q == 0 or q == 0:  # employee or task finished
            break

    session.commit()
    return q, emp_q


# returns updated q and emp_q
def unload(grp, q, emp_q, session=None):
    # list of inventory to unload
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    prod = session.query(ModelProduct)\
        .filter(ModelProduct.grp_id == grp).one()
    inv_list = session.query(ModelInventory)\
        .filter(ModelInventory.grp_id == grp)\
        .filter(ModelInventory.available == today)\
        .filter(ModelInventory.pending_stock > 0)\
        .order_by(ModelInventory.id).all()

    # unload
    # print(q)
    q = q * prod.get_lot_quantity()
    # print(q)
    for inv in inv_list:
        amt = min(q, emp_q, inv.pending_stock)
        inv.increment(StockType.BACK, amt, session)
        # print("\t\t--> back = ", inv.back_stock)
        inv.decrement(StockType.PENDING, amt, session)
        # print("\t\t    pending = ", inv.pending_stock)
        emp_q -= amt
        q -= amt
        if emp_q == 0 or q == 0:  # employee or task finished
            break
    session.commit()
    q = q / prod.get_lot_quantity()
    return q, emp_q


# returns a list of tuples in the format (grp, quantity, action)
def toss_list(session=None):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)

    tossme = []
    for prod in Const.products:
        lst = session.query(ModelInventory)\
            .filter(ModelInventory.grp_id == prod.grp_id)\
            .filter(ModelInventory.sell_by <= today).all()

        q = 0
        for inv in lst:
            q += (inv.shelved_stock + inv.back_stock + inv.pending_stock)
            if q == 0:
                inv.print()
        if q != 0:
            t = (prod.grp_id, q, "TOSS")
            tossme.append(t)
    return tossme


# returns a list of tuples in the format (grp, quantity, action)
def restock_list(session=None):
    restockme = []
    for prod in Const.products:
        shelf_space = available_shelf_space(prod.grp_id, session)
        # t = log()
        back_stock = session.query(
            func.sum(ModelInventory.back_stock))\
            .filter(ModelInventory.grp_id == prod.grp_id).one()[0]
        # delta("\t\t\tquery back_stock", t)
        if back_stock is None:
            # print("NO BACK STOCK YIIIIIIIKES... grp = ", prod.grp_id)
            continue
        shelved = prod.get_max_shelved_stock() - shelf_space
        if (shelved <= prod.get_restock_threshold()):
            t = [(prod.grp_id, min(back_stock, shelf_space), "RESTOCK"),
                 shelved]
            restockme.append(t)
    # FIXME: sort is time expensive. Can we skip this?
    t = log()
    restockme.sort(key=lambda x: x[1])
    delta("\t\t\tsort restockme[]", t)
    t = log()
    restockme = [sublist[0] for sublist in restockme]
    delta("\t\t\tflatten restockme[]", t)
    return restockme


# returns a list of tuples in the format (grp, quantity, action)
def unload_list(session=None):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    unloadme = []
    for prod in Const.products:
        # t = log()
        quantity = session.query(func.sum(ModelInventory.pending_stock))\
            .filter(ModelInventory.grp_id == prod.grp_id)\
            .filter(ModelInventory.available == today).one()[0]
        # delta("\t\t\tquery pending unloads", t)
        if quantity:
            quantity = int(quantity / prod.get_lot_quantity())
            t = (prod.grp_id, quantity, "UNLOAD")
            # print("~~~", t)
            unloadme.append(t)

    return unloadme


@provide_session
def print_stock_status(session=None):
    print("\t--- STOCK ---")
    products = session.query(ModelProduct).all()
    for prod in products:
        counts = session.query(
                func.sum(ModelInventory.shelved_stock),
                func.sum(ModelInventory.back_stock))\
            .filter(ModelInventory.grp_id == prod.grp_id).all()[0]
        print("GRP_{}: shelf={}, back={}"
              .format(prod.grp_id, counts[0], counts[1]))
