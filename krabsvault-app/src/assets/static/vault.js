const backdrop = document.getElementById("popup-backdrop");

function openPopup() {
  backdrop.classList.remove("hidden");
}

function closePopup() {
  backdrop.classList.add("hidden");
}

/** @param {KeyboardEvent} event */
function handleEscapeKey(event) {
  if (event.key === "Escape") {
    closePopup();
  }
}

document.getElementById("btn-preview").addEventListener("click", openPopup);
document.getElementById("btn-download").addEventListener("click", openPopup);
document.getElementById("popup-dismiss").addEventListener("click", closePopup);
document.getElementById("popup-close").addEventListener("click", closePopup);
document.addEventListener("keydown", handleEscapeKey);
