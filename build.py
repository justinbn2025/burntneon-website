#!/usr/bin/env python3
"""Build the Burnt Neon site.

    python3 build.py

Reads content/*.json and static/, writes the finished site to _site/.
Standard library only: nothing to install.

Everything you read on the site lives in content/*.json. Page wording is in
content/pages.json; credits, quotes, samples, prices and links are in the others.
"""
import html
import json
import math
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
    path = ROOT / "content" / (name + ".json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as err:
        sys.exit("Could not read content/%s.json: %s at line %d, column %d.\n"
                 "Usually a missing comma or quotation mark on that line or the one above."
                 % (name, err.msg, err.lineno, err.colno))


SITE = load("site")
CREDITS = load("credits")
QUOTES = load("quotes")
MUSIC = load("music")
PODCASTS = load("podcasts")
PAGES = load("pages")

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
    if not (STATIC / "audio" / src).exists():
        missing("audio file not found: static/audio/" + src)
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

NAV = [("film.html", "film"), ("music.html", "music"), ("podcasts.html", "podcasts"), ("index.html#about", "about")]


def logo():
    """The wordmark in the menu bar: the logo image, or plain text if the image files are missing."""
    if (STATIC / "img" / "logo.png").exists() and (STATIC / "img" / "logo-compact.png").exists():
        mark = ('<picture><source media="(max-width: 40em)" srcset="img/logo-compact.png" width="617" height="132">'
                '<img src="img/logo.png" alt="%s, home" width="1104" height="132"></picture>' % e(SITE["name"]))
    else:
        mark = '<span class="logo-a">BURNT NEON</span> <span class="logo-b">PRODUCTIONS</span>'
    return '<a class="logo" href="index.html">%s</a>' % mark


def layout(page, title, description, body):
    short = PAGES["shared"].get("menu_on_phones", {})

    def label(key):
        """Menu wording, with a shorter version for narrow screens where one is given."""
        full = e(PAGES["shared"]["menu"][key])
        if not short.get(key):
            return full
        return '<span class="nav-wide">%s</span><span class="nav-narrow">%s</span>' % (full, e(short[key]))

    nav = "".join('<li><a href="%s"%s>%s</a></li>' % (href, ' aria-current="page"' if key == page else "", label(key))
                  for href, key in NAV)
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
<link rel="icon" href="favicon.ico" sizes="48x48">
<link rel="icon" href="icon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&amp;family=Inter:wght@400;500;600&amp;display=swap">
<link rel="stylesheet" href="css/site.css?v={ver}">
<script src="js/site.js?v={ver}" defer></script>
</head>
<body class="page-{page}">
<a class="skip" href="#main">{skip}</a>
{defs}
<header class="site-header">
<div class="wrap nav-row">
{logo}
<nav aria-label="Main"><ul class="nav-list" role="list">{nav}</ul></nav>
<a class="btn btn-small nav-cta" href="{mail}">{menu_button}</a>
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
           defs=wave_defs(), ver=VERSION, nav=nav, logo=logo(), skip=e(PAGES["shared"]["skip_link"]),
           menu_button=e(PAGES["shared"]["menu_button"]), mail=mailto(), wave=WAVE_USE, body=body,
           legal=e(SITE["legal_name"]), loc=e(SITE["location"]), foot=foot)


def section(inner, cls="", sid=""):
    return '<section class="band %s"%s><div class="wrap">%s</div></section>' % (
        cls, ' id="%s"' % sid if sid else "", inner)


def heading(eyebrow, h2=""):
    return '<p class="eyebrow">%s</p>' % eyebrow + ('<h2>%s</h2>' % h2 if h2 else "")


def reel(key, label, src, poster):
    """A video card. Plays a YouTube or Vimeo link, or an .mp4, when clicked.
    Left out entirely (drafts included) until its link is filled in under "reels" in site.json."""
    if not src:
        missing("video: " + label)
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


