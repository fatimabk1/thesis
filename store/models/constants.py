from datetime import datetime
from enum import IntEnum
CLOCK = datetime(2019, 9, 15, 10, 0)
TRUCK_DAYS = 0

# ------------------------------------------------------------------------------------------------ CONSTANTS & ENUMS
SUNDAY = 0
MONDAY = 1
TUESDAY = 2
WEDNESDAY = 3
THURSDAY = 4
FRIDAY = 6
SATURDAY = 7


class Status(IntEnum):   
    INERT = 0  # has not started the shopping process yet
    SHOPPING = 1  # is shopping
    QUEUEING = 2  # has finished shopping (yet to join a lane || waiting in a lane)
    CHECKOUT = 3  # lane is in the process of checking out this shopper's cart
    DONE = 4  # this shopper has completed the checkout process, has no further processes

NUM_DAYS = 7	 # 7 days in a week
DAY_START = 10	 # store opens at 10:00 am

# session = Session()
# PRODUCT_COUNT  = session.query(product.grp_id).count()   # total # of products in db
# CATEGORY_COUNT = session.query(category.cat_id).count()  # total # of categories in db
# endSession(session)


MANAGE_FREQUENCY	= 1			# manage() evaluates average lane qtime and qlen every MANAGE_FREQUENCY minutes
MANAGE_DELAY 		= 15		# after manage() is executed, manage is not called again for at least MANAGE_DELAY minutes

QTIME_RANGE			= 7			# average queue time is calculated over the last QTIME_RANGE minutes
QTIME_IDEAL			= 8			# the ideal amount of time a consumer is willing to wait in line (close to max, but not quite), in minutes
QTIME_MIN 			= 4			# if the avg qtime is less than this value, need to close some lanes
QTIME_MAX 			= 12		# if the avg qtime is greater than this value, need to open more lanes

QLEN_MAX			= 5			# if avg_qlen > QLEN_MAX --> open more lanes
QLEN_MIN			= 2			# if avg_qlen < QLEN_MIN --> close some lanes
RESTOCK_THRESHOLD	= 100		# if shelved_stock falls below this value, restock from back_stock

# ------------------------------------------------------------------------------------------------ PARAMATERS
CHECKOUT_MIN	= 2					 
CHECKOUT_MAX	= 5					
RESTOCK_MIN		= 20			# this group of paramaters set the speed restraints for checking out, restocking, etc.		 
RESTOCK_MAX		= 50
UNLOAD_MIN 		= 10
UNLOAD_MAX 		= 30
TOSS_MIN 		= 10
TOSS_MAX		= 30				 


MAX_LANES		= 30				# max possible lanes 
MIN_LANES 		= 2					# num of open lanes at start

HOURS_RUN 		= 1					# hours to run simulation
RUN_TIME		= HOURS_RUN *60		# HOURS_RUN converted to minutes

SHOPPER_MIN		= 10				# min number of items a shopper will attempt to purchase
SHOPPER_MAX		= 50				# max number of items a shopper will attempt to purchase
NUM_EMPLOYEES	= 30				