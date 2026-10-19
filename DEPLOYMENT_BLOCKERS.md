# Deployment blockers

Fly authentication is unavailable. Official `flyctl` v0.4.118 returned `Error: no access token available` for `flyctl auth whoami` in this execution environment. Neither `FLY_API_TOKEN` nor `FLY_ACCESS_TOKEN` is set. Do **not** attempt Fly provisioning without authorization. The `arnaudjalbert-escalographe` app and `/data` volume have not been provisioned, a deploy token has not been created, and no public URL or live deployment has been verified.

The Docker CLI is present here but its local daemon is unavailable, so a local `docker build` returned `Cannot connect to the Docker daemon at unix:///var/run/docker.sock`; this CLI also lacks the Compose plugin. GitHub Actions did successfully build and boot the production image, then verified that the mounted data survived a container restart. Fly's remote build cannot be run without Fly authentication.

The GitHub deployment workflow skips deployment if the `FLY_API_TOKEN` repository secret is missing. An authorized maintainer must provision the app and exactly one `yyz` volume, create an app-scoped Fly deploy token, save it as the repository Actions secret `FLY_API_TOKEN`, then let the `main` deployment workflow run. The commands and post-deploy verification are in [DEPLOYMENT.md](DEPLOYMENT.md). The configured hostname is not evidence of a live site.
