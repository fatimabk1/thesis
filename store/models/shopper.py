from models.product import ModelProduct, choose_category
from sqlalchemy import (Column,
                        Integer,
                        Float)
import random
from datetime import date
from enum import IntEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.sql import func
from models import (Base,
                    provide_session,
                    ModelProduct,
                    ModelInventory,
                    ModelCategory,
                    ModelRevenue,
                    ModelQtime,
                    PRICE)
# CATEGORY_COUNT, SHOPPER_MIN, SHOPPER_MAX
from models import constants as const
from models import cart

CLOCK = const.CLOCK


class Status(IntEnum):
    INERT = 0
    SHOPPING = 1
    QUEUEING = 2
    CHECKOUT = 3
    DONE = 4


class ModelPreference(Base):
    __tablename__ = "tbl_preference"

    id = Column(Integer, primary_key=True)
    shopper_id = Column(Integer)
    grp_id = Column(Integer)
    regular_roll = Column(Float)
    sale_roll = Column(Float)

    def __repr__(self):
        return (
            "<PREF: sid=%d, grp=%d, reg=%d, sale=%d>"
            % (self.shopper_id, self.grp_id, self.reg_roll, self.sale_roll))


class ModelShopper(Base):
    __tablename__ = "tbl_shopper"

    id = Column(Integer, primary_key=True)
    start_min = Column(Integer, default=random.randint(0, 60))
    browse_mins = Column(Integer, default=None)
    quota = Column(Integer, default=random.randint(
                    const.SHOPPER_MIN, const.SHOPPER_MAX))
    cart_count = Column(Integer, default=None)
    lane = Column(Integer, default=None)
    qtime = Column(Integer, default=None)
    status = Column(Integer, default=Status.INERT)
    total = Column(Float, default=0.00)

    # START: setting defaults for postgres columns with python values
    # and compiler thinking self.total is a None type and thus can't
    # be put into the strin properly in __repr__ below

    def __repr__(self):
        return(
            '''sid_%d: start=%d, browse=%s, quota=%d, cart_count=%s, lane=%s,
            qtime=%s, status=%s, total=%d'''
            % (self.id, self.start_min, str(self.browse_mins), self.quota,
                str(self.cart_count), str(self.lane), str(self.qtime),
                repr(self.status), self.total)
            )

    def get_status(self):
        return self.status

    def set_status(self, stat):
        self.status = stat

    def reset_browse(self):
        if const.EOD_FLAG is True:
            self.browse_mins = random.randint(1, 3)
        else:
            self.browse_mins = random.randint(1, 6)

    # sample randomly (between 0.01 and 0.99) from distribution
    @provide_session
    def roll(self, grp_id, product, session=None):
        pref = session.query(ModelPreference)\
            .filter(ModelPreference.shopper_id == self.id)\
            .filter(ModelPreference.grp_id == grp_id).one_or_none()
        
        if pref is None:
            reg = random.rand()  # FIXME
            sale = random.rand()  # FIXME
            pref = ModelPreference(
                shopper_id=self.id,
                grp_id=grp_id,
                regular_roll=reg,
                sale_roll=sale
            )
            session.add(pref)
            session.commit()

        return pref

    @provide_session
    def select_grp(self, session=None):
        category = choose_category()

        while True:
            prod = session.query(ModelProduct)\
                .filter(ModelProduct.category == category)\
                .order_by(func.random()).first()
            pref = self.roll(session)
            if prod.evaluate(pref) is True:
                cart.add_item(self.id, prod.grp_id, session)
                break

    # START HERE
    @provide_session
    def advance(self, session=None):
        # def advance(self, laneManager, session=None):
        if self.status == Status.INERT:
            if CLOCK.minute == self.start_min:
                print("\nINERT_ready")
                self.status = Status.SHOPPING
                self.reset_browse()
            print("\nINERT_waiting")
        elif self.status == Status.SHOPPING:
            # done shopping
            if self.quota == 0:
                print("\nSHOPPING_complete")
                self.total = cart.get_total(self.id, session)
                self.cart_count = cart.get_size(self.id, session)
                self.status = Status.QUEUEING
                # laneManager.enq(self)  # TEST when LaneManager is done
            # continue shopping
            else:
                if self.browse_mins == 0:
                    print("\nSHOPPING_choose")
                    self.select_grp(session)
                    self.quota -= 1
                    self.reset_browse()
                else:
                    print("\nSHOPPING_browse")
                    self.browse_mins -= 1
        elif self.status == Status.DONE:
            print("DONE")
            assert(self.status == Status.DONE)
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
            session.commit()
        else:
            print("QUEUEING_or_CHECKOUT")
            assert(self.status == Status.QUEUEING
                   or self.status == Status.CHECKOUT)
            pass  # handled by lane manager
