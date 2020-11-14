import random
from time import time
# from collections import deque

from models.Base import provide_session
from models import (Model_Shopper)
from models import Const, Cart, Shopper, Employee
# from constants import (MIN_LANES, MAX_LANES, QTIME_MIN, QTIME_RANGE,
# QTIME_IDEAL, CHECKOUT_MIN, CHECKOUT_MAX, Status)


class SingleLane:
    def __init__(self):
        self.queue = []
        self.employee = None
        self.items_per_min = None
        self.length = 0

    def set_employee_and_speed(self, eid, speed):
        self.employee = eid
        self.items_per_min = speed

    def enq(self, sid):
        self.queue.append(sid)
        self.length += 1

    def deq(self):
        sid = self.queue.pop(0)
        self.length -= 1
        return sid

    def insert_left(self, sid):
        self.queue.insert(0, sid)
        self.length += 1

    def close(self):
        employee.return_employee(self.employee)

    def open(self):
        self.eid, self.items_per_min = self.employee.request_employee()

    def step(self, session=None):
        quota = self.items_per_min
        while self.length > 0:
            sid = self.queue.deq()
            cart_size = cart.get_size(sid, session)
            amount = min(cart_size, quota)

            cart.scan_n(sid, amount, session)
            quota -= amount

            # partial scan
            if amount < cart_size:
                self.insert_left(sid)
            # shopper is done
            else:
                s = session.query(Model_Shopper)\
                    .filter(Model_Shopper.id == sid).one()
                s.set_status(Status.DONE)

            if quota == 0:
                break
        session.commit()


# ----------------------------------------------- EXTERNAL FUNCTIONS
# returns index of the shortest lane
# takes a list of lanes and the number of open lanes
def shortest(lanes, open_lanes):
    min_index, min_count = 0, lanes[0].length
    for i in range(open_lanes):
        if lanes[i].length < min_count:
            min_index = i
            min_count = lanes[i].length
    return min_index


# CHECK if we need to pass a session in here in order
# for shopper changes to persist
def queue_shopper(shopper, lanes, open_lanes):
    index = shortest(lanes, open_lanes)
    shopper.lane = index
    lanes[index].enq(shopper)
    shopper.qtime = 0


def shift_change(lanes, num_open):
    for i in range(num_open):
        lane = lanes[i]
        if Employee.valid_cashier(lane.id, lane.employee) is False:
            eid, speed = Employee.swap(lane.employee, lane.id)
            lane.set_employee(eid, speed)


def manage(lanes, open_lanes):
    clock = Const.CLOCK
    now = time(clock.hour, clock.minute)
    if now < time(10, 15):
        return

    if Const.manage_delay is None:
        qlen = self.avg_qlen()
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


# ----------------------------------------------- INTERNAL FUNCTIONS

def total_shoppers(lanes):
    count = 0
    for lane in lanes:
        count += lane.length
    return count

# average time to check out last person in each lane
def expected_avg_qtime(self):
    total = 0
    for i in range(self.open_lanes):
    for i in range(open_lanes):
        q = self.lanes[lane_no].queue
        q = lanes[lane_no].queue
        items = 0
        for shopper in q:
            items += shopper.cart_size
        mins = items / self.lanes[i].items_per_min
        mins = items / lanes[i].items_per_min
        total += mins

    return total / self.open_lanes
    return total / open_lanes

#  average queue length
def avg_qlen(self):
    total = 0
    for lane in self.lanes:
    for lane in lanes:
        total += lane.length
    return round(total / self.open_lanes)
    return round(total / open_lanes)

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




















def collapse(avg_qlen, avg_qtime):
    assert (self.open_lanes > MIN_LANES)
    assert (open_lanes > MIN_LANES)

    # calculate number of lanes to remove
    if avg_qlen == 0:   # remove 2/3 of lanes
        num_removed = 2 * round(self.open_lanes / 3)
        num_removed = 2 * round(open_lanes / 3)
    elif avg_qlen == 1: # remove 1/2 of lanes
        num_removed = round(self.open_lanes / 2)
        num_removed = round(open_lanes / 2)
    else:
        num_removed = self.open_lanes % avg_qlen
        num_removed = open_lanes % avg_qlen

    num_remaining = self.open_lanes - num_removed
    num_remaining = open_lanes - num_removed

    # CHECK MINIMUM BOUNDS
    if num_remaining < MIN_LANES:
        num_remaining = MIN_LANES

    new_end = num_remaining-1
    self.open_lanes = num_remaining
    open_lanes = num_remaining


def expand():
    assert (self.open_lanes != MAX_LANES)
    assert (open_lanes != MAX_LANES)
    ideal_qlen = None
    num_new_lanes = None

    # calculate number of lanes to add
    if avg_qlen == 0:
        return
    elif avg_qlen == 1:
        num_new_lanes = round(self.open_lanes / 3)
        num_new_lanes = round(open_lanes / 3)
        ideal_qlen = 1
    else:
        wait_per_person = avg_qtime / (avg_qlen -1)
        ideal_qlen = round(QTIME_IDEAL / wait_per_person)
        delta_qlen = avg_qlen - ideal_qlen
        assert(delta_qlen != 0)
        excess_ppl = delta_qlen * self.open_lanes
        excess_ppl = delta_qlen * open_lanes
        if ideal_qlen == 0 or ideal_qlen == 1 or avg_qlen < 3:
            num_new_lanes = self.total_shoppers() - self.open_lanes
            num_new_lanes = self.total_shoppers() - self.open_lanes
            num_new_lanes = total_shoppers() - open_lanes
        else:
            num_new_lanes = round(excess_ppl / ideal_qlen)

    # CHECK MAX BOUNDS 
    if num_new_lanes + self.open_lanes > MAX_LANES:
    if num_new_lanes + open_lanes > MAX_LANES:
        num_new_lanes = MAX_LANES - self.open_lanes
        num_new_lanes = MAX_LANES - open_lanes

    # append new lanes
    qcount_old = self.open_lanes
    qcount_old = open_lanes
    for i in range(num_new_lanes):
        self.open_lanes += 1
        open_lanes += 1
        self.lanes[self.open_lanes-1].reset() ## FIX: items per min from employee
        self.lanes[self.open_lanes-1].reset() ## FIX: items per min from employee
        lanes[open_lanes-1].reset() ## FIX: items per min from employee
    assert(self.open_lanes <= MAX_LANES)
    assert(open_lanes <= MAX_LANES)

    # redistribute customers
    new_lane_index = qcount_old
    old_lane_index = 0;
    for i in range(qcount_old):
        old_lane = self.lanes[i]
        old_lane = lanes[i]
        if old_lane.length == 1: # no need to redistribute
            continue

        # redistribute to new lanes while they have space
        if ideal_qlen is not None:
            while old_lane.length>ideal_qlen and new_lane_index<self.open_lanes:
            while old_lane.length>ideal_qlen and new_lane_index<open_lanes:
                shopper = old_lane.deq()
                new_lane = self.lanes[new_lane_index]
                new_lane = lanes[new_lane_index]
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
                new_lane = lanes[old_lane_index] 
                new_lane.append(shopper)
                old_lane_index+=1
