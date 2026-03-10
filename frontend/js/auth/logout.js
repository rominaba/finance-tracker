import { clearSession } from "./session.js";

export function setupLogout() {
  const logoutBtn = document.getElementById("logout-btn");
  if (!logoutBtn) return;

  logoutBtn.addEventListener("click", () => {
    clearSession();
    window.location.href = "/login.html";
  });

}
