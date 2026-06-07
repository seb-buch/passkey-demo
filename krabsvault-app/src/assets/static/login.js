function handlePasswordFormSubmit() {
  const btn = document.getElementById("submit-btn");
  btn.disabled = true;
  btn.textContent = "Authenticating...";
}

document.getElementById("login-form").addEventListener("submit",
    handlePasswordFormSubmit);
