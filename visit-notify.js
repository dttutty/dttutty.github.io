(function () {
  "use strict";

  var endpoint = "https://notify.dttutty.com/visit";
  var storageKey = "dttutty-visit-notified-at";
  var cooldownMs = 30 * 60 * 1000;
  var now = Date.now();

  try {
    if (navigator.webdriver || /bot|crawler|spider|headless/i.test(navigator.userAgent)) {
      return;
    }

    var lastNotification = Number(window.localStorage.getItem(storageKey) || 0);
    if (now - lastNotification < cooldownMs) {
      return;
    }

    var referrer = "direct";
    if (document.referrer) {
      try {
        referrer = new URL(document.referrer).hostname || "direct";
      } catch (error) {
        referrer = "unknown";
      }
    }

    window.localStorage.setItem(storageKey, String(now));
    window.fetch(endpoint, {
      method: "POST",
      mode: "cors",
      credentials: "omit",
      keepalive: true,
      headers: { "Content-Type": "text/plain;charset=UTF-8" },
      body: JSON.stringify({
        path: window.location.pathname,
        referrer: referrer
      })
    }).catch(function () {
      window.localStorage.removeItem(storageKey);
    });
  } catch (error) {
    // Notifications are optional and must never interfere with page rendering.
  }
}());
