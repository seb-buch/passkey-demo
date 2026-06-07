/** @returns {Promise<PublicKeyCredentialCreationOptions>} */
async function fetchRegistrationOptions() {
  const resp = await apiPost("/webauthn/register/options");
  return PublicKeyCredential.parseCreationOptionsFromJSON(await resp.json());
}

/**
 * @param {PublicKeyCredentialCreationOptions} options
 * @returns {Promise<PublicKeyCredentialJSON>}
 */
async function createPasskeyOnAuthenticator(options) {
  const credential = await navigator.credentials.create({publicKey: options});
  return credential.toJSON();
}

/** @param {PublicKeyCredentialJSON} credential */
async function verifyRegistration(credential) {
  await apiPost("/webauthn/register/verify", credential);
}

/** @returns {Promise<void>} */
async function registerPasskey() {
  const options = await fetchRegistrationOptions();
  const credential = await createPasskeyOnAuthenticator(options);
  await verifyRegistration(credential);
}

// region UI handler
/** @returns {Promise<void>} */
async function handlePasskeyRegistration() {
  const statusEl = document.getElementById("passkey-status");
  const btn = document.getElementById("register-passkey-btn");

  btn.disabled = true;
  btn.textContent = "Registering...";
  statusEl.style.display = "none";

  try {
    await registerPasskey();
    statusEl.textContent = "Passkey registered successfully!";
    statusEl.style.color = "#4CAF50";
    btn.textContent = "Passkey Registered";
  } catch (e) {
    statusEl.textContent = "Registration failed: " + e.message;
    statusEl.style.color = "#C41E3A";
    btn.disabled = false;
    btn.textContent = "Register a Passkey";
  }

  statusEl.style.display = "block";
}

document.getElementById("register-passkey-btn").addEventListener("click",
    handlePasskeyRegistration);

async function checkWebauthnRegistrationSupport() {
  const button = document.getElementById("register-passkey-btn");
  try {
    await apiPost("/webauthn/register/options");
    console.log("Webauthn registration options available");
    button.style.display = "";
  } catch {
    console.warn(
        "Disabling Webauthn registration because it is not available!");
    button.style.display = "none";
  }
}

document.addEventListener("DOMContentLoaded", checkWebauthnRegistrationSupport);

// endregion
