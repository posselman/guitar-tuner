import re

with open('/home/posselman/Projects/guitar-tuner/index.html', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update Build version
code = code.replace('Build 20260905.5', 'Build 20260905.6')

# 2. Update updatePitch to handle low-confidence decay
old_pitch_logic = '''      // Noise gate: start detectie bij voldoende signaalsterkte boven achtergrondruis
      if (rms >= 0.007) {
        rawFreq = yinPitch(buffer, audioContext.sampleRate);

        if (rawFreq !== -1 && rawFreq >= 65 && rawFreq <= 450) {
          silenceCounter = 0;

          // Voeg toe aan mediaanfilter buffer
          freqHistory.push(rawFreq);
          if (freqHistory.length > FREQ_HISTORY_SIZE) {
            freqHistory.shift();
          }
          medianFreq = calculateMedian(freqHistory);

          // Vloeiende frequentie-interpolatie (Smoothing)
          if (smoothedFreq === 0) {
            smoothedFreq = medianFreq;
          } else {
            smoothedFreq = smoothedFreq * 0.70 + medianFreq * 0.30;
          }

          let activeString = null;
          let targetFreqVal = 0;
          let fundamentalFreq = 0;
          let harmonicK = 1;

          if (isManualLock && currentLockedString) {
            activeString = currentLockedString;
            let bestDiffCents = Math.abs(1200 * Math.log2(smoothedFreq / activeString.freq));

            // Check 2e en 3e harmonischen (vooral Lage E en A)
            if (activeString.id === 'E2' || activeString.id === 'A2') {
              for (const k of [2, 3]) {
                const diffCents = Math.abs(1200 * Math.log2(smoothedFreq / (activeString.freq * k)));
                if (diffCents < bestDiffCents) {
                  bestDiffCents = diffCents;
                  harmonicK = k;
                }
              }
            }

            targetFreqVal = activeString.freq * harmonicK;
            cents = Math.round(1200 * Math.log2(smoothedFreq / targetFreqVal));
            inTune = Math.abs(cents) <= 4;
            fundamentalFreq = smoothedFreq / harmonicK;

            stringTitle.textContent = '🔒 ' + activeString.label.toUpperCase() + (harmonicK > 1 ? ` (${harmonicK}e overtoon)` : '');
            noteDisplay.textContent = activeString.id;
            freqCurrent.textContent = fundamentalFreq.toFixed(1) + ' Hz';
            freqTarget.textContent = activeString.freq.toFixed(1) + ' Hz';
            centsLabel.textContent = (cents > 0 ? '+' + cents : cents) + ' cents';
          } else {
            match = detectNearestGuitarString(smoothedFreq);
            if (match) {
              const detectedString = match.string;
              // Hysteresis / Lock-on: vereist meerdere opeenvolgende frames om van snaar te wisselen
              if (!currentLockedString) {
                currentLockedString = detectedString;
                pendingCandidateString = null;
                pendingCandidateCount = 0;
              } else if (currentLockedString.id !== detectedString.id) {
                if (pendingCandidateString && pendingCandidateString.id === detectedString.id) {
                  pendingCandidateCount++;
                  if (pendingCandidateCount >= STRING_SWITCH_FRAMES) {
                    currentLockedString = detectedString;
                    pendingCandidateString = null;
                    pendingCandidateCount = 0;
                  }
                } else {
                  pendingCandidateString = detectedString;
                  pendingCandidateCount = 1;
                }
              } else {
                pendingCandidateString = null;
                pendingCandidateCount = 0;
              }

              activeString = currentLockedString;
              harmonicK = match.isOctave ? 2 : 1;
              targetFreqVal = match.isOctave && (activeString.id === 'E2' || activeString.id === 'A2')
                ? activeString.freq * 2
                : activeString.freq;

              cents = Math.round(1200 * Math.log2(smoothedFreq / targetFreqVal));
              inTune = Math.abs(cents) <= 4;
              fundamentalFreq = match.isOctave ? (smoothedFreq / 2) : smoothedFreq;

              stringTitle.textContent = activeString.label.toUpperCase();
              noteDisplay.textContent = activeString.id;
              freqCurrent.textContent = fundamentalFreq.toFixed(1) + ' Hz';
              freqTarget.textContent = activeString.freq.toFixed(1) + ' Hz';
              centsLabel.textContent = (cents > 0 ? '+' + cents : cents) + ' cents';
            }
          }

          if (activeString) {
            // Analoge naald-demping (EWMA) voor een rustig reagerende meter
            const clampedCents = Math.max(-50, Math.min(50, cents));
            const targetAngle = (clampedCents / 50) * 45;
            smoothNeedleAngle = smoothNeedleAngle * 0.75 + targetAngle * 0.25;
            needle.style.transform = 'rotate(' + smoothNeedleAngle.toFixed(1) + 'deg)';

            if (inTune) {
              needle.className = 'needle in-tune';
              statusBadge.textContent = '✓ ZUIVER GESTEMD!';
              statusBadge.className = 'status-badge in-tune';
              if (navigator.vibrate && !lastWasInTune) navigator.vibrate(40);
            } else if (cents < 0) {
              needle.className = 'needle off-tune';
              statusBadge.textContent = '▲ TE LAAG (Draai vaster omhoog)';
              statusBadge.className = 'status-badge too-low';
            } else {
              needle.className = 'needle off-tune';
              statusBadge.textContent = '▼ TE HOOG (Draai losser omlaag)';
              statusBadge.className = 'status-badge too-high';
            }
            lastWasInTune = inTune;

            updateVisualHeadstock(activeString.id, inTune);
          }
        }
      } else {
        silenceCounter++;
        if (silenceCounter > 25) {
          freqHistory = [];
          smoothedFreq = 0;
          // Laat naald rustig naar het midden zakken
          smoothNeedleAngle = smoothNeedleAngle * 0.85;
          if (Math.abs(smoothNeedleAngle) > 0.5) {
            needle.style.transform = 'rotate(' + smoothNeedleAngle.toFixed(1) + 'deg)';
          }
          if (currentLockedString) {
            statusBadge.textContent = 'Wachten op aanslag...';
            statusBadge.className = 'status-badge';
          }
        }
      }'''

new_pitch_logic = '''      // Noise gate & confidence check
      const isConfident = (rms >= 0.007 && lastYinDetails.cmndfVal < 0.18);
      
      if (isConfident) {
        rawFreq = yinPitch(buffer, audioContext.sampleRate);
      }

      if (rawFreq !== -1 && rawFreq >= 65 && rawFreq <= 450) {
        silenceCounter = 0;
        freqHistory.push(rawFreq);
        if (freqHistory.length > FREQ_HISTORY_SIZE) freqHistory.shift();
        medianFreq = calculateMedian(freqHistory);
        if (smoothedFreq === 0) smoothedFreq = medianFreq;
        else smoothedFreq = smoothedFreq * 0.70 + medianFreq * 0.30;

        let activeString = null;
        let targetFreqVal = 0;
        let fundamentalFreq = 0;
        let harmonicK = 1;

        if (isManualLock && currentLockedString) {
          activeString = currentLockedString;
          let bestDiffCents = Math.abs(1200 * Math.log2(smoothedFreq / activeString.freq));
          if (activeString.id === 'E2' || activeString.id === 'A2') {
            for (const k of [2, 3]) {
              const diffCents = Math.abs(1200 * Math.log2(smoothedFreq / (activeString.freq * k)));
              if (diffCents < bestDiffCents) { bestDiffCents = diffCents; harmonicK = k; }
            }
          }
          targetFreqVal = activeString.freq * harmonicK;
          cents = Math.round(1200 * Math.log2(smoothedFreq / targetFreqVal));
          inTune = Math.abs(cents) <= 4;
          fundamentalFreq = smoothedFreq / harmonicK;
          stringTitle.textContent = '🔒 ' + activeString.label.toUpperCase() + (harmonicK > 1 ? ` (${harmonicK}e overtoon)` : '');
          noteDisplay.textContent = activeString.id;
          freqCurrent.textContent = fundamentalFreq.toFixed(1) + ' Hz';
          freqTarget.textContent = activeString.freq.toFixed(1) + ' Hz';
          centsLabel.textContent = (cents > 0 ? '+' + cents : cents) + ' cents';
        } else {
          match = detectNearestGuitarString(smoothedFreq);
          if (match) {
            const detectedString = match.string;
            if (!currentLockedString) {
              currentLockedString = detectedString;
              pendingCandidateString = null;
              pendingCandidateCount = 0;
            } else if (currentLockedString.id !== detectedString.id) {
              if (pendingCandidateString && pendingCandidateString.id === detectedString.id) {
                pendingCandidateCount++;
                if (pendingCandidateCount >= STRING_SWITCH_FRAMES) {
                  currentLockedString = detectedString;
                  pendingCandidateString = null;
                  pendingCandidateCount = 0;
                }
              } else {
                pendingCandidateString = detectedString;
                pendingCandidateCount = 1;
              }
            } else {
              pendingCandidateString = null;
              pendingCandidateCount = 0;
            }
            activeString = currentLockedString;
            harmonicK = match.isOctave ? 2 : 1;
            targetFreqVal = match.isOctave && (activeString.id === 'E2' || activeString.id === 'A2')
              ? activeString.freq * 2 : activeString.freq;
            cents = Math.round(1200 * Math.log2(smoothedFreq / targetFreqVal));
            inTune = Math.abs(cents) <= 4;
            fundamentalFreq = match.isOctave ? (smoothedFreq / 2) : smoothedFreq;
            stringTitle.textContent = activeString.label.toUpperCase();
            noteDisplay.textContent = activeString.id;
            freqCurrent.textContent = fundamentalFreq.toFixed(1) + ' Hz';
            freqTarget.textContent = activeString.freq.toFixed(1) + ' Hz';
            centsLabel.textContent = (cents > 0 ? '+' + cents : cents) + ' cents';
          }
        }

        if (activeString) {
          const clampedCents = Math.max(-50, Math.min(50, cents));
          const targetAngle = (clampedCents / 50) * 45;
          smoothNeedleAngle = smoothNeedleAngle * 0.75 + targetAngle * 0.25;
          needle.style.transform = 'rotate(' + smoothNeedleAngle.toFixed(1) + 'deg)';
          if (inTune) {
            needle.className = 'needle in-tune';
            statusBadge.textContent = '✓ ZUIVER GESTEMD!';
            statusBadge.className = 'status-badge in-tune';
            if (navigator.vibrate && !lastWasInTune) navigator.vibrate(40);
          } else if (cents < 0) {
            needle.className = 'needle off-tune';
            statusBadge.textContent = '▲ TE LAAG (Draai vaster omhoog)';
            statusBadge.className = 'status-badge too-low';
          } else {
            needle.className = 'needle off-tune';
            statusBadge.textContent = '▼ TE HOOG (Draai losser omlaag)';
            statusBadge.className = 'status-badge too-high';
          }
          lastWasInTune = inTune;
          updateVisualHeadstock(activeString.id, inTune);
        }
      } else {
        // SNELLE DECAY: Als signaal zwak/onzeker is, zet de naald direct richting midden
        silenceCounter++;
        freqHistory = [];
        smoothedFreq = 0;
        smoothNeedleAngle = smoothNeedleAngle * 0.85; // Snelle demping
        needle.style.transform = 'rotate(' + smoothNeedleAngle.toFixed(1) + 'deg)';
        if (silenceCounter > 10) {
          if (currentLockedString && !isManualLock) {
            currentLockedString = null;
            clearHeadstockVisual();
            stringTitle.textContent = 'SLA EEN SNAAR AAN';
          }
          statusBadge.textContent = 'Wachten op aanslag...';
          statusBadge.className = 'status-badge';
        }
      }'''

assert old_pitch_logic in code, "old_pitch_logic not found"
code = code.replace(old_pitch_logic, new_pitch_logic, 1)

with open('/home/posselman/Projects/guitar-tuner/index.html', 'w', encoding='utf-8') as f:
    f.write(code)
"