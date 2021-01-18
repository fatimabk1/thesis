from models.Base import check_session, check_object_status
from sqlalchemy import Column, Integer, func
from tabulate import tabulate
from models import Inventory
from models import Base, provide_session, ModelProduct, Session


class ModelCart(Base):
    __tablename__ = "tbl_cart"

    id = Column(Integer, primary_key=True)
    shopper_id = Column(Integer)
    inventory_id = Column(Integer)
    grp_id = Column(Integer)

    def print(self):
        print("<item_{}: sid={}, inv={}, grp={}>"
              .format(self.id,
                      self.shopper_id,
                      self.inventory_id,
                      self.grp_id))

    def __repr__(self, session=None):
        prod = session.query(ModelProduct)\
            .filter(ModelProduct.grp_id == self.grp_id).one()
        return [self.shopper_id,
                self.id,
                self.grp_id,
                self.inventory_id,
                prod.name,
                prod.brand]


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


def add_item(sid, grp_id, session=None):
    inv_id = Inventory.select_inv(grp_id, session)
    row = ModelCart(
        shopper_id=sid,
        inventory_id=inv_id,
        grp_id=grp_id
    )
    session.add(row)
    session.commit()


def scan_n(sid, n, session=None):
    # print_cart(sid, session)
    cart_list = session.query(ModelCart)\
        .filter(ModelCart.shopper_id == sid)\
        .order_by(ModelCart.id).all()

    for row in cart_list:
        if n == 0:
            break
        session.delete(row)
        n -= 1
        session.commit()
    return n


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
            product = session.query(ModelProduct)\
                .filter(ModelProduct.grp_id == item.grp_id).one()
            total += product.get_price()
    return round(total, 2)
