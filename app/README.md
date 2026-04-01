# Backend API Overview

---

## Endpoints

All API endpoints are registered on the `api_bp` blueprint in `routes.py`, plus two health endpoints in `__init__.py`.

- **Auth**
  - **POST `/auth/register`**
    - Registers a new user with `email`, `password`.
  - **POST `/auth/login`**
    - Authenticates user and returns a JWT access token.
- **Transactions**
  - **POST `/transactions`** (JWT required)
    - Creates a transaction (implicitly ensures category exists, and updates account balance).
  - **GET `/transactions`** (JWT required)
    - Lists current user’s transactions; supports `account_id`, `category_id` query params.
  - **GET `/transactions/<int:transaction_id>`** (JWT required)
    - Fetches a specific transaction belonging to the current user.
  - **PUT `/transactions/<int:transaction_id>`** (JWT required)
    - Updates transaction fields and re-adjusts account balances.
  - **DELETE `/transactions/<int:transaction_id>`** (JWT required)
    - Deletes a transaction and rolls back its effect on the account balance.
- **Accounts**
  - **POST `/accounts`** (JWT required)
    - Creates an account or returns an existing one if same name+type already exists for the user.
  - **GET `/accounts`** (JWT required)
    - Lists all accounts for the current user.
  - **GET `/accounts/<int:account_id>`** (JWT required)
    - Returns details for one account belonging to the user.
  - **PUT `/accounts/<int:account_id>`** (JWT required)
    - Updates name, type, and optionally balance; enforces uniqueness of (name, type) per user.
  - **DELETE `/accounts/<int:account_id>`** (JWT required)
    - Deletes the account.
- **Categories**
  - **POST `/categories`** (JWT required)
    - Creates a category for the user, enforcing rules on name/type combinations.
  - **GET `/categories`** (JWT required)
    - Lists categories; supports optional `type` filter (`income` / `expense`).
  - **GET `/categories/<int:category_id>`** (JWT required)
    - Returns one category for the user.
  - **PUT `/categories/<int:category_id>`** (JWT required)
    - Updates category name/type with conflict checks.
  - **DELETE `/categories/<int:category_id>`** (JWT required)
    - Deletes a category.

---

## Data Model & Relations + Core Logic

From `models.py`:

- **User**
  - Table: `users`
  - Fields: `id`, `email` (unique), `password_hash`, `created_at`
  - Relations:
    - `accounts`: `User` → many `Account` (`db.relationship("Account", backref="user", cascade="all, delete")`)
- **Account**
  - Table: `accounts`
  - Fields: `id`, `user_id (FK users.id)`, `name`, `type`, `balance`, `created_at`
  - Relations:
    - `user`: each account belongs to a user.
    - `transactions`: `Account` → many `Transaction` (`cascade="all, delete"`)
- **Category**
  - Table: `categories`
  - Fields: `id`, `user_id (FK users.id)`, `name`, `type` (`income`/`expense`), `created_at`
  - Constraints:
    - `UniqueConstraint("user_id", "name", name="uq_user_category")` – a user cannot have two categories with the same name, regardless of type (although logic adds extra constraints, see below).
- **Transaction**
  - Table: `transactions`
  - Fields: `id`, `account_id (FK accounts.id)`, `category_id (FK categories.id, ondelete="SET NULL")`, `amount`, `description`, `transaction_date`, `created_at`

**Key relationships and logic across routes:**

- **User ↔ Account**:
  - All account queries are filtered by `user_id` (via `get_current_user()` + `get_user_account_or_404`).
  - On user deletion (DB cascade), their accounts and transactions are deleted.
- **User ↔ Category**:
  - Categories are always tied to a `user_id`.
  - Category conflict rules:
    - In `create_category` and `update_category`, logic checks whether a category with same name but opposite type exists and rejects that.
    - `create_or_retrieve_category_for_user` (used during transaction creation) enforces:
      - same name + same type → reuse existing category
      - same name + opposite type → reject
      - missing name → use or create `"uncategorized income"` or `"uncategorized expense"`.
- **Account ↔ Transaction ↔ Category**:
  - Each transaction references an account and a category (`category_type` and `account_id`are required).
  - Helper `transaction_to_dict` plus `get_transaction_category_type` (which may fetch category from DB) is used to attach category type for balance calculations.
  - **Balance logic**:
    - Transactions are always stored as non-negative values. But, the balance logic interprets them, as +/- depending on category type, to keep account balances up-to-date after their corresponding transaction calls.
    - `get_signed_amount(amount, category_type)`: Assigns a sign (+/-) to values based on the category type.
      - income → positive
      - expense → negative
    - On create/delete:
      - `update_balance_for_create_delete(transaction_dict, user_id, transaction_type)` adjusts `account.balance`:
        - create: `new_balance = current + signed_amount`
        - delete: `new_balance = current - signed_amount`
    - On update:
      - `update_balance_for_update(old_transaction_dict, new_transaction_dict, user_id)`:
        - If same account: subtract old signed amount, add new signed amount.
        - If account changed: subtract from old account, add to new.

