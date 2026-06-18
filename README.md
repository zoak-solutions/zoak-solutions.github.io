# zoak-solutions.github.io

Official website and software repository for ZOAK Solutions.

## Lunch Vote Token Admin

Keep voter CSV files and generated links under `local-sensitive/`. The directory is ignored by Git, excluded from Docker build contexts, and blocked by the local static preview.

Generate token links through the internal admin container so it uses the same SQLite volume and `.env` salts as the API:

```bash
docker compose -f docker-compose-example.yaml run --rm lunch_vote_token_admin generate \
  --voters voters.csv \
  --base-url https://zoak.solutions/lunch-vote/ \
  --output lunch-vote-links.csv \
  --mock-email-dir mock-emails
```

Paths in that command are relative to `local-sensitive/`, which is mounted as `/work` inside the container.

## Lunch Vote Results Embed

Email and calendar clients do not reliably support JavaScript, iframes, or live HTML includes. Use the email-safe snippet endpoint instead:

```text
https://zoak.solutions/api/lunch-vote/results-embed.html
```

Copy that HTML into an email or calendar invite body. The snippet displays a dynamic remote PNG:

```text
https://zoak.solutions/api/lunch-vote/results-card.png
```

Some clients block or cache remote images, so the snippet also includes a normal link to `/lunch-vote/`.

## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0) License. See the [LICENSE.md](LICENSE.md) file for details.

## Attribution

zoak-solutions.github.io uses Software by ZOAK Pty Ltd Licensed under CC BY-NC 4.0.