def quotes(page, eyebrow, look="band-dots", reviews_line=""):
    """Client quotes for one page; the section appears once quotes.json has at least one quote for the page.
    reviews_line is that page's own line under the quotes, if it has one."""
    items = [q for q in QUOTES if page in q.get("pages", [])]
    filled = [q for q in items if q.get("quote")]
    if len(filled) < len(items):
        missing("client quotes for the %s page (%d of %d written)" % (page, len(filled), len(items)))
    if not filled:      # no quotes written for this page yet: leave the whole section out, drafts included
        return ""
    show = items if SHOW else filled
    figs = "".join(
        '<figure class="quote"><blockquote>&ldquo;%s&rdquo;</blockquote><figcaption>%s</figcaption></figure>'
        % (e(q["quote"]) if q.get("quote") else '<span class="todo">[client quote]</span>',
           e(", ".join(x for x in (q.get("name"), q.get("role")) if x)) or '<span class="todo">[name, role or project]</span>')
        for q in show)
    line = '<p class="reviews">%s</p>' % t(reviews_line) if reviews_line else ""
    return section(heading(eyebrow) + '<div class="grid quotes">%s</div>%s' % (figs, line), look)


def contact_band(h2, text, button, subject=""):
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


def filmstrip(items):
    """Film & Games 'How it works': each stage is a frame on a strip of film."""
    frames = "".join(
        '<li class="frame"><div class="frame-mark" aria-hidden="true"><span>REEL 1</span><span>FRAME %02d</span></div>'
        '<h3>%s</h3><p>%s</p></li>' % (i, h, p) for i, (h, p) in enumerate(items, 1))
    # On narrower screens the strip scrolls sideways; site.js adds the dots and makes it reachable by keyboard.
    hint = e(PAGES["shared"].get("swipe_hint", "Swipe"))
    return ('<div class="filmstrip" role="group" aria-label="%s"><ol class="frames" role="list">%s</ol></div>'
            '<p class="film-hint" aria-hidden="true"><span class="film-dots"></span><span>%s</span></p>' % (hint, frames, hint))


def knob(i, n):
    """A rotary knob drawn as SVG, turned further for each later step."""
    angle = 135 if i == n else -135 + 270 * (2 * i - 1) / (2 * n)     # 0 = straight up
    ticks = ""
    for k in range(11):
        a = -135 + 27 * k
        r = math.radians(a)
        ticks += '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="%s"/>' % (
            60 + 46 * math.sin(r), 60 - 46 * math.cos(r), 60 + 53 * math.sin(r), 60 - 53 * math.cos(r),
            "on" if a <= angle + 0.1 else "off")
    r = math.radians(angle)
    return ('<svg class="knob" aria-hidden="true" viewBox="0 0 120 120">%s<circle cx="60" cy="60" r="38" class="knob-body"/>'
            '<circle cx="60" cy="60" r="30" class="knob-face"/><line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="knob-pointer"/></svg>'
            % (ticks, 60 + 12 * math.sin(r), 60 - 12 * math.cos(r), 60 + 30 * math.sin(r), 60 - 30 * math.cos(r)))


def knobs(items):
    """Music 'How it works': one knob per step."""
    n = len(items)
    return '<ol class="grid knobs" role="list">%s</ol>' % "".join(
        '<li class="knob-card"><div class="knob-head">%s<div><div class="knob-stage" aria-hidden="true">STAGE %d</div><h3>%s</h3></div></div><p>%s</p></li>'
        % (knob(i, n), i, h, p) for i, (h, p) in enumerate(items, 1))


def step_list(lines):
    """The short list under a step. "Vocals: the instrumental" shows "Vocals" as the lead-in."""
    out = ""
    for line in lines or []:
        head, sep, rest = line.partition(": ")
        out += "<li><b>%s</b> %s</li>" % (t(head), t(rest)) if sep else "<li>%s</li>" % t(line)
    return '<ul class="strip-list">%s</ul>' % out if out else ""


