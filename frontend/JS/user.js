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

  if (current === "hal1") title.textContent = "Halaman 1";
  if (current === "hal2") title.textContent = "Halaman 2";
  if (current === "hal3") title.textContent = "Halaman 3";
  if (current === "hal4") title.textContent = "Halaman 4";
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

