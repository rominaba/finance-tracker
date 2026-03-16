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

  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) return dateValue;

  return date.toLocaleDateString();
}

export function renderTransactions(
  transactions,
  tableBodyId = "transactions-body",
  accountsMap = {}
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
    .map((tx) => {
      const accountName =
        accountsMap[String(tx.account_id)] || `Account #${tx.account_id ?? ""}`;

      return `
        <tr>
          <td>${tx.id ?? ""}</td>
          <td>${formatDate(tx.transaction_date || tx.date)}</td>
          <td>${accountName}</td>
          <td>${tx.category_name || tx.category_type || ""}</td>
          <td>${formatAmount(tx)}</td>
          <td>${tx.description || ""}</td>
          <td></td>
        </tr>
      `;
    })
    .join("");
}
