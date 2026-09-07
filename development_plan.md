# AIR-DV — vývojový plán pro MVP demo

Navazuje na [product_spec.md](product_spec.md). Cílem je ukázat během krátkého dema, co AI z nahraného dokumentu skutečně přečte, které konkrétní problémy z toho plynou a komu patří jejich oprava.

## Jazyková konvence

Produktový jazyk je **angličtina**. Anglicky budou všechny prvky, které mohou vidět uživatelé či budoucí integrace: UI, findings, doporučení, reporty, exportovaný AI view, CLI výstup a chybové zprávy. Stejně tak zdrojový kód používá anglické názvy a případné komentáře v angličtině. Lokalizace není součástí MVP.

## Aktuální stav vývoje — 7. září 2026

Poslední publikovaný commit před aktuálním UI blokem: `3d19b76` na větvi `main`.

### Dokončeno

- **Fáze 0:** projektová kostra, serializovatelný datový kontrakt findings a testy.
- **Fáze 1:** normalizace Markdownu, Wordu a PDF přes Docling a Excelu přes `openpyxl`; Excel zachovává workbook, sheet, rozpoznaný titul tabulky a metadata. PDF používá obrazové placeholdery, nikdy inline Base64 data.
- **Fáze 2:** deterministické checky pro strukturu, vizuální obsah bez textového ekvivalentu, neúspěšnou extrakci, PDF OCR varování, externí reference, Excel kontext a husté řádky.
- **Fáze 3:** lokální CLI a export AI view, Markdown reportu a JSON. Krátký spouštěč z kořene projektu:

  ```bash
  ./air-dv "Data/document.docx" --report report.md
  ```

- Terminál i Markdown report obsahují status, dokument, přehled kontrol, hlavní další krok, findings s místem/důkazem/důvodem/opravou a cesty k exportům.
- V repozitáři jsou malé anonymizované fixture soubory; reálná lokální data jsou v `Data/` a jsou ignorována Gitem.
- Zdrojové lokace uvádějí řádky Markdownu, odstavce Wordu, stránky PDF a sheet/cell range Excelu, pokud je lze bezpečně namapovat.
- Aktuální ověření: **47/47 testů prochází**; integrační běh na 17stránkovém PDF vrací dva agregované warnings (37 vizuálních placeholderů a 6 OCR varování), nikoli desítky duplicitních findings.
- **Fáze 4A:** základní lokální upload UI přes FastAPI. Přijímá `.md`, `.docx`, `.pdf`, `.xlsx`, volá existující `analyse_file()` a zobrazí status, přehled kontrol i akční findings. Upload je omezen na 50 MB a po analýze se smaže z dočasného adresáře. Ověření: **50/50 testů**, včetně HTTP uploadu přes lokální server.

### Rozhodnutí a omezení

- PDF je podporovaný formát, ale OCR a vizuální layout zůstávají explicitní nejistotou: warning neznamená, že je text chybně přečtený, ale že je nutné porovnat AI view s originálními stranami.
- Confluence přímý přístup není součástí MVP. Pro jednotlivou stránku lze použít Confluence export do Wordu, který AIR-DV již podporuje.
- Budoucí Confluence HTML ZIP import dává smysl až při dostupném exportu space; individuální Confluence menu běžně nabízí pouze Word/PDF.
- Word findings odkazují na původní odstavec, Excel findings na původní sheet a cell range a PDF findings na původní stránku, pokud lze extrahovaný blok bezpečně mapovat. Markdown findings odkazují na řádek souboru.
- `uv` v tomto headless prostředí při některých příkazech padá v macOS systémové knihovně; vytvořené `.venv` funguje a testy se spouštějí přes ni.

### Doporučený další blok

**Fáze 4B — rozšíření výsledku UI:** nad existujícím uploadem zobrazit AI view a nabídnout stažení Markdown reportu / AI view / JSON. Až po ověření této části následuje Fáze 5: kalibrace nálezů na reálných souborech z `Data/`.

### Handoff pro příští restart

