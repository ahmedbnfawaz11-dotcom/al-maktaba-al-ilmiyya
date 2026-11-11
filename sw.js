const CACHE_NAME = "ilm-library-v6";
const APP_FILES = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icon.svg",
  "./texts/kitab-al-tawhid.md",
  "./texts/kashf-al-shubuhat.md",
  "./texts/usul-al-iman.md",
  "./texts/masail-al-jahiliyyah.md",
  "./texts/fadl-al-islam.md",
  "./texts/usul-thalatha.md",
  "./texts/al-qawaid-al-arba.md",
  "./texts/nawaqid-al-islam.md",
  "./texts/kitab-al-tawhid-guide.md",
  "./texts/masail-al-jahiliyyah-guide.md",
  "./texts/adab-al-mashy-guide.md",
  "./texts/usul-al-iman-guide.md",
  "./texts/mukhtasar-sirat-guide.md"
];
self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(APP_FILES)));
  self.skipWaiting();
});
self.addEventListener("activate", event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))));
  self.clients.claim();
});
self.addEventListener("fetch", event => {
  if (event.request.method !== "GET") return;
  event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request).then(response => {
    if (response && response.ok) {
      const copy = response.clone();
      caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
    }
    return response;
  }).catch(() => caches.match("./index.html"))));
});
