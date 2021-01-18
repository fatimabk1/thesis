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
