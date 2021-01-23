from sqlalchemy import func
from models import ModelInventory
from models.Base import check_session, check_object_status
from models.Cart import ModelCart
from models.Product import ModelProduct, ModelCategory
from sqlalchemy import (Column, Integer, Float)
import random
from datetime import date
from enum import IntEnum
from tabulate import tabulate

from models import (Base,
                    provide_session,
                    ModelRevenue,
                    ModelQtime)
# CATEGORY_COUNT, SHOPPER_MIN, SHOPPER_MAX
from models import Const, log, delta
from models import Cart

# random.seed(time.clock())
CLOCK = Const.CLOCK


class Status(IntEnum):
    INERT = 0
    SHOPPING = 1
    QUEUE_READY = 2
    QUEUEING = 3
    CHECKOUT = 4
    DONE = 5


def random_start_min():
    return random.randint(0, 59)


def random_quota():
    return random.randint(Const.SHOPPER_MIN, Const.SHOPPER_MAX)


class ModelShopper(Base):
    __tablename__ = "tbl_shopper"

    id = Column(Integer, primary_key=True)
    start_min = Column(Integer, default=random_start_min)
    browse_mins = Column(Integer, default=None)
    quota = Column(Integer, default=random_quota)
    cart_count = Column(Integer, default=0)
    lane = Column(Integer, default=None)
    qtime = Column(Integer, default=None)
    status = Column(Integer, default=Status.INERT)
    total = Column(Float, default=0.00)

    def print(self):
        stat_string = ""
        if self.status == 0:
            stat_string = "INERT"
        elif self.status == 1:
            stat_string = "SHOPPING"
        elif self.status == 2:
            stat_string = "QUEUING"
        elif self.status == 3:
            stat_string = "CHECKOUT"
        elif self.status == 4:
            stat_string = "DONE"

        browse, cart, ln, qt = self.browse_mins, self.cart_count, self.lane, self.qtime
        if self.browse_mins is None:
            browse = "NONE"
        if self.cart_count is None:
            cart = "NONE"
        if self.lane is None:
            ln = "NONE"
        if self.qtime is None:
            qt = "NONE"

        print("<shopper_{}_{}: start={}, browse={}, quota={}, cart_count={}, lane={}, qtime={}, total={}>"
              .format(self.id, stat_string, self.start_min,
                      browse, self.quota, cart,
                      ln, qt, self.total))

    def __repr__(self):
        stat_string = ""
        if self.status == 0:
            stat_string = "INERT"
        elif self.status == 1:
            stat_string = "SHOPPING"
        elif self.status == 2:
            stat_string = "QUEUING"
        elif self.status == 3:
            stat_string = "CHECKOUT"
        elif self.status == 4:
            stat_string = "DONE"

        return [self.id,
                stat_string,
                self.start_min,
                self.browse_mins,
                self.quota,
                self.cart_count,
                "n/a",
                # self.lane,
                self.qtime,
                self.total]

    def get_status(self):
        return self.status

    def set_status(self, stat):
        self.status = stat

    def reset_browse(self):
        if Const.CLOSING_SOON:
            self.browse_mins = random.randint(1, 3)
        else:
            self.browse_mins = random.randint(2, 5)

    def increment_qtime(self, session=None):
        self.qtime += 1
        session.commit()

    def set_lane(self, lid):
        if self.lane is None:
            self.qtime = 0
        self.lane = lid

    @provide_session
    def step(self, prod_lst, inv_lookup, session=None):
        CLOCK = Const.CLOCK
        prev, prev_id = None, None

        if self.status == Status.INERT:
            if Const.CLOSED:
                # TODO: mark as delted
                pass
            elif CLOCK.minute == self.start_min:
                print("\tSTARTING TO SHOP!")
                self.status = Status.SHOPPING
                self.reset_browse()

        elif self.status == Status.SHOPPING:

            # done shopping
            if self.quota == 0:
                self.status = Status.QUEUE_READY
                self.qtime = 0

            # select grp or keep browsing
            else:
                if self.browse_mins == 1:
                    print("\tSELECTING NOW!")
                    assert(len(prod_lst) > 0 and len(inv_lookup) > 0)
  
                    grp_id = prod_lst.pop()
                    inv_lst = inv_lookup[grp_id - 1]

                    # # confirm successful update
                    # print("\n~~~BEFORE")
                    # print("\inv_lst (grp = ", grp_id, "):")
                    # for row in inv_lst:
                    #     print("\t" + row.__repr__())
                    # print("\inv_lookup[{}]:".format(grp_id))
                    # for row in inv_lookup[grp_id - 1]:
                    #     print("\t" + row.__repr__())

                    while(inv_lst[0].shelved_stock == 0):
                        inv = inv_lst.pop(0)
                        inv_lst.append(inv)
                    assert(inv_lst[0].shelved_stock != 0)
                    inv = inv_lst[0]
                    prev_shelf = inv.shelved_stock
                    Cart.add_inv_item(self.id, inv, session)
                    assert(inv.shelved_stock == prev_shelf - 1)
                    prev, prev_id = inv.shelved_stock, inv.id

                    # update inv_lst
                    # inv_lst[0] = inv
                    # inv_lookup[grp_id - 1] = inv_lst

                    # # confirm successful update
                    # print("\n~~~AFTER")
                    # print("\inv_lst (grp = ", grp_id, "):")
                    # for row in inv_lst:
                    #     print("\t" + row.__repr__())
                    # print("\inv_lookup[{}]:".format(grp_id))
                    # for row in inv_lookup[grp_id - 1]:
                    #     print("\t" + row.__repr__())
                    # exit(1)

                    # other shoper updates
                    self.quota -= 1
                    self.cart_count += 1
                    self.total += Const.products[grp_id - 1].get_price()
                    self.reset_browse()
                else:
                    self.browse_mins -= 1

        elif self.status == Status.DONE:
            today = date(CLOCK.year, CLOCK.month, CLOCK.day)

            rev = ModelRevenue(
                stamp=today,
                value=self.total)
            session.add(rev)

            qt = ModelQtime(
                lane=self.lane,
                stamp=today,
                time=self.qtime)
            session.add(qt)
        else:
            pass
        return self.status, prev, prev_id


def create(n, session=None):
    for i in range(n):
        s = ModelShopper()
        session.add(s)
    session.commit()


def print_active_shoppers(session=None):
    print("\t--- ACTIVE SHOPPERS --- ")
    count = session.query(func.count(ModelShopper.id), ModelShopper.status)\
        .group_by(ModelShopper.status)\
        .order_by(ModelShopper.status).all()
    shoppers = session.query(ModelShopper)\
        .filter(ModelShopper.status != Status.DONE,
                ModelShopper.status != Status.INERT,
                ModelShopper.status != Status.SHOPPING)\
        .order_by(ModelShopper.status).all()
    count = [sublist[0] for sublist in count]
    while len(count) < 6:
        count.append(0)
    print("COUNT: inert = {}, shopping = {}, qready = {}, queueing = {}, checkout = {}, done = {}"\
          .format(count[0], count[1], count[2], count[3], count[4], count[5]))
    for s in shoppers:
        s.print()
