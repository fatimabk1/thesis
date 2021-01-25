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
    # cart_stock = Column(Integer, default=None)
    shelved_stock = Column(Integer, default=None)
    back_stock = Column(Integer, default=None)
    pending_stock = Column(Integer, default=None)
    available = Column(Date, default=None)  # truck -> back storage
    sell_by = Column(Date, default=None)

    def print(self):
        print("<inv_{}: grp={}, shelved={}, back={}, pending={}, available={}, sell_by{}>"
              .format((self.id), self.grp_id,
                      self.shelved_stock, self.back_stock, self.pending_stock,
                      self.available, self.sell_by))

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
        # else:
        #     assert(type == StockType.CART)
        #     self.cart_stock -= n

        # FIXME: no deletions --> IS_DELETED
        if (self.shelved_stock == 0
                and self.back_stock == 0 and self.pending_stock == 0):
            pass

    def increment(self, type, n):
        if type == StockType.PENDING:
            self.pending_stock += n
        elif type == StockType.BACK:
            self.back_stock += n
        elif type == StockType.SHELF:
            self.shelved_stock += n
        # else:
        #     assert(type == StockType.CART)
        #     self.cart_stock += n


# ------------------------------------------- Inventory-Affiliated Functions

# returns a grp_id indexed list of inventories[n]
@provide_session
def pull_inventory(n, session=None):  # FIX
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    t = log()
    # START >>>>
    # 1. Fix so that lookup has n inventories for each product
    all_qualified_inventory = session.query(ModelInventory)\
        .filter(ModelInventory.shelved_stock > 0)\
        .filter(ModelInventory.sell_by >= today)\
        .order_by(ModelInventory.grp_id,
                  ModelInventory.sell_by,
                  ModelInventory.shelved_stock,
                  ModelInventory.back_stock).all()
    delta("\t\t\tqualified inventory, db query", t)
    if all_qualified_inventory is None:
        return {}

    t = log()
    lookup = {}
    for inv in all_qualified_inventory:
        if inv.grp_id not in lookup:
            lookup[inv.grp_id] = []

        if len(lookup[inv.grp_id]) < n:
            lookup[inv.grp_id].append(inv)
    delta("\t\t\tlookup dictionary", t)
    delta("\t\t\t\t\tinv_lst query, limit({})".format(n), t)
    return lookup


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
            # cart_stock=0,
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


def unload(inv, emp_q, quantity):
    # print("\t\t\tunload params: inv.pending = {}, quantity = {}, emp_Q = {}"
    #       .format(inv.pending_stock, quantity, emp_q))
    q = min(emp_q,
            inv.pending_stock,
            quantity)
    # print("\t\t\tq = ", q)
    inv.increment(StockType.BACK, q)
    inv.decrement(StockType.PENDING, q)
    # emp_q -= q
    # quantity -= q
    # return emp_q, quantity
    return q


def restock(inv, emp_q, quantity):
    q = min(emp_q,
            inv.back_stock,
            quantity)
    inv.increment(StockType.SHELF, q)
    inv.decrement(StockType.BACK, q)
    # emp_q -= q
    # quantity -= q
    # return emp_q, quantity
    return q


def toss_shelf(inv, emp_q, quantity):
    q = min(emp_q,
            inv.shelved_stock,
            quantity)
    inv.decremnt(StockType.SHELF, q)
    # emp_q -= q
    # quantity -= q
    # return emp_q, quantity
    return q


def toss_back(inv, emp_q, quantity):
    q = min(emp_q,
            inv.back_stock,
            quantity)
    inv.decremnt(StockType.BACK, q)
    # emp_q -= q
    # quantity -= q
    # return emp_q, quantity
    return q


def toss_pending(inv, emp_q, quantity):
    q = min(emp_q,
            inv.pending_Stock,
            quantity)
    inv.decremnt(StockType.PENDING, q)
    # emp_q -= q
    # quantity -= q
    # return emp_q, quantity
    return q


