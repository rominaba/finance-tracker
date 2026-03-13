import { getAccounts } from "../api.js";

export async function populateAccountsDropdown() {
  const select = document.getElementById("account-id");
  if (!select) return;

  select.innerHTML = "";

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Select an account";
  placeholder.disabled = true;
  placeholder.selected = true;
  select.appendChild(placeholder);

  const result = await getAccounts();
  const accounts = result.accounts || [];

  if (!accounts.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No accounts available";
    option.disabled = true;
    select.appendChild(option);
    return;
  }

  accounts.forEach((account) => {
    const option = document.createElement("option");
    option.value = account.id;
    option.textContent = `${account.name} (${account.type})`;
    select.appendChild(option);
  });
}