from constants import *

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