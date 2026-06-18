# Codex implementation brief: public lunch voting form with hero thumbnails

## Context

The `zoak-solutions/zoak-solutions.github.io` repo is a static HTML site. It currently has standalone entry points for the home page, terms page, and privacy policy page. The existing `privacy_policy/index.html` is the best template for this feature because it is a self-contained page with inline CSS, ZOAK styling tokens, a sticky topbar, hero section, card layout, and footer.   

The site is served through Caddy in Docker. Caddy’s `file_server` directive is intended for static files, usually paired with a site root, and `reverse_proxy` can proxy requests to a backend service. Caddy’s `handle_path` can strip a matched path prefix before passing the request to handlers, which is useful for `/api/*` routing. ([Caddy Web Server][1]) ([Caddy Web Server][2]) ([Caddy Web Server][3])

## Goal

Create a public lunch voting page at:

```text
/lunch-vote/
```

The page should look like the existing privacy policy page, but with a more visual hero section that includes thumbnails for each lunch venue option.

The form should allow visitors to vote for one venue and optionally provide dietary notes and comments. Votes should be persisted by a small backend API behind Caddy.

## Lunch options

Use these options exactly:

| Venue           | Cuisine              | Vibe & Atmosphere                                  | Order Method                               | Walk Time |
| :-------------- | :------------------- | :------------------------------------------------- | :----------------------------------------- | :-------- |
| Hazel           | Modern AU / European | Ultra-premium, crisp, and beautifully designed.    | À la carte or shared wood-fired plates.    | 1 min     |
| Il Solito Posto | Classic Italian      | Warm, legendary underground corporate institution. | Traditional à la carte, individual plates. | 2 mins    |
| Supernormal     | Contemporary Asian   | Lively, trendy, and high-energy iconic hotspot.    | Shared à la carte.                         | 2 mins    |
| Tazio           | Contemporary Italian | Quiet and spacious historic warehouse.             | Individual plates or fast structured menu. | 3 mins    |
| Rare Steakhouse | Premium Steakhouse   | Classic, polished, and long-standing favorite.     | Traditional à la carte.                    | 4 mins    |

## Files to add

Add these files:

```text
lunch-vote/index.html
assets/lunch-vote/hazel.webp
assets/lunch-vote/il-solito-posto.webp
assets/lunch-vote/supernormal.webp
assets/lunch-vote/tazio.webp
assets/lunch-vote/rare-steakhouse.webp
assets/lunch-vote/placeholder.svg
lunch-vote-api/server.py
lunch-vote-api/Dockerfile
docker-compose-example.yaml
```

Do not refactor the existing home page unless adding a link to `/lunch-vote/` is explicitly desired.

## Image handling

Use local thumbnail assets under:

```text
/assets/lunch-vote/
```

Do not hotlink restaurant images from third-party websites. Use properly licensed, owned, or approved images. If final venue images are not available, use `placeholder.svg` for all five thumbnails and leave clear filenames for later replacement.

Thumbnail requirements:

```text
Format: webp preferred
Target size: 800x600 or similar
Max file size: ideally under 150 KB each
Aspect ratio in UI: 4:3 or 16:10
Object fit: cover
```

Use these image paths in the page data model:

