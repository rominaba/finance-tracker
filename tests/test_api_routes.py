import os
import sys
from datetime import date
from decimal import Decimal

import pytest
from argon2 import PasswordHasher

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import User, Account, Category, Transaction


password_hasher = PasswordHasher()


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "JWT_SECRET_KEY": "test-secret-key",
        "JWT_EXPIRATION_MINUTES":60,
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def create_user(email="user@example.com", password="password123"):
    user = User(
        email=email,
        password_hash=password_hasher.hash(password),
    )
    db.session.add(user)
    db.session.commit()
    return user


def create_account(user_id, name="Checking", type_="checking", balance="100.00"):
    account = Account(
        user_id=user_id,
        name=name,
        type=type_,
        balance=Decimal(balance),
    )
    db.session.add(account)
    db.session.commit()
    return account


def create_category(user_id, name="Food", type_="expense"):
    category = Category(
        user_id=user_id,
        name=name,
        type=type_,
    )
    db.session.add(category)
    db.session.commit()
    return category


def create_transaction(
    account_id,
    amount="25.50",
    category_id=None,
    description="Lunch",
    transaction_date_=date(2025, 9, 20),
):
    transaction = Transaction(
        account_id=account_id,
        category_id=category_id,
        amount=Decimal(amount),
        description=description,
        transaction_date=transaction_date_,
    )
    db.session.add(transaction)
    db.session.commit()
    return transaction


@pytest.fixture
def auth_headers(client, app):
    with app.app_context():
        create_user()

    response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )
    token = response.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_home_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.data.decode() == "Finance Tracker API is running!"


