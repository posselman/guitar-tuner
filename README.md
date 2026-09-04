# 🎸 Gitaarstemmer PWA (Auto-Detect)

Een moderne, responsieve Progressive Web App (PWA) om een akoestische of elektrische gitaar nauwkeurig te stemmen via de microfoon van je computer of smartphone (Android / iOS).

---

## 🚀 Belangrijkste Eigenschappen

* **Auto-Detect van alle 6 snaren:** Herkent automatisch welke snaar je aanslaat (E2, A2, D3, G3, B3, E4).
* **Geavanceerde DSP Pitch Engine:** Gebaseerd op het **YIN-algoritme** (Cumulative Mean Normalized Difference Function) met parabolische interpolatie voor sub-cent precisie.
* **Robuuste Audio-Voorfiltering:** Biquad Highpass (65 Hz) en Lowpass (420 Hz) filters die achtergrondgerommel, netbrom en overmatige boventonen elimineren.
* **Harmonische- & Octaaf-Bewust:** Voorkomt het verspringen naar verkeerde snaren wanneer een smartphone-microfoon de lage grondtoon (E2/A2) zwak opvangt en de 2e harmonische domineert.
* **Mediaan- & EWMA-Demping:** Geen nerveus trillende naald; uitschieters worden weggefilterd via een 5-traps mediaanfilter en de meter glijdt vloeiend via analoge traagheid.
* **Hysteresis (Snaar Lock-on):** Vereist meerdere opeenvolgende consistente metingen om van snaar te wisselen, waardoor de weergave stabiel blijft tijdens het stemmen.
* **PWA & Offline Gereed:** Volledig installeerbaar op het startscherm met offline Service Worker ondersteuning.

---

## 📐 Technische Architectuur & Signaalpad

```
Microfoon (getUserMedia)
       │
       ▼
   GainNode (instelbare software-versterking 1x - 16x)
       │
       ▼
 BiquadFilter (Highpass 65 Hz, 12dB/oct)  ──> Snijdt wind, contactgeluid & 50Hz netbrom af
       │
       ▼
 BiquadFilter (Lowpass 420 Hz, 12dB/oct)  ──> Snijdt sissende ruis en boventonen > E4 af
       │
       ▼
  AnalyserNode (fftSize: 2048 samples)
       │
       ▼
   YIN Pitch Engine (CMNDF + threshold 0.15 + parabolische interpolatie)
       │
       ▼
  Mediaanfilter (N=5)  ──> Elimineert kortstondige ruispieken / outliers
       │
       ▼
  Harmonische Snaar-Toewijzing & Hysteresis (Lock-on na 4 consistente frames)
       │
       ▼
  EWMA Naald-Demping (hoek = vorige * 0.75 + doel * 0.25)
       │
       ▼
  Visuele Koppeling (SVG Gitaarkop, Stemknoppen, Wijzerplaat & Trilling)
```

---

## ⚙️ Lokale Ontwikkeling & Starten

Omdat microfoontoegang in moderne browsers (`getUserMedia`) een veilige context (HTTPS of localhost) vereist, draait de lokale ontwikkelserver met een SSL-certificaat:

```bash
# Start de lokale HTTPS server op poort 8443
python3 serve.py
```

Open vervolgens op je laptop of mobiel in hetzelfde netwerk:
```text
https://<jouw-ip>:8443
```
*(Accepteer de zelfondertekende SSL-waarschuwing eenmalig via Geavanceerd -> Doorgaan).*

---

## 📱 PWA Installatie op Mobiel (Android / iOS)

* **Android (Chrome):** Tik op het menu (drie puntjes) of de knop **"Installeer App"** onderaan het scherm en kies *Toevoegen aan startscherm*.
* **iOS (Safari):** Tik op de *Deel*-knop onderaan en kies *Zet op beginscherm*.
