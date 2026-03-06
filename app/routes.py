"""API routes for authentication and transaction CRUD operations."""
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app import db
from app.models import Transaction, User, Category, Account
from datetime import UTC, datetime, date
from decimal import Decimal, InvalidOperation
from functools import wraps
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required


api_bp = Blueprint("main", __name__)
password_hasher = PasswordHasher()

@api_bp.route("/")
def home():
    return "Finance Tracker API is running!"

# --------Helper Functions---------
def clean_string(value, field_name, required=True, max_length=None):
    """
    Validate and clean a string input.
    - Strips whitespace
    - Checks required fields
    - Checks max length if provided
    """
    if value is None:
        if required:
            raise ValueError(f"{field_name} is required.")
        return None

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")

    value = value.strip()

    if required and not value:
        raise ValueError(f"{field_name} cannot be empty.")

    if max_length and len(value) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters.")

    return value


def clean_email(email):
    email = clean_string(email, "email", required=True, max_length=255).lower()

    if "@" not in email or "." not in email:
        raise ValueError("email must be a valid email address.")

    return email


def clean_password(password):
    password = clean_string(password, "password", required=True)

    if len(password) < 8:
        raise ValueError("password must be at least 8 characters long.")

    return password


def clean_decimal(value, field_name):
    """
    Convert incoming amount into Decimal and validate it.
    Accepts strings, ints, floats, etc.
    """
    if value is None:
        raise ValueError(f"{field_name} is required.")

    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field_name} must be a valid number.")

    return decimal_value


def clean_int(value, field_name, required=True):
    """
    Convert a value into an integer if possible.
    """
    if value is None:
        if required:
            raise ValueError(f"{field_name} is required.")
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer.")


def clean_transaction_date(value):
    """
    Validate transaction_date in YYYY-MM-DD format and convert it to a date object.
    """
    if value is None:
        return date.today()

    if not isinstance(value, str):
        raise ValueError("transaction_date must be a string in YYYY-MM-DD format.")

    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("transaction_date must be in YYYY-MM-DD format.")


def transaction_to_dict(transaction):
    """
    Convert a Transaction model instance into JSON-friendly output.
    """
    return {
        "id": transaction.id,
        "account_id": transaction.account_id,
        "category_id": transaction.category_id,
        "amount": str(transaction.amount),
        "description": transaction.description,
        "transaction_date": transaction.transaction_date.isoformat(),
        "created_at": transaction.created_at.isoformat(),
    }


def get_current_user():
    """
    Read the current user ID from the JWT and fetch the matching user record.
    """
    user_id = get_jwt_identity()

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None

    return User.query.get(user_id)


def get_user_account_or_404(account_id, user_id):
    """
    Ensure the requested account belongs to the logged-in user.
    """
    return Account.query.filter_by(id=account_id, user_id=user_id).first()


def get_user_category_or_404(category_id, user_id):
    """
    Ensure the requested category belongs to the logged-in user.
    """
    return Category.query.filter_by(id=category_id, user_id=user_id).first()


def get_user_transaction_or_404(transaction_id, user_id):
    """
    Ensure the requested transaction belongs to one of the user's accounts.
    This prevents users from accessing another user's transactions.
    """
    return (
        Transaction.query
        .join(Account, Transaction.account_id == Account.id)
        .filter(Transaction.id == transaction_id, Account.user_id == user_id)
        .first()
    )

# --------Authentication Routes-----------
@api_bp.post("/auth/register")
def register_user():
    """
    Register a new user.
    Expects JSON:
    {
        "email": "user@example.com",
        "password": "example_password"
    }
    """
    data = request.get_json() or {}

    try:
        email = clean_email(data.get("email"))
        password = clean_password(data.get("password"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "A user with that email already exists."}), 409

    # Hash password securely with Argon2 before storing it
    password_hash = password_hasher.hash(password)

    user = User(email=email, password_hash=password_hash)

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "User registered successfully.",
        "user": {
            "id": user.id,
            "email": user.email,
            "created_at": user.created_at.isoformat()
        }
    }), 201

@api_bp.post("/auth/login")
def login_user():
    """
    Log a user in.
    Expects JSON:
    {
        "email": "user@example.com",
        "password": "example_password"
    }

    Returns a JWT access token on success.
    """
    data = request.get_json() or {}
    try:
        email = clean_email(data.get("email"))
        password = clean_password(data.get("password"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Invalid email or password."}), 401

    try:
        password_hasher.verify(user.password_hash, password)
    except VerifyMismatchError:
        return jsonify({"error": "Invalid email or password."}), 401
    except Exception:
        return jsonify({"error": "Password verification failed."}), 500

    # Put the user ID inside the signed JWT token
    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        "message": "Login successful.",
        "access_token": access_token,
        "user": {
            "id": user.id,
            "email": user.email
        }
    }), 200

