# Uppdragsbeskrivning: VG Dashboard – automatiserad regional statistikpipeline

## Vem är användaren

Jakob Lindahl arbetar som utvecklingsledare (utvecklingsledare) på Länsstyrelsen Västra Götaland (Lst VG), en statlig myndighet med ca 926 anställda. Han bygger intern verktyg och automationer för att stödja myndighetens analysfunktion inom regional utveckling. Han har begränsad tillgång till lokal Python-installation och arbetar primärt via webbgränssnitt (n8n, Supabase, GitHub, Claude.ai).

---

## Vad som ska byggas

Ett **automatiserat system** som varje månad hämtar officiell statistik om Västra Götalands 49 kommuner från flera datakällor, lagrar datan i en central databas, och presenterar den i ett interaktivt webbaserat dashboard — utan att någon manuellt behöver ladda ner eller sammanställa data.

Systemet ska göra det möjligt för Lst VG:s analytiker att snabbt få en samlad bild av regional ekonomi, arbetsmarknad och näringsliv för VG:s 49 kommuner, med möjlighet att jämföra kommuner med varandra och med andra regioner i Sverige.

---

## Systemarkitektur (befintlig, delvis fungerande)

Fyra komponenter samverkar:

### 1. n8n (automationsplattform)
- Körs på `n8n-edu.walkstripe.cc`
- Styr hela datainsamlingsflödet via ett schema-triggerbaserat workflow
- Hämtar en lista med aktiva indikatorer från Supabase (`vg_indikatorer`)
- Loopar igenom varje indikator och skickar till rätt datakälla via en Switch-nod (SCB / Kolada / AF)
- Normaliserar rådata till ett gemensamt format
- Sparar (upserterar) i Supabase

### 2. Supabase (databas)
- Projekt: `xqeyxlonarwcqykbemsg.supabase.co`
- Två centrala tabeller:
  - `vg_indikatorer` — konfigurationslista över indikatorer (kpi, källa, tabell_id, filter, kolada_id etc.)
  - `vg_kommundata` — all insamlad statistik, gemensamt format oavsett källa (kommun_kod, kommun_namn, ar, kpi, bransch, kon, varde, enhet)
- Unik nyckel: `(kommun_kod, kpi, ar, bransch, kon)`

### 3. Mellanserver på Render.com
- Python/FastAPI-server: `scb-mcp-v2.onrender.com`
- GitHub-repo: `github.com/Larjaklin/scb-mcp-v2`
- Hanterar komplexa API-anrop mot SCB:s och Koladas API:er åt n8n
- Endpoints: `POST /query` (SCB), `POST /kolada`, `GET /af` (AF, under utredning)
- OBS: körs på Render.com gratisnivå → kallstartar efter inaktivitet (30-60 sek fördröjning)

### 4. Dashboard (GitHub Pages)
- Frontend: `github.com/Larjaklin/vg-dashboard`
- Publicerad: `https://larjaklin.github.io/vg-dashboard`
- Hämtar data direkt från Supabase REST API (anon-nyckel) i webbläsaren
- Byggd med vanilla JS + Leaflet.js (karta) + Chart.js (diagram)
- Fristående HTML-fil utan byggsteg

---

## Datakällor

### SCB (Statistiska centralbyrån) — primär källa
- API: SCB PxWebAPI 2.0
- Anropas via mellanservern med `table_id` + `variable_filters` (semikolon-separerade variabel=värde-par)
- Svarar i JSON-stat2-format (kompakt matrisformat som kräver en parser)
- Befintliga indikatorer:
  - `brp_per_inv` — BRP per invånare, TAB3143
  - `brp_per_syss` — BRP per sysselsatt, TAB3143
  - `sysselsatta_naringsgren` — Sysselsatta 15-74 år per nearingsgren (SNI 2007), kön och år, TAB3204

### Kolada (kommunal databas)
- API: Koladas öppna REST API
- Anropas via mellanservern, hämtar alla 49 VG-kommuner sekventiellt
- Befintlig indikator: `arbetslöshet` — Öppen arbetslöshet, KPI N00708

### Arbetsförmedlingen (AF) — under utredning, ej fungerande
- AF saknar öppet API för kommunal månadsstatistik
- Deras Excel-filer på webben innehåller bara riksaggregat, inte kommunnivå
- Grenen finns i n8n men är satt till "Continue on error" (kraschar alltid pga att n8n-instansen inte tillåter `xlsx`-modulen)
- Som interim-lösning används Kolada N00708 istället

---

## Databasschema (förenklat)

