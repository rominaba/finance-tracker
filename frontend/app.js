import { requireAuth, populateUserLabel } from "./auth/guard.js";
import { setupLogout } from "./auth/logout.js";
import { setupAddTransaction } from "./transactions/add.js";
import { refreshTransactionsPage } from "./transactions/page.js";

function setupRefresh() {
  const refreshBtn = document.getElementById("refresh-btn");
  if (!refreshBtn) return;

  refreshBtn.addEventListener("click", async () => {
    await refreshTransactionsPage();
  });
}

async function initTransactionsPage() {
  if (!requireAuth()) return;

  populateUserLabel();
  setupLogout();
  setupAddTransaction();
  setupRefresh();
  await refreshTransactionsPage();
}

initTransactionsPage();