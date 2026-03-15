import { getToken } from "./auth/session.js";

const API_BASE =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1"
    ? "http://localhost:5001"
    : "/api";

async function request(path, options = {}) {
  const token = getToken();

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  let data = null;

  try {
    data = await response.json();
  } catch {
    data = {};
  }

  if (!response.ok) {
    const message =
      data?.error || data?.message || `Request failed: ${response.status}`;
    throw new Error(message);
  }

  return data;
}

export async function loginUser(email, password) {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function registerUser(email, password) {
  return request("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getAccounts() {
  return request("/accounts");
}

export async function createAccount(account) {
  return request("/accounts", {
    method: "POST",
    body: JSON.stringify(account),
  });
}

export async function getTransactions() {
  return request("/transactions");
}

export async function createTransaction(transaction) {
  return request("/transactions", {
    method: "POST",
    body: JSON.stringify(transaction),
  });
}

export async function deleteTransaction(transactionId) {
  return request(`/transactions/${transactionId}`, {
    method: "DELETE",
  });
}
