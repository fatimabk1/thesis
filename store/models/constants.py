from datetime import datetime, time, timedelta
from enum import IntEnum
import sys

CLOCK = datetime(2019, 9, 15, 10, 0)  # SUNDAY
TRUCK_DAYS = 2
EOD_FLAG = False
PRODUCT_COUNT = 100  # total # of products in db 3k
CATEGORY_COUNT = 10  # total # of categories in db 100
# PRODUCTS_PER_CATEGORY = int(PRODUCT_COUNT / CATEGORY_COUNT) 3000
PRODUCTS_PER_CATEGORY = 10

# ------------- performance monitoring
LOGGING = True
curr = None


def log(message=None):
    if LOGGING:
        curr = datetime.now()
        if message:
            message += ": "
            print(message, curr)
        return curr


def delta(message, prev):
    if LOGGING:
        curr = datetime.now()
        diff = curr - prev
        message += " ∆: "
        print(message, curr - prev)
        if diff > timedelta(milliseconds=100):
            print(message, curr - prev, file=sys.stderr)


# ----------------------------------- PULLING DATA
categories = []  # ordered by category.id; access via categories[id-1]
products = []  # ordered by product.grp_id ;access products[id-1]


TASK_UNLOAD = 0
TASK_RESTOCK = 1
TASK_TOSS = 2
TASK_CASHIER = 3


# ------------------------------------------------------------------------------------------------ CONSTANTS & ENUMS
class Day(IntEnum):
    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6


NUM_DAYS = 7	 # 7 days in a week
DAY_START = 10	 # store opens at 10:00 am


MANAGE_FREQUENCY = 1  # manage() evaluates average lane qtime and qlen every MANAGE_FREQUENCY minutes
MANAGE_DELAY = None  # after manage() is executed, manage is not called again for at least MANAGE_DELAY minutes

QTIME_RANGE = 7  # average queue time is calculated over the last QTIME_RANGE minutes
QTIME_IDEAL = 8  # the ideal amount of time a consumer is willing to wait in line (close to max, but not quite), in minutes
QTIME_MIN = 4  # if the avg qtime is less than this value, need to close some lanes
QTIME_MAX = 12  # if the avg qtime is greater than this value, need to open more lanes

QLEN_MAX = 5  # if avg_qlen > QLEN_MAX --> open more lanes
QLEN_MIN = 2  # if avg_qlen < QLEN_MIN --> close some lanes
RESTOCK_THRESHOLD = 100  # if shelved_stock falls below this value, restock from back_stock

# ------------------------------------------------------------------------------------------------ PARAMATERS
CHECKOUT_MIN = 2
CHECKOUT_MAX = 5
STOCK_MIN = 40  # this group of paramaters set the speed restraints for checking out, restocking, etc.		 
STOCK_MAX = 100
UNLOAD_MIN = 10  # in terms of lots
UNLOAD_MAX = 30


MAX_LANES = 30				    # max possible lanes
MIN_LANES = 2					# num of open lanes at start

HOURS_RUN = 1					# hours to run simulation
RUN_TIME = HOURS_RUN * 60		# HOURS_RUN converted to minutes

# initally min=10, max=50
SHOPPER_MIN = 10                # min number of items a shopper will attempt to purchase
SHOPPER_MAX = 30                # max number of items a shopper will attempt to purchase
NUM_EMPLOYEES = 100


WAGE_MIN = 8
WAGE_MAX = 18


# ------------------------------------------------------------- VARS/FUNCTIONS RELATED TO EMPLOYEE SHIFTS & TIME

# specific times an employee works
class Shift(IntEnum):
    MORNING = 0  # 8am - 3pm, 7 hours
    EVENING = 1  # 3pm - 10pm, 7 hours
    OFF = 2


# store time flags
CURRENT_SHIFT = None
BEFORE = False
OPEN = True
CLOSED = False
CLOSING_SOON = False


def shift_change():
    if CLOCK.hour == 15 and CLOCK.minute == 00:
        CURRENT_SHIFT = Shift.EVENING  # check that this works
        return True
    return False


# # pre-open, employees work from 8am - 10am
# def store_before():
#     if time(CLOCK.hour, CLOCK.minute) < time(10, 0):
#         return True
#     else:
#         return False


# # store hours: 10am - 8pm
# def store_open():
#     if (time(CLOCK.hour, CLOCK.minute) >= time(10, 0) and
#             time(CLOCK.hour, CLOCK.minute) < time(20, 0)):
#         return True
#     else:
#         return False


# # post-close, employees work from 8pm - 10pm
# def store_closed():
#     if time(CLOCK.hour, CLOCK.minute) >= time(20, 0):
#         return True
#     else:
#         return False
