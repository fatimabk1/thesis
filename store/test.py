# -------------------------------------------- Product
# @provide_session
# def print_product(grp_id, session=None):
#     r = session.execute(
#         "SELECT * FROM tbl_product WHERE grp_id=:p",
#         {"p": grp_id})
#     for row in r:
#         keys = row.keys()
#         vals = row.values()
#         x = len(keys)
#         for i in range(x):
#             row = [keys[i], vals[i]]
#             if row[0] is None:
#                 row[0] = "None"
#             if row[1] is None:
#                 row[1] = "None"
#             print("|||", "{: <20} {: <20} ".format(*row))


@provide_session
# def test_product(session=None):
#     products = session.query(ModelProduct).all()
#     if products is None:
#         print("nooooo prudcts lmaooo")
#         exit(1)
#     for prod in products:
#         print("--------------------------------------------------")
#         prod.setup()
#         print_product(prod.grp_id)
#         print("Possible Sell-By dates, today = ", CLOCK)
#         print("\t", prod.generate_sell_by())
#         print("\t", prod.generate_sell_by())
#         print("\t", prod.generate_sell_by())
#         print("\t", prod.generate_sell_by())
#         print("\t", prod.generate_sell_by())
#         print("\t", prod.generate_sell_by())
#         print("sublot_q: ", prod.get_sublot_quantity())
#         print("current price: ", prod.get_price())
#         prod.set_sale()
#         print("sale price: ", prod.get_price())
#         prod.set_regular()
#         print("regular price: ", prod.get_price())
#         print("pop: ", prod.get_popularity())
#         print("pop∆: ", prod.get_popularity_delta())
#         print("None threshold: ", prod.threshold)
#         prod.set_threshold()
#         print("None-set threshold: ", prod.threshold)
#         print("\t~~~DONZO~~~")
#         exit(1)


# ----------------------------------------------------------- Inventory
# @provide_session
# def test_inventory(session=None):
#     initialize()

#     # select_inv()
#     inv_id = select_inv(1)
#     assert(inv_id == 4), "fail: select()"
#     session.commit()

#     # decrement_n() --------------------------------------------
#     inv = session.query(ModelInventory)\
#         .filter(ModelInventory.id == inv_id).one()
#     before = inv.shelved_stock
#     inv.decrement_n(1)
#     after = inv.shelved_stock
#     assert(before == after + 1), "fail: decrement_n()"

#     # toss_list()   --------------------------------------------
#     lst = toss_list()
#     print("toss list: ", lst)
#     assert(len(lst) == 1 and lst[0] == 3), "fail: toss_list()"

#     # toss()        --------------------------------------------
#     # before = session.query(func.count(ModelInventory.id))\
#     #     .filter(ModelInventory.grp_id == 3).one()
#     # toss(3, 33)
#     # after = session.query(func.count(ModelInventory.id))\
#     #     .filter(ModelInventory.grp_id == 3).one()

#     # create_pending() ------------------------------------------
#     before = session.query(func.count(ModelInventory.id))\
#         .filter(ModelInventory.grp_id == 5)\
#         .filter(ModelInventory.pending > 0).one()
#     create_pending(5, 6)
#     after = session.query(func.count(ModelInventory.id))\
#         .filter(ModelInventory.grp_id == 5)\
#         .filter(ModelInventory.pending > 0).one()
#     lst = session.query(ModelInventory)\
#         .filter(ModelInventory.grp_id == 5).all()
#     emptyl = []
#     for each in lst:
#         emptyl.append(each.id)
#     print("\nPending Test, grp 5 with 6 pending entries")
#     lst = emptyl.sort()
#     print(lst)
#     assert(before[0] == 0 and after[0] == 6), "fail: create_pending()"

#     # order_inventory()
#     order_inventory()
#     lst = session.query(ModelInventory)\
#         .filter(ModelInventory.pending > 0)\
#         .order_by(ModelInventory.id).all()
#     order_lst = []
#     for each in lst:
#         order_lst.append(each.id)
#     order_lst.sort()
#     print("\nOrdered Inventory:", order_lst)

