"""API routes for authentication and transaction CRUD operations."""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from sqlalchemy.exc import IntegrityError

from app import db
from app import socketio
from app.models import Account, Category, Transaction, User


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M",
)
logger = logging.getLogger(__name__)

api_bp = Blueprint("main", __name__)
password_hasher = PasswordHasher()



# -------- Helper Functions --------
def clean_string(value, field_name, required=True, max_length=None):
    if value is None:
        if required:
            raise ValueError(f"{field_name} is required.")
        return None

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")

    value = value.strip()

    if required and not value:
        raise ValueError(f"{field_name} cannot be empty.")

    if max_length is not None and len(value) > max_length:
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
    if value is None:
        raise ValueError(f"{field_name} is required.")

    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{field_name} must be a valid number.")

    return decimal_value


def clean_int(value, field_name, required=True):
    if value is None:
        if required:
            raise ValueError(f"{field_name} is required.")
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer.")


def clean_transaction_date(value):
    if value is None:
        return date.today()

    if not isinstance(value, str):
        raise ValueError("transaction_date must be a string in YYYY-MM-DD format.")

    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("transaction_date must be in YYYY-MM-DD format.")


def get_category_type_or_400(category_type):
    if category_type is None or not isinstance(category_type, str):
        raise ValueError(f"Unexpected category type: {category_type}")

    cleaned_category_type = category_type.strip().lower()
    if cleaned_category_type not in {"income", "expense"}:
        raise ValueError(f"{category_type} is not a valid category type.")

    return cleaned_category_type


def get_transaction_category_type(transaction):
    if transaction.category_id is None:
        return None

    category = getattr(transaction, "category", None)
    if category is None:
        category = db.session.get(Category, transaction.category_id)

    return category.type if category else None


def transaction_to_dict(transaction):
    return {
        "id": transaction.id,
        "account_id": transaction.account_id,
        "category_id": transaction.category_id,
        "category_type": get_transaction_category_type(transaction),
        "amount": str(transaction.amount),
        "description": transaction.description,
        "transaction_date": (
            transaction.transaction_date.isoformat()
            if transaction.transaction_date
            else None
        ),
        "created_at": (
            transaction.created_at.isoformat()
            if transaction.created_at
            else None
        ),
    }


def account_to_dict(account):
    return {
        "id": account.id,
        "user_id": account.user_id,
        "name": account.name,
        "type": account.type,
        "balance": str(account.balance),
        "created_at": account.created_at.isoformat() if account.created_at else None,
    }


def category_to_dict(category):
    return {
        "id": category.id,
        "user_id": category.user_id,
        "name": category.name,
        "type": category.type,
        "created_at": category.created_at.isoformat() if category.created_at else None,
    }


def get_current_user():
    user_id = get_jwt_identity()

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None

    return db.session.get(User, user_id)


def get_user_account_or_404(account_id, user_id):
    return Account.query.filter_by(id=account_id, user_id=user_id).first()


def get_user_category_or_404(category_id, user_id):
    return Category.query.filter_by(id=category_id, user_id=user_id).first()


def get_user_transaction_or_404(transaction_id, user_id):
    return (
        Transaction.query
        .join(Account, Transaction.account_id == Account.id)
        .filter(Transaction.id == transaction_id, Account.user_id == user_id)
        .first()
    )


def get_user_account_by_name_type(user_id, name, account_type, exclude_id=None):
    query = Account.query.filter_by(user_id=user_id, name=name, type=account_type)
    if exclude_id is not None:
        query = query.filter(Account.id != exclude_id)
    return query.first()


def get_user_category_by_name_type(user_id, name, category_type, exclude_id=None):
    query = Category.query.filter_by(user_id=user_id, name=name, type=category_type)
    if exclude_id is not None:
        query = query.filter(Category.id != exclude_id)
    return query.first()


