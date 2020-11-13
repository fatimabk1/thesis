from sqlalchemy import Column, Integer, ForeignKey, String, Float, DateTime, Interval
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from base import Session, Engine, Base
import random
from session import provide_session

from constants import MIN_LANES, MAX_LANES, QTIME_MIN, QTIME_RANGE, QTIME_IDEAL, CHECKOUT_MIN, CHECKOUT_MAX, Status

from shopper    import Model_Shopper
from cart       import Model_Cart
from price      import Model_Price
from inventory  import Model_Inventory
from revenue    import Model_Revenue
from qtime      import Model_Qtime


class LanePool:

    class SingleLane:
        def __init__(self):
            self.queue = deque()
            self.items_per_min = None       ## FIX: based off of assigned employee
            self.length = 0                 # number of shoppers in queue

        def reset(self):                    
            self.items_per_min = random.randint(CHECKOUT_MIN, CHECKOUT_MAX)  

        def enq(self, shopper):
            self.queue.append(shopper)
            self.length +=1

        def deq(self):
            shopper = self.queue.pop()
            self.length -=1
            return shopper

        @provide_session
        def checkout_cart(self, checkout_quota, lane, clock, session=None):
            assert lane.length != 0    # precondition: lane must have shoppers to checkout, should not call checkout_cart() if False

            shopper = lane.deq()
            shopper.status = Status.CHECKOUT
            cart = session.query(Model_Cart).filter(Model_Cart.shopper_id==shopper.id).all()

            while (checkout_quota != 0 and len(cart) != 0):

                # lookup item price
                cart_row = cart.pop(0)
                cart_row.checkout(shopper)
                checkout_quota -= 1
                session.delete(cart_row)

            if len(cart) == 0:
                rev = Model_Revenue(stamp=clock, value=shopper.total)
                qt = Model_Qtime(queue_num=shopper.queue, stamp=clock, q_time=shopper.queue_time, total_qs=self.open_lanes)
                session.add(rev)
                session.add(qt)
                shopper.status = Status.DONE
            else:
                # cart still has items, return shopper to queue
                lane.enq(shopper)

            session.commit() 
            return checkout_quota


    def __init__(self):
        self.lanes = []
        self.open_lanes     = 0 
        self.manage_delay   = None

        for i in range(MAX_LANES):
            L = SingleLane()
            self.lanes.append(L)
            if i <= MIN_LANES:
                L.reset()
        self.open_lanes = MIN_LANES

    # return index of shortest lane
    def shortest(self):
        min_index, min_count = 0, self.lanes[0].length
        for i in range(self.open_lanes):
            if self.lanes[i].length < min_count:
                min_index = i 
                min_count = self.lanes[i].length
        return min_index

    # add shopper to shortest queue
    def push(self, shopper):
        index = self.shortest()
        shopper.lane = index
        self.lanes[index].enq(shopper)
        shopper.qtime = 0

    def total_shoppers(self):
        count = 0
        for lane in self.lanes:
            count += lane.length
        return count

    # average time to check out last person in each lane
    def expected_avg_qtime(self):
        total = 0
        for i in range(self.open_lanes):
            q = self.lanes[lane_no].queue
            items = 0
            for shopper in q:
                items += shopper.cart_size
            mins = items / self.lanes[i].items_per_min
            total += mins

        return total / self.open_lanes

    #  average queue length
    def avg_qlen(self):
        total = 0
        for lane in self.lanes:
            total += lane.length
        return round(total / self.open_lanes)

    # average queue time of shoppers who finished checking out in the past QTIME_RANGE minutes
    @provide_session
    def avg_qtime(self, clock, session=None):
        qtime, results = 0, 0
        time = clock - timedelta(minutes=QTIME_RANGE)
        avg_qtime = session.query(func.avg(Model_Qtime.qtime)).filter(Model_Qtime.stamp==time).first()
  
        if avg_qtime is None:
            return 0
        else:
            return round(avg_qtime)

    # open more lanes and redistribute customers to these lanes
    def expand(self, avg_qlen, avg_qtime):
        assert (self.open_lanes != MAX_LANES)
        ideal_qlen = None
        num_new_lanes = None

        # calculate number of lanes to add
        if avg_qlen == 0:
            return
        elif avg_qlen == 1:
            num_new_lanes = round(self.open_lanes / 3)
            ideal_qlen = 1
        else:
            wait_per_person = avg_qtime / (avg_qlen -1)
            ideal_qlen = round(QTIME_IDEAL / wait_per_person)
            delta_qlen = avg_qlen - ideal_qlen
            assert(delta_qlen != 0)
            excess_ppl = delta_qlen * self.open_lanes
            if ideal_qlen == 0 or ideal_qlen == 1 or avg_qlen < 3:
                num_new_lanes = self.total_shoppers() - self.open_lanes
            else:
                num_new_lanes = round(excess_ppl / ideal_qlen)

        # CHECK MAX BOUNDS 
        if num_new_lanes + self.open_lanes > MAX_LANES:
            num_new_lanes = MAX_LANES - self.open_lanes

        # append new lanes
        qcount_old = self.open_lanes
        for i in range(num_new_lanes):
            self.open_lanes += 1
            self.lanes[self.open_lanes-1].reset() ## FIX: items per min from employee
        assert(self.open_lanes <= MAX_LANES)

        # redistribute customers
        new_lane_index = qcount_old
        old_lane_index = 0;
        for i in range(qcount_old):
            old_lane = self.lanes[i]
            if old_lane.length == 1: # no need to redistribute
                continue

            # redistribute to new lanes while they have space
            if ideal_qlen is not None:
                while old_lane.length>ideal_qlen and new_lane_index<self.open_lanes:
                    shopper = old_lane.deq()
                    new_lane = self.lanes[new_lane_index]
                    new_lane.enq(shopper)

                    if(new_lane.length >= ideal_qlen):
                        new_lane_index +=1

                # redistribute remaining customers to all lanes one-by-one
                while old_lane.length> ideal_qlen:
                    if i == old_lane_index:
                        old_lane_index+=1
                        break
                    shopper = old_lane.deq()
                    new_lane = self.lanes[old_lane_index] 
                    new_lane.append(shopper)
                    old_lane_index+=1

    # close  lanes and redistribute customers to open lanes
    def collapse(self, avg_qlen, avg_qtime):
        assert (self.open_lanes > MIN_LANES)

        # calculate number of lanes to remove
        if avg_qlen == 0:   # remove 2/3 of lanes
            num_removed = 2 * round(self.open_lanes / 3)
        elif avg_qlen == 1: # remove 1/2 of lanes
            num_removed = round(self.open_lanes / 2)
        else:
            num_removed = self.open_lanes % avg_qlen

        num_remaining = self.open_lanes - num_removed

        # CHECK MINIMUM BOUNDS
        if num_remaining < MIN_LANES:
            num_remaining = MIN_LANES

        new_end = num_remaining-1
        self.open_lanes = num_remaining


    # determine whether & how many lanes to open/close 
    def manage(self, clock):                ## CHANGE: clock will become a global variable. maybe a singleton class? 
        if clock.hour==10 and clock.minute<15:
            return

        if self.manage_delay is None:
            qlen = self.avg_qlen()
            qtime = self.avg_qtime(clock)
            qalt = self.avg_alt()
            num_shoppers = self.total_shoppers()

            if (num_shoppers<round(self.open_lanes/2) or qalt<QTIME_MIN) and self.open_lanes>MIN_LANES:
                self.collapse(qlen, qalt)
                self.manage_delay = 0

            elif qalt>QTIME_MAX and num_shoppers>self.open_lanes and self.open_lanes<MAX_LANES:
                self.expand(qlen, qalt)
                self.manage_delay = 0

            else:
                pass

        else :
            self.manage_delay += 1
            if self.manage_delay == QTIME_RANGE:
                self.manage_delay = None


    # checkout up to x items in in a single cart within a single lane. 
    # if less than x items are checked out, returns the difference
    @provide_session
    def checkout_cart(self, checkout_quota, lane, clock, session=None):
        assert lane.length != 0    # precondition: lane must have shoppers to checkout, should not call checkout_cart() if False

        shopper = lane.deq()
        shopper.status = Status.CHECKOUT
        cart = session.query(Model_Cart).filter(Model_Cart.shopper_id==shopper.id).all()

        while (checkout_quota != 0 and len(cart) != 0):
            cart_row = cart.pop(0)
            cart_row.checkout(shopper)
            checkout_quota -= 1
            session.delete(cart_row)

        if len(cart) == 0:
            rev = Model_Revenue(stamp=clock, value=shopper.total)
            qt = Model_Qtime(queue_num=shopper.queue, stamp=clock, q_time=shopper.queue_time, total_qs=self.open_lanes)
            session.add(rev)
            session.add(qt)
            shopper.status = Status.DONE
        else:
            # cart still has items, return shopper to queue
            lane.enq(shopper)

        session.commit()
        return checkout_quota

    # for each lane, checkout up to x items 
    def advance(self, clock):
        for lane_obj in self.lanes:
            lane, x = lane_obj.queue, lane_obj.items_per_min

            if len(lane) > 0:
                while x!=0:
                    if len(lane) == 0:
                        break
                    x = self.checkout_cart(x, lane, clock)
                lane_obj.reset()

            # update queue time for waiting shoppers
            for index, shopper in enumerate(lane):
                if shopper.status is Status.QUEUEING:
                    shopper.queue_time += 1  










