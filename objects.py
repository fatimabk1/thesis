from base import Engine, Session, Base
from models import inventory, product, category, price, revenue, cost, employee, role, queuetime
import random
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.sql.expression import func
from collections import deque
import time
import sys


def endSession(session):
	try:
		session.commit()
	except:
		session.rollback()
		raise
	finally:
		session.close()

# ------------------------------------------------------------------------------------------------ CONSTANTS & ENUMS
SUNDAY = 0
MONDAY = 1
TUESDAY = 2
WEDNESDAY = 3
THURSDAY = 4
FRIDAY = 6
SATURDAY = 7

class Status(Enum):   
	INERT 		= 0		# has not started the shopping process yet
	SHOPPING 	= 1		# is shopping
	QUEUEING 	= 2		# has finished shopping (yet to join a lane || waiting in a lane)
	CHECKOUT 	= 3		# lane is in the process of checking out this shopper's cart
	DONE 		= 4		# this shopper has completed the checkout process, has no further processes

NUM_DAYS = 7	 # 7 days in a week
DAY_START = 10	 # store opens at 10:00 am

session = Session()
PRODUCT_COUNT  = session.query(product.grp_id).count()   # total # of products in db
CATEGORY_COUNT = session.query(category.cat_id).count()  # total # of categories in db
endSession(session)


MANAGE_FREQUENCY	= 1			# manage() evaluates average lane qtime and qlen every MANAGE_FREQUENCY minutes
QTIME_CONSTANT		= 15		# average queue time is calculated over the last QTIME_CONSTANT minutes
IDEAL_QTIME			= 6			# the ideal amount of time a consumer is willing to wait in line (close to max, but not quite), in minutes
QTIME_MIN 			= 4			# if the avg qtime is less than this value, need to close some lanes
QTIME_MAX 			= 8			# if the avg qtime is greater than this value, need to open more lanes

# ------------------------------------------------------------------------------------------------ PARAMATERS
CHECKOUT_MIN	= 2		# min num of items a lane can checkout per min
CHECKOUT_MAX	= 5		# max num of items a lane can checkout per min
MAX_LANES		= 20	# max possible lanes 
NUM_LANES 		= 5		# num of open lanes at start
RUN_TIME		= 60	# minutes to run simulation
SHOPPER_MIN		= 10	# min number of items a shopper will attempt to purchase
SHOPPER_MAX		= 50	# max number of items a shopper will attempt to purchase


# ------------------------------------------------------------------------------------------------ CLASSES

# A class for generating unique IDs for shoppers over the lifetime of the program 
class Auto_ID:
	def __init__(self):
		self.val = None
			
	def generate(self):
		if self.val is None:
			self.val = 0
		else:
			self.val +=1
		return self.val

# simulates the store for a number of months and days
# handles restocking, inventory ordering, price/sale updates, removing expired products
# outputs aggregate stats to data visualizor application
# class Period_Simulator(sim, months, days):
# 	def __init__(self):
# 		self.simulator = sim



