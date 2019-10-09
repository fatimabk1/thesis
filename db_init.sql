-- SET UP THE DATABASE 
-- CREATE DATABASE store;
-- \c store;

-- SET UP TABLE SCHEMAS 
CREATE TABLE inventory(
	grp_id			 	INT,
	shelved_stock		INT,
	back_stock			INT,
	cart_stock			INT,
	exp_date			TIMESTAMP,
	CONSTRAINT pk PRIMARY KEY (grp_id, exp_date),
	CONSTRAINT fk1 FOREIGN KEY (grp_id) REFERENCES product(grp_id),
	CONSTRAINT fk2 FOREIGN KEY (grp_id) REFERENCES price(grp_id)
);

CREATE TABLE product(
	grp_id			INT,
	brand			VARCHAR(200),
	name			VARCHAR(600),
	lot_price		FLOAT(5),
	lot_size		INT,
	category		INT,
	CONSTRAINT pk PRIMARY KEY (grp_id),
	CONSTRAINT fk1 FOREIGN KEY (grp_id) REFERENCES inventory(grp_id),
	CONSTRAINT fk2 FOREIGN KEY (grp_id) REFERENCES price(grp_id),
	CONSTRAINT fk3 FOREIGN KEY	(category) REFERENCES category(cat_id)
);

-- compare adding constraints vs just declaring fk / pk etc.
-- ALTER TABLE inventory ADD CONSTRAINT fk1_inventory type (col_name);

CREATE TABLE category(
	cat_id			INT,
	category		VARCHAR(50),
	coefficient		FLOAT(5),
	CONSTRAINT pk PRIMARY KEY (cat_id),
	CONSTRAINT fk1 FOREIGN KEY (cat_id) REFERENCES product(category)
);

CREATE TABLE price(
	grp_id			INT,
	price 			FLOAT(5),
	start_date		TIMESTAMP,
	end_date		TIMESTAMP,
	qty_max			INT,
	CONSTRAINT pk PRIMARY KEY (grp_id),
	CONSTRAINT fk1 FOREIGN KEY (grp_id) REFERENCES product(grp_id),
	CONSTRAINT fk2 FOREIGN KEY (grp_id) REFERENCES inventory(grp_id)
);

-- CREATE TABLE revenue(
-- 	rev_id			INT,
-- 	stamp			TIMESTAMP,
-- 	value			FLOAT(5),
-- 	CONSTRAINT pk PRIMARY KEY (rev_id) 
-- );

CREATE TABLE cost(
	cost_id			INT,
	stamp			TIMESTAMP,
	value 			FLOAT(5),
	ctype			VARCHAR(30),
	CONSTRAINT pk PRIMARY KEY (cost_id)
);

CREATE TABLE employee (
	emp_id			INT,
	role_id			INT,
	CONSTRAINT pk PRIMARY KEY (emp_id),
	CONSTRAINT fk FOREIGN KEY (role_id) REFERENCES role(role_id)
);

CREATE TABLE role(
	role_id			INT,
	role 			VARCHAR(100),
	hr_salary		FLOAT(5),
	max_hrs			INT,
	CONSTRAINT pk PRIMARY KEY (role_id),
	CONSTRAINT fk FOREIGN KEY (role_id) REFERENCES employee(role_id)
);

-- INSERT STARTER DATA INTO TABLES FROM EXCEL SHEETS
COPY inventory
FROM 'test-data/inventory.xlsx' DELIMITER ',' CSV HEADER;

COPY product
FROM 'test-data/product.xlsx' DELIMITER ',' CSV HEADER;

COPY category
FROM 'test-data/category.xlsx' DELIMITER ',' CSV HEADER;

COPY price
FROM 'test-data/price.xlsx' DELIMITER ',' CSV HEADER;

COPY employee
FROM 'test-data/employee.xlsx' DELIMITER ',' CSV HEADER;

COPY role
FROM 'test-data/role.xlsx' DELIMITER ',' CSV HEADER;

