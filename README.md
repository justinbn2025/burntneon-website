# Burnt Neon Productions website

A static site: plain HTML, CSS and one small script. No server, database, login or
third-party builder, so there is very little to attack and nothing to pay for.

## See it on your computer

    python3 build.py
    open _site/index.html

Opened this way (straight from the file), the podcast before/after players cannot load and the
Music page's volume meters stay dark, because browsers restrict audio in files opened directly.
To hear and see everything as visitors will, serve the folder instead and open
<http://localhost:8000>:

    python3 -m http.server 8000 --directory _site

`build.py` uses only what ships with Python. It prints a list of everything still
to fill in.

## Update the site

Every word on the site is in `content/`. Never edit `_site/`: it is rebuilt from
scratch each time and your changes there are lost.

| To change                                   | Edit                    |
|---------------------------------------------|-------------------------|
| Headlines, paragraphs, button and menu text | `content/pages.json`    |
| Film credits, posters, clip links           | `content/credits.json`  |
| Client quotes                               | `content/quotes.json`   |
| Music samples, reels, prices, review count  | `content/music.json`    |
| Podcast samples, packages, prices, questions| `content/podcasts.json` |
| Email, links, reels, reply time             | `content/site.json`     |

Then run `python3 build.py`, look at the result, commit and push. The push
publishes it (see "Publishing").

In `pages.json`:

- `*asterisks*` around words colour them orange (headlines).
- `{reply_days}`, `{turnaround_days}`, `{revision_rounds}` and `{review_count}` are
  filled in from `site.json`, `music.json` and `podcasts.json`.
- A part in `[square brackets]` is left out of the page while the number it needs
  is still empty (once placeholders are switched off).
- If an edit breaks the file, the build stops and names the line.

Examples:

- **Add a film credit:** copy one `{ ... }` block in `credits.json`, change the
  text, and put the poster in `static/img/posters/` (vertical, 2:3, about 800 px
  wide). `"on_home": true` also shows it on the Home page.
  A credit with no `"poster"` shows a title card in the poster's place: the film's title in
  type, with the optional `"status"` line under it (for example `"In post-production"`). Add
  the poster's file name later and the card is replaced by the poster.
- **Hide a credit for now:** add `"hidden": true` to its block in `credits.json` (for work
  or permission still pending). It stays off the site until you remove that line or set it
  to `false`; the build lists hidden credits as a reminder.
- **Hide a music sample for now:** add `"hidden": true` to its line in `music.json`, and keep
  its audio file out of `static/audio/` until it can go up: everything in that folder is
  published even if no page uses it. The build warns if a hidden sample's file is still there.
- **Add a callout to a music sample** (a stream count, press, a TV credit): add a `"callout"`
  to its line in `music.json`, for example
  `"callout": { "type": "streams", "showcase": "200,000+", "description": "streams on Spotify", "link": "" }`.
  It appears as a line under that sample's progress bar. `"type"` picks the icon: `streams`
  (rising chart), `press` (newspaper), `tv` (screen), `award` (star) or `news` (general).
  `"showcase"` is the part shown in white, `"description"` the rest, and `"link"` is optional.
  The link's words come from `pages.json` (`music` > `listen` > `callout_links`), or add
  `"link_text"` to the callout to set them for that one.
  With nothing to announce, a callout holding only a link, `"callout": { "link": "https://..." }`,
  shows a plain "Hear the full track" line with a link out.
- **Add a client review:** copy one `{ ... }` block in `quotes.json`. Put your strongest three
  first: three show at a time, and the arrows reach the rest. Once a page has more than two
  screens' worth (seven or more on a wide screen), the row loops back to the start. A page with
  exactly one quote shows it as a single featured quote, and switches to the row by itself when
  a second is added. Optional fields: `"stars"` (1 to 5, exactly as given on the platform),
  `"source"` (`"Fiverr"`, `"SoundBetter"`) and `"project"` (the film, show or record the work
  was for; it appears in italics after the role). Reviews of about 320 characters or fewer show in
  full; longer ones are cut to eight lines with a "Read full review" link.
- **Add a clip to a credit:** paste the YouTube or Vimeo link into `"clip"`.
- **Add a music sample:** put the MP3 in `static/audio/` and write its file name
  in `"src"`, or paste a full `https://` link to a file hosted elsewhere.
  Each sample has a `"genre"` (its bold title on the page), a `"title"` and `"artist"` (shown
  together on the next line) and `"roles"`, a list such as `["Mixing", "Mastering"]`, shown
  as one tag each.
- **Add a podcast before/after:** fill in `title`, `note`, `before` and `after`.
  The two files must be the same length and start at the same moment.
  Only the first sample shows while `"show_more_samples": false` in
  `podcasts.json`; set it to `true` to bring back the "More examples" section
  for samples 2 and up.

### Placeholders

While `"show_placeholders": true` in `site.json`, anything not filled in shows as
an orange `[placeholder]` or a dashed box. Set it to `false` before going live:
unfilled items are then left out of the pages instead.

### Photos and video

Drop files into `static/img/` with these exact names and they appear on the next
build. Sizes are a guide; JPG at about 80% quality.

| File                 | Where it shows                 | Shape                  |
|----------------------|--------------------------------|------------------------|
| `hero-home.jpg`      | Home banner (and phone fallback) | landscape, 2400 px wide |
| `hero-film.jpg`      | Film & Games banner            | landscape, 2400 px wide |
| `hero-music.jpg`     | Music banner                   | landscape, 2400 px wide |
| `hero-podcasts.jpg`  | Podcasts banner                | landscape, 2400 px wide |
| `tile-film.jpg`, `tile-music.jpg`, `tile-podcasts.jpg` | Home tiles | portrait, 800 px wide |
| `portrait.jpg`       | About                          | portrait 4:5, 900 px wide |
| `theater.jpg`        | Music, theater writers section | landscape 4:3          |
| `reel-film.jpg`      | Still shown on the sound reel before play | 16:9 or wider |
| `posters/<name>.jpg` | Film credits                   | portrait 2:3, 800 px wide |

The Home banner video loop goes in `static/video/hero-home.mp4` (muted, 8 to 10
seconds, under 4 MB).

## Where things are

    build.py            builds the site (layout only; no wording)
    content/            every word, credit, sample, price and link
    static/css/site.css colours, type and layout (colours are set once at the top)
    static/js/site.js   scroll waveform, audio players, video cards
    static/img/         photos and posters
    _site/              the built site (not committed)

## The sound reel (Film & Games)

The reel plays under the Film & Games banner. It stays hidden until a file is named.

1. Put the video in `static/video/` (an `.mp4`, H.264 with AAC sound, under 100 MB) and a still
   for it in `static/img/` (the picture shown, dimmed, until play is pressed).
2. In `content/site.json`, under `"reels"` > `"film"`, fill in `"video"` and `"poster"` with the
   two file names, and one line per clip under `"chapters"`, in the order they play: its
   `"title"`, your `"role"` on it, and its `"duration"` (`"0:22"`, or `"0:22.5"` for half
   seconds). Each clip's marker is worked out by adding up the durations before it, so to add
   or reorder clips, add or move lines and change nothing else. The last clip's duration is
   optional: it runs to the end of the video. (`"start"` still works in place of a duration
   and overrides the running count from that clip on.) Leave `"chapters"` empty for one plain
   line.
   A chapter can also have a `"link"` (a full address, for example the film's official trailer).
   A "Watch the trailer" link then shows beside the title while that chapter plays, and opens
   in a new tab. `"link_text"` changes the wording for that one chapter.

The whole picture is shown, uncropped, in the video's own shape (16:9 or otherwise), centred
in a band that runs the full width of the page: a blurred, dimmed copy of the picture fills the
sides. The picture dims while paused, and a pause button appears when the pointer moves over it.

## Publishing

The site publishes from GitHub Pages using `.github/workflows/deploy.yml`.

1. Create a repo on GitHub and push this folder to its `main` branch.
2. In the repo: Settings > Pages > Source: **GitHub Actions**.
3. Every push to `main` rebuilds and publishes. Until the domain is switched, the
   preview address is `https://<your-user>.github.io/<repo-name>/`.

Going live on burntneonproductions.com (do this last):

1. Settings > Pages > Custom domain: `www.burntneonproductions.com`.
2. At the domain registrar, point the `www` CNAME record at
   `<your-user>.github.io`. Leave the MX (email) records alone.
3. Back in Settings > Pages, tick **Enforce HTTPS** once it is offered.
4. Unpublish the Google Sites version.

If the site ever has to leave GitHub Pages, the plan is in `MIGRATING-TO-CLOUDFLARE.md`.

## Security notes

- Turn on two-factor sign-in for GitHub and for the domain registrar. Those two
  accounts are the only way anyone could change the site.
- Each page carries a Content-Security-Policy that only allows this site's own
  script and styles, Google Fonts, the audio hosts named in `content/`, and
  YouTube/Vimeo players. If you host media somewhere new, the build adds that host
  for audio automatically.
- No cookies, analytics or forms. Contact is by email link. The one thing the site keeps in a
  visitor's browser is their volume setting, and only until they close the tab.