```js
const VENUES = [
  {
    id: 'hazel',
    name: 'Hazel',
    cuisine: 'Modern AU / European',
    vibe: 'Ultra-premium, crisp, and beautifully designed.',
    orderMethod: 'À la carte or shared wood-fired plates.',
    walkTime: '1 min',
    image: '/assets/lunch-vote/hazel.webp',
    fallbackImage: '/assets/lunch-vote/placeholder.svg'
  },
  {
    id: 'il-solito-posto',
    name: 'Il Solito Posto',
    cuisine: 'Classic Italian',
    vibe: 'Warm, legendary underground corporate institution.',
    orderMethod: 'Traditional à la carte, individual plates.',
    walkTime: '2 mins',
    image: '/assets/lunch-vote/il-solito-posto.webp',
    fallbackImage: '/assets/lunch-vote/placeholder.svg'
  },
  {
    id: 'supernormal',
    name: 'Supernormal',
    cuisine: 'Contemporary Asian',
    vibe: 'Lively, trendy, and high-energy iconic hotspot.',
    orderMethod: 'Shared à la carte.',
    walkTime: '2 mins',
    image: '/assets/lunch-vote/supernormal.webp',
    fallbackImage: '/assets/lunch-vote/placeholder.svg'
  },
  {
    id: 'tazio',
    name: 'Tazio',
    cuisine: 'Contemporary Italian',
    vibe: 'Quiet and spacious historic warehouse.',
    orderMethod: 'Individual plates or fast structured menu.',
    walkTime: '3 mins',
    image: '/assets/lunch-vote/tazio.webp',
    fallbackImage: '/assets/lunch-vote/placeholder.svg'
  },
  {
    id: 'rare-steakhouse',
    name: 'Rare Steakhouse',
    cuisine: 'Premium Steakhouse',
    vibe: 'Classic, polished, and long-standing favorite.',
    orderMethod: 'Traditional à la carte.',
    walkTime: '4 mins',
    image: '/assets/lunch-vote/rare-steakhouse.webp',
    fallbackImage: '/assets/lunch-vote/placeholder.svg'
  }
];
```

## Page implementation

Create `lunch-vote/index.html` by adapting the structure and visual style of `privacy_policy/index.html`.

Keep:

```text
- Figtree font
- dark ZOAK theme
- sticky topbar
- brand link back to /
- rounded cards
- orange/yellow accent treatment
- same footer style
```

Change the content to a lunch voting page.

Suggested document metadata:

```html
<title>Vote for Lunch — ZOAK Solutions</title>
<meta name="description" content="Vote for the next ZOAK Solutions team lunch venue." />
```

## Hero section requirement

The hero section must include thumbnails of all five venue options.

Structure:

```html
<section class="hero">
  <span class="eyebrow">Team Lunch</span>
  <h1>Vote for Lunch</h1>
  <p class="lede">
    Pick your preferred venue for the next ZOAK lunch. Browse the options below, then cast your vote.
  </p>

  <div class="hero-venue-strip" aria-label="Lunch venue options">
    <!-- five thumbnail buttons/cards rendered here -->
  </div>
</section>
```

Each hero thumbnail should include:

```text
- Venue image
- Venue name
- Cuisine
- Walk time badge
```

Interaction:

```text
- Each hero thumbnail should be clickable.
- Clicking a thumbnail selects the matching venue radio option in the form.
- After selection, scroll or focus the voting form.
- Add selected styling to the chosen thumbnail.
```

Hero thumbnail card example:

```html
<button class="hero-venue-thumb" type="button" data-select-venue="hazel">
  <img src="/assets/lunch-vote/hazel.webp" alt="Hazel venue thumbnail" width="320" height="240" />
  <span class="thumb-overlay">
    <strong>Hazel</strong>
    <span>Modern AU / European</span>
    <em>1 min walk</em>
  </span>
</button>
```

Responsive behavior:

```text
Desktop:
- Display five thumbnails in a single responsive grid row if space allows.
- Use equal card heights.

Tablet/mobile:
- Use horizontal scroll with scroll-snap, or a 2-column grid.
- Ensure thumbnails remain tappable and readable.
```

Suggested CSS:

```css
.hero-venue-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: .85rem;
  margin-top: 1.75rem;
}

.hero-venue-thumb {
  position: relative;
  min-height: 150px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  overflow: hidden;
  padding: 0;
  cursor: pointer;
  background: var(--color-card);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-lg);
  transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
}

.hero-venue-thumb:hover,
.hero-venue-thumb:focus-visible {
  transform: translateY(-2px);
  border-color: var(--color-primary);
}

.hero-venue-thumb[aria-pressed="true"] {
  border-color: var(--color-secondary);
  box-shadow: 0 0 0 3px rgba(249, 220, 6, .18), var(--shadow-lg);
}

.hero-venue-thumb img {
  width: 100%;
  height: 100%;
  min-height: 150px;
  object-fit: cover;
  display: block;
  filter: saturate(1.05) contrast(1.05);
}

.thumb-overlay {
  position: absolute;
  inset: auto 0 0;
  display: grid;
  gap: .15rem;
  padding: .85rem;
  text-align: left;
  background: linear-gradient(180deg, transparent, rgba(0,0,0,.84));
}

.thumb-overlay strong {
  font-size: .95rem;
}

.thumb-overlay span,
.thumb-overlay em {
  color: rgba(255,255,255,.82);
  font-size: .78rem;
  font-style: normal;
}

.thumb-overlay em {
  color: var(--color-secondary);
  font-weight: 700;
}

@media (max-width: 900px) {
  .hero-venue-strip {
    display: flex;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    padding-bottom: .5rem;
  }

  .hero-venue-thumb {
    flex: 0 0 min(76vw, 280px);
    scroll-snap-align: start;
  }
}
```

## Main content layout

After the hero, add three main cards:

```text
1. Vote card
2. Results card
3. Details card
```

### Vote card

Fields:

```text
- Venue: required radio group
- Dietary/accessibility note: optional textarea
- Comment: optional textarea
- Hidden honeypot field named "website"
```

Venue radio cards should show the same venue metadata as the table, but not necessarily repeat the images unless the page still feels balanced.

Required behavior:

```text
- Submit button disabled during submission.
- Show inline error messages.
- Show success message after a successful vote.
- Require a unique voter token from the email invitation link.
- If no usable token is present, leave results available but disable voting.
- Remove the token from the browser address bar after reading it from the link.
```

Use:

```text
POST /api/poll-vote/<PollSlug>
Content-Type: application/json
```

### Results card

Show aggregate public results from:

```text
GET /api/poll-vote/<PollSlug>/results
```

Display:

```text
- Total votes
- Venue rows
- Count
- Percentage
- Horizontal result bar
```

No names, comments, dietary notes, IP addresses, or user agents should be shown publicly.

The only sections below the hero are `voteCard` and `resultsCard`.

## Client-side JavaScript

Implement JavaScript in `lunch-vote/poll-vote.js`.

Functions to include:

```text
initializeVoteToken()
verifyVoteToken()
renderHeroThumbnails()
renderCandidateRadios()
selectCandidate(candidateSlug)
submitVote(event)
loadResults()
renderResults(data)
setStatus(message, type)
```

Validation:

```text
- Candidate is required.
- One-time vote token is required.
- Dietary note max length: 500 characters.
- Comment max length: 500 characters.
- Honeypot must remain empty.
```

Fetch behavior:

```js
const response = await fetch(`/api/poll-vote/${poll.PollSlug}`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
});
```

After successful submission:

```text
- Show success message.
- Reload results.
- Keep the session token and selected candidate visible so the same voter can update their current vote without inflating results.
```

Image fallback behavior:

```js
img.addEventListener('error', () => {
  img.src = venue.fallbackImage;
});
```

## Backend API

Add a minimal Python API using only the standard library plus SQLite.

File:

```text
lunch-vote-api/server.py
```

Runtime:

```text
Python 3.12+
Port: 8080
Database path from VOTE_DB_PATH, default /data/lunch-votes.sqlite
Salt from VOTE_IP_HASH_SALT
```

Endpoints:

```text
GET  /health
POST /poll-vote/<PollSlug>
GET  /poll-vote/<PollSlug>/config
GET  /poll-vote/<PollSlug>/results
GET  /poll-vote/<PollSlug>/results-card.png
GET  /poll-vote/<PollSlug>/results-embed.html
GET  /poll-vote/<PollSlug>/token
```

