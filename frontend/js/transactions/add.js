import { createTransaction } from "../api.js";
import { refreshTransactionsPage } from "./page.js";

export function setupAddTransaction() {
  const form = document.getElementById("transaction-form");
  const message = document.getElementById("transaction-message");

  if (!form || !message) return;

  const submitBtn = form.querySelector('button[type="submit"]');

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (submitBtn) {
      submitBtn.disabled = true;
    }

    message.textContent = "Creating transaction...";
    message.className = "";

    const accountId = document.getElementById("account-id").value;
    const categoryType = document.getElementById("category-type").value;
    const categoryName = document.getElementById("category-name").value.trim();
    const amount = document.getElementById("amount").value;
    const description = document.getElementById("description").value.trim();
    const transactionDate = document.getElementById("transaction-date").value;

    const payload = {
      account_id: Number(accountId),
      category_type: categoryType,
      amount: Number(amount),
    };

    if (categoryName !== "") {
      payload.category_name = categoryName;
    }

    if (description !== "") {
      payload.description = description;
    }

    if (transactionDate !== "") {
      payload.transaction_date = transactionDate;
    }

    try {
      await createTransaction(payload);
      form.reset();
      message.textContent = "Transaction created successfully.";
      message.className = "success";

      await refreshTransactionsPage();
    } catch (error) {
      message.textContent = error.message || "Failed to create transaction.";
      message.className = "error";
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
      }
    }
  });
}
