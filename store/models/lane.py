import random
from datetime import time, timedelta
from models import ModelProduct
# from collections import deque
from sqlalchemy import func
import sys

from models.Base import provide_session
from models import Status, ModelShopper
from models import Const, Cart, Shopper, Employee
# from constants import (MIN_LANES, MAX_LANES, QTIME_MIN, QTIME_RANGE,
# QTIME_IDEAL, CHECKOUT_MIN, CHECKOUT_MAX, Status)


class SingleLane:
    def __init__(self, index):

        self.id = index
        self.queue = []
        self.employee = None
        self.items_per_min = None
        self.length = 0

    def print(self, index):
        print("<Lane_{}: eid={}, speed={}, length={},"
              .format(self.id, self.employee, self.items_per_min, self.length),
              "\tqueue: ", self.queue, ">")

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

    def deq_right(self):
        sid = self.queue.pop(self.length - 1)
        self.length -= 1
        return sid

    def insert_left(self, sid):
        self.queue.insert(0, sid)
        self.length += 1

    def close(self):
        print("\tclosing lane_{}, returning emp_{}".format(self.id, self.employee))
        Employee.return_employee(self.employee)

    def open(self):
        print("\topening lane_{}".format(self.id))
        self.employee, self.items_per_min = Employee.request_employee(self.id)

    def step(self, session=None):
        quota = self.items_per_min
        if self.length == 0 and self.employee is not None:
            self.close()

        while self.length > 0:
            sid = self.deq()
            cart_size = Cart.get_size(sid, session)
            amount = min(cart_size, quota)
            print("> lane {}: {} items for sid_{}, scanning...".format(self.id, amount, sid))
            Cart.scan_n(sid, amount, session)
            quota -= amount

            # partial scan
            if amount < cart_size:
                self.insert_left(sid)
            # shopper is done
            else:
                s = session.query(ModelShopper)\
                    .filter(ModelShopper.id == sid).one()
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
def queue_shopper(sid, lanes, open_lanes):
    index = shortest(lanes, open_lanes)
    print("\tENQ: shopper_{} --> lane_{} "
          .format(sid, index))
    lanes[index].enq(sid)
    return index


def shift_change(lanes, num_open):
    for i in range(num_open):
        ln = lanes[i]
        if Employee.valid_cashier(ln.id, ln.employee) is False:
            Employee.return_employee(ln.employee)
            eid, speed = Employee.request_employee(ln.id)
            ln.set_employee(eid, speed)


def manage(lanes, open_lanes, session=None):
    clock = Const.CLOCK
    now = time(clock.hour, clock.minute)
    print("\n")
    if now < time(10, 15):
        print("too early for lane management...")
        if now == time(10, 15):
            Const.MANAGE_DELAY = None
        return open_lanes

    if Const.MANAGE_DELAY is None:
        print("managing lanes...")
        qlen = avg_qlen(lanes, open_lanes)
        qtime = avg_last_shopper_qtime(lanes, open_lanes, session)
        num_shoppers = total_shoppers(lanes)
        print("\t******** qtime = {}, qlen = {}, num_shoppers = {}, num_lanes = {}"
              .format(qtime, qlen, num_shoppers, open_lanes))

        # (qtime > 12 AND shoppers > lanes AND lanes < 30)
        open_condition = (
            qtime > Const.QTIME_MAX
            and num_shoppers > open_lanes
            and open_lanes < Const.MAX_LANES)

        # (shoppers < 2x lanes OR qtime < 4) AND (lanes > 2)
        # (qtime < 4) AND (lanes > 2)  --> test this version too
        close_condition = (
            (num_shoppers < round(open_lanes / 2)
             or qtime < Const.QTIME_MIN)
            and open_lanes > Const.MIN_LANES)

        # print lane queues before management
        if open_condition or close_condition:
            print("\nBEFORE MANAGMEENT")
            for i in range(open_lanes):
                lanes[i].print(i)

            if open_condition:
                print("\nEXPANDING...")
                print("\t[{}_qtime > 12] AND [{}_shoppers  > {}_lanes] and [{}_lanes < 30]"\
                      .format(qtime, num_shoppers, open_lanes, open_lanes))
                open_lanes = expand(lanes, open_lanes, qlen, qtime)
                Const.MANAGE_DELAY = 0
            elif close_condition:
                print("\nCOLLAPSING...")
                print("\t([{}_shoppers < {}_2xlanes] OR [{}_qtime < 4_minqtime]) AND ([{}_lanes > 2_minlanes])"\
                      .format(num_shoppers, open_lanes, qtime, open_lanes))
                open_lanes = collapse(qlen, open_lanes)
                Const.MANAGE_DELAY = 0
                print("\nAFTER MANAGMEENT")
                print("open:")
                for i in range(open_lanes):
                    lanes[i].print(i)
                print("closed:")
                for i in range(Const.MAX_LANES):
                    if i > open_lanes and lanes[i].length > 0:
                        lanes[i].print[i]
                exit(1)

            print("\nAFTER MANAGMEENT")
            print("open:")
            for i in range(open_lanes):
                lanes[i].print(i)
            print("closed:")
            for i in range(Const.MAX_LANES):
                if i > open_lanes and lanes[i].length > 0:
                    lanes[i].print[i]
        else:
            pass

        return open_lanes

    else:
        print("no lane management...")
        Const.MANAGE_DELAY += 1
        print("\t manage delay = ", Const.MANAGE_DELAY)
        if Const.MANAGE_DELAY < 0:
            exit(1)
        if Const.MANAGE_DELAY == Const.QTIME_RANGE:
            Const.MANAGE_DELAY = None
        return open_lanes


