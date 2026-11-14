# Times of the calculation

`tests/test_calculation.py` checks `calculate_prayer_times()` against two kinds of
times.

## The times of mawaqit-js

`mawaqit-js/mawaqit-js.json` holds the times of `calculatePrayerTimes()` of
[mawaqit-js](https://github.com/mawaqit/mawaqit-js) 1.5.0, the TypeScript twin of
this library, whose own tests check it against adhan-js. Python must give the same
minutes on every day of it: random positions from pole to pole, in the time zone of
their longitude or in a real one, from the year 1000 to 9999, with every method,
madhab and high-latitude rule, adjustments and Hijri adjustments; the days around
Ramadan for Umm al-Qura; and every day of a year in Paris, Lille, Tromsø, Makkah,
Kiritimati, Kashgar, Santiago and McMurdo. It also holds the names of the methods
and the default settings of the countries.

`mawaqit-js/generate.mjs` writes it. To write it again, for a new version of
mawaqit-js, run it with Node.js where `@mawaqit/sdk` is installed:

```sh
cd "$(mktemp -d)" && npm install @mawaqit/sdk@1.5.0
node --input-type=module < "$OLDPWD/tests/data/calculation/mawaqit-js/generate.mjs" \
  > "$OLDPWD/tests/data/calculation/mawaqit-js/mawaqit-js.json"
```

The test expects version 1.5.0: change it with the version installed.

## Reference times of the MAWAQIT app

The prayer times of the MAWAQIT mobile app 4.4.0 for a position (_Prayer times by
location_), for every day of 2027, from the calculation of the app itself. The test
calculates the same days with the same settings and expects the same times, with
Dhuhr one minute later, as mawaqit/mawaqit-js#16 decided.

They are the files of `tests/data/calculation/` in mawaqit-js, copied here. One
JSON file per place and settings, named like `paris-angle_15.json`, with the names
of mawaqit-js:

```json
{
  "source": "The calculation of the MAWAQIT app 4.4.0, run for every day of 2027 on 2026-11-14",
  "position": { "latitude": 48.8566, "longitude": 2.3522, "timeZone": "Europe/Paris" },
  "settings": {
    "method": "angle_15",
    "madhab": "shafi",
    "highLatitudeRule": "twilight_angle",
    "adjustments": {}
  },
  "options": { "hijriAdjustment": 0 },
  "differences": { "2027-06-05": { "fajr": "04:13" } },
  "days": {
    "2027-06-21": ["03:45", "05:47", "13:57", "18:04", "21:58", "23:58"]
  }
}
```

- `position`: the latitude and longitude, with 4 decimals, and the time zone of the
  phone.
- `settings` and `options`: those of `calculatePrayerTimes()`, set the same in the
  app.
- `days`: Fajr, Shuruq, Dhuhr, Asr, Maghrib and Isha, as the app shows them.
- `differences`: the times where the library gives another minute than the app, by
  day and prayer. 8 of the 32,850 times, all of them a Fajr one minute earlier, on a
  day where the high-latitude rule sets Fajr less than a second from the
  half-minute: the app rounds there to the next minute, mawaqit-js keeps the time of
  adhan-js, and this library the time of mawaqit-js.

The files cover Paris (`angle_15`, `muslims_of_france`), Lille and Oslo (every
high-latitude rule), London (`north_america`), Tromsø (the midnight sun), Montreal
(the Hanafi Asr), Jakarta (`singapore`), Algiers (`algeria`), Moscow (`russia`),
Sydney (the southern hemisphere), Makkah, and Toulouse (`custom` angles with
adjustments).

Two settings are left out:

- `umm_al_qura` and `qatar`: Isha is 90 minutes after Maghrib here, as these
  methods define it, where the app uses an angle of 18°. Makkah is recorded with
  the app's angles, as `custom`.
- `morocco`: Morocco went back to UTC on 2026-09-20, and a system with older time
  zone data shows its times an hour off. The method has the angles of `algeria`.
