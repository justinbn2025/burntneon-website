#!/usr/bin/env python3
"""Build the Burnt Neon site.

    python3 build.py

Reads content/*.json and static/, writes the finished site to _site/.
Standard library only: nothing to install.

Everything you read on the site lives in content/*.json. Page wording is in
content/pages.json; credits, quotes, samples, prices and links are in the others.
"""
import hashlib
import html
import json
import math
import os
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
# Where the site is being published. The publishing workflow passes the real address (the preview address
# before the domain is switched, the domain after), so links meant for other sites to read, like the
# picture shown when a page is shared, always point somewhere that exists. Locally, site.json's "url" is used.
SITE["url"] = (os.environ.get("SITE_URL") or SITE["url"]).rstrip("/")
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


def mailto(subject="", to=""):
    """An email link. `to` names an address under "emails" in site.json (one per service, so
    enquiries arrive already sorted); anything else goes to the main address."""
    return "mailto:" + (SITE.get("emails", {}).get(to) or SITE["email"]) + ("?subject=" + quote(subject) if subject else "")


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


SHARE_ALT = {"home": "The studio desk: monitor, speakers and keyboard, lit warm in a dark room",
             "film": "Justin at the desk with a film's sound session on the monitor",
             "music": "Justin singing at a studio microphone",
             "podcasts": "A studio microphone, headphones and a speaker"}


