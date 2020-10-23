from sqlalchemy import Column, Integer, String, Float, Enum
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import Date
# from .base import Base, provide_session
from . import base
from constants import CLOCK  # REVIEW: clock access
from random import randint
from datetime import datetime, timedelta, date
from math import ceil
from enum import IntEnum


class ModelCategory(base.Base):
    __tablename__ = "tbl_category"

    cat_id = Column(Integer, primary_key=True)
    category = Column(String(50))
    coefficient = Column(Float)

    def __repr__(self):
        if self.cat_id == 1:
            return "frozen"
        elif self.cat_id == 2:
            return "fridge"
        elif self.cat_id == 3:
            return "pantry"
        elif self.cat_id == 4:
            return "pet"
        else:
            return "meat"


class ModelSold(base.Base):
    __tablename__ = "tbl_sold"

    id = Column(Integer, primary_key=True)
    grp_id = Column(Integer)
    date = Column(Date)
    sold = Column(Integer)


# CHECK: enum database type class works?
class PRICE(IntEnum):
    regular = 0
    sale = 1


class ModelProduct(base.Base):
    __tablename__ = "tbl_product"

    # basic info
    grp_id = Column(Integer, primary_key=True)
    brand = Column(String(200))
    name = Column(String(600))
    category = Column(Integer)
    max_shelved_stock = Column(Integer)
    max_back_stock = Column(Integer)
    restock_threshold = Column(Integer)

    # selection info
    regular_price = Column(Float(precision=2))
    sale_price = Column(Float(precision=2))
    price_status = Column(Enum(PRICE))
    popularity = Column(Float(precision=2))
    popularity_delta = Column(Float(precision=2))

    # order info
    lot_price = Column(Float(precision=2))
    lot_quantity = Column(Integer)
    sublots = Column(Integer)
    sublot_quantity = Column(Integer)
    sell_by_days = Column(Integer)
    order_threshold = Column(Integer)

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

    def get_popularity(self):
        return self.popularity

    def get_popularity_delta(self):
        return self.popularity_delta

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

    @provide_session
    def set_threshold(self, session=None):
        '''
        Sets the minimum amount of product to keep in stock.
        Based on average quantity sold in the past three days.       
        '''
        today = datetime(CLOCK.year, CLOCK.month, CLOCK.day, 0, 0)
        filter_after = today - timedelta(days=3)
        avg = session.query(func.avg(ModelSold.sold).label("average"))\
            .filter(ModelSold.grp_id == self.grp_id)\
            .filter(ModelSold.date > filter_after).one()
        if avg.average is not None:
            self.threshold = round(avg.average) + ceil(0.1 * avg.average)

    def get_sell_by(self):
        noise = timedelta(days=randint(-2, 2))
        today = date(CLOCK.year, CLOCK.month, CLOCK.day)
        return today + noise + timedelta(days=self.sell_by_days)

    # -------------------------------------------- Other functions
    def setup(self):
        self.sale_price = round(
            self.regular_price - (0.15 * self.regular_price), 2
            )
        self.price_status = PRICE.regular
        self.popularity_delta = round(0.12 * self.popularity, 2)
        self.lot_price = 2
        self.order_threshold = self.max_shelved_stock
        self.restock_threshold = round(self.max_shelved_stock / 2)

    @provide_session
    def __repr__(self, session=None):
        cat = session.query(ModelCategory)\
            .filter(ModelCategory.cat_id == self.category).first()
        return (
            "<Product(grp_id={}, category={}, price_status={}, "
            "reg_price={}, sale_price={}, popularity={}%, "
            "popularity_delta={})"
            .format(
                self.grp_id, cat, self.price_status, self.regular_price,
                self.sale_price, self.popularity, self.popularity_delta
            )
        )
