/* Burnt Neon Productions: scroll waveform, audio players, video cards.
   No libraries, no tracking, nothing stored on the visitor's device. */
(function () {
  'use strict';
  document.documentElement.classList.add('js');

  var PLAY = '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
  var PAUSE = '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg>';
  var calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var stoppers = [];                       // one "stop" function per player, so only one plays at a time

  function fmt(t) {
    t = Math.max(0, Math.floor(t || 0));
    return Math.floor(t / 60) + ':' + ('0' + (t % 60)).slice(-2);
  }
  function stopOthers(me) {
    stoppers.forEach(function (stop) { if (stop !== me) stop(); });
  }
  function each(sel, fn) {
    Array.prototype.forEach.call(document.querySelectorAll(sel), fn);
  }

  /* 1. The waveform under the menu fills from the left as the page scrolls. */
  var wave = document.querySelector('.wave');
  if (wave) {
    var ticking = false;
    var paintWave = function () {
      ticking = false;
      var max = document.documentElement.scrollHeight - window.innerHeight;
      var p = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;
      wave.style.setProperty('--p', (p * 100).toFixed(2) + '%');
    };
    var queue = function () { if (!ticking) { ticking = true; requestAnimationFrame(paintWave); } };
    window.addEventListener('scroll', queue, { passive: true });
    window.addEventListener('resize', queue);
    paintWave();
  }

  /* 2. Sections fade up as they arrive. */
  if (!calm && 'IntersectionObserver' in window) {
    var seen = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); seen.unobserve(en.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px' });
    each('.band > .wrap', function (el) { el.classList.add('reveal'); seen.observe(el); });
  }
  /* The dot texture ripples once when a dotted section comes into view.
     Only the first two dotted sections on a page do this (the banner and the next one);
     any after that keep the still texture. */
  if (!calm && 'IntersectionObserver' in window) {
    var pulse = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('pulse'); pulse.unobserve(en.target); }
      });
    }, { rootMargin: '0px 0px -35% 0px' });   /* fires once the section's top is about a third of the way up the screen, however tall the section is */
    Array.prototype.slice.call(document.querySelectorAll('.hero, .band-dots'), 0, 2)
      .forEach(function (el) { pulse.observe(el); });
  }
  /* Background video: a visible pause button, and it starts paused for visitors who ask for less motion. */
  each('.hero-pause', function (b) {
    var v = b.parentNode.querySelector('video.hero-bg');
    function set(paused) {
      if (paused) v.pause(); else v.play();
      b.setAttribute('aria-pressed', String(paused));
      b.textContent = paused ? 'Play background video' : 'Pause background video';
    }
    if (calm) { v.removeAttribute('autoplay'); set(true); }
    b.addEventListener('click', function () { set(!v.paused); });
  });

  /* Keep in-page links from landing under the sticky header, whatever its height. */
  var header = document.querySelector('.site-header');
  if (header) {
    var setH = function () { document.documentElement.style.setProperty('--header-h', header.offsetHeight + 'px'); };
    setH();
    if ('ResizeObserver' in window) new ResizeObserver(setH).observe(header); else window.addEventListener('resize', setH);
  }

  /* 3. Single audio samples: <div class="player" data-src="..."> and the Home tile buttons. */
  function simplePlayer(button, src, name, timeEl, seek) {
    var audio = null, seeking = false;
    function paint() {
      var on = audio && !audio.paused;
      button.innerHTML = on ? PAUSE : PLAY;
      button.setAttribute('aria-label', (on ? 'Pause ' : 'Play ') + name);
      if (timeEl && audio) timeEl.textContent = fmt(audio.currentTime) + (audio.duration ? ' / ' + fmt(audio.duration) : '');
      if (seek && audio && audio.duration && !seeking) {
        seek.value = Math.round(audio.currentTime / audio.duration * 1000);
        seek.setAttribute('aria-valuetext', fmt(audio.currentTime) + ' of ' + fmt(audio.duration));
      }
    }
    function stop() { if (audio && !audio.paused) audio.pause(); }
    function ready() {
      if (audio) return;
      audio = new Audio(src);
      audio.preload = 'auto';
      ['play', 'pause', 'timeupdate', 'loadedmetadata', 'ended'].forEach(function (ev) { audio.addEventListener(ev, paint); });
    }
    stoppers.push(stop);
    button.addEventListener('click', function () {
      ready();
      if (audio.paused) { stopOthers(stop); audio.play(); } else { audio.pause(); }
    });
    if (seek) {
      seek.addEventListener('input', function () { seeking = true; });
      seek.addEventListener('change', function () {
        ready(); seeking = false;
        var go = function () { audio.currentTime = seek.value / 1000 * audio.duration; };
        if (audio.duration) go(); else audio.addEventListener('loadedmetadata', go, { once: true });
      });
    }
  }
  each('.player[data-src]', function (el) {
    var src = el.getAttribute('data-src');
    if (src) simplePlayer(el.querySelector('.play'), src, el.getAttribute('data-label'), el.querySelector('.player-time'), el.querySelector('.player-seek'));
  });
  each('.tile-play[data-src]', function (b) { simplePlayer(b, b.getAttribute('data-src'), b.getAttribute('data-label')); });

  /* 4. Before/after samples. Both files play in step; the switch crossfades between them. */
  var ctx = null;
  function getCtx() {
    if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
    if (ctx.state === 'suspended') ctx.resume();
    return ctx;
  }
  function loadBuffer(c, url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error('load');
      return r.arrayBuffer();
    }).then(function (data) {
      return new Promise(function (ok, fail) { c.decodeAudioData(data, ok, fail); });
    });
  }
  each('.ab[data-before]', function (el) {
    var urls = { before: el.getAttribute('data-before'), after: el.getAttribute('data-after') };
    var playBtn = el.querySelector('.play'), seek = el.querySelector('.ab-seek'), time = el.querySelector('.ab-time');
    var err = el.querySelector('.ab-error'), name = (el.querySelector('.ab-title') || {}).textContent || 'sample';
    var btn = { before: el.querySelector('.ab-before'), after: el.querySelector('.ab-after') };
    var s = { active: 'before', playing: false, buffers: null, loading: null, duration: 0, offset: 0, startedAt: 0, nodes: null, seeking: false, raf: 0, want: null };

    function pos() { return s.playing ? Math.min(s.duration, Math.max(0, ctx.currentTime - s.startedAt)) : s.offset; }
    function paint() {
      btn.before.setAttribute('aria-pressed', String(s.active === 'before'));
      btn.after.setAttribute('aria-pressed', String(s.active === 'after'));
      playBtn.innerHTML = s.playing ? PAUSE : PLAY;
      playBtn.setAttribute('aria-label', (s.playing ? 'Pause ' : 'Play ') + name);
    }
    function paintTime() {
      var t = pos();
      if (!s.seeking) seek.value = s.duration ? Math.round(t / s.duration * 1000) : 0;
      if (s.duration) seek.setAttribute('aria-valuetext', fmt(t) + ' of ' + fmt(s.duration));
      time.textContent = s.duration ? fmt(t) + ' / ' + fmt(s.duration) : (s.loading ? 'Loading' : '0:00');
    }
    function tick() { paintTime(); if (s.playing) s.raf = requestAnimationFrame(tick); }
    function stopNodes() {
      if (!s.nodes) return;
      var n = s.nodes; s.nodes = null;
      ['before', 'after'].forEach(function (k) {
        n[k].src.onended = null;
        try { n[k].src.stop(); } catch (e) { /* already stopped */ }
        n[k].src.disconnect(); n[k].gain.disconnect();
      });
    }
    function startNodes(from) {
      var c = getCtx(), when = c.currentTime + 0.06, n = {};
      ['before', 'after'].forEach(function (k) {
        var src = c.createBufferSource(), gain = c.createGain();
        src.buffer = s.buffers[k];
        gain.gain.value = k === s.active ? 1 : 0;
        src.connect(gain); gain.connect(c.destination);
        n[k] = { src: src, gain: gain };
      });
      n.before.src.onended = function () {
        if (s.nodes !== n) return;
        stopNodes(); s.playing = false; s.offset = 0; cancelAnimationFrame(s.raf); paint(); paintTime();
      };
      n.before.src.start(when, from); n.after.src.start(when, from);
      s.nodes = n; s.startedAt = when - from;
    }
    function pause() {
      s.want = null;
      if (!s.playing) return;
      s.offset = pos(); s.playing = false; stopNodes(); cancelAnimationFrame(s.raf); paint(); paintTime();
    }
    stoppers.push(pause);
    function load() {
      if (s.buffers) return Promise.resolve();
      if (!s.loading) {
        var c = getCtx();
        s.loading = Promise.all([loadBuffer(c, urls.before), loadBuffer(c, urls.after)]).then(function (b) {
          s.buffers = { before: b[0], after: b[1] };
          s.duration = Math.min(b[0].duration, b[1].duration);
        });
        s.loading.catch(function () { s.loading = null; });
        paintTime();
      }
      return s.loading;
    }
    function play() {
      getCtx();
      err.hidden = true;
      stopOthers(pause);
      var want = s.want = {};
      load().then(function () {
        if (s.want !== want || s.playing) return;
        if (s.offset >= s.duration - 0.05) s.offset = 0;
        s.want = null; startNodes(s.offset); s.playing = true; paint(); tick();
      }).catch(function () {
        s.want = null; err.textContent = 'Could not load this sample.'; err.hidden = false; paint(); paintTime();
      });
    }
    function setActive(which) {
      if (s.active === which) return;
      s.active = which;
      if (s.nodes) {
        var t = ctx.currentTime;
        ['before', 'after'].forEach(function (k) {
          var g = s.nodes[k].gain.gain;
          g.cancelScheduledValues(t); g.setValueAtTime(g.value, t);
          g.linearRampToValueAtTime(k === which ? 1 : 0, t + 0.03);
        });
      }
      paint();
    }
    playBtn.addEventListener('click', function () { if (s.playing || s.want) pause(); else play(); });
    btn.before.addEventListener('click', function () { setActive('before'); });
    btn.after.addEventListener('click', function () { setActive('after'); });
    seek.addEventListener('input', function () { s.seeking = true; });
    seek.addEventListener('change', function () {
      var t = seek.value / 1000 * s.duration;
      s.seeking = false;
      if (s.playing) { stopNodes(); startNodes(t); } else { s.offset = t; }
      paintTime();
    });
    paint(); paintTime();
  });

  /* 5. Video cards and film clips: nothing loads from YouTube or Vimeo until the visitor presses play. */
  function embedFor(url) {
    var m = url.match(/(?:youtube\.com\/watch\?(?:.*&)?v=|youtu\.be\/|youtube\.com\/embed\/)([\w-]{6,})/);
    if (m) return 'https://www.youtube-nocookie.com/embed/' + m[1] + '?autoplay=1&rel=0';
    m = url.match(/vimeo\.com\/(?:video\/)?(\d+)/);
    if (m) return 'https://player.vimeo.com/video/' + m[1] + '?autoplay=1';
    return null;
  }
  function showVideo(box, url, title) {
    var src = embedFor(url), node;
    stopOthers(null);
    if (src) {
      node = document.createElement('iframe');
      node.src = src; node.allow = 'autoplay; fullscreen; picture-in-picture'; node.allowFullscreen = true;
      node.title = title || 'Video';
    } else {
      node = document.createElement('video');
      node.src = url; node.controls = true; node.setAttribute('aria-label', title || 'Video'); node.autoplay = true; node.playsInline = true;
    }
    box.classList.add('playing');
    box.appendChild(node);
  }
  each('.reel[data-video]', function (box) {
    var url = box.getAttribute('data-video'), node;
    if (url) box.querySelector('.play').addEventListener('click', function () { showVideo(box, url, box.getAttribute('data-title')); node = box.lastElementChild; if (node) { node.tabIndex = 0; node.focus(); } });
  });
  /* 5b. Touch screens have no hover, so the service card that fills most of the screen lights up instead.
         Only when the cards are stacked in one column; side by side, none is singled out. */
  (function () {
    var cards = Array.prototype.slice.call(document.querySelectorAll('.pack-hover'));
    if (cards.length < 2 || !window.matchMedia('(hover: none)').matches) return;
    var queued = false;
    function pick() {
      queued = false;
      var head = document.querySelector('.site-header');
      var top = head ? Math.max(0, head.getBoundingClientRect().bottom) : 0, bottom = window.innerHeight;
      var stacked = cards[1].getBoundingClientRect().top >= cards[0].getBoundingClientRect().bottom - 1;
      var best = null, most = 0;
      if (stacked) cards.forEach(function (card) {
        var r = card.getBoundingClientRect();
        var seen = Math.min(r.bottom, bottom) - Math.max(r.top, top);
        if (seen > most) { most = seen; best = card; }
      });
      if (best && most < Math.min(best.offsetHeight, bottom - top) * 0.5) best = null;   // at least half in view
      cards.forEach(function (card) { card.classList.toggle('lit', card === best); });
    }
    function ask() { if (!queued) { queued = true; window.requestAnimationFrame(pick); } }
    window.addEventListener('scroll', ask, { passive: true });
    window.addEventListener('resize', ask);
    pick();
  })();

  /* 6. The sound reel: plays in place, one marker per film, optional full screen. */
  each('.rs', function (box) {
    var v = box.querySelector('video'), playBtn = box.querySelector('.rs-play'), full = box.querySelector('.rs-full');
    var time = box.querySelector('.rs-time'), title = box.querySelector('.rs-title'), role = box.querySelector('.rs-role');
    var rail = box.querySelector('.rs-chapters'), err = box.querySelector('.rs-error');
    var segs = Array.prototype.slice.call(box.querySelectorAll('.rs-seg'));
    var starts = segs.map(function (s) { return parseFloat(s.getAttribute('data-start')) || 0; });
    var name = playBtn.getAttribute('aria-label').replace(/^Play /, '');
    v.controls = false;                                   // the page's own controls take over from the browser's
    function dur() { return isFinite(v.duration) ? v.duration : 0; }
    function end(k) { return k + 1 < starts.length ? starts[k + 1] : dur(); }
    function stop() { v.pause(); }
    stoppers.push(stop);
    function layout() {                                   // each marker is as wide as its film's share of the reel
      if (!dur() || segs.length < 2) return;
      rail.style.gridAutoFlow = 'row';
      rail.style.gridTemplateColumns = starts.map(function (s, k) {
        return 'minmax(0, ' + Math.max(end(k) - s, dur() * 0.08).toFixed(2) + 'fr)';
      }).join(' ');
    }
    function paint() {
      var t = v.currentTime || 0, cur = 0, k, len;
      for (k = 0; k < starts.length; k++) if (t >= starts[k]) cur = k;
      for (k = 0; k < segs.length; k++) {
        len = end(k) - starts[k];
        segs[k].style.setProperty('--f', len > 0 ? Math.min(1, Math.max(0, (t - starts[k]) / len)).toFixed(4) : 0);
        segs[k].classList.toggle('on', k === cur && segs.length > 1);
        if (k === cur) segs[k].setAttribute('aria-current', 'true'); else segs[k].removeAttribute('aria-current');
      }
      if (segs[cur].getAttribute('data-title')) {
        title.textContent = segs[cur].getAttribute('data-title');
        role.textContent = segs[cur].getAttribute('data-role') || '';
      }
      time.textContent = dur() ? fmt(t) + ' / ' + fmt(dur()) : fmt(t);
    }
    function toggle() {
      if (v.paused) { stopOthers(stop); v.play(); } else v.pause();
    }
    function inFull() { return (document.fullscreenElement || document.webkitFullscreenElement) === box; }
    function toggleFull() {
      if (inFull()) (document.exitFullscreen || document.webkitExitFullscreen).call(document);
      else if (box.requestFullscreen) box.requestFullscreen();
      else if (box.webkitRequestFullscreen) box.webkitRequestFullscreen();
      else if (v.webkitEnterFullscreen) v.webkitEnterFullscreen();      // iPhone: only the video itself can go full screen
    }
    function fullChanged() {
      full.setAttribute('aria-pressed', inFull() ? 'true' : 'false');
      full.setAttribute('aria-label', inFull() ? 'Leave full screen' : 'Full screen');
    }
    playBtn.addEventListener('click', toggle);
    v.addEventListener('click', toggle);
    full.addEventListener('click', toggleFull);
    document.addEventListener('fullscreenchange', fullChanged);
    document.addEventListener('webkitfullscreenchange', fullChanged);
    v.addEventListener('play', function () {
      box.classList.add('started'); box.classList.add('playing');
      playBtn.innerHTML = PAUSE; playBtn.setAttribute('aria-label', 'Pause ' + name);
    });
    v.addEventListener('pause', function () {
      box.classList.remove('playing');
      playBtn.innerHTML = PLAY; playBtn.setAttribute('aria-label', 'Play ' + name);
    });
    v.addEventListener('loadedmetadata', function () { layout(); paint(); });
    v.addEventListener('durationchange', function () { layout(); paint(); });
    v.addEventListener('timeupdate', paint);
    v.addEventListener('seeked', paint);
    v.addEventListener('error', function () { err.hidden = false; });
    segs.forEach(function (seg, k) {
      seg.addEventListener('click', function (ev) {
        var box2 = seg.getBoundingClientRect(), to = starts[k];
        if (segs.length < 2 && dur() && ev.clientX) to = dur() * Math.min(1, Math.max(0, (ev.clientX - box2.left) / box2.width));
        v.currentTime = to;
        if (v.paused) { stopOthers(stop); v.play(); }
        paint();
      });
    });
    box.addEventListener('keydown', function (ev) {
      if (ev.key === 'ArrowRight' || ev.key === 'ArrowLeft') {
        v.currentTime = Math.min(dur() || 0, Math.max(0, v.currentTime + (ev.key === 'ArrowRight' ? 5 : -5)));
        ev.preventDefault();
      } else if (ev.key === 'f' || ev.key === 'F') toggleFull();
    });
    if (v.readyState >= 1) layout();
    paint();
  });
  // Film strip: when it is narrow enough to scroll sideways, show which frame is centred
  // and let the keyboard reach it (a scrolling area has to be focusable).
  each('.filmstrip', function (strip) {
    var frames = strip.querySelectorAll('.frame'), dots = [], i;
    var holder = strip.parentNode.querySelector('.film-dots');
    if (holder) for (i = 0; i < frames.length; i++) dots.push(holder.appendChild(document.createElement('i')));
    function mark() {
      var room = strip.scrollWidth - strip.clientWidth;
      var best = room > 0 ? Math.round(strip.scrollLeft / room * (frames.length - 1)) : 0;
      for (var k = 0; k < dots.length; k++) dots[k].classList.toggle('on', k === best);
    }
    function fit() {
      if (strip.scrollWidth > strip.clientWidth + 1) strip.tabIndex = 0; else strip.removeAttribute('tabindex');
      mark();
    }
    strip.addEventListener('scroll', mark, { passive: true });
    window.addEventListener('resize', fit);
    fit();
  });
  each('.poster-play[data-video]', function (b) {
    b.addEventListener('click', function () {
      window.open(b.getAttribute('data-video'), '_blank', 'noopener');
    });
  });
})();