def share_image(page):
    """The picture other sites and apps show when a page's link is shared (messages, LinkedIn, Slack...):
    static/img/share-<page>.jpg, 1200 x 630. Without one, each app guesses and keeps its guess for a long time.
    The address carries a short fingerprint of the file, so replacing the picture gives it a new address
    and apps fetch it afresh instead of showing their saved copy."""
    f = STATIC / "img" / ("share-%s.jpg" % page)
    if not f.exists():
        f = STATIC / "img" / "share-home.jpg"
        if not f.exists():
            return ""
    src = "%s/img/%s?v=%s" % (SITE["url"], f.name, hashlib.sha1(f.read_bytes()).hexdigest()[:8])
    alt = e(SHARE_ALT.get(f.name[6:-4], ""))
    return ('<meta property="og:image" content="%s">\n<meta property="og:image:width" content="1200">\n'
            '<meta property="og:image:height" content="630">\n<meta property="og:image:alt" content="%s">\n'
            '<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:image" content="%s">\n' % (src, alt, src))


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
    foot = "".join('<li><a href="%s" target="_blank" rel="noopener">%s<span class="sr-only"> (opens in a new tab)</span></a></li>' % (e(links[k]), label)
                   for k, label in (("instagram", "Instagram"), ("imdb", "IMDb"), ("linkedin", "LinkedIn"))
                   if links.get(k))
    for k in ("imdb", "linkedin"):
        if not links.get(k):
            missing("link: " + k)
    path = "" if page == "home" else page
    csp = ("default-src 'self'; script-src 'self'; style-src 'self'; "
           "font-src 'self'; img-src 'self' data: https://i.ytimg.com; "
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
<meta property="og:site_name" content="{site_name}">
{share}<link rel="icon" href="favicon.ico" sizes="48x48">
<link rel="icon" href="icon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="preload" href="fonts/inter-400.woff" as="font" type="font/woff" crossorigin>
<link rel="preload" href="fonts/oswald.woff" as="font" type="font/woff" crossorigin>
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
<span>&copy; 2026 {legal}. {loc}.{privacy}</span>
<div class="foot-side">
<span class="foot-mail">{mail_label} <a class="foot-addr" href="mailto:{mail_plain}">{mail_plain}</a></span>
<ul class="foot-links" role="list">{foot}</ul>
</div>
</div>
</footer>
</body>
</html>
""".format(csp=csp, title=e(title), desc=e(description), url=SITE["url"], path=path, page=page,
           site_name=e(SITE["name"]), share=share_image(page),
           mail_label=e(PAGES["shared"].get("footer_email", "Email:")), mail_plain=e(SITE["email"]),
           defs=wave_defs(), ver=VERSION, nav=nav, logo=logo(), skip=e(PAGES["shared"]["skip_link"]),
           menu_button=e(PAGES["shared"]["menu_button"]), mail=mailto("", page), wave=WAVE_USE, body=body,
           legal=e(SITE["legal_name"]), loc=e(SITE["location"]), foot=foot,
           privacy=(' <a class="foot-privacy" href="privacy.html"%s>%s</a>' % (' aria-current="page"' if page == "privacy" else "", e(PAGES["privacy"].get("footer_link", "Privacy")))
                    if PAGES.get("privacy") else ""))


def section(inner, cls="", sid=""):
    return '<section class="band %s"%s><div class="wrap">%s</div></section>' % (
        cls, ' id="%s"' % sid if sid else "", inner)


def heading(eyebrow, h2=""):
    return '<p class="eyebrow">%s</p>' % eyebrow + ('<h2>%s</h2>' % h2 if h2 else "")


def clock(value, fps=0):
    """"1:05" or 65 -> seconds. With fps (the reel's frame rate) a time with colons is read as an editor's
    timecode, whose last number is frames: at 24, "44:19" is 44 seconds 19 frames, "1:02:00" is 1 minute 2 seconds."""
    parts = [float(x) for x in str(value or 0).split(":")]
    frames = parts.pop() / fps if fps and len(parts) > 1 else 0
    return sum(x * 60 ** i for i, x in enumerate(reversed(parts))) + frames


FULL = ('<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def film_reel():
    """The sound reel under the Film & Games banner: the whole 16:9 picture, centred, its edges
    fading into the page, one marker per film underneath.
    Left out entirely until "reels" > "film" > "video" in site.json names a file in static/video
    (or a full address). "chapters" is optional: without it there is one plain progress line.
    Each chapter gives its "duration" ("0:22", "1:05.5"): the clips are taken in the order listed and each
    one's starting point is added up from the ones before it, so reordering or adding a clip needs no
    other edits. A "start" on a chapter is still honoured and overrides the running count.
    With "fps" set on the reel (e.g. 24), times are read as timecode copied from the editor: "44:19" is
    44 seconds and 19 frames.
    A chapter may carry "link" (an address, e.g. the film's official trailer) and "link_text": the link
    shows beside the title while that chapter plays, and opens in a new tab."""
    r = SITE["reels"].get("film") or {}
    if isinstance(r, str):
        r = {"video": r}
    src = r.get("video")
    if not src:
        missing("video: sound reel")
        return ""
    if src.startswith("http"):
        u = urlparse(src)
        MEDIA_HOSTS.add(u.scheme + "://" + u.netloc)
    else:
        if not (STATIC / "video" / src).exists():
            missing("video file not found: static/video/" + src)
        src = "video/" + src
    label = r.get("label") or "Sound reel"
    poster = r.get("thumbnail") or r.get("poster") or "reel-film.jpg"      # the thumbnail: the picture shown until play is pressed
    poster = ' poster="img/%s"' % e(poster) if (STATIC / "img" / poster).exists() else ""
    chapters = [c for c in r.get("chapters", []) if c.get("title")]
    fps = float(r.get("fps") or 0)                        # set: times are timecode, as the editor shows them (last number = frames)
    at = 0.0                                              # where the next clip begins, counted up from the durations
    for c in chapters:
        for key in ("start", "duration"):
            t = str(c.get(key) or "")
            if fps and ":" in t and float(t.split(":")[-1]) >= fps:
                missing('sound reel: "%s" has %s frames in "%s", but "fps" is %g' % (c["title"], t.split(":")[-1], t, fps))
        if c.get("start") not in (None, ""):              # a written "start" wins, and the count carries on from it
            at = clock(c["start"], fps)
        elif at < 0:
            missing('sound reel: "%s" needs a "start", or a "duration" on the clip before it' % c["title"])
            at = 0.0
        c["_at"] = at
        at = at + clock(c["duration"], fps) if c.get("duration") not in (None, "") else -1.0
    if any(b["_at"] <= a["_at"] for a, b in zip(chapters, chapters[1:])):
        missing("sound reel: chapter times are not in order")
    link_text = PAGES["film"].get("reel_link", "Watch the trailer")
    first = chapters[0] if chapters else {}
    link = ('<a class="rs-link" href="%s" target="_blank" rel="noopener"%s><span class="rs-link-text">%s</span>%s'
            '<span class="sr-only"> (opens in a new tab)</span></a>'
            % (e(first.get("link", "")), "" if first.get("link") else " hidden", e(first.get("link_text") or link_text), EXTERNAL)
            if any(c.get("link") for c in chapters) else "")
    if chapters:
        segs = "".join(
            '<button class="rs-seg" type="button" data-start="%g" data-title="%s" data-role="%s"%s aria-label="Jump to %s">'
            '<i></i><span><em>%02d</em>%s</span></button>'
            % (c["_at"], e(c["title"]), e(c.get("role", "")),
               ' data-link="%s" data-link-text="%s"' % (e(c["link"]), e(c.get("link_text") or link_text)) if c.get("link") else "",
               e(c["title"]), n, e(c["title"]))
            for n, c in enumerate(chapters, 1))
    else:
        segs = '<button class="rs-seg rs-seek" type="button" data-start="0" aria-label="Skip to this point in the reel"><i></i></button>'
    html = ('<section class="reelband" id="reel" aria-label="%s"><div class="rs">'
            '<div class="rs-pic"><video class="rs-video" src="%s"%s preload="metadata" playsinline controls></video>'
            '<button class="play rs-play" type="button" aria-label="Play the %s">%s</button></div>'
            '<div class="rs-ui"><div class="rs-row rs-head"><span class="rs-kicker">%s</span><span class="rs-title">%s</span></div>'
            '<div class="rs-row"><span class="rs-role">%s</span>@@LINK@@<span class="rs-time">0:00</span>@@VOL@@'
            '<button class="rs-full" type="button" aria-label="Full screen" aria-pressed="false">%s</button></div>'
            '<div class="rs-chapters">%s</div><p class="rs-error" role="alert" hidden>This video didn’t load. Try again in a moment.</p>'
            '</div></div></section>'
            % (e(label), e(src), poster, e(label.lower()), PLAY, e(label),
               e(chapters[0]["title"]) if chapters else "", e(chapters[0].get("role", "")) if chapters else "", FULL, segs))
    return html.replace("@@VOL@@", VOLCTL).replace("@@LINK@@", link)


def player(title, sub, src, label, foot="", extra=""):
    """One audio sample: play button, title, time. `extra` is an optional third line in the details
    (the role tags); `foot` an optional line under the progress bar (a callout)."""
    if not src:
        missing("audio: " + label)
        if not SHOW:
            return ""
    off = "" if src else " disabled"
    return ('<div class="player%s%s" data-src="%s" data-label="%s">'
            '<button class="play" type="button" aria-label="Play %s"%s>%s</button>'
            '<div class="player-meta"><div class="player-title">%s</div><div class="player-sub">%s</div>%s</div>'
            '<span class="player-time">0:00</span>'
            '<input class="player-seek" type="range" min="0" max="1000" value="0" aria-label="Position in %s"%s>%s</div>'
            % ("" if src else " slot", " player-rich" if extra else "", e(media(src)) if src else "", e(label), e(label), off, PLAY, title, sub, extra,
               e(label), off, foot))


def _icon(shapes):
    return ('<svg class="callout-icon" aria-hidden="true" viewBox="0 0 16 16" fill="none" stroke="currentColor" '
            'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">%s</svg>' % shapes)


# One small icon per kind of callout; "type" in music.json picks it. Add a line here for a new kind.
CALLOUT_ICONS = {
    "streams": _icon('<path d="M1.5 12.5 6 8l3 2.5 5.5-6.5"/><path d="M10.5 4h4v4"/>'),             # rising chart arrow
    "press": _icon('<rect x="1.5" y="2.5" width="13" height="11" rx="1.5"/><path d="M4.5 6h4M4.5 9h7M4.5 11.5h7M11 5.5h.5"/>'),
    "tv": _icon('<rect x="1.5" y="2.5" width="13" height="9" rx="1.5"/><path d="M5.5 14h5"/>'),
    "award": _icon('<path d="m8 1.8 1.9 3.9 4.3.6-3.1 3 .7 4.3L8 11.6l-3.8 2 .7-4.3-3.1-3 4.3-.6z"/>'),
    "listen": _icon('<path d="M6 12.5v-9l7-1.5v8.5"/><circle cx="4.2" cy="12.5" r="1.8"/><circle cx="11.2" cy="10.5" r="1.8"/>'),   # music notes
    "news": _icon('<path d="M8 1.5v3M8 11.5v3M1.5 8h3M11.5 8h3M3.6 3.6l2 2M10.4 10.4l2 2M12.4 3.6l-2 2M5.6 10.4l-2 2"/>'),
}


# "Go to this page": a plain arrow, drawn (not typed) so it is as heavy as the link's lettering and easy to see.
GO = ('<svg class="go-icon" aria-hidden="true" viewBox="0 0 24 16" fill="none" stroke="currentColor" stroke-width="2.6" '
      'stroke-linecap="round" stroke-linejoin="round"><path d="M2 8h20M17 3l5 5-5 5"/></svg>')
# The usual "leaves this site" mark: a box with an arrow out of its top-right corner.
EXTERNAL = ('<svg class="ext-icon" aria-hidden="true" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7" '
            'stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 2.5h4v4M13.5 2.5l-6 6M11.5 9.5v3a1 1 0 0 1-1 1h-7a1 1 0 0 1-1-1v-7'
            'a1 1 0 0 1 1-1h3"/></svg>')


def callout_line(tr, words):
    """The line under a sample's progress bar when its track has a "callout" in music.json:
    {"type": which icon, "showcase": the part in white ("200,000+"), "description": the rest
    ("streams on Spotify"), "link": an address (optional), "link_text": the link's words (optional;
    otherwise the usual words for that type from pages.json)}.
    A callout holding only a "link" becomes a plain line inviting the visitor to hear the full track."""
    c = dict(tr.get("callout") or {})
    if not (c.get("showcase") or c.get("description")):
        if not c.get("link"):
            return ""
        # a link and nothing else: a plain "hear the full track" line
        c.setdefault("type", "listen")
        c["description"] = words.get("listen_line", "Hear the full track")
    kind = c.get("type") or "news"
    if kind not in CALLOUT_ICONS:
        missing("callout type not recognised (using the general icon): " + kind)
    links = words.get("callout_links", {})
    link = ('<a href="%s" target="_blank" rel="noopener">%s%s<span class="sr-only"> (opens in a new tab)</span></a>'
            % (e(c["link"]), t(c.get("link_text") or links.get(kind) or links.get("other") or "See more"), EXTERNAL)
            if c.get("link") else "")
    showcase = "<b>%s</b> " % e(c["showcase"]) if c.get("showcase") else ""
    return ('<p class="player-foot"><span>%s%s%s</span>%s</p>'
            % (CALLOUT_ICONS.get(kind, CALLOUT_ICONS["news"]), showcase, t(c.get("description", "")), link))


# A small volume control for a single player: a speaker icon and a slider. site.js keeps every one of
# these, and the Music page's master fader, on the same setting. Hidden on phones and tablets.
VOLCTL = ('<span class="volctl"><span class="volctl-icon" aria-hidden="true"></span>'
          '<input class="volctl-range" type="range" min="0" max="100" value="75" aria-label="Volume"></span>')


def master_strip(words):
    """The Music page's master fader: sets the volume for every player and shows the level of whatever
    is playing. site.js drives it; it is left out on phones and tablets. The scale goes to 11."""
    meter = '<div class="m-meter">%s</div>' % ("<i></i>" * 18)
    scale = "".join('<span data-n="%d">%d</span>' % (n, n) for n in (11, 10, 8, 6, 4, 2, 0))
    return ('<aside class="master" aria-label="%s"><div class="m-top" aria-hidden="true"><span>%s</span><i class="m-led"></i></div>'
            '<div class="m-body"><div class="m-scale" aria-hidden="true">%s</div>'
            '<div class="m-fader" role="slider" tabindex="0" aria-orientation="vertical" aria-label="%s" aria-valuemin="0" aria-valuemax="100" aria-valuenow="75" aria-valuetext="75%%">'
            '<i class="m-cap"></i></div><div class="m-meters" aria-hidden="true">%s%s</div></div>'
            '<div class="m-name" aria-hidden="true">%s</div><p class="m-read" aria-hidden="true">75%%</p></aside>'
            % (e(words.get("volume_label", "Volume")), e(words.get("master_label", "Master")), scale, e(words.get("volume_label", "Volume")),
               meter, meter, e(words.get("volume_label", "Volume"))))


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
            '<span class="ab-time">0:00</span>%s</div><p class="ab-error" role="alert" hidden></p></div>'
            % ("" if ready else " slot", name, data, title, note, name, off, PLAY, off, off, name, off, VOLCTL if ready else ""))


STAR = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="m8 1.3 2 4.2 4.6.6-3.4 3.2.9 4.6L8 11.7 3.9 13.9l.9-4.6L1.4 6.1 6 5.5z"/></svg>'
CHEVRON = ('<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
           'aria-hidden="true"><path d="%s"/></svg>')


def star_row(n):
    """The rating a review was given on its platform, out of 5. Left out when quotes.json gives none."""
    try:
        n = max(0, min(5, int(n)))
    except (TypeError, ValueError):
        return ""
    if not n:
        return ""
    return ('<div class="stars" role="img" aria-label="%d out of 5 stars">%s%s</div>'
            % (n, STAR * n, '<span class="stars-off">%s</span>' % (STAR * (5 - n)) if n < 5 else ""))


def credit(q):
    """A quote's role and project, e.g. Director, <i>Film Title</i>."""
    return ", ".join(x for x in (e(q.get("role", "")), '<i class="quote-project">%s</i>' % e(q["project"]) if q.get("project") else "") if x)


def quotes(page, eyebrow, look="band-dots", reviews_line="", sid=""):
    """Client quotes for one page; the section appears once quotes.json has at least one quote for the page.
    A page with exactly one quote shows it as a single featured quote. With more, three are in view (two on
    tablets, one on phones) with the arrows there from the start, and the row loops once there are enough.
    Each quote may carry "stars" (1 to 5, as given on the platform), "source" (the platform's name) and
    "project" (the film, show or record it was for, set in italics after the role).
    reviews_line is that page's own line under the quotes, if it has one; sid gives the section an id to link to."""
    items = [q for q in QUOTES if page in q.get("pages", [])]
    filled = [q for q in items if q.get("quote")]
    if len(filled) < len(items):
        missing("client quotes for the %s page (%d of %d written)" % (page, len(filled), len(items)))
    if not filled:      # no quotes written for this page yet: leave the whole section out, drafts included
        return ""
    show = items if SHOW else filled
    w = PAGES["shared"].get("reviews", {})
    line = '<p class="reviews">%s</p>' % t(reviews_line) if reviews_line else ""
    if len(show) == 1:  # one quote: featured on its own, no row and no arrows
        q = show[0]
        who = "".join(x for x in (
            "<b>%s</b>" % e(q["name"]) if q.get("name") else "",
            "<span>%s</span>" % credit(q) if credit(q) else "",
            '<span class="quote-src">%s %s</span>' % (e(w.get("via", "via")), e(q["source"])) if q.get("source") else ""))
        fig = ('<figure class="quote-solo">%s<span class="qs-mark" aria-hidden="true">&ldquo;</span><blockquote>%s</blockquote>'
               '<span class="qs-rule" aria-hidden="true"></span><figcaption>%s</figcaption></figure>'
               % (star_row(q.get("stars")), e(q["quote"]) if q.get("quote") else '<span class="todo">[client quote]</span>',
                  who or '<span class="todo">[name, role or project]</span>'))
        return section(heading(eyebrow) + fig + (line and '<div class="rv-bar">%s</div>' % line), look + " quote-one", sid)
    figs = "".join(
        '<figure class="quote">%s<blockquote>&ldquo;%s&rdquo;</blockquote><figcaption>%s%s</figcaption></figure>'
        % (star_row(q.get("stars")),
           e(q["quote"]) if q.get("quote") else '<span class="todo">[client quote]</span>',
           ", ".join(x for x in (e(q.get("name", "")), credit(q)) if x) or '<span class="todo">[name, role or project]</span>',
           '<span class="quote-src">%s %s</span>' % (e(w.get("via", "via")), e(q["source"])) if q.get("source") else "")
        for q in show)
    controls = ('<div class="rv-controls"><button class="rv-prev" type="button" aria-label="%s">%s</button>'
                '<span class="rv-count sr-only" aria-live="polite"></span>'
                '<button class="rv-next" type="button" aria-label="%s">%s</button></div>'
                % (e(w.get("previous", "Previous reviews")), CHEVRON % "M10 3 5 8l5 5",
                   e(w.get("next", "More reviews")), CHEVRON % "m6 3 5 5-5 5"))
    return section(heading(eyebrow) + '<div class="rv" data-full="%s" data-less="%s" data-of="%s" data-showing="%s"><div class="rv-track" tabindex="0" role="group" aria-label="%s">%s</div>'
                   '<div class="rv-bar">%s%s</div></div>'
                   % (e(w.get("read_full", "Read full review")), e(w.get("read_less", "Show less")), e(w.get("of", "of")), e(w.get("showing", "Showing reviews")),
                      e(eyebrow_text(eyebrow)), figs, line or "<span></span>", controls), look, sid)


def eyebrow_text(html):
    return re.sub(r"<[^>]+>", "", html)


def contact_band(h2, text, button, subject="", blend=False, to=""):
    """The contact band. blend=True drops its top line, for a page whose last section
    fades into the band's own colours (fade-ember)."""
    return ('<section class="band band-cta%s"><div class="wrap cta-row"><div><h2>%s</h2><p>%s</p></div>'
            '<a class="btn" href="%s">%s</a></div></section>' % (" seamless" if blend else "", h2, text, mailto(subject, to), button))


def credit_cards(items):
    """Film credits. A credit with "hidden": true in credits.json is left off the site
    (and out of the page source) until that line is removed or set to false. A credit with no
    "poster" gets a title card in the poster's place, showing its "status" if it has one."""
    cards = []
    for c in items:
        if c.get("hidden"):
            missing("hidden for now: credit " + c["title"])
            continue
        if c.get("poster"):
            poster = image("posters/" + c["poster"], "Poster: " + c["title"], "poster", "Poster: " + c["title"])
        else:           # no poster yet: a title card in the poster's place, with the optional "status" line
            poster = ('<div class="poster title-card"><b aria-hidden="true">%s</b><span class="tc-rule" aria-hidden="true"></span>%s</div>'
                      % (e(c["title"]), "<em>%s</em>" % e(c["status"]) if c.get("status") else ""))
        clip = ('<button class="play poster-play" type="button" data-video="%s" aria-label="Watch a clip from %s (opens in a new tab)">%s</button>'
                % (e(c["clip"]), e(c["title"]), PLAY)) if c.get("clip") else ""
        cards.append('<li class="credit"><div class="poster-wrap">%s%s</div><p class="credit-title">%s '
                     '<span>(%s)</span></p><p class="credit-role">%s</p></li>'
                     % (poster, clip, e(c["title"]), e(c["year"]), e(c["role"])))
    return '<ul class="grid credits" role="list">%s</ul>' % "".join(cards) if cards else ""


def steps(items):
    return '<ol class="grid steps" role="list">%s</ol>' % "".join(
        '<li class="step"><div class="step-n" aria-hidden="true">%d</div><h3>%s</h3><p>%s</p></li>' % (i, h, p)
        for i, (h, p) in enumerate(items, 1))


def cards(items):
    return '<div class="grid cards">%s</div>' % "".join(
        '<div class="card"><h3>%s</h3><p>%s</p>%s</div>' % (h, p, extra) for h, p, extra in items)


def filmstrip(items, hint="Swipe"):
    """Film & Games 'How it works': each stage is a frame on a strip of film."""
    frames = "".join(
        '<li class="frame"><div class="frame-mark" aria-hidden="true"><span>REEL 1</span><span>FRAME %02d</span></div>'
        '<h3>%s</h3><p>%s</p></li>' % (i, h, p) for i, (h, p) in enumerate(items, 1))
    # On narrower screens the strip scrolls sideways; site.js adds the dots and makes it reachable by keyboard.
    hint = e(hint)
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


def ask_button(label, name, subject, ghost=True, to=""):
    """A card's enquiry button, always on two lines: the label, then the thing asked about."""
    return ('<a class="btn btn-ask%s" href="%s"><span>%s</span> <span>%s</span></a>'
            % (" btn-ghost" if ghost else "", mailto(subject, to), label, e(name)))


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
    return ('<section class="hero hero-%s">%s<div class="hero-shade"></div>%s<div class="wrap hero-row%s"><div class="hero-text">'
            '<p class="eyebrow">%s</p><h1>%s</h1><p class="lead">%s</p>%s</div>'
            '%s</div></section>' % (page, bg, pause, (" stack" if page in STACKED_HEROES else "") if side else " solo", eyebrow, h1, lead,
                                    '<div class="btn-row">%s</div>' % btns if btns else "", side_html))


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
    text = re.sub(r"(?<!\w)_(?=\S)(.+?)(?<=\S)_(?!\w)", r"<em>\1</em>", text)      # _italics_, e.g. the title of a show or film
    return re.sub(r"\*(.+?)\*", r'<span class="hi">\1</span>', text)


def banner_buttons(b, first_href, subject=""):
    """The banner's buttons, from pages.json: "button" (jumps down the page) and "second_button" (email).
    Leave either out of pages.json and it is not shown; leave both out and the banner has no buttons."""
    out = []
    if b.get("button"):
        out.append((first_href, t(b["button"])))
    if b.get("second_button"):
        out.append((mailto(b.get("email_subject", subject), b.get("email_to", "")), t(b["second_button"])))
    return out


def contact(c, blend=False):
    return contact_band(t(c["heading"]), t(c["text"]), t(c["button"]), c.get("email_subject", ""), blend, c.get("email_to", ""))


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
                      '<p>%s</p><a class="go" href="%s">%s%s</a></div></div>'
                      % (image("tile-%s.jpg" % key, "", "tile-img tile-img-%s" % key, "Photo: " + slots[key]), t(tile["name"]), btn,
                         t(tile["text"]), hrefs[key], t(tile["link"]), GO))
    b = p["banner"]
    body = hero("home", t(b["label"]), t(b["headline"]), t(b["text"]), banner_buttons(b, "#paths"),
                "", "", "Background: a muted video loop or photo of the studio")
    body += section(heading(t(p["paths"]["label"]), t(p["paths"]["heading"])) + '<div class="grid tiles">%s</div>' % tile_html,
                    "band-rings rings-side fade-in", "paths")
    body += quotes("home", t(p["quotes_label"]), "band-foam foam-fade band-line")
    a = p["about"]
    about_btn = '<a class="btn btn-ghost" href="%s">%s</a>' % (mailto(), t(a["button"])) if a.get("button") else ""   # optional: the contact band sits right under this section
    body += section('<div class="about">%s<div class="about-text">%s%s%s</div></div>'
                    % (image("portrait.jpg", "Justin at the studio desk", "portrait", "Portrait: Justin at the desk or the mic"),
                       heading(t(a["label"]), t(a["heading"])), "".join("<p>%s</p>" % t(x) for x in a["paragraphs"]),
                       about_btn), "glow-tr band-line", "about")
    body += contact(p["contact"])
    return layout("home", p["browser_title"], p["search_description"], body)


def film():
    p = PAGES["film"]
    imdb = SITE["links"].get("imdb")
    b = p["banner"]
    sound_reel = film_reel()
    body = hero("film", t(b["label"]), t(b["headline"]), t(b["text"]),
                banner_buttons(b, "#reel" if sound_reel else "#credits", p["contact"].get("email_subject", "")),
                "", "", "Background: a darkened film still, or the mix session on screen")
    body += sound_reel
    c = p["credits"]
    shown = credit_cards(CREDITS)
    if shown:       # with every credit hidden, the whole section is left out
        body += section('<div class="split-head"><div>%s</div>%s</div>%s' % (
            heading(t(c["label"]), t(c["heading"])),
            '<a href="%s" target="_blank" rel="noopener">%s%s<span class="sr-only"> (opens in a new tab)</span></a>'
            % (e(imdb), t(c["link"]), EXTERNAL) if imdb else "",
            shown), "glow-br", "credits")      # glow kept low: the top stays dark under the banner's fade
    s = p["services"]
    body += section(heading(t(s["label"]), t(s["heading"])) + cards([(t(i["title"]), t(i["text"]), "") for i in s["items"]]),
                    "band-timeline band-line")
    s = p["steps"]
    body += section(heading(t(s["label"]), t(s["heading"])) + filmstrip([(t(i["title"]), t(i["text"])) for i in s["items"]], s.get("swipe_hint", "Swipe")),
                    "glow-bl")       # no line: what I do runs straight into how it works
    body += quotes("film", t(p["quotes_label"]), "band-foam foam-fade band-line")
    body += contact(p["contact"])
    return layout("film", p["browser_title"], p["search_description"], body)


def sample_player(tr, words):
    """A music sample. The bold title is the genre, so visitors can find the samples nearest their own
    music; under it the song and artist on one line, then one tag per role."""
    song = val(tr.get("title"), "track title")
    artist = e(tr["artist"]) if tr.get("artist") else ("" if tr.get("src") else val("", "artist"))
    line = '<span class="player-song">%s</span>%s' % (song, ' <span class="player-artist">%s</span>' % artist if artist else "")
    roles = tr.get("roles") or ([tr["role"]] if tr.get("role") else [])
    if not roles:
        missing("your role on: " + (tr.get("title") or "a music sample"))
    tags = ('<ul class="player-roles" role="list" aria-label="%s">%s</ul>'
            % (e(words.get("roles_label", "My role")), "".join("<li>%s</li>" % e(r) for r in roles)) if roles else "")
    name = " ".join(x for x in (tr.get("genre", "") + ":" if tr.get("genre") else "", tr.get("title"),
                                "by " + tr["artist"] if tr.get("artist") else "") if x) or "sample"
    return player(val(tr.get("genre"), "genre"), line, tr.get("src"), name, callout_line(tr, words), tags)


def hidden_track(tr):
    """A sample with "hidden": true in music.json stays off the page (and out of the page source)
    until that is removed or set to false. Its audio file should not be in static/audio meanwhile:
    everything in that folder is published whether or not a page uses it."""
    if tr.get("hidden"):
        missing("hidden for now: music sample " + (tr.get("title") or "(untitled)"))
        if tr.get("src") and not tr["src"].startswith("http") and (STATIC / "audio" / tr["src"]).exists():
            missing("hidden sample's file is still in static/audio and will be published: " + tr["src"])
        return True
    return False


def music():
    p = PAGES["music"]
    b = p["banner"]
    # "show_banner_reel": false in music.json leaves the banner without a player.
    side = ""
    if MUSIC.get("show_banner_reel", True):
        side = '<div class="reel-audio">%s</div>' % player(t(p["reel"]["title"]), t(p["reel"]["text"]), MUSIC.get("reel"), "singing reel")
    body = hero("music", t(b["label"]), t(b["headline"]), t(b["text"]), banner_buttons(b, "#services"),
                "", "", "Background: you singing at the mic, on the right third")
    body = body.replace('<div class="btn-row">', side + '<div class="btn-row">', 1) if side else body
    # The reviews sit straight after the samples, and the banner links down to them: five stars and
    # the banner's own "reviews_link" line. Stars and words wrap as two whole lines when they don't fit on one.
    music_quotes = quotes("music", t(p["quotes_label"]), "band-foam foam-fade band-line", p.get("reviews_line", ""), "reviews")
    if music_quotes and b.get("reviews_link"):
        proof = ('<p class="hero-proof"><a href="#reviews"><span class="hp-stars" aria-hidden="true">&#9733;&#9733;&#9733;&#9733;&#9733;</span>'
                 '<span class="hp-text">%s <span class="hp-down" aria-hidden="true">&darr;</span></span></a></p>' % t(b["reviews_link"]))
        body = body.replace('</div></div></section>', proof + '</div></div></section>', 1)      # last thing in the banner's text column
    groups = ""
    for style in MUSIC["styles"]:
        rows = "".join(sample_player(tr, p["listen"]) for tr in style["tracks"] if not hidden_track(tr))
        if rows:
            groups += '<div class="style"><h3>%s</h3>%s</div>' % (e(style["name"]), rows)
    spotify = SITE["links"].get("spotify")
    if not spotify:
        missing("link: spotify")
    li = p["listen"]
    body += section(heading(t(li["label"]), t(li["heading"]))
                    + '<div class="listen-row"><div class="grid styles">%s</div>%s</div>' % (groups, master_strip(li))
                    + ('<p class="aside">%s <a href="%s" target="_blank" rel="noopener">%s%s<span class="sr-only"> (opens in a new tab)</span></a>.</p>'
                       % (t(li["spotify_line"]), e(spotify), t(li["spotify_link"]), EXTERNAL) if spotify else ""), "band-spectro spectro-join", "listen")
    body += music_quotes
    # Services is the page's pricing section, so it takes the dots (kept for pricing) and plain cards
    # like the podcast packages, with the same "Before you ask" questions under it.
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
                   ask_button(t(sv["button"]), s["name"], "Music: " + s["name"], to=s.get("email_to", ""))))
    body += section(heading(t(sv["label"]), t(sv["heading"])) + '<div class="grid packs">%s</div>' % svc
                    + '<p class="aside">%s</p>' % t(sv["note"]), "band-dots fade-out", "services")
    if MUSIC.get("questions"):
        q = p["questions"]
        body += section(heading(t(q["label"]), t(q["heading"])) + '<div class="grid faq">%s</div>' % "".join(
            "<div><h3>%s</h3><p>%s</p></div>" % (e(x["q"]), e(x["a"])) for x in MUSIC["questions"]), "")
    th = p["theater"]
    body += section('<div class="about"><div class="about-text">%s<p>%s</p><a class="btn" href="%s">%s</a></div>%s</div>'
                    % (heading(t(th["label"]), t(th["heading"])), t(th["text"]), mailto(th.get("email_subject", ""), th.get("email_to", "")), t(th["button"]),
                       image("theater.jpg", "A score on the music stand", "wide-img", "Photo: a score on the stand, or recording a cast number")),
                    "band-notes fade-ember")
    body += contact(p["contact"], blend=True)      # the theater section fades out into the contact band
    return layout("music", p["browser_title"], p["search_description"], body)


