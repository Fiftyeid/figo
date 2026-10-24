# Problems log (War Factor, as of 2026-10-24)

## Status of the build
- ffmpeg: 7.0.2 (static, venv). `ffmpeg -version` works. Video assembly is not started.
- Voice samples: three AI voices (voice-00, voice-01, voice-02). Each reads the same 50-word hook. Durations 20.98 s, 17.95 s, 19.88 s. The speech tool does not name the provider. The earlier 21-word samples were replaced (in git history).
- Narration: NOT generated. Blocked until the user chooses a voice.
- Captions (SRT): NOT produced. Needs narration audio timing.
- Graphics layers (PNG/alpha), composite preview, thumbnail: NOT produced. Blocked on the palette and layout approval step and on the voice choice. The composite preview also needs the footage, which the sandbox cannot download from DVIDS.
- Music and music_license.txt: NOT started. Music is chosen after the voice.
- final_video.mp4: NOT produced. Depends on all of the above and on the user's DVIDS downloads.
- unverified.txt: updated (G1 resolved, G2 resolved, G5 and G6 added).

## Runtime
- Rev 3 VO is 772 words, about 5:09 at 150 wpm. Estimated runtime with graphics about 5:50.
- The 6:15 to 7:15 target is NOT met by verified content. No padding was added, as instructed.
- Options for the user: (a) accept about 5:45; (b) add a verified section (for example, further type breakdowns from CBO or the almanac); (c) relax the target.

## Figures and sources
- CBO row 53 (H-60): trend table 2023 value is 2.09 thousand. The earlier note said 2.10. Corrected in sources.csv.
- CBO row 56 (H-47): text says 400, trend table says 0.43 thousand, variant table says 450 (the variant table is from an earlier read; not re-read this turn). Displayed as "about 400 (CBO text)" per the user's decision.
- CBO row 61 (definition comparability): NOT confirmed. Spoken caveat kept.
- Navy + Marine Corps combined (about 4,000, FY2022): the primary DoD document is subscriber-only and was not read. Cited via CRS IF12803. The source does not say whether the figure includes unmanned aircraft. Script now says this.
- Derived figures shown on screen: Air Force manned 4,959 (5,286 minus 327), Army with drones about 4,600 (3,900 plus 700), and the Air Force-Army gap ("more than a thousand"; 4,959 minus about 3,900). Derived figures must be labelled "derived" on screen.
- Hook is 50 words (not 45), so the 25 to 28 s target is met with the on-screen beat.
- User-reported search volume (about 8,700) and vidIQ score (97) are NOT verified and are NOT in the description or the video.

## Footage
- 15 clips in the list. Clip 16 (C-17 flyover, 1024038) is on hold: its event context is football-game flyovers. Your decision.
- Visual checks for all 15 clips are PENDING. The sandbox shows "HLS playlist request error" on DVIDS pages, so no clip could be watched.
- Credit mismatch: 1024004 (DC ANG) credit line says "U.S. Army National Guard video." Copy the exact line from the page; the mismatch needs a decision.
- Caption wording to decide: 1025674 (KC-135) and 1025348 (F-35C) say "U.S. Central Command area of responsibility." This is not a named operation, but it is your call.
- Exercise names kept in captions: 972113 (REFORPAC), 1027256 (Beverly Sunrise 27-01), 1025001 (MOBEX 26), 1019464 (Harpoon, from an earlier draft; confirm on the page).
- Search snippet vs page mismatch for 1026939: the search snippet described a fixed-wing launch; the fetched page says helicopter flight operations (Aug 12, 2026). The page version is used.
- Air Force section has 8 clips in about 44 s of estimated VO. Some clips will need to run under graphics or be cut. Check in the edit.
- Alternate for clip 2: 1009682 (F-16 launches, Rickenbacker). Its license was not re-checked on 10-24.
- Blur: all clips will need tail numbers and unit markings checked. The DoD copyright page requires obscuring them in commercial use.
- B-2A (1026631): skipped per decision 7. No aircraft-only segment was checked.
- A-10C: clip dropped per decision 2. 261 stays on screen only.

## Copyright and publishing
- DoW sentence in the description: copied from https://www.dvidshub.net/about/copyright on 2026-10-24. Re-copy on publish day (the DVIDS copyright page moved from /copyright to /about/copyright earlier; the old URL returned 404).
- Nothing is published or uploaded.

## Process notes
- Rev 3 script: header updated; hook and race wording updated; Army mission sentence attributed to CRS; H-47 wording updated.
- Two earlier problems were fixed: a title with a year (2023) on a card that includes FY2022 data was removed from title option 2, and the Air Force sentence about "five core functions" (not sourced) was removed.
- The old footage log and step-6 drafts were overwritten. They listed replaced clips.
