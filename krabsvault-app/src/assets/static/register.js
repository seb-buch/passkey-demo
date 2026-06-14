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
  const infobox = document.getElementById("infobox");
  const btn = document.getElementById("register-passkey-btn");

  btn.disabled = true;
  btn.textContent = "Registering...";

  const showInfobox = (message, isError) => {
    infobox.textContent = message;
    infobox.classList.toggle("error", isError);
    infobox.style.display = "block";
    setTimeout(() => { infobox.style.display = "none"; }, 5000);
  };

  try {
    await registerPasskey();
    showInfobox("Passkey registered! Reloading...", false);
    setTimeout(() => location.reload(), 1500);
  } catch (e) {
    if (e.name === "InvalidStateError") {
      showInfobox("This device already has a passkey registered.", false);
      btn.replaceWith((() => {
        const icon = document.createElement("span");
        icon.className = "material-symbols-outlined";
        icon.textContent = "shield_lock";
        const badge = document.createElement("span");
        badge.className = "secured-badge";
        badge.appendChild(icon);
        badge.append(" Passkey Registered");
        return badge;
      })());
      return;
    }
    showInfobox("Registration failed: " + e.message, true);
    btn.disabled = false;
    btn.textContent = "Register Passkey";
  }
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
