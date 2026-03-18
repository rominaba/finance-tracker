import { createAccount, getAccounts } from "../api.js";

export async function populateAccountsDropdown(selectedAccountId = "") {
  const select = document.getElementById("account-id");
  if (!select) return [];

  select.innerHTML = "";

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Select an account";
  placeholder.disabled = true;
  placeholder.selected = true;
  select.appendChild(placeholder);

  const result = await getAccounts();
  const accounts = result.accounts || result || [];

  if (!accounts.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No accounts available";
    option.disabled = true;
    select.appendChild(option);
    return accounts;
  }

  accounts.forEach((account) => {
    const option = document.createElement("option");
    option.value = String(account.id);
    option.textContent = `${account.name} (${account.type})`;
    if (String(account.id) === String(selectedAccountId)) {
      option.selected = true;
      placeholder.selected = false;
    }
    select.appendChild(option);
  });

  return accounts;
}

export function setupAccountForm() {
  const form = document.getElementById("account-form");
  const message = document.getElementById("account-message");

  if (!form || !message) return;

  const submitBtn = form.querySelector('button[type="submit"]');

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (submitBtn) {
      submitBtn.disabled = true;
    }

    message.textContent = "Creating account...";
    message.className = "";

    const name = document.getElementById("account-name").value.trim();
    const type = document.getElementById("account-type").value;

    if (!name) {
      message.textContent = "Please enter an account name.";
      message.className = "error";
      if (submitBtn) submitBtn.disabled = false;
      return;
    }

    if (!type) {
      message.textContent = "Please select an account type.";
      message.className = "error";
      if (submitBtn) submitBtn.disabled = false;
      return;
    }

    const payload = {
      name,
      type,
    };

    try {
      const result = await createAccount(payload);
      const createdAccount = result.account;

      form.reset();
      message.textContent = "Account created successfully.";
      message.className = "success";

      if (createdAccount?.id) {
        await populateAccountsDropdown(createdAccount.id);
      } else {
        await populateAccountsDropdown();
      }
    } catch (error) {
      message.textContent = error.message || "Failed to create account.";
      message.className = "error";
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
      }
    }
  });
}
