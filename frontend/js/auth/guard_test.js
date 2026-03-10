export function requireAuth() {
  return true;
}

export function populateUserLabel() {
  const userLabel = document.getElementById("user-label");
  if (!userLabel) return;

  userLabel.textContent = "Logged in as demo@test.com";

}
