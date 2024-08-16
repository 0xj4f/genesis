#!/bin/bash

banner(){
    echo;echo;
    echo "================================================"
    echo "[+] $1"
    echo "================================================"
}

banner "TESTING USER APIs"
pytest -v tests/test_user_api.py
banner "TESTING Authententication flow"
pytest -v tests/test_auth_flow.py