from base import Engine, Session, Base
from models import inventory, product, category, price, revenue, cost, employee, role
import random

class simulator:
	def __init__(self, scale, behavior):
		# Time step for a faster than real-time simulation
		self.scale = scale

		# ---------------------------------------------------------------------------- SHOPPERS
		# Percentage busyness per hour per day --> Day: { hr: % busyness }
		self.shopper_frequency = {42, 11:58, 12:74, 13:84, 14:85, 15:81, 16:79, 17:80, 18:78, 19:69, 20:54, 21:37, 22:22
			"Sunday": {10:},
			"Monday": {10:47, 11:55, 12:59, 13:58, 14:58, 15:65, 16:74, 17:92, 18:97, 19:88, 20:67, 21:43, 22:22},
			"Tuesday": {10:43, 11:52, 12:56, 13:58, 14:61, 15:70, 16:84, 17:97, 18:100, 19:89, 20:67, 21:43, 22:23},
			"Wednesday": {10:42,11:46, 12:46, 13:45, 14:48, 15:59, 16:76, 17:84, 18:80, 19:69, 20:58, 21:43, 22:23},
			"Thursday": {10:40, 11:44, 12:45, 13:46, 14:52, 15:62, 16:74, 17:83, 18:83, 19:74, 20:58, 21:39, 22:23},
			"Friday": {10:37, 11:47, 12:57, 13:62, 14:63, 15:66, 16:74, 17:82, 18:84, 19:75, 20:59, 21:40, 22:22},
			"Saturday": {10:51, 11:63, 12:69, 13:70, 14:67, 15:66, 16:68, 17:72, 18:73, 19:66, 20:51, 21:33, 22:17},
		}

		# average number of shoppers per day
		self.shopper_count = 2200

		# Probability a shopper will take x minutes to browse for a single item 
		self.browsing = {}

		self.cart = {}
		self.max_items = 

	def simulate(self):


		# ---------------------------------------------------------------------------- EMPLOYEES
		# some employee data here


class shopper:
	def __init__(self, num_products):
		# self.scale = scale
		self.cart = {}
		self.max_items = 200
		self.prod_count = num_products

		# Random time within a given hour a shopper will start shopping
		self.begin =

	def shop(self):
		x = random.randint(0,200)
		browse = random.randint(1,8)



	def checkout(self):



# SHOPPER(scale)
# - data
#     - cart: dictionary
#     - items: probability curve
#     - browse time: probability curve
# - functions
#     - shop
#         - randomly choose x items to be purchased  (1-200 items)
#         - randomly select browse time y (1-10 minutes)
#         - select category to purchase from 
#         - select random item, decide to purchase 1 of 2 (if two, deduct from x)
#         - browse y minutes w/ scale
#         - add to cart
#         - repeat until x items selected
#     - checkout
#         - select shortest checkout lane
#         - add cart to lane queue