- Začít **Fází 4, blok 4B**: rozšířit existující `air_dv.web` o AI view a exporty z již vytvořeného `AnalysisResult`; nepřepisovat logiku normalizace ani checků.
- Podporované uploady zůstávají `.md`, `.docx`, `.pdf`, `.xlsx`. Soubory i odvozené exporty musí zůstat dočasné a lokální.
- Ověřit UI s jedním anonymizovaným fixture pro každý formát; jako dodatečný lokální integrační vzorek lze použít soubory v `Data/`, které nesmějí do Gitu.
- Po 4B se zastavit, ověřit AI view a stažení v prohlížeči a teprve poté rozhodnout o filtrech findings nebo kalibraci.

## Výsledek MVP

Lokálně spustitelná webová aplikace, ve které uživatel nahraje `.md`, `.docx`, `.pdf` nebo `.xlsx` a získá:

1. normalizovaný AI vstup;
2. prioritizované findings s důkazem v obsahu;
3. u každého findingu severity, vlastníka opravy a doporučení;
4. jasné rozlišení mezi problémem obsahu a omezením ingestu.

PDF je součástí MVP s transparentním označením OCR a vizuálních omezení.

## Doporučená technická volba

Pro demo zvolit jeden lokální Python projekt:

- **FastAPI** jako malé HTTP API;
- **server-rendered HTML + HTMX** nebo jednoduché šablony pro upload a report — bez samostatného front-endu;
- **Docling** pro extrakci Wordu a běžných dokumentů;
- **openpyxl** pro jisté čtení metadat Excel workbooku (názvy sheetů, sloučené buňky, rozměry, vzorce); Docling zůstane zdrojem tabulkového obsahu;
- **pytest** pro pravidla a testovací sadu;
- lokální dočasné úložiště uploadů; žádná databáze ani autentizace v demo verzi.

Rozhraní mezi vrstvami má být čisté. UI nesmí znát pravidla analýzy a checky nesmí být závislé na Doclingu.

```text
UI / HTTP
   ↓
analyse(file) → AnalysisResult
   ├── extractors      (md, docx, xlsx)
   ├── normalizer      (jednotný dokumentový model)
   ├── checks          (deterministická pravidla)
   └── report builder  (findings + AI view)
```

## Fáze 0 — založení projektu a testovací kontrakt

**Cíl:** vytvořit spustitelný základ a nejdřív formalizovat, co přesně má systém vracet.

### Práce

- založit Python projekt a zamknout závislosti;
- vytvořit datové modely `Document`, `Block`, `Table`, `SourceLocation`, `Finding` a `AnalysisResult`;
- zavést enumy:
  - `severity`: `critical`, `warning`, `info`;
  - `owner`: `content_owner`, `platform_team`, `shared`;
  - `category`: `content_issue`, `ingestion_limitation`;
- založit pytest a fixtures;
- vložit anonymizované/minimální testovací soubory nebo jejich malé reprezentativní výřezy.

### Hotovo, když

- `pytest` běží na prázdném projektu;
- existuje serializovatelný vzorový `AnalysisResult`;
- struktura projektu neobsahuje logiku UI ani pravidel v jednom souboru.

## Fáze 1 — extrakce a normalizovaný AI pohled

**Cíl:** pro každý podporovaný formát vytvořit transparentní, konzistentní „co AI uvidí“ výstup.

### 1A. Markdown

- načíst soubor bez konverze;
- rozpoznat skutečné Markdown nadpisy, odkazy, obrázky, tabulky a délky bloků;
- zachovat čísla řádků pro důkazy v reportu.

### 1B. Word

- extrahovat přes Docling;
- rozlišit skutečné nadpisy od běžných tučných odstavců;
- zachovat dostupné odkazy, obrázky a tabulky;
- pokud extractor narazí na nejistě zpracovaný objekt, vytvořit explicitní marker místo tichého vynechání.

### 1C. PDF

