import { getTransactions } from "../api.js";

let transactions = [];

export function getTransactionState() {
  return transactions;
}

export async function loadTransactions() {
  const result = await getTransactions();
  transactions = result.transactions || [];
  return transactions;
}