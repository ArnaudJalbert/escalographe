# Deployment

The live deployment is [arnaudjalbert-escalographe.fly.dev](https://arnaudjalbert-escalographe.fly.dev), in Toronto (`yyz`), with one shared-CPU Machine, 512 MB RAM, and one encrypted 1 GB `data` volume mounted at `/data`. The container listens on port 8000 and requires HTTPS. Fly stops the Machine after several minutes without traffic and starts it when the next request arrives. No Machines are kept running when idle.

Ingestion pauses while the Machine is stopped. On startup, the scheduler refreshes STM and OSM in the background; the first visitor sees persisted observations until that refresh completes and may wait for a cold start. History has observation gaps during idle periods. This deployment does not provide continuous monitoring. The volume remains attached and billable while the Machine is stopped. See Fly's [autostop/autostart documentation](https://fly.io/docs/launch/autostop-autostart/).

## Deployment status

PR #7 was deployed on October 20, 2026 from commit `6e94064269356e2460b6b05d326487825d658eb1`. Machine `8ed676b7119202` has volume `vol_v3gx07p3wdzeowl4` attached. The health check passes. Live imports received 245 STM records and 74 OSM records with city-boundary coverage. A second remote build and deployment preserved an existing device's ID, source identifiers, first-seen timestamps, complete history, and original ingestion run.

The GitHub Actions secret `FLY_API_TOKEN` contains an app-scoped deploy token created on October 20, 2026 with a 90-day lifetime. Rotate it before January 18, 2027. The first automatic deployment from `main` still needs a merge and successful CI; the initial deployment used `fly deploy` from the PR branch.

## Provision once

Install `flyctl` and authenticate with the account that owns the app. From the repository root:

```sh
fly auth login
fly apps create arnaudjalbert-escalographe --org personal
fly volumes create data --app arnaudjalbert-escalographe --region yyz --size 1 --yes
fly deploy --remote-only --ha=false --config fly.toml --build-arg GIT_SHA="$(git rev-parse HEAD)"
fly scale count 1 --app arnaudjalbert-escalographe --yes
fly status --app arnaudjalbert-escalographe
fly volumes list --app arnaudjalbert-escalographe
```

If `yyz` is unavailable to the Fly organization, choose the nearest permitted region, then change `primary_region` in `fly.toml` and the volume's `--region` together *before* provisioning. Confirm that `status` lists exactly one machine and `volumes list` one attached volume. Do not run `scale count` on an existing unrelated app without inspecting its resources first. Keep a backup of SQLite; one Fly volume is not automatically replicated.

Do not use Fly's `[deploy] release_command` for SQLite migrations. Fly's release-command Machine cannot mount volumes, so it would migrate an ephemeral database. `docker-entrypoint.sh` runs `python -m app.cli migrate` on the attached `/data` volume before serving requests. The image drops privileges after preparing mount ownership. There can be a short interruption during a single-volume deployment; do not run two schedulers against independent copies.

## Continuous deployment

CI checks every pull request and push to `main`, including booting the production image twice against the same mounted test volume. The deploy workflow waits for a successful CI workflow on `main`, checks out the exact tested commit, then deploys with `flyctl deploy --remote-only --ha=false`. It verifies HTTPS at `/api/health`, `/`, and `/docs` and waits for real escalator and live-status data in `/api/v1/stats/summary`. It skips deployment when the GitHub repository secret is absent; it never commits or prints credentials.

Once the app exists, create a Fly app-scoped deploy token and set the GitHub repository Actions secret `FLY_API_TOKEN`. Treat the output as a credential; do not paste it into issues, chat, or source control.

```sh
fly tokens create deploy --app arnaudjalbert-escalographe --expiry 2160h \
  | gh secret set FLY_API_TOKEN --repo ArnaudJalbert/escalographe
```

The token expires after 90 days using this example; rotate it before then. Fly's [GitHub Actions deployment guide](https://fly.io/docs/app-guides/continuous-deployment-with-github-actions/) recommends a repository secret and a deploy-scoped token. Never use a broad organization token if an app-scoped one suffices. Merge to `main` only after the app and volume are ready and the secret is configured.

## Verify after deployment

Do not report a live site on the basis of a configured hostname alone. Once a deploy succeeds, check the Fly status, machine and volume count, logs, HTTPS site, health, docs, and API data. Check that status observations are recent and sourced from real STM records. Direct navigation to an escalator route must return the SPA; an invalid `/api/*` path must not return its HTML. Check the database still exists after a second deploy, and watch the next scheduled ingestion. An unexplained empty database is a failed launch, not a successful smoke test.

To verify idle shutdown, close browser tabs that poll the API and stop sending HTTP probes. Inspect `fly status --app arnaudjalbert-escalographe` until the Machine is `stopped`, then request `/api/health` over HTTPS and confirm it starts again with its persisted data. Fly health checks do not require keeping one Machine running.

Fly references: [app configuration, HTTP checks, mounts, and release commands](https://fly.io/docs/reference/configuration/), [volumes and their limits](https://fly.io/docs/volumes/overview/), [volume creation](https://fly.io/docs/flyctl/volumes-create/), [app-scoped deploy tokens](https://fly.io/docs/flyctl/tokens-create-deploy/), [GitHub Actions deployment](https://fly.io/docs/app-guides/continuous-deployment-with-github-actions/).