---

## Input Validation

Validation is centralized via helper functions at the top of `routes.py`, and then applied in each route.

**Helper validators (all in `routes.py`):**

- `clean_string(value, field_name, required=True, max_length=None)`
  - Ensures required presence, type is `str`, trimmed, non-empty when required.
  - Optionally enforces maximum length.
  - Used for: `email`, `password`, account name & type, category name & type, transaction description, etc.
- `clean_email(email)`
  - Calls `clean_string` with `max_length=255` and `required=True`.
  - Basic structural check (`"@" in email and "." in email`).
  - Used in `/auth/register`, `/auth/login`.
- `clean_password(password)`
  - Uses `clean_string`.
  - Checks `len(password) >= 8`.
  - Used in auth routes.
- `clean_decimal(value, field_name)`
  - Converts to `Decimal` using `Decimal(str(value))`.
  - On failure (`InvalidOperation`, `ValueError`, `TypeError`), raises `ValueError("<field> must be a valid number.")`.
  - Used for transaction `amount`, account `balance`, recalculated balances.
- `clean_int(value, field_name, required=True)`
  - Casts to `int`; on failure raises `ValueError`.
  - Used for IDs coming from JSON or query params: `account_id`, `category_id`, `transaction_id` where applicable.
- `clean_transaction_date(value)`
  - If `None`, defaults to `date.today()`.
  - Requires a `YYYY-MM-DD` string; raises `ValueError` on format error.
  - Used for adding and updating transactions
- `get_category_type_or_400(category_type)`
  - Ensures non-empty string; normalizes to lowercase.
  - Ensures type is `"income"` or `"expense"`, else raises `ValueError`.
  - Used for adding and updating transactions and categories

---

## Error Handling

Error handling is consistently done via `try/except` blocks in the routes, returning JSON responses.

**Patterns:**

- **Validation errors (`ValueError`)**
  - Almost all routes wrap their core logic in `try` and catch `ValueError as e`:
    - Rollback DB session (for write operations).
    - Return `400` with `{"error": str(e)}`.
- **Database integrity errors (`IntegrityError`)**
  - `create_transaction`, `create_account`, `create_category`, `update_account`, `update_category` catch `IntegrityError`:
    - For create account/category, they may re-query to see if entity already exists and return either `200` with existing entity or `409` conflict (`"Duplicate ... data violates uniqueness rules."`).
    - For update account/category, return `409` conflict if uniqueness is violated.
- **Authentication / authorization**
  - `get_current_user()` uses `get_jwt_identity` and fetches `User` by ID; if parse fails or user not found, routes typically respond with:
    - `{"error": "User not found."}`, `404`.
  - 401-specific responses used on login failure:
    - `{"error": "Invalid email or password."}`, `401`.
- **Resource not found**
  - Helpers:
    - `get_user_account_or_404`, `get_user_category_or_404`, `get_user_transaction_or_404` return `None` if not found.
  - Routes check return value and respond with `404` and appropriate message:
    - `"Account not found."`, `"Category not found."`, `"Transaction not found."` or `"Account not found or does not belong to the user."`.
- **Generic exceptions**
  - For each mutating route:
    - Catch `Exception` as a final fallback, `db.session.rollback()`, and return `400` or `500` with a generic error, e.g.:
      - `"Failed to register user."`, `"Failed to create account."`, `"Failed to create the transaction and update the balance:\n{e}"`,
      - `"Failed to update category."`, `"Failed to delete account."`, etc.
  - In login route, generic password verification failure returns `500`.

**HTTP status code usage:**

- `200 OK` – successful reads/updates, idempotent creates that return “already existed”.
- `201 Created` – successful new user, account, category, transaction creation.
- `400 Bad Request` – validation errors or generic failures when request is invalid.
- `401 Unauthorized` – incorrect login credentials.
- `404 Not Found` – missing user (after JWT), account, category, transaction.
- `409 Conflict` – uniqueness/constraint violations.

---

## Health Endpoints

The health endpoints are located in `app/__init__.py`:

- **GET `/health`** verifies that the application is running.
- **GET `/health/db`** verifies that the application can reach the database.

---

## Logging

Logging of outcomes is mainly handled through HTTP responses. Additional logs regarding the intermediary steps of processes are maintained using `logging.getLogger()`, which is configured in `routes.py`.

---