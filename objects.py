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


# ------------------------------------------------------------------------------------------------ CLASSES

# A class for generating unique IDs for shoppers and employeesover the lifetime of the program 
class Auto_ID:
	def __init__(self):
		self.shopper_val = None
		self.employee_val = None
			
	def generate_sid(self):
		if self.shopper_val is None:
			self.shopper_val = 0
		else:
			self.shopper_val +=1
		return self.shopper_val

	def generate_eid(self):
		if self.employee_val is None:
			self.employee_val = 0
		else:
			self.employee_val +=1
		return self.employee_val

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

	# TODO: write employee and employee group classes before writing restock()
	def restock(self):
		session = Session()
		restock_proxy = session.execute(
			"SELECT grp_id FROM inventory WHERE shelved_stock<:min ORDER BY grp_id ASC",
			{"min": RESTOCK_THRESHOLD}
		)

		restock = []
		for row in restock_proxy:
			restock.append(row.grp_id)

		# need to compare to employee_restock[] and employee[]
	

	# store simulation for a single day, continues until all shoppers in the store complete their trips
	def run(self):
		def minutes_elapsed():
			return int((self.clock - self.start).seconds / 60)

		def debug(i):
			print("-------------------------------------------------------------------------------------------------------- TIME ELAPSED ", end="")
			print("%02d:%02d, | %02d" % (int(minutes_elapsed()/60), minutes_elapsed()%60, self.clock.minute))
			self.shoppers.sort(key=lambda x: x.status.value, reverse = True)
			for shopper in self.shoppers:
				shopper.__repr__()
			self.shoppers.sort(key=lambda x: x.id, reverse = False)
			self.lanes.__repr__()
		
		# simulator during official store hours
		for i in range(RUN_TIME):
			# assign a new set of shoppers at the start of each hour until the store closes
			if self.clock.minute == 0:
				print("\t\t******************\tADDING NEW SHOPPERS\t******************")
				time.sleep(1)
				day_freq = self.shopper_frequency[self.day]
				freq = day_freq[self.clock.hour-DAY_START]
				self.hour_shopper_count = int(((self.avg_shoppers + random.randint(-400,400))/sum(day_freq))*freq)

				for x in range(self.hour_shopper_count):
					self.shoppers.append(Shopper(self.id_generator))

			# mangage lane queues 
			self.lanes.manage(self.clock)
			self.advance()
			if i > 50:
				self.restock()
			self.shoppers = [shopper for shopper in self.shoppers if shopper.status is not Status.DONE]
			debug(self.clock.minute)
			self.clock += timedelta(minutes=1)

		# simulator after store close for lingering shoppers
		while any((shopper.status is not Status.DONE and shopper.status is not Status.INERT) for shopper in self.shoppers):
			self.lanes.manage(self.clock)
			self.advance()
			self.shoppers = [shopper for shopper in self.shoppers if shopper.status is not Status.DONE]
			debug(self.clock.minute)
			self.clock += timedelta(minutes=1)

	# advance simulation by one hour
	def advance(self):
		
		# advance shopper simulations by one minute
		for index, shopper in enumerate(self.shoppers):
			assert (shopper.status is not Status.DONE)
			if shopper.status is Status.QUEUEING:
				if shopper.queue is None:
					self.lanes.push(shopper)				
			elif shopper.status is Status.INERT or Status.SHOPPING:
				shopper.advance(self.clock)
			else: # shopper.status is Status.CHECKOUT or
				continue

		# update lane simulations by one minute
		self.lanes.advance(self.clock)
		self.shoppers = [shopper for shopper in self.shoppers if shopper.status is not Status.DONE]
		
