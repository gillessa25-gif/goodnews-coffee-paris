/* Good News Coffee Shop — scroll parallax, reveals, opening status. */
(function () {
  'use strict';

  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)');

  /* ---- transform-based parallax, 3 layered depths ---- */
  var layers = Array.prototype.slice.call(document.querySelectorAll('[data-depth]'));
  var ticking = false;

  function place() {
    ticking = false;
    var viewport = window.innerHeight;
    for (var i = 0; i < layers.length; i++) {
      var el = layers[i];
      var host = el.closest('section, header') || el;
      var box = host.getBoundingClientRect();
      if (box.bottom < -viewport * 0.5 || box.top > viewport * 1.5) continue;
      var progress = (box.top + box.height / 2 - viewport / 2) / viewport;
      var shift = progress * parseFloat(el.dataset.depth) * viewport * -0.5;
      el.style.transform = 'translate3d(0,' + shift.toFixed(2) + 'px,0)';
    }
  }

  function onScroll() {
    if (!ticking) {
      ticking = true;
      window.requestAnimationFrame(place);
    }
  }

  function startParallax() {
    if (reduced.matches) {
      layers.forEach(function (el) { el.style.transform = ''; });
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      return;
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    place();
  }

  /* ---- scroll reveals ---- */
  function startReveals() {
    var items = document.querySelectorAll('.reveal');
    if (reduced.matches || !('IntersectionObserver' in window)) {
      Array.prototype.forEach.call(items, function (el) { el.classList.add('is-in'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.style.transitionDelay =
          (Array.prototype.indexOf.call(entry.target.parentNode.children, entry.target) % 3) * 90 + 'ms';
        entry.target.classList.add('is-in');
        io.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -12% 0px', threshold: 0.12 });
    Array.prototype.forEach.call(items, function (el) { io.observe(el); });
  }

  /* ---- hero film: honour reduced motion, recover from autoplay blocks ---- */
  function startVideo() {
    var video = document.getElementById('heroVideo');
    if (!video) return;
    if (reduced.matches) {
      video.removeAttribute('autoplay');
      video.pause();
      return;
    }
    var attempt = video.play();
    if (attempt && typeof attempt.catch === 'function') {
      attempt.catch(function () {
        var resume = function () {
          video.play().catch(function () {});
          document.removeEventListener('touchstart', resume);
          document.removeEventListener('click', resume);
        };
        document.addEventListener('touchstart', resume, { once: true, passive: true });
        document.addEventListener('click', resume, { once: true });
      });
    }
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) video.pause();
      else if (!reduced.matches) video.play().catch(function () {});
    });
  }

  /* ---- today's row + open/closed badge, in Paris time ---- */
  var SCHEDULE = {
    0: [570, 1020], 1: [495, 1020], 2: [495, 1020], 3: [495, 1020],
    4: [495, 1020], 5: [495, 1020], 6: [570, 1020]
  };

  function parisNow() {
    try {
      var parts = new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Europe/Paris', weekday: 'short', hour: '2-digit',
        minute: '2-digit', hour12: false
      }).formatToParts(new Date());
      var map = {};
      parts.forEach(function (p) { map[p.type] = p.value; });
      var days = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
      return { day: days[map.weekday], minutes: (+map.hour) * 60 + (+map.minute) };
    } catch (error) {
      var now = new Date();
      return { day: now.getDay(), minutes: now.getHours() * 60 + now.getMinutes() };
    }
  }

  function startStatus() {
    var badge = document.getElementById('status');
    if (!badge) return;
    var now = parisNow();
    var row = document.querySelector('.hours tr[data-day="' + now.day + '"]');
    if (row) row.setAttribute('data-today', '');

    var window_ = SCHEDULE[now.day];
    var open = now.minutes >= window_[0] && now.minutes < window_[1];
    badge.hidden = false;
    badge.setAttribute('data-open', String(open));
    badge.textContent = open ? 'Ouvert maintenant · ferme à 17 h' : 'Fermé actuellement';
  }

  function boot() {
    startParallax();
    startReveals();
    startVideo();
    startStatus();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  if (reduced.addEventListener) {
    reduced.addEventListener('change', function () { startParallax(); startVideo(); });
  }
})();
