export function renderTransactions(transactions, tbodyId, emptyMessageId = null) {
  const tbody = document.getElementById(tbodyId);
  const message = emptyMessageId ? document.getElementById(emptyMessageId) : null;

  if (!tbody) return;

  tbody.innerHTML = "";

  if (!transactions.length) {
    if (message) {
      message.textContent = "No transactions found.";
      message.className = "";
    }
    return;
  }

  if (message) {
    message.textContent = "";
  }

  transactions.forEach((tx) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${tx.id}</td>
      <td>${tx.transaction_date ?? ""}</td>
      <td>${tx.account_id ?? ""}</td>
      <td>${tx.category_id ?? ""}</td>
      <td>${tx.amount ?? ""}</td>
      <td>${tx.description ?? ""}</td>
    `;
    tbody.appendChild(row);
  });
}