class Shopper:
	def __init__(self, Auto_ID):
		self.begin 			= random.randint(0,60)
		self.browse 		= None
		self.cart 			= []
		self.cart_size  	= None
		self.count 			= random.randint(SHOPPER_MIN,SHOPPER_MAX)	
		self.id 			= Auto_ID.generate_sid()
		self.queue  		= None
		self.queue_time 	= None
		self.status 		= Status.INERT
		self.total			= 0.0

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


	###		NEXT: implement restocking --> run cProfile profiler on program to probe runtime bottlenecks in shop()
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
		if self.status is Status.INERT or self.status is Status.DONE:
			pass
		else:
			s = '<shopper %d>: ' % (self.id)
		
			if self.status is Status.SHOPPING or self.status is Status.CHECKOUT:
				if self.status is Status.SHOPPING:
					s+='SHOPPING %d items / %d ' %(len(self.cart), self.count)
					# s+='SHOPPING %d items / %d ---   cart[' %(len(self.cart), self.count)
				else:
					s+='CHECKOUT %d items / %d ' %(len(self.cart), self.count)
					# s+='CHECKOUT %d items ---   cart[' %(len(self.cart))
				
				# session = Session()
				# for each in self.cart:
				# 	s = s + str(each) + ", "
				# endSession(session)
				# s = s+ ']>' 			 # ----  Browse = ' + str(self.browse) + ", Count = " + str(self.count)
			else: # self.status is Status.QUEUEING
				s= s+'QUEUEING --- [lane ' + str(self.queue) + ", qtime = "+ str(self.queue_time) +"]"
			
			print(s)

# a single lane contains: a queue and max # of items checked out per minute
class SingleLane:
	def __init__(self):		 			## 	FIX: init__(self, workers):, where workers is the pool of employees
		self.queue = deque()
		## ADD: self.emp = workers.get()
		self.items_per_min = None		## FIX: = self.emp.cashier_speed


	## REMOVE FUNCTION reset()
	def reset(self):					
		self.items_per_min = random.randint(CHECKOUT_MIN, CHECKOUT_MAX)		

# a list of lane objects, advances lanes by one time step
class Lane:
	def __init__(self):
		self.lanes			= []
		self.open_lanes		= 0	
		self.manage_delay   = None

		for i in range(MAX_LANES):
			L = SingleLane()
			L.reset()
			self.lanes.append(L)
		self.open_lanes = MIN_LANES			

	# return index of shortest lane
	def shortest(self):
		# lane w/ fewest items to check out
		min_index, min_count = None, None
		for i in range(self.open_lanes):
			index, count = i, self.total_items(i)
			if min_index is None:
				min_index = index
				min_count = count
			elif count < min_count:
				min_index = index
				min_count = count
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
		return round(length / self.open_lanes)

	# caclculates and returns the average queue time over the past QTIME_RANGE minutes
	def avg_qtime(self, clock):
		qtime, results = 0, 0
		time = clock - timedelta(minutes=QTIME_RANGE)
		avg_qtime = session.execute(
			"SELECT AVG(q_time) FROM queuetime WHERE stamp>=:time",
			{"time": time}
		).first()[0]

		if avg_qtime is None:
			return 0
		else:
			return round(avg_qtime)

	def total_items(self, lane_no):
		q = self.lanes[lane_no].queue
		count = 0
		for shopper in q:
			count += shopper.cart_size
		return count

	def total_shoppers(self):
		count = 0
		for lane_obj in self.lanes:
			count += len(lane_obj.queue)
		return count

	def avg_alt(self):
		total = 0
		for i in range(self.open_lanes):
			items = self.total_items(i)
			mins = items / self.lanes[i].items_per_min
			total += mins

		return total / self.open_lanes

	def empty_lane_count(self):
		count = 0
		for lane_obj in self.lanes:
			if len(lane_obj.queue) == 0:
				count +=1
		return count
	
	# open more lanes and redistribute customers to these lanes
	def expand(self, avg_qlen, avg_qtime):
		assert (self.open_lanes != MAX_LANES)
		ideal_qlen = None

		# calculate number of lanes to add
		if avg_qlen == 0:
			print("EXPAND STATS: avg_qlen == 0 --> return")
			return
		elif avg_qlen == 1:
			num_new_lanes = round(self.open_lanes / 3)
			print("EXPAND STATS: open_lanes=%d, num_new_lanes=%d" \
				% (self.open_lanes, num_new_lanes))
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
			print("EXPAND STATS: open_lanes=%d, wait_per_person=%d, ideal_qlen=%d, delta_qlen=%d, excess_ppl=%d, num_new_lanes=%d" \
				% (self.open_lanes, wait_per_person, ideal_qlen, delta_qlen, excess_ppl, num_new_lanes))

		# CHECK MAX BOUNDS 
		if num_new_lanes + self.open_lanes > MAX_LANES:
			num_new_lanes = MAX_LANES - self.open_lanes

		# append new lanes
		qcount_old = self.open_lanes
		for i in range(num_new_lanes):
			self.open_lanes += 1
			self.lanes[self.open_lanes-1].reset()
		assert(self.open_lanes <= MAX_LANES)

		# redistribute customers
		new_lane_index = qcount_old
		old_lane_index = 0;
		for i in range(qcount_old):
			q = self.lanes[i].queue
			if len(q) == 1: 
				continue

			# redistribute to new lanes while they have space
			if ideal_qlen is not None:
				while len(q)>ideal_qlen and new_lane_index<self.open_lanes:
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


	# closes or opens lanes for optomized productivity (lower wait times and labor costs). Called periodically by day sim.
	def manage(self, clock):				## CHANGE: clock will become a global variable. maybe a singleton class? 
		if clock.hour==10 and clock.minute<15:
			# print("\t\t.................................................................... start_delay %d :)" % (clock.minute))
			return

		if self.manage_delay is None:
			qlen = self.avg_qlen()
			qtime = self.avg_qtime(clock)
			qalt = self.avg_alt()
			num_shoppers = self.total_shoppers()

			if (num_shoppers<round(self.open_lanes/2) or qalt<QTIME_MIN) and self.open_lanes>MIN_LANES:
				# print("\t\t.................................................................... collapse() %d" %(qalt))
				self.collapse(qlen, qalt)
				self.manage_delay = 0

			elif qalt>QTIME_MAX and num_shoppers>self.open_lanes and self.open_lanes<MAX_LANES:
				# print("\t\t.................................................................... expand() %d" %(qalt))
				self.expand(qlen, qalt)
				self.manage_delay = 0

			else:
				pass
				# print("\t\t.................................................................... ideal :) / avg_qtime %d" %(qalt))

		else :
			# print("\t\t.................................................................... manage_delay %d" % (self.manage_delay))
			self.manage_delay += 1
			if self.manage_delay == QTIME_RANGE:
				self.manage_delay = None
		

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

			# publish revenue to db
			rev = revenue(stamp=clock, value=shopper.total)
			session.add(rev)

			# publish shopper's queue time to db
			qt = queuetime(queue_num=shopper.queue, stamp=clock, q_time=shopper.queue_time, total_qs=self.open_lanes)
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
		print("%d open lanes, %d total lanes" % (self.open_lanes, len(self.lanes)))
		for index, lane_obj in enumerate(self.lanes):
			if len(lane_obj.queue) >= 1:
				s = "<LANE %d: %d shoppers --- [" % (index, len(lane_obj.queue))
				if len(lane_obj.queue) != 0:
					for shopper in lane_obj.queue:
						s+="s%d, " %(shopper.id)
				s+= "]>"
				print(s)


