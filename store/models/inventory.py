from sqlalchemy import Column, Integer, Date, distinct
import sys
from datetime import timedelta, date
from sqlalchemy.sql import func
from math import floor
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
    available = Column(Date)  # truck -> back storage
    sell_by = Column(Date)

    def _repr_(self):
        return (
            "<Inventory(id={}, grp_id = {}, shelved={}, back={}, "
            "pending={}, available={}, sell_by={})>"
            .format(
                self.id, self.grp_id, self.shelved_stock,
                self.back_stock, self.pending, self.available,
                self.sell_by
                    )
                )

    @provide_session
    def decrement_n(self, n, session=None):
        if self.shelved_stock >= n:
            self.shelved_stock -= n
            if self.shelved_stock == 0 and self.back_stock == 0:
                row = session.query(ModelInventory)\
                    .filter(ModelInventory.id == self.id).one()
                session.delete(row)
        else:
            sys.exit("decrement_n(): invalid n")
        session.commit()


# ------------------------------------------- Inventory-Affiliated Functions
@provide_session
def select_inv(grp_id, session=None):
    """
    Select an item <grp_id> from the store's shelved stock with soonest
    sell_by date. For a given sell_by date, sort by fewest shelved & back
    stock.
    :returns:
        Returns the inventory_id of the selected stock
    """
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    inv = session.query(ModelInventory)\
        .filter(ModelInventory.grp_id == grp_id)\
        .filter(ModelInventory.shelved_stock > 0)\
        .filter(ModelInventory.sell_by >= today)\
        .order_by(ModelInventory.sell_by.asc())\
        .order_by(ModelInventory.back_stock.asc())\
        .order_by(ModelInventory.shelved_stock.asc()).first()
    inv.decrement_n(1)
    return inv.id


@provide_session
def toss(grp_id, n, session=None):
    """
    Remove up to <n> items of expired (shelved and back) stock for a particular
    product <grp_id>. This can span mutiple inventory entries.
    :param int grp_id:
        The prodcut to removed.
    :param int n:
        number of items to remove
    """
    # list of inventory entries with sell_by date matching current
    # or previous CLOCK date, sorted in order of earliest date
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    inv_list = session.query(ModelInventory)\
        .filter(ModelInventory.grp_id == grp_id)\
        .filter(ModelInventory.sell_by <= today)\
        .order_by(ModelInventory.sell_by.asc()).all()

    if inv_list[0] is None: # CHECK
        sys.exit("Fatal: request to toss() nonexistent inventory")

    for inv in inv_list:
        print("n = %d, len(inv_list) = %d" % (n, len(inv_list)))
        if n == 0:
            print("departing")
            break
        print(
            "\tid = %d, shelved = %d, back = %d | n = %d" %
            (inv.id, inv.shelved_stock, inv.back_stock, n)
            )
        if inv.shelved_stock >= n:
            print("\teliminating part of shelved stock")
            inv.shelved_stock -= n
            n = 0
        else:
            n = n - inv.shelved_stock
            inv.shelved_stock = 0
            if inv.back_stock >= n:
                print("\teliminating all shelved + partial back")
                inv.back_stock -= n
                n = 0
            else:
                print("\teliminating all shelved + all back stock --> deleting entry")
                n = n - inv.back_stock
                inv.back_stock = 0
                session.delete(inv)
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


@provide_session
def restock(grp_id, n, session=None):
    '''
    Transfer up to <n> items from back_stock to shelved_stock for a
    product <grp_id> in order of soonest sell_by date.
    :Constraint: can't exceed max_shelved_stock for that product.
    '''
    # product's inventory entries that have stock in back, ordered by
    # sell_by date
    product = session.query(ModelProduct)\
        .filter(ModelProduct.grp_id == grp_id).one()
    inv_list = session.query(ModelInventory)\
        .filter(ModelInventory.grp_id == grp_id)\
        .filter(ModelInventory.shelved_stock < product.get_sublot_quantity())\
        .filter(ModelInventory.back_stock > 0)\
        .order_by(ModelInventory.sell_by).all()  # TEST

    shelf_space = available_shelf_space(grp_id)
    if n > shelf_space:
        n = shelf_space

    # for each inv, transfer up to n items from back to shelved stock
    for inv in inv_list:
        if inv.back_stock >= n:
            inv.shelved_stock += n
            inv.back_stock -= n
            n = 0
        else:
            n = n - inv.back_stock
            inv.shelved_stock += inv.back_stock
            inv.back_stock = 0
        session.commit()
        if n == 0:
            break
        print("\t", inv._repr_())


