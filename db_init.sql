/********************************************************************** SET UP THE DATABASE */
CREATE DATABASE IF NOT EXISTS grocer;
USE grocer;

/* SET UP TABLE SCHEMAS */
CREATE TABLE IF NOT EXISTS item(
  item_name   		 VARCHAR(30),
  characteristic	 VARCHAR(60),
  brand          	 VARCHAR(30),
  quantity      	 INT,
  CONSTRAINT pk_name PRIMARY KEY (item_name, characteristic, brand)
);

/* INSERT STARTER DATA INTO TABLES */

-- milk
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('milk', 'half gallon', 'a', 20);
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('milk', 'half gallon', 'b', 20);
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('milk', 'half gallon', 'c', 20);
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('milk', 'half gallon', 'd', 20);

INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('milk', 'whole gallon' ,'a', 20);
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('milk', 'whole gallon', 'b', 20);
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('milk', 'whole gallon', 'c', 20);
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('milk', 'whole gallon', 'd', 20);

-- eggs
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('eggs', 'organic', 'a', 20);
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('eggs', 'organic', 'b', 20);
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('eggs', 'organic', 'c', 20);
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('eggs', 'organic', 'd', 20);

-- cheese
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('cheese', 'cheddar', 'a', 20);
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('cheese', 'cheddar', 'b', 20);
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('cheese', 'cheddar', 'c', 20);
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('cheese', 'cheddar', 'd', 20);

INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('cheese', 'swiss', 'a', 20);
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('cheese', 'swiss', 'b', 20);
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('cheese', 'swiss', 'c', 20);
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('cheese', 'swiss', 'd', 20);

INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('cheese', 'provolone', 'a', 20);
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('cheese', 'provolone', 'b', 20);
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('cheese', 'provolone', 'c', 20);
INSERT INTO item(item_name, characteristic, brand, quantity) VALUES ('cheese', 'provolone', 'd', 20);

