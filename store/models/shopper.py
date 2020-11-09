from models.base import check_session, check_object_status
from models.cart import ModelCart
from models.product import ModelProduct, ModelCategory
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
from models import constants as const
from models import cart

# random.seed(time.clock())
CLOCK = const.CLOCK


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
    return random.randint(const.SHOPPER_MIN, const.SHOPPER_MAX)


class ModelShopper(Base):
    __tablename__ = "tbl_shopper"

    id = Column(Integer, primary_key=True)
    start_min = Column(Integer, default=random_start_min)
    browse_mins = Column(Integer, default=None)
    quota = Column(Integer, default=random_quota)
    cart_count = Column(Integer, default=None)
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

        return ("<shopper_{}_{}: start={}, browse={}, quota={}, cart={}, lane={}, qtime={}, total={}>"
                .format(self.id, stat_string, self.start_min,
                        self.browse_mins, self.quota, self.cart_count,
                        self.lane, self.qtime, self.total))

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
        if const.EOD_FLAG is True:
            self.browse_mins = random.randint(1, 3)
        else:
            self.browse_mins = random.randint(2, 5)

    def select_grp(self, session=None):
        cat = random.randint(1, const.CATEGORY_COUNT)
        category = session.query(ModelCategory)\
            .filter(ModelCategory.id == cat).one()
        r = random.randint(1, category.product_count()) - 1
        prod = session.query(ModelProduct)\
            .filter(ModelProduct.category == cat).all()
        prod = prod[r]
        cart.add_item(self.id, prod.grp_id, session)
        # print("\t\tgrp = {}, cart = {}"
        #       .format(prod.grp_id, cart.get_size(self.id)))

    def increment_qtime(self, session=None):
        self.qtime += 1
        session.commit()

    def set_lane(self, lid):
        self.lane = lid


def create(n, session=None):
    for i in range(n):
        s = ModelShopper()
        session.add(s)
    session.commit()


@provide_session
def step(sid, CLOCK, session=None):
    shopper = session.query(ModelShopper)\
        .filter(ModelShopper.id == sid).one()

    if shopper.status == Status.INERT and CLOCK.minute == shopper.start_min:
        shopper.status = Status.SHOPPING
        shopper.reset_browse()

    elif shopper.status == Status.SHOPPING:

        # done shopping
        if shopper.quota == 0:
            shopper.total = cart.get_total(shopper.id, session)
            shopper.status = Status.QUEUE_READY
            shopper.qtime = 0

        # select grp or keep browsing
        else:
            if shopper.browse_mins == 1:
                shopper.select_grp(session)
                shopper.quota -= 1
                shopper.reset_browse()
            else:
                shopper.browse_mins -= 1

        shopper.cart_count = cart.get_size(shopper.id, session)

    elif shopper.status == Status.DONE:
        today = date(CLOCK.year, CLOCK.month, CLOCK.day)

        rev = ModelRevenue(
            stamp=today,
            value=shopper.total)
        session.add(rev)

        qt = ModelQtime(
            lane=shopper.lane,
            stamp=today,
            time=shopper.qtime)
        session.add(qt)

    else:
        pass

    session.commit()
    return shopper.status
