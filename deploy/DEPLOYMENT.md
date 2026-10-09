# Active deployment - October 9, 2026

Website: https://pitch.gbaonvo.com. Sign in with Google as `gbao.n.vo@gmail.com`. The Access application is **A Story Founder OS**, with the single **Pitch OS - Bao only** allow policy. Other identities are denied. No bypass or service-token policy was added. Access cookies use HttpOnly and binding protection.

The full existing app, live SQLite database, pitch material references and workers remain on the Windows PC. Cloudflare Tunnel `a-story-founder-os` routes only this hostname to `http://127.0.0.1:8766`, sets Host to `pitch.gbaonvo.com`, and requires the exact application's signed Access JWT. The origin independently verifies signature, issuer, audience, expiry and owner email. Local-only access on port 8765 remains separate.

Windows task **A Story - Protected Pitch Website** starts missing origin/connector processes at owner sign-in and checks every five minutes. Its first completed run returned result 0. The official cloudflared 2026.10.0 binary was checked against its release SHA-256. The connector token stays in ignored `deploy/private/tunnel-token.txt`, readable only by this Windows owner and SYSTEM. It is supplied through `--token-file`, not a command-line secret.

Keep the PC awake, connected to the Internet and signed into Windows. This deployment does not relocate the app to an always-on cloud server. The agent research and email schedules retain their existing approval rules. Future reports and application previews use the protected website URL; previously claimed/sent messages remain immutable.

## Verification

- Google sign-in as the exact owner opened the live command center.
- Unauthenticated requests to the homepage, API, script and Pitch Studio were denied. The protected loopback origin independently returned 403 without identity.
- All 143 automated tests passed, including signed identity checks, wrong-email denial, CSRF, preserved application approval rules and immutable email delivery.
- The live Pitch Studio showed 14 active pitches. Remote duplication and saving were verified on a separate copy, which was then archived. Original pitch wording was preserved.
- The live materials catalog showed 1,551 source references, 1,234 distinct files and 192 searchable texts. Original material files remain in the original Pitch Competition folder.
- An authenticated original deck download matched its preserved SHA-256 content hash.
- Cloudflare reports the tunnel healthy and the exact hostname route saved. No external program application was submitted during deployment.

Application ID: `b7bcf10e-5f8d-485c-bc83-48f58b07eacc`. Tunnel ID: `85c81174-b998-44ad-864a-b8ba06c98319`. These are resource identifiers, not credentials.

The private GitHub repository includes source, tests, startup scripts and the October 8 recovery snapshot. It is not a live database synchronization service. Keep the repository private. Screenshots, runtime logs and connector credentials are excluded from Git.