# simulates the store for a single day
# advances shoppers and lanes one minute at a time
# allows shoppers to finish shopping after store closes but doesn't introduce new shoppers 
class Simulator:
	def __init__(self):
		self.clock 				= datetime(2019, 12, 12, 10, 0)
		self.start 				= datetime(2019, 12, 12, 10, 0)	# the exact time the day simulator starts, used to monitor time elapsed
		self.day 				= SUNDAY
		self.avg_shoppers		= 2200
		self.shoppers 			= []
		self.lanes				= Lane()
		self.id_generator		= Auto_ID()
		self.manage_delay		= None

		# Percentage busyness per hour per day --> Day[hr-10] = % busyness 
		self.shopper_frequency 	= [
				[42, 58, 74, 84, 85, 81, 79, 80, 78,  69, 54, 37, 22],
				[47, 55, 59, 58, 58, 65, 74, 92, 97,  88, 67, 43, 22],
				[43, 52, 56, 58, 61, 70, 84, 97, 100, 89, 67, 43, 23],
				[42, 46, 46, 45, 48, 59, 76, 84, 80,  69, 58, 43, 23],
				[40, 44, 45, 46, 52, 62, 74, 83, 83,  74, 58, 39, 23],
				[37, 47, 57, 62, 63, 66, 74, 82, 84,  75, 59, 40, 22],
				[51, 63, 69, 70, 67, 66, 68, 72, 73,  66, 51, 33, 17]
		]

	

	# store simulation for a single day, continues until all shoppers in the store complete their trips
	def run(self):
		def minutes_elapsed():
			return int((self.clock - self.start).seconds / 60)

		def debug(i):
			print("-------------------------------------------------------------------- MINUTE ", minutes_elapsed(), " | ", self.clock.minute)
			self.lanes.__repr__()
		
		# simulator during official store hours
		for i in range(RUN_TIME):
			# assign a new set of shoppers at the start of each hour until the store closes
			if self.clock.minute == 0:
				print("ADDING NEW SHOPPERS\n\n")
				day_freq = self.shopper_frequency[self.day]
				freq = day_freq[self.clock.hour-DAY_START]
				self.hour_shopper_count = int(((self.avg_shoppers + random.randint(-400,400))/sum(day_freq))*freq)

				for x in range(self.hour_shopper_count):
					self.shoppers.append(Shopper(self.id_generator))

			#### START: figure out where to put manage() - in lanes or in sim? rn moved all to lanes, but need sim vars for manage_delay, elapsed_mins
			### NEXT: test manage() w/ QTIME_CONSTANT delay after activation
			### NEXT: make clock into global var / singleton class

			# mangage lane queues 
			self.lanes.manage(self.clock)
			self.advance()
			debug(self.clock.minute)
			self.clock += timedelta(minutes=1)

		# simulator after store close for lingering shoppers
		while any((shopper.status is not Status.DONE and shopper.status is not Status.INERT) for shopper in self.shoppers):
			self.lanes.manage(self.clock)
			self.advance()
			debug(self.clock.minute)
			self.clock += timedelta(minutes=1)

	# advance simulation by one hour
	def advance(self):
		# advance shopper simulations by one minute
		for index, shopper in enumerate(self.shoppers):
			if shopper.status is Status.QUEUEING:
				if shopper.queue is None:
					self.lanes.push(shopper)				
			elif shopper.status is Status.INERT or Status.SHOPPING:
				shopper.advance(self.clock)
			elif shopper.status is Status.CHECKOUT or shopper.status is Status.DONE:
				continue

		# update lane simulations by one minute
		self.lanes.advance(self.clock)
		
class Shopper:
	def __init__(self, Auto_ID):
		self.begin 			= random.randint(0,60)
		self.browse 		= None
		self.cart 			= []
		self.cart_size  	= None
		self.count 			= random.randint(SHOPPER_MIN,SHOPPER_MAX)	
		self.id 			= Auto_ID.generate()
		self.queue  		= None
		self.queue_time 	= None
		self.status 		= Status.INERT
		self.total			= 0.0


	def publishQueueTime(self, clock, total_qs):
		qt1 = queuetime(queue_num=self.queue, stamp=clock, q_time=self.queue_time, total_qs=total_qs)
		qt1.save()

	def addToCart(self, item):
		session = Session()
		row = session.query(inventory).filter(inventory.grp_id==item).first()
		row.shelved_stock -=1
		row.cart_stock +=1
		self.cart.append(item)
		endSession(session)

	def advance(self, clock):

		if self.status is Status.INERT:
			if clock.minute == self.begin:
				self.status = Status.SHOPPING
				return

		elif self.status is Status.SHOPPING:
			# finished shopping trip, set status to queueing
			if self.count <= len(self.cart):
				self.browse = None
				self.cart_size = len(self.cart)

				if self.cart_size == 0:
					self.status = Status.DONE
				else:
					self.status = Status.QUEUEING
				return

			# advance SHOPPING shoppers
			else:
				
				# choose selection_freq for next set of items
				if self.browse is None:
					count = 0
					selection_freq = random.choice([0.33, 0.5])
					# selection_freq = random.choice([0.33, 0.5, 1, 2, 3, 4, 5])

					if selection_freq == 0.33:
						count = 3
					elif selection_freq == 0.5:
						count = 2
					elif selection_freq == 1:
						count = 1
					else:
						self.browse = selection_freq -1
						return

					for i in range(count):
						item = self.shop()
						if item is None:	# skip if out of stock
							continue
						self.addToCart(item)

				# time to add item to cart
				elif self.browse is 0:
					item = self.shop()
					if item is None:	# skip if out of stock
						return
					self.addToCart(item)

				# still browsing
				else: 
					self.browse -=1
		else:
			return

	def shop(self):
		session = Session()
		category = random.randint(1,CATEGORY_COUNT)
		item = session.query(product).filter(product.category==category).order_by(func.random()).first()

		# keep shopping if desired item is out of stock
		stock = session.query(inventory.shelved_stock).filter(inventory.grp_id==item.grp_id).first().shelved_stock			

		# if item is out of stock, pick a new item
		i = 0
		while(stock == 0):
			category = random.randint(1,CATEGORY_COUNT)
			item = session.query(product).filter(product.category==category).order_by(func.random()).first()
			stock = session.query(inventory.shelved_stock).filter(inventory.grp_id==item.grp_id).first().shelved_stock
			
			if(stock == 0):
				i+=1
			if(i==4):
				endSession(session)
				return None

		item = item.grp_id
		endSession(session)
		return item

	def __repr__(self):
		s = '<shopper[%d]: ' % (self.id)

		# status
		if self.status is Status.INERT:
			s+='INERT >'
			# print(s)
		elif self.status is Status.SHOPPING or self.status is Status.CHECKOUT:
			if self.status is Status.SHOPPING:
				s+='SHOPPING %d items / %d ---   cart[' %(len(self.cart), self.count)
			else:
				s+='CHECKOUT %d items ---   cart[' %(len(self.cart))
			
			session = Session()
			for each in self.cart:
				s = s + str(each) + ", "
			endSession(session)
			s = s+ ']>' 			 # ----  Browse = ' + str(self.browse) + ", Count = " + str(self.count)
		elif self.status is Status.QUEUEING:
			s= s+'QUEUEING --- [lane ' + str(self.queue) + ", queue time "+ str(self.queue_time) +"]>"
		else:
			s+='DONE >'
		
		print(s)

