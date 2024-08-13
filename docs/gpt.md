
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