#----------Transaction CRUD Routes-----------
@api_bp.post("/transactions")
@jwt_required()
def create_transaction():
    """
    Create a new transaction for the logged-in user.

    Expects JSON:
    {
        "account_id": 1,
        "category_id": 2,  # optional
        "amount": 25.50,
        "description": "Lunch",
        "transaction_date": "2025-09-20" # optional
    }
    """
    data = request.get_json() or {}
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    try:
        account_id = clean_int(data.get("account_id"), "account_id")
        category_id = clean_int(data.get("category_id"), "category_id", required=False)
        amount = clean_decimal(data.get("amount"), "amount")
        description = clean_string(data.get("description"), "description", required=False)
        transaction_date = clean_transaction_date(data.get("transaction_date"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    # Make sure the account belongs to the logged-in user
    account = get_user_account_or_404(account_id, user.id)
    if not account:
        return jsonify({"error": "Account not found or does not belong to the user."}), 404

    # If category_id is provided, make sure it belongs to the user too
    if category_id is not None:
        category = get_user_category_or_404(category_id, user.id)
        if not category:
            return jsonify({"error": "Category not found or does not belong to the user."}), 404
    else:
        category = None

    transaction = Transaction(
        account_id=account.id,
        category_id=category.id if category else None,
        amount=amount,
        description=description,
        transaction_date=transaction_date
    )

    db.session.add(transaction)
    db.session.commit()

    return jsonify({
        "message": "Transaction created successfully.",
        "transaction": transaction_to_dict(transaction)
    }), 201


@api_bp.get("/transactions")
@jwt_required()
def get_transactions():
    """
    Return all transactions for the logged-in user.
    Optional query params:
    - account_id
    - category_id
    """
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    account_id = request.args.get("account_id")
    category_id = request.args.get("category_id")

    query = (
        Transaction.query
        .join(Account, Transaction.account_id == Account.id)
        .filter(Account.user_id == user.id)
    )

    # Optional filter by account_id
    if account_id is not None:
        try:
            account_id = clean_int(account_id, "account_id")
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        query = query.filter(Transaction.account_id == account_id)

    # Optional filter by category_id
    if category_id is not None:
        try:
            category_id = clean_int(category_id, "category_id")
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        query = query.filter(Transaction.category_id == category_id)

    transactions = query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).all()

    return jsonify({
        "transactions": [transaction_to_dict(t) for t in transactions],
        "count": len(transactions)
    }), 200


@api_bp.get("/transactions/<int:transaction_id>")
@jwt_required()
def get_transaction(transaction_id):
    """
    Return one transaction if it belongs to the logged-in user.
    """
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    transaction = get_user_transaction_or_404(transaction_id, user.id)
    if not transaction:
        return jsonify({"error": "Transaction not found."}), 404

    return jsonify({
        "transaction": transaction_to_dict(transaction)
    }), 200

@api_bp.put("/transactions/<int:transaction_id>")   
@jwt_required()
def update_transaction(transaction_id):
    """
    Update a transaction that belongs to the logged-in user.

    Accepts any of these JSON fields:
    {
        "account_id": 1,
        "category_id": 2,
        "amount": 35.75,
        "description": "Updated description",
        "transaction_date": "2025-09-21"
    }

    To remove a category, send:
    {
        "category_id": null
    }
    """
    data = request.get_json() or {}
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    transaction = get_user_transaction_or_404(transaction_id, user.id)
    if not transaction:
        return jsonify({"error": "Transaction not found."}), 404

    try:
        # Update account if provided
        if "account_id" in data:
            new_account_id = clean_int(data.get("account_id"), "account_id")
            account = get_user_account_or_404(new_account_id, user.id)
            if not account:
                return jsonify({"error": "Account not found or does not belong to the user."}), 404
            transaction.account_id = account.id

        # Update category if provided
        if "category_id" in data:
            raw_category_id = data.get("category_id")

            if raw_category_id is None:
                # Allow the client to remove the category
                transaction.category_id = None
            else:
                new_category_id = clean_int(raw_category_id, "category_id")
                category = get_user_category_or_404(new_category_id, user.id)
                if not category:
                    return jsonify({"error": "Category not found or does not belong to the user."}), 404
                transaction.category_id = category.id

        # Update amount if provided
        if "amount" in data:
            transaction.amount = clean_decimal(data.get("amount"), "amount")

        # Update description if provided
        if "description" in data:
            transaction.description = clean_string(
                data.get("description"),
                "description",
                required=False
            )

        # Update transaction_date if provided
        if "transaction_date" in data:
            transaction.transaction_date = clean_transaction_date(data.get("transaction_date"))

    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    db.session.commit()

    return jsonify({
        "message": "Transaction updated successfully.",
        "transaction": transaction_to_dict(transaction)
    }), 200


@api_bp.delete("/transactions/<int:transaction_id>")
@jwt_required()
def delete_transaction(transaction_id):
    """
    Delete a transaction if it belongs to the logged-in user.
    """
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    transaction = get_user_transaction_or_404(transaction_id, user.id)
    if not transaction:
        return jsonify({"error": "Transaction not found."}), 404

    db.session.delete(transaction)
    db.session.commit()

    return jsonify({
        "message": "Transaction deleted successfully."
    }), 200


# ---------- Account CRUD Routes ----------
@api_bp.post("/accounts")
@jwt_required()
def create_account():
    """
    Create a new account for the logged-in user.

    Expects JSON:
    {
        "name": "Main Checking",
        "type": "checking",
        "balance": 1000.00   # optional, defaults to 0
    }
    """
    data = request.get_json() or {}
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    try:
        name = clean_string(data.get("name"), "name", required=True, max_length=100)
        account_type = clean_string(data.get("type"), "type", required=True, max_length=50)

        # Balance is optional. If it is not provided, default to 0.
        if "balance" in data and data.get("balance") is not None:
            balance = clean_decimal(data.get("balance"), "balance")
        else:
            balance = Decimal("0.00")

    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    account = Account(
        user_id=user.id,
        name=name,
        type=account_type,
        balance=balance,
    )

    db.session.add(account)
    db.session.commit()

    return jsonify({
        "message": "Account created successfully.",
        "account": {
            "id": account.id,
            "user_id": account.user_id,
            "name": account.name,
            "type": account.type,
            "balance": str(account.balance),
            "created_at": account.created_at.isoformat(),
        }
    }), 201


@api_bp.get("/accounts")
@jwt_required()
def get_accounts():
    """
    Return all accounts for the logged-in user.
    """
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    accounts = (
        Account.query
        .filter_by(user_id=user.id)
        .order_by(Account.created_at.desc(), Account.id.desc())
        .all()
    )

    return jsonify({
        "accounts": [
            {
                "id": account.id,
                "user_id": account.user_id,
                "name": account.name,
                "type": account.type,
                "balance": str(account.balance),
                "created_at": account.created_at.isoformat(),
            }
            for account in accounts
        ],
        "count": len(accounts)
    }), 200


@api_bp.get("/accounts/<int:account_id>")
@jwt_required()
def get_account(account_id):
    """
    Return one account if it belongs to the logged-in user.
    """
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    account = get_user_account_or_404(account_id, user.id)
    if not account:
        return jsonify({"error": "Account not found."}), 404

    return jsonify({
        "account": {
            "id": account.id,
            "user_id": account.user_id,
            "name": account.name,
            "type": account.type,
            "balance": str(account.balance),
            "created_at": account.created_at.isoformat(),
        }
    }), 200


@api_bp.put("/accounts/<int:account_id>")
@jwt_required()
def update_account(account_id):
    """
    Update an account that belongs to the logged-in user.

    Accepts any of these JSON fields:
    {
        "name": "Updated Account Name",
        "type": "savings",
        "balance": 1500.00
    }
    """
    data = request.get_json() or {}
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    account = get_user_account_or_404(account_id, user.id)
    if not account:
        return jsonify({"error": "Account not found."}), 404

    try:
        if "name" in data:
            account.name = clean_string(data.get("name"), "name", required=True, max_length=100)

        if "type" in data:
            account.type = clean_string(data.get("type"), "type", required=True, max_length=50)

        if "balance" in data:
            account.balance = clean_decimal(data.get("balance"), "balance")

    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    db.session.commit()

    return jsonify({
        "message": "Account updated successfully.",
        "account": {
            "id": account.id,
            "user_id": account.user_id,
            "name": account.name,
            "type": account.type,
            "balance": str(account.balance),
            "created_at": account.created_at.isoformat(),
        }
    }), 200


@api_bp.delete("/accounts/<int:account_id>")
@jwt_required()
def delete_account(account_id):
    """
    Delete an account if it belongs to the logged-in user.
    Deleting the account will also delete its transactions because of cascade rules.
    """
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    account = get_user_account_or_404(account_id, user.id)
    if not account:
        return jsonify({"error": "Account not found."}), 404

    db.session.delete(account)
    db.session.commit()

    return jsonify({
        "message": "Account deleted successfully."
    }), 200


# ---------- Category CRUD Routes ----------
@api_bp.post("/categories")
@jwt_required()
def create_category():
    """
    Create a new category for the logged-in user.

    Expects JSON:
    {
        "name": "Food",
        "type": "expense"
    }
    """
    data = request.get_json() or {}
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    try:
        name = clean_string(data.get("name"), "name", required=True, max_length=100)
        category_type = clean_string(data.get("type"), "type", required=True, max_length=50).lower()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Restrict category type to the values expected by the app.
    if category_type not in {"income", "expense"}:
        return jsonify({"error": "type must be either 'income' or 'expense'."}), 400

    # Prevent duplicate category names for the same user.
    existing_category = Category.query.filter_by(user_id=user.id, name=name).first()
    if existing_category:
        return jsonify({"error": "A category with that name already exists for this user."}), 409

    category = Category(
        user_id=user.id,
        name=name,
        type=category_type,
    )

    db.session.add(category)
    db.session.commit()

    return jsonify({
        "message": "Category created successfully.",
        "category": {
            "id": category.id,
            "user_id": category.user_id,
            "name": category.name,
            "type": category.type,
            "created_at": category.created_at.isoformat(),
        }
    }), 201


@api_bp.get("/categories")
@jwt_required()
def get_categories():
    """
    Return all categories for the logged-in user.
    Optional query param:
    - type
    """
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    category_type = request.args.get("type")

    query = Category.query.filter_by(user_id=user.id)

    if category_type is not None:
        try:
            category_type = clean_string(category_type, "type", required=True, max_length=50).lower()
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        if category_type not in {"income", "expense"}:
            return jsonify({"error": "type must be either 'income' or 'expense'."}), 400

        query = query.filter(Category.type == category_type)

    categories = query.order_by(Category.created_at.desc(), Category.id.desc()).all()

    return jsonify({
        "categories": [
            {
                "id": category.id,
                "user_id": category.user_id,
                "name": category.name,
                "type": category.type,
                "created_at": category.created_at.isoformat(),
            }
            for category in categories
        ],
        "count": len(categories)
    }), 200


@api_bp.get("/categories/<int:category_id>")
@jwt_required()
def get_category(category_id):
    """
    Return one category if it belongs to the logged-in user.
    """
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    category = get_user_category_or_404(category_id, user.id)
    if not category:
        return jsonify({"error": "Category not found."}), 404

    return jsonify({
        "category": {
            "id": category.id,
            "user_id": category.user_id,
            "name": category.name,
            "type": category.type,
            "created_at": category.created_at.isoformat(),
        }
    }), 200


@api_bp.put("/categories/<int:category_id>")
@jwt_required()
def update_category(category_id):
    """
    Update a category that belongs to the logged-in user.

    Accepts any of these JSON fields:
    {
        "name": "Groceries",
        "type": "expense"
    }
    """
    data = request.get_json() or {}
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    category = get_user_category_or_404(category_id, user.id)
    if not category:
        return jsonify({"error": "Category not found."}), 404

    try:
        new_name = category.name
        new_type = category.type

        if "name" in data:
            new_name = clean_string(data.get("name"), "name", required=True, max_length=100)

        if "type" in data:
            new_type = clean_string(data.get("type"), "type", required=True, max_length=50).lower()
            if new_type not in {"income", "expense"}:
                return jsonify({"error": "type must be either 'income' or 'expense'."}), 400

        # Prevent duplicate category names for the same user after update.
        existing_category = (
            Category.query
            .filter(Category.user_id == user.id, Category.name == new_name, Category.id != category.id)
            .first()
        )
        if existing_category:
            return jsonify({"error": "A category with that name already exists for this user."}), 409

        category.name = new_name
        category.type = new_type

    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    db.session.commit()

    return jsonify({
        "message": "Category updated successfully.",
        "category": {
            "id": category.id,
            "user_id": category.user_id,
            "name": category.name,
            "type": category.type,
            "created_at": category.created_at.isoformat(),
        }
    }), 200


@api_bp.delete("/categories/<int:category_id>")
@jwt_required()
def delete_category(category_id):
    """
    Delete a category if it belongs to the logged-in user.
    Related transactions will keep existing records and set category_id to NULL
    because of the foreign key rule in the model.
    """
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    category = get_user_category_or_404(category_id, user.id)
    if not category:
        return jsonify({"error": "Category not found."}), 404

    db.session.delete(category)
    db.session.commit()

    return jsonify({
        "message": "Category deleted successfully."
    }), 200