def podcasts():
    p = PAGES["podcasts"]
    b = p["banner"]
    samples = PODCASTS["samples"]
    first = ab_player(samples[0], 1) if samples else ""
    body = hero("podcasts", t(b["label"]), t(b["headline"]), t(b["text"]), banner_buttons(b, "#packages"),
                "", "", "Background: your editing screen with a podcast waveform, headphones in frame")
    # The first before-and-after sample has its own section under the banner: words on the left,
    # the player on the right, over a waveform that runs from rough (before) to clean (after).
    if first:
        sm = p["sample"]
        body += section('<div class="sample"><div>%s<p class="sample-lead">%s</p></div><div class="sample-player">%s</div></div>'
                        % (heading(t(sm["label"]), t(sm["heading"])), t(sm["hint"]), first),
                        "band-ba", "sample")
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
                     items, ask_button(t(pk["button"]), pack["name"], "Podcast: " + pack["name"], not pack.get("highlight"), "podcasts")))
    body += section(heading(t(pk["label"]), t(pk["heading"])) + '<div class="grid packs">%s</div>' % packs
                    + '<p class="aside">%s</p>' % t(pk["note"]), look_packages, "packages")
    q = p["questions"]
    body += section(heading(t(q["label"]), t(q["heading"])) + '<div class="grid faq">%s</div>' % "".join(
        "<div><h3>%s</h3><p>%s</p></div>" % (e(x["q"]), e(x["a"])) for x in PODCASTS["questions"]), "")      # plain black; questions follow on from the prices
    body += contact(p["contact"])
    return layout("podcasts", p["browser_title"], p["search_description"], body)


