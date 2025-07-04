window.addEventListener("load", function () {
  setTimeout(() => {
    const loader = document.getElementById("loader-wrapper");
    if (loader) loader.style.display = "none";
  }, 2000);
});

// Caterpillar motion using GSAP
const caterpillar = gsap.timeline({ repeat: -1 });

for (let i = 1; i <= 4; i++) {
  caterpillar.to(`.shape-${i}`, {
    y: -12,
    x: i % 2 === 0 ? 4 : -4,  // slight zigzag forward
    scale: 1.4,
    duration: 0.3,
    ease: "power1.inOut",
    yoyo: true,
    repeat: 1
  }, i * 0.05);
}
