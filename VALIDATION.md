# Verifiering av första versionen

## Uppdatering av uppladdning

Nio Python-tester passerar. De fyra tillkommande testar HTTP-hanterarna direkt i minnet: korrekt JavaScript-filtyp även när systemet rapporterar text/plain, uppladdning med svenskt filnamn följt av en verklig PNG-förhandsvisning, felaktig fil följt av lyckat nytt försök samt uppladdning av båda användarens GPX-filer. JavaScript klarar syntaxkontrollen. Ingen ny webbläsar- eller Windows-körning gjordes; detta verifierar serverflödet och skyddet mot felaktig MIME-typ, inte den exakta orsaken på användarens dator.

Utförd i Linux-miljön där projektet byggdes.

- Python-källfiler kompilerar och JavaScript klarar `node --check`.
- Fem automatiska tester passerar: nollvärden/interpolering, tidsluckor/segment, saknade sensorer, felaktig indata/inställningar och transparent rendering i samtliga ytor med både rad och stapel.
- Björsäter_z2.gpx: 9 561 punkter, 9 786 sekunder; puls och kadens i samtliga punkter, effekt i 9 560.
- KvällsMTB.gpx: 6 451 punkter, 6 929 sekunder; effekt och kadens markeras otillgängliga.
- Riktiga MOV- och WebM-filer skapades från Björsäter_z2, elapsed 15–18 sekunder. FFprobe bekräftar 3840 × 2160, 2 fps och 3 sekunders längd för båda.
- Båda filerna avkodades till RGBA. Alfakanalen innehåller 0 och 255, hörnpixeln är helt transparent och 48 354 pixlar har synlig text/symboler i första bildrutan. WebM avkodades med libvpx-vp9, eftersom standardavkodaren kan utelämna alpha.
- Den renderade förhandsvisningsbilden granskades för läsbarhet och avklippning av de fem förvalda mätvärdena.

Windows-startfilen har inte körts på en faktisk Windows-dator här. Gränssnittet har inte funktionstestats i en webbläsare. WebMCP-registrering och verktygsanrop har inte verifierats i en stödd webbläsarkontext. Import i en extern videoeditor är inte testad; formatstöd beror på vald editor. Dessa punkter är inte täckta av export-/enhetstesterna.