def not_found():
    p = PAGES["not_found"]
    return layout("404", p["browser_title"], p["text"],
                  section('<h1>%s</h1><p class="lead">%s</p><div class="btn-row"><a class="btn" href="index.html">%s</a></div>'
                          % (t(p["heading"]), t(p["text"]), t(p["button"])), "glow-tr"))


def privacy():
    """The privacy note: plain text, linked from the footer. All of its words are under "privacy" in pages.json;
    take that block out and the page and its footer link both go. A part may carry "link" and "link_text"
    (shown after its text, opening in a new tab); the last line is followed by the main email address."""
    p = PAGES["privacy"]
    parts = ""
    for x in p["parts"]:
        link = (' <a href="%s" target="_blank" rel="noopener">%s%s<span class="sr-only"> (opens in a new tab)</span></a>.'
                % (e(x["link"]), t(x.get("link_text", x["link"])), EXTERNAL)) if x.get("link") else ""
        parts += "<h2>%s</h2><p>%s%s</p>" % (t(x["heading"]), t(x["text"]), link)
    ask = '<p>%s <a href="mailto:%s">%s</a>.</p>' % (t(p["contact"]), e(SITE["email"]), e(SITE["email"])) if p.get("contact") else ""
    updated = '<p class="prose-date">%s</p>' % t(p["updated"]) if p.get("updated") else ""
    return layout("privacy", p["browser_title"], p["search_description"],
                  section('<div class="prose"><h1>%s</h1><p class="lead">%s</p>%s%s%s</div>'
                          % (t(p["heading"]), t(p["intro"]), parts, ask, updated), "glow-tr"))


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT, ignore=shutil.ignore_patterns(".DS_Store"))
    pages = {"index.html": home(), "film.html": film(), "music.html": music(),
             "podcasts.html": podcasts(), "404.html": not_found()}
    if PAGES.get("privacy"):
        pages["privacy.html"] = privacy()
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
