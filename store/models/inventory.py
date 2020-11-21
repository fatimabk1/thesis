from sqlalchemy import Column, Integer, Date, distinct, select
import sys
from enum import IntEnum
from datetime import timedelta, date
from sqlalchemy.sql import func
from math import floor
from tabulate import tabulate
from models import Base, provide_session, ModelCost, ModelProduct, Const

CLOCK = Const.CLOCK
TRUCK_DAYS = Const.TRUCK_DAYS


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
        self.clean_up()

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
        self.clean_up()

    @provide_session  # CHECK that values persist
    def clean_up(self, session=None):
        if (self.cart_stock == 0
                and self.shelved_stock == 0
                and self.back_stock == 0):
            row = session.query(ModelInventory)\
                .filter(ModelInventory.id == self.id).one()
            session.delete(row)
        session.commit()


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
        sys.exit("FATAL select_inv(): no inventory fits criteria")

    inv.decrement(StockType.SHELF, 1)
    inv.increment(StockType.CART, 1)
    return inv.id


def toss(grp_id, q, session=None):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    inv_list = session.query(ModelInventory)\
        .filter(ModelInventory.grp_id == grp_id)\
        .filter(ModelInventory.sell_by <= today)\
        .order_by(ModelInventory.sell_by.asc()).all()

    assert(inv_list[0] is not None), "toss(): nonexistent inventory"

    for inv in inv_list:
        inv.print()
        if q == 0:
            break
        else:
            amount = min(inv.shelved_stock, q)
            inv.decrement(StockType.SHELF, amount)
            q -= amount
    session.commit()


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


def restock(grp_id, q, session=None):
    product = session.query(ModelProduct)\
        .filter(ModelProduct.grp_id == grp_id).one()
    inv_list = session.query(ModelInventory)\
        .filter(ModelInventory.grp_id == grp_id)\
        .filter(ModelInventory.shelved_stock < product.get_sublot_quantity())\
        .filter(ModelInventory.back_stock > 0)\
        .order_by(ModelInventory.sell_by)\
        .order_by(ModelInventory.id).all()

    shelf_space = available_shelf_space(grp_id, session)
    q = min(q, shelf_space)

    # transfer from back to shelved stock
    for inv in inv_list:
        if q == 0:
            break
        else:
            amount = min(inv.back_stock, q)
            inv.decrement(StockType.BACK, amount)
            inv.increment(StockType.SHELF, amount)
            q -= amount
        session.commit()


# unloads one lot of product into back storage
def unload(grp_id, session=None):
    # list of inventory to unload
    product = session.query(ModelProduct)\
        .filter(ModelProduct.grp_id == grp_id).first()
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    space = available_back_space(grp_id, session)
    q = product.get_lot_quantity()
    inv_list = session.query(ModelInventory)\
        .filter(ModelInventory.grp_id == grp_id)\
        .filter(ModelInventory.available == today)\
        .filter(ModelInventory.pending_stock > 0)\
        .order_by(ModelInventory.id).all()

    # unload
    q = min(space, q)
    for inv in inv_list:
        if q == 0:
            break
        else:
            amount = min(q, inv.pending_stock)
            inv.decrement(StockType.PENDING, amount)
            inv.increment(StockType.BACK, amount)
            q -= amount
    session.commit()


# creates a set of pending inventory entries for ordered stock
def create_pending(grp_id, sublots, session=None):
    product = session.query(ModelProduct)\
        .filter(ModelProduct.grp_id == grp_id).one()
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    for i in range(sublots):
        inv = ModelInventory(
            grp_id=grp_id,
            cart_stock=0,
            shelved_stock=0,
            back_stock=0,
            pending_stock=product.get_sublot_quantity(),
            available=(today + timedelta(days=TRUCK_DAYS)),
            sell_by=product.get_sell_by()
        )
        session.add(inv)
    session.commit()


def order_inventory(session=None):
    products = session.query(ModelProduct).all()
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    order_cost = 0

    for prod in products:
        quantity = prod.max_back_stock - prod.order_threshold
        money = order(prod, quantity, session)
        order_cost += money
        c = ModelCost(stamp=today, value=order_cost, ctype="labor")
        session.add(c)
    session.commit()


def order(product, quantity, session=None):
    lot_q = product.get_lot_quantity()
    num_lots = floor(quantity / lot_q)
    assert(num_lots >= 2)
    sublots = num_lots * product.get_num_sublots()
    create_pending(product.grp_id, sublots, session)
    return product.lot_price * num_lots


def toss_list(session=None):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    lst = session.query(distinct(ModelInventory.grp_id))\
        .filter(ModelInventory.sell_by <= today).all()
    inv_lst = [item for sublist in lst for item in sublist]
    return inv_lst


def restock_list(session=None):
    # table = []
    inv_list = []
    products = session.query(ModelProduct).all()
    for prod in products:
        current_shelved_stock = session.query(
            func.sum(ModelInventory.shelved_stock))\
            .filter(ModelInventory.grp_id == prod.grp_id).one_or_none()

        if current_shelved_stock:
            current_shelved_stock = current_shelved_stock[0]
        else:
            current_shelved_stock = 0

        if current_shelved_stock < prod.restock_threshold:
            inv_list.append(prod.grp_id)

    return inv_list


def unload_list(session=None):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    lst = session.query(ModelInventory.grp_id)\
        .filter(ModelInventory.available == today)\
        .filter(ModelInventory.pending_stock > 0).distinct()
    inv_list = [item for sublist in lst for item in sublist]
    return inv_list
