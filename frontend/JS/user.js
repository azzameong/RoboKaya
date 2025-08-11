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

  if (current === "hal1") title.textContent = "ABOUT";
  if (current === "hal2") title.textContent = "PREFERENCE";
  if (current === "hal3") title.textContent = "PORTFOLIO";
  if (current === "hal4") title.textContent = "COMMENT";
});

function updateDateTime() {
  const now = new Date();

  // Format jam:menit
  const time = now.toLocaleTimeString("id-ID", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false
  });

  // Format tanggal dd/mm/yyyy
  const day = String(now.getDate()).padStart(2, '0');
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const year = now.getFullYear();
  const date = `${day}/${month}/${year}`;

  // Gabung jadi satu baris
  document.getElementById("time").textContent = `${time} WIB`;
  document.getElementById("date").textContent = date;
}
setInterval(updateDateTime, 1000);
updateDateTime();