#     # restock_list()
#     restock_lst = restock_list()
#     restock_lst.sort()
#     print("\nRestock list: ", restock_lst)

#     # unload_list()
#     unload_lst = unload_list()
#     unload_lst.sort()
#     print("\nUnload list aka PENDING available today: ", unload_lst)

#     # unload()
#     # START: unload is not working
#     # today = date(CLOCK.year, CLOCK.month, CLOCK.day)
#     for grp in unload_lst:
#         # space = available_back_space(grp)
#         unload(grp)
#         # product = session.query(ModelProduct)\
#         #     .filter(ModelProduct.grp_id == grp).one()
#         # inv_lst = session.query(ModelInventory.id)\
#         #     .filter(ModelInventory.grp_id == grp)\
#         #     .filter(ModelInventory.available == today)\
#         #     .order_by(ModelInventory.id).all()
#         # lst = []
#         # for row in inv_lst:
#         #     lst.append(row[0])
#         # inv_lst = lst
#         # print("\nUnloaded %d -- space=%d, max=%d, lot_q=%d" % (
#         #     grp, space, product.max_back_stock, product.lot_quantity))
#         # all_grp = session.query(ModelInventory)\
#         #     .filter(ModelInventory.grp_id == grp)\
#         #     .order_by(ModelInventory.id).all()
#         # for inv in all_grp:
#         #     if inv.id in inv_lst:
#         #         print("\t", inv._repr_(), "-- NEW")
#         #     else:
#         #         print("\t", inv._repr_())

#     # restock()
#     print("\nRestocked Inventory")
#     for grp in restock_lst:
#         inv = session.query(ModelInventory)\
#             .filter(ModelInventory.grp_id == grp)\
#             .order_by(ModelInventory.id).all()
#         restock(grp, 200)


# ----------------------------------------------------------- Shopper & Cart
# @provide_session
# def test_shopper_cart(session=None):
#     initialize()

#     # ======================================================== #
#     # =================== create & __repr__ ================== #
#     # ======================================================== #
#     for i in range(20):
#         s = ModelShopper()
#         session.add(s)
#     session.commit()
#     group = session.query(ModelShopper).all()
#     table = []
#     for s in group:
#         table.append(s.__repr__())
#     print("\n-------------------- SHOPPERS_pre_stat ------------------- ")
#     headers = ["id",
#                "start",
#                "browse",
#                "quota",
#                "cart count",
#                "lane",
#                "qtime",
#                "total",
#                "status"]
#     print(tabulate(table, headers, tablefmt="fancy_grid"))

#     # ======================================================== #
#     # ============== set_status() & get_status() ============= #
#     # ======================================================== #
#     print("\nSET & GET STATUS:")
#     group = session.query(ModelShopper).all()
#     for shopper in group:
#         assert(shopper.get_status() == Status.INERT)
#         shopper.set_status(Status.SHOPPING)
#     session.commit()
#     group = session.query(ModelShopper).all()
#     # table = []
#     for shopper in group:
#         assert(shopper.get_status() == Status.SHOPPING)
#         # table.append(shopper.__repr__())
#     # print("\n-------------------- SHOPPERS_post_stat ------------------- ")
#     # headers = ["id",
#     #            "start",
#     #            "browse",
#     #            "quota",
#     #            "cart count",
#     #            "lane",
#     #            "qtime",
#     #            "total",
#     #            "status"]
#     # print(tabulate(table, headers, tablefmt="fancy_grid"))

