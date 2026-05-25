#!/bin/bash

set -e

python3 -m imgtests makemigrations
python3 -m imgtests migrate

supervisord -n -c "/home/$USER/$LIB_NAME/conf/supervisord.conf"
