#!/bin/bash

banner(){
    echo;echo;
    echo "================================================"
    echo "[+] $1"
    echo "================================================"
}

banner "TESTING USER APIs"
pytest -v -p no:warnings tests/test_user_api.py
banner "TESTING Authententication flow"
pytest -v -p no:warnings tests/test_auth_flow.py
banner "TESTING Authententication flow 2"
pytest -v -p no:warnings tests/test_auth_flow-2.py