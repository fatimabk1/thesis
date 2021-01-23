\c store;

-- INSERT STARTER DATA INTO TABLES FROM EXCEL SHEETS
-- \copy tbl_category FROM 'store/data/category.csv' WITH DELIMITER ',' CSV HEADER;
-- \copy tbl_product FROM 'store/data/product.csv' WITH DELIMITER ',' CSV HEADER;
-- \copy tbl_inventory FROM 'store/data/inventory-2.csv' WITH DELIMITER ',' CSV HEADER;
-- \copy tbl_employee FROM 'store/data/employee.csv' WITH DELIMITER ',' CSV HEADER;

-- Add foreign keys
ALTER TABLE tbl_sold ADD CONSTRAINT fk1_sold FOREIGN KEY (grp_id) REFERENCES tbl_product (grp_id);
ALTER TABLE tbl_product ADD CONSTRAINT fk1_prod FOREIGN KEY (category) REFERENCES tbl_category (id);
ALTER TABLE tbl_inventory ADD CONSTRAINT fk1_inv FOREIGN KEY (grp_id) REFERENCES tbl_product (grp_id);
ALTER TABLE tbl_cart ADD CONSTRAINT fk2_cart FOREIGN KEY (inventory_id) REFERENCES tbl_inventory (id);
ALTER TABLE tbl_cart ADD CONSTRAINT fk1_cart FOREIGN KEY (shopper_id) REFERENCES tbl_shopper (id);

-- correct primary key starting index (due to CSV inserts)
-- ALTER SEQUENCE tbl_inventory_id_seq RESTART WITH 14;

-- CREATE VIEW view_stocked 
-- AS SELECT a.grp_id, b.max_shelved_stock AS max_shelf, a.SUM(shelved_stock) AS curr_shelf, max_shelf - curr_shelf AS shelf_space
--           b.max_back_stock AS max_back, SUM(a.back_stock) AS curr_back, max_back - curr_back as back_space,
--           SUM(a.pending_stock) AS curr_pending
-- FROM tbl_inventory a, tbl_product b
-- GROUP BY grp_id;


-- -- dates don't matter
-- CREATE VIEW view_restock
-- AS SELECT a.grp_id, a.curr_back, a.curr_shelf, a.shelf_space,
--           b.restock_threshold, MIN(a.curr_back, a.shelf_space) AS quantity
-- FROM view_stocked a, tbl_product b
-- WHERE a.curr_shelf < b.restock_threshold
-- GROUP BY grp_id
-- ORDER BY quantity;


# inventory list for selecting a grp & inv
inv_lst = session.query(ModelInventory)\
    .filter(ModelInventory.shelved_stock > 0)\
    .filter(ModelInventory.sell_by >= today)\
    .group_by(ModelInventory.grp_id)\
    .order_by(ModelInventory.sell_by)\
    .order_by(ModelInventory.shelved_stock)\
    .order_by(ModelInventory.back_stock).all()
    

-- -- dates matter (AVAILABLE == TODAY?)
-- CREATE VIEW view_unload
-- AS SELECT a.grp_id, b.curr_pending, b.curr_pending / a.lot_quantity AS quantity
-- FROM tbl_inventory a, view_stocked b
-- WHERE available == today  -- HOW TO MAKE TODAY A VARIABLE? RUN AT THE START OF EACH DAY?
-- GROUP BY grp_id; 


-- -- dates matter (EXPIRED <= TODAY?)
-- CREATE VIEW view_toss
-- AS SELECT a.grp_id, 
-- FROM tbl_product a, view_stocked b
-- WHERE sell_by <= today   -- HOW TO MAKE TODAY A VARIABLE? RUN AT THE START OF EACH DAY?
-- GROUP BY grp_id;


