// Script untuk update judul header sesuai halaman yang terlihat
const sections = document.querySelectorAll(".page");
const title = document.getElementById("page-title");

window.addEventListener("scroll", () => {
  let current = "";
  sections.forEach((section) => {
    const sectionTop = section.offsetTop - 100;
    if (pageYOffset >= sectionTop) {
      current = section.getAttribute("id");
    }
  });

  if (current === "hal1") title.textContent = "DASHBOARD";
  if (current === "hal2") title.textContent = "PREFERENCE";
  if (current === "hal3") title.textContent = "PORTFOLIO";
  if (current === "hal4") title.textContent = "COMMENT";
});

const menuLinks = document.querySelectorAll(".menu ul li a");

window.addEventListener("scroll", () => {
  let current = "";
  sections.forEach((section) => {
    const sectionTop = section.offsetTop - 100;
    if (pageYOffset >= sectionTop) {
      current = section.getAttribute("id");
    }
  });

  // Update title header
  if (current === "hal1") title.textContent = "DASHBOARD";
  if (current === "hal2") title.textContent = "PREFERENCE";
  if (current === "hal3") title.textContent = "PORTFOLIO";
  if (current === "hal4") title.textContent = "COMMENT";

  // Update active menu
  menuLinks.forEach((link) => {
    link.classList.remove("active");
    if (link.getAttribute("href") === "#" + current) {
      link.classList.add("active");
    }
  });
});

function updateDateTime() {
  const now = new Date();

  const monthNames = [
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"
  ];

  const day = String(now.getDate()).padStart(2, '0');
  const month = monthNames[now.getMonth()];
  const year = now.getFullYear();

  const time = now.toLocaleTimeString("id-ID", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  });

  document.getElementById("datetime-container").textContent =
    `${day} ${month} ${year}, ${time} WIB`;
}

setInterval(updateDateTime, 1000);
updateDateTime();


document.getElementById("search-btn").addEventListener("click", function () {
  const input = document.getElementById("search-input");
  input.classList.toggle("show");
  if (input.classList.contains("show")) {
    input.focus(); // otomatis fokus kalau muncul
  }
});

let currentSection = 0;
let scrollCount = 0;
const sectionsArr = Array.from(sections);

window.addEventListener("wheel", function(e) {
  // Cegah scroll default hanya jika di dalam main content
  if (document.activeElement === document.body) {
    e.preventDefault();

    // Scroll ke bawah
    if (e.deltaY > 0) {
      scrollCount++;
      if (scrollCount >= 2 && currentSection < sectionsArr.length - 1) {
        currentSection++;
        sectionsArr[currentSection].scrollIntoView({ behavior: "smooth" });
        scrollCount = 0;
      }
    }
    // Scroll ke atas
    if (e.deltaY < 0) {
      scrollCount++;
      if (scrollCount >= 2 && currentSection > 0) {
        currentSection--;
        sectionsArr[currentSection].scrollIntoView({ behavior: "smooth" });
        scrollCount = 0;
      }
    }
  }
}, { passive: false });

// Tempatkan di file JS utama, atau di <script> sebelum </body>
const canvas = document.getElementById('molecule-bg');
const ctx = canvas.getContext('2d');
let particles = [];

function resizeCanvas() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

function createParticles(num) {
  particles = [];
  for (let i = 0; i < num; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: 2 + Math.random() * 2,
      dx: (Math.random() - 0.5) * 0.7,
      dy: (Math.random() - 0.5) * 0.7,
    });
  }
}
createParticles(60);

function animate() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  for (let p of particles) {
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    ctx.fillStyle = '#d9d9d9';
    ctx.fill();
    // Gerakkan partikel
    p.x += p.dx;
    p.y += p.dy;
    // Pantulkan jika kena tepi
    if (p.x < 0 || p.x > canvas.width) p.dx *= -1;
    if (p.y < 0 || p.y > canvas.height) p.dy *= -1;
  }
  requestAnimationFrame(animate);
}
animate();

