from constants import *

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
