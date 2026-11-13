# Shape brief · Founder OS home screen (Nov 11, 2026)

Written before any UI edit for the home screen. Lead skill: impeccable (product UI on shadcn). Mode: Operate, with one arrival moment.

## Why
Bao, Nov 11: "from now on all my website need a good landing screen/motion homescreen/theme loading homepage or whatever before going into the content"; "not need to be a multi second load like my personal website, but at least the home screen doesnt take you to the dashboard of what to do like pitch agent and serial startup rn." Reference: Serial Startup's paper-model home; "brainstorm like it, not copy". The logo: "can scrap it". Desktop first: "care less about phone app design for now".

## Bao's pick
"2 · Outbox wall" (Nov 11), from three scenes shown as pictures (docs/design-concepts/2026-11-11-opening/home-scenes.jpg).

## The screen
- **Job:** the front door. Bao lands, sees his company's applications as one crafted object, reads one line on where things stand, and goes in.
- **Zones (1366 and 1920):** the picture is the whole screen. Top-left: the name "Founder OS" (type only, no mark). Middle band: the outbox wall model. Bottom-left: greeting (display size), one line of live facts, one button. Nothing else: no nav, no panels, no second action.
- **Reading order:** picture, greeting, line, button.
- **The line (live, from the same data as Today):** accepted and waiting counts, then the next deadline: "5 accepted, 7 waiting on results. Duquesne closes in 4 days." The deadline phrase is red only when it is within 14 days. With no deadline: the counts only. If the data fails to load: the greeting and the button still show; the line is left out.
- **The way in:** "Open today" goes to Today (/next/today). Today's brand link returns home.
- **The picture:** a GPT render of the outbox wall in The Turn palette, impressionistic (no countable state baked in), served by the app as one WebP under about 200 KB, with the paper colour as the fallback ground.
- **The moment (once, under about 600 ms, reduced-motion still):** the picture settles in, the words rise, and the two counts tick up to their values. The button works from the first frame.
- **Type:** Switzer; greeting at display size (clamp 44px to 5.5rem), line 20px to 1.75rem, button 18px and up, all scaling with the window. Nothing under 14px.
- **States:** loading shows the picture and greeting at once (the line arrives with the data); error keeps the screen usable.
- **Phone:** only kept from breaking: picture cropped toward the navy envelope, text and a full-width button below it, no sideways scroll.

## Not in scope
A new logo, new navigation, or changes to Today beyond its links.