####	START: write Employee and Employee Group classes
# a single employee object
class Emp:
	class Shift:
		cashier 		= 0
		restock 		= 1
		toss 			= 2
		unload			= 3 
		br 				= 4 
		off				= 5


	def __init__(self, id):
		self.id 				= Auto_ID.generate_eid()
		self.wage 				= random.randint(8, 13)							# pay per hour
		self.cashier_speed 		= random.randint(CHECKOUT_MIN, CHECKOUT_MAX)	# items per min
		self.restock_speed 		= random.randint(RESTOCK_MIN, RESTOCK_MAX)		# items per min	
		self.unload_speed 		= random.randint(UNLOAD_MIN, UNLOAD_MAX)		# items per min	
		self.toss_speed			= random.randint(TOSS_MIN, TOSS_MAX)			# items per min	
		self.minutes_worked 	= 0	
		self.current			= None		# current shift
		self.scheduled			= None		# scheduled shift
		self.lane_no 			= None		# lane number if assigned to cashier
		self.prod 				= None		# grp_id of current product employee is restocking, unloading, or tossing. None if n/a

	def schedule(self, shift):
		self.scheduled = shift

	def assign(self, shift):
		self.current = shift


	def advance():
		pass

	def product(self):
		if self.prod is not None:
			return True


	def restock(self):
		# confirm  self.prod is set, else set it
		# if shelved_stock < full restock by self.restock_speed items  ---- else set self.prod & restock by self.restock_speed items
		pass

	def unload(self):
		# confirm self.prod is set, else set it
		pass

	def toss(self):
		pass


	
# class of employees and functions to manipulate them
class Employees:
	def __init__():
		self.employees = []
		self.available = []


		for i in range(NUM_EMPLOYEES):
			e = Emp()
			employees.append(e)

	# advance employee by one minute
	def advance(self):
		pass



# class Stats:

# class Day_Simulator:













