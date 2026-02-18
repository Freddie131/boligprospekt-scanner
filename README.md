# BoligProspekt-Scanner (MVP)

MVP som ukentlig finner og rangerer de beste boligprospektene for investering/utleie i Sør-Norge, med høy prioritet for nærhet til Grimstad.

## Compliance

**Ingen crawling/skraping av FINN-sider er implementert.** Løsningen støtter kun:
1. **FINN API-modus** (krever partner/annonsørtilgang med `FINN_ORG_ID` + `FINN_API_KEY`)
2. **Email ingest-modus** via FINN “Lagre søk”-varsler på e-post (IMAP)

Hvis ingen datakilde er konfigurert, brukes **mock-data** for å sikre end-to-end rapportgenerering.

## Arkitektur

- Python 3.11+
- FastAPI
- SQLAlchemy + PostgreSQL
- Jobber via CLI (`python -m app run-job weekly`) og API-endepunkt
- Jinja2 HTML-rapport + WeasyPrint PDF
- Structlog
- pytest for enhetstester

## Prosjektstruktur

```
/app
  /core
  /ingest
  /domain
  /services
  /api
  /jobs
  /templates
/tests
```

## Hvordan bruke

### 1) Start med Docker Compose

```bash
docker compose up --build -d
```

### 2) Sett miljøvariabler

Kopier og juster:

```bash
cp .env.example .env
```

Velg datakilde via `INGEST_MODE`:
- `finn_api`: bruker FINN API (hvis key/orgId mangler faller jobben tilbake til email/mock)
- `email`: bruker IMAP e-post ingest (hvis IMAP ikke er satt opp faller den tilbake til mock)
- `mock`: demo/happy-path

### 3) Kjør ukesjobb lokalt

```bash
python -m app run-job weekly
```

Output: rapportfiler i `reports/` (`.html` + `.pdf` hvis WeasyPrint tilgjengelig).

### 4) Kjør API

```bash
uvicorn app.main:app --reload
```

Endepunkter:
- `GET /api/prospects` – liste prospekter
- `PATCH /api/prospects/{id}` – manuelle overstyringer (leie/opppussing/ekstra soverom)
- `POST /api/jobs/weekly` – trigge ukesrapport

## FINN “Lagre søk” e-postoppsett

1. Lag søk i FINN Eiendom med ønsket område/prisfilter.
2. Velg “Lagre søk” + e-postvarsling.
3. Sett `IMAP_USERNAME` + `IMAP_PASSWORD` (app-passord) i `.env`.
4. Kjør med `INGEST_MODE=email`.

> Hvis e-post ikke inneholder nok felter, lagres prospektet med `needs_manual_enrichment` og kan overstyres via API.

## Standard satser (overstyrbare)

- Dokumentavgift: `2.5%` (for selveier/eierseksjon)
- Tinglysingsgebyr: `545 kr` per dokument (2026)
- Default dokumenter: `2` (skjøte + pantedokument)

Alle ligger i config/.env og brukes i kalkylene.

## Tester

```bash
pytest
```

## Eksempel `.env`

Se `.env.example`.