def create_or_retrieve_category_for_user(user_id, name, category_type):
    """
    Rules:
    - same name + same type => reuse
    - same name + opposite type => reject
    - missing name => reuse/create uncategorized <type>
    """
    if user_id is None:
        raise ValueError("user_id is required.")

    cleaned_category_type = get_category_type_or_400(category_type)

    if name is None or (isinstance(name, str) and not name.strip()):
        cleaned_name = f"uncategorized {cleaned_category_type}"
    else:
        cleaned_name = clean_string(
            name,
            "category_name",
            required=True,
            max_length=100,
        )

    opposite_category = (
        Category.query
        .filter(
            Category.user_id == user_id,
            Category.name == cleaned_name,
            Category.type != cleaned_category_type,
        )
        .first()
    )
    if opposite_category:
        raise ValueError(
            f'Category "{cleaned_name}" already exists as "{opposite_category.type}".'
        )

    existing_category = get_user_category_by_name_type(
        user_id=user_id,
        name=cleaned_name,
        category_type=cleaned_category_type,
    )
    if existing_category:
        return existing_category

    category = Category(
        user_id=user_id,
        name=cleaned_name,
        type=cleaned_category_type,
    )
    db.session.add(category)
    db.session.flush()
    return category


def get_signed_amount(amount, category_type):
    normalized_amount = clean_decimal(amount, "amount")
    normalized_type = get_category_type_or_400(category_type)
    return abs(normalized_amount) if normalized_type == "income" else -abs(normalized_amount)


def update_balance_for_create_delete(transaction, user_id, transaction_type):
    account = get_user_account_or_404(transaction["account_id"], user_id)
    if not account:
        raise ValueError("Account not found or does not belong to the user.")

    if transaction["category_type"] is None:
        raise ValueError("Transaction category type is required for balance updates.")

    existing_balance = account.balance
    signed_amount = get_signed_amount(transaction["amount"], transaction["category_type"])

    if transaction_type == "create":
        new_balance = account.balance + signed_amount
    elif transaction_type == "delete":
        new_balance = account.balance - signed_amount
    else:
        raise ValueError(f"Unexpected transaction type: {transaction_type}")

    account.balance = clean_decimal(new_balance, "balance")

    logger.info(
        "Updated account balance: "
        f'{{"id": {account.id}, "user_id": {account.user_id}, "name": "{account.name}"}} '
        f"{existing_balance} -> {new_balance}"
    )


def update_balance_for_update(old_transaction, new_transaction, user_id):
    old_account = get_user_account_or_404(old_transaction["account_id"], user_id)
    new_account = get_user_account_or_404(new_transaction["account_id"], user_id)

    if not old_account or not new_account:
        raise ValueError("Account not found or does not belong to the user.")

    if old_transaction["category_type"] is None or new_transaction["category_type"] is None:
        raise ValueError("Transaction category type is required for balance updates.")

    old_signed = get_signed_amount(old_transaction["amount"], old_transaction["category_type"])
    new_signed = get_signed_amount(new_transaction["amount"], new_transaction["category_type"])

    if old_account.id == new_account.id:
        new_account.balance = clean_decimal(
            new_account.balance - old_signed + new_signed,
            "balance",
        )
    else:
        old_account.balance = clean_decimal(old_account.balance - old_signed, "balance")
        new_account.balance = clean_decimal(new_account.balance + new_signed, "balance")


# -------- Authentication Routes --------
@api_bp.post("/auth/register")
def register_user():
    data = request.get_json(silent=True) or {}

    try:
        email = clean_email(data.get("email"))
        password = clean_password(data.get("password"))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({"error": "A user with that email already exists."}), 409

        password_hash = password_hasher.hash(password)
        user = User(email=email, password_hash=password_hash)

        db.session.add(user)
        db.session.commit()

    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to register user."}), 500

    return jsonify({
        "message": "User registered successfully.",
        "user": {
            "id": user.id,
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
    }), 201


@api_bp.post("/auth/login")
def login_user():
    data = request.get_json(silent=True) or {}

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

    access_token = create_access_token(
        identity=str(user.id),
        expires_delta=timedelta(
            minutes=current_app.config["JWT_EXPIRATION_MINUTES"]
        ),
    )

    return jsonify({
        "message": "Login successful.",
        "access_token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
        }
    }), 200


# -------- Transaction CRUD Routes --------
@api_bp.post("/transactions")
@jwt_required()
def create_transaction():
    data = request.get_json(silent=True) or {}
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    try:
        account_id = clean_int(data.get("account_id"), "account_id")
        category_name = clean_string(
            data.get("category_name"),
            "category_name",
            required=False,
            max_length=100,
        )
        category_type = get_category_type_or_400(data.get("category_type"))
        amount = clean_decimal(data.get("amount"), "amount")
        description = clean_string(
            data.get("description"),
            "description",
            required=False,
        )
        transaction_date = clean_transaction_date(data.get("transaction_date"))

        account = get_user_account_or_404(account_id, user.id)
        if not account:
            return jsonify({"error": "Account not found or does not belong to the user."}), 404

        category = create_or_retrieve_category_for_user(
            user_id=user.id,
            name=category_name,
            category_type=category_type,
        )

        transaction = Transaction(
            account_id=account.id,
            category_id=category.id,
            amount=amount,
            description=description,
            transaction_date=transaction_date,
        )

        db.session.add(transaction)
        db.session.flush()

        update_balance_for_create_delete(
            transaction=transaction_to_dict(transaction),
            user_id=user.id,
            transaction_type="create",
        )

        db.session.commit()
        socketio.emit("data_updated", {"type": "transaction_created"})

    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Duplicate transaction/category/account data violates uniqueness rules."}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": f"Failed to create the transaction and update the balance:\n{e}"
        }), 400

    return jsonify({
        "message": "Transaction created successfully.",
        "transaction": transaction_to_dict(transaction),
        "category": {
            "id": category.id,
            "name": category.name,
            "type": category.type,
        }
    }), 201


@api_bp.get("/transactions")
@jwt_required()
def get_transactions():
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

    if account_id is not None:
        try:
            account_id = clean_int(account_id, "account_id")
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        query = query.filter(Transaction.account_id == account_id)

    if category_id is not None:
        try:
            category_id = clean_int(category_id, "category_id")
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        query = query.filter(Transaction.category_id == category_id)

    transactions = query.order_by(
        Transaction.transaction_date.desc(),
        Transaction.id.desc(),
    ).all()

    return jsonify({
        "transactions": [transaction_to_dict(t) for t in transactions],
        "count": len(transactions),
    }), 200


@api_bp.get("/transactions/<int:transaction_id>")
@jwt_required()
def get_transaction(transaction_id):
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    transaction = get_user_transaction_or_404(transaction_id, user.id)
    if not transaction:
        return jsonify({"error": "Transaction not found."}), 404

    return jsonify({
        "transaction": transaction_to_dict(transaction),
    }), 200


@api_bp.put("/transactions/<int:transaction_id>")
@jwt_required()
def update_transaction(transaction_id):
    data = request.get_json(silent=True) or {}
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    transaction = get_user_transaction_or_404(transaction_id, user.id)
    if not transaction:
        return jsonify({"error": "Transaction not found."}), 404

    old_transaction = transaction_to_dict(transaction)

    try:
        if "account_id" in data:
            new_account_id = clean_int(data.get("account_id"), "account_id")
            account = get_user_account_or_404(new_account_id, user.id)
            if not account:
                return jsonify({"error": "Account not found or does not belong to the user."}), 404
            transaction.account_id = account.id

        if "category_id" in data:
            raw_category_id = data.get("category_id")

            if raw_category_id is None:
                return jsonify({
                    "error": "category_id cannot be null. Transactions must always have a category."
                }), 400

            new_category_id = clean_int(raw_category_id, "category_id")
            category = get_user_category_or_404(new_category_id, user.id)
            if not category:
                return jsonify({"error": "Category not found or does not belong to the user."}), 404
            transaction.category_id = category.id

        if "amount" in data:
            transaction.amount = clean_decimal(data.get("amount"), "amount")

        if "description" in data:
            transaction.description = clean_string(
                data.get("description"),
                "description",
                required=False,
            )

        if "transaction_date" in data:
            transaction.transaction_date = clean_transaction_date(
                data.get("transaction_date")
            )

        new_transaction = transaction_to_dict(transaction)

        update_balance_for_update(
            old_transaction=old_transaction,
            new_transaction=new_transaction,
            user_id=user.id,
        )

        db.session.commit()

    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": f"Failed to update the transaction and update the balance:\n{e}"
        }), 400

    return jsonify({
        "message": "Transaction updated successfully.",
        "transaction": transaction_to_dict(transaction),
    }), 200


