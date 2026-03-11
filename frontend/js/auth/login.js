
import { loginUser, registerUser } from "../api.js";
import { setSession, getToken } from "./session.js";

document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("login-form");
  const loginMessage = document.getElementById("login-message");

  const registerForm = document.getElementById("register-form");
  const registerMessage = document.getElementById("register-message");

  // Simple email validation
  function isValidEmail(email) {
    const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return pattern.test(email);
  }

  if (getToken()) {
    window.location.href = "/dashboard.html";
  }

  if (loginForm && loginMessage) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      loginMessage.textContent = "Logging in...";
      loginMessage.className = "";

      const email = document.getElementById("email").value.trim();
      const password = document.getElementById("password").value;

      if (!isValidEmail(email)) {
        loginMessage.textContent = "Invalid email.";
        loginMessage.className = "error";
        return;
      }

      try {
        const result = await loginUser(email, password);
        setSession(result.access_token, result.user);

        loginMessage.textContent = "Login successful.";
        loginMessage.className = "success";

        window.location.href = "/dashboard.html";
      } catch (error) {
        loginMessage.textContent = error.message;
        loginMessage.className = "error";
      }
    });
  }

  if (registerForm && registerMessage) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      registerMessage.textContent = "Registering...";
      registerMessage.className = "";

      const email = document.getElementById("register-email").value.trim();
      const password = document.getElementById("register-password").value;

      if (!isValidEmail(email)) {
        registerMessage.textContent = "Invalid email.";
        registerMessage.className = "error";
        return;
      }

      try {
        const result = await registerUser(email, password);
        console.log("REGISTER RESPONSE:", result); // debug

        registerMessage.textContent =
          "Registration successful. You can now login.";
        registerMessage.className = "success";

        // Optional: clear form after successful registration
        registerForm.reset();
      } catch (error) {
        registerMessage.textContent = error.message;
        registerMessage.className = "error";
      }
    });
  }
});