/** @returns {Promise<PublicKeyCredentialRequestOptions>} */
async function fetchAuthenticationOptions() {
  const resp = await apiPost("/webauthn/login/options");
  return PublicKeyCredential.parseRequestOptionsFromJSON(await resp.json());
}

/**
 * @param {PublicKeyCredentialRequestOptions} options
 * @returns {Promise<PublicKeyCredentialJSON>}
 */
async function getPasskeyFromAuthenticator(options) {
  const credential = await navigator.credentials.get({publicKey: options});
  return credential.toJSON();
}

/** @param {PublicKeyCredentialJSON} credential */
async function verifyAuthentication(credential) {
  await apiPost("/webauthn/login/verify", credential);
}

/** @returns {Promise<void>} */
async function authenticateWithPasskey() {
  const options = await fetchAuthenticationOptions();
  const credential = await getPasskeyFromAuthenticator(options);
  await verifyAuthentication(credential);
}

// region UI handler
/** @returns {Promise<void>} */
async function handlePasskeyLogin() {
  const btn = document.getElementById("passkey-login-btn");
  btn.disabled = true;
  btn.textContent = "Authenticating...";

  try {
    await authenticateWithPasskey();
    globalThis.location.href = "/";
  } catch (e) {
    btn.disabled = false;
    btn.textContent = "Sign in with a Passkey";
    alert("Passkey login failed: " + e.message);
  }
}

document.getElementById("passkey-login-btn").addEventListener("click",
    handlePasskeyLogin);

async function checkWebauthnLoginSupport() {
  const button = document.getElementById("passkey-login-btn");
  const separator = document.getElementById("passkey-login-separator");

  try {
    await apiPost("/webauthn/login/options");
    button.style.display = "";
    separator.style.display = "";
    console.log("Webauthn login options available");
  } catch {
    console.warn("Disabling Webauthn login because it is not available!");
    button.style.display = "none";
    separator.style.display = "none";
  }
}

document.addEventListener("DOMContentLoaded", checkWebauthnLoginSupport);
// endregion
