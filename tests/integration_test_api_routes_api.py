#!/usr/bin/env python3
import json
import os
import sys
from decimal import Decimal

import requests

BASE_URL = os.getenv("BASE_URL", "http://localhost:5001")
EMAIL = os.getenv("EMAIL", "test@example.com")
PASSWORD = os.getenv("PASSWORD", "StrongPass123")


def print_section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    sys.exit(1)


def pass_msg(message: str) -> None:
    print(f"PASS: {message}")


def assert_nonempty(value, message: str) -> None:
    if value is None or value == "":
        fail(message)


def assert_eq(actual, expected, message: str) -> None:
    if actual != expected:
        fail(f"{message}\n  expected: {expected}\n  actual:   {actual}")


def assert_contains(haystack: str, needle: str, message: str) -> None:
    if needle not in haystack:
        fail(f"{message}\n  expected to find: {needle}\n  in: {haystack}")


def assert_decimal_eq(actual, expected, message: str) -> None:
    a = Decimal(str(actual))
    e = Decimal(str(expected))
    if a != e:
        fail(f"{message}\n  expected: {e}\n  actual:   {a}")
    pass_msg(message)


def api_call(method: str, path: str, token: str | None = None, body: dict | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.request(method, url, headers=headers, json=body, timeout=20)

    try:
        payload = response.json()
    except ValueError:
        fail(f"Non-JSON response from {method} {path}:\n{response.text}")

    return payload


def main() -> None:
    print_section("1) Register user")
    register_response = api_call(
        "POST",
        "/auth/register",
        body={"email": EMAIL, "password": PASSWORD},
    )
    print(json.dumps(register_response, indent=2))

    register_error = register_response.get("error")
    if register_error:
        assert_contains(
            register_error,
            "already exists",
            "Register should only fail because the user already exists",
        )
        pass_msg("User already existed")
    else:
        assert_eq(
            register_response.get("user", {}).get("email"),
            EMAIL,
            "Registered email mismatch",
        )
        pass_msg("User registered")

    print_section("2) Login")
    login_response = api_call(
        "POST",
        "/auth/login",
        body={"email": EMAIL, "password": PASSWORD},
    )
    print(json.dumps(login_response, indent=2))

    token = login_response.get("access_token")
    assert_nonempty(token, "Login did not return an access token")
    pass_msg("Login succeeded")

    print_section("3) Create account")
    account_response = api_call(
        "POST",
        "/accounts",
        token=token,
        body={
            "name": "Checking",
            "type": "checking",
            "balance": 1000,
        },
    )
    print(json.dumps(account_response, indent=2))

    account = account_response.get("account", {})
    account_id = account.get("id")
    account_balance = account.get("balance")
    assert_nonempty(account_id, "Account ID missing")
    assert_decimal_eq(account_balance, "1000", "Initial account balance should be 1000")

    msg = account_response.get("message", "")
    if msg == "Account already existed.":
        pass_msg("Account reused instead of duplicated")
    else:
        assert_eq(msg, "Account created successfully.", "Unexpected create account response")
        pass_msg("Account created")

    print_section("4) Create same account again: should reuse, not duplicate")
    account_response_2 = api_call(
        "POST",
        "/accounts",
        token=token,
        body={
            "name": "Checking",
            "type": "checking",
            "balance": 999999,
        },
    )
    print(json.dumps(account_response_2, indent=2))

    account2 = account_response_2.get("account", {})
    assert_eq(account_response_2.get("message"), "Account already existed.", "Duplicate account should be reused")
    assert_eq(account2.get("id"), account_id, "Duplicate account call should return same account id")
    pass_msg("Duplicate account was not created")

    print_section("5) Create expense transaction with named category food")
    tx1_response = api_call(
        "POST",
        "/transactions",
        token=token,
        body={
            "account_id": account_id,
            "category_type": "expense",
            "category_name": "food",
            "amount": 25.50,
            "description": "Lunch",
        },
    )
    print(json.dumps(tx1_response, indent=2))

    tx1 = tx1_response.get("transaction", {})
    tx1_category = tx1_response.get("category", {})
    tx1_id = tx1.get("id")
    tx1_category_id = tx1.get("category_id")
    tx1_category_name = tx1_category.get("name")
    tx1_category_type = tx1_category.get("type")

    assert_nonempty(tx1_id, "Transaction ID missing")
    assert_nonempty(tx1_category_id, "Category ID should be assigned to transaction")
    assert_eq(tx1_category_name, "food", "Named category should be food")
    assert_eq(tx1_category_type, "expense", "Category type should be expense")
    pass_msg("Named expense category created and assigned")

    print_section("6) Same name + same type category should reuse")
    tx2_response = api_call(
        "POST",
        "/transactions",
        token=token,
        body={
            "account_id": account_id,
            "category_type": "expense",
            "category_name": "food",
            "amount": 10.00,
            "description": "Snack",
        },
    )
    print(json.dumps(tx2_response, indent=2))

    tx2_category_id = tx2_response.get("transaction", {}).get("category_id")
    assert_eq(
        tx2_category_id,
        tx1_category_id,
        "Same name + same type should reuse existing category id",
    )
    pass_msg("Same-name same-type category reused")

    print_section("7) Opposite-type conflict: food as income should fail")
    tx3_response = api_call(
        "POST",
        "/transactions",
        token=token,
        body={
            "account_id": account_id,
            "category_type": "income",
            "category_name": "food",
            "amount": 99.99,
            "description": "Conflict",
        },
    )
    print(json.dumps(tx3_response, indent=2))

    tx3_error = tx3_response.get("error", "")
    assert_nonempty(tx3_error, "Opposite-type conflict should return an error")
    assert_contains(tx3_error, "food", "Conflict should mention category name")
    assert_contains(tx3_error, "expense", "Conflict should mention existing opposite type")
    pass_msg("Opposite-type named category conflict rejected")

    print_section("8) Create same category explicitly: should reuse, not duplicate")
    category_response = api_call(
        "POST",
        "/categories",
        token=token,
        body={
            "name": "food",
            "type": "expense",
        },
    )
    print(json.dumps(category_response, indent=2))

    category_obj = category_response.get("category", {})
    assert_eq(category_response.get("message"), "Category already existed.", "Duplicate category should be reused")
    assert_eq(category_obj.get("id"), tx1_category_id, "Duplicate category call should return same category id")
    pass_msg("Duplicate category was not created")

    print_section("9) No-name expense transaction should use uncategorized expense")
    tx4_response = api_call(
        "POST",
        "/transactions",
        token=token,
        body={
            "account_id": account_id,
            "category_type": "expense",
            "amount": 5.25,
            "description": "Unnamed expense",
        },
    )
    print(json.dumps(tx4_response, indent=2))

    tx4 = tx4_response.get("transaction", {})
    tx4_category = tx4_response.get("category", {})
    tx4_category_id = tx4.get("category_id")
    tx4_category_name = tx4_category.get("name")
    tx4_category_type = tx4_category.get("type")

    assert_nonempty(tx4_category_id, "Unnamed expense should get a category id")
    assert_eq(tx4_category_name, "uncategorized expense", "Unnamed expense should use default expense category")
    assert_eq(tx4_category_type, "expense", "Unnamed expense category type mismatch")
    pass_msg("Unnamed expense category created and assigned")

    print_section("10) Reuse no-name expense category")
    tx5_response = api_call(
        "POST",
        "/transactions",
        token=token,
        body={
            "account_id": account_id,
            "category_type": "expense",
            "amount": 6.75,
            "description": "Second unnamed expense",
        },
    )
    print(json.dumps(tx5_response, indent=2))

    tx5_category_id = tx5_response.get("transaction", {}).get("category_id")
    assert_eq(tx5_category_id, tx4_category_id, "Unnamed expense should reuse default expense category")
    pass_msg("Unnamed expense category reused")

    print_section("11) No-name income transaction should use uncategorized income")
    tx6_response = api_call(
        "POST",
        "/transactions",
        token=token,
        body={
            "account_id": account_id,
            "category_type": "income",
            "amount": 200.00,
            "description": "Unnamed income",
        },
    )
    print(json.dumps(tx6_response, indent=2))

    tx6 = tx6_response.get("transaction", {})
    tx6_category = tx6_response.get("category", {})
    tx6_category_id = tx6.get("category_id")
    tx6_category_name = tx6_category.get("name")
    tx6_category_type = tx6_category.get("type")

    assert_nonempty(tx6_category_id, "Unnamed income should get a category id")
    assert_eq(tx6_category_name, "uncategorized income", "Unnamed income should use default income category")
    assert_eq(tx6_category_type, "income", "Unnamed income category type mismatch")
    pass_msg("Unnamed income category created and assigned")

    print_section("12) Reuse no-name income category")
    tx7_response = api_call(
        "POST",
        "/transactions",
        token=token,
        body={
            "account_id": account_id,
            "category_type": "income",
            "amount": 50.00,
            "description": "Second unnamed income",
        },
    )
    print(json.dumps(tx7_response, indent=2))

    tx7_category_id = tx7_response.get("transaction", {}).get("category_id")
    assert_eq(tx7_category_id, tx6_category_id, "Unnamed income should reuse default income category")
    pass_msg("Unnamed income category reused")

    print_section("13) Verify category list has no duplicate name+type rows")
    categories_response = api_call("GET", "/categories", token=token)
    print(json.dumps(categories_response, indent=2))

    categories = categories_response.get("categories", [])
    seen = set()
    for c in categories:
        key = (c.get("name"), c.get("type"))
        if key in seen:
            fail(f"Duplicate category found in API results: {key}")
        seen.add(key)
    pass_msg("No duplicate category name+type pairs found")

    print_section("14) Verify account list has no duplicate name+type rows")
    accounts_response = api_call("GET", "/accounts", token=token)
    print(json.dumps(accounts_response, indent=2))

    accounts = accounts_response.get("accounts", [])
    seen = set()
    for a in accounts:
        key = (a.get("name"), a.get("type"))
        if key in seen:
            fail(f"Duplicate account found in API results: {key}")
        seen.add(key)
    pass_msg("No duplicate account name+type pairs found")

    print_section("15) Verify final account balance")
    account_show_response = api_call("GET", f"/accounts/{account_id}", token=token)
    print(json.dumps(account_show_response, indent=2))

    final_balance = account_show_response.get("account", {}).get("balance")
    assert_decimal_eq(final_balance, "1202.50", "Final balance should be 1202.50")

    print_section("16) Summary")
    print("All requested duplicate-prevention and category scenarios passed.")


if __name__ == "__main__":
    main()