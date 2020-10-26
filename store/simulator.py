from constants import *

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
