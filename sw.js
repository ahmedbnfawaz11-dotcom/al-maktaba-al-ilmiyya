const CACHE_NAME = "ilm-library-v14";
const APP_FILES = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icon.svg",
  "./texts/kitab-al-tawhid.md",
  "./texts/kashf-al-shubuhat.md",
  "./texts/usul-al-iman.md",
  "./texts/masail-al-jahiliyyah.md",
  "./texts/mufid-al-mustafid.md",
  "./texts/adab-al-mashy.md",
  "./texts/arba-qawaid.md",
  "./texts/radd-al-rawafid.md",
  "./texts/mabahith-al-ijtihad.md",
  "./texts/mukhtasar-sirat-al-rasul.md",
  "./texts/aqidat-al-firqa-al-najiya.md",
  "./texts/kitab-al-kabair.md",
  "./texts/shurut-al-salah.md",
  "./texts/kitab-al-taharah-shamela.md",
  "./texts/majmuat-rasail-tawhid-iman.md",
  "./texts/al-rasail-al-shakhsiyya.md",
  "./texts/ahkam-tamanni-al-mawt.md",
  "./texts/fatawa-wa-masail.md",
  "./texts/khutab-minbariyya.md",
  "./texts/fawaid-hudaybiyya.md",
  "./texts/tafsir-ayat-min-al-quran.md",
  "./texts/mukhtasar-tafsir-al-anfal.md",
  "./texts/fadael-al-quran.md",
  "./texts/fadl-al-islam.md",
  "./texts/usul-thalatha.md",
  "./texts/al-qawaid-al-arba.md",
  "./texts/nawaqid-al-islam.md",
  "./texts/al-usul-al-sittah.md",
  "./texts/mukhtasar-zad-al-maad.md",
  "./texts/mukhtasar-al-insaf.md",
  "./texts/kitab-al-tawhid-guide.md",
  "./texts/masail-al-jahiliyyah-guide.md",
  "./texts/adab-al-mashy-guide.md",
  "./texts/usul-al-iman-guide.md",
  "./texts/mukhtasar-sirat-guide.md"
];
self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => Promise.allSettled(APP_FILES.map(file => cache.add(file)))));
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
