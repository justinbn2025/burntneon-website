/* Burnt Neon Productions: scroll waveform, audio players, the sound reel.
   No libraries, no tracking, and nothing kept on the visitor's device after the visit:
   the volume setting is remembered only until the tab is closed. */
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

  /* Volume. One setting for every player on the site, remembered for the visit (sessionStorage).
     Sound goes through one output stage, so the Music page's master fader can set its level and
     meter it. Phones and tablets are left alone: their own volume buttons are the control. */
  var touch = window.matchMedia('(hover: none) and (pointer: coarse)').matches;
  var AC = window.AudioContext || window.webkitAudioContext;
  var vol = 0.75, lastVol = 0.75, volWatch = [], meterKick = function () {};
  var ctx = null, out = null, taps = null;
  if (!touch) {
    try {
      var saved = window.sessionStorage.getItem('bn-volume');
      if (saved !== null && saved !== '' && isFinite(saved)) vol = Math.min(1, Math.max(0, Number(saved)));
      var before = Number(window.sessionStorage.getItem('bn-volume-before'));
      lastVol = vol > 0 ? vol : (before > 0 && before <= 1 ? before : 0.75);     // what "unmute" goes back to
    } catch (e) { /* storage switched off: the setting just lasts for this page */ }
  } else { vol = 1; }
  function loud() { return vol * vol; }                  // the ear hears level roughly this way
  function getCtx() {
    if (!ctx) {
      ctx = new AC();
      out = ctx.createGain();
      out.channelCount = 2; out.channelCountMode = 'explicit';      // mono samples light both meters
      out.gain.value = loud();
      out.connect(ctx.destination);
      try {
        var split = ctx.createChannelSplitter(2);
        taps = [ctx.createAnalyser(), ctx.createAnalyser()];
        out.connect(split);
        taps.forEach(function (a, i) { a.fftSize = 1024; split.connect(a, i); });
      } catch (e) { taps = null; }
    }
    if (ctx.state === 'suspended') ctx.resume();
    meterKick();
    return ctx;
  }
  function setVol(v) {
    v = Math.min(1, Math.max(0, v));
    if (v > 0) lastVol = v;
    vol = v;
    try { window.sessionStorage.setItem('bn-volume', String(v)); window.sessionStorage.setItem('bn-volume-before', String(lastVol)); } catch (e) { /* see above */ }
    if (out) out.gain.setTargetAtTime(loud(), ctx.currentTime, 0.015);
    volWatch.forEach(function (fn) { fn(); });
  }
  // An <audio> or <video> can be metered only when it comes from this site over http(s).
  function canRoute(src) {
    if (touch || !AC || location.protocol === 'file:') return false;
    try { return new URL(src, location.href).origin === location.origin; } catch (e) { return false; }
  }
  var SPEAKER = '<path d="M2.5 6.2h2.6L8.6 3v10L5.1 9.8H2.5z" fill="currentColor" stroke="none"/>';
  function volIcon() {
    var waves = vol === 0 ? '<path d="M11 6l3.5 4M14.5 6L11 10"/>'
      : '<path d="M10.8 6.2a2.6 2.6 0 0 1 0 3.6"/>' + (vol < 0.45 ? '' : '<path d="M12.6 4.4a5.2 5.2 0 0 1 0 7.2"/>');
    return '<svg aria-hidden="true" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' + SPEAKER + waves + '</svg>';
  }
  each('.volctl', function (box) {
    var mute = box.querySelector('.volctl-mute'), range = box.querySelector('.volctl-range');
    function show() {
      range.value = Math.round(vol * 100);
      range.setAttribute('aria-valuetext', Math.round(vol * 100) + '%');
      mute.innerHTML = volIcon();
      mute.setAttribute('aria-pressed', String(vol === 0));
      mute.setAttribute('aria-label', vol === 0 ? 'Unmute' : 'Mute');
    }
    range.addEventListener('input', function () { setVol(range.value / 100); });
    mute.addEventListener('click', function () { setVol(vol === 0 ? lastVol : 0); });
    volWatch.push(show); show();
  });
  each('.master', function (strip) {
    var fader = strip.querySelector('.m-fader'), read = strip.querySelector('.m-read');
    var bars = Array.prototype.map.call(strip.querySelectorAll('.m-meter'), function (m) { return m.querySelectorAll('i'); });
    var shown = [0, 0], lit = [-1, -1], quiet = 0, running = false, frame = 0, buf = null;
    function show() {
      var pct = Math.round(vol * 100);
      fader.style.setProperty('--v', vol);
      fader.setAttribute('aria-valuenow', pct); fader.setAttribute('aria-valuetext', pct + '%');
      read.textContent = pct + '%';
    }
    function fromPointer(ev) {
      var r = fader.getBoundingClientRect(), cap = parseFloat(getComputedStyle(fader).getPropertyValue('--cap')) * parseFloat(getComputedStyle(document.documentElement).fontSize) || 50;
      setVol((r.bottom - cap / 2 - ev.clientY) / (r.height - cap));
    }
    fader.addEventListener('pointerdown', function (ev) {
      fader.setPointerCapture(ev.pointerId); fromPointer(ev);
      var move = function (e) { fromPointer(e); };
      var up = function () { fader.removeEventListener('pointermove', move); fader.removeEventListener('pointerup', up); fader.removeEventListener('pointercancel', up); };
      fader.addEventListener('pointermove', move); fader.addEventListener('pointerup', up); fader.addEventListener('pointercancel', up);
      ev.preventDefault(); fader.focus();
    });
    fader.addEventListener('keydown', function (ev) {
      var step = { ArrowUp: 0.05, ArrowRight: 0.05, ArrowDown: -0.05, ArrowLeft: -0.05, PageUp: 0.2, PageDown: -0.2 }[ev.key];
      if (step) setVol(vol + step); else if (ev.key === 'Home') setVol(0); else if (ev.key === 'End') setVol(1); else return;
      ev.preventDefault();
    });
    function paintMeter(ch, level) {                      // level: 0 to 18 segments, counted from the bottom
      var n = Math.round(level), cells = bars[ch], k;
      if (n === lit[ch]) return;
      lit[ch] = n;
      for (k = 0; k < cells.length; k++) {
        var rank = cells.length - k;                      // the first cell is the top one
        cells[k].className = rank <= n ? (rank > cells.length - 3 ? 'on hot' : 'on') : '';
      }
    }
    function tick() {
      var any = false, ch, i, peak, db, want;
      frame++;
      if (taps && (!calm || frame % 8 === 0)) {            // "less motion": the meters step a few times a second
        for (ch = 0; ch < 2; ch++) {
          if (!buf) buf = new Float32Array(taps[ch].fftSize);
          taps[ch].getFloatTimeDomainData(buf);
          for (peak = 0, i = 0; i < buf.length; i++) if (Math.abs(buf[i]) > peak) peak = Math.abs(buf[i]);
          db = peak > 0 ? 20 * Math.log(peak) / Math.LN10 : -100;
          want = Math.min(18, Math.max(0, (db + 45) / 45 * 18));
          shown[ch] = calm ? want : Math.max(want, shown[ch] - 0.7);
          if (shown[ch] > 0.5) any = true;
          paintMeter(ch, shown[ch]);
        }
        strip.classList.toggle('live', any);
        quiet = any ? 0 : quiet + 1;
      }
      if (quiet < 90 * (calm ? 0.125 : 1)) requestAnimationFrame(tick); else running = false;
    }
    meterKick = function () { quiet = 0; if (!running && taps) { running = true; requestAnimationFrame(tick); } };
    volWatch.push(show); show();
  });

  /* 3. Single audio samples: <div class="player" data-src="..."> and the Home tile buttons. */
  function simplePlayer(button, src, name, timeEl, seek) {
    var audio = null, seeking = false, wired = false, routed = canRoute(src), card = button.closest ? button.closest('.player') : null;
    function level() { if (audio && !routed) audio.volume = loud(); }
    function wire() {                                     // once, on the first press of play
      if (!routed || wired) { if (routed) getCtx(); return; }
      wired = true;
      try { getCtx().createMediaElementSource(audio).connect(out); } catch (e) { routed = false; level(); }
    }
    volWatch.push(level);
    function paint() {
      var on = audio && !audio.paused;
      button.innerHTML = on ? PAUSE : PLAY;
      button.setAttribute('aria-label', (on ? 'Pause ' : 'Play ') + name);
      if (card) card.classList.toggle('is-playing', !!on);
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
      level();
      ['play', 'pause', 'timeupdate', 'loadedmetadata', 'ended'].forEach(function (ev) { audio.addEventListener(ev, paint); });
    }
    stoppers.push(stop);
    button.addEventListener('click', function () {
      ready();
      if (audio.paused) { wire(); stopOthers(stop); audio.play(); } else { audio.pause(); }
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
        src.connect(gain); gain.connect(out);
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

  /* 5. Touch screens have no hover, so the service card that fills most of the screen lights up instead.
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
    function level() { v.volume = loud(); }
    volWatch.push(level); level();
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