#     # ======================================================== #
#     # ===================== reset_browse ===================== #
#     # ======================================================== #
#     print("\nBROWSE_RESET:")
#     sid = group[0].id
#     group[0].reset_browse()
#     session.commit()
#     table = []
#     s = session.query(ModelShopper)\
#         .filter(ModelShopper.id == sid).one()
#     row = s.__repr__()
#     row = [1, row[2]]
#     table.append(row)
#     s.reset_browse()
#     session.commit()
#     s = session.query(ModelShopper)\
#         .filter(ModelShopper.id == sid).one()
#     row = s.__repr__()
#     row = [2, row[2]]
#     table.append(row)
#     s.reset_browse()
#     session.commit()
#     s = session.query(ModelShopper)\
#         .filter(ModelShopper.id == sid).one()
#     row = s.__repr__()
#     row = [3, row[2]]
#     table.append(row)
#     print("\n-------------------- SHOPPERS_browse ------------------- ")
#     headers = ["reset #",
#                "browse_mins"]
#     print(tabulate(table, headers, tablefmt="fancy_grid"))

#     # ======================================================== #
#     # ================ select_grp & print_cart =============== #
#     # ======================================================== #
#     group = session.query(ModelShopper).all()
#     for shopper in group:
#         for i in range(30):
#             shopper.select_grp()
#         print("\tCart filled for shopper {}".format(shopper.id))
#         session.commit()
#         cart.print_cart(shopper.id, session)

#     # ======================================================== #
#     # ======================== scan_n ======================== #
#     # ======================================================== #
#     group = session.query(ModelShopper).all()
#     for shopper in group:
#         shopper.total = cart.get_total(shopper.id)
#         cart.scan_n(shopper.id, 12)
#         session.commit()
#         print("\n-------------------- CHECKOUT_{} ------------------- "
#               .format(shopper.id))
#         cart.print_cart(shopper.id, session)
#         assert(cart.get_size(shopper.id, session) == 30-12)

# @provide_session
# def test_shopper_advance(num_shoppers, runtime, session=None):
#     # seting up inventory & shopper pool
#     inv_lst = session.query(ModelInventory).all()
#     for inv in inv_lst:
#         inv.shelved_stock = 500000
#     session.commit()
#     s = ModelShopper()
#     s.start_min = 1
#     session.add(s)
#     session.commit()

#     const.CLOCK = datetime(2019, 9, 15, 10, 0)
#     headers = ["sid", "status", "start", "browse",
#                "quota", "cart", "lane", "qtime", "total"]

#     for i in range(runtime):
#         group = session.query(ModelShopper).all()
#         group.sort(key=lambda x: x.status)

#         # advance shoppers
#         table = []
#         for shopper in group:
#             shopper.advance(session)
#             assert(session)
#             # table.append(shopper.__repr__())
#             # print(inspect(shopper))
#             shopper.cart_count = cart.get_size(shopper.id)
#             print(shopper.cart_count)
#             session.commit()
#             assert(shopper.cart_count is not None)
#         # session.commit()
#         # print(tabulate(table, headers))
#         table = []

#         # advance between statuses & print stats
#         group = session.query(ModelShopper).all()
#         group.sort(key=lambda x: x.status)
#         for shopper in group:
#             stat = shopper.get_status()

#             if stat is Status.QUEUEING:
#                 shopper.qtime += 1
#                 table.append(shopper.__repr__())
#                 shopper.set_status(Status.CHECKOUT)

#             elif stat is Status.CHECKOUT:
#                 remainder = cart.scan_n(shopper.id, 12)
#                 table.append(shopper.__repr__())
#                 if remainder == 0:
#                     shopper.set_status(Status.DONE)

#             elif stat is Status.DONE:
#                 table.append(shopper.__repr__())
#                 session.delete(shopper)

#             else:
#                 table.append(shopper.__repr__())

#         print("\n\n--------------------------------------------------------------------------------------------------- {0:02}:{1:02}"
#               .format(const.CLOCK.hour, const.CLOCK.minute))
#         print(tabulate(table, headers=headers))
#         print("\n")
#         session.commit()
#         const.CLOCK = const.CLOCK + timedelta(minutes=1)

#         # loop exit condition
#         group = session.query(ModelShopper).all()
#         if not group:
#             break