Important: if Caddy uses `handle_path /api/*`, the backend will receive `/poll-vote/<PollSlug>`, not `/api/poll-vote/<PollSlug>`.

### Database schema

Use SQLite:

```sql
CREATE TABLE IF NOT EXISTS votes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  poll_slug TEXT,
  candidate_slug TEXT,
  venue TEXT NOT NULL,
  voter_name TEXT,
  dietary_note TEXT,
  comment TEXT,
  vote_token_hash TEXT,
  vote_key_hash TEXT,
  ip_hash TEXT,
  user_agent TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vote_tokens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  poll_slug TEXT,
  token_hash TEXT NOT NULL UNIQUE,
  recipient_label TEXT,
  recipient_email_hash TEXT,
  created_at TEXT NOT NULL,
  used_at TEXT,
  used_vote_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_votes_created_at ON votes(created_at);
CREATE INDEX IF NOT EXISTS idx_votes_poll_slug ON votes(poll_slug);
CREATE INDEX IF NOT EXISTS idx_votes_candidate_slug ON votes(candidate_slug);
CREATE INDEX IF NOT EXISTS idx_votes_venue ON votes(venue);
CREATE INDEX IF NOT EXISTS idx_votes_ip_hash ON votes(ip_hash);
CREATE INDEX IF NOT EXISTS idx_votes_vote_token_hash ON votes(vote_token_hash);
CREATE INDEX IF NOT EXISTS idx_vote_tokens_used_at ON vote_tokens(used_at);
```

### Allowed candidates

Server must reject any candidate slug not configured in the active poll instance YAML.

### POST `/poll-vote/<PollSlug>`

Request body:

```json
{
  "token": "unique-token-from-email-link",
  "candidateSlug": "hazel",
  "dietary": "No seafood",
  "comment": "Prefer somewhere quiet",
  "website": ""
}
```

Server behavior:

```text
- Reject non-JSON requests.
- Reject payloads over 16 KB.
- Reject missing or invalid candidate.
- Reject missing, invalid, or unknown vote tokens.
- Reject if honeypot field "website" is non-empty.
- Trim all text fields.
- Enforce max lengths.
- Hash IP address with server-side salt before storage.
- Store only salted token hashes, not raw tokens.
- Insert or update the token's current vote in the same database transaction.
- Store created_at as UTC ISO-8601.
```

Response success:

```json
{
  "ok": true,
  "message": "Vote recorded.",
  "voted": true,
  "candidateSlug": "hazel",
  "candidateName": "Hazel",
  "venue": "Hazel"
}
```

Response error:

```json
{
  "ok": false,
  "error": "Invalid candidate."
}
```

### GET `/poll-vote/<PollSlug>/token`

Query string:

```text
?token=unique-token-from-email-link
```

Response for a token with no current vote:

```json
{
  "ok": true,
  "usable": true,
  "voted": false,
  "pollClosed": false,
  "candidateSlug": "",
  "candidateName": "",
  "venue": ""
}
```

Response for a token with a current vote:

```json
{
  "ok": true,
  "usable": true,
  "voted": true,
  "pollClosed": false,
  "candidateSlug": "hazel",
  "candidateName": "Hazel",
  "venue": "Hazel"
}
```

### GET `/poll-vote/<PollSlug>/results`

Response:

```json
{
  "total": 12,
  "options": [
    { "name": "Hazel", "slug": "hazel", "venue": "Hazel", "votes": 4, "percentage": 33.3 },
    { "name": "Il Solito Posto", "slug": "il-solito-posto", "venue": "Il Solito Posto", "votes": 2, "percentage": 16.7 }
  ]
}
```

Always return all configured candidates, even if some have zero votes.

## Dockerfile

Create:

```text
lunch-vote-api/Dockerfile
```

Suggested content:

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY server.py /app/server.py

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
  && mkdir -p /data \
  && chown -R appuser:appuser /data /app

USER appuser

EXPOSE 8080

CMD ["python", "/app/server.py"]
```

## Example Docker Compose

Create:

```text
docker-compose-example.yaml
```

Suggested content:

```yaml
services:
  zoak_site:
    image: caddy:2-alpine
    ports:
      - "8088:80"
    volumes:
      - ./:/srv:ro
    configs:
      - source: zoak_caddyfile
        target: /etc/caddy/Caddyfile
    depends_on:
      - lunch_vote_api
    restart: unless-stopped

  lunch_vote_api:
    build: ./lunch-vote-api
    environment:
      VOTE_DB_PATH: /data/lunch-votes.sqlite
      VOTE_IP_HASH_SALT: change-me-in-production
      VOTE_TOKEN_HASH_SALT: change-me-in-production
    volumes:
      - lunch_vote_data:/data
    restart: unless-stopped

configs:
  zoak_caddyfile:
    content: |
      :80 {
        root * /srv
        encode zstd gzip

        handle_path /api/* {
          reverse_proxy lunch_vote_api:8080
        }

        file_server
      }

volumes:
  lunch_vote_data:
```

Do not assume this repo owns the production Compose file. This example shows the full static site plus API stack and can be adapted into the actual deployment stack.

## Caddy integration

Add this to the deployment Caddyfile, adjusting service names as needed:

```caddyfile
handle_path /api/* {
  reverse_proxy lunch_vote_api:8080
}

handle {
  root * /usr/share/caddy
  file_server
}
```

With this config:

```text
Browser request: /api/poll-vote/lunch-vote
Backend receives: /poll-vote/lunch-vote
```

That path-stripping behavior is expected when using `handle_path`.

## Accessibility requirements

Implement:

```text
- Real radio inputs for venue selection.
- Hero thumbnail buttons must have accessible labels.
- Visible focus states.
- aria-live region for submission status.
- Form labels tied to inputs.
- Results must not rely on color alone.
- Images must have useful alt text or decorative empty alt text if repeated nearby.
```

Suggested live region:

```html
<div id="voteStatus" class="status" role="status" aria-live="polite"></div>
```

## Privacy and abuse controls

For this lunch poll, keep privacy lightweight but sensible:

```text
- Do not show comments publicly.
- Do not store raw IP addresses.
- Store salted voter token and IP hashes only.
- Require a unique email invitation token for each vote.
- Include hidden honeypot field.
- Limit request body size.
- Limit text field lengths.
```

Implemented token voting rule:

```text
Allow one current vote per generated email invitation token and poll slug. The organiser generates one random token per voter and sends each voter a unique /lunch-vote/?token=... link. The first submission creates that token's vote; later submissions from the same token update the same vote row, so results do not inflate.
```

Successful update response:

```json
{
  "ok": true,
  "message": "Vote updated.",
  "voted": true,
  "candidateSlug": "tazio",
  "candidateName": "Tazio",
  "venue": "Tazio"
}
```

## Poll instance configuration

Poll instances live in `polls/<poll_instance>.yaml`. Required top-level fields are `PollTitle`, `PollDescription`, and `PollSlug`; the API also accepts `PullSlug` for compatibility with the original request wording.

Each candidate must include `name`, `details`, `slug`, and `img`. It may also include `informationUrl` and `tags`, where tags are a list of `{key, val}` pairs. The API accepts the misspelled `informaionUrl` alias and normalizes it to `informationUrl`.

Optional `closeTime` must be an ISO-8601 timestamp. When present, the page displays `Closes in DD:HH:MM.SS`; once the timestamp is reached, the API rejects new or updated votes with `403 This poll is closed.`

## Unique link email workflow

Keep the voter list outside the repository. Create a private CSV such as:

```csv
email,name
person@example.com,Person Name
```

Generate individualized mail-merge links through the internal token admin container:

```bash
docker compose -f docker-compose-example.yaml run --rm lunch_vote_token_admin generate \
  --poll-slug lunch-vote \
  --voters voters.csv \
  --base-url https://zoak.solutions/lunch-vote/ \
  --output lunch-vote-links.csv \
  --mock-email-dir mock-emails
```

The admin container has no network access, mounts the same SQLite volume as the API at `/data`, and mounts the ignored `local-sensitive/` directory as `/work` for private CSV inputs and outputs.

Send `lunch-vote-links.csv` through an email mail-merge tool using the `vote_link` column. Do not send one BCC email if every recipient needs a unique URL; use a per-recipient mail merge or transactional email job. The database stores token hashes and recipient email hashes only.

## Email and calendar results embed

Use this endpoint to copy an email/calendar-safe HTML fragment:

```text
/api/poll-vote/lunch-vote/results-embed.html
```

The fragment uses a linked PNG for live results:

```text
/api/poll-vote/lunch-vote/results-card.png
```

JavaScript, iframes, and fetched HTML are not reliable in email or calendar invites. Remote images can also be blocked or cached by some clients, so every embed includes a normal link back to `/lunch-vote/`.

## Acceptance criteria

The implementation is complete when:

```text
- /lunch-vote/ loads as a standalone ZOAK-styled page.
- The hero section shows configured candidate thumbnails.
- The only sections below the hero are voteCard and resultsCard.
- Clicking a hero thumbnail selects the corresponding candidate in the form.
- The form submits to /api/poll-vote/<PollSlug>.
- Votes persist in SQLite.
- Each current vote is owned by a unique voter token and poll slug and can be updated by that token.
- Results load from /api/poll-vote/<PollSlug>/results.
- Results show aggregate counts only.
- If closeTime is configured, the UI shows a countdown and the API rejects late votes.
- The page works on mobile.
- The page remains usable if a thumbnail fails to load.
- The backend rejects invalid candidates and honeypot submissions.
- Caddy can serve the static page and reverse-proxy the API.
```

## Implementation order for Codex

1. Copy the visual structure of `privacy_policy/index.html` into `lunch-vote/index.html`.
2. Replace the legal content with the poll hero, thumbnail strip, vote card, and results card.
3. Add local image references and fallback handling.
4. Implement client-side rendering and form submission.
5. Add `lunch-vote-api/server.py` with SQLite persistence.
6. Add `lunch-vote-api/Dockerfile`.
7. Add `docker-compose-example.yaml` for the static site plus lunch-vote API.
8. Document the Caddy `handle_path /api/*` integration in a comment or deployment note.
9. Test with:

   ```text
   curl http://localhost:8080/health
   curl http://localhost:8080/poll-vote/lunch-vote/results
   python3 lunch-vote-api/manage_tokens.py generate --poll-slug lunch-vote --count 1 --base-url http://localhost:8080/lunch-vote/ --output /tmp/lunch-vote-links.csv
   curl -X POST http://localhost:8080/poll-vote/lunch-vote \
     -H 'Content-Type: application/json' \
     -d '{"candidateSlug":"hazel","token":"TOKEN_FROM_GENERATED_CSV","dietary":"","comment":"","website":""}'
   ```
10. Verify the browser flow through Caddy at:

```text
/lunch-vote/
/api/poll-vote/lunch-vote/results
```

[1]: https://caddyserver.com/docs/caddyfile/directives/file_server "file_server (Caddyfile directive) — Caddy Documentation"
[2]: https://caddyserver.com/docs/caddyfile/directives/reverse_proxy "reverse_proxy (Caddyfile directive) — Caddy Documentation"
[3]: https://caddyserver.com/docs/caddyfile/directives/handle_path "handle_path (Caddyfile directive) — Caddy Documentation"
