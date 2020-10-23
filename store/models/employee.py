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

