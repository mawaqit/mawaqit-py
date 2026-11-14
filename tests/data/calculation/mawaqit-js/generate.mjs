// Write the times of calculatePrayerTimes() of mawaqit-js, for test_calculation.py to
// expect the same: see the README of tests/data/calculation.
//
// Run from a directory where @mawaqit/sdk is installed, so that Node.js finds it:
// node --input-type=module < generate.mjs > mawaqit-js.json

import { readFileSync } from 'node:fs';
import { fromGregorian, HijriMonth } from '@mawaqit/sdk/hijri';
import {
  CALCULATION_METHODS,
  calculatePrayerTimes,
  calculationMethodName,
  defaultCalculationSettings,
} from '@mawaqit/sdk/prayer-times';

const { version } = JSON.parse(
  readFileSync('node_modules/@mawaqit/sdk/package.json', 'utf8'),
);

/** A pseudo-random number from 0 to 1, always the same from the same seed: Mulberry32. */
function randomNumbers(seed) {
  let state = seed;
  return () => {
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4_294_967_296;
  };
}

const random = randomNumbers(2026);
const pick = (items) => items[Math.floor(random() * items.length)];
const pad = (n) => String(n).padStart(2, '0');
const isoDate = (year, month, day) => `${year}-${pad(month)}-${pad(day)}`;

const METHODS = [...Object.keys(CALCULATION_METHODS), 'custom'];
const MADHABS = ['shafi', 'hanafi'];
const RULES = ['middle_of_the_night', 'seventh_of_the_night', 'twilight_angle'];
const ADJUSTED = ['fajr', 'shuruq', 'dhuhr', 'asr', 'maghrib', 'isha'];
// Zones whose rules have not changed for years, so that every tz database agrees.
const ZONES = [
  'Europe/Paris',
  'Europe/London',
  'Europe/Oslo',
  'America/New_York',
  'America/Toronto',
  'America/Santiago',
  'Australia/Sydney',
  'Pacific/Auckland',
  'Pacific/Kiritimati',
  'Asia/Riyadh',
  'Asia/Shanghai',
  'Asia/Tokyo',
  'Asia/Kolkata',
  'UTC',
];

function calculate(position, settings, options, dates) {
  const times = calculatePrayerTimes(position, settings, options);
  const days = {};
  for (const date of dates) {
    const [, month, day] = date.split('-').map(Number);
    days[date] = times.calendar[month - 1][String(day)];
  }
  return { position, settings, options, days };
}

function everyDay(year) {
  const dates = [];
  for (let day = Date.UTC(year, 0, 1); day < Date.UTC(year + 1, 0, 1); day += 86_400_000) {
    dates.push(new Date(day).toISOString().slice(0, 10));
  }
  return dates;
}

const MWL = { method: 'muslim_world_league', madhab: 'shafi', highLatitudeRule: 'twilight_angle' };

// Every day of a year, at places that each test something.
const years = [
  [{ latitude: 48.8566, longitude: 2.3522, timeZone: 'Europe/Paris' }, defaultCalculationSettings('FR'), 2026],
  [{ latitude: 50.6292, longitude: 3.0573, timeZone: 'Europe/Paris' }, MWL, 2026],
  [{ latitude: 69.6496, longitude: 18.956, timeZone: 'Europe/Oslo' }, MWL, 2026],
  [{ latitude: 21.4225, longitude: 39.8262, timeZone: 'Asia/Riyadh' }, defaultCalculationSettings('SA'), 2026],
  [{ latitude: 21.4225, longitude: 39.8262, timeZone: 'Asia/Riyadh' }, defaultCalculationSettings('SA'), 2027],
  [{ latitude: 1.87, longitude: -157.4, timeZone: 'Pacific/Kiritimati' }, MWL, 2026],
  [
    { latitude: 39.4704, longitude: 75.9898, timeZone: 'Asia/Shanghai' },
    { ...MWL, method: 'karachi', madhab: 'hanafi' },
    2026,
  ],
  [
    { latitude: -33.4489, longitude: -70.6693, timeZone: 'America/Santiago' },
    { ...MWL, highLatitudeRule: 'middle_of_the_night', adjustments: { fajr: -3, maghrib: 3 } },
    2026,
  ],
  [{ latitude: -77.85, longitude: 166.67, timeZone: 'Antarctica/McMurdo' }, MWL, 2026],
];
const cases = years.map(([position, settings, year]) =>
  calculate(position, settings, { year }, everyDay(year)),
);