```sql
-- Indikatorlista (konfiguration)
CREATE TABLE vg_indikatorer (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  aktiv BOOLEAN,
  kalla TEXT,           -- 'SCB', 'Kolada', 'AF', 'Beräknad'
  kpi TEXT,             -- kort namn, t.ex. 'brp_per_inv'
  beskrivning TEXT,
  enhet TEXT,
  tabell_id TEXT,       -- SCB-tabellnamn, t.ex. 'TAB3204'
  filter TEXT,          -- SCB variable_filters-sträng
  kolada_id TEXT,       -- Kolada KPI-kod, t.ex. 'N00708'
  af_id TEXT,
  skapad TIMESTAMPTZ DEFAULT now()
);

-- Insamlad statistik (alla källor, gemensamt format)
CREATE TABLE vg_kommundata (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kommun_kod TEXT,
  kommun_namn TEXT,
  ar INTEGER,
  manad INTEGER,
  kalla TEXT,
  kpi TEXT,
  bransch TEXT DEFAULT 'alla',   -- SNI-kod eller 'alla'
  kon TEXT DEFAULT 'totalt',     -- 'man', 'kvinna', 'totalt'
  varde NUMERIC,
  enhet TEXT,
  uppdaterad TIMESTAMPTZ DEFAULT now(),
  UNIQUE (kommun_kod, kpi, ar, bransch, kon)
);
```

---

## Dashboard-funktionalitet (befintlig, v10)

- **Nivå-väljare**: Kommun (VG:s 49 kommuner) eller Län (VG vs Stockholm vs Skåne)
- **Indikatorväljare**: dropdown med alla aktiva indikatorer från `vg_indikatorer`
- **Filtrering**: år, nearingsgren (om relevant), kön (om relevant)
- **Områdesväljare**: multiselect-komponent med kryssrutor för kommuner/län — styr karta, diagram och tabell
- **Visualiseringsväljare**: Karta (choropleth, Leaflet) / Stapeldiagram / Linjediagram (Chart.js)
- **Tabell**: sorterbar tabell under kartan/diagrammet
- **Länsjämförelse**: VG, Stockholm, Skåne — använder för tillfället PLATSHÅLLARDATA för Stockholm/Skåne (tydligt markerat i UI), väntar på riktig länsdatakälla
- **Paginering**: hämtar data i omgångar om 1000 rader (Supabase-begränsning)

---

## Pågående och kommande uppgifter

### Akut felsökning (högst prioritet)
Det stora SCB-anropet för `sysselsatta_naringsgren` (49 kommuner × 15 branscher × 3 kön × 5 år) misslyckas konsekvent i n8n-pipeline. Loop Over Items processar bara 4 av 6 indikatorer (Sysselsatta och en AF-indikator faller bort varje gång). Se överlämningsdokumentet `overlamning_vg_dashboard.md` för detaljerad felsökningsstatus.

### Planerade utökningar
1. **Fler SCB-indikatorer** — TAB5179 (investeringsutgifter per kommun) är identifierad och redo att läggas till enligt samma mönster som befintliga
2. **Beräknade indikatorer** — t.ex. "andel anställda i byggindustrin" = bransch F ÷ totalt per kommun/år, beräknad i n8n efter att `sysselsatta_naringsgren` hämtats och sparad som egen kpi-rad (`andel_bygg`) i `vg_kommundata`
3. **Riktig länsdata** — ersätta platshållardata för Stockholm/Skåne med faktiska SCB läns-/regionindikatorer
4. **Diakritik-fix** — äldre körningar av BRP/Kolada-normaliseringskoden producerade namn utan å/ä/ö ("Goteborg" istället för "Göteborg"), en skuggrad-variant som lever kvar i databasen
5. **Instruktionsbok → Word** — Markdown-versionen är klar, ska konverteras till Word för intern distribution

### Designprinciper att respektera
- Konfigurationsdriven pipeline: nya indikatorer läggs till via en SQL-rad i `vg_indikatorer`, inga kod-ändringar i n8n
- Gemensamt lagringsformat för alla källor: samma `vg_kommundata`-tabell och same upsert-logik oavsett om data kommer från SCB, Kolada, eller är beräknad
- Dashboard hämtar direkt från Supabase (ingen mellanserver för läsning) — enkelhet och lägre latens
- Tydlig markering av platshållardata i UI
- Allt ska kunna förvaltas av en icke-teknisk efterträdare med stöd av instruktionsboken

---

## Tekniska begränsningar att hålla kvar i minnet

- n8n-instansen tillåter INTE `xlsx`-modulen i Code-noder (AF-grenen kraschar alltid av denna anledning)
- Render.com gratisnivå: mellanservern kallstartar efter inaktivitet, kan ta 30-60 sek att svara på första anropet
- Supabase gratisnivå: max 1000 rader per API-anrop, kräver paginering (Range-header)
- GitHub Pages: aggressiv CDN-cache, kräver cache-busting (`?cachebust=`) vid testning av ny uppladdad version
- GeoJSON för VG-kommuner: genereras med Python-paketet `swemaps` som redan levererar koordinater i EPSG:4326 — ingen CRS-transformation ska göras (tidigare bugg som kollapsade koordinaterna)
- Jakob kan inte installera Python lokalt — all serverkod körs på Render.com, all frontend på GitHub Pages
