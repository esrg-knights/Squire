self.addEventListener("install", e => {
    self.skipWaiting()
});


self.addEventListener("activate", e => {
    self.clients.claim();
});

self.addEventListener("fetch", function (e)
{
    e.respondWith(
        (async () => {
                // Always try the network first. No caching is implemented for now.
                const networkResponse = await fetch(e.request);
                return networkResponse;
        })()
    );
});