# a single lane contains: a queue and max # of items checked out per minute
class SingleLane:
	def __init__(self):
		self.queue = deque()
		self.items_per_min = None		
		## ADD: property for assigned employee

	def reset(self):					
		## CHANGE:  this should be based on the assigned employee's checkout speed
		self.items_per_min = random.randint(CHECKOUT_MIN, CHECKOUT_MAX)		

# a list of lane objects, advances lanes by one time step
class Lane:
	def __init__(self):
		self.lanes			= []
		self.num_lanes 		= 0
		self.max 			= MAX_LANES

		for i in range(NUM_LANES):
			L = SingleLane()
			L.reset()
			self.lanes.append(L)
			self.num_lanes += 1

	# return index of shortest lane
	def shortest(self):
		min_index, min_count = None, None
		for i, lane_object in enumerate(self.lanes):
			index, count = i, len(lane_object.queue)
			if min_index is None or count < min_count:
				min_index, min_count = index, count
			if min_count is 0:
				break
		print("*** SELECTED lane: %d w/ %d shoppers" % (min_index, min_count))
		return min_index

	# push shopper to shortest queue
	def push(self, shopper):
		index = self.shortest()
		shopper.queue = index
		self.lanes[index].queue.append(shopper)
		shopper.queue_time = 0
		print("*** PUSHED shopper %d w/ %d items into lane %d" % (shopper.id, len(shopper.cart), index))

	# pop shopper from queue index
	def pop(self, index):
		self.lanes[index].queue.popleft() 
		print("*** POPPED shopper %d from lane %d" % (shopper.id, index))  

	# calculates and returns the current average queue length
	def avg_qlen(self):
		length = 0
		for queue_obj in self.lanes:
			length += len(queue_obj.queue)
		return round(length / self.num_lanes)

	# caclculates and returns the average queue time over the past QTIME_CONSTANT minutes
	def avg_qtime(self, clock):
		qtime, results = 0, 0
		time = clock - timedelta(minutes=QTIME_CONSTANT)
		avg_qtime = session.execute(
			"SELECT AVG(q_time) FROM queuetime WHERE stamp>=:time",
			{"time": time}
		).first()[0]

		if avg_qtime is None:
			return 0
		else:
			return round(avg_qtime)
	
	# open more lanes and redistribute customers to these lanes
	def expand(self, avg_qlen, avg_qtime):

		# preliminary calculations
		wait_per_person = avg_qtime / (avg_qlen -1)
		ideal_qlen = round(IDEAL_QTIME / wait_per_person)
		delta_qlen = avg_qlen - ideal_qlen
		excess_ppl = delta_qlen * self.num_lanes
		num_new_lanes = round(excess_ppl / ideal_qlen)

		print("EXPAND STATS: wait_per_person=%d, ideal_qlen=%d, delta_qlen=%d, excess_ppl=%d, num_new_lanes=%d" \
			% (wait_per_person, ideal_qlen, delta_qlen, excess_ppl, num_new_lanes))

		# append new lanes
		qcount_old = self.num_lanes
		for i in range(num_new_lanes):
			L = SingleLane()
			L.reset()				## CHANGE: employee assignment should determine checkout speed
			self.lanes.append(L)
			self.num_lanes += 1

		# redistribute customers
		new_lane_index = qcount_old
		old_lane_index = 0;

		for i in range(qcount_old):
			q = self.lanes[i].queue

			if len(q) == 1: 
				continue

			# redistribute to new lanes while they have space
			while len(q)>ideal_qlen and new_lane_index<self.num_lanes:
				shopper = q.pop()
				laneq = self.lanes[new_lane_index].queue 
				laneq.append(shopper)
				if(len(laneq) >= ideal_qlen):
					new_lane_index +=1

			# redistribute remaining customers to all lanes one-by-one
			while len(q)> ideal_qlen:
				if i == old_lane_index:
					old_lane_index+=1
					break
				shopper = q.pop()
				laneq = self.lanes[old_lane_index].queue 
				laneq.append(shopper)
				old_lane_index+=1

			print("\n")
			self.__repr__()

				
	# close  lanes and redistribute customers to open lanes
	def collapse(self, qlen, qtime):
		###  NEXT: write collapse()
		pass
		# append x more lanes

		# assign employee to lane

		# redistribute customers

	# closes or opens lanes for optomized productivity (lower wait times and labor costs). Called periodically by day sim.
	def manage(self, clock, manage_delay):				## CHANGE: clock will become a global variable. maybe a singleton class? 
		if clock.hour==10 and clock.minute<10:
			return

		if self.manage_delay is None:
			qlen = self.avg_qlen()
			qtime = self.avg_qtime(clock)
			result = False

			if qtime<QTIME_MIN:
				# self.collapse(qlen, qtime)
				print("\t\t.................................................................... collapse()")
				result = True
			elif qtime>QTIME_MAX and qlen>1:
				self.expand(qlen, qtime)
				print("\t\t.................................................................... expand()")
				result = True
			else:
				print("\t\t.................................................................... ideal :)")

			if result is True:
				self.manage_delay = 0

		else :
			self.manage_delay += 1
			if self.manage_delay == QTIME_CONSTANT:
				self.manage_delay = None

		return
		

	# checkout up to x items in in a single cart within a single lane. 
	# if less than x items are checked out, returns the difference
	def checkout_cart(self, x, lane, clock):
		assert len(lane) != 0    # precondition: lane must have shoppers to checkout, should not call checkout_cart() if False

		shopper 		= lane.popleft()
		shopper.status 	= Status.CHECKOUT
		cart 			= shopper.cart
		session 		= Session()

		print("\t*** CHECKING OUT <shopper %d> with %d items " % (shopper.id, len(cart)))

		while (x != 0 and len(cart) != 0):

			# lookup item price
			item = cart.pop(0)
			price = session.execute(
					"SELECT price FROM price WHERE grp_id=:id;",
					{"id": item}
				).first()[0]

			# reduce item inventory
			r = session.execute(
				"UPDATE inventory SET cart_stock=cart_stock-1 WHERE grp_id=:id;",
				{"id": item}
			)

			# update total, update cart
			shopper.total += price
			x -= 1

		if len(cart) == 0:
			# add total to revenue table
			print("\t*** TOTAL = $%d" % (shopper.total))

			# session.execute(
			# 	"INSERT INTO revenue (stamp, value) VALUES (:stamp, :value)",
			# 	{"stamp": clock, "value": shopper.total}
			# )

			# publish revenue to db
			rev = revenue(stamp=clock, value=shopper.total)
			session.add(rev)

			# publish shopper's queue time to db
			qt = queuetime(queue_num=shopper.queue, stamp=clock, q_time=shopper.queue_time, total_qs=self.num_lanes)
			session.add(qt)
			shopper.status = Status.DONE
		else:
			# cart still has items, put back
			lane.appendleft(shopper)

		endSession(session)
		return x

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

	def __repr__(self):
		for index, lane_obj in enumerate(self.lanes):
			assert lane_obj is not None
			s = "<LANE %d: %d shoppers --- [" % (index, len(lane_obj.queue))
			if len(lane_obj.queue) != 0:
				for shopper in lane_obj.queue:
					s+="s%d, " %(shopper.id)
			s+= "]>"
			print(s)

# class Stats:

# class Day_Simulator:













