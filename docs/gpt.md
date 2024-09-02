
## Pedantic Model 
The pattern you’re seeing in FastAPI documentation with Pydantic models is a common practice to separate concerns and maintain clarity in API design. Let me explain the structure and the specific concept of `orm_mode`.

### Structure of Pydantic Models in FastAPI

1. **`UserBase`**:
   - This is a base model that contains shared fields across different variants of the `User` model.
   - Example:
     ```python
     class UserBase(BaseModel):
         email: str
     ```
   - **Purpose**: To define common attributes shared across various forms of the `User` model, reducing redundancy.

2. **`UserCreate`**:
   - Inherits from `UserBase`, adding fields necessary for user creation, like `password`.
   - Example:
     ```python
     class UserCreate(UserBase):
         password: str
     ```
   - **Purpose**: To be used when a new user is created, so it includes fields like `password` that aren’t necessarily returned when reading a user’s information.

3. **`User`**:
   - Also inherits from `UserBase` but represents the full data structure returned from the API, including fields like `id`, `is_active`, and related `items`.
   - Example:
     ```python
     class User(UserBase):
         id: int
         is_active: bool
         items: list[Item] = []

         class Config:
             orm_mode = True
     ```
   - **Purpose**: To represent the full user data returned in API responses, including fields that are stored in the database.

### What is `orm_mode`?

- **`orm_mode`** is a configuration setting in Pydantic models that allows models to work seamlessly with ORMs (Object-Relational Mappers) like SQLAlchemy.
- **Purpose**:
  - When `orm_mode` is enabled, Pydantic models can read data from ORM objects (e.g., SQLAlchemy models) and convert them into the Pydantic model structure.
  - This means you can directly pass SQLAlchemy model instances to Pydantic model constructors and have Pydantic automatically extract and validate the data.

### How `orm_mode` Works:

- Without `orm_mode` enabled, Pydantic models expect dictionaries, not ORM instances.
- With `orm_mode` enabled, Pydantic can read attributes from an ORM model instance as if it were a dictionary.

### Example Usage:

Let’s say you have a SQLAlchemy `User` model instance:

```python
db_user = UserModel(id=1, email="user@example.com", is_active=True)
```

You can then create a Pydantic `User` model from this SQLAlchemy instance like this:

```python
pydantic_user = User.from_orm(db_user)
```

Here, `from_orm` uses `orm_mode` to automatically map fields from the SQLAlchemy model to the Pydantic model.

### Why Use `orm_mode`?

- **Integration with ORMs**: It simplifies the conversion between database models and Pydantic models, which is particularly useful in FastAPI for returning database models as API responses.
- **Readability and Maintainability**: Keeps the API’s data representation consistent with the database schema, making it easier to manage and understand.

### Summary

- **`orm_mode = True`** allows Pydantic models to interact smoothly with ORM models, making it possible to convert ORM instances directly into Pydantic model instances.
- **Model Structure**: Using a base model like `UserBase` allows shared attributes to be reused, while `UserCreate` is specialized for input (like creating a user) and `User` for output (like returning user data in a response).

This structure is both efficient and clear, aligning well with the separation of concerns in API design.



## ASYNC and GIL 
> in my case that I'm creating users crud to the database is it good to add async in my api routes?  will it not block or be a problem for other request, some say there is a problem in GIL 


Yes, adding `async` to your API routes, especially for a CRUD application interacting with a database, is generally a good practice. It can improve the performance of your application by allowing other requests to be handled while waiting for I/O operations, such as database queries, to complete.

### **Why Use `async` for CRUD Operations?**

1. **Non-blocking I/O**: 
   - Database operations are typically I/O-bound, meaning they spend time waiting for data to be read or written. Using `async` in your CRUD operations allows the server to handle other incoming requests during this waiting period, making your application more responsive and scalable.

2. **Concurrency**: 
   - When your application is handling multiple requests simultaneously, using `async` ensures that one long-running request (e.g., a complex database query) doesn't block others. This improves throughput and reduces latency under load.

### **Concerns with the Global Interpreter Lock (GIL)**

The Global Interpreter Lock (GIL) is a mutex that protects access to Python objects, preventing multiple native threads from executing Python bytecodes at once. This can be a concern for CPU-bound tasks that require intensive computation, as it can limit the performance of multi-threaded applications.

**For I/O-bound tasks (like database operations), the GIL is less of a concern**:

- **Async I/O**: When you're performing I/O-bound tasks asynchronously, the GIL isn't as restrictive because the operations are waiting for external events (like data from a database) rather than using CPU time. This allows other tasks to be executed in the meantime.

- **Database Libraries**: Many modern database libraries, such as `asyncpg` for PostgreSQL, are designed to work well with asynchronous frameworks like FastAPI, bypassing many of the issues related to the GIL by offloading tasks to asynchronous I/O operations.

### **When `async` Might Not Be Necessary**

- **CPU-bound tasks**: If your CRUD operations involve heavy computation or processing within Python itself (e.g., complex data transformations), `async` might not be beneficial because the GIL can become a bottleneck. For CPU-bound tasks, you might consider other techniques, such as multiprocessing or offloading the work to background workers.

- **Simplicity**: If your application is simple and doesn't need to handle a high volume of concurrent requests, using `async` might add unnecessary complexity.

### **Best Practice**

For typical CRUD operations involving database interactions, adding `async` to your API routes is usually beneficial and aligns with FastAPI's design:

- **Use `async` for database interactions** to take advantage of non-blocking I/O.
- **Ensure your database library** supports asynchronous operations (e.g., `asyncpg` for PostgreSQL, `aiomysql` for MySQL).
- **Monitor performance**: If you notice performance issues, it might be related to how the async operations are managed or the specific use case (e.g., too many concurrent connections to the database). 

In summary, for a CRUD application that interacts with a database, using `async def` in your API routes is generally a good approach and will likely improve your application's performance and scalability. The GIL is not a significant issue for these I/O-bound tasks.


> I need to have some raw test without async and  
> use async database interactions: 

## ASYNC OPERATIONS

To determine if your FastAPI code and the database interaction are using non-blocking I/O, we need to review a few key aspects:

1. **FastAPI and Async Support**: FastAPI supports asynchronous programming and non-blocking I/O, but this only applies if the endpoints and the database interactions are implemented in an asynchronous manner.

2. **SQLAlchemy with MySQL**: SQLAlchemy is traditionally blocking and does not natively support asynchronous interactions with the database. However, there is support for asynchronous programming when combined with `asyncpg` (for PostgreSQL) or when using `SQLAlchemy 1.4` with `async` capabilities. Since you're using MySQL, you could leverage `asyncmy` or `aiomysql` with `SQLAlchemy` for asynchronous interactions.

3. **Current Code Review**: The provided code uses SQLAlchemy in a traditional, synchronous way (`create_engine`, `sessionmaker`, and typical ORM queries). This means that your database calls are blocking, and if you want non-blocking behavior, you would need to refactor the code to use asynchronous session handling and async-compatible MySQL drivers.

### Current Implementation and Blocking I/O

- **Database Session**: You're using `create_engine` and `sessionmaker` from SQLAlchemy for database interactions, which are synchronous. This means that when your code executes a database query, it will block the execution thread until the query completes. This behavior can cause performance bottlenecks, especially under heavy load or when database queries are slow.

- **Asynchronous Programming in FastAPI**: FastAPI supports async functions, and they are recommended for I/O-bound operations, such as database interactions. Since your current implementation does not use async/await for database operations, these operations are blocking.

### Moving to Non-Blocking I/O with FastAPI and SQLAlchemy

To convert your codebase to use non-blocking I/O with asynchronous database interactions, you would need to:

1. **Use an Async-compatible Database Driver**: For MySQL, you can use `aiomysql` or `asyncmy`.

2. **Configure SQLAlchemy for Async Usage**: Use SQLAlchemy's async session capabilities introduced in version 1.4.

3. **Refactor the Code**: Change the database interaction code to use async sessions and async functions. This would mean refactoring the `get_db` function, the service functions, and the route handlers to use `async def` and `await`.

### Example of Asynchronous Setup with FastAPI and SQLAlchemy for MySQL

Here’s how you might refactor your current setup to be asynchronous:

#### 1. Update Dependencies

Make sure you have the necessary async libraries installed:

```bash
pip install asyncmy sqlalchemy[asyncio] fastapi uvicorn
```

#### 2. Asynchronous Database Session

Refactor your `database/session.py` to use async sessions:

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
import os

DATABASE_USER = os.getenv("MYSQL_DEV_USER", "root")
DATABASE_PASSWORD = os.getenv("MYSQL_DEV_PASSWORD", "")
DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = os.getenv("DATABASE_PORT", "3306")
DATABASE_NAME = os.getenv("DATABASE_NAME", "genesis")
encoded_password = quote_plus(DATABASE_PASSWORD)  # if password has special characters

# Use asyncmy for MySQL async support
SQLALCHEMY_DATABASE_URL = f"mysql+asyncmy://{DATABASE_USER}:{encoded_password}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        yield session
```

#### 3. Asynchronous CRUD Operations

Refactor your `database/user_db_interface.py` to use async methods:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user_db_model import User
from app.models.user_api_model import UserCreate, UserUpdate
from sqlalchemy import update, delete

async def create_user_db(db: AsyncSession, user_create: UserCreate) -> User:
    db_user = User(**user_create.dict())
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def get_all_users_db(db: AsyncSession):
    result = await db.execute(select(User))
    return result.scalars().all()

async def get_user_by_id_db(db: AsyncSession, user_id: str):
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalar()

# Similar refactoring for update and delete functions
```

#### 4. Asynchronous Route Handlers

Make sure your route handlers call these async functions and use `async def` and `await` appropriately:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.services.user_service import create_user_service, get_all_users_service

router = APIRouter()

@router.post("/", response_model=User)
async def create_user(user_create: UserCreate, db: AsyncSession = Depends(get_db)):
    return await create_user_service(db, user_create)

@router.get("/", response_model=List[User])
async def read_users(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    users = await get_all_users_service(db)
    return users[skip: skip + limit]
```

### Conclusion

- The original implementation uses synchronous database calls, which are blocking. For non-blocking I/O, you need to use asynchronous drivers and sessions.
- With the above changes, you can leverage FastAPI’s full potential for handling asynchronous operations, which will improve scalability and responsiveness, especially under high loads.
- Ensure that the entire stack, including routes, services, and database interactions, are consistently using asynchronous code to avoid blocking. 

This conversion allows you to handle more concurrent requests efficiently, making your FastAPI application truly async and non-blocking.