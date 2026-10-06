# Geographic reference 1.0.0

Reviewed on 2026-10-06. The immutable Python data snapshot in eligibility performs
no runtime file or network access. Its schema is the strict `GeographicReference`
value contract; changes to identities, aliases or membership require a new version.

Country names, ISO alpha-3 identities and regional membership come from the
[UN Statistics Division M49 English hierarchy](https://unstats.un.org/unsd/methodology/m49/).
ISO alpha-2 identities were joined by numeric M49 code against Debian `iso-codes`
4.16.0-1 (`iso_3166-1.json`), with every alpha-3 identity checked for agreement.
[iso-codes upstream](https://salsa.debian.org/iso-codes-team/iso-codes) publishes
these factual identifiers. The reviewed intersection contains 248 countries/areas;
Taiwan, absent from this M49 hierarchy, is not in this version. Unknown candidate
identities must remain unknown, including for worldwide facts.

Membership includes territories as listed by M49: South America (005) has 16
members, Latin America and the Caribbean (419) has 52, and Americas (019) has 57.
Bolivia (BO/BOL/068) belongs to all three. US and Canada belong only to Americas.
These are statistical groupings, not statements about employment authorization.

Product policy explicitly maps LATAM and Latin America to M49 419, including the
Caribbean. The regional aliases are exact, case-insensitive, whitespace-normalized
values. Bolivia additionally accepts its short name alongside the UN name.
Approved worldwide values are `worldwide`, `global`, and `anywhere in the world`,
only when extraction identifies them as explicit hiring inclusion facts. Marketing
phrases such as `Americas-friendly` and general remote language are unsupported.

To review an update, download the official English M49 hierarchy, join ISO alpha-2
identities by numeric code, verify alpha-3 agreement and uniqueness, review the
membership/alias diff, bump the reference version, and run the offline reference
and eligibility tests. Downloads are development inputs, never runtime inputs.
