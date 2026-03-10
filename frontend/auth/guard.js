import { getToken, getUser } from "./session.js";

export function requireAuth() {
  const token = getToken();

  if (!token) {
    window.location.href = "/login.html";
    return false;
  }

  return true;
}

export function populateUserLabel() {
  const userLabel = document.getElementById("user-label");
  const user = getUser();

  if (!userLabel) return;

  userLabel.textContent = user?.email
    ? `Logged in as ${user.email}`
    : "Logged in";

}