@api_bp.delete("/transactions/<int:transaction_id>")
@jwt_required()
def delete_transaction(transaction_id):
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    transaction = get_user_transaction_or_404(transaction_id, user.id)
    if not transaction:
        return jsonify({"error": "Transaction not found."}), 404

    target_transaction = transaction_to_dict(transaction)

    try:
        update_balance_for_create_delete(
            transaction=target_transaction,
            user_id=user.id,
            transaction_type="delete",
        )
        db.session.delete(transaction)
        db.session.commit()
        socketio.emit("data_updated", {"type": "transaction_deleted"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": f"Failed to delete the transaction and update the balance:\n{e}"
        }), 400

    return jsonify({
        "message": "Transaction deleted successfully."
    }), 200


# -------- Account CRUD Routes --------
@api_bp.post("/accounts")
@jwt_required()
def create_account():
    data = request.get_json(silent=True) or {}
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    try:
        name = clean_string(data.get("name"), "name", required=True, max_length=100)
        account_type = clean_string(data.get("type"), "type", required=True, max_length=50)

        if "balance" in data and data.get("balance") is not None:
            balance = clean_decimal(data.get("balance"), "balance")
        else:
            balance = Decimal("0.00")

        existing_account = get_user_account_by_name_type(
            user_id=user.id,
            name=name,
            account_type=account_type,
        )
        if existing_account:
            return jsonify({
                "message": "Account already existed.",
                "account": account_to_dict(existing_account),
            }), 200

        account = Account(
            user_id=user.id,
            name=name,
            type=account_type,
            balance=balance,
        )

        db.session.add(account)
        db.session.commit()

    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except IntegrityError:
        db.session.rollback()
        existing_account = get_user_account_by_name_type(
            user_id=user.id,
            name=name,
            account_type=account_type,
        )
        if existing_account:
            return jsonify({
                "message": "Account already existed.",
                "account": account_to_dict(existing_account),
            }), 200
        return jsonify({"error": "Duplicate account data violates uniqueness rules."}), 409
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to create account."}), 400

    return jsonify({
        "message": "Account created successfully.",
        "account": account_to_dict(account),
    }), 201


@api_bp.get("/accounts")
@jwt_required()
def get_accounts():
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
        "accounts": [account_to_dict(account) for account in accounts],
        "count": len(accounts),
    }), 200


@api_bp.get("/accounts/<int:account_id>")
@jwt_required()
def get_account(account_id):
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    account = get_user_account_or_404(account_id, user.id)
    if not account:
        return jsonify({"error": "Account not found."}), 404

    return jsonify({
        "account": account_to_dict(account),
    }), 200


@api_bp.put("/accounts/<int:account_id>")
@jwt_required()
def update_account(account_id):
    data = request.get_json(silent=True) or {}
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    account = get_user_account_or_404(account_id, user.id)
    if not account:
        return jsonify({"error": "Account not found."}), 404

    try:
        new_name = account.name
        new_type = account.type

        if "name" in data:
            new_name = clean_string(data.get("name"), "name", required=True, max_length=100)

        if "type" in data:
            new_type = clean_string(data.get("type"), "type", required=True, max_length=50)

        existing_account = get_user_account_by_name_type(
            user_id=user.id,
            name=new_name,
            account_type=new_type,
            exclude_id=account.id,
        )
        if existing_account:
            return jsonify({"error": "An account with that name and type already exists for this user."}), 409

        account.name = new_name
        account.type = new_type

        if "balance" in data:
            account.balance = clean_decimal(data.get("balance"), "balance")

        db.session.commit()

    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "An account with that name and type already exists for this user."}), 409
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to update account."}), 400

    return jsonify({
        "message": "Account updated successfully.",
        "account": account_to_dict(account),
    }), 200


