# Deployment blockers

The initial Fly authentication and provisioning blockers were resolved on October 20, 2026. The app is deployed at [arnaudjalbert-escalographe.fly.dev](https://arnaudjalbert-escalographe.fly.dev). One Toronto Machine uses one encrypted persistent volume, and the GitHub repository has its app-scoped `FLY_API_TOKEN` Actions secret. Remote image builds, the health check, real STM ingestion, and persistence across a second deployment passed.

Continuous deployment is configured for successful CI on `main`. Its first automatic run awaits merging the PR. Rotate the 90-day deploy token before January 18, 2027.

The app still uses one SQLite volume without replication or an independent backup service. Daily Fly snapshots are enabled with five-day retention. See [DEPLOYMENT.md](DEPLOYMENT.md) for operation and verification commands.
