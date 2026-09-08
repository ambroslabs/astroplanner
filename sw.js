// Offline. The planner is for standing in a field at night, which is where
// there is least likely to be a signal, so the whole thing is kept on the
// device: the page, the code, the fonts, and every catalogue - twenty-seven
// files, 1.9 MB, 0.76 MB over the wire. Nothing here talks to anything else;
// the app has no server side and never did.
//
// BUILD_STAMP is rewritten at build time. It names the cache, so a deployment
// gets a fresh one and the old one is deleted on activation.
const VERSION = 'BUILD_STAMP';
const CACHE = 'astroplanner-' + VERSION;
// Rewritten at build time from what is actually in dist/, so the list cannot
// drift away from the deployment: a catalogue whose contents change gets a new
// hashed filename, and a list written by hand would still be asking for the
// old one.
const ASSETS = [/*BUILD_ASSETS*/];

self.addEventListener('install', e => {
  // Every file, up front. The catalogues are fetched lazily by the page - it
  // does not read the NGC file until someone asks for NGC - and that is the
  // right behaviour online and useless offline, where the moment of asking is
  // the moment there is no network. So installation takes them all.
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== CACHE) await caches.delete(k);
    await self.clients.claim();
  })());
});

self.addEventListener('message', e => { if (e.data === 'skipWaiting') self.skipWaiting(); });

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  // The page itself: network first, so a visit with a signal always gets the
  // current one, and the cache is the fallback rather than the default. A
  // service worker that serves the page from cache first will happily show
  // someone a version from six months ago and give them no way to know.
  //
  // Only the root document is the app. This worker's scope is the whole origin,
  // which means it also sees /beta - a second, deliberately unstable copy of
  // the site - and neither storing that under '/' nor answering a request for
  // it with the production page would be honest. Both were possible until this
  // said so: offline, /beta would have quietly shown production.
  if (req.mode === 'navigate') {
    const isApp = url.pathname === '/';
    e.respondWith((async () => {
      try {
        const net = await fetch(req);
        if (isApp && net && net.ok) (await caches.open(CACHE)).put('/', net.clone());
        return net;
      } catch (err) {
        return (await caches.match(req, { ignoreSearch: true })) || Response.error();
      }
    })());
    return;
  }

  // Everything else is content-addressed - the filename carries a hash of the
  // bytes - so a hit can be served from the cache without a thought, and a
  // miss is a file this version did not know about.
  //
  // A miss is passed through and not stored. Storing it would be the obvious
  // thing and it is a trap: Pages answers a path it does not have with the
  // page itself and a 200, so a miss for a file this version never had would
  // put an HTML document in the cache under an asset's URL. The precache list
  // is generated from the deployment, so there is nothing legitimate to miss.
  e.respondWith(caches.match(req, { ignoreSearch: true }).then(hit => hit || fetch(req)));
});
