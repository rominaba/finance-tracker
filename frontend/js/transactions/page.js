import { requireAuth, populateUserLabel } from "../auth/guard.js";
import { setupLogout } from "../auth/logout.js";
import { loadTransactions } from "./state.js";
import { renderTransactions } from "./render.js";
import { setupAddTransaction } from "./add.js";
import { populateAccountsDropdown } from "./accounts.js";

export async function refreshTransactionsPage() {
  const message = document.getElementById("transactions-message");

  try {
    if (message) {
      message.textContent = "Loading transactions...";
      message.className = "";
    }

    const transactions = await loadTransactions();
    renderTransactions(transactions, "transactions-body");

    if (message) {
      message.textContent = `${transactions.length} transaction(s) loaded.`;
      message.className = "success";
    }
  } catch (error) {
    renderTransactions([], "transactions-body");

    if (message) {
      message.textContent = error.message || "Failed to load transactions.";
      message.className = "error";
    }
  }
}

function setupRefresh() {
  const refreshBtn = document.getElementById("refresh-btn");
  if (!refreshBtn) return;

  refreshBtn.addEventListener("click", async () => {
    await refreshTransactionsPage();
  });
}

export async function initTransactionsPage() {
  if (!requireAuth()) return;

  populateUserLabel();
  setupLogout();

  try {
    await populateAccountsDropdown();
  } catch (error) {
    console.error("Failed to populate accounts dropdown:", error);
  }

  setupAddTransaction();
  setupRefresh();

  await refreshTransactionsPage();
}

initTransactionsPage();

