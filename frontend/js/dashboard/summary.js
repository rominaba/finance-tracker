import { requireAuth, populateUserLabel } from "../auth/guard.js";
import { setupLogout } from "../auth/logout.js";
import { getAccounts } from "../api.js";
import { loadTransactions } from "../transactions/state.js";
import { renderTransactions } from "../transactions/render.js";

function formatCurrency(value) {
  return `$${Number(value).toFixed(2)}`;
}

function computeSummary(transactions) {
  let total = 0;
  let income = 0;
  let expense = 0;

  for (const tx of transactions) {
    const amount = Number(tx.amount || 0);

    if (tx.category_type === "income") {
      income += amount;
      total += amount;
    } else if (tx.category_type === "expense") {
      expense += amount;
      total -= amount;
    }
  }

  return {
    count: transactions.length,
    total,
    income,
    expense,
  };
}

async function initDashboard() {
  if (!requireAuth()) return;

  populateUserLabel();
  setupLogout();

  const message = document.getElementById("dashboard-message");

  try {
    if (message) {
      message.textContent = "Loading dashboard...";
      message.className = "";
    }

    const transactions = await loadTransactions();
    const accountsResult = await getAccounts();
    const accounts = accountsResult.accounts || [];

    const accountsMap = {};
    accounts.forEach((acc) => {
      accountsMap[String(acc.id)] = acc.name;
    });

    const summary = computeSummary(transactions);

    document.getElementById("summary-count").textContent = String(summary.count);
    document.getElementById("summary-total").textContent = formatCurrency(summary.total);
    document.getElementById("summary-income").textContent = formatCurrency(summary.income);
    document.getElementById("summary-expense").textContent = formatCurrency(summary.expense);

    renderTransactions(
      transactions.slice(0, 5),
      "dashboard-transactions-body",
      accountsMap,
      false
    );

    if (message) {
      message.textContent = "Dashboard loaded.";
      message.className = "success";
    }
  } catch (error) {
    if (message) {
      message.textContent = error.message;
      message.className = "error";
    }
  }
}

function resolveHealthUrl() {
  if (window.location.hostname === "localhost") {
    return "http://localhost:5001/health";
  }

  const host = window.location.hostname;
  const apiHost = host.startsWith("app.") ? `api.${host.slice(4)}` : host;

  return `${window.location.protocol}//${apiHost}/health`;
}

async function checkBackendStatus() {
  const statusEl = document.getElementById("status-backend");
  const timeEl = document.getElementById("status-time");

  if (!statusEl) return;

  try {
    const res = await fetch(resolveHealthUrl());

    if (!res.ok) throw new Error();

    statusEl.textContent = "Backend: 🟢 Healthy";
    statusEl.style.color = "green";
  } catch (err) {
    statusEl.textContent = "Backend: 🔴 Down";
    statusEl.style.color = "red";
  }

  if (timeEl) {
    const now = new Date().toLocaleTimeString();
    timeEl.textContent = `Last checked: ${now}`;
  }
}

function resolveSocketUrl() {
  if (window.location.hostname === "localhost") {
    return "http://localhost:5001";
  }

  const host = window.location.hostname;
  const apiHost = host.startsWith("app.") ? `api.${host.slice(4)}` : host;

  return `${window.location.protocol}//${apiHost}`;
}

async function startDashboard() {
  await initDashboard();
  await checkBackendStatus();
}

startDashboard();

const socket = io(resolveSocketUrl());

socket.on("connect", () => {
  console.log("WS connected (dashboard)");
});

socket.on("data_updated", async () => {
  console.log("Realtime update (dashboard)");
  await initDashboard();
  await checkBackendStatus();
});

setInterval(checkBackendStatus, 5000);
