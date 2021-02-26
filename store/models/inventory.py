from sqlalchemy import Column, Integer, Date, Boolean
from sqlalchemy.sql.expression import false
import sys
import functools
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
    # cart_stock = Column(Integer, default=None)
    shelved_stock = Column(Integer, default=None)
    back_stock = Column(Integer, default=None)
    pending_stock = Column(Integer, default=None)
    available = Column(Date, default=None)  # truck -> back storage
    sell_by = Column(Date, default=None)
    deleted = Column(Boolean, default=False)

    def print(self):
        print("<inv_{}: grp={}, shelved={}, back={}, pending={}, available={}, sell_by={}, deleted={}>"
              .format((self.id), self.grp_id,
                      self.shelved_stock, self.back_stock, self.pending_stock,
                      self.available, self.sell_by, self.deleted))

    def __repr__(self):
        return("<inv_{}: grp={}, shelved={}, back={}, pending={}, available={}, sell_by{}>"
               .format((self.id), self.grp_id,
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
            print("ERROR: invalid stock type: ", type)
            exit(1)

        if (self.shelved_stock == 0
                and self.back_stock == 0
                and self.pending_stock == 0):
            self.deleted = True

    def increment(self, type, n):
        if type == StockType.PENDING:
            self.pending_stock += n
        elif type == StockType.BACK:
            self.back_stock += n
        elif type == StockType.SHELF:
            self.shelved_stock += n


# ------------------------------------------- Inventory-Affiliated Functions

# returns a dictionary {grp_id: inv_lst}, where inv_lst sorted by sell_by
@provide_session
def pull_inventory(session=None):  # FIX
    # today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    t = log()
    all_inventory = session.query(ModelInventory)\
        .order_by(ModelInventory.grp_id, ModelInventory.sell_by).all()
    delta("\t\t\tInventory.pull_inventory(): all_inventory", t)

    t = log()
    lookup = {}
    for inv in all_inventory:
        if inv.grp_id not in lookup:
            lookup[inv.grp_id] = []
        lookup[inv.grp_id].append(inv)
    delta("\t\t\tlookup dictionary", t)

    for grp in lookup:
        assert(len(lookup[grp]) > 0)

    return lookup


# creates a set of pending inventory entries for ordered stock
def create_pending(product, sublots, session):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    for i in range(sublots):
        sell = product.get_sell_by()
        inv = ModelInventory(
            grp_id=product.grp_id,
            shelved_stock=0,
            back_stock=0,
            pending_stock=product.get_sublot_quantity(),
            available=(today + timedelta(days=Const.TRUCK_DAYS)),
            sell_by=sell
        )
        session.add(inv)
    session.commit()


def order_inventory(session):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    order_cost = 0

    for prod in Const.products:
        t = log()
        print("\tordering inventory --> grp ", prod.grp_id)

        curr_back = Const.product_stats[prod.grp_id - 1]["back"]
        back_space = prod.max_back_stock - curr_back
        if back_space > prod.order_threshold:
            amount = (prod.order_amount
                      or (prod.order_threshold * 1.5 - curr_back))
            money = order(prod, amount, session)
            order_cost += money

        c = ModelCost(stamp=today, value=order_cost, ctype="stock")
        session.add(c)
        delta("\t\t\torder one product", t)
    session.commit()


def order(product, quantity, session):
    lot_q = product.get_lot_quantity()
    num_lots = int(floor(quantity / lot_q))
    assert(num_lots >= 2)
    sublots = int(num_lots * product.get_num_sublots())
    create_pending(product, sublots, session)

    # update product_stats
    total_q = num_lots * lot_q
    Const.product_stats[product.grp_id - 1]["pending"] += total_q
    return product.lot_price * num_lots


# ---------------------------------------------- update all inv for a grp

def mass_restock(data, emp_q):
    delta = 0
    while(data["quantity"] > 0 and delta != emp_q):
        inv = data["inventory"].pop(0)
        q = min(emp_q,
                inv.back_stock,
                data["quantity"])
        inv.increment(StockType.SHELF, q)
        inv.decrement(StockType.BACK, q)
        data["quantity"] -= q
        delta += q
        if inv.back_stock > 0:
            data["inventory"].insert(0, inv)
        else:
            data["inventory"].append(inv)
    return delta


def mass_toss(data, emp_q):
    delta = 0
    while(data["quantity"] > 0 and delta != emp_q):
        inv = data["inventory"].pop()

        # toss expired on shelf
        q = min(emp_q, inv.shelved_stock, data["quantity"])
        inv.decremnt(StockType.SHELF, q)
        data["quantity"] -= q
        delta += q
        Const.product_stats[inv.grp_id]["shelf"] -= q

        # toss expired in back
        if(data["quantity"] > 0 and delta != emp_q):
            q = min(emp_q, inv.back_stock, data["quantity"])
            inv.decrement(StockType.BACK, q)
            data["quantity"] -= q
            delta += q
            Const.product_stats[inv.grp_id]["back"] -= q

            # toss expired in pending / on truck
            if(data["quantity"] > 0 and delta != emp_q):
                q = min(emp_q, inv.pending_stock, data["quantity"])
                inv.decrement(StockType.PENDING, q)
                data["quantity"] -= q
                delta += q
                Const.product_stats[inv.grp_id]["pending"] -= q

        if data["quantity"] > 0:
            data["inventory"].insert(0, inv)
        else:
            data["inventory"].append(inv)
    return delta


# data = {"quantity": #, "inv": [inv, inv, inv,...]}
def mass_unload(data, emp_q):
    delta = 0
    while(data["quantity"] > 0 and delta != emp_q):
        inv = data["inventory"].pop()
        # print("\n\t\t", inv.__repr__())
        q = min(emp_q,
                inv.pending_stock,
                data["quantity"])
        inv.increment(StockType.BACK, q)
        inv.decrement(StockType.PENDING, q)
        data["quantity"] -= q
        delta += q
        if data["quantity"] > 0:
            data["inventory"].insert(0, inv)
        else:
            data["inventory"].append(inv)
        # print("\t\t--->", inv.__repr__())
    return delta


# ---------------------------------------------- update all grp for a task
def dispatch(task, lookup, emp_q):
    keys = list(lookup.keys())
    for grp in keys:
        t = log()
        if emp_q == 0:
            return

        if lookup[grp]["quantity"] == 0:
            continue

        if task == Const.TASK_UNLOAD:
            print("\tunloading grp ", grp)
            prod = Const.products[grp - 1]
            # emp_q --> # of lots an emp can unload
            emp_q = emp_q * prod.get_lot_quantity()
            diff = mass_unload(lookup[grp], emp_q)

            Const.product_stats[grp - 1]["pending"] -= diff
            Const.product_stats[grp - 1]["back"] += diff
            emp_q -= diff
            emp_q = int(emp_q / prod.get_lot_quantity())
        elif task == Const.TASK_RESTOCK:
            diff = mass_restock(lookup[grp], emp_q)
            Const.product_stats[grp - 1]["back"] -= diff
            Const.product_stats[grp - 1]["shelf"] += diff
            emp_q -= diff
        else:
            assert(task == Const.TASK_TOSS)
            # print("\ttossing grp ", grp)
            diff = mass_toss(lookup[grp], emp_q)
            emp_q -= diff

        delta("\t\t\tdispatch one grp", t)


# ---------------------------------------------- pull task lists
# returns a dictionary of grp: {quantity, inv_lst}
# toss inventory w/sell_by date > today
def toss_list(inv_lookup):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    lookup = {}
    for grp_id in inv_lookup:
        inv_lst = [inv for inv in inv_lookup[grp_id]
                   if inv.deleted is False
                   and inv.sell_by < today]
        quantity_reduce = (lambda x: x.shelved_stock
                           + x.back_stock + x.pending_stock)
        quantity = functools.reduce(quantity_reduce, inv_lst, 0)
        if quantity != 0:
            lookup[grp_id] = {"quantity": quantity, "inventory": inv_lst}
    return lookup


# returns a dictionary of grp: {quantity, inv_lst}
# restock all inv where total shelf_stock < restock_threshold
# until shelf filled or back stock is used up
def restock_list(inv_lookup):
    lookup = {}
    for grp_id in inv_lookup:
        prod = Const.products[grp_id - 1]
        curr_shelf = Const.product_stats[grp_id-1]["shelf"]
        curr_back = Const.product_stats[grp_id-1]["back"]

        if curr_shelf < prod.get_restock_threshold():
            inv_lst = [inv for inv in inv_lookup[grp_id]
                       if inv.deleted is False
                       and inv.back_stock > 0]
            inv_lst.sort(key=lambda x: x.sell_by)
            assert(len(inv_lst) > 0), "restock_list(): no inventory"
            quantity = min(prod.get_max_shelved_stock() - curr_shelf,
                           curr_back)
            lookup[grp_id] = {"quantity": quantity, "inventory": inv_lst}

    return lookup

    # >>>>> NEXT:
    # 2. inv_lst is None in Shopper.step() line 156
    # 3. make max # of shoppers at start of program:
    #   > reset at start of day
    #   > release x shopper at each hour
    #   > add attribute for released or not


# returns a dictionary of grp: {quantity, inv_lst}
# where inv is available today, pending_stock > 0 
# sorted by sell_by
def unload_list(inv_lookup):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    lookup = {}
    for grp_id in inv_lookup:
        inv_lst = [inv for inv in inv_lookup[grp_id]
                   if inv.deleted is False
                   and inv.available == today
                   and inv.pending_stock > 0]
        total_pending = sum(inv.pending_stock for inv in inv_lst)
        if total_pending > 0:
            lookup[grp_id] = {"quantity": total_pending, "inventory": inv_lst}
            print("GRP_{}: pending={}".format(grp_id, total_pending))
    return lookup


@provide_session
def print_stock_status(session):
    print("\n\t--- STOCK ---")
    stats = session.query(
        ModelInventory.grp_id,
        func.sum(ModelInventory.shelved_stock),
        func.sum(ModelInventory.back_stock))\
        .filter(ModelInventory.deleted == False)\
        .group_by(ModelInventory.grp_id).all()
    assert(stats is not None)
    for row in stats:
        print("GRP_{}: shelf={}, back={}"
              .format(row[0], row[1], row[2]))
