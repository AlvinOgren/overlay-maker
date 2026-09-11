# Verifiering av kompakt export

- Elva Python-tester passerar. Befintliga tester för GPX, uppladdning, Windows-filtyp, luckor och saknade värden passerar fortfarande.
- Nya tester kontrollerar MP4 som standard, fast och jämn pixelstorlek vid olika tidsstämplar, svart MP4-bakgrund och att text/symboler får plats i både horisontell och vertikal layout för alla tre textstorlekar.
- Verkliga exportfiler skapades med Björsäter_z2.gpx, fem standardmätvärden, medium text, elapsed 15–18 sekunder och 2 fps. FFprobe verifierade mått, bildfrekvens och tre sekunders längd. MP4 avkodades till RGB och har svart hörnpixel samt synliga siffror. WebM avkodades med libvpx-vp9 och behåller alfakanalen.

| Format/layout | Mått | Exporttid i testmiljön | Filstorlek |
| --- | --- | --- | --- |
| MP4 horisontell | 1364 × 184 | 0,104 s | 40 852 byte |
| MP4 vertikal | 466 × 956 | 0,123 s | 41 909 byte |
| MOV horisontell | 1364 × 184 | 0,149 s | 854 732 byte |
| WebM horisontell | 1364 × 184 | 0,545 s | 114 976 byte |

Tiderna mäter exportjobbet i Linuxmiljön efter GPX-inläsning och är korta stickprov, inte en garanti för andra datorer eller långa klipp. Horisontell standardlayout behandlar cirka 97 procent färre pixlar än en hel 3840 × 2160-bild, med samma numeriska textstorlek på 88 px.

JavaScript klarar syntaxkontrollen. Den renderade horisontella bilden har granskats. Ingen webbläsar-, Windows- eller extern videoeditortestning gjordes här. WebMCP har inte verifierats i en stödd webbläsarkontext.
