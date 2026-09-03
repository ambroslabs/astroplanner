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

export default {
  fetch(request, env) {
    const url = new URL(request.url);
    if (url.hostname === PAGES_HOST) {
      url.hostname = SITE_HOST;
      return Response.redirect(url.toString(), 301);
    }
    return env.ASSETS.fetch(request);
  },
};
