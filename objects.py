from base import Engine, Session, Base
from models import inventory, product, category, price, revenue, cost, employee, role
import random
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.sql.expression import func
from collections import deque
import time


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

# ------------------------------------------------------------------------------------------------ PARAMATERS
CHECKOUT_MIN	= 5
CHECKOUT_MAX	= 10
NUM_LANES		= 5
RUN_TIME		= 30
SHOPPER_MIN		= 10	# number of items a shopper will attempt to purchase
SHOPPER_MAX		= 50	


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

	# store simulation for a single day, continues until all shoppers in the store complete their trips
	def run(self):

		def debug(i):
			print("-------------------------------------------------------------------- MINUTE ", i)
			print("SHOPPERS ---- ")
			self.shoppers.sort(key=lambda x: x.status.value, reverse=True)
			for shopper in self.shoppers:
				if shopper.status != Status.INERT and shopper.status != Status.DONE:
					s = "<shopper %d: "%(shopper.id) + str(shopper.status) 
					if shopper.queue_time is not None:
						s+= "__%d"%(shopper.queue_time)
					s += "> --- %d items / %d planned" %(len(shopper.cart), shopper.count) 
					if shopper.status == Status.QUEUEING or shopper.status == Status.CHECKOUT:
						if shopper.queue is not None:
							s += " --- Lane %d" % (shopper.queue)
					s += ">"
					print(s)
			self.shoppers.sort(key=lambda x: x.id, reverse=True)
			self.lanes.__repr__()
			# time.sleep(0.5)
		
		for i in range(RUN_TIME):

			# assign a new set of shoppers at the start of each hour until the store closes
			if self.clock.minute == 0:
				# display prev hr stats
				day_freq = self.shopper_frequency[self.day]
				freq = day_freq[self.clock.hour-DAY_START]
				self.hour_shopper_count = int(((self.avg_shoppers + random.randint(-400,400))/sum(day_freq))*freq)

				for x in range(self.hour_shopper_count):
					self.shoppers.append(Shopper(self.id_generator))

			self.advance()
			debug(i)

		i = 1
		while any((shopper.status is not Status.DONE and shopper.status is not Status.INERT) for shopper in self.shoppers):
			self.advance()
			debug(RUN_TIME + i)
			i+=1

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
		self.clock += timedelta(minutes=1)

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

	def reset(self):
		self.items_per_min = random.randint(CHECKOUT_MIN, CHECKOUT_MAX)

# a list of lane objects, advances lanes by one time step
class Lane:
	def __init__(self):
		self.lanes			= []
		for i in range(NUM_LANES):
			L = SingleLane()
			L.reset()
			self.lanes.append(L)

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
			session.execute(
				"INSERT INTO revenue (stamp, value) VALUES (:stamp, :value)",
				{"stamp": clock, "value": shopper.total}
			)
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
			if len(lane_obj.queue) != 0:
				s = "<LANE %d: %d shoppers --- [" % (index, len(lane_obj.queue))
				for shopper in lane_obj.queue:
					s+="shopper %d, " %(shopper.id)
				s+= "]>"
				print(s)

# class Stats:

# class Day_Simulator:













