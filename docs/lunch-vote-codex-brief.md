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

The form should allow visitors to vote for one venue and optionally provide their name, dietary notes, and comments. Votes should be persisted by a small backend API behind Caddy.

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
docker-compose.lunch-vote.example.yml
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
- Name or initials: optional text input
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
- Store localStorage key after successful vote:
  zoak-lunch-vote-submitted
- If localStorage says the user has already voted, show a friendly “You have already voted from this browser” notice, but still allow results to load.
```

Use:

```text
POST /api/lunch-vote
Content-Type: application/json
```

### Results card

Show aggregate public results from:

```text
GET /api/lunch-vote/results
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

### Details card

Include the original venue matrix as a compact table for comparison.

## Client-side JavaScript

Implement inline JavaScript in `lunch-vote/index.html`.

Functions to include:

```text
renderHeroThumbnails()
renderVenueRadios()
selectVenue(venueId)
submitVote(event)
loadResults()
renderResults(data)
setStatus(message, type)
```

Validation:

```text
- Venue is required.
- Name max length: 80 characters.
- Dietary note max length: 500 characters.
- Comment max length: 500 characters.
- Honeypot must remain empty.
```

Fetch behavior:

```js
const response = await fetch('/api/lunch-vote', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
});
```

After successful submission:

```text
- Save localStorage flag.
- Show success message.
- Reload results.
- Keep selected venue visible.
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
POST /lunch-vote
GET  /lunch-vote/results
```

Important: if Caddy uses `handle_path /api/*`, the backend will receive `/lunch-vote`, not `/api/lunch-vote`.

### Database schema

Use SQLite:

```sql
CREATE TABLE IF NOT EXISTS votes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  venue TEXT NOT NULL,
  voter_name TEXT,
  dietary_note TEXT,
  comment TEXT,
  ip_hash TEXT,
  user_agent TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_votes_created_at ON votes(created_at);
CREATE INDEX IF NOT EXISTS idx_votes_venue ON votes(venue);
CREATE INDEX IF NOT EXISTS idx_votes_ip_hash ON votes(ip_hash);
```

### Allowed venues

Server must reject any venue not in this set:

```python
ALLOWED_VENUES = {
    "Hazel",
    "Il Solito Posto",
    "Supernormal",
    "Tazio",
    "Rare Steakhouse",
}
```

### POST `/lunch-vote`

Request body:

```json
{
  "name": "Mark",
  "venue": "Hazel",
  "dietary": "No seafood",
  "comment": "Prefer somewhere quiet",
  "website": ""
}
```

Server behavior:

```text
- Reject non-JSON requests.
- Reject payloads over 16 KB.
- Reject missing or invalid venue.
- Reject if honeypot field "website" is non-empty.
- Trim all text fields.
- Enforce max lengths.
- Hash IP address with server-side salt before storage.
- Store created_at as UTC ISO-8601.
```

Response success:

```json
{
  "ok": true,
  "message": "Vote recorded."
}
```

Response error:

```json
{
  "ok": false,
  "error": "Invalid venue."
}
```

### GET `/lunch-vote/results`

Response:

```json
{
  "total": 12,
  "options": [
    { "venue": "Hazel", "votes": 4, "percentage": 33.3 },
    { "venue": "Il Solito Posto", "votes": 2, "percentage": 16.7 },
    { "venue": "Supernormal", "votes": 3, "percentage": 25.0 },
    { "venue": "Tazio", "votes": 1, "percentage": 8.3 },
    { "venue": "Rare Steakhouse", "votes": 2, "percentage": 16.7 }
  ]
}
```

Always return all five venues, even if some have zero votes.

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
docker-compose.lunch-vote.example.yml
```

Suggested content:

```yaml
services:
  lunch_vote_api:
    build: ./lunch-vote-api
    environment:
      VOTE_DB_PATH: /data/lunch-votes.sqlite
      VOTE_IP_HASH_SALT: change-me-in-production
    volumes:
      - lunch_vote_data:/data
    restart: unless-stopped

volumes:
  lunch_vote_data:
```

Do not assume this repo owns the production Compose file. This example file is for integration into the actual deployment stack.

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
Browser request: /api/lunch-vote
Backend receives: /lunch-vote
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
- Do not show names/comments publicly.
- Do not store raw IP addresses.
- Store salted IP hash only.
- Add basic rate limiting or duplicate throttling by hashed IP if simple to implement.
- Include hidden honeypot field.
- Limit request body size.
- Limit text field lengths.
```

Optional duplicate rule:

```text
Allow one vote per hashed IP every 12 hours.
```

If implemented, return:

```json
{
  "ok": false,
  "error": "A vote has already been recorded recently from this network."
}
```

## Acceptance criteria

The implementation is complete when:

```text
- /lunch-vote/ loads as a standalone ZOAK-styled page.
- The hero section shows five venue thumbnails.
- Clicking a hero thumbnail selects the corresponding venue in the form.
- The form submits to /api/lunch-vote.
- Votes persist in SQLite.
- Results load from /api/lunch-vote/results.
- Results show aggregate counts only.
- The page works on mobile.
- The page remains usable if a thumbnail fails to load.
- The backend rejects invalid venues and honeypot submissions.
- Caddy can serve the static page and reverse-proxy the API.
```

## Implementation order for Codex

1. Copy the visual structure of `privacy_policy/index.html` into `lunch-vote/index.html`.
2. Replace the legal content with the lunch voting hero, thumbnail strip, vote form, results card, and venue details table.
3. Add local image references and fallback handling.
4. Implement client-side rendering and form submission.
5. Add `lunch-vote-api/server.py` with SQLite persistence.
6. Add `lunch-vote-api/Dockerfile`.
7. Add `docker-compose.lunch-vote.example.yml`.
8. Document the Caddy `handle_path /api/*` integration in a comment or deployment note.
9. Test with:

   ```text
   curl http://localhost:8080/health
   curl http://localhost:8080/lunch-vote/results
   curl -X POST http://localhost:8080/lunch-vote \
     -H 'Content-Type: application/json' \
     -d '{"venue":"Hazel","name":"Test","dietary":"","comment":"","website":""}'
   ```
10. Verify the browser flow through Caddy at:

```text
/lunch-vote/
/api/lunch-vote/results
```

[1]: https://caddyserver.com/docs/caddyfile/directives/file_server "file_server (Caddyfile directive) — Caddy Documentation"
[2]: https://caddyserver.com/docs/caddyfile/directives/reverse_proxy "reverse_proxy (Caddyfile directive) — Caddy Documentation"
[3]: https://caddyserver.com/docs/caddyfile/directives/handle_path "handle_path (Caddyfile directive) — Caddy Documentation"