def manage_inventory(task, lookup, emp_q):
    print("MANAGE INVENTORY: TASK = ", task)
    completed = []
    for grp_id in lookup:
        if emp_q == 0:
            break

        if task == Const.TASK_UNLOAD:
            lot_q = Const.products[grp_id - 1].get_lot_quantity()
            emp_q *= lot_q

        lst = lookup[grp_id]["inventory"]
        quantity = lookup[grp_id]["quantity"]
        if quantity == 0:
            completed.append(grp_id)
            continue
        t = log()
        for inv in lst:
            q = None

            if task == Const.TASK_RESTOCK:
                q = restock(inv, emp_q, quantity)
                emp_q -= q
                quantity -= q
                if quantity == 0 or emp_q == 0:
                    break

            elif task == Const.TASK_TOSS:
                # toss shelved stock
                q = toss_shelf(inv, emp_q, quantity)
                emp_q -= q
                quantity -= q
                if quantity == 0 or emp_q == 0:
                    break

                # toss back stock
                q = toss_back(inv, emp_q, quantity)
                emp_q -= q
                quantity -= q
                if quantity == 0 or emp_q == 0:
                    break

                # toss pending stock
                q = toss_pending(inv, emp_q, quantity)
                emp_q -= q
                quantity -= q
                if quantity == 0 or emp_q == 0:
                    break

                # NOTE: check if empty inv --> mark IS_DELETED
            elif task == Const.TASK_UNLOAD:
                q = unload(inv, emp_q, quantity)
                emp_q -= q
                quantity -= q
                if quantity == 0 or emp_q == 0:
                    break
            else:
                print("ERROR -- INVALID TASK")
                exit(3)

            # TODO: mark inv as is_deleted if necc

        lookup[grp_id]["quantity"] = quantity
        delta("\t\t\tone grp", t)
        if task == Const.TASK_UNLOAD:
            lot_q = Const.products[grp_id - 1].get_lot_quantity()
            emp_q = int(emp_q / lot_q)

        if quantity > 0 and len(lst) == 0:
            print("quantity = ", quantity, ", len(lst) = ", len(lst))
            print('ERROR: Inventory.inventory_manage() --> quantity>0 but no inventory available')
            exit(2)

    return emp_q, completed


# returns a list of tuples in the format (grp, quantity, action)
def toss_list(session=None):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    t = log()
    qualified_inv = session.query(ModelInventory)\
        .filter(ModelInventory.sell_by < today)\
        .order_by(ModelInventory.grp_id).all()
    delta("\t\t\t-qualifed inventory", t)

    t = log()
    lookup = {}
    for inv in qualified_inv:
        if inv.grp_id not in lookup:
            lookup[inv.grp_id] = {"quantity": 0,
                                  "inventory": []}
        lookup[inv.grp_id]["inventory"].append(inv)
        q = inv.shelved_stock + inv.back_stock + inv.pending_stock
        lookup[inv.grp_id]["quantity"] += q
    delta("\t\t\t-create lookup", t)

    return lookup


# returns a list of tuples in the format (grp, quantity, action)
def restock_list(session=None):
    # pull all inventory for products with sum(shelf) < restock_threshold
    t = log()
    all_qualified_products = session.query(
        ModelInventory.grp_id,
        func.sum(ModelInventory.shelved_stock),
        func.sum(ModelInventory.back_stock))\
        .group_by(ModelInventory.grp_id)\
        .order_by(ModelInventory.grp_id).all()
    assert(all_qualified_products is not None)
    delta("\t\t\t-qualified products", t)

    t = log()
    qualified_inventory = session.query(ModelInventory)\
        .filter(ModelInventory.back_stock > 0)\
        .order_by(ModelInventory.grp_id,
                  ModelInventory.sell_by,
                  ModelInventory.shelved_stock).all()
    assert(qualified_inventory is not None)
    delta("\t\t\t-qualified inventory", t)

    t = log()
    prod_lst = {}
    for item in all_qualified_products:
        if item[1] < Const.products[item[0] - 1].get_restock_threshold():
            # prod_lst[grp_id] = [sum(curr_shelf), min(max_shelf - curr_shelf, curr_back)]
            prod_lst[item[0]] = [item[1], min(item[2], Const.products[item[0] - 1]
                                 .get_max_shelved_stock() - item[1])]
    delta("\t\t\t-prod_lst dictionary", t)

    t = log()
    lookup = {}
    for inv in qualified_inventory:
        if inv.grp_id in prod_lst:
            if inv.grp_id not in lookup:
                lookup[inv.grp_id] = {"quantity": prod_lst[inv.grp_id][1],
                                      "inventory": []}

            if(inv.shelved_stock
               < Const.products[inv.grp_id - 1].get_max_shelved_stock()):
                lookup[inv.grp_id]["inventory"].append(inv)
    delta("\t\t\t-lookup dictionary", t)
    return lookup


# returns a list of tuples in the format (grp, quantity, action)
def unload_list(session=None):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    t = log()
    qualified_inv = session.query(ModelInventory)\
        .filter(ModelInventory.available == today)\
        .filter(ModelInventory.pending_stock > 0)\
        .order_by(ModelInventory.grp_id)\
        .order_by(ModelInventory.sell_by).all()
    delta("\t\t\t-qualified inventory", t)

    t = log()
    lookup = {}
    for inv in qualified_inv:
        if inv.grp_id not in lookup:
            lookup[inv.grp_id] = {"quantity": 0,
                                  "inventory": []}
        lookup[inv.grp_id]["inventory"].append(inv)
        lookup[inv.grp_id]["quantity"] += inv.pending_stock
    delta("\t\t\t-create lookup", t)

    # inv_lst = lookup[1]["inventory"]
    # for inv in inv_lst:
    #     inv.print()

    return lookup


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
