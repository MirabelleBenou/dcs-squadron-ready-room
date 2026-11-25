# Changelog — Squadron Ready Room

What changes in Squadron Ready Room, release by release, for the people who use it.

### Version numbers

Each release is a GitHub release tagged `RR-V<major>.<minor>.<patch>`:

- **Major** (**x**.0.0): a redesign, or a file format that breaks.
- **Minor** (1.**x**.0): a new tool, screen or feature, or a change visible everywhere.
- **Patch** (1.2.**x**): fixes.

The footer of the home page shows the version the server runs: `RR-V1.2.0` for a release, `RR-V1.2.0+3` for the third update installed on the server since that release.

## Unreleased

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
