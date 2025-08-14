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

  if (current === "hal1") title.textContent = "HOME";
  if (current === "hal2") title.textContent = "PREFERENCE";
  if (current === "hal3") title.textContent = "PORTFOLIO";
  if (current === "hal4") title.textContent = "COMMENT";
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

