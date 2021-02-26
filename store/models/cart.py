from models.Base import check_session, check_object_status
from sqlalchemy import Column, Integer, func, Boolean
from sqlalchemy.sql.expression import false
from tabulate import tabulate
from models import Inventory, Const, log, delta, StockType
from models import Base, provide_session, ModelProduct, Session


class ModelCart(Base):
    __tablename__ = "tbl_cart"

    id = Column(Integer, primary_key=True)
    shopper_id = Column(Integer)
    inventory_id = Column(Integer)
    grp_id = Column(Integer)
    deleted = Column(Boolean, default=False)

    def print(self):
        print("<item_{}: sid={}, inv={}, grp={}>"
              .format(self.id,
                      self.shopper_id,
                      self.inventory_id,
                      self.grp_id))


def print_cart(sid, session=None):
    # collect cart info
    tot = get_total(sid, session)
    size = get_size(sid, session)
    cart = session.query(ModelCart)\
        .filter(ModelCart.shopper_id == sid).all()

    table = []
    for item in cart:
        table.append(item.__repr__(session))

    # print cart
    print("\n---------- CART_{}: total = {}, size = {} ------------"
          .format(sid, tot, size))
    # print("\n-------------------- CART_{} -------------------".format(sid))
    headers = ["sid",
               "item_no",
               "product",
               "inv_id",
               "name",
               "brand"]
    print(tabulate(table, headers, tablefmt="fancy_grid"))


def add_inv_item(sid, inv, session=None):
    row = ModelCart(
        shopper_id=sid,
        inventory_id=inv.id,
        grp_id=inv.grp_id
    )
    session.add(row)
    inv.increment(StockType.CART, 1)
    inv.decrement(StockType.SHELF, 1)


def scan_n(cart, n):
    for inv in cart["inv"]:
        if n == 0:
            break
        inv.deleted = True
        n -= 1
        cart["count"] -= 1


def get_size(sid, session=None):
    count = session.query(func.count(ModelCart.id))\
        .filter(ModelCart.shopper_id == sid).one_or_none()
    if count:
        return count[0]
    else:
        return 0


def get_total(sid, session=None):
    cart = session.query(ModelCart)\
        .filter(ModelCart.shopper_id == sid).all()

    total = 0
    if cart:
        for item in cart:
            product = Const.products[item.grp_id-1]
            # product = session.query(ModelProduct)\
            #     .filter(ModelProduct.grp_id == item.grp_id).one()
            total += product.get_price()
    return round(total, 2)