# unloads one lot of product into back storage
@provide_session
def unload(grp_id, session=None):
    print("-------------------------------- UNLOAD --------------------------------")
    # START: unloaded is not working properly
    product = session.query(ModelProduct)\
        .filter(ModelProduct.grp_id == grp_id).first()
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    inv_list = session.query(ModelInventory)\
        .filter(ModelInventory.grp_id == grp_id)\
        .filter(ModelInventory.available == today)\
        .filter(ModelInventory.pending > 0).all()
    print("unload grp = ", grp_id)
    for row in inv_list:
        print("\t", row._repr_())

    space = available_back_space(grp_id)
    q = product.get_lot_quantity()
    print("space = ", space, ", q = ", q)

    # set limiting factor (storage space or lot quantity)
    if space < q:
        q = space

    # unlaod at most max(space, q)
    for inv in inv_list:
        if q <= 0:  # unloaded max amt for one time step
            break

        # unload items
        if q > inv.pending:
            inv.back_stock += inv.pending
            q -= inv.pending
            inv.pending = 0
            print("NEW_%d: back=%d, pending=%d, q=%d" % (
                    inv.id, inv.back_stock, inv.pending, q))
        else:
            inv.back_stock += q
            inv.pending -= q
            q = 0
            print("NEW_%d: back=%d, pending=%d, q=%d" % (
                inv.id, inv.back_stock, inv.pending, q))
        session.commit()
        inv_obj = session.query(ModelInventory)\
            .filter(ModelInventory.id == inv.id).one()
        print(inv_obj._repr_())
    return


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
    order_cost = 0
    for prod in products:
        inv_stock = session.query(
            func.sum(ModelInventory.shelved_stock),
            func.sum(ModelInventory.back_stock)
            ).filter(ModelInventory.grp_id == prod.grp_id).one()

        SHELVED = 0
        BACK = 1
        if inv_stock[SHELVED] is None and inv_stock[BACK] is None:
            total_stock = 0
        elif inv_stock[SHELVED] is None:
            total_stock = inv_stock[BACK]
        elif inv_stock[BACK] is None:
            total_stock = inv_stock[SHELVED]
        else:
            total_stock = inv_stock[SHELVED] + inv_stock[BACK]
 
        if total_stock < prod.order_threshold:
            # order enough stock to have up to order_threshold total items
            # do not violate storage constraints
            shortage = prod.order_threshold - total_stock
            space = available_back_space(prod.grp_id)
            delta = min(shortage, space)
            money = order(prod, delta)
            order_cost += money

    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    c = ModelCost(stamp=today, value=order_cost, ctype="labor")
    session.add(c)
    session.commit()


@provide_session
def order(product, quantity, session=None):
    """ Return the number of sublots required for an order of at most
        quantity items.
    :Constraint: can't excceed the available storage space in inventory
        (max_back_stock)
    :Constraint: can't exceed quantity
    :param int quantity:
        Number of individual products for reorder
    :param int grp_id:
        The grp_id of the product to reorder
    :returns:
        Returns the number of sublots to order at most n individual items, 
        without overshooting.
    :rtype:
        int
    """
    if quantity <= 0:
        sys.exit("order(): invalid quantity")

    back_stock = available_back_space(product.grp_id)
    space = product.max_back_stock - back_stock
    if space < quantity:
        num_lots = floor(quantity / product.lot_quantity)
    else:
        num_lots = floor(space / product.lot_quantity)

    sublots = num_lots * product.sublots
    create_pending(product.grp_id, sublots)
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
    inv_list = []
    products = session.query(ModelProduct).all()
    for prod in products:
        current_shelved_stock = session.query(
            func.sum(ModelInventory.shelved_stock))\
            .filter(ModelInventory.grp_id == prod.grp_id).one()[0]

        if current_shelved_stock is None:
            current_shelved_stock = 0

        if current_shelved_stock < prod.restock_threshold:
            inv_list.append(prod.grp_id)

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
