# USERS DOMAIN 

## SETUP

```bash
python3 -m venv .venv 
. .venv/bin/activate
pip install "fastapi[all]" bcrypt
pip install sqlalchemy "databases[mysql]" pymysql alembic

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


## TEST DRIVEN DEVELOPMENT

```bash
pytest scripts/test_user_api.py
```

## GPT

Act as Greatest Python and Fast API developer who's good at backend development and with a devsecops mindset.
I want to tailor fit the experience that I'm having. 
- I use an ubuntu 24.04 on a macbook pro. 
- python3.12 version
- mysql 8

project_name: genesis

we are going to create a fastapi web application for creating IAM management.
- users with profile
- will have a choice for oauth
- and this microservice can be extended to any web application

but let's build it slowly and accurate

I want to start at creating USERS 
- pedantic base model
- database model 
- database interface (CRUD OPERATIONS)
    - create_user 
    - read_users
    - read_users_by_id
    - update_users_by_id
    - delete_users_by_id
- API endpoints
    - create_user 
    - read_users
    - read_users_by_id
    - update_users_by_id
    - delete_users_by_id

API endpoints will consume the database interface 


file structure and naming convention
- main.py : will hold the api routes
- database_interface.py : will hold database CRUD OPERATIONS
- database_models.py : will use sqlalchemy and hold database models of users
- database_config.py :  will hold the database configuration and connection
- api_models.py: will host the pedendatic models

This is user will have this fields

USER model
- username: str 
- email: email str
- password: secret str
optional:
- created_at
- last_modified

the user should have UUID as the ID 

I don't know where should I put that logic. so the database model will have user_id

I want to heavily use the pedantic for performance. 
so let's start first at the schemas

## VSCODE
- github dark
- https://vscodethemes.com/e/fms-cat.theme-monokaisharp/monokai-sharp?language=python
- https://vscodethemes.com/e/catppuccin.catppuccin-vsc/catppuccin-frappe?language=python
