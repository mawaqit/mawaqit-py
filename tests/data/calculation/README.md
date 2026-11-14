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

The prayer times the MAWAQIT mobile app calculates for a position (_Prayer times by
location_), copied by hand. The test calculates the same days with the same
settings and expects the same times, with Dhuhr one minute later, as
mawaqit/mawaqit-js#16 decided. Until a file is recorded, the test is skipped.

They are the files of `tests/data/calculation/` in mawaqit-js: copy them here. One
JSON file per place and settings, named like `paris-angle_15.json`, with the names
of mawaqit-js:

```json
{
  "source": "MAWAQIT 5.4.2 on Android, recorded on 2026-11-20",
  "position": { "latitude": 48.8566, "longitude": 2.3522, "timeZone": "Europe/Paris" },
  "settings": {
    "method": "angle_15",
    "madhab": "shafi",
    "highLatitudeRule": "twilight_angle",
    "adjustments": {}
  },
  "options": { "hijriAdjustment": 0 },
  "days": {
    "2027-06-21": ["03:45", "05:47", "13:57", "18:04", "21:58", "23:58"]
  }
}
```

- `position`: the latitude and longitude the app uses, with 4 decimals, and the
  time zone of the phone.
- `settings` and `options`: those of `calculatePrayerTimes()`, set the same in the
  app. Umm al-Qura needs the `hijriAdjustment` of the app, which says when Ramadan
  starts.
- `days`: Fajr, Shuruq, Dhuhr, Asr, Maghrib and Isha, as the app shows them.

To record, as listed in mawaqit/mawaqit-js#16:

- Paris, FR: `angle_15` and `muslims_of_france`, in June and December
- Lille, FR: `muslim_world_league` on 21 June, where the high-latitude rule decides
  Fajr
- London, GB: `north_america`, in June
- Oslo, NO: `muslim_world_league`, in June, where the rule decides Fajr and Isha
- Makkah, SA: `umm_al_qura`, in Ramadan and outside it
- Montreal, CA: the Hanafi Asr
- Jakarta, ID: `singapore`
- Algiers, DZ; Casablanca, MA; Moscow, RU: the method of their country
- Tromsø, NO: in June, when the sun does not set
- A `custom` setting with adjustments
