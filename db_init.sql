-- SET UP THE DATABASE
CREATE DATABASE store;
\c store;

-- SET UP TABLE SCHEMAS
CREATE TABLE inventory(
	grp_id			 	SERIAL,
	shelved_stock		INT,
	back_stock			INT,
	cart_stock			INT,
	exp_date			TIMESTAMP,
	CONSTRAINT pk_inv PRIMARY KEY (grp_id, exp_date)
);

CREATE TABLE product(
	grp_id			SERIAL,
	brand			VARCHAR(200),
	name			VARCHAR(600),
	lot_price		FLOAT(5),
	lot_size		INT,
	category		INT,
	CONSTRAINT pk_prod PRIMARY KEY (grp_id)
);

CREATE TABLE category(
	cat_id			SERIAL,
	category		VARCHAR(50),
	coefficient		FLOAT(5),
	CONSTRAINT pk_cat PRIMARY KEY (cat_id)
);

CREATE TABLE price(
	grp_id			SERIAL,
	price 			FLOAT(5),
	start_date		TIMESTAMP,
	end_date		TIMESTAMP,
	qty_max			INT,
	CONSTRAINT pk_price PRIMARY KEY (grp_id)
);

CREATE TABLE revenue(
	rev_id			SERIAL,
	stamp			TIMESTAMP,
	value			FLOAT(5),
	CONSTRAINT pk_revenue PRIMARY KEY (rev_id)
);

CREATE TABLE cost(
	cost_id			SERIAL,
	stamp			TIMESTAMP,
	value 			FLOAT(5),
	ctype			VARCHAR(30),
	CONSTRAINT pk_cost PRIMARY KEY (cost_id)
);

CREATE TABLE employee (
	emp_id			SERIAL,
	role_id			INT,
	CONSTRAINT pk_emp PRIMARY KEY (emp_id)
);

CREATE TABLE role(
	role_id			SERIAL,
	role 			VARCHAR(100),
	hr_salary		FLOAT(5),
	max_hrs			INT,
	CONSTRAINT pk_role PRIMARY KEY (role_id)
);

CREATE TABLE queuetime(
	qt_id			SERIAL,
	queue_num		INTEGER,
	stamp			TIMESTAMP,
	q_time			INTEGER,
	total_qs		Integer,
	CONSTRAINT	pk_qtime PRIMARY KEY (qt_id)
);


-- INSERT STARTER DATA INTO TABLES FROM EXCEL SHEETS
\copy inventory FROM 'test-data/inventory.csv' 	WITH DELIMITER ',' CSV HEADER;
\copy product 	FROM 'test-data/product.csv' 	WITH DELIMITER ',' CSV HEADER;
\copy category 	FROM 'test-data/category.csv' 	WITH DELIMITER ',' CSV HEADER;
\copy price 	FROM 'test-data/price.csv' 		WITH DELIMITER ',' CSV HEADER;
\copy employee 	FROM 'test-data/employee.csv' 	WITH DELIMITER ',' CSV HEADER;
\copy role 		FROM 'test-data/role.csv' 		WITH DELIMITER ',' CSV HEADER;


-- Add foreign keys
ALTER TABLE inventory ADD CONSTRAINT fk1_inv FOREIGN KEY (grp_id) REFERENCES product(grp_id);
ALTER TABLE inventory ADD CONSTRAINT fk2_inv FOREIGN KEY (grp_id) REFERENCES price(grp_id);
ALTER TABLE product ADD CONSTRAINT fk2_prod FOREIGN KEY (grp_id) REFERENCES price(grp_id);
ALTER TABLE product ADD CONSTRAINT fk3_prod FOREIGN KEY	(category) REFERENCES category(cat_id);
ALTER TABLE price ADD CONSTRAINT fk1_price FOREIGN KEY (grp_id) REFERENCES product(grp_id);
ALTER TABLE employee ADD CONSTRAINT fk_emp FOREIGN KEY (role_id) REFERENCES role(role_id);

UPDATE inventory SET shelved_stock=200, back_stock=800;

