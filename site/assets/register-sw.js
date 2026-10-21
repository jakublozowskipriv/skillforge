// Register the offline service worker generated at build time (site root /sw.js).
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    const root = document.querySelector('link[rel="manifest"]')?.href.replace(/manifest\.webmanifest$/, "") ?? "./";
    navigator.serviceWorker.register(root + "sw.js", { scope: root }).catch(() => {});
  });
}
