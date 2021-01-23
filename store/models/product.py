from sqlalchemy import Column, Integer, String, Float, Enum
from sqlalchemy.sql import func, null
from sqlalchemy.sql.sqltypes import Date
import random
from datetime import datetime, timedelta, date
from math import ceil
from enum import IntEnum
import random
from tabulate import tabulate

from models import Const, Base, provide_session  # REVIEW: clock access


CLOCK = Const.CLOCK


def make_sell_by():
    return round(random.triangular(14, 365, 30))


class ModelCategory(Base):
    __tablename__ = "tbl_category"

    id = Column(Integer, primary_key=True)
    sell_by = Column(Integer, default=make_sell_by)
    count = Column(Integer, default=0)  # number of products in this category

    # FIX: come back to this
    # START >>> category is source of sell_by dates,
    # initialize all categories before initializing products
    def print(self):
        print("<cat_{}: sell_by: {}, count: {}"
              .format(self.id, self.sell_by, self.count))

    def __repr__(self):
        return "<cat_{}: sell_by: {}, count: {}"\
            .format(self.id, self.sell_by, self.count)

    def product_count(self):
        return self.count


class ModelSold(Base):
    __tablename__ = "tbl_sold"

    id = Column(Integer, primary_key=True)
    grp_id = Column(Integer)
    date = Column(Date)
    sold = Column(Integer)


# CHECK: enum database type class works?
class PRICE(IntEnum):
    regular = 0
    sale = 1


class ModelProduct(Base):
    __tablename__ = "tbl_product"

    # basic info
    grp_id = Column(Integer, primary_key=True)
    # name = Column(String(600))
    category = Column(Integer)
    max_shelved_stock = Column(Integer)
    max_back_stock = Column(Integer)
    restock_threshold = Column(Integer)

    # selection info
    regular_price = Column(Float(precision=2))
    sale_price = Column(Float(precision=2))
    price_status = Column(Enum(PRICE))

    # order info
    lot_price = Column(Float(precision=2))
    lot_quantity = Column(Integer)
    sublots = Column(Integer)
    sublot_quantity = Column(Integer)
    sell_by_days = Column(Integer)
    order_threshold = Column(Integer)
    order_amount = Column(Integer)

    def print(self):
        print("<grp_{}: cat={}, max_shelf={}, max_back={}, restock_t={}, price={}, sale={}, p_stat={}, lot_p={}, lot_q={}, sublots={}, sublot_q={}, order_t={}, order_q={}, sell={}"
        .format(self.grp_id, self.category, self.max_shelved_stock, self.max_back_stock, self.restock_threshold, self.regular_price, self.sale_price,
                self.price_status, self.lot_price, self.lot_quantity, self.sublots, self.sublot_quantity, self.order_threshold, self.order_amount, self.sell_by_days))

    # -------------------------------------------- getters and setters
    def get_lot_quantity(self):
        return self.lot_quantity

    def get_num_sublots(self):
        return self.sublots

    def get_sublot_quantity(self):
        return self.sublot_quantity

    def get_price(self):
        if self.price_status == PRICE.regular:
            return self.regular_price
        else:
            return self.sale_price

    def get_max_back_stock(self):
        return self.max_back_stock

    def get_max_shelved_stock(self):
        return self.max_shelved_stock

    def get_order_threshold(self):
        return self.order_threshold

    def get_restock_threshold(self):
        return self.restock_threshold

    def set_sale(self):
        self.price_status = PRICE.sale

    def set_regular(self):
        self.price_status = PRICE.regular

    def set_order_threshold(self, session=None):
        '''
        Sets the product ordering threshold and amount to order.
        truck takes 2 days to arrive, so need to order when back stock
        falls below 2 days worth of product. Order 4 days worth of product
        or max_back stock, whichever is less.
        '''
        today = datetime(CLOCK.year, CLOCK.month, CLOCK.day, 0, 0)
        filter_after = today - timedelta(days=4)
        avg = session.query(func.avg(ModelSold.sold).label("average"))\
            .filter(ModelSold.grp_id == self.grp_id)\
            .filter(ModelSold.date > filter_after).one()
        if avg.average is not None:
            self.order_threshold = (2 * round(avg.average))
            self.order_amount = min((4 * round(avg.average)),
                                    self.max_back_stock)

    def get_sell_by(self):
        noise = timedelta(days=random.randint(-2, 2))
        today = date(CLOCK.year, CLOCK.month, CLOCK.day)
        return today + noise + timedelta(days=self.sell_by_days)

    # -------------------------------------------- Other functions
    def setup(self, cat):
        self.category = cat
        self.lot_quantity = random.randint(4, 100) * 100

        if self.lot_quantity > 500:
            self.sublot_quantity = 100
        else:
            self.sublot_quantity = random.choice([10, 20, 50])

        self.sublots = self.lot_quantity / self.sublot_quantity

        self.max_shelved_stock = self.lot_quantity * 2
        self.max_back_stock = self.lot_quantity * 8
        self.order_threshold = round(self.max_back_stock/2)
        self.restock_threshold = round((self.max_shelved_stock / 3) * 2)
        self.order_amount = None

        self.price_status = PRICE.regular
        self.regular_price = round(random.uniform(1, 22), 2)
        self.sale_price = round(
            (self.regular_price - (0.08 * self.regular_price)), 2)
        self.lot_price = round(
            (self.regular_price
             + random.choice([0.01, 0.02, 0.03, 0.04, 0.05]))
            * self.lot_quantity, 2)

        self.sell_by_days = round(random.uniform(14, 90))

        # return self.row_order_info()

    def row_order_info(self):
        return [self.grp_id,
                self.max_back_stock,
                self.order_threshold,
                self.max_shelved_stock,
                self.restock_threshold,
                self.lot_quantity,
                ]

    def row_basic_info(self, session=None):
        return [self.grp_id,
                self.category,
                self.price_status,
                self.regular_price,
                self.sale_price,
                self.popularity,
                self.popularity_delta
                ]


# return a list of n randomly selected grp_id
def select_grp(n):
    prod_lst = []
    for i in range(n):
        cid = random.randint(1, Const.CATEGORY_COUNT)
        c = Const.categories[cid - 1]
        start_index = (c.id - 1) * Const.PRODUCTS_PER_CATEGORY
        end_index = c.id * Const.PRODUCTS_PER_CATEGORY - 1
        r = random.randint(start_index, end_index)
        p = Const.products[r]
        prod_lst.append(p.grp_id)
    return prod_lst
