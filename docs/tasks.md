# SCRUM Breakdown


BackEnd API Foundations
- creating API endpoint
- business logic
- sanitizing input data 
- validating input data
- database connection
- unit test 


FrontEnd Foundations
- setup API connection
- create code component (example reusable card )
- style (css)
- responsiveness (mobile, laptop, big desktop)


Definition of Done:
- deployed to development environment
- tested by dev
- tested by QA


Backend API optimizations
- rate limiting
- async logging 


---
## SPRINT 0 : Setup 
- setup LOCAL Environment: 1 hr
    - setup fastapi and dependencies: 30 mins
    - setup mysql: 30 
        - database administration
        - database init sql 
- data structure design: 1hr 
- systems design: 1hr

## SPRINT 1 : User, Profiles and Authentication

### BackEnd

USER FEATURE: 8 hr
- create user feature: 2 hr 
    - api endpoint
    - api model
    - database interface
    - database model 

- get users feature: 2 hr
    - get all
    - get by id
    - get by email 

- update user feature: 1 hr
    - api endpoint
    - api model
    - database interface

- delete user feature: 1hr
    - api endpoint
    - api model
    - database interface

- created unit test for all apis: 1hr


- Business Logic: 1 hr
    creating users:
    - validate email before creating user
    - validate username before creating user
    updating user:
    - validate if email is already used
    - validate if username is already used

- Security
  paswword strength:
    - 1 lower char
    - 1 upper char
    - 1 symbol
    - 1 number

- test_user_apis: 1 hr 
  - create 5 user 
  - get all user 
  - search user by id 
  - delete user
    - check if user is really deleted 

AUTHENTICATION : 4 hrs 
- create login endpoint 
  - update storing of password to be hashed
  - check hashed password 

- setup oauth dependencies 
- password verifier
- create jwt tokens
- jwt tokens verifier
- /token api endpoint 
- authenticated by JWT endpoint 

- test validity of authentication 
    - token expiry
    - encryption
    - oauth library 

- create refresh tokens endpoint: 1 hr
  - token validator
  -  


- test_auth_flow: 1 hr 
    - create test user
    - use user creds to login
    - login and get access_token
    - use access_token to visit authenticated endpoint

- test_auth_flow-2: 1 hr 
    - create test user
    - use user creds to login
    - login and get access_token
    - use access_token to visit authenticated endpoint
    - refresh token
    - use fresh access_token to visit authenticated endpoint


PROFILE FEATURE 
- create profile feature: 4hrs
- get own profile feature: 2hrs
- get profile by id: 2hrs
- update profile by id: 2hrs
- delete profile by id: 2hrs
- get profile by UUID: 2hrs

Logic:
- profile is associated with user's






## GPT 

Creating a feature
- create api endpoint
- create dabase interface 
- create pydantic request and response model if needed


---

CREATE PROFILE FEATURE 

Feature 
- user_id: UUID 
- given_name: str 
- family_name: str 
- nick_name: str 
- picture: str 
- updated_at: date str 
- email: email str 
- sub: str 

please create:
- api model using pydantic for api_models.py
- database model for database_models.py

I want this data structure to be ready when I integrate oauth openID connect.
what do you think are the fields that are need. 
and analyze what are things to be optional and what should be required


---

Now I want to update the code base to my use case
- create user
- get token
- create profile
  - needs authentication
  - validate  if profile is already existing
  - use current user uuid
- get own profile
  - needs auth
  - use current user uuid for profile
  - return profile
- update own profile
  - needs auth
  - use current user uuid for profile
  - update profile
  - return profile
- delete profile
  - needs auth
  - use current user uuid for profile
  - delete profile
  
I want you to focus on producing the code base for these features.
as next we're going to create the test script.

## Sep3 , 2024

11 AM - 1pm  IAM, RBAC and research and decision making if it's in the best direction.

Implementing IAM and RBAC access requires being very accurate on the planning which access you will have to give.
which means you need to know first the exact features.

right now it will be a slow down if I started thinking about the RBAC and IAM management. 

lets simplify, roles
- admin
- seller/artist
- user

most endpoints will be protected, by admin role

every registration should be a default user,
so the validation should happen in group role,
group role will be added manually, for now



Ok let's start in the ecommerce, to make it this simple

- admin
- seller
- user

let's create the admin dashboard, finish it.
then come back later to analyze all the endpoints created. 

- Users created.
- Products Created.


Product Item

Create PRODUCTS CRUD