def ask_button(label, name, subject, ghost=True):
    """A card's enquiry button, always on two lines: the label, then the thing asked about."""
    return ('<a class="btn btn-ask%s" href="%s"><span>%s</span> <span>%s</span></a>'
            % (" btn-ghost" if ghost else "", mailto(subject), label, e(name)))


def strips(items, label="CH", ordered=False):
    """Channel strips on a mixing board; the fader and meter are decoration.
    Music's 'How it works' uses them as an ordered list, one strip per stage."""
    meter = "<i></i>" * 12
    outer, inner = ("ol", "li") if ordered else ("div", "div")
    return '<%s class="grid strips"%s>%s</%s>' % (outer, ' role="list"' if ordered else "", "".join(
        '<%s class="strip"><div class="strip-top" aria-hidden="true"><span>%s %d</span><i class="led"></i></div>'
        '<div class="strip-fader" aria-hidden="true"><div class="fader"><i class="fader-cap"></i></div><div class="meter">%s</div></div>'
        '<h3 class="strip-name">%s</h3><p>%s</p>%s</%s>' % (inner, label, i, meter, h, p, extra, inner)
        for i, (h, p, extra) in enumerate(items, 1)), outer)


def thread(items, names):
    """Podcasts 'How it works': the job as a short message thread."""
    out = ""
    for i, it in enumerate(items, 1):
        mine = it.get("from") == "me"
        names_ = it.get("files") or ([it["file"]] if it.get("file") else [])
        file = ('<span class="files">%s</span>' % "".join('<span class="file">%s</span>' % e(f) for f in names_)) if names_ else ""
        out += ('<li class="msg %s"><div class="bubble"><span class="bubble-who">%s</span>%s%s</div>'
                '<div class="msg-step"><div class="msg-title"><span class="msg-n" aria-hidden="true">%d</span><h3>%s</h3></div><p>%s</p></div></li>'
                % ("msg-me" if mine else "msg-them", e(names["me" if mine else "host"]), t(it.get("says", "")), file,
                   i, t(it["title"]), t(it["text"])))
    return '<ol class="thread" role="list">%s</ol>' % out


# Banners whose side card sits under the text instead of beside it, leaving the photo clear.
STACKED_HEROES = set()


def hero(page, eyebrow, h1, lead, buttons, side, bg_alt, bg_label):
    bg = image("hero-%s.jpg" % page, "", "hero-bg hero-bg-%s" % page, bg_label)   # decorative: empty alt
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
            '%s</div></section>' % (bg, pause, (" stack" if page in STACKED_HEROES else "") if side else " solo", eyebrow, h1, lead, btns, side_html))


# ---------- wording ----------

def numbers():
    """The values that {placeholders} in pages.json can use."""
    return {"reply_days": SITE.get("reply_days"), "review_count": MUSIC.get("review_count"),
            "turnaround_days": PODCASTS.get("turnaround_days"), "revision_rounds": PODCASTS.get("revision_rounds")}


LABELS = {"reply_days": "reply time", "review_count": "number of reviews",
          "turnaround_days": "turnaround", "revision_rounds": "number of"}


def t(text):
    """Wording from pages.json, made safe for the page.

    *word* becomes orange, {name} is filled in from the content files, and a
    [bracketed part] is dropped when a number it needs is still missing and
    placeholders are switched off.
    """
    vals = numbers()

    def optional(m):
        inner = m.group(1)
        for name in re.findall(r"\{(\w+)\}", inner):
            if not vals.get(name):
                missing(LABELS.get(name, name))
                if not SHOW:
                    return ""
        return inner

    def fill(m):
        name = m.group(1)
        if name not in vals:
            return m.group(0)
        if vals[name]:
            return e(vals[name])
        missing(LABELS.get(name, name))
        return '<span class="todo">[' + e(LABELS.get(name, name)) + "]</span>" if SHOW else ""

    text = re.sub(r"\[([^\]]*)\]", optional, str(text))
    text = e(text)
    text = re.sub(r"\{(\w+)\}", fill, text)
    return re.sub(r"\*(.+?)\*", r'<span class="hi">\1</span>', text)


