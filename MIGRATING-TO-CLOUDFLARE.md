# Moving the site to Cloudflare Pages (if it is ever needed)

Written 19 November 2026. **Nothing here has been done.** The site stays on GitHub Pages;
this is the plan to follow if that has to change. Cloudflare's limits and prices change, so
re-check the figures in "Limits" against the linked pages before starting.

## When to use this

- The site regularly passes GitHub Pages' soft limit of 100 GB of traffic a month.
- The site needs video files larger than GitHub's 100 MB per-file limit.
- Any other reason to change hosts.

Otherwise there is no reason to move. GitHub Pages currently suits the site better because
it accepts files up to 100 MB (the sound reel); Cloudflare Pages stops at 25 MiB per file.

## What changes and what does not

| Stays the same | Changes |
|---|---|
| The repo on GitHub, and pushing to `main` to publish | Cloudflare builds and serves the site instead of GitHub |
| `build.py`, `content/`, `static/`: no code changes | One DNS record for `www` points somewhere new |
| The domain registrar and email (MX) records | The sound reel needs a home if it is over 25 MiB (see step 2) |

Time: about an hour, plus waiting for DNS. Cost: free on Cloudflare's Free plan.

## Limits (Cloudflare Pages, Free plan, as checked 19 November 2026)

- 25 MiB for any single file. This is the one that matters.
- 20,000 files per site; 500 builds a month.

## Steps

### 1. Check for large files

From the repo folder:

```
python3 build.py && find _site -type f -size +25M
```

Anything listed cannot go on Cloudflare Pages as it is. Today that would only be the sound
reel, once it is added.

### 2. Decide where the sound reel lives (only if it is over 25 MiB)

Justin's position (19 November 2026): the reel is crucial to the business, so paying a
little to keep full quality is fine. That makes Option A the preferred one.

- **Option A, preferred: host the video files in Cloudflare R2** (their file storage).
  Free up to 10 GB stored, then $0.015 per GB a month, and no charge for downloads. Ten
  50 MB videos would still be free. No limit that matters on file size.
  Put the video's full address in `content/site.json` under `"reels"` > `"film"` >
  `"video"`. The build already accepts a full address there and adds that host to the
  page's security policy by itself, so the player, film markers and full screen all work
  unchanged.
  Catch, confirmed in Cloudflare's docs: to serve R2 files properly you connect your own
  address (for example `media.burntneonproductions.com`), and that needs the domain's DNS
  to be run by Cloudflare. See "Moving the domain's DNS to Cloudflare" below; that is the
  careful step. (R2's ready-made `r2.dev` address is rate-limited and meant for testing only.)
- **Option B: Cloudflare Stream**, their video service. $5 a month per 1,000 minutes stored
  plus $1 per 1,000 minutes watched. It adjusts quality to each visitor's connection, which
  is better on phones, but it plays through their player or a streaming format, so the reel
  player would need rework. Worth it only if there are many or long videos.
- **Option C, free: export the reel under 25 MiB.** A 1:12 reel fits at about 2.5 Mbps
  total. Softer at 1080p; 720p at that bitrate looks cleaner. No other changes.
- **Option D: YouTube or Vimeo.** The reel then plays in their player, without the film
  markers and custom controls. Needs a small code change.

### 3. Create the Cloudflare Pages project

1. Make a Cloudflare account. Turn on two-factor sign-in.
2. Workers & Pages > Create > Pages > Connect to Git. Authorize the
   `justinbn2025/burntneon-website` repo only.
3. Build settings:
   - Production branch: `main`
   - Framework preset: None
   - Build command: `python3 build.py`
   - Build output directory: `_site`
4. Save and deploy. The site appears at `<project-name>.pages.dev`.

`build.py` uses only Python's standard library, so there is nothing to install. Cloudflare's
current build image ships Python 3.13; if a build ever fails on the Python version, add an
environment variable `PYTHON_VERSION` (for example `3.12`).

### 4. Check the preview before touching DNS

On the `pages.dev` address, check:

- All four pages, plus a made-up address to see the "page not found" page.
- Audio players, the before/after sample, and the sound reel (play, markers, full screen).
- Links between pages. Cloudflare Pages may redirect `film.html` to `/film`. That is
  harmless for visitors, but if it happens, tell Claude so the links, `sitemap.xml` and
  page addresses in `build.py` can be switched to match (a small change).
- Phone and desktop.

### 5. Switch the domain

1. In the Pages project: Custom domains > Set up a domain > `www.burntneonproductions.com`.
2. At the domain registrar, change the `www` CNAME record from `justinbn2025.github.io` to
   `<project-name>.pages.dev`. **Do not touch the MX records** (email).
3. Wait until the Pages project shows the domain as active with HTTPS. Usually minutes,
   sometimes a few hours.

### 6. Turn off the GitHub Pages copy

Only after the domain works on Cloudflare:

1. In the GitHub repo: Settings > Pages > remove the custom domain, then unpublish the site.
2. Delete `.github/workflows/deploy.yml` (or disable the workflow) so pushes stop deploying
   to GitHub. Commit and push.
3. Update the "Publishing" section of `README.md`.

## Going back

Until step 6, going back is one change: point the `www` CNAME at `justinbn2025.github.io`
again. After step 6, restore `deploy.yml` from git history, set Settings > Pages > Source to
GitHub Actions, re-add the custom domain, then switch the CNAME.

## Moving the domain's DNS to Cloudflare

Needed for two things: serving video from R2 on your own address (step 2, Option A), and
serving the bare domain (burntneonproductions.com without www) from Cloudflare Pages. A
`www` address alone does not need it. It means changing the nameservers at the
registrar, which moves **every** DNS record, email included. Before doing that, copy every
existing record (especially MX and any TXT records for email) into Cloudflare and compare
them line by line. This is the only step in this document that can break email; avoid it
unless you need it.

Setup, confirmed from the live records on 19 November 2026: the domain's DNS is run by
GoDaddy (nameservers `ns01` / `ns02.domaincontrol.com`) and mail is delivered to Google
Workspace (five MX records: `aspmx.l.google.com` at priority 1, `alt1` and `alt2` at 5,
`alt3` and `alt4` at 10). The mailboxes live at Google, but these records, plus SPF, DKIM
and DMARC as TXT records (not yet checked), live at GoDaddy. Those are the records to carry over. To see the current ones, run
in Terminal:

```
dig +short NS burntneonproductions.com
dig +short MX burntneonproductions.com
dig +short TXT burntneonproductions.com
dig +short TXT _dmarc.burntneonproductions.com
dig +short TXT google._domainkey.burntneonproductions.com
```

The first line shows who runs the DNS. Save the full output before changing nameservers and
compare it with the same commands afterwards. Also export the whole record list from
GoDaddy's DNS page, since `dig` only shows the records you ask for by name.

## Sources (checked 19 November 2026)

- Cloudflare Pages limits: https://developers.cloudflare.com/pages/platform/limits
- Cloudflare Pages custom domains: https://developers.cloudflare.com/pages/platform/custom-domains/
- Cloudflare Pages build image: https://developers.cloudflare.com/pages/configuration/build-image/
- Cloudflare R2 pricing: https://developers.cloudflare.com/r2/platform/pricing/
- Cloudflare R2 public buckets and custom domains: https://developers.cloudflare.com/r2/buckets/public-buckets/
- Cloudflare Stream pricing: https://developers.cloudflare.com/stream/pricing
