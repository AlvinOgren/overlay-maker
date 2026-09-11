# Ride Overlay

Lokal GPX → kompakt video med MP4 som standard. Mörkt webbgränssnitt, valbara mätvärden och samma renderare för förhandsvisning och export.

## Uppdatering: kompakt rendering och MP4

Stäng den gamla appens terminal med Ctrl+C. Packa upp den nya ZIP-filen i en ny mapp och kör dess `START.bat`. Använd den nya fliken som öppnas. Du kan kopiera gamla videofiler från den gamla mappens `exports/` om du vill samla dem.

Videoytan anpassas nu automatiskt runt valda mätvärden, symboler och enheter. MP4/H.264 med svart bakgrund är standard. Horisontell och vertikal layout finns kvar; placering görs i redigeringen. Endast den kompakta ytan renderas och statiska symboler/etiketter återanvänds mellan bildrutor.

Uppladdningen visar “Läser filen…” och därefter “✓ Filen är inläst” tillsammans med filnamn, antal mätpunkter och aktivitetens längd. Fel visas direkt under filväljaren. Samma fil kan väljas igen efter ett fel. Appen levererar JavaScript och CSS med fasta webbfiltyper, oberoende av Windows filassociationer, för att undvika att webbläsaren blockerar appkoden. Om index.html öppnas direkt visas startinstruktioner.

## Starta i Windows

1. Packa upp hela ZIP-filen i en vanlig mapp, exempelvis `C:\Users\alvin\git\ride-overlay`.
2. Ha **Python 3.10 eller senare** installerat. Om Python saknas: installera från https://www.python.org/downloads/windows/ och välj alternativet att lägga Python i PATH.
3. Dubbelklicka **START.bat**. Första starten installerar Pillow och imageio-ffmpeg i projektets egen `.venv` och behöver internet. Därefter sker behandlingen lokalt.
4. Webbläsaren öppnas automatiskt. Låt terminalfönstret vara öppet medan du använder appen. Stäng med Ctrl+C.

I CMD eller VS Codes terminal, från projektmappen:

```cmd
py -3 bootstrap.py
```

På macOS/Linux: `python3 bootstrap.py`. Linux kan behöva paketet `python3-venv` installerat. Öppna inte `dist/index.html` direkt: appen behöver sin lokala Python-server. Ingen SSH, GitHub, Node eller separat FFmpeg-installation krävs. Om FFmpeg redan finns i PATH används den; annars används den som följer med imageio-ffmpeg.

## Skapa en video

1. Släpp en GPX-fil i appen. Endast tillgängliga mätvärden går att välja.
2. Välj hastighet, puls, effekt, kadens, elapsed time, distans, höjd och/eller temperatur. Anpassa textstorlek, horisontell/vertikal layout, symbolfärg och kontur.
3. Dra tidsreglaget för att granska siffrorna. Spela-knappen spelar tidslinjen i realtid med två uppdateringar per sekund; exportens bildfrekvens väljs separat.
4. Välj 1, 2, 3 eller 5 fps. Videoytan beräknas automatiskt och pixelmåtten visas ovanför förhandsvisningen. Textstorleken anger detaljnivån (64, 88 eller 116 px); bilden får en liten marginal och fast storlek under hela klippet. Måtten tar höjd för alla värden i aktiviteten, så siffrorna inte hoppar eller klipps när de blir längre.
5. Första utsnittet är **10 sekunder**. Välj “Hela aktiviteten” för hela turen eller skriv egna start-/sluttider. Full aktivitet kan ta lång tid och ge stora filer, särskilt i ProRes.
6. Klicka **Skapa overlay**. Framsteg visas och exporten kan avbrytas. Resultatet sparas i `exports/` och kan laddas ner från sidan. En pågående export använder inställningarna från när du klickade, även om du ändrar kontrollerna senare.

## Transparens och redigering

- **MP4 / H.264** är standard, med svart bakgrund och utan transparens.
- **MOV / ProRes 4444** finns kvar som alternativ med alfakanal och kan ge större filer.
- **WebM / VP9 alpha** har också riktig transparens och blir ofta mindre. Stödet varierar mellan redigeringsprogram.
- MP4 visar samma svarta bakgrund i förhandsvisning och export. För MOV/WebM är schackrutorna bara ett hjälpmedel i förhandsvisningen.
- En vanlig videospelare kan visa svart bakgrund även när alfakanalen finns. Testa filen på ett spår ovanför en annan video i din editor.
- Behåll klippets faktiska längd när det läggs på en 25/30/60 fps-tidslinje. Tolka inte om 2 fps som 30 fps, eftersom det då spelas för snabbt.
- Elapsed time börjar vid **GPX-filens första giltiga tidsstämpel**, även om filen redan var beskuren. Ett utsnitt från 00:15:00 visar 00:15:00, inte 00:00:00. Synka det manuellt mot kamerafilmen.
- Exportlängden avrundas upp till hela bildrutor: högst mindre än en bildrutas extra tid.

I `examples/` finns två riktiga 3-sekunders överlägg från din Björsäter-fil, vid elapsed 00:00:15–00:00:18, i kompakt MP4/2 fps: horisontellt (1364 × 184) och vertikalt (466 × 956). De innehåller bara siffror och symboler, ingen karta eller GPS-position.

## Hur GPX-data behandlas

Puls, effekt, kadens och temperatur läses från GPX-tillägg oberoende av namespace-prefix. Noll watt och noll kadens är giltiga värden. Saknade värden visas som streck. Hastighet beräknas från avståndet mellan GPS-punkter och deras tidsstämplar; detta är GPS-hastighet och kan vara brusigt. Distans summeras från samma punkter.

Sensorvärden interpoleras linjärt mellan två giltiga mätningar inom samma segment, högst 10 sekunder från varandra. Längre luckor och segmentbyten ger streck, medan elapsed time fortsätter. Distans över sådana luckor räknas inte med. Punkter utan tid och tidsstämplar som inte ökar hoppas över. Orimliga GPS-hopp över 100 m/s räknas inte in i hastighet/distans. Filgräns: 20 MB, 200 000 punkter, 7 dygn.

GPX behandlas i minnet. Appen binder endast till `127.0.0.1` och laddar inte upp aktiviteter till någon tjänst. Exportfiler finns kvar efter omstart; uppladdad aktivitet och exporthistoriken i webbsidan gör det inte. Flera öppna flikar delar samma server och högst tre uppladdade aktiviteter behålls samtidigt.

## Kod och verifiering

- `dist/`: HTML, CSS och JavaScript.
- `gpx.py`: parsing och tidsbaserad sampling.
- `rendering.py`: kompakt Pillow-rendering, återanvända etiketter och konfigurationsvalidering.
- `jobs.py`: strömmad videoexport genom FFmpeg, en bildruta åt gången.
- `server.py`: lokal webbserver och API.
- `bootstrap.py`, `START.bat`: installation och start.
- `assets/`: medföljande DejaVu-teckensnitt och licens.

Kör tester i appens Python-miljö:

```cmd
.venv\Scripts\python -m unittest discover -s tests -v
```

Se `VALIDATION.md` för vad som kontrollerats och återstående miljöbegränsningar.

Formatreferenser: [Apple om ProRes 4444 och alpha](https://support.apple.com/en-us/102207), [FFmpeg ProRes](https://ffmpeg.org/ffmpeg-codecs.html#ProRes), [GPX 1.1](https://www.topografix.com/GPX/1/1/).
