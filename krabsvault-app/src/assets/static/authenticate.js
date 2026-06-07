/** @returns {Promise<PublicKeyCredentialRequestOptions>} */
async function fetchAuthenticationOptions() {
  const resp = await apiPost("/webauthn/login/options");
  return PublicKeyCredential.parseRequestOptionsFromJSON(await resp.json());
}

/**
 * @param {PublicKeyCredentialRequestOptions} options
 * @param {AbortSignal} [signal]
 * @returns {Promise<PublicKeyCredentialJSON>}
 */
async function getPasskeyFromAuthenticator(options, signal) {
  const getOptions = { publicKey: options };
  if (signal) {
    getOptions.signal = signal;
  }
  const credential = await navigator.credentials.get(getOptions);
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

const conditionalUIController = new AbortController();

// region UI handler
/** @returns {Promise<void>} */
async function handlePasskeyLogin() {
  const btn = document.getElementById("passkey-login-btn");
  btn.disabled = true;
  btn.textContent = "Authenticating...";

  try {
    // Abort conditional UI if it's still running
    conditionalUIController.abort();
  } catch (e) {
    // ignore
  }

  try {
    await authenticateWithPasskey();
    globalThis.location.href = "/";
  } catch (e) {
    // Only show error if the user didn't abort/cancel it intentionally
    if (e.name !== "AbortError") {
      btn.disabled = false;
      btn.textContent = "🔑 Sign in with a Passkey";
      alert("Passkey login failed: " + e.message);
    }
  }
}

document.getElementById("passkey-login-btn").addEventListener("click",
    handlePasskeyLogin);

// Also abort conditional UI if user submits the traditional password form
const loginForm = document.getElementById("login-form");
if (loginForm) {
  loginForm.addEventListener("submit", () => {
    try {
      conditionalUIController.abort();
    } catch (e) {
      // ignore
    }
  });
}

async function initPasskeyLogin() {
  const button = document.getElementById("passkey-login-btn");
  const separator = document.getElementById("passkey-login-separator");

  if (!window.PublicKeyCredential) {
    console.warn("WebAuthn is not supported by this browser.");
    button.style.display = "none";
    separator.style.display = "none";
    return;
  }

  let isConditionalSupported = false;
  if (PublicKeyCredential.isConditionalMediationAvailable) {
    try {
      isConditionalSupported = await PublicKeyCredential.isConditionalMediationAvailable();
    } catch (e) {
      console.error("Error checking conditional mediation availability:", e);
    }
  }

  try {
    // Fetch authentication options
    const options = await fetchAuthenticationOptions();
    button.style.display = "";
    separator.style.display = "";
    console.log("Webauthn options loaded successfully");

    if (isConditionalSupported) {
      console.log("Starting conditional WebAuthn flow (Passkey Autofill)...");
      
      // Start the conditional flow
      navigator.credentials.get({
        publicKey: options,
        mediation: "conditional",
        signal: conditionalUIController.signal
      }).then(async (credential) => {
        if (credential) {
          console.log("Conditional authentication received credential:", credential);
          // Disable UI to prevent double submission
          if (button) button.disabled = true;
          const submitBtn = document.getElementById("submit-btn");
          if (submitBtn) submitBtn.disabled = true;

          await verifyAuthentication(credential.toJSON());
          globalThis.location.href = "/";
        }
      }).catch((err) => {
        if (err.name !== "AbortError") {
          console.error("Conditional WebAuthn flow failed:", err);
        }
      });
    }
  } catch (err) {
    console.warn("Disabling Webauthn login because options could not be retrieved:", err);
    button.style.display = "none";
    separator.style.display = "none";
  }
}

document.addEventListener("DOMContentLoaded", initPasskeyLogin);
// endregion
