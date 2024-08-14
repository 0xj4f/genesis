#!/bin/bash
set -x 
pytest -v scripts/test_user_api.py
pytest -v scripts/test_auth_flow.py