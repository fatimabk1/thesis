from store.models import cart
from sqlalchemy import Column, Integer, Date, distinct
import sys
from datetime import timedelta, date
from sqlalchemy.sql import func
from math import floor
from tabulate import tabulate
from models import Base, provide_session, ModelCost, ModelProduct, const

CLOCK = const.CLOCK
TRUCK_DAYS = const.TRUCK_DAYS


class ModelInventory(Base):
    __tablename__ = "tbl_inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grp_id = Column(Integer)
    shelved_stock = Column(Integer)
    back_stock = Column(Integer)
    pending = Column(Integer)
    cart_stock = Column(Integer)
    available = Column(Date)  # truck -> back storage
    sell_by = Column(Date)

    def __repr__(self):
        return [self.id,
                self.grp_id,
                self.shelved_stock,
                self.back_stock,
                self.pending,
                self.cart_stock,
                self.available,
                self.sell_by]

    @provide_session
    def decrement_pending(self, n, session=None):
        assert(self.pending >= n), "decrement_pending(): invalid n"
        self.pending -= n
        self.back_stock -= n
        session.commit()

    @provide_session
    def decrement_back(self, n, session=None):
        assert(self.back_stock >= n), "decrement_back(): invalid n"
        self.back_stock -= n
        self.shelved_stock -= n
        session.commit()

    @provide_session
    def decrement_shelved(self, n, session=None):
        assert(self.shelved_stock >= n), "decrement_shelved(): invalid n"
        self.shelved_stock -= n
        self.cart_stock += n
        session.commit()

    @provide_session
    def decrement_cart(self, n, session=None):
        assert(self.cart_stock >= n), "decrement_cart(): invalid n"
        self.cart_stock -= n
        if (self.cart_stock == 0 and self.shelved_stock == 0 and self.back_stock == 0):
            row = session.query(ModelInventory)\
                .filter(ModelInventory.id == self.id).one()
            session.delete(row)
        session.commit()


# ------------------------------------------- Inventory-Affiliated Functions
@provide_session
def select_inv(grp_id, session=None):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    inv = session.query(ModelInventory)\
        .filter(ModelInventory.grp_id == grp_id)\
        .filter(ModelInventory.shelved_stock > 0)\
        .filter(ModelInventory.sell_by >= today)\
        .order_by(ModelInventory.sell_by.asc())\
        .order_by(ModelInventory.back_stock.asc())\
        .order_by(ModelInventory.shelved_stock.asc()).first()
    if inv is None:
        sys.exit("FATAL select_inv(): no inventory fits criteria")
    inv.decrement_shelved(1, session)
    return inv.id


@provide_session
def toss(grp_id, n, session=None):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    inv_list = session.query(ModelInventory)\
        .filter(ModelInventory.grp_id == grp_id)\
        .filter(ModelInventory.sell_by <= today)\
        .order_by(ModelInventory.sell_by.asc()).all()

    assert(inv_list[0] is not None), "toss(): nonexistent inventory"

    for inv in inv_list:
        if n == 0:
            break
        else:
            q = min(inv.shelved_stock, n)
            inv.decrement_shelved(q, session)
            n -= q
    session.commit()


# Returns the max number of items that can be added to shelves.
@provide_session
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
@provide_session
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


# START HERE >>>>>>>>> cleaning up functions :)
# --> use min to set limiting factor use new decrement_xxx() functions for
# restock/unload/toss/create_pending -- this could use an increment function()
# NEXT >>>>>>>>>>>>>>> double check that inventory still works
# NEXT NEXT >>>>>>>>>> WHEN_2_ORDER vs QUANTITY_2_ORDER
# for order and restock lists
@provide_session
def restock(grp_id, n, session=None):
    product = session.query(ModelProduct)\
        .filter(ModelProduct.grp_id == grp_id).one()
    inv_list = session.query(ModelInventory)\
        .filter(ModelInventory.grp_id == grp_id)\
        .filter(ModelInventory.shelved_stock < product.get_sublot_quantity())\
        .filter(ModelInventory.back_stock > 0)\
        .order_by(ModelInventory.sell_by)\
        .order_by(ModelInventory.id).all()

    shelf_space = available_shelf_space(grp_id, session)
    n = min(n, shelf_space)

    # for each inv, transfer min(n, shelf_space) from back to shelved stock
    for inv in inv_list:
        if n == 0:
            break
        else:
            q = min(inv.back_stock, n)
            inv.decrement_back(q, session)
            n -= q
    session.commit()


