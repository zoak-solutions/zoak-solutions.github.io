# zoak-solutions.github.io

Official website and software repository for ZOAK Solutions.

## Poll Configuration

Poll instances live in `polls/<poll_instance>.yaml`. Each file configures one API-backed poll with:

```yaml
PollTitle: Vote for Lunch
PollDescription: Pick your preferred venue for the next ZOAK lunch.
PollSlug: lunch-vote
closeTime: 2026-07-01T12:00:00+10:00
candidates:
  - name: Hazel
    details: Modern AU and European plates.
    slug: hazel
    img: /assets/lunch-vote/hazel.webp
    informationUrl: https://example.com/
    tags:
      - key: Cuisine
        val: Modern AU / European
```

`closeTime` is optional. When configured, the page shows a `Closes in DD:HH:MM.SS` timer and the API rejects votes after that timestamp. `PollSlug` is the canonical key; the API also accepts the misspelled `PullSlug` and `informaionUrl` for compatibility with the original request wording.

The generic API route is `/api/poll-vote/<PollSlug>`. The existing `/api/lunch-vote` route remains as a compatibility alias for `/api/poll-vote/lunch-vote`.

## Poll Vote Token Admin

Keep voter CSV files and generated links under `local-sensitive/`. The directory is ignored by Git, excluded from Docker build contexts, and blocked by the local static preview.

Generate token links through the internal admin container so it uses the same SQLite volume, `.env` salts, and poll configuration as the API:

```bash
docker compose -f docker-compose-example.yaml run --rm lunch_vote_token_admin generate \
  --poll-slug lunch-vote \
  --voters voters.csv \
  --base-url https://zoak.solutions/lunch-vote/ \
  --output lunch-vote-links.csv \
  --mock-email-dir mock-emails
```

Paths in that command are relative to `local-sensitive/`, which is mounted as `/work` inside the container.

## Poll Results Embed

Email and calendar clients do not reliably support JavaScript, iframes, or live HTML includes. Use the email-safe snippet endpoint instead:

```text
https://zoak.solutions/api/poll-vote/lunch-vote/results-embed.html
```

Copy that HTML into an email or calendar invite body. The snippet displays a dynamic remote PNG:

```text
https://zoak.solutions/api/poll-vote/lunch-vote/results-card.png
```

Some clients block or cache remote images, so the snippet also includes a normal link to `/lunch-vote/`.

## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0) License. See the [LICENSE.md](LICENSE.md) file for details.

## Attribution

zoak-solutions.github.io uses Software by ZOAK Pty Ltd Licensed under CC BY-NC 4.0.
