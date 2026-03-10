import { loadTransactions } from "./state.js";
import { renderTransactions } from "./render.js";

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
      message.textContent = error.message;
      message.className = "error";
    }
  }

}
