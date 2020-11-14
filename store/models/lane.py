import random
from time import time, timedelta
# from collections import deque
from sqlalchemy import func
import sys

from models.Base import provide_session
from models import Status, Model_Shopper
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
        Employee.return_employee(self.employee)

    def open(self):
        self.eid, self.items_per_min = Employee.request_employee()

    def step(self, session=None):
        quota = self.items_per_min
        while self.length > 0:
            sid = self.queue.deq()
            cart_size = Cart.get_size(sid, session)
            amount = min(cart_size, quota)

            Cart.scan_n(sid, amount, session)
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
        qlen = avg_qlen(lanes, open_lanes)
        qtime = avg_last_shopper_qtime(lanes, open_lanes)
        num_shoppers = total_shoppers(lanes)

        open_condition = (
            (num_shoppers < round(open_lanes / 2)
             or qtime < Const.QTIME_MIN)
            and open_lanes > Const.MIN_LANES)
        close_condition = (
            qtime > Const.QTIME_MAX
            and num_shoppers > open_lanes
            and Const.open_lanes < Const.MAX_LANES)

        if open_condition:
            open_lanes = collapse(qlen, open_lanes)
            Const.manage_delay = 0
        elif close_condition:
            open_lanes = expand(lanes, open_lanes, qlen, qtime)
            Const.manage_delay = 0
        else:
            pass

        return open_lanes

    else:
        Const.manage_delay += 1
        if Const.manage_delay == Const.QTIME_RANGE:
            Const.manage_delay = None


# ----------------------------------------------- INTERNAL FUNCTIONS

def total_shoppers(lanes):
    count = 0
    for lane in lanes:
        count += lane.length
    return count


# average time to check out last person in each lane
def avg_last_shopper_qtime(lanes, open_lanes):
    total = 0
    for i in range(open_lanes):
        items = 0
        for sid in lanes[i].queue:
            items += Cart.get_size(sid)
        total += items / lanes[i].items_per_min
    return total / open_lanes


#  average queue length
def avg_qlen(lanes, open_lanes):
    total = 0
    for lane in lanes:
        total += lane.length
    return round(total / open_lanes)


def collapse(qlen, open_lanes):
    assert (open_lanes > Const.MIN_LANES)

    # calculate number of lanes to remove
    if qlen == 0:   # remove 2/3 of lanes
        num_removed = 2 * round(open_lanes / 3)
    elif qlen == 1:  # remove 1/2 of lanes
        num_removed = round(open_lanes / 2)
    else:
        num_removed = open_lanes % qlen

    num_remaining = open_lanes - num_removed

    # CHECK MINIMUM BOUNDS
    if num_remaining < Const.MIN_LANES:
        num_remaining = Const.MIN_LANES

    open_lanes = num_remaining - 1
    return open_lanes


def expand(lanes, open_lanes, qtime, qlen):
    assert (open_lanes != Const.MAX_LANES)
    ideal_qlen = None
    num_new_lanes = None

    # calculate number of lanes to add
    if qlen == 0:  # few shoppers w/large carts
        return
    elif qlen == 1:  # increase num lanes by 1/3
        num_new_lanes = round(open_lanes / 3)
        ideal_qlen = 1
    else:
        wait_per_person = qtime / (qlen - 1)
        ideal_qlen = round(Const.QTIME_IDEAL / wait_per_person)
        delta_qlen = qlen - ideal_qlen
        assert(delta_qlen != 0)
        excess_ppl = delta_qlen * open_lanes
        if ideal_qlen == 0 or ideal_qlen == 1 or qlen < 3:
            num_new_lanes = total_shoppers() - open_lanes
        else:
            num_new_lanes = round(excess_ppl / ideal_qlen)

    # CHECK MAX BOUNDS
    num_new_lanes = min(num_new_lanes, Const.MAX_LANES - open_lanes)

    # open new lanes
    qcount_old = open_lanes
    for i in range(num_new_lanes):
        lanes[open_lanes].open()
        open_lanes += 1
    assert(open_lanes <= Const.MAX_LANES)

    # redistribute customers
    new_lane_index = qcount_old
    old_lane_index = 0
    for i in range(qcount_old):
        old_lane = lanes[i]
        if old_lane.length == 1:  # no need to redistribute
            continue

        # redistribute to new lanes while they have space
        if ideal_qlen is not None:
            while old_lane.length > ideal_qlen and new_lane_index < open_lanes:
                sid = old_lane.deq()
                new_lane = lanes[new_lane_index]
                new_lane.enq(sid)

                if(new_lane.length >= ideal_qlen):
                    new_lane_index += 1

            # redistribute remaining customers to all lanes one-by-one
            while old_lane.length > ideal_qlen:
                if i == old_lane_index:
                    old_lane_index += 1
                    break
                sid = old_lane.deq()
                new_lane = lanes[old_lane_index]
                new_lane.enq(sid)
                old_lane_index += 1
        else:
            sys.exit("FATAL: ideal_qlen is None")

    return open_lanes
