// Pages "advanced mode" worker: this file takes over routing for the whole
// project, so it must forward everything it does not handle itself to the
// static assets (env.ASSETS), or nothing gets served.
//
// Its only job is to send the project's canonical pages.dev URL to the real
// domain, so the site has one address rather than two indexed copies. The
// _redirects file cannot do this - Pages does not support domain-level
// redirects there - which is why it takes a worker.
//
// The match is exact on purpose. Per-deployment preview URLs look like
// <hash>.astroplanner.pages.dev and are how a build gets checked before it is
// promoted, so those must keep serving the site rather than bouncing to
// production.
const PAGES_HOST = "astroplanner.pages.dev";
const SITE_HOST = "astroplanner.ambroslabs.io";

// The catalogue files carry a hash of their own contents in the name, so a
// given URL's bytes can never change: rebuilding a catalogue produces a new
// filename, and the old one simply stops being asked for. That is what makes
// `immutable` safe here - the browser is told never to revalidate, and there is
// no stale version to be stuck with. It matters because these are the large
// files (NGC is 74 KB gzipped) and they should be fetched once per reader, not
// once per visit.
//
// This has to happen in the worker. Pages ignores the _headers file for
// anything served through an advanced-mode _worker.js, so a _headers rule would
// look correct in the repository and do nothing at all.
const HASHED = /^\/(?:beta\/)?assets\/catalogs\/[a-z0-9]+\.[0-9a-f]{12}\.txt$/;
const IMMUTABLE = "public, max-age=31536000, immutable";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.hostname === PAGES_HOST) {
      url.hostname = SITE_HOST;
      return Response.redirect(url.toString(), 301);
    }
    const response = await env.ASSETS.fetch(request);
    // /beta is a copy of the site for trying things on, and there is no reason
    // for a search engine to carry a second, deliberately unstable version of
    // every page.
    if (url.pathname === "/beta" || url.pathname.startsWith("/beta/")) {
      const headers = new Headers(response.headers);
      headers.set("X-Robots-Tag", "noindex, nofollow");
      if (HASHED.test(url.pathname) && response.ok) headers.set("Cache-Control", IMMUTABLE);
      return new Response(response.body, {
        status: response.status, statusText: response.statusText, headers,
      });
    }
    if (HASHED.test(url.pathname) && response.ok) {
      // The body has to be re-wrapped: an ASSETS response's headers are frozen.
      const headers = new Headers(response.headers);
      headers.set("Cache-Control", IMMUTABLE);
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers,
      });
    }
    return response;
  },
};
