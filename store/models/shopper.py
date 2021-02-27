from sqlalchemy import func
from sqlalchemy.sql.sqltypes import Boolean
from sqlalchemy.sql.expression import false
from models import ModelInventory, beepy
from models.Base import check_session, check_object_status
from models.Cart import ModelCart
from models.Product import ModelProduct, ModelCategory
from sqlalchemy import Column, Integer, Float, Boolean
import random
from datetime import date
from enum import IntEnum
from tabulate import tabulate
from models import (Base,
                    provide_session,
                    ModelRevenue,
                    ModelQtime)
# CATEGORY_COUNT, SHOPPER_MIN, SHOPPER_MAX
from models import Const, log, delta, StoreStatus
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
    deleted = Column(Boolean, default=False)

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
        if stat == Status.DONE:
            self.deleted = True

    def reset_browse(self, t_step):
        if t_step >= StoreStatus.CLOSING_SOON:
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
    def step(self, t_step, inv_lookup, session=None):
        # print("inside step")
        CLOCK = Const.CLOCK

        if self.status == Status.INERT:
            if t_step >= StoreStatus.CLOSED:
                self.deleted = True

            elif CLOCK.minute == self.start_min:
                # print("\tSTARTING TO SHOP!")
                self.status = Status.SHOPPING
                self.reset_browse(t_step)

        elif self.status == Status.SHOPPING:
            # done shopping
            if self.quota == 0:
                self.status = Status.QUEUE_READY
                self.qtime = 0

            # select grp or keep browsing
            else:
                if self.browse_mins == 1:
                    shopper_select = log()
                    grp_id = random.randint(1, Const.PRODUCT_COUNT)
                    assert(grp_id in inv_lookup)
                    t = log()
                    inv_lst = [inv for inv in inv_lookup[grp_id]
                               if inv.deleted is False
                               and inv.shelved_stock > 0]
                    delta("shopper select inv, list comprehension", t)

                    t = log()
                    inv_lst.sort(key=lambda x: x.sell_by)
                    delta("\t\t\t\tsort inv_lst", t)

                    while(inv_lst[0].shelved_stock == 0):
                        inv_lst[0].print()
                        grp_id = random.randint(1, Const.PRODUCT_COUNT)
                        inv_lst = inv_lookup[grp_id]
                        beepy.beep(sound=3)
                        exit(0)
                    assert(inv_lst[0].shelved_stock != 0), "grp {} has no shelf stock".format(grp_id)
                    inv = inv_lst[0]
                    prev_shelf = inv.shelved_stock
                    t = log()
                    Cart.add_inv_item(self.id, inv, session)
                    delta("\t\t\tCart.add_inv_item()", t)
                    assert(inv.shelved_stock == prev_shelf - 1)

                    # other shoper updates
                    self.quota -= 1
                    self.cart_count += 1
                    self.total += Const.products[grp_id - 1].get_price()
                    self.reset_browse(t_step)
                    Const.product_stats[grp_id - 1]["shelf"] -= 1
                    delta("\t\t\tShopper select for status=1", shopper_select)
                else:
                    self.browse_mins -= 1

        elif self.status == Status.DONE:
            self.deleted = True
            today = date(CLOCK.year, CLOCK.month, CLOCK.day)
            rev = ModelRevenue(stamp=today, value=self.total)
            session.add(rev)
            qt = ModelQtime(lane=self.lane, stamp=today, time=self.qtime)
            session.add(qt)
        else:
            pass
        # session.flush()
        return self.status


def create(n, session=None):
    for i in range(n):
        s = ModelShopper()
        session.add(s)


def print_active_shoppers(session=None):
    print("\t--- ACTIVE SHOPPERS --- ")
    count = session.query(func.count(ModelShopper.id), ModelShopper.status)\
        .filter(ModelShopper.deleted == False)\
        .group_by(ModelShopper.status)\
        .order_by(ModelShopper.status).all()

    shoppers = session.query(ModelShopper).all()
    shoppers = [shopper
                for shopper in shoppers
                if shopper.deleted is False
                and (shopper.status == Status.QUEUEING
                     or shopper.status == Status.SHOPPING)]
    shoppers.sort(key=lambda x: x.status)
        # .filter(ModelShopper.deleted is False)\
        # .filter(ModelShopper.status != Status.DONE,
        #         ModelShopper.status != Status.INERT,
        #         ModelShopper.status != Status.SHOPPING)\
        # .order_by(ModelShopper.status).all()

    count = [sublist[0] for sublist in count]
    while len(count) < 6:
        count.append(0)
    not_del = 0
    for quantity in count:
        not_del += quantity
    total = (Const.HOURS_PER_DAY - 2) * Const.SHOPPER_ADD

    print("COUNT: inert = {}, shop = {}, qready = {}, queue = {}, check = {}, done = {}, del = {}\n"\
          .format(count[0], count[1], count[2], count[3], count[4], count[5], total - not_del))
    for s in shoppers:
        s.print()
