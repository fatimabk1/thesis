from sqlalchemy import Column, Integer, Date, distinct, select
import sys
from enum import IntEnum
from datetime import timedelta, date
from sqlalchemy.sql import func
from math import floor
from models import Base, provide_session, ModelCost, ModelProduct, Const

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
        return [self.id,
                self.grp_id,
                self.cart_stock,
                self.shelved_stock,
                self.back_stock,
                self.pending_stock,
                self.available,
                self.sell_by]

    def decrement(self, type, n, session):
        if type == StockType.PENDING:
            self.pending_stock -= n
        elif type == StockType.BACK:
            self.back_stock -= n
        elif type == StockType.SHELF:
            self.shelved_stock -= n
        else:
            assert(type == StockType.CART)
            self.cart_stock -= n

        # delete inv if done
        if (self.cart_stock == 0 and self.shelved_stock == 0
                and self.back_stock == 0 and self.pending_stock == 0):
            print("~~~CLEAN UP ON AISLE 5~~~")
            print("deleting inv_", self.id)
            self.print()
            row = session.query(ModelInventory)\
                .filter(ModelInventory.id == self.id).one()
            session.delete(row)
            session.commit()

    def increment(self, type, n, session):
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
def select_inv(grp_id, session=None):  # FIX
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    inv = session.query(ModelInventory)\
        .filter(ModelInventory.grp_id == grp_id)\
        .filter(ModelInventory.shelved_stock > 0)\
        .filter(ModelInventory.sell_by >= today)\
        .order_by(ModelInventory.sell_by)\
        .order_by(ModelInventory.shelved_stock)\
        .order_by(ModelInventory.back_stock).first()

    if inv is None:
        print("FATAL Inventory.select_inv(): no inventory fits criteria")
        print("grp = ", grp_id)
        inv = session.query(ModelInventory)\
            .filter(ModelInventory.grp_id == grp_id)\
            .order_by(ModelInventory.sell_by)\
            .order_by(ModelInventory.shelved_stock).all()
        for i in inv:
            i.print()
        sys.exit(1)

    inv.decrement(StockType.SHELF, 1, session)
    inv.increment(StockType.CART, 1, session)
    return inv.id


# Returns the max number of items that can be added to shelves.
def available_shelf_space(grp_id, session=None):
    product = session.query(ModelProduct)\
        .filter(ModelProduct.grp_id == grp_id).one()
    max_shelved = product.get_max_shelved_stock()
    current_shelved = session.query(func.sum(ModelInventory.shelved_stock))\
        .filter(ModelInventory.grp_id == grp_id).first()[0]
    if current_shelved is None:
        return max_shelved
    else:
        return max_shelved - current_shelved


# Returns the max number of items that can be added to back storage
def available_back_space(grp_id, session=None):
    product = session.query(ModelProduct)\
        .filter(ModelProduct.grp_id == grp_id).one()
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
        inv = ModelInventory(
            grp_id=product.grp_id,
            cart_stock=0,
            shelved_stock=0,
            back_stock=0,
            pending_stock=product.get_sublot_quantity(),
            available=(today + timedelta(days=Const.TRUCK_DAYS)),
            sell_by=product.get_sell_by()
        )
        session.add(inv)
    session.commit()


def order_inventory(session=None):
    products = session.query(ModelProduct).all()
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    order_cost = 0

    for prod in products:
        print("\tordering inventory --> grp ", prod.grp_id)
        back_space = available_back_space(prod.grp_id, session)
        back_stock = prod.max_back_stock - back_space
        if back_space > prod.order_threshold:
            amount = (prod.order_amount
                      or (prod.order_threshold * 1.5 - back_stock))
            money = order(prod, amount, session)
            order_cost += money
            c = ModelCost(stamp=today, value=order_cost, ctype="stock")
            session.add(c)
    session.commit()


def order(product, quantity, session=None):
    lot_q = product.get_lot_quantity()
    num_lots = int(floor(quantity / lot_q))
    assert(num_lots >= 2)
    sublots = int(num_lots * product.get_num_sublots())
    create_pending(product, sublots, session)
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
    products = session.query(ModelProduct.grp_id).all()
    for prod in products:
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
    products = session.query(ModelProduct).all()
    for prod in products:
        shelf_space = available_shelf_space(prod.grp_id, session)
        back_stock = session.query(
            func.sum(ModelInventory.back_stock))\
            .filter(ModelInventory.grp_id == prod.grp_id).one()[0]
        shelved = prod.get_max_shelved_stock() - shelf_space
        if (shelved <= prod.get_restock_threshold()):
            t = [(prod.grp_id, min(back_stock, shelf_space), "RESTOCK"),
                 shelved]
            restockme.append(t)
    restockme.sort(key=lambda x: x[1])
    restockme = [sublist[0] for sublist in restockme]
    return restockme


# returns a list of tuples in the format (grp, quantity, action)
def unload_list(session=None):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    products = session.query(ModelProduct).all()
    unloadme = []
    for prod in products:
        quantity = session.query(func.sum(ModelInventory.pending_stock))\
            .filter(ModelInventory.grp_id == prod.grp_id)\
            .filter(ModelInventory.available == today)\
            .filter(ModelInventory.pending_stock > 0).one()[0]
        if quantity:
            quantity = int(quantity / prod.get_lot_quantity())
            t = (prod.grp_id, quantity, "UNLOAD")
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
