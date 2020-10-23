
# Run the Grocery Store Simulator

Open terminal, make sure you are CD'd into desktop

In terminal, run: 

* git clone https://github.com/fatimabk1/thesis.git
* mkvirtualenv grocery_sim
* workon grocery_sim
* pip install requirements.txt
* psql
* \i db_init.sql
* \q
* ./simulate.sh

Follow instructions in simulate.sh terminal output to do a test run of the program thus far.


# File Overviews:
simulate.sh is a shell script that automates the process of running simulations over and over
prog.py 	is a program that runs the simulation
objects.py 	contains all the objects used by the simulation, including the simulation
models.py   is the database tables ORM using SQLAlchemy
db_init.sql is an SQL instruction list to build and populate the database and its tables


# Existing Features:
## Shopper
* shoppers browse for 1, 2, or 3 minutes for each item
* shoppers select a random item from a random category
* shoppers can add items to cart
* shoppers shop for a random number of items within a given range
* shoppers start shopping / enter the store at a random minute within a given hour
* shoppers track their own data (queue time, cart size, cart contents, id, browse time, status, total checkout cost)

## SingleLane
* singleLanes have a deque of shoppers needing to be checked out

## Lane
* Lane had a list of all lanes, the number of all (consecutive) open lanes 
* shoppers are added to the shortest open lane
* shoppers are removed from the lane when done checking out
* lanes are expanded (closed lanes are opened) or collapsed (open lanes are closed) to maintain an acceptable queue time and lane length for customers. Queing customers are redistributed from closed lanes to the consecutive set of open lanes (starting from lane 0). Customers checking out in a closed lane will finish checking out, but that lane will not accept new customers.
* lanes carry out partial and continuous checkouts. Lanes can checkout x items a minute * they can partly check out a customer or check out multiple customers.


## Simulator
* Simulator releases new shoppers at the top the hour, according to google maps data on Walmart visitor frequency
* Simulator time step is one minute
* Simulator advances shoppers each time step
* Simulator advances lanes each time step
* Simulator updates its clock
* Simulator runs for runtime minutes whilDay-Simulator releases new shoppers at the top the hour, according to google maps data on Walmart visitor frequency
Day-Simulator time step is one minute
Day-Simulator advances shoppers each time step
Day-Simulator advances lanes each time step
Day-Simulator updates its clock
Day-Simulator runs for runtime minutes while regularly adding customers. After runtime minutes, Simulator runs without adding customers in order to close the store.e regularly adding customers. After runtime minutes, Simulator runs without adding customers in order to close the store.
* 




# Future Features:
## Shopper
* shoppers have browsing and selection behavior that is more natural / less formulaic, with greater variety (something more interesting than random item selection)
* shoppers' selection behavior responds price changes

## SingleLane
* the items per minute checkout speed for a lane should come from its assigned employee

## Lane
* users can set # of lanes at runtime 

## Simulator
* Simulator issues 30 minute and 15 minute before closing warnings and shoppers experience a reduced browse time correspodingly.


more future features: https://docs.google.com/document/d/1HDub2Vvo0DocS4ybc*InAagNey73RxO0sH*Pc7q98iI/edit?usp=sharing

