import { requireAuth, populateUserLabel } from "../auth/guard.js";
import { setupLogout } from "../auth/logout.js";
import { getAccounts, deleteTransaction } from "../api.js";
import { loadTransactions } from "./state.js";
import { renderTransactions } from "./render.js";
import { setupAddTransaction } from "./add.js";
import { populateAccountsDropdown, setupAccountForm } from "./accounts.js";

function buildAccountsMap(accounts) {
  const map = {};

  accounts.forEach((account) => {
    map[String(account.id)] = account.name;
  });

  return map;
}

function setupRefresh() {
  const refreshBtn = document.getElementById("refresh-btn");
  if (!refreshBtn) return;

  refreshBtn.addEventListener("click", async () => {
    await refreshTransactionsPage();
  });
}

function setupDeleteButtons() {
  const tbody = document.getElementById("transactions-body");
  const message = document.getElementById("transactions-message");

  if (!tbody) return;

  tbody.addEventListener("click", async (event) => {
    const button = event.target.closest(".delete-transaction-btn");
    if (!button) return;

    const transactionId = button.dataset.id;
    if (!transactionId) return;

    const confirmed = window.confirm(
      "Are you sure you want to delete this transaction?"
    );

    if (!confirmed) return;

    try {
      button.disabled = true;

      if (message) {
        message.textContent = "Deleting transaction...";
        message.className = "";
      }

      await deleteTransaction(transactionId);
      await refreshTransactionsPage();

      if (message) {
        message.textContent = "Transaction deleted successfully.";
        message.className = "success";
      }
    } catch (error) {
      if (message) {
        message.textContent =
          error.message || "Failed to delete transaction.";
        message.className = "error";
      }
      button.disabled = false;
    }
  });
}

export async function refreshTransactionsPage() {
  const message = document.getElementById("transactions-message");

  try {
    if (message) {
      message.textContent = "Loading transactions...";
      message.className = "";
    }

    const [accountsResult, transactions] = await Promise.all([
      getAccounts(),
      loadTransactions(),
    ]);

    const accounts = accountsResult.accounts || [];
    const accountsMap = buildAccountsMap(accounts);

    renderTransactions(transactions, "transactions-body", accountsMap);

    if (message) {
      message.textContent = `${transactions.length} transaction(s) loaded.`;
      message.className = "success";
    }
  } catch (error) {
    renderTransactions([], "transactions-body", {});

    if (message) {
      message.textContent = error.message || "Failed to load transactions.";
      message.className = "error";
    }
  }
}

export async function initTransactionsPage() {
  if (!requireAuth()) return;

  populateUserLabel();
  setupLogout();
  setupAccountForm();

  try {
    await populateAccountsDropdown();
  } catch (error) {
    console.error("Failed to populate accounts dropdown:", error);
  }

  setupAddTransaction();
  setupRefresh();
  setupDeleteButtons();

  await refreshTransactionsPage();
}

initTransactionsPage();