@api_bp.delete("/accounts/<int:account_id>")
@jwt_required()
def delete_account(account_id):
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    account = get_user_account_or_404(account_id, user.id)
    if not account:
        return jsonify({"error": "Account not found."}), 404

    try:
        db.session.delete(account)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to delete account."}), 400

    return jsonify({
        "message": "Account deleted successfully."
    }), 200


# -------- Category CRUD Routes --------
@api_bp.post("/categories")
@jwt_required()
def create_category():
    data = request.get_json(silent=True) or {}
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    try:
        name = clean_string(data.get("name"), "name", required=True, max_length=100)
        category_type = get_category_type_or_400(data.get("type"))

        opposite_category = (
            Category.query
            .filter(
                Category.user_id == user.id,
                Category.name == name,
                Category.type != category_type,
            )
            .first()
        )
        if opposite_category:
            return jsonify({
                "error": f'Category "{name}" already exists as "{opposite_category.type}".'
            }), 400

        existing_category = get_user_category_by_name_type(
            user_id=user.id,
            name=name,
            category_type=category_type,
        )
        if existing_category:
            return jsonify({
                "message": "Category already existed.",
                "category": category_to_dict(existing_category),
            }), 200

        category = Category(
            user_id=user.id,
            name=name,
            type=category_type,
        )

        db.session.add(category)
        db.session.commit()

    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except IntegrityError:
        db.session.rollback()
        existing_category = get_user_category_by_name_type(
            user_id=user.id,
            name=name,
            category_type=category_type,
        )
        if existing_category:
            return jsonify({
                "message": "Category already existed.",
                "category": category_to_dict(existing_category),
            }), 200
        return jsonify({"error": "Duplicate category data violates uniqueness rules."}), 409
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to create category."}), 400

    return jsonify({
        "message": "Category created successfully.",
        "category": category_to_dict(category),
    }), 201


@api_bp.get("/categories")
@jwt_required()
def get_categories():
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    category_type = request.args.get("type")
    query = Category.query.filter_by(user_id=user.id)

    if category_type is not None:
        try:
            category_type = get_category_type_or_400(category_type)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        query = query.filter(Category.type == category_type)

    categories = query.order_by(Category.created_at.desc(), Category.id.desc()).all()

    return jsonify({
        "categories": [category_to_dict(category) for category in categories],
        "count": len(categories),
    }), 200


@api_bp.get("/categories/<int:category_id>")
@jwt_required()
def get_category(category_id):
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    category = get_user_category_or_404(category_id, user.id)
    if not category:
        return jsonify({"error": "Category not found."}), 404

    return jsonify({
        "category": category_to_dict(category),
    }), 200


@api_bp.put("/categories/<int:category_id>")
@jwt_required()
def update_category(category_id):
    data = request.get_json(silent=True) or {}
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
            new_type = get_category_type_or_400(data.get("type"))

        opposite_category = (
            Category.query
            .filter(
                Category.user_id == user.id,
                Category.name == new_name,
                Category.type != new_type,
                Category.id != category.id,
            )
            .first()
        )
        if opposite_category:
            return jsonify({
                "error": f'Category "{new_name}" already exists as "{opposite_category.type}".'
            }), 400

        existing_category = get_user_category_by_name_type(
            user_id=user.id,
            name=new_name,
            category_type=new_type,
            exclude_id=category.id,
        )
        if existing_category:
            return jsonify({
                "error": "A category with that name and type already exists for this user."
            }), 409

        category.name = new_name
        category.type = new_type
        db.session.commit()

    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "A category with that name and type already exists for this user."}), 409
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to update category."}), 400

    return jsonify({
        "message": "Category updated successfully.",
        "category": category_to_dict(category),
    }), 200


@api_bp.delete("/categories/<int:category_id>")
@jwt_required()
def delete_category(category_id):
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found."}), 404

    category = get_user_category_or_404(category_id, user.id)
    if not category:
        return jsonify({"error": "Category not found."}), 404

    try:
        db.session.delete(category)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to delete category."}), 400

    return jsonify({
        "message": "Category deleted successfully."
    }), 200
