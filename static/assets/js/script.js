'use strict';

// ===============================
// Element Toggle Utility
// ===============================
const elementToggleFunc = function (elem) {
  elem.classList.toggle("active");
};

// ===============================
// Sidebar Toggle (Mobile)
// ===============================
const sidebar = document.querySelector("[data-sidebar]");
const sidebarBtn = document.querySelector("[data-sidebar-btn]");

if (sidebar && sidebarBtn) {
  sidebarBtn.addEventListener("click", () => elementToggleFunc(sidebar));
}

// ===============================
// Testimonials Modal
// ===============================
const modalContainer = document.querySelector("[data-modal-container]");
const modalCloseBtn = document.querySelector("[data-modal-close-btn]");
const overlay = document.querySelector("[data-overlay]");
const modalImg = document.querySelector("[data-modal-img]");
const modalTitle = document.querySelector("[data-modal-title]");
const modalText = document.querySelector("[data-modal-text]");
const testimonialsItem = document.querySelectorAll("[data-testimonials-item]");

if (testimonialsItem.length > 0 && modalContainer && modalCloseBtn && overlay) {
  testimonialsItem.forEach(item => {
    item.addEventListener("click", function () {
      modalImg.src = this.querySelector("[data-testimonials-avatar]").src;
      modalTitle.innerHTML = this.querySelector("[data-testimonials-title]").innerHTML;
      modalText.innerHTML = this.querySelector("[data-testimonials-text]").innerHTML;
      modalContainer.classList.add("active");
      overlay.classList.add("active");
    });
  });

  modalCloseBtn.addEventListener("click", () => {
    modalContainer.classList.remove("active");
    overlay.classList.remove("active");
  });

  overlay.addEventListener("click", () => {
    modalContainer.classList.remove("active");
    overlay.classList.remove("active");
  });
}

// ===============================
// Project Filtering System
// ===============================
// Filter logic


// ===============================
// Contact Form Validation
// ===============================
const form = document.querySelector("[data-form]");
const formInputs = document.querySelectorAll("[data-form-input]");
const formBtn = document.querySelector("[data-form-btn]");

if (form && formInputs.length > 0 && formBtn) {
  formInputs.forEach(input => {
    input.addEventListener("input", () => {
      formBtn.disabled = !form.checkValidity();
    });
  });
}

// ===============================
// Image Modal (Zoom)
// ===============================
function openModal(img) {
  const modal = document.getElementById("myModal");
  const modalImg = document.getElementById("modalImage");
  const captionText = document.getElementById("caption");

  if (modal && modalImg && captionText) {
    modal.style.display = "flex";
    modalImg.src = img.src;
    captionText.innerHTML = img.alt || "";
  }
}

function closeModal() {
  const modal = document.getElementById("myModal");
  if (modal) modal.style.display = "none";
}

window.onclick = function (e) {
  const modal = document.getElementById("myModal");
  if (e.target === modal) closeModal();
};

window.onkeydown = function (e) {
  if (e.key === "Escape") closeModal();
};

document.querySelectorAll("[data-src]").forEach(img => {
  img.addEventListener("click", () => openModal(img));
});