# ----------------------------------------------- INTERNAL FUNCTIONS

def total_shoppers(lanes):
    count = 0
    for lane in lanes:
        count += lane.length
    return count


# average time to check out last person in each lane
def avg_last_shopper_qtime(lanes, open_lanes, session=None):
    x = session.query(ModelProduct).all()
    total = 0
    for i in range(open_lanes):
        items = 0
        for sid in lanes[i].queue:
            items += Cart.get_size(sid, session)
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


def expand(lanes, open_lanes, qlen, qtime):
    assert (open_lanes != Const.MAX_LANES)
    ideal_qlen = None
    num_new_lanes = None

    # calculate number of lanes to add
    if qlen == 0:  # few shoppers w/large carts
        print("\tqlen = 0 --> few shopper w/large carts")
        return
    elif qlen == 1:  # increase num lanes by 1/3
        num_new_lanes = round(open_lanes / 3)
        ideal_qlen = 1
        print("\t num_new_lanes = {}, ideal_qlen = {}"
              .format(num_new_lanes, ideal_qlen))
    else:
        print("qtime = {}, qlen= {}, wpp = {}".format(qtime, qlen, qtime / (qlen - 1)))
        wait_per_person = qtime / (qlen - 1)
        ideal_qlen = round(Const.QTIME_IDEAL / wait_per_person)
        delta_qlen = qlen - ideal_qlen
        assert(delta_qlen != 0)
        excess_ppl = delta_qlen * open_lanes
        if ideal_qlen == 0 or ideal_qlen == 1 or qlen < 3:
            num_new_lanes = total_shoppers(lanes) - open_lanes
        else:
            num_new_lanes = round(excess_ppl / ideal_qlen)
        print("\t waitpp = {}, ideal_qlen = {}, delta_qlen = {}, execessppl = {}, num_new_lanes = {}"
              .format(wait_per_person, ideal_qlen, delta_qlen, excess_ppl, num_new_lanes))

    # CHECK MAX BOUNDS
    num_new_lanes = min(num_new_lanes, Const.MAX_LANES - open_lanes)
    print("\t num_new_lanes (bounded) = ", num_new_lanes)

    # open new lanes
    qcount_old = open_lanes
    print("opening lanes...")
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

        if ideal_qlen:
            # redistribute to new lanes while they have space
            while old_lane.length > ideal_qlen and new_lane_index < open_lanes:
                sid = old_lane.deq_right()
                new_lane = lanes[new_lane_index]
                new_lane.insert_left(sid)

                if(new_lane.length >= ideal_qlen):
                    new_lane_index += 1

            # redistribute remaining customers to all lanes one-by-one
            while old_lane.length > ideal_qlen:
                print("\t[length={} > {}=ideal_qlen]"
                      .format(old_lane.length, ideal_qlen))
                if i == old_lane_index:
                    old_lane_index += 1
                    print("\nold_lane_index = ", old_lane_index)
                    break
                sid = old_lane.deq_right()
                new_lane = lanes[old_lane_index]
                new_lane.enq(sid)
                old_lane_index += 1
        else:
            sys.exit("FATAL: ideal_qlen is None")

    return open_lanes


def print_active_lanes(lanes):
    print("\t--- ACTIVE SHOPPERS --- ")
    for i, ln in enumerate(lanes):
        if ln.length > 0:
            ln.print(i)
