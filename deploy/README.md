# pitch.gbaonvo.com

The deployment is active. See [verified deployment details](DEPLOYMENT.md). Future report links are enabled by `report_links_enabled: true` in the private Access configuration only after successful live verification; already claimed or sent messages are preserved.

The current deployment uses the full Windows Founder OS through Cloudflare Tunnel. The app, SQLite state, material references, research and application workers stay on this PC. This is not an always-on Cloudflare Worker rewrite. The PC must be awake and online. Existing local access remains at port 8765; the protected origin uses a separate loopback port 8766.

Cloudflare Access application: A Story Founder OS. Hostname: `pitch.gbaonvo.com`. Team: `astoryapp.cloudflareaccess.com`. Allow only `gbao.n.vo@gmail.com`, with no bypass or service-token policy. Email login is provided by Cloudflare Access. The origin independently verifies RS256 signatures, issuer, exact audience, token validity and email on every route. No asserted email header alone is trusted. Cloudflare should also enable Protect with Access on the tunnel route.

Copy `cloudflare.example.json` to `deploy/private/cloudflare.json` and set the actual Access audience. This file contains configuration, not an API credential, but remains outside Git. Start `Start-Pitch-Origin.ps1` after installing `requirements.txt`. Route the tunnel to HTTP `127.0.0.1:8766` and preserve/set the HTTP Host header to `pitch.gbaonvo.com`. Do not route the public hostname to the unprotected local port 8765.

Tunnel credentials stay under ignored `deploy/private/`; never commit the connector token. Put the connector token in `deploy/private/tunnel-token.txt`; use the official `cloudflared.exe` under `%USERPROFILE%\.cache\astory-deployment\`. After configuring Access and the tunnel, run `Install-Pitch-Startup.ps1` to install the owner-level Windows startup task. It checks at sign-in and every five minutes, starts missing processes in hidden windows, and keeps the token out of process arguments. `Start-Pitch-Deployment.ps1 -CheckOnly` checks configuration without starting services. Closing the website does not stop the workers. Powering off this PC does.

## GitHub contents and private state

`vngiabao/pitch` must remain private. It holds application code, tests, scripts, design documentation, starter pitch drafts and a compressed consistent database snapshot under `private-snapshots/`. The snapshot contains private company memory, application drafts, evidence, source paths and receipt history. It does not contain the 3GB original folder or Cloudflare/Gmail credentials. Original material files stay at their existing paths and are available through the authenticated site while this PC is online.

The snapshot is a recovery artifact, not a live database or automatically restored state. Recheck schedules, queued work, email delivery states and individual application approvals before starting workers on a restored machine. Do not make the repository public or publish snapshot files as website assets. Runtime reports, screenshots, credentials, generated release packages and live SQLite files stay ignored.

See https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/ for the origin validation boundary and https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/ for Access-protected publication.
