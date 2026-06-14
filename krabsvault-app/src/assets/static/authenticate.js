/** @returns {Promise<PublicKeyCredentialRequestOptions>} */
async function fetchAuthenticationOptions() {
  const resp = await apiPost("/webauthn/login/options");
  return PublicKeyCredential.parseRequestOptionsFromJSON(await resp.json());
}

/** @param {PublicKeyCredentialJSON} credential */
async function verifyAuthentication(credential) {
  await apiPost("/webauthn/login/verify", credential);
}

const conditionalUIController = new AbortController();

// Abort conditional UI when the user submits the password form instead
const loginForm = document.getElementById("login-form");
if (loginForm) {
  loginForm.addEventListener("submit", () => conditionalUIController.abort());
}

async function initPasskeyLogin() {
  if (!globalThis.PublicKeyCredential) {
    console.warn("WebAuthn not supported by this browser.");
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

  if (!isConditionalSupported) {
    console.warn("Passkey autofill not supported by this browser.");
    return;
  }

  try {
    const options = await fetchAuthenticationOptions();
    console.log("Starting conditional WebAuthn flow (Passkey Autofill)…");

    navigator.credentials.get({
      publicKey: options,
      mediation: "conditional",
      signal: conditionalUIController.signal,
    }).then(async (credential) => {
      if (!credential) return;
      const submitBtn = document.getElementById("submit-btn");
      if (submitBtn) submitBtn.disabled = true;
      await verifyAuthentication(credential.toJSON());
      globalThis.location.href = "/";
    }).catch((err) => {
      if (err.name !== "AbortError") {
        console.error("Conditional WebAuthn flow failed:", err);
      }
    });
  } catch (err) {
    console.warn("Could not start passkey autofill:", err);
  }
}

document.addEventListener("DOMContentLoaded", initPasskeyLogin);
