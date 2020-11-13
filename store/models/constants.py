from datetime import datetime, time
CLOCK = datetime(2019, 9, 15, 9, 0)
TRUCK_DAYS = 0  # initally 3
EOD_FLAG = False

# ------------------------------------------------------------------------------------------------ CONSTANTS & ENUMS
SUNDAY = 0
MONDAY = 1
TUESDAY = 2
WEDNESDAY = 3
THURSDAY = 4
FRIDAY = 6
SATURDAY = 7

NUM_DAYS = 7	 # 7 days in a week
DAY_START = 10	 # store opens at 10:00 am

PRODUCT_COUNT = 20  # total # of products in db
CATEGORY_COUNT = 5  # total # of categories in db


MANAGE_FREQUENCY = 1  # manage() evaluates average lane qtime and qlen every MANAGE_FREQUENCY minutes
MANAGE_DELAY = 15  # after manage() is executed, manage is not called again for at least MANAGE_DELAY minutes

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
SHOPPER_MIN = 1                 # min number of items a shopper will attempt to purchase
SHOPPER_MAX = 30				# max number of items a shopper will attempt to purchase
NUM_EMPLOYEES = 30


WAGE_MIN = 8
WAGE_MAX = 18


def store_before(clock):
    if time(clock.hour, clock.minute) < time(10, 0):
        return True
    else:
        return False


def store_open(clock):
    if (time(clock.hour, clock.minute) >= time(10, 0) and
            time(clock.hour, clock.minute) < time(8, 0)):
        return True
    else:
        return False


def store_closed(clock):
    if time(clock.hour, clock.minute) >= time(8,0):
        return True
    else:
        return False