def banner_buttons(b, first_href, subject=""):
    return [(first_href, t(b["button"])), (mailto(b.get("email_subject", subject)), t(b["second_button"]))]


def contact(c):
    return contact_band(t(c["heading"]), t(c["text"]), t(c["button"]), c.get("email_subject", ""))


# ---------- pages ----------

def home():
    p = PAGES["home"]
    hrefs = {"film": "film.html", "music": "music.html", "podcasts": "podcasts.html"}
    slots = {"film": "a still from one of your films, or a mix session on screen",
             "music": "you at the mic, or the vocal booth",
             "podcasts": "your editing screen with a podcast waveform"}
    tile_html = ""
    for key in ("film", "music", "podcasts"):
        tile = p["paths"][key]
        sample = SITE["tile_samples"].get(key)
        if not sample:
            missing("audio: short %s sample for the Home tile" % key)
        btn = ('<button class="play tile-play" type="button" data-src="%s" data-label="a %s sample" aria-label="Play a %s sample">%s</button>'
               % (e(media(sample)), key, key, PLAY)) if sample else ""
        tile_html += ('<div class="tile">%s<div class="tile-panel"><div class="tile-head"><h3>%s</h3>%s</div>'
                      '<p>%s</p><a href="%s">%s &rarr;</a></div></div>'
                      % (image("tile-%s.jpg" % key, "", "tile-img", "Photo: " + slots[key]), t(tile["name"]), btn,
                         t(tile["text"]), hrefs[key], t(tile["link"])))
    b = p["banner"]
    body = hero("home", t(b["label"]), t(b["headline"]), t(b["text"]), banner_buttons(b, "#paths"),
                reel("home", b["video_label"], SITE["reels"].get("home"), "reel-home.jpg"),
                "", "Background: a muted video loop or photo of the studio")
    body += section(heading(t(p["paths"]["label"]), t(p["paths"]["heading"])) + '<div class="grid tiles">%s</div>' % tile_html,
                    "band-rings rings-side fade-in", "paths")
    body += quotes("home", t(p["quotes_label"]), "band-foam foam-fade band-line")
    a = p["about"]
    body += section('<div class="about">%s<div class="about-text">%s%s<a class="btn btn-ghost" href="%s">%s</a></div></div>'
                    % (image("portrait.jpg", "Justin at the studio desk", "portrait", "Portrait: Justin at the desk or the mic"),
                       heading(t(a["label"]), t(a["heading"])), "".join("<p>%s</p>" % t(x) for x in a["paragraphs"]),
                       mailto(), t(a["button"])), "glow-tr band-line", "about")
    body += contact(p["contact"])
    return layout("home", p["browser_title"], p["search_description"], body)


def film():
    p = PAGES["film"]
    imdb = SITE["links"].get("imdb")
    b = p["banner"]
    body = hero("film", t(b["label"]), t(b["headline"]), t(b["text"]),
                banner_buttons(b, "#credits", p["contact"].get("email_subject", "")),
                reel("film", b["video_label"], SITE["reels"].get("film"), "reel-film.jpg"),
                "", "Background: a darkened film still, or the mix session on screen")
    c = p["credits"]
    body += section('<div class="split-head"><div>%s</div>%s</div>%s' % (
        heading(t(c["label"]), t(c["heading"])),
        '<a href="%s" rel="noopener">%s &rarr;</a>' % (e(imdb), t(c["link"])) if imdb else "",
        credit_cards(CREDITS)), "glow-br", "credits")      # glow kept low: the top stays dark under the banner's fade
    s = p["services"]
    body += section(heading(t(s["label"]), t(s["heading"])) + cards([(t(i["title"]), t(i["text"]), "") for i in s["items"]]),
                    "band-timeline band-line")
    s = p["steps"]
    body += section(heading(t(s["label"]), t(s["heading"])) + filmstrip([(t(i["title"]), t(i["text"])) for i in s["items"]]),
                    "glow-bl")       # no line: what I do runs straight into how it works
    body += quotes("film", t(p["quotes_label"]), "band-rings band-line")
    body += contact(p["contact"])
    return layout("film", p["browser_title"], p["search_description"], body)


