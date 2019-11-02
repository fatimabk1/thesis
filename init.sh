#!/bin/bash

# start db server
pg_ctl -D /usr/local/var/postgres/ -l logfile start	 

# create db
psql
\i 'db_init.sql'
\q
