# USERS DOMAIN 

quick run
```bash
uvicorn app.main:app --reload
# fastapi dev main.py  # before when the project was flat
```
## SETUP

```bash
python3 -m venv .venv 
. .venv/bin/activate
pip install "fastapi[all]" # main dependency 
pip install sqlalchemy "databases[mysql]" pymysql alembic # database
pip install bcrypt python-jose pyjwt # authentication

```

### Database

you need to create the database schema before running your FastAPI application if it doesn't exist yet. SQLAlchemy won't create the database itself; it will only create the tables within an existing database


create dev user
```bash
CREATE USER 'dev-project'@'%' IDENTIFIED BY 'SECURE_PASSWORD';
GRANT ALL PRIVILEGES ON *.* TO 'dev-project'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;

mysql -u "$MYSQL_DEV_USER" -p"$MYSQL_DEV_PASSWORD" < scripts/init.sql
```

## REPO STRUCTURE

```bash 
app
├── auth
│   └── auth.py
├── database
│   ├── session.py
│   └── user_db_interface.py
├── main.py
├── models
│   ├── user_api_model.py
│   └── user_db_model.py
├── routes
│   ├── auth.py
│   ├── profiles.py
│   └── users.py
├── services
│   ├── auth_service.py
│   ├── profile_service.py
│   └── user_service.py
└── utils
    ├── helpers.py
    └── security.py
```


## TEST DRIVEN DEVELOPMENT

```bash
pytest -v scripts/test_user_api.py
pytest -v scripts/test_auth_flow.py
```

## REFERENCES

Authentication 
- https://github.com/fastapi/fastapi/issues/3303
- https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#check-it
- https://indominusbyte.github.io/fastapi-jwt-auth/usage/refresh/