// Random positions, from pole to pole, with every method, madhab and rule in turn, a
// few days of a random year each, and the start and end of Ramadan for Umm al-Qura.
for (let i = 0; i < 432; i++) {
  const method = METHODS[i % METHODS.length];
  const latitude = Math.round((random() * 180 - 90) * 1e4) / 1e4;
  const longitude = Math.round((random() * 360 - 180) * 1e4) / 1e4;
  let timeZone;
  let year;
  if (random() < 0.25) {
    timeZone = pick(ZONES);
    year = 1980 + Math.floor(random() * 61);
  } else {
    const offset = Math.round(longitude / 15);
    timeZone = offset === 0 ? 'Etc/GMT' : `Etc/GMT${offset > 0 ? '-' : '+'}${Math.abs(offset)}`;
    year = random() < 0.8 ? 1900 + Math.floor(random() * 201) : 1000 + Math.floor(random() * 9000);
  }
  const settings = {
    method,
    madhab: MADHABS[Math.floor(i / METHODS.length) % 2],
    highLatitudeRule: RULES[Math.floor(i / (METHODS.length * 2)) % 3],
  };
  if (method === 'custom') {
    settings.fajrAngle = Math.round(1 + random() * 299) / 10;
    settings.ishaAngle = Math.round(1 + random() * 299) / 10;
  }
  const adjustments = Object.fromEntries(
    ADJUSTED.filter(() => random() < 0.3).map((name) => [name, Math.floor(random() * 41) - 20]),
  );
  if (Object.keys(adjustments).length > 0) {
    settings.adjustments = adjustments;
  }
  const options = { year, hijriAdjustment: Math.floor(random() * 5) - 2 };
  const all = everyDay(year);
  const start = Math.floor(random() * 61);
  const dates = all.filter((_, n) => n % 61 === start);
  if (method === 'umm_al_qura') {
    const hijri = { hijriAdjustment: options.hijriAdjustment, hijriDateForceTo30: false };
    const ramadan = all.map((date) => fromGregorian(date, hijri).month === HijriMonth.RAMADAN);
    for (const [n, date] of all.entries()) {
      if (ramadan[n] !== (ramadan[n - 1] ?? ramadan[n])) {
        dates.push(all[n - 1], date);
      }
    }
  }
  // Every case of the year 9999 has its last day, when Python dates end.
  if (year === 9999 || i % 50 === 0) {
    dates.push(all[0], all.at(-1));
  }
  cases.push(calculate({ latitude, longitude, timeZone }, settings, options, [...new Set(dates)].sort()));
}

// The first and last years.
for (const [year, longitude, timeZone] of [
  [1000, -179.9, 'Etc/GMT+12'],
  [9999, 179.9, 'Etc/GMT-12'],
  [9999, -157.4, 'Pacific/Kiritimati'],
]) {
  const all = everyDay(year);
  const position = { latitude: 1.87, longitude, timeZone };
  cases.push(calculate(position, MWL, { year }, [...all.slice(0, 3), ...all.slice(-3)]));
}

const LANGUAGES = ['ar', 'de', 'en', 'fr', 'tr', 'fr-FR', 'tr_TR', 'es'];
const methodNames = Object.fromEntries(
  LANGUAGES.map((language) => [
    language,
    Object.fromEntries(METHODS.map((method) => [method, calculationMethodName(method, language)])),
  ]),
);
const COUNTRIES = [
  'FR DZ MA SA EG IQ LB SY AO BF BI BJ BW CD CF CI CM CV DJ ER ET GA GH GM GN GQ GW KE KM LR LS',
  'LY MG ML MR MU MW MZ NA NE NG RW SC SD SL SN SO SS ST SZ TD TG TZ UG ZA ZM ZW CA US GB ES PK',
  'IN BD AF TN OM JO MY SG ID AE KW QA TR IR RU NO DE BE CH NL IT PT fr pk',
]
  .join(' ')
  .split(' ');
const defaultSettings = Object.fromEntries(
  [...COUNTRIES, ''].map((country) => [country, defaultCalculationSettings(country)]),
);

const rows = cases.reduce((count, { days }) => count + Object.keys(days).length, 0);
const lines = [
  '{',
  `  "source": ${JSON.stringify(`calculatePrayerTimes() of @mawaqit/sdk ${version}`)},`,
  `  "version": ${JSON.stringify(version)},`,
  `  "rows": ${rows},`,
  `  "methodNames": ${JSON.stringify(methodNames)},`,
  `  "defaultSettings": ${JSON.stringify(defaultSettings)},`,
  '  "cases": [',
  cases.map((item) => `    ${JSON.stringify(item)}`).join(',\n'),
  '  ]',
  '}',
];
process.stdout.write(`${lines.join('\n')}\n`);
