'use strict';

// Helper function to toggle "active" class
const elementToggleFunc = function (elem) {
  elem.classList.toggle("active");
};

// ===============================
// Sidebar (for mobile)
// ===============================
const sidebar = document.querySelector("[data-sidebar]");
const sidebarBtn = document.querySelector("[data-sidebar-btn]");

if (sidebar && sidebarBtn) {
  sidebarBtn.addEventListener("click", function () {
    elementToggleFunc(sidebar);
  });
}

// ===============================
// Testimonials Modal
// ===============================
const testimonialsItem = document.querySelectorAll("[data-testimonials-item]");
const modalContainer = document.querySelector("[data-modal-container]");
const modalCloseBtn = document.querySelector("[data-modal-close-btn]");
const overlay = document.querySelector("[data-overlay]");
const modalImg = document.querySelector("[data-modal-img]");
const modalTitle = document.querySelector("[data-modal-title]");
const modalText = document.querySelector("[data-modal-text]");

const testimonialsModalFunc = function () {
  modalContainer.classList.toggle("active");
  overlay.classList.toggle("active");
};

if (testimonialsItem.length > 0 && modalContainer && modalCloseBtn && overlay) {
  for (let i = 0; i < testimonialsItem.length; i++) {
    testimonialsItem[i].addEventListener("click", function () {
      modalImg.src = this.querySelector("[data-testimonials-avatar]").src;
      modalImg.alt = this.querySelector("[data-testimonials-avatar]").alt;
      modalTitle.innerHTML = this.querySelector("[data-testimonials-title]").innerHTML;
      modalText.innerHTML = this.querySelector("[data-testimonials-text]").innerHTML;
      testimonialsModalFunc();
    });
  }

  modalCloseBtn.addEventListener("click", testimonialsModalFunc);
  overlay.addEventListener("click", testimonialsModalFunc);
}

// ===============================
// Project Filtering System
// ===============================
const select = document.querySelector("[data-select]");
const selectItems = document.querySelectorAll("[data-select-item]");
const selectValue = document.querySelector("[data-select-value]");
const filterBtn = document.querySelectorAll("[data-filter-btn]");
const filterItems = document.querySelectorAll("[data-filter-item]");

// Main filter function
const filterFunc = function (selectedValue) {
  selectedValue = selectedValue.toLowerCase(); // Ensure selected value is lowercase

  console.log("Filtering by category:", selectedValue); // Debugging line

  filterItems.forEach(item => {
    const category = item.dataset.category.toLowerCase(); // Ensure project category is lowercase
    console.log("Project category:", category); // Debugging line

    if (selectedValue === "all" || category === selectedValue) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });
};

// Mobile dropdown functionality
if (select && selectItems.length > 0 && selectValue) {
  select.addEventListener("click", function () {
    elementToggleFunc(this);
  });

  for (let i = 0; i < selectItems.length; i++) {
    selectItems[i].addEventListener("click", function () {
      const selectedValue = this.innerText.toLowerCase();
      selectValue.innerText = this.innerText;
      elementToggleFunc(select); // close dropdown
      filterFunc(selectedValue);

      // Update desktop button UI to match
      filterBtn.forEach(btn => {
        btn.classList.toggle("active", btn.innerText.toLowerCase() === selectedValue);
      });
    });
  }
}

// Desktop button filtering
if (filterBtn.length > 0) {
  let lastClickedBtn = filterBtn[0];
  
  for (let i = 0; i < filterBtn.length; i++) {
    filterBtn[i].addEventListener("click", function () {
      const selectedValue = this.innerText.toLowerCase();
      
      // Update mobile dropdown to match
      if (selectValue) {
        selectValue.innerText = this.innerText;
      }
      
      filterFunc(selectedValue);

      // Update button states
      lastClickedBtn.classList.remove("active");
      this.classList.add("active");
      lastClickedBtn = this;
    });
  }
}

// ===============================
// Contact Form Validation
// ===============================
const form = document.querySelector("[data-form]");
const formInputs = document.querySelectorAll("[data-form-input]");
const formBtn = document.querySelector("[data-form-btn]");

if (form && formInputs.length > 0 && formBtn) {
  for (let i = 0; i < formInputs.length; i++) {
    formInputs[i].addEventListener("input", function () {
      formBtn.disabled = !form.checkValidity();
    });
  }
}

// ===============================
// Image Modal (Profile Zoom)
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
  if (modal) {
    modal.style.display = "none";
  }
}

window.onclick = function (event) {
  const modal = document.getElementById("myModal");
  if (event.target === modal) closeModal();
};

window.onkeydown = function (event) {
  if (event.key === "Escape") closeModal();
};

// Add click listeners to images with data-src attribute
document.querySelectorAll("[data-src]").forEach(img => {
  img.addEventListener("click", () => openModal(img));
});

// ===============================
// Initialize filters on page load
// ===============================
document.addEventListener('DOMContentLoaded', function() {
  // Show all projects initially
  filterFunc('all');
});