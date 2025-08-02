function updateWIBTime() {
  const now = new Date();

  // Ubah ke UTC, lalu tambah 7 jam untuk WIB (UTC+7)
  const utc = now.getTime() + now.getTimezoneOffset() * 60000;
  const wib = new Date(utc + 7 * 60 * 60000);

  // Format tanggal tanpa nama hari
  const optionsTanggal = {
    year: "numeric",
    month: "long",
    day: "numeric",
  };
  const tanggal = wib.toLocaleDateString("id-ID", optionsTanggal);

  // Format waktu tanpa detik
  const jam = wib.getHours().toString().padStart(2, "0");
  const menit = wib.getMinutes().toString().padStart(2, "0");

  document.getElementById("date").textContent = tanggal;
  document.getElementById("clock").textContent = `${jam}:${menit} WIB`;
}

setInterval(updateWIBTime, 1000); // Update tiap detik
updateWIBTime(); // Panggil pertama kali

