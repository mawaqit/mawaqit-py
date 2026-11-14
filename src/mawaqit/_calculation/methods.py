"""The methods of calculation, their names, and the default settings of a country."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

from mawaqit._language import language_of

from .settings import CalculationMethod, CalculationSettings

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True)
class CalculationMethodAngles:
    """The angles of a method of `CALCULATION_METHODS`.

    Attributes:
        fajr_angle: The angle of the sun below the horizon at Fajr, in degrees.
        isha_angle: The angle at Isha, in degrees, or `None` when Isha is a time after
            Maghrib.
        isha_minutes_after_maghrib: The minutes from Maghrib, before its adjustment,
            to Isha, or `None` when Isha has an angle. 90 for Umm al-Qura, 120 during
            Ramadan, and 90 for Qatar.
    """

    fajr_angle: float
    isha_angle: float | None
    isha_minutes_after_maghrib: int | None


def _angles(fajr_angle: float, isha_angle: float) -> CalculationMethodAngles:
    return CalculationMethodAngles(fajr_angle, isha_angle, None)


CALCULATION_METHODS: Mapping[CalculationMethod, CalculationMethodAngles] = (
    MappingProxyType(
        {
            "muslim_world_league": _angles(18, 17),
            "muslims_of_france": _angles(12, 12),
            "angle_15": _angles(15, 15),
            "algeria": _angles(18, 17),
            "morocco": _angles(18, 17),
            "egypt": _angles(19.5, 17.5),
            "karachi": _angles(18, 18),
            "umm_al_qura": CalculationMethodAngles(18.5, None, 90),
            "gulf": _angles(18.2, 18.2),
            "moonsighting_committee": _angles(18, 18),
            "north_america": _angles(15, 15),
            "kuwait": _angles(18, 17.5),
            "qatar": CalculationMethodAngles(18, None, 90),
            "singapore": _angles(20, 18),
            "turkey": _angles(18, 17),
            "tehran": _angles(17.7, 14),
            "russia": _angles(16, 15),
        }
    )
)
"""The angles of each method but `custom`.

A method has no offset of its own: Dhuhr is one minute after the solar transit for
every method, and any other minute is an adjustment of the settings. Umm al-Qura and
Qatar have a time for Isha instead of an angle.
"""

# The countries of each method. The other countries have the Muslim World League.
_COUNTRIES: tuple[tuple[CalculationMethod, str], ...] = (
    ("angle_15", "FR"),
    ("algeria", "DZ"),
    ("morocco", "MA"),
    ("umm_al_qura", "SA"),
    (
        "egypt",
        "EG IQ LB SY AO BF BI BJ BW CD CF CI CM CV DJ ER ET GA GH GM GN GQ GW KE KM LR "
        "LS LY MG ML MR MU MW MZ NA NE NG RW SC SD SL SN SO SS ST SZ TD TG TZ UG ZA ZM "
        "ZW",
    ),
    ("north_america", "CA US GB ES"),
    ("karachi", "PK IN BD AF TN OM JO MY"),
    ("singapore", "SG ID"),
    ("gulf", "AE"),
    ("kuwait", "KW"),
    ("qatar", "QA"),
    ("turkey", "TR"),
    ("tehran", "IR"),
    ("russia", "RU"),
)

_METHOD_OF_COUNTRY: dict[str, CalculationMethod] = {
    country: method for method, countries in _COUNTRIES for country in countries.split()
}

# Where the Hanafi school is the majority.
_HANAFI_COUNTRIES = frozenset({"PK", "IN", "BD", "AF"})


def default_calculation_method(country_code: str | None = None) -> CalculationMethod:
    """Return the method of calculation of a country.

    Args:
        country_code: The country, as an ISO 3166-1 alpha-2 code like `FR`.

    Returns:
        The method of the country: `angle_15` in France, for example. The Muslim World
        League for the other countries, and without a country.
    """
    return _METHOD_OF_COUNTRY.get((country_code or "").upper(), "muslim_world_league")


def default_calculation_settings(
    country_code: str | None = None,
) -> CalculationSettings:
    """Return the settings of calculation of a country, for `calculate_prayer_times()`.

    Args:
        country_code: The country, as an ISO 3166-1 alpha-2 code like `FR`.

    Returns:
        The method of the country, from `default_calculation_method()`; the Hanafi Asr
        in Pakistan, India, Bangladesh and Afghanistan, and the Shafi'i Asr elsewhere;
        the `twilight_angle` rule for high latitudes; and no adjustment.
    """
    hanafi = (country_code or "").upper() in _HANAFI_COUNTRIES
    return CalculationSettings(
        method=default_calculation_method(country_code),
        madhab="hanafi" if hanafi else "shafi",
        high_latitude_rule="twilight_angle",
    )


_ENGLISH_NAMES: dict[CalculationMethod, str] = {
    "muslim_world_league": "Muslim World League",
    "muslims_of_france": "Muslim of France (ex UOIF)",
    "angle_15": "Fajr and Isha at 15°",
    "algeria": "Algerian Ministry of Religious Affairs and Wakfs",
    "morocco": "Moroccan Ministry of Wakfs and Islamic Affairs",
    "egypt": "Egyptian General Authority of Survey",
    "karachi": "University of Islamic Sciences, Karachi",
    "umm_al_qura": "Umm al-Qura University, Makkah",
    "gulf": "The Gulf Region",
    "moonsighting_committee": "Moon Sighting Committee",
    "north_america": "Islamic Society of North America",
    "kuwait": "Kuwait",
    "qatar": "Qatar",
    "singapore": "Singapore",
    "turkey": "Turkey",
    "tehran": "Institute of Geophysics, University of Tehran",
    "russia": "Spiritual Administration of Muslims in Russia",
    "custom": "Custom angles",
}

# The names of the MAWAQIT app. It has none for `angle_15`, named here with its names of
# Fajr and Isha.
_NAMES: dict[str, dict[CalculationMethod, str]] = {
    "ar": {
        "muslim_world_league": "رابطة العالم الإسلامي",
        "muslims_of_france": "المسلمون في فرنسا (مثال: الاتحاد الإسلامي للعلماء في فرنسا)",  # noqa: E501
        "angle_15": "الفجر والعشاء بزاوية 15°",
        "algeria": "وزارة الشؤون الدينية والأوقاف في الجزائر",
        "morocco": "وزارة الأوقاف والشؤون الإسلامية في المغرب",
        "egypt": "الهيئة العامة للمساحة في مصر",
        "karachi": "جامعة العلوم الإسلامية في كراتشي",
        "umm_al_qura": "جامعة أم القرى في مكة المكرمة",
        "gulf": "المنطقة الخليجية",
        "moonsighting_committee": "لجنة رؤية الهلال",
        "north_america": "الجمعية الإسلامية في أمريكا الشمالية",
        "kuwait": "الكويت",
        "qatar": "قطر",
        "singapore": "سنغافورة",
        "turkey": "تركيا",
        "tehran": "معهد الجيوفيزياء، جامعة طهران",
        "russia": "الإدارة الروحية للمسلمين في روسيا",
        "custom": "زوايا مخصصة",
    },
    "de": {
        "muslim_world_league": "Liga der muslimischen Welt",
        "muslims_of_france": "Musulman de France (ehemals UOIF)",
        "angle_15": "Fadjr und Ishaa bei 15°",
        "algeria": "Algerisches Ministerium für religiöse Angelegenheiten und Wakfs",
        "morocco": "Marokkanisches Ministerium für Wakfs und Islamische Angelegenheiten",  # noqa: E501
        "egypt": "Egyptian General Authority of Survey",
        "karachi": "Universität für Islamische Wissenschaften, Karachi",
        "umm_al_qura": "Universität Umm al-Qura, Mekka",
        "gulf": "Golfregion",
        "moonsighting_committee": "Mondbeobachtungskomitee",
        "north_america": "Islamische Gesellschaft Nordamerikas",
        "kuwait": "Kuwait",
        "qatar": "Katar",
        "singapore": "Singapur",
        "turkey": "Türkei",
        "tehran": "Institut für Geophysik, Universität Teheran",
        "russia": "Geistliche Verwaltung der Muslime in Russland",
        "custom": "Eigene Winkel",
    },
    "en": _ENGLISH_NAMES,
    "fr": {
        "muslim_world_league": "Ligue du monde musulman",
        "muslims_of_france": "Musulman de France (ancien UOIF)",
        "angle_15": "Fajr et Isha à 15°",
        "algeria": "Ministère des affaires religieuses et des wakfs Algérien",
        "morocco": "Ministère des wakfs et affaires islamiques Marocain",
        "egypt": "Egyptian General Authority of Survey",
        "karachi": "Université des sciences islamiques, Karachi",
        "umm_al_qura": "Université Umm al-Qura, La Mecque",
        "gulf": "Région du Golfe",
        "moonsighting_committee": "Comité d'observation de la lune",
        "north_america": "Société islamique d'Amérique du Nord",
        "kuwait": "Koweït",
        "qatar": "Qatar",
        "singapore": "Singapour",
        "turkey": "Turquie",
        "tehran": "Institut de géophysique, Université de Téhéran",
        "russia": "Administration spirituelle des musulmans en Russie",
        "custom": "Angles personnalisés",
    },
    "tr": {
        "muslim_world_league": "Müslüman Dünya Ligi",
        "muslims_of_france": "Musulman de France (eski UOIF)",
        "angle_15": "Sabah ve Yatsı için 15°",
        "algeria": "Cezayir Din İşleri ve Vakıflar Bakanlığı",
        "morocco": "Fas Vakıflar ve İslami İşler Bakanlığı",
        "egypt": "Egyptian General Authority of Survey",
        "karachi": "University of Islamic Sciences, Karachi",
        "umm_al_qura": "Umm al-Qura Üniversitesi, Mekke",
        "gulf": "Körfez Bölgesi",
        "moonsighting_committee": "Ay Gözlem Komitesi",
        "north_america": "Islamic Society of North America",
        "kuwait": "Kuveyt",
        "qatar": "Katar",
        "singapore": "Singapur",
        "turkey": "Türkiye",
        "tehran": "Institute of Geophysics, University of Tehran",
        "russia": "Rusya'daki Müslümanların Ruhani Yönetimi",
        "custom": "Özel açılar",
    },
}


def calculation_method_name(method: CalculationMethod, language: str = "en") -> str:
    """Return the name of a method of calculation, like `Muslim World League`.

    Args:
        method: The method.
        language: A language, like `fr`, or a language tag, like `fr-FR` or `fr_FR`.
            Arabic, English, French, German and Turkish have the names of the MAWAQIT
            app; the other languages get the English name.

    Returns:
        The name of the method in this language.
    """
    return _NAMES.get(language_of(language), _ENGLISH_NAMES)[method]
