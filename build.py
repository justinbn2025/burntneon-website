#!/usr/bin/env python3
"""Build the Burnt Neon site.

    python3 build.py

Reads content/*.json and static/, writes the finished site to _site/.
Standard library only: nothing to install.

What changes often lives in content/*.json. Page wording that rarely
changes lives in the page functions below.
"""
import html
import json
import random
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"
STATIC = ROOT / "static"


def load(name):
    with open(ROOT / "content" / (name + ".json"), encoding="utf-8") as f:
        return json.load(f)


SITE = load("site")
CREDITS = load("credits")
QUOTES = load("quotes")
MUSIC = load("music")
PODCASTS = load("podcasts")

def _version():
    """Changes whenever the stylesheet or script changes, so browsers never show a stale copy."""
    import hashlib
    h = hashlib.sha1()
    for f in ("css/site.css", "js/site.js"):
        h.update((STATIC / f).read_bytes())
    return h.hexdigest()[:8]


VERSION = _version()
SHOW = bool(SITE.get("show_placeholders"))
MISSING = []          # everything still to fill in, printed after the build
MEDIA_HOSTS = set()   # outside hosts that audio is loaded from


def e(text):
    return html.escape(str(text), quote=True)


def missing(what):
    if what not in MISSING:
        MISSING.append(what)


def val(value, label):
    """A filled-in value, or a visible [placeholder] while drafting."""
    if value:
        return e(value)
    missing(label)
    return '<span class="todo">[' + e(label) + "]</span>" if SHOW else ""


def media(src):
    """Audio address as written in the content files; remembers outside hosts."""
    if src.startswith("http"):
        u = urlparse(src)
        MEDIA_HOSTS.add(u.scheme + "://" + u.netloc)
        return src
    return "audio/" + src


def image(name, alt, cls, label):
    """An image from static/img if it exists, else a dashed slot while drafting."""
    if name and (STATIC / "img" / name).exists():
        return '<img class="%s" src="img/%s" alt="%s" loading="lazy">' % (cls, e(name), e(alt))
    missing("image: " + label)
    if SHOW:
        return '<div class="%s slot" role="img" aria-label="%s">%s</div>' % (cls, e(alt), e(label))
    return ""


def mailto(subject=""):
    return "mailto:" + SITE["email"] + ("?subject=" + quote(subject) if subject else "")


PLAY = '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>'


# ---------- shared pieces ----------

def wave_defs():
    """The waveform bars, drawn once and reused by the scroll bar in the header."""
    rng = random.Random(7)
    bars, level = [], 0.3
    for i in range(160):
        level = min(1.0, max(0.12, level + rng.uniform(-0.22, 0.22)))
        if i % 27 > 22:
            level *= 0.55
        h = round(4 + level * 30)
        bars.append('<rect x="%d" y="%d" width="4" height="%d" rx="2"/>' % (i * 8, 20 - h // 2, h))
    return ('<svg class="defs" aria-hidden="true" width="0" height="0"><defs><g id="wv">'
            + "".join(bars) + "</g></defs></svg>")


WAVE_USE = '<svg viewBox="0 0 1280 40" preserveAspectRatio="none"><use href="#wv"/></svg>'

NAV = [("film.html", "Film &amp; Games", "film"), ("music.html", "Music", "music"),
       ("podcasts.html", "Podcasts", "podcasts"), ("index.html#about", "About", "about")]


def layout(page, title, description, body):
    nav = "".join('<li><a href="%s"%s>%s</a></li>' % (href, ' aria-current="page"' if key == page else "", label)
                  for href, label, key in NAV)
    links = SITE["links"]
    foot = "".join('<li><a href="%s" rel="noopener">%s</a></li>' % (e(links[k]), label)
                   for k, label in (("instagram", "Instagram"), ("imdb", "IMDb"), ("linkedin", "LinkedIn"))
                   if links.get(k))
    for k in ("imdb", "linkedin"):
        if not links.get(k):
            missing("link: " + k)
    path = "" if page == "home" else page
    csp = ("default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; "
           "font-src https://fonts.gstatic.com; img-src 'self' data: https://i.ytimg.com; "
           "media-src 'self' {m}; connect-src 'self' {m}; "
           "frame-src https://www.youtube-nocookie.com https://player.vimeo.com; "
           "base-uri 'self'; form-action 'none'; object-src 'none'").format(m="@@MEDIA@@")
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{csp}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}/{path}">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}/{path}">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&amp;family=Inter:wght@400;500;600&amp;display=swap">
<link rel="stylesheet" href="css/site.css?v={ver}">
<script src="js/site.js?v={ver}" defer></script>
</head>
<body class="page-{page}">
<a class="skip" href="#main">Skip to content</a>
{defs}
<header class="site-header">
<div class="wrap nav-row">
<a class="logo" href="index.html"><span class="logo-a">BURNT NEON</span> <span class="logo-b">PRODUCTIONS</span></a>
<nav aria-label="Main"><ul class="nav-list" role="list">{nav}<li><a class="btn btn-small" href="{mail}">Get in touch</a></li></ul></nav>
</div>
<div class="wave" aria-hidden="true"><div class="wave-base">{wave}</div><div class="wave-fill">{wave}</div><i class="wave-head"></i></div>
</header>
<main id="main">
{body}
</main>
<footer class="site-footer">
<div class="wrap foot-row">
<span>&copy; 2026 {legal}. {loc}.</span>
<ul class="foot-links" role="list">{foot}</ul>
</div>
</footer>
</body>
</html>
""".format(csp=csp, title=e(title), desc=e(description), url=SITE["url"], path=path, page=page,
           defs=wave_defs(), ver=VERSION, nav=nav, mail=mailto(), wave=WAVE_USE, body=body,
           legal=e(SITE["legal_name"]), loc=e(SITE["location"]), foot=foot)


def section(inner, cls="", sid=""):
    return '<section class="band %s"%s><div class="wrap">%s</div></section>' % (
        cls, ' id="%s"' % sid if sid else "", inner)


def heading(eyebrow, h2=""):
    return '<p class="eyebrow">%s</p>' % eyebrow + ('<h2>%s</h2>' % h2 if h2 else "")


def reel(key, label, src, poster):
    """A video card. Plays a YouTube or Vimeo link, or an .mp4, when clicked."""
    if not src:
        missing("video: " + label)
        if not SHOW:
            return ""
    img = ('<img src="img/%s" alt="" loading="lazy">' % poster) if (STATIC / "img" / poster).exists() else ""
    note = "" if src else '<span class="reel-note">Video to add: %s</span>' % e(label)
    return ('<div class="reel%s" data-video="%s" data-title="%s">%s<span class="reel-label">%s</span>'
            '<button class="play play-big" type="button" aria-label="Play the %s video"%s>%s</button>%s</div>'
            % ("" if src else " slot", e(src or ""), e(label), img, e(label), e(label.lower()),
               "" if src else " disabled", PLAY, note))


def player(title, sub, src, label):
    """One audio sample: play button, title, time."""
    if not src:
        missing("audio: " + label)
        if not SHOW:
            return ""
    off = "" if src else " disabled"
    return ('<div class="player%s" data-src="%s" data-label="%s">'
            '<button class="play" type="button" aria-label="Play %s"%s>%s</button>'
            '<div class="player-meta"><div class="player-title">%s</div><div class="player-sub">%s</div></div>'
            '<span class="player-time">0:00</span>'
            '<input class="player-seek" type="range" min="0" max="1000" value="0" aria-label="Position in %s"%s></div>'
            % ("" if src else " slot", e(media(src)) if src else "", e(label), e(label), off, PLAY, title, sub,
               e(label), off))


def ab_player(sample, n):
    """A before/after sample. Both files must be the same length."""
    ready = sample.get("before") and sample.get("after")
    if not ready:
        missing("podcast before/after sample %d" % n)
        if not SHOW:
            return ""
    title = val(sample.get("title"), "sample %d title" % n)
    note = val(sample.get("note"), "one line on the problem and what changed")
    data = ('data-before="%s" data-after="%s"' % (e(media(sample["before"])), e(media(sample["after"])))
            if ready else "")
    off = "" if ready else " disabled"
    name = e(sample.get("title") or "sample %d" % n)
    return ('<div class="ab%s" role="group" aria-label="Before and after: %s" %s><p class="ab-title">%s</p><p class="ab-note">%s</p>'
            '<div class="ab-row"><button class="play" type="button" aria-label="Play %s"%s>%s</button>'
            '<div class="ab-switch" role="group" aria-label="Version"><button type="button" class="ab-before" aria-pressed="true"%s>Before</button>'
            '<button type="button" class="ab-after" aria-pressed="false"%s>After</button></div>'
            '<input class="ab-seek" type="range" min="0" max="1000" value="0" aria-label="Position in %s"%s>'
            '<span class="ab-time">0:00</span></div><p class="ab-error" role="alert" hidden></p></div>'
            % ("" if ready else " slot", name, data, title, note, name, off, PLAY, off, off, name, off))


def quotes(page, eyebrow):
    items = [q for q in QUOTES if page in q.get("pages", [])]
    filled = [q for q in items if q.get("quote")]
    if len(filled) < len(items):
        missing("client quotes for the %s page (%d of %d written)" % (page, len(filled), len(items)))
    show = items if SHOW else filled
    if not show:
        return ""
    figs = "".join(
        '<figure class="quote"><blockquote>&ldquo;%s&rdquo;</blockquote><figcaption>%s</figcaption></figure>'
        % (e(q["quote"]) if q.get("quote") else '<span class="todo">[client quote]</span>',
           e(", ".join(x for x in (q.get("name"), q.get("role")) if x)) or '<span class="todo">[name, role or project]</span>')
        for q in show)
    count = val(SITE.get("review_count"), "number of reviews")
    line = ('<p class="reviews">5.0 average across %s client reviews on Fiverr and SoundBetter.</p>' % count
            if count and page != "film" else "")
    return section(heading(eyebrow) + '<div class="grid quotes">%s</div>%s' % (figs, line), "band-dots")


def contact_band(h2, text, button, subject=""):
    days = val(SITE.get("reply_days"), "reply time")
    text = text.replace("{days}", days) if days else re.sub(r"\s*[^.]*\{days\}[^.]*\.", "", text)
    return ('<section class="band band-cta"><div class="wrap cta-row"><div><h2>%s</h2><p>%s</p></div>'
            '<a class="btn" href="%s">%s</a></div></section>' % (h2, text, mailto(subject), button))


def credit_cards(items):
    cards = []
    for c in items:
        poster = image("posters/" + c["poster"] if c.get("poster") else "", "Poster: " + c["title"],
                       "poster", "Poster: " + c["title"])
        clip = ('<button class="play poster-play" type="button" data-video="%s" aria-label="Watch a clip from %s (opens in a new tab)">%s</button>'
                % (e(c["clip"]), e(c["title"]), PLAY)) if c.get("clip") else ""
        cards.append('<li class="credit"><div class="poster-wrap">%s%s</div><p class="credit-title">%s '
                     '<span>(%s)</span></p><p class="credit-role">%s</p></li>'
                     % (poster, clip, e(c["title"]), e(c["year"]), e(c["role"])))
    return '<ul class="grid credits" role="list">%s</ul>' % "".join(cards)


def steps(items):
    return '<ol class="grid steps" role="list">%s</ol>' % "".join(
        '<li class="step"><div class="step-n" aria-hidden="true">%d</div><h3>%s</h3><p>%s</p></li>' % (i, h, p)
        for i, (h, p) in enumerate(items, 1))


def cards(items):
    return '<div class="grid cards">%s</div>' % "".join(
        '<div class="card"><h3>%s</h3><p>%s</p>%s</div>' % (h, p, extra) for h, p, extra in items)


def hero(page, eyebrow, h1, lead, buttons, side, bg_alt, bg_label):
    bg = image("hero-%s.jpg" % page, "", "hero-bg", bg_label)   # decorative: empty alt
    if page == "home" and (STATIC / "video" / "hero-home.mp4").exists():
        bg = ('<video class="hero-bg" autoplay muted loop playsinline aria-hidden="true" tabindex="-1" poster="img/hero-home.jpg">'
              '<source src="video/hero-home.mp4" type="video/mp4"></video>'
              '<button class="hero-pause" type="button" aria-pressed="false">Pause background video</button>')
    btns = "".join('<a class="btn%s" href="%s">%s</a>' % (" btn-ghost" if i else "", href, label)
                   for i, (href, label) in enumerate(buttons))
    if "hero-pause" in bg:      # keep the pause button above the shade
        bg, pause = bg.split('<button class="hero-pause"')
        pause = '<button class="hero-pause"' + pause
    else:
        pause = ""
    side_html = '<div class="hero-side">%s</div>' % side if side else ""
    return ('<section class="hero">%s<div class="hero-shade"></div>%s<div class="wrap hero-row%s"><div class="hero-text">'
            '<p class="eyebrow">%s</p><h1>%s</h1><p class="lead">%s</p><div class="btn-row">%s</div></div>'
            '%s</div></section>' % (bg, pause, "" if side else " solo", eyebrow, h1, lead, btns, side_html))


# ---------- pages ----------

def home():
    tiles = [
        ("film", "Film &amp; games", "Sound design, dialogue editing, and stereo and 5.1 mixing that serve the story.",
         "film.html", "See film credits", "a still from one of your films, or a mix session on screen"),
        ("music", "Music", "Session vocals, production, mixing and mastering, from musical theater to modern pop.",
         "music.html", "Hear the music", "you at the mic, or the vocal booth"),
        ("podcasts", "Podcasts", "Every episode edited, mixed and mastered, so you sound clear, even and close.",
         "podcasts.html", "Hear a before and after", "your editing screen with a podcast waveform"),
    ]
    tile_html = ""
    for key, name, text, href, link, slot in tiles:
        sample = SITE["tile_samples"].get(key)
        if not sample:
            missing("audio: short %s sample for the Home tile" % key)
        btn = ('<button class="play tile-play" type="button" data-src="%s" data-label="a %s sample" aria-label="Play a %s sample">%s</button>'
               % (e(media(sample)), key, key, PLAY)) if sample else ""
        tile_html += ('<div class="tile">%s<div class="tile-panel"><div class="tile-head"><h3>%s</h3>%s</div>'
                      '<p>%s</p><a href="%s">%s &rarr;</a></div></div>'
                      % (image("tile-%s.jpg" % key, "", "tile-img", "Photo: " + slot), name, btn, text, href, link))
    body = hero("home", "Los Angeles audio studio",
                'Sound for <span class="hi">film</span>, <span class="hi">music</span> and <span class="hi">podcasts</span>.',
                "Sound editing and mixing, session vocals, and podcast post-production. One engineer, start to finish.",
                [("#paths", "Hear the work"), (mailto(), "Get in touch")],
                reel("home", "Featured reel", SITE["reels"].get("home"), "reel-home.jpg"),
                "", "Background: a muted video loop or photo of the studio")
    body += section(heading("What do you need?", "Pick your path.") + '<div class="grid tiles">%s</div>' % tile_html,
                    "glow-tr", "paths")
    body += section('<div class="split-head"><div>%s</div><a href="film.html">All credits and reel &rarr;</a></div>%s'
                    % (heading("Selected credits", "Recent film work."),
                       credit_cards([c for c in CREDITS if c.get("on_home")])), "band-line", "work")
    body += quotes("home", "What clients say")
    body += section('<div class="about">%s<div class="about-text">%s<p>I&rsquo;m a sound editor, mixer and session singer in Los Angeles. '
                    'I started Burnt Neon in 2025 to do the work I care about most: making stories and songs sound the '
                    'way their makers hear them.</p><p>On screen, I&rsquo;ve been supervising sound editor and re-recording '
                    'mixer on independent films. On stage, I&rsquo;ve played Melchior in Spring Awakening and Jamie in The '
                    'Last Five Years. In the studio, I sing, produce and mix across pop, rock, R&amp;B and musical theater.</p>'
                    '<a class="btn btn-ghost" href="%s">Tell me about your project</a></div></div>'
                    % (image("portrait.jpg", "Justin at the studio desk", "portrait", "Portrait: Justin at the desk or the mic"),
                       heading("About", "Hi, I&rsquo;m Justin."), mailto()), "glow-tr band-line", "about")
    body += contact_band("Have a project in mind?",
                         "Tell me what you&rsquo;re making and when you need it. I reply within {days} business days.",
                         "Get in touch")
    return layout("home", "Burnt Neon Productions: sound for film, music and podcasts",
                  "Sound editing and mixing, session vocals, and podcast post-production in Los Angeles.", body)


def film():
    imdb = SITE["links"].get("imdb")
    body = hero("film", "Post-production sound for film, animation and games",
                'Sound that <span class="hi">serves the story</span>.',
                "Sound design, dialogue editing and mixing for independent films, animation and game trailers. "
                "One person on your sound from first spot to final delivery.",
                [("#credits", "Watch the work"), (mailto("Film sound"), "Tell me about your film")],
                reel("film", "Sound reel", SITE["reels"].get("film"), "reel-film.jpg"),
                "", "Background: a darkened film still, or the mix session on screen")
    body += section('<div class="split-head"><div>%s</div>%s</div>%s' % (
        heading("Credits", "Recent work."),
        '<a href="%s" rel="noopener">Full credits on IMDb &rarr;</a>' % e(imdb) if imdb else "",
        credit_cards(CREDITS)), "glow-tr", "credits")
    body += section(heading("Services", "What I do on a film.") + cards([
        ("Sound design and foley", "I build the sound world your picture needs, from library effects to custom foley recorded for the scene.", ""),
        ("Dialogue editing", "The best takes from every microphone, blended so the cuts disappear. Room tone smoothed, levels evened, space added where the scene calls for it.", ""),
        ("Stereo and 5.1 mixing", "Dialogue, music and effects balanced so nothing fights. Delivered at the loudness your festival or platform specifies, without losing impact.", ""),
    ]), "band-dots band-line")
    body += section(heading("How it works", "From picture lock to delivery.") + steps([
        ("Spotting", "We watch the cut together and agree what each scene needs."),
        ("Edit and design", "Dialogue cleaned and cut. Effects, ambiences and foley built."),
        ("Mix", "Everything balanced to picture. You review and send notes."),
        ("Deliver", "Final mixes in the formats on your delivery list."),
    ]), "glow-bl band-line")
    body += quotes("film", "What filmmakers say")
    body += contact_band("Have a cut that needs sound?",
                         "Send me the film, your delivery list and your deadline. I&rsquo;ll reply with a quote and a schedule within {days} business days.",
                         "Tell me about your film", "Film sound")
    return layout("film", "Film and game sound: Burnt Neon Productions",
                  "Sound design, dialogue editing and mixing for independent films, animation and game trailers.", body)


def music():
    side = '<div class="reel-audio">%s</div>' % player(
        "Singing reel", "Ninety seconds across musical theater, pop and rock.", MUSIC.get("reel"), "singing reel")
    body = hero("music", "Session vocals, production, mixing and mastering",
                'The voice and the mix that <span class="hi">finish the song</span>.',
                "A tenor for musical theater, pop and rock who also produces and mixes. Hire me for one part of your track or all of it.",
                [("#listen", "Hear the work"), (mailto("Session vocals"), "Send me your song")],
                "", "",
                "Background: you singing at the mic, on the right third")
    body = body.replace('<div class="btn-row">', side + '<div class="btn-row">', 1) if side else body
    groups = ""
    for style in MUSIC["styles"]:
        rows = "".join(
            player(val(t.get("title"), "track title"),
                   " &middot; ".join(x for x in (val(t.get("artist"), "artist"), val(t.get("role"), "your role")) if x),
                   t.get("src"), "%s sample" % style["name"])
            for t in style["tracks"])
        if rows:
            groups += '<div class="style"><h3>%s</h3>%s</div>' % (e(style["name"]), rows)
    spotify = SITE["links"].get("spotify")
    if not spotify:
        missing("link: spotify")
    body += section(heading("Listen", "Work by style.") + '<div class="grid styles">%s</div>' % groups
                    + ('<p class="aside">My own artist project, JVSTN., is on <a href="%s" rel="noopener">Spotify</a>.</p>'
                       % e(spotify) if spotify else ""), "glow-tr", "listen")
    svc = []
    for s in MUSIC["services"]:
        if s.get("price") == "quote":
            price = "Quoted " + e(s["unit"])
        else:
            p = val(s.get("price"), "price: " + s["name"].lower())
            price = "From %s %s" % (p, e(s["unit"])) if p else ""
        svc.append((e(s["name"]), e(s["text"]), '<div class="price">%s</div>' % price if price else ""))
    body += section(heading("Services", "Hire one part, or all four.") + cards(svc)
                    + '<p class="aside">Backing vocals are quoted by arrangement. Bundle rates for 3 or more songs booked together.</p>',
                    "band-dots band-line")
    body += section(heading("How a vocal session works", "Three steps, from anywhere.") + steps([
        ("Send your song", "The instrumental, a guide vocal, lyrics or sheet music, and the tempo."),
        ("I record", "First pass within 5 days. Join live over Zoom if you&rsquo;d like to direct."),
        ("Revise and deliver", "Two rounds of revisions included. WAV files at the sample rate and bit depth you ask for."),
    ]), "glow-bl band-line")
    body += section('<div class="about"><div class="about-text">%s<p>Writing a musical? I sing, bring in the rest of the cast, and '
                    'record, edit and mix the whole set, so your score sounds like a show when you send it out.</p>'
                    '<a class="btn" href="%s">Ask about your score</a></div>%s</div>'
                    % (heading("For musical theater writers", "Demos and workshop albums, start to finish."),
                       mailto("Musical theater demo"),
                       image("theater.jpg", "A score on the music stand", "wide-img", "Photo: a score on the stand, or recording a cast number")),
                    "band-line")
    body += quotes("music", "What clients say")
    body += contact_band("Have a song that needs a voice?",
                         "Send me the track and what you&rsquo;re hearing for it. I&rsquo;ll reply with a price and a delivery date within {days} business days.",
                         "Send me your song", "Session vocals")
    return layout("music", "Session vocals, production and mixing: Burnt Neon Productions",
                  "Session singing, music production, mixing and mastering, from musical theater to modern pop.", body)


def podcasts():
    samples = PODCASTS["samples"]
    first = ab_player(samples[0], 1) if samples else ""
    body = hero("podcasts", "Podcast editing, mixing and mastering",
                'Sound <span class="hi">as good</span> as what you&rsquo;re saying.',
                "Send me your recording. It comes back clear, even and close-sounding, ready to publish.",
                [("#packages", "See packages"), (mailto("Free podcast sample"), "Get a free sample")],
                first + '<p class="hint">Press play, then switch between Before and After while it plays. Headphones show it best.</p>',
                "", "Background: your editing screen with a podcast waveform, headphones in frame")
    more = "".join(ab_player(s, i) for i, s in enumerate(samples[1:], 2))
    if more:
        body += section(heading("More examples", "Different problems, same result.") + '<div class="grid ab-grid">%s</div>' % more,
                        "glow-tr")
    days = val(PODCASTS.get("turnaround_days"), "turnaround")
    body += section(heading("How it works", "Three steps, every episode.") + steps([
        ("Send your recording", "Upload the raw file, or your own edit, to a shared folder. Audio or video shows both work."),
        ("I edit, mix and master", "Room echo and noise reduced, levels evened out, harsh &ldquo;s&rdquo; sounds tamed, intro and outro added."),
        ("Publish", "A finished file comes back%s, ready to upload. For video shows it&rsquo;s the same length as your original, so it drops straight into your editor."
         % (" within %s days" % days if days else "")),
    ]), "band-dots band-line")
    rounds = val(PODCASTS.get("revision_rounds"), "number of")
    packs = ""
    for p in PODCASTS["packages"]:
        price = val(p.get("price"), "price: " + p["name"])
        items = "".join("<li>%s</li>" % e(i).replace("{revision_rounds}", rounds)
                        for i in p["includes"] if "{revision_rounds}" not in i or rounds)
        packs += ('<div class="pack%s"><div class="pack-kind">%s</div><h3>%s</h3>%s<ul>%s</ul>'
                  '<a class="btn%s" href="%s">Ask about %s</a></div>'
                  % (" pack-hi" if p.get("highlight") else "", e(p["kind"]), e(p["name"]),
                     '<div class="pack-price">%s%s</div>' % (price, " <span>/ %s</span>" % e(p["per"]) if p.get("per") else "") if price else "",
                     items, "" if p.get("highlight") else " btn-ghost", mailto("Podcast: " + p["name"]), e(p["name"])))
    body += section(heading("Packages", "Simple monthly pricing.") + '<div class="grid packs">%s</div>' % packs
                    + '<p class="aside">Longer or more frequent shows are quoted on request.</p>', "glow-bl band-line", "packages")
    body += section(heading("Questions", "Before you ask.") + '<div class="grid faq">%s</div>' % "".join(
        "<div><h3>%s</h3><p>%s</p></div>" % (e(q["q"]), e(q["a"])) for q in PODCASTS["questions"]), "band-line")
    body += contact_band("Hear your own show, mixed.",
                         "Send me a recent episode and I&rsquo;ll mix a free 30-second sample, so you can hear the difference on your own voice before deciding anything.",
                         "Get a free sample", "Free podcast sample")
    return layout("podcasts", "Podcast editing, mixing and mastering: Burnt Neon Productions",
                  "Podcast editing, mixing and mastering. Hear a before and after, then get a free sample of your own show.", body)


def not_found():
    return layout("404", "Page not found: Burnt Neon Productions", "Page not found.",
                  section('<h1>That page isn&rsquo;t here.</h1><p class="lead">It may have moved when the site was rebuilt.</p>'
                          '<div class="btn-row"><a class="btn" href="index.html">Go to the home page</a></div>', "glow-tr"))


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT, ignore=shutil.ignore_patterns(".DS_Store"))
    pages = {"index.html": home(), "film.html": film(), "music.html": music(),
             "podcasts.html": podcasts(), "404.html": not_found()}
    hosts = " ".join(sorted(MEDIA_HOSTS))
    for name, text in pages.items():
        (OUT / name).write_text(text.replace("@@MEDIA@@", hosts), encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % SITE["url"])
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join("<url><loc>%s/%s</loc></url>\n" % (SITE["url"], p) for p in ("", "film", "music", "podcasts"))
        + "</urlset>\n")
    print("Built %d pages into %s" % (len(pages), OUT.name + "/"))
    if MISSING:
        print("\nStill to fill in (%d)%s:" % (len(MISSING), ", shown as [placeholders]" if SHOW else ", hidden on the site"))
        for m in MISSING:
            print("  - " + m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