- extrahovat přes Docling s `--image-export-mode placeholder`, nikdy ne s embedded Base64 obrázky;
- zachovat číslo stránky, pokud jej lze bezpečně přiřadit ke zdrojovému bloku;
- evidovat OCR varování a počet neověřených vizuálních objektů;
- agregovat opakované vizuální placeholdery do jednoho srozumitelného findingu.

### 1D. Excel

- načíst názvy workbooku a všech sheetů přes `openpyxl`;
- z Doclingu získat text/tabulky;
- před každý obsah sheetu vložit minimálně:

  ```md
  # <název workbooku>
  ## List: <název sheetu>
  ```

- bezpečně připojit jasný název tabulky, pokud je v rozpoznatelné titulní buňce/řádku přímo nad tabulkou;
- nehádat popisy tabulek, kde vazbu nelze dokázat;
- zaznamenat merged cells, vzorce, odkazy a obrázky pro budoucí checky.

### Hotovo, když

- analyzovaný Word, Markdown, PDF a Excel vrátí `AnalysisResult`;
- výsledný normalizovaný obsah je zobrazenelný jako Markdown/text;
- export Excelu nikdy neztratí název workbooku ani sheetu;
- analýza neskončí chybou jen proto, že soubor obsahuje nepodporovaný objekt: místo toho vrátí marker či finding.

## Fáze 2 — deterministické AI-ready checky

**Cíl:** implementovat malý počet nálezů s vysokou přesností.

Implementovat v tomto pořadí:

1. **Skutečné nadpisy chybí / dlouhý blok bez struktury**
   - warning, `content_owner`;
   - důkaz: rozsah řádků/bloku;
   - oprava: použít styly nadpisů ve Wordu nebo `#` strukturu v Markdownu.
2. **Obrázek či objekt bez textového ekvivalentu**
   - critical nebo warning podle jistoty;
   - `content_owner`, pokud zdroj nemá popis;
   - `platform_team`, pokud popis existuje ve zdroji, ale nebyl převeden.
3. **Nejistá či neúplná extrakce**
   - critical;
   - vlastník podle příčiny;
   - žádné tvrzení, že dokument je bez rizik.
4. **Externí reference bez lokálního shrnutí**
   - warning, `content_owner`;
   - konzervativní detekce formulací jako „viz příloha“, „viz ticket“, „viz Jira“.
5. **Excel: ztracený kontext tabulky/sheetu nebo příliš hustý řádek**
   - ingestion limitation, `platform_team`, pokud přidaná metadata chybí v exportu;
   - shared, pokud tabulka nemá zjistitelný název/účel;
   - warning pro řádky výrazně přesahující dohodnutý limit znaků/tokenů.
6. **PDF: OCR nebo vizuální objekt nelze ověřit**
   - warning, `platform_team` nebo `shared` podle povahy nejistoty;
   - PDF nesmí být označeno jako bezrizikové jen proto, že převod technicky doběhl;
   - opakované placeholdery se reportují souhrnně, s odkazem na první dostupnou stránku.

Každé pravidlo vrací jeden či více `Finding` objektů. Pravidlo nemá stanovovat finální celkové skóre.

### Hotovo, když

- každé pravidlo má pozitivní, negativní a hraniční unit test;
- každý finding obsahuje `title`, `severity`, `owner`, `category`, `why`, `recommendation` a `evidence`;
- na testovacích souborech nejsou evidentní falešné poplachy;
- report nenazývá „chybu autora“ ztrátu metadat způsobenou extraktorem.

## Fáze 3 — CLI pro rychlou kalibraci

**Cíl:** umožnit analyzovat soubor bez UI a rychle ladit pravidla.

### Příkazy

```bash
air-dv analyse path/to/document.docx
air-dv analyse path/to/workbook.xlsx --report report.md --ai-view normalized.md
```

CLI vypíše stručné shrnutí do terminálu a umí uložit:

- Markdown report;
- normalizovaný AI view;
- JSON s `AnalysisResult` pro automatizované testy.

### Hotovo, když

- referenční Word, Excel a PDF projdou CLI;
- report pro Word upozorní na nedostatek semantických nadpisů;
- report pro Excel obsahuje kontext workbooku/sheetů a neoznačí platformní ztrátu jako chybu autora.