# unloads one lot of product into back storage
@provide_session
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
        .filter(ModelInventory.pending > 0)\
        .order_by(ModelInventory.id).all()

    # unload
    q = min(space, q)
    for inv in inv_list:
        if q == 0:
            break
        elif q > inv.pending:
            inv.back_stock += inv.pending
            q -= inv.pending
            inv.pending = 0
        else:
            inv.back_stock += q
            inv.pending -= q
            q = 0
    session.commit()


# creates a set of pending inventory entries for ordered stock
@provide_session
def create_pending(grp_id, sublots, session=None):
    product = session.query(ModelProduct)\
        .filter(ModelProduct.grp_id == grp_id).one()
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    for i in range(sublots):
        inv = ModelInventory(
            grp_id=grp_id,
            shelved_stock=0,
            back_stock=0,
            pending=product.get_sublot_quantity(),
            available=(today + timedelta(days=TRUCK_DAYS)),
            sell_by=product.get_sell_by()
        )
        session.add(inv)
    session.commit()


@provide_session
def order_inventory(session=None):
    products = session.query(ModelProduct).all()
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    order_cost = 0
    table = []

    for prod in products:
        quantity = prod.max_back_stock - prod.order_threshold
        money = order(prod, quantity, table, session)
        order_cost += money
        c = ModelCost(stamp=today, value=order_cost, ctype="labor")
        session.add(c)
    session.commit()

    # print inventory order
    print(" -------------------------- ORDER --------------------------")
    headers = ["product", "total_quantity", "# pending inv", "inv_quantity"]
    print(tabulate(table, headers, tablefmt="fancy_grid"))


@provide_session
def order(product, quantity, table, session=None):
    lot_q = product.get_lot_quantity()
    num_lots = floor(quantity / lot_q)
    assert(num_lots >= 2)
    sublots = num_lots * product.get_num_sublots()
    table.append([product.grp_id,
                  num_lots * lot_q,
                  sublots,
                  floor(lot_q/sublots)])
    create_pending(product.grp_id, sublots, session)
    return product.lot_price * num_lots


@provide_session
def toss_list(session=None):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    lst = session.query(distinct(ModelInventory.grp_id))\
        .filter(ModelInventory.sell_by <= today).all()
    inv_lst = []
    for row in lst:
        if row[0] is not None:
            inv_lst.append(row[0])
    return inv_lst


@provide_session
def restock_list(session=None):
    table = []
    inv_list = []
    products = session.query(ModelProduct).all()
    for prod in products:
        current_shelved_stock = session.query(
            func.sum(ModelInventory.shelved_stock))\
            .filter(ModelInventory.grp_id == prod.grp_id).one()[0]

        if current_shelved_stock is None:
            current_shelved_stock = 0

        if current_shelved_stock < prod.restock_threshold:
            table.append([prod.grp_id,
                         current_shelved_stock,
                         prod.restock_threshold - current_shelved_stock])
            inv_list.append(prod.grp_id)

    # print restocked
    # print("\n-------------------- RESTOCKED ------------------- ")
    # headers = ["product", "shelved", "remaining"]
    # print(tabulate(table, headers, tablefmt="fancy_grid"))
    return inv_list


@provide_session
def unload_list(session=None):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    lst = session.query(ModelInventory.grp_id)\
        .filter(ModelInventory.available == today)\
        .filter(ModelInventory.pending > 0).distinct()
    inv_list = []
    for row in lst:
        if row[0] is not None:
            inv_list.append(row[0])
    return inv_list