def test_register_user_success(client):
    response = client.post(
        "/auth/register",
        json={"email": "NEWUSER@example.com", "password": "password123"},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["message"] == "User registered successfully."
    assert body["user"]["email"] == "newuser@example.com"


def test_register_user_duplicate_email(client, app):
    with app.app_context():
        create_user("dup@example.com", "password123")

    response = client.post(
        "/auth/register",
        json={"email": "dup@example.com", "password": "password123"},
    )

    assert response.status_code == 409
    assert response.get_json()["error"] == "A user with that email already exists."


def test_register_user_invalid_email(client):
    response = client.post(
        "/auth/register",
        json={"email": "bad-email", "password": "password123"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "email must be a valid email address."


def test_register_user_short_password(client):
    response = client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "short"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "password must be at least 8 characters long."


def test_login_user_success(client, app):
    with app.app_context():
        create_user("login@example.com", "password123")

    response = client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["message"] == "Login successful."
    assert "access_token" in body
    assert body["user"]["email"] == "login@example.com"


def test_login_user_invalid_password(client, app):
    with app.app_context():
        create_user("login@example.com", "password123")

    response = client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "Invalid email or password."


def test_login_user_missing_user(client):
    response = client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": "password123"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "Invalid email or password."


def test_protected_route_requires_jwt(client):
    response = client.get("/accounts")
    assert response.status_code == 401


def test_create_account_success(client, auth_headers):
    response = client.post(
        "/accounts",
        headers=auth_headers,
        json={"name": "Main Checking", "type": "checking", "balance": "1000.50"},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["message"] == "Account created successfully."
    assert body["account"]["name"] == "Main Checking"
    assert body["account"]["type"] == "checking"
    assert body["account"]["balance"] == "1000.50"


def test_create_account_defaults_balance_to_zero(client, auth_headers):
    response = client.post(
        "/accounts",
        headers=auth_headers,
        json={"name": "Savings", "type": "savings"},
    )

    assert response.status_code == 201
    assert response.get_json()["account"]["balance"] == "0.00"


def test_create_account_invalid_name(client, auth_headers):
    response = client.post(
        "/accounts",
        headers=auth_headers,
        json={"name": "", "type": "checking"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "name cannot be empty."


def test_get_accounts_only_returns_current_users_accounts(client, app):
    with app.app_context():
        user1 = create_user("u1@example.com", "password123")
        user2 = create_user("u2@example.com", "password123")
        create_account(user1.id, name="U1 Account")
        create_account(user2.id, name="U2 Account")

    login = client.post(
        "/auth/login",
        json={"email": "u1@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.get("/accounts", headers=headers)
    body = response.get_json()

    assert response.status_code == 200
    assert body["count"] == 1
    assert body["accounts"][0]["name"] == "U1 Account"


def test_get_account_success(client, app):
    with app.app_context():
        user = create_user("acct@example.com", "password123")
        account = create_account(user.id, name="Primary")
        account_id = account.id

    login = client.post(
        "/auth/login",
        json={"email": "acct@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.get(f"/accounts/{account_id}", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["account"]["name"] == "Primary"


def test_get_account_forbidden_cross_user_returns_404(client, app):
    with app.app_context():
        create_user("u1@example.com", "password123")
        user2 = create_user("u2@example.com", "password123")
        account2 = create_account(user2.id, name="User2 Account")
        account2_id = account2.id

    login = client.post(
        "/auth/login",
        json={"email": "u1@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.get(f"/accounts/{account2_id}", headers=headers)

    assert response.status_code == 404
    assert response.get_json()["error"] == "Account not found."


def test_update_account_success(client, app):
    with app.app_context():
        user = create_user("acct@example.com", "password123")
        account = create_account(user.id, name="Old Name", type_="checking", balance="10.00")
        account_id = account.id

    login = client.post(
        "/auth/login",
        json={"email": "acct@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.put(
        f"/accounts/{account_id}",
        headers=headers,
        json={"name": "New Name", "type": "savings", "balance": "999.99"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["account"]["name"] == "New Name"
    assert body["account"]["type"] == "savings"
    assert body["account"]["balance"] == "999.99"


def test_delete_account_success(client, app):
    with app.app_context():
        user = create_user("acct@example.com", "password123")
        account = create_account(user.id)
        account_id = account.id

    login = client.post(
        "/auth/login",
        json={"email": "acct@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.delete(f"/accounts/{account_id}", headers=headers)
    assert response.status_code == 200
    assert response.get_json()["message"] == "Account deleted successfully."

    with app.app_context():
        assert Account.query.get(account_id) is None


def test_create_category_success(client, auth_headers):
    response = client.post(
        "/categories",
        headers=auth_headers,
        json={"name": "Food", "type": "expense"},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["category"]["name"] == "Food"
    assert body["category"]["type"] == "expense"


def test_create_category_rejects_invalid_type(client, auth_headers):
    response = client.post(
        "/categories",
        headers=auth_headers,
        json={"name": "Stuff", "type": "other"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "type must be either 'income' or 'expense'."


def test_create_category_duplicate_for_same_user_returns_409(client, app):
    with app.app_context():
        user = create_user("cat@example.com", "password123")
        create_category(user.id, name="Food", type_="expense")

    login = client.post(
        "/auth/login",
        json={"email": "cat@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.post(
        "/categories",
        headers=headers,
        json={"name": "Food", "type": "expense"},
    )

    assert response.status_code == 409
    assert response.get_json()["error"] == "A category with that name already exists for this user."


def test_create_category_same_name_for_different_users_is_allowed(client, app):
    with app.app_context():
        user1 = create_user("u1@example.com", "password123")
        create_category(user1.id, name="Food", type_="expense")
        create_user("u2@example.com", "password123")

    login = client.post(
        "/auth/login",
        json={"email": "u2@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.post(
        "/categories",
        headers=headers,
        json={"name": "Food", "type": "expense"},
    )

    assert response.status_code == 201


def test_get_categories_filter_by_type(client, app):
    with app.app_context():
        user = create_user("cat@example.com", "password123")
        create_category(user.id, name="Salary", type_="income")
        create_category(user.id, name="Groceries", type_="expense")

    login = client.post(
        "/auth/login",
        json={"email": "cat@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.get("/categories?type=expense", headers=headers)

    assert response.status_code == 200
    body = response.get_json()
    assert body["count"] == 1
    assert body["categories"][0]["name"] == "Groceries"


def test_update_category_duplicate_name_returns_409(client, app):
    with app.app_context():
        user = create_user("cat@example.com", "password123")
        create_category(user.id, name="Food", type_="expense")
        cat2 = create_category(user.id, name="Transport", type_="expense")
        cat2_id = cat2.id

    login = client.post(
        "/auth/login",
        json={"email": "cat@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.put(
        f"/categories/{cat2_id}",
        headers=headers,
        json={"name": "Food"},
    )

    assert response.status_code == 409
    assert response.get_json()["error"] == "A category with that name already exists for this user."


def test_update_category_success(client, app):
    with app.app_context():
        user = create_user("cat@example.com", "password123")
        category = create_category(user.id, name="Food", type_="expense")
        category_id = category.id

    login = client.post(
        "/auth/login",
        json={"email": "cat@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.put(
        f"/categories/{category_id}",
        headers=headers,
        json={"name": "Groceries", "type": "expense"},
    )

    assert response.status_code == 200
    assert response.get_json()["category"]["name"] == "Groceries"


def test_delete_category_success(client, app):
    with app.app_context():
        user = create_user("cat@example.com", "password123")
        category = create_category(user.id, name="Food", type_="expense")
        category_id = category.id

    login = client.post(
        "/auth/login",
        json={"email": "cat@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.delete(f"/categories/{category_id}", headers=headers)
    assert response.status_code == 200
    assert response.get_json()["message"] == "Category deleted successfully."


def test_create_transaction_success(client, app):
    with app.app_context():
        user = create_user("txn@example.com", "password123")
        account = create_account(user.id, name="Checking")
        category = create_category(user.id, name="Food", type_="expense")
        account_id = account.id
        category_id = category.id

    login = client.post(
        "/auth/login",
        json={"email": "txn@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": account_id,
            "category_id": category_id,
            "amount": "25.50",
            "description": "Lunch",
            "transaction_date": "2025-09-20",
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["message"] == "Transaction created successfully."
    assert body["transaction"]["account_id"] == account_id
    assert body["transaction"]["category_id"] == category_id
    assert body["transaction"]["amount"] == "25.50"
    assert body["transaction"]["description"] == "Lunch"
    assert body["transaction"]["transaction_date"] == "2025-09-20"


def test_create_transaction_without_category_success(client, app):
    with app.app_context():
        user = create_user("txn@example.com", "password123")
        account = create_account(user.id)
        account_id = account.id

    login = client.post(
        "/auth/login",
        json={"email": "txn@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": account_id,
            "amount": "40.00",
            "description": "Misc",
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["transaction"]["category_id"] is None
    assert body["transaction"]["amount"] == "40.00"


def test_create_transaction_rejects_other_users_account(client, app):
    with app.app_context():
        create_user("u1@example.com", "password123")
        user2 = create_user("u2@example.com", "password123")
        foreign_account = create_account(user2.id)
        foreign_account_id = foreign_account.id

    login = client.post(
        "/auth/login",
        json={"email": "u1@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": foreign_account_id,
            "amount": "10.00",
            "description": "Hack attempt",
        },
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "Account not found or does not belong to the user."


def test_create_transaction_rejects_invalid_amount(client, app):
    with app.app_context():
        user = create_user("txn@example.com", "password123")
        account = create_account(user.id)
        account_id = account.id

    login = client.post(
        "/auth/login",
        json={"email": "txn@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": account_id,
            "amount": "not-a-number",
            "description": "Bad data",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "amount must be a valid number."


def test_get_transactions_only_for_current_user(client, app):
    with app.app_context():
        user1 = create_user("u1@example.com", "password123")
        user2 = create_user("u2@example.com", "password123")

        account1 = create_account(user1.id)
        account2 = create_account(user2.id)

        create_transaction(account1.id, amount="10.00", description="User1 txn")
        create_transaction(account2.id, amount="20.00", description="User2 txn")

    login = client.post(
        "/auth/login",
        json={"email": "u1@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.get("/transactions", headers=headers)
    body = response.get_json()

    assert response.status_code == 200
    assert body["count"] == 1
    assert body["transactions"][0]["description"] == "User1 txn"


def test_get_transactions_filter_by_account_id(client, app):
    with app.app_context():
        user = create_user("txn@example.com", "password123")
        account1 = create_account(user.id, name="A1")
        account2 = create_account(user.id, name="A2")

        create_transaction(account1.id, amount="10.00", description="On A1")
        create_transaction(account2.id, amount="20.00", description="On A2")

        account1_id = account1.id

    login = client.post(
        "/auth/login",
        json={"email": "txn@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.get(f"/transactions?account_id={account1_id}", headers=headers)
    body = response.get_json()

    assert response.status_code == 200
    assert body["count"] == 1
    assert body["transactions"][0]["description"] == "On A1"


def test_get_single_transaction_success(client, app):
    with app.app_context():
        user = create_user("txn@example.com", "password123")
        account = create_account(user.id)
        txn = create_transaction(account.id, amount="22.22")
        txn_id = txn.id

    login = client.post(
        "/auth/login",
        json={"email": "txn@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.get(f"/transactions/{txn_id}", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["transaction"]["id"] == txn_id


def test_get_single_transaction_cross_user_returns_404(client, app):
    with app.app_context():
        create_user("u1@example.com", "password123")
        user2 = create_user("u2@example.com", "password123")
        account2 = create_account(user2.id)
        txn2 = create_transaction(account2.id, amount="11.11")
        txn2_id = txn2.id

    login = client.post(
        "/auth/login",
        json={"email": "u1@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.get(f"/transactions/{txn2_id}", headers=headers)

    assert response.status_code == 404
    assert response.get_json()["error"] == "Transaction not found."


def test_update_transaction_success(client, app):
    with app.app_context():
        user = create_user("txn@example.com", "password123")
        account = create_account(user.id)
        category = create_category(user.id, name="Food", type_="expense")
        txn = create_transaction(account.id, amount="25.50", description="Lunch")

        txn_id = txn.id
        category_id = category.id

    login = client.post(
        "/auth/login",
        json={"email": "txn@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.put(
        f"/transactions/{txn_id}",
        headers=headers,
        json={
            "amount": "30.75",
            "description": "Updated lunch",
            "category_id": category_id,
            "transaction_date": "2025-09-21",
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["transaction"]["amount"] == "30.75"
    assert body["transaction"]["description"] == "Updated lunch"
    assert body["transaction"]["category_id"] == category_id
    assert body["transaction"]["transaction_date"] == "2025-09-21"


def test_update_transaction_can_remove_category(client, app):
    with app.app_context():
        user = create_user("txn@example.com", "password123")
        account = create_account(user.id)
        category = create_category(user.id, name="Food", type_="expense")
        txn = create_transaction(account.id, category_id=category.id)
        txn_id = txn.id

    login = client.post(
        "/auth/login",
        json={"email": "txn@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.put(
        f"/transactions/{txn_id}",
        headers=headers,
        json={"category_id": None},
    )

    assert response.status_code == 200
    assert response.get_json()["transaction"]["category_id"] is None


def test_update_transaction_rejects_other_users_category(client, app):
    with app.app_context():
        user1 = create_user("u1@example.com", "password123")
        user2 = create_user("u2@example.com", "password123")
        account1 = create_account(user1.id)
        txn = create_transaction(account1.id)
        foreign_category = create_category(user2.id, name="Foreign", type_="expense")

        txn_id = txn.id
        foreign_category_id = foreign_category.id

    login = client.post(
        "/auth/login",
        json={"email": "u1@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.put(
        f"/transactions/{txn_id}",
        headers=headers,
        json={"category_id": foreign_category_id},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "Category not found or does not belong to the user."


def test_delete_transaction_success(client, app):
    with app.app_context():
        user = create_user("txn@example.com", "password123")
        account = create_account(user.id)
        txn = create_transaction(account.id)
        txn_id = txn.id

    login = client.post(
        "/auth/login",
        json={"email": "txn@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    response = client.delete(f"/transactions/{txn_id}", headers=headers)
    assert response.status_code == 200
    assert response.get_json()["message"] == "Transaction deleted successfully."

    with app.app_context():
        assert Transaction.query.get(txn_id) is None