def music():
    p = PAGES["music"]
    b = p["banner"]
    # "show_banner_reel": false in music.json leaves the banner without a player.
    side = ""
    if MUSIC.get("show_banner_reel", True):
        side = '<div class="reel-audio">%s</div>' % player(t(p["reel"]["title"]), t(p["reel"]["text"]), MUSIC.get("reel"), "singing reel")
    body = hero("music", t(b["label"]), t(b["headline"]), t(b["text"]), banner_buttons(b, "#listen"),
                "", "", "Background: you singing at the mic, on the right third")
    body = body.replace('<div class="btn-row">', side + '<div class="btn-row">', 1) if side else body
    groups = ""
    for style in MUSIC["styles"]:
        rows = "".join(
            player(val(tr.get("title"), "track title"),
                   " &middot; ".join(x for x in (e(tr["artist"]) if tr.get("artist") else ("" if tr.get("src") else val("", "artist")),
                                                val(tr.get("role"), "your role")) if x),
                   tr.get("src"), "%s sample" % style["name"])
            for tr in style["tracks"])
        if rows:
            groups += '<div class="style"><h3>%s</h3>%s</div>' % (e(style["name"]), rows)
    spotify = SITE["links"].get("spotify")
    if not spotify:
        missing("link: spotify")
    li = p["listen"]
    body += section(heading(t(li["label"]), t(li["heading"])) + '<div class="grid styles">%s</div>' % groups
                    + ('<p class="aside">%s <a href="%s" rel="noopener">%s</a>.</p>'
                       % (t(li["spotify_line"]), e(spotify), t(li["spotify_link"])) if spotify else ""), "band-spectro", "listen")
    # How it works comes first, as channel strips in the rack panel; Services is the page's pricing
    # section, so it takes the dots (kept for pricing) and plain cards like the podcast packages.
    st = p["steps"]
    body += section(heading(t(st["label"]), t(st["heading"]))
                    + strips([(t(i["title"]), t(i["text"]), step_list(i.get("list"))) for i in st["items"]], "STAGE", ordered=True), "band-rack")
    sv = p["services"]
    svc = ""
    for s in MUSIC["services"]:
        if s.get("price") == "quote":
            price = "Quoted <span>/ %s</span>" % e(s["unit"])
        else:
            pr = val(s.get("price"), "price: " + s["name"].lower())
            price = "From %s <span>/ %s</span>" % (pr, e(s["unit"])) if pr else ""
        send = ('<p class="pack-send"><b>%s</b> %s</p>' % (t(sv["send_label"]), e(s["send"]))) if s.get("send") else ""
        svc += ('<div class="pack pack-hover"><h3>%s</h3>%s<p>%s</p>%s%s</div>'
                % (e(s["name"]), '<div class="pack-price">%s</div>' % price if price else "", e(s["text"]), send,
                   ask_button(t(sv["button"]), s["name"], "Music: " + s["name"])))
    body += section(heading(t(sv["label"]), t(sv["heading"])) + '<div class="grid packs">%s</div>' % svc
                    + '<p class="aside">%s</p>' % t(sv["note"]), "band-dots", "services")
    th = p["theater"]
    body += section('<div class="about"><div class="about-text">%s<p>%s</p><a class="btn" href="%s">%s</a></div>%s</div>'
                    % (heading(t(th["label"]), t(th["heading"])), t(th["text"]), mailto(th.get("email_subject", "")), t(th["button"]),
                       image("theater.jpg", "A score on the music stand", "wide-img", "Photo: a score on the stand, or recording a cast number")),
                    "glow-bl band-line")
    body += quotes("music", t(p["quotes_label"]), "band-foam foam-fade band-line", p.get("reviews_line", ""))
    body += contact(p["contact"])
    return layout("music", p["browser_title"], p["search_description"], body)


def podcasts():
    p = PAGES["podcasts"]
    b = p["banner"]
    samples = PODCASTS["samples"]
    first = ab_player(samples[0], 1) if samples else ""
    body = hero("podcasts", t(b["label"]), t(b["headline"]), t(b["text"]), banner_buttons(b, "#packages"),
                "", "", "Background: your editing screen with a podcast waveform, headphones in frame")
    # The first before-and-after sample has its own section under the banner: words on the left,
    # the player on the right, set in the dark rack panel like a piece of outboard gear.
    if first:
        sm = p["sample"]
        body += section('<div class="sample"><div>%s<p class="sample-lead">%s</p></div><div class="sample-player">%s</div></div>'
                        % (heading(t(sm["label"]), t(sm["heading"])), t(PAGES["shared"]["sample_hint"]), first),
                        "band-rack rack-dark", "sample")
    # "show_more_samples": false in podcasts.json hides the "More examples" section
    # (and stops the build asking for those samples) until it is switched back on.
    more = ""
    if PODCASTS.get("show_more_samples", True):
        more = "".join(ab_player(s, i) for i, s in enumerate(samples[1:], 2))
    if more:
        m = p["more_samples"]
        body += section(heading(t(m["label"]), t(m["heading"])) + '<div class="grid ab-grid">%s</div>' % more, "band-spectro")
    # Dots are kept for pricing: the packages are the only dotted section on the site.
    look_steps, look_packages = ("glow-bl band-line" if more else "glow-bl"), "band-dots band-line fade-out"
    st = p["steps"]
    body += section(heading(t(st["label"]), t(st["heading"])) + thread(st["items"], st.get("names", {"host": "You", "me": "Me"})),
                    look_steps)
    pk = p["packages"]
    packs = ""
    for pack in PODCASTS["packages"]:
        price = val(pack.get("price"), "price: " + pack["name"])
        items = "".join("<li>%s</li>" % x for x in (t(i) for i in pack["includes"]) if x.strip())
        packs += ('<div class="pack%s"><div class="pack-kind">%s</div><h3>%s</h3>%s<ul>%s</ul>'
                  '%s</div>'
                  % (" pack-hi" if pack.get("highlight") else "", e(pack["kind"]), e(pack["name"]),
                     '<div class="pack-price">%s%s</div>' % (price, " <span>/ %s</span>" % e(pack["per"]) if pack.get("per") else "") if price else "",
                     items, ask_button(t(pk["button"]), pack["name"], "Podcast: " + pack["name"], not pack.get("highlight"))))
    body += section(heading(t(pk["label"]), t(pk["heading"])) + '<div class="grid packs">%s</div>' % packs
                    + '<p class="aside">%s</p>' % t(pk["note"]), look_packages, "packages")
    q = p["questions"]
    body += section(heading(t(q["label"]), t(q["heading"])) + '<div class="grid faq">%s</div>' % "".join(
        "<div><h3>%s</h3><p>%s</p></div>" % (e(x["q"]), e(x["a"])) for x in PODCASTS["questions"]), "band-rings rings-br fade-in")      # questions follow on from the prices
    body += contact(p["contact"])
    return layout("podcasts", p["browser_title"], p["search_description"], body)


def not_found():
    p = PAGES["not_found"]
    return layout("404", p["browser_title"], p["text"],
                  section('<h1>%s</h1><p class="lead">%s</p><div class="btn-row"><a class="btn" href="index.html">%s</a></div>'
                          % (t(p["heading"]), t(p["text"]), t(p["button"])), "glow-tr"))


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
