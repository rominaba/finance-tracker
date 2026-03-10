import { loginUser } from "../api.js";
import { setSession, getToken } from "./session.js";

const form = document.getElementById("login-form");
const message = document.getElementById("login-message");

if (getToken()) {
  window.location.href = "/dashboard.html";
}

if (form && message) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    message.textContent = "Logging in...";
    message.className = "";

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    try {
      const result = await loginUser(email, password);
      setSession(result.access_token, result.user);
      message.textContent = "Login successful.";
      message.className = "success";

      window.location.href = "/dashboard.html";
    } catch (error) {
      message.textContent = error.message;
      message.className = "error";
    }
  });
}