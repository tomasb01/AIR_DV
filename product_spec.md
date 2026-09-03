# AI-ready dokumenty — product specification (MVP demo)

**Stav:** návrh před vývojem  
**Cíl verze:** krátké, srozumitelné demo nad jednotlivým nahraným souborem.  
**Není cílem MVP:** adopce přes Confluence/CI ani simulace konkrétní RAG pipeline.

## Jazyk produktu

Veškerá komunikace nástroje s uživatelem bude v **angličtině**: UI, findings, severity, doporučení, exportované reporty, normalizovaný AI view i chybové zprávy. Angličtina je výchozí produktový jazyk; případná lokalizace není součástí MVP.

## 1. Problém a produktová teze

AI agent nebo RAG často selže ne proto, že by „model neuměl odpovědět“, ale protože podkladový dokument není pro stroj spolehlivě čitelný. Důležitá informace může být pouze v diagramu, tabulka se může při exportu rozpadnout nebo se může ztratit kontext kapitoly či Excel sheetu.

Produkt je **diagnostický nástroj pro AI-readiness dokumentů**. Vezme existující dokument, ukáže, co z něj AI skutečně získá, najde konkrétní rizika, vysvětlí jejich dopad a navrhne opravu.

Nástroj neměří úplnost ani věcnou správnost znalostí. Měří nutnou, nikoli postačující podmínku: zda je obsah čitelný, strukturovaný a dostatečně kontextový pro obecné AI konzumenty.

## 2. Cíl MVP

Uživatel nahraje jeden soubor a během krátké doby dostane důvěryhodný report.

Podporované vstupy v MVP:

- Markdown (`.md`)
- Word (`.docx`)
- Excel (`.xlsx`)
- PDF, pokud je jeho extrakce spolehlivá; skeny a složité layouty se označí jako omezeně analyzovatelné

Primární výstup není procentuální známka. Je to seznam konkrétních, akčních nálezů s vlastníkem opravy.

## 3. Základní princip: nejdřív normalizace

Soubor se interně převede do jednotné reprezentace: text, nadpisy, bloky, tabulky, odkazy, obrázky a dostupná metadata. Pro převod se používá hotové řešení, například Docling; vlastní konvertor není součástí produktu.

```text
Word / Excel / Markdown / PDF
              ↓
  extractor + normalizační vrstva
              ↓
  jednotný strukturovaný obsah
              ↓
  deterministické AI-ready checky
              ↓
  report + náhled „co AI uvidí"
```

Normalizace není pouhá konverze do Markdownu. Musí doplnit bezpečně dostupný kontext, který by lineární export mohl ztratit.

Příklad Excelu:

```text
Název souboru
  └── název sheetu
       └── jasně rozpoznaný název / popis tabulky
            └── tabulka nebo záznamy
```

Název workbooku a sheetu se vkládá vždy. Popis tabulky se přebírá pouze při vysoké jistotě (například jasný titulek bezprostředně nad tabulkou). Při nejistotě nástroj kontext nevymýšlí a označí riziko.

## 4. AI-ready baseline

Dokument je obecně AI-ready, pokud:

1. **Stojí sám o sobě.** Je jasné, čeho se týká, k jakému systému/procesu patří a co znamenají klíčové zkratky.
2. **Podstatný obsah je dostupný jako text.** Diagram, obrázek nebo tabulka-jako-obrázek mají textový ekvivalent.
3. **Struktura přežije rozdělení obsahu.** Skutečné nadpisy, rozumné bloky a strukturované tabulky zachovávají kontext.
4. **Externí odkazy nenahrazují obsah.** „Viz ticket/příloha/mail“ obsahuje alespoň lokální shrnutí podstatného rozhodnutí.
5. **Formát lze spolehlivě extrahovat.** Nástroj transparentně označí sken, textové pole, SmartArt či jiný objekt, který nedokáže bezpečně vyhodnotit.

## 5. Typy nálezů a vlastníci oprav

Každý nález má severity, důkaz v dokumentu, vysvětlení dopadu, doporučenou opravu a vlastníka opravy.

| Typ | Příklad | Vlastník opravy |
|---|---|---|
| Content issue | Diagram bez textového popisu, neoznačené kapitoly, kontext pouze v externím ticketu | Autor / owner dokumentu |
| Ingestion limitation | Excel obsahuje pojmenované sheety, ale běžný export jejich názvy ztrácí | AI platforma / tým extrakce |
| Shared issue | Tabulka nemá jasný titul ani účel | Autor doplní kontext, platforma jej zachová |

Toto rozlišení je zásadní: autor nesmí dostat úkol opravovat chybu, kterou způsobil extraktor, pokud potřebná informace v originálu existuje.

## 6. Checky pro první verzi

MVP začne konzervativně: jen checky s vysokou přesností.

### Content issues

- obrázek/diagram bez dostupného textového popisu nebo alt textu
- dlouhý blok bez skutečného nadpisu či přirozeného členění
- kapitoly zvýrazněné pouze tučně místo semantických nadpisů
- odkaz typu „viz příloha/ticket/mail“ bez shrnutí
- neextrahovatelný nebo nejistě extrahovaný obsah

### Ingestion issues

- metadata zdroje existují, ale ztratila se v normalizovaném výstupu (zejména název Excel sheetu)
- titul/popisek tabulky ztratil vazbu na samotnou tabulku
- extrahovaná tabulka je příliš široká nebo obsahuje velmi dlouhé řádky, které se obtížně zachovají jako celek

### Mimo MVP

- posuzování věcné správnosti dokumentu
- detekce duplicit a rozporů mezi dokumenty
- zjištění, které znalosti nejsou zdokumentované vůbec
- automatický přepis originálu
- kompletní LLM analýza self-containmentu

## 7. Uživatelské rozhraní pro demo

MVP má malé upload UI. Upload není cílový model adopce; je to nejrychlejší způsob, jak ukázat hodnotu a ověřit důvěru ve findings.

### Hlavní tok

1. Uživatel přetáhne soubor nebo jej vybere.
2. Systém rozpozná typ souboru, extrahuje a normalizuje obsah.
3. Zobrazí report s prioritizovanými nálezy.
4. Uživatel může otevřít důkaz a náhled normalizovaného obsahu („co AI skutečně uvidí“).

### Obrazovka reportu

```text
AI-ready document check

3 content findings · 1 ingestion limitation · 0 critical issues

[Warning] Sections are not marked with semantic headings
Owner: Content owner
Why it matters: Section context may be lost when the document is split.
How to fix: Use Heading 1–3 styles in Word.
[View evidence] [View AI-ready content]

[Platform limitation] Excel sheet names were lost during export
Owner: AI platform team
Author action: None required.
Platform fix: Add the workbook and sheet name before each table.
```

Severity:

- **Critical:** podstatný obsah není jako text dostupný nebo soubor nelze bezpečně analyzovat.
- **Warning:** obsah je dostupný, ale hrozí ztráta kontextu či špatné dělení.
- **Info:** doporučení ke zlepšení struktury nebo metadat.

Skóre lze přidat později. V MVP se nepoužívá jako hlavní sdělení, aby nevytvářelo falešnou jistotu.

## 8. Náhled normalizovaného obsahu

Náhled je povinná část UX. Umožňuje ověřit, zda nástroj hodnotí realitu, a odlišit problém dokumentu od problému ingestu.

Uživatel má vidět:

- normalizovaný text/Markdown;
- vložené nadpisy z názvu souboru a Excel sheetů;
- označení míst, která nebyla spolehlivě extrahována;
- vazbu z nálezu na konkrétní blok obsahu.

Originál se nikdy automaticky nemění. Budoucí verze může nabídnout návrh opravy ke zkopírování nebo potvrzení člověkem.

## 9. Příklady ověřené na testovacích souborech

### Word: kniha

Docling z dokumentu spolehlivě vytáhl text. Významné kapitoly však byly ve Wordu formátované zejména tučně, nikoli styly nadpisů; výsledný Markdown neměl `#`/`##` nadpisy. Jde o content issue: oprava patří autorovi zdrojového Wordu.

### Excel: katalog tagů

Workbook má čtyři pojmenované sheety a zjevné titulky tabulek. Běžný Markdown export zachoval data, ale nezachoval názvy sheetů a jejich vztah k tabulkám. Jde primárně o ingestion limitation: normalizační vrstva má názvy sheetů doplnit automaticky. Pokud účel tabulky nelze spolehlivě určit, jde o shared issue.

## 10. Budoucí rozšíření

### LLM asistence

Teprve po ověření deterministicých checků:

- návrh textového ekvivalentu diagramu/obrázku;
- návrh konkrétní opravy opakovaných nálezů;
- kontrola self-containmentu a nerozepsaných zkratek.

LLM nad podnikovým obsahem vyžaduje před zapnutím rozhodnutí o klasifikaci dat, schváleném modelu a místě zpracování.

### Profily konzumentů

Obecný baseline zůstává jádrem. Později lze jednou nakonfigurovat profil konkrétního řešení, například Orchidu: skutečný export, chunking a známá omezení. Profil upravuje severity a přidává specifické nálezy; nenahrazuje baseline.

### Adopce

Po pilotu lze stejnou analytickou logiku napojit na:

- Confluence kontrolu jednotlivé stránky či celého space;
- CI check pro README a dokumentaci v repozitáři;
- agregovaný report pro AI platformu a tribe leady.

## 11. Kritérium úspěchu pilotu

Pilot není úspěšný podle počtu oskenovaných souborů. Je úspěšný, pokud autoři a tým platformy po reportu opraví alespoň část konkrétních nálezů a zlepší se kvalita normalizovaného AI vstupu.

První ověření:

1. Vybrat 20–30 reálných artefaktů různých typů.
2. Ručně označit očekávané nálezy podle baseline.
3. Porovnat je s výsledkem MVP a odstranit šum.
4. Ověřit, zda lidé rozumí nálezům, důvěřují jim a dokážou podle nich provést opravu.
