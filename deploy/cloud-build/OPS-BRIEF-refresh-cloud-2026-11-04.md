# Refresh pitch.gbaonvo.com's cloud copy (Nov 4, 2026)

Bao approved the refresh in chat ("Refresh the cloud copy"). Claude built and tested it, and GPT ships it. Run everything in this folder: `deploy/cloud-build/pitch-cloud`.

## What changed
- `app_bundle.py` is rebuilt from today's `founder_os`. Skip/Watch now hides programs, and the 30-day rule no longer reopens Applied or Expired programs.
- `entry.py`: `/api/cloud/import` refreshes only when `replace_sha256` names the current cloud copy. The old database stays inside the Durable Object at `data/repair-backups/cloud-before-refresh-<sha12>.sqlite`.
- `wrangler.jsonc` is new, rebuilt from the deployed settings.
- Tested with `test_entry_refresh.py`, a CPython harness, because Wrangler's local Python runtime fails on Windows (GPT's original build fails there too). Every check passed: import, refusal without or with a wrong hash, refresh with backup, state surviving a restart, and 11 recommended programs.
- The only change on the cloud since Oct 25 is today's queued Win Scout click.

## Retry, 2026-11-04 afternoon
The first run deployed the code, but the import crashed (Cloudflare 1101) because it held about three copies of the 49 MB database in a 128 MB isolate.
- **Live state:** the site works, the old data is intact, the current version is `99123f64`, and the old `11f95972` can't be rolled back to because it lacks the exports declaration.
- **What changed in `entry.py`:** the upload is unpacked in 1 MB steps straight to disk, the old copy is truncated first, and the backup is made with SQL inside Durable Object storage. Backups are never loaded into memory.
- **Harness result:** 35 MB of new Python memory during a refresh, and every check passes.
- **Current cloud copy hash:** `d1dfd57395b1a2879b213d59b0fb7a71771926a174c5a108e2e788a463a9e2e6`.
- **For the rollback in step 1,** use the version that is active now.

## Steps
1. Confirm the login and save the rollback point:
   - Run `npx wrangler@4 whoami` and expect gbao.n.vo@gmail.com.
   - Run `npx wrangler@4 deployments list --name pitch-cloud` and write down the active version id.
2. Set `"workers_dev": true` in `wrangler.jsonc`, then run `npx wrangler@4 deploy`. If Wrangler reports a Durable Object migration or exports conflict, stop.
3. Add the key from `.migration-key` without printing it: `Get-Content .migration-key -Raw | npx wrangler@4 secret put MIGRATION_KEY`
4. Run `py -X utf8 migrate.py https://pitch-cloud.<workers.dev subdomain>`. It returns 409 with the current sha256. Then run `py -X utf8 migrate.py <same url> --replace <that sha256>`.
5. Clean up:
   - Run `npx wrangler@4 secret delete MIGRATION_KEY`.
   - Set `"workers_dev": false` again, then run `npx wrangler@4 deploy`.
6. Check that `deployments list` shows the new version, and that pitch-free is untouched.

## Rollback
- **Code:** `npx wrangler@4 rollback <version id from step 1>`.
- **Data:** the old cloud database is kept inside the Durable Object, so nothing is lost.

## Don't touch
pitch-free, Access, DNS, routes or other Workers. Never print or commit the key.
