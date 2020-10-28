from sqlalchemy import Column, Integer, func
from models import inventory
from models import Base, provide_session, ModelProduct


class ModelCart(Base):
    __tablename__ = "tbl_cart"

    id = Column(Integer, primary_key=True)
    shopper_id = Column(Integer)
    inventory_id = Column(Integer)
    grp_id = Column(Integer)

    @provide_session
    def __repr__(self, session):
        info = session.query(ModelProduct.name, ModelProduct.brand)\
            .filter(ModelProduct.grp_id == self.grp_id).one()
        return ("< item_%d: name=%s, brand=%s, inv_id=%s, grp_id=%s >" %
                (self.id, info.name, info.brand,
                    self.inventory_id, self.grp_id))


@provide_session
def print_cart(sid, session=None):
    tot = get_total(sid, session)
    size = get_size(sid, session)
    cart = session.query(ModelCart)\
        .filter(ModelProduct.shopper_id == sid).all()
    print("CART_%d: total=%d, size=%d" % (sid, tot, size))
    for item in cart:
        print("\t", item.__repr__())


@provide_session
def add_item(sid, grp_id, session=None):
    inv_id = inventory.select_inv(grp_id, session)
    row = ModelCart(
        shopper_id=sid,
        inventory_id=inv_id
    )
    session.commit(row)


@provide_session
def scan_n(sid, n, session=None):
    cart_list = session.query(ModelCart)\
        .filter(ModelCart.shopper_id == sid)\
        .order_by(ModelCart.id).all()
    for row in cart_list:
        if n == 0:
            break
        session.delete(row)
        n -= 1
    session.commit()


@provide_session
def get_size(sid, session=None):
    size = session.query(func.count(ModelCart))\
        .filter(ModelCart.shopper_id == sid).one()[0]
    if size is None:
        size = 0
    return size


@provide_session
def get_total(sid, session=None):
    cart = session.query(ModelCart)\
        .filter(ModelCart.shopper_id == sid).all()
    total = 0
    for item in cart:
        product = session.query(ModelProduct)\
            .filter(ModelProduct.grp_id == item.grp_id).one()
        total += product.get_price()
    return total
