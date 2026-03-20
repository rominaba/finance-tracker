function formatAmount(transaction) {
  const amount = Number(transaction.amount || 0);
  const type = (transaction.category_type || "").toLowerCase();

  if (type === "expense") {
    return `-$${Math.abs(amount).toFixed(2)}`;
  }

  if (type === "income") {
    return `+$${Math.abs(amount).toFixed(2)}`;
  }

  return `$${amount.toFixed(2)}`;
}

function formatDate(dateValue) {
  if (!dateValue) return "";

  const dateExtracted = String(dateValue).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (dateExtracted) {
    const year = Number(dateExtracted[1]);
    const month = Number(dateExtracted[2]) - 1; // 0 indexed
    const day = Number(dateExtracted[3]);
    const localDate = new Date(year, month, day);
    return localDate.toLocaleDateString();
  }
}

export function renderTransactions(
  transactions,
  tableBodyId = "transactions-body",
  accountsMap = {},
  showDelete = true
) {
  const tbody = document.getElementById(tableBodyId);
  if (!tbody) return;

  if (!transactions.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7">No transactions found.</td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = transactions
    .map((tx, index) => {
      const accountName =
        accountsMap[String(tx.account_id)] || `Account #${tx.account_id ?? ""}`;

      return `
        <tr>
          <td>${index+1}</td>
          <td>${formatDate(tx.transaction_date || tx.date)}</td>
          <td>${accountName}</td>
          <td>${tx.category_name || tx.category_type || ""}</td>
          <td>${formatAmount(tx)}</td>
          <td>${tx.description || ""}</td>
          ${showDelete ? `
          <td>
            <button
              type="button"
              class="delete-transaction-btn"
              data-id="${tx.id}"
            >
              Delete
            </button>
          </td>` : ""}
        </tr>
      `;
    })
    .join("");
}
