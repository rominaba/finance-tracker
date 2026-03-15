import { getToken } from "./auth/session.js";

function resolveApiBase() {
  if (window.location.hostname === "localhost") {
    return "http://localhost:5001";
  }

  // When deployed, frontend is on app.* and backend is on api.*.
  const host = window.location.hostname;
  const apiHost = host.startsWith("app.") ? `api.${host.slice(4)}` : host;
  return `${window.location.protocol}//${apiHost}`;
}

const API_BASE = resolveApiBase();

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
