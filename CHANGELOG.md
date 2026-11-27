# Changelog — Squadron Ready Room

What changes in Squadron Ready Room, release by release, for the people who use it.

### Version numbers

Each release is a GitHub release tagged `RR-V<major>.<minor>.<patch>`:

- **Major** (**x**.0.0): a redesign, or a file format that breaks.
- **Minor** (1.**x**.0): a new tool, screen or feature, or a change visible everywhere.
- **Patch** (1.2.**x**): fixes.

The footer of the home page shows the version the server runs: `RR-V1.2.0` for a release, `RR-V1.2.0+3` for the third update installed on the server since that release.

## Unreleased

**A map of each session's destructions**
- From a session, "Map" shows where each wreck fell, by side and by type, on the map of the theatre (Syria, Germany (Cold War), Caucasus).
- Pick a pilot to show their kills: a wreck is credited by name only when it is the only one of its type. Ejections, pilots killed, take-offs and landings are listed beside the map.

**The mission list opens on the current year**
- Missions loads one year at a time: the most recent year opens first; pick another year, or "All years", in the filters.
- The squadron, year and month filters are now drop-down lists, lighter on a phone.

**A faster pilot file**
- Your logbook loads its full history only when you ask for it with "Show all".

**Lists drawn in the style of the screen**
- On Missions and on the destruction map, the filter and pilot lists now open as a sheet in the screen's paper-and-ink style, on a phone as on a computer, instead of the device's own list.
- They also work with the keyboard: arrows to move, Enter to choose, Escape to close.

**More aircraft for the squadrons**
- Squadrons and RSVP preferences can now pick 16 more aircraft: A-10C, A-10C II, AV-8B, Christen Eagle II, F-15E, F-86F, Hawk, J-11A, JF-17, Ka-50, M-2000C, MiG-15bis, MiG-19P, Mirage F1 BE, Su-33 and Yak-52.

**A side outline for every aircraft**
- The squadron header, the flight screens and the member lists now show a side outline for every aircraft type the wing can fly, not only seven.

## RR-V1.1.0 — 2026-11-26

Every time now reads in the wing's time zone, the Pilot Manual gains a Help annex, and four fixes.

**A Help annex in the Pilot Manual**
- The Pilot Manual has a new Help annex: a glossary of the Ready Room's words, each pointing to the page that explains it, and answers to the most common difficulties, from a refused sign-in to a missing flight.

**Pilot Manual brought up to date**
- The Pilot Manual now explains that times are read in the wing's time zone, with your own time added in the event sheet and form, and shown on hover in the Command Centre.
- Its Configuration chapter describes the read-only Server folders block, and its Rights chapter notes that the list of access roles is managed on that screen.

**Command Centre times in the wing's time zone**
- The Command Centre (members, archives and backups, journal, server agent, settings) and invitations show their dates and times in the wing's time zone, whatever the time zone of your device.
- Where your own time differs, hovering over a time shows it.

**Wing dates in the wing's time zone**
- The Wing home page, member files, the pilots' logbook and campaigns show their dates in the wing's time zone, whatever the time zone of your device.

**Forward after a link from an event**
- Fixed: after opening a debrief from an event sheet and changing tab, the browser's Forward button no longer brings back a screen you had left, and ‹ returns to the event sheet.

**An ACMI file that cannot be read**
- Fixed: uploading as ACMI a file that is not a Tacview archive is now refused with a clear message instead of a server error.

**Discord messages after a restart**
- Fixed: when the server restarted, an event's Discord message could keep its old answers until the next change; the Ready Room now follows Discord's sending limits.

**Times in the wing's time zone**
- The Board, the Weekly Table and the event sheet show every time in the wing's time zone, whatever the time zone of your device; when it differs, the event sheet and the event form also give your local time.
- Fixed: an event created or edited from a device in another time zone was saved at the wrong time.

**Access rights checked by a test**
- Nothing visible changes: an automated test now checks, for every address of the application and every kind of member, who gets in and who is refused.

## RR-V1.0.0 — 2026-11-25

The first public release: the web portal of a DCS World virtual squadron, behind a Discord sign-in, on a desktop, a tablet or a phone, in English and in French.

**Scheduling.**
- The Board shows the wing's trainings, missions, campaigns and free play by month, by week or as an agenda, with their series, cancellations and changes.
- Each member answers present, maybe or absent, in the Ready Room or from Discord; reminders go to those who have not answered.

**Wing and debriefings.**
- The order of battle and organisation chart of the wing, each squadron's unit file and each pilot's personal file.
- Mission debriefings built from the DCS server's logs: the roster, each flight's log, kills, shots and weapon accuracy, and an optional written account of the mission.

**Command Center.**
- Members, ranks and rights, squadrons with their crests and liveries, campaigns and reference lists.
- The server's settings on screen (time zone, Discord, the written account), backups, and the journal of every change.

**Pilot's Manual.**
- The illustrated guide to every screen, served with the application.

**Installation.**
- Docker Compose runs the application and PostgreSQL on a Linux server; members sign in through a Discord application.
- An installation guide in English and in French, online and as two PDF files attached to this release, from preparing the server to backups, updates and uninstalling.

**Known issue.**
- The DCS server agent, which sends the server's logs to the Ready Room, is not published yet: it will come with its own first release. Until then, debriefings are uploaded by hand.
