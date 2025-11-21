GENERAL:

- One request at a time. If 429 Too Many Requests occurs, wait ≥ 2s and retry (exponential backoff).
- If 400/500: check hex length/max ~80 bytes and command format.
- Parse and produce hex strictly; helper toU16BE/fromU16BE.

CORE COMMANDS (read/write):

- Device type: GET /api/rest/FF00 → "44" means ZEWA i-SAFE
- Serial number: GET /api/rest/0600 → 4B serial (hex)
- FW version: GET /api/rest/0100 → 3B version
- Commission date: GET /api/rest/0E00 → 4B Unix timestamp (BE)
- Total water (L): GET /api/rest/2800 → 4B total liters

Valve/modes:

- Ack alarm: /api/rest/6300
- Close valve: /api/rest/5100
- Open valve: /api/rest/5200
- Sleep start/end: /api/rest/5400 /api/rest/5500
- Vacation start/end: /api/rest/5700 /api/rest/5800
- Micro-leak test: /api/rest/5C00
- Learn mode start: /api/rest/5D00

Limits & settings:

- Read absence limits: /api/rest/5E00 → 6B: [flow l/h (U16), volume l (U16), time min (U16)]
- Write absence limits: /api/rest/5F00<flow><volume><minutes> (each U16 BE)
- Write leak preset (incl. vacation type & maxima): /api/rest/50<7B>
  - B1=vacation type (0=off,1=U1,2=U2,3=U3)
  - B2-3=max flow l/h (U16), B4-5=max volume l (U16), B6-7=max duration min (U16)
- Set sleep hours: /api/rest/53<1B hours 1..10> (then /5400 to start)
- Read sleep hours: /api/rest/6600 → 1B hours
- Set vacation type: /api/rest/56<1B 0..3>
- Read micro-leak mode: /api/rest/6500 → 0=off,1=notify,2=notify+close
- Set micro-leak mode: /api/rest/5B<1B 0|1|2>

Absence windows (index 0..6):

- Read window i: /api/rest/60<1B index> → 6B: startDay(0=Sun..6=Sat), startH, startM, stopDay, stopH, stopM
- Write window i: /api/rest/61<index><startDay><startH><startM><stopDay><stopH><stopM>
- Delete window i: /api/rest/6200<index> → subsequent read returns 000000000000

Clock:

- Read datetime: /api/rest/5900 → 6B: day,month,year, hour,min,sec
- Set datetime: /api/rest/5A<6B>

Statistics (liters):

- Day: /api/rest/FB<4B day> → 8×4B (0:00,3:00,…,21:00)
- Week: /api/rest/FC<3B week/yr> → 7×4B (Mon..Sun)
- Month: /api/rest/FD<3B m/yr> → up to 31×4B
- Year: /api/rest/FE<2B yr> → 12×4B

CONSTRAINTS:

- Implement safe fetch with Basic Auth and backoff (≥2s on 429).
- Provide hex helpers (U8/U16/U32 BE).
- Export a clean API with typed models for parsed responses.
- Include examples for closing/opening valve, configuring sleep, writing limits.