## Fáze 4 — malé upload UI pro demo

**Cíl:** autor bez terminálu nahraje soubor a porozumí výsledku do jedné až dvou minut.

### Obrazovky

1. **Upload**
   - drop zone, podporované formáty, limit velikosti;
   - stručná informace, že soubor se pouze analyzuje a originál se nemění.
2. **Výsledek**
   - počet critical/warning/info nálezů;
   - filtry podle severity a vlastníka opravy;
   - karty nálezů: co, proč, doporučení, vlastník, důkaz;
   - oddělené označení `Platform limitation`, aby nebylo zaměněno za chybu autora.
3. **Co AI uvidí**
   - čitelný normalizovaný Markdown/text;
   - zvýraznění bloků, k nimž směřuje evidence z nálezů;
   - možnost stáhnout tento výstup a report.

### Zásady UX

- žádná hlavní procentuální známka;
- žádné automatické přepisování originálu;
- přesná, neobviňující formulace;
- když si systém není jistý, řekne to otevřeně.

### Hotovo, když

- demo lze spustit jedním příkazem;
- uživatel nahraje Markdown, Word, PDF nebo Excel, prohlédne findings a AI view;
- výsledek je použitelný bez znalosti Doclingu, chunkingu nebo RAG.

## Fáze 5 — kalibrace s reálným vzorkem

**Cíl:** odstranit šum před rozšířením funkcí.

### Práce

- vybrat 20–30 reálných artefaktů: Word, Markdown, Excel a PDF;
- ručně vytvořit očekávané findings podle product spec;
- změřit precision každého checku a popsat nejasné případy;
- upravit thresholdy a formulace;
- získat od 3–5 uživatelů zpětnou vazbu: rozuměli nálezu, věřili mu, věděli co udělat?

### Go/no-go kritérium

Do další investice jít jen tehdy, když nálezy vedou k opravě obsahu nebo jasně identifikované opravě ingestu. Počet analyzovaných dokumentů není metrika úspěchu.

## Doporučené pořadí a časový rámec

| Fáze | Odhad | Výstup |
|---|---:|---|
| 0 | 0,5 dne | Projekt, modely výsledku, testy |
| 1 | 2–3 dny | Normalizace `.md`, `.docx`, `.xlsx` |
| 2 | 2–3 dny | Pět konzervativních checků |
| 3 | 0,5–1 den | CLI a export reportů |
| 4 | 2–3 dny | Upload UI pro demo |
| 5 | 2–3 dny průběžně | Kalibrace a rozhodnutí o pokračování |

Celkem: přibližně 8–12 pracovních dnů pro funkční demo a první kalibraci. LLM, Confluence, CI a Orchid profil nejsou součástí tohoto odhadu.

## Rizika, která je nutné hlídat během vývoje

- **Testy nejsou prostředek k dosažení zeleného výsledku.** Selhaný test se nejdřív analyzuje jako možná chyba implementace. Očekávání testu se mění pouze tehdy, když se nezávisle prokáže chyba ve specifikaci, fixture nebo samotném testu; důvod změny musí být uveden v commitu či reportu bloku.
- **Přesnost je důležitější než počet checků.** Nové pravidlo přidat jen s testy a reprezentativními příklady.
- **Normalizovaný výstup je produktová pravda.** Nelze hodnotit originál jinak, než jaký obsah nástroj předá do AI view.
- **Excel není jen Markdown tabulka.** Metadata workbooku/sheetů musí zůstat zachována.
- **Nejistota musí být vidět.** Neúspěšná extrakce je finding, ne prázdný výsledek.
- **Žádný obsah nesmí opustit lokální prostředí bez výslovného rozhodnutí.** MVP nepotřebuje LLM ani externí API.

## Co následuje po schválení plánu

Začít Fází 0: založit projektovou kostru, datový kontrakt výsledku, testy a dva malé fixture soubory vycházející z ověřeného Word/Excel případu.
