// Standaard gitaarsnaren en frequenties (Hz)
const GUITAR_STRINGS = [
  { name: 'E2', note: 'E', octave: 2, freq: 82.41 },
  { name: 'A2', note: 'A', octave: 2, freq: 110.00 },
  { name: 'D3', note: 'D', octave: 3, freq: 146.83 },
  { name: 'G3', note: 'G', octave: 3, freq: 196.00 },
  { name: 'B3', note: 'B', octave: 3, freq: 246.94 },
  { name: 'E4', note: 'E', octave: 4, freq: 329.63 },
];

const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

let audioContext = null;
let analyser = null;
let mediaStream = null;
let isRunning = false;
let animationId = null;

const startBtn = document.getElementById('startBtn');
const needle = document.getElementById('needle');
const centsLabel = document.getElementById('centsLabel');
const noteDisplay = document.getElementById('noteDisplay');
const freqDisplay = document.getElementById('freqDisplay');
const statusBadge = document.getElementById('statusBadge');
const stringBadges = document.querySelectorAll('.string-badge');

startBtn.addEventListener('click', () => {
  if (isRunning) {
    stopTuner();
  } else {
    startTuner();
  }
});

async function startTuner() {
  try {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
      }
    });

    const source = audioContext.createMediaStreamSource(mediaStream);
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 4096; // Hoge resolutie voor lage gitaar-frequenties (E2 ~82Hz)
    source.connect(analyser);

    isRunning = true;
    startBtn.textContent = 'Stop Stemmer';
    startBtn.classList.add('active');
    statusBadge.textContent = 'Luisteren naar gitaar...';
    statusBadge.className = 'status-badge';

    updatePitch();
  } catch (err) {
    console.error('Microfoontoegang geweigerd of fout:', err);
    alert('Kon microfoon niet openen: ' + err.message);
  }
}

function stopTuner() {
  isRunning = false;
  if (animationId) cancelAnimationFrame(animationId);
  if (mediaStream) {
    mediaStream.getTracks().forEach(t => t.stop());
  }
  if (audioContext) audioContext.close();

  startBtn.textContent = 'Start Microfoon';
  startBtn.classList.remove('active');
  statusBadge.textContent = 'Gestopt';
  statusBadge.className = 'status-badge';
  resetUI();
}

function resetUI() {
  needle.style.transform = 'rotate(0deg)';
  needle.className = 'needle';
  centsLabel.textContent = '0 cents';
  noteDisplay.textContent = '--';
  freqDisplay.textContent = '0.0 Hz';
  stringBadges.forEach(b => b.className = 'string-badge');
}

// Autocorrelatie pitch detectie met parabolische interpolatie
function autoCorrelate(buffer, sampleRate) {
  const SIZE = buffer.length;
  let rms = 0;

  for (let i = 0; i < SIZE; i++) {
    rms += buffer[i] * buffer[i];
  }
  rms = Math.sqrt(rms / SIZE);

  // Ruisfilter (noise gate)
  if (rms < 0.015) return -1;

  // Snijvenster bepalen (gitaar bereik ca. 65 Hz tot 450 Hz)
  const minFreq = 65;
  const maxFreq = 450;
  const minPeriod = Math.floor(sampleRate / maxFreq);
  const maxPeriod = Math.floor(sampleRate / minFreq);

  let bestPeriod = -1;
  let bestCorrelation = 0;

  for (let period = minPeriod; period <= maxPeriod; period++) {
    let correlation = 0;
    for (let i = 0; i < maxPeriod; i++) {
      correlation += buffer[i] * buffer[i + period];
    }
    correlation = correlation / maxPeriod;

    if (correlation > bestCorrelation) {
      bestCorrelation = correlation;
      bestPeriod = period;
    }
  }

  if (bestCorrelation > 0.01 && bestPeriod > 0) {
    // Parabolische interpolatie rond het maximum voor sub-sample precisie
    const y1 = buffer[bestPeriod - 1] || 0;
    const y2 = buffer[bestPeriod];
    const y3 = buffer[bestPeriod + 1] || 0;
    const delta = (y3 - y1) / (2 * (2 * y2 - y1 - y3));
    const refinedPeriod = bestPeriod + (isNaN(delta) ? 0 : delta);
    return sampleRate / refinedPeriod;
  }

  return -1;
}

function updatePitch() {
  if (!isRunning) return;

  const buffer = new Float32Array(analyser.fftSize);
  analyser.getFloatTimeDomainData(buffer);

  const freq = autoCorrelate(buffer, audioContext.sampleRate);

  if (freq !== -1) {
    freqDisplay.textContent = `${freq.toFixed(1)} Hz`;

    // Bereken dichtstbijzijnde semitone (A4 = 440 Hz = MIDI 69)
    const midiNum = 12 * (Math.log2(freq / 440)) + 69;
    const roundedMidi = Math.round(midiNum);
    const noteName = NOTE_NAMES[((roundedMidi % 12) + 12) % 12];
    const octave = Math.floor(roundedMidi / 12) - 1;

    // Afwijking in cents (-50 tot +50)
    const cents = Math.round((midiNum - roundedMidi) * 100);

    noteDisplay.textContent = `${noteName}${octave}`;
    centsLabel.textContent = (cents > 0 ? `+${cents}` : `${cents}`) + ' cents';

    // Update naaldrotatie: -50 cents -> -45deg, +50 cents -> +45deg
    const clampedCents = Math.max(-50, Math.min(50, cents));
    const angle = (clampedCents / 50) * 45;
    needle.style.transform = `rotate(${angle}deg)`;

    // Kleuring & Status
    const inTune = Math.abs(cents) <= 4;
    if (inTune) {
      needle.className = 'needle in-tune';
      statusBadge.textContent = 'Stemming Perfect! (Zuiver)';
      statusBadge.className = 'status-badge in-tune';
    } else if (cents < 0) {
      needle.className = 'needle off-tune';
      statusBadge.textContent = 'Te laag (span de snaar op)';
      statusBadge.className = 'status-badge too-low';
    } else {
      needle.className = 'needle off-tune';
      statusBadge.textContent = 'Te hoog (draai snaar losser)';
      statusBadge.className = 'status-badge too-high';
    }

    // Highlight overeenkomende gitaarsnaar
    highlightGuitarString(freq, inTune);
  }

  animationId = requestAnimationFrame(updatePitch);
}

function highlightGuitarString(freq, inTune) {
  let closestString = null;
  let minDiff = Infinity;

  GUITAR_STRINGS.forEach(s => {
    const diff = Math.abs(freq - s.freq);
    if (diff < minDiff && diff < (s.freq * 0.2)) { // binnen 20% van snaarfrequentie
      minDiff = diff;
      closestString = s.name;
    }
  });

  stringBadges.forEach(badge => {
    const stringKey = badge.getAttribute('data-note');
    if (stringKey === closestString) {
      badge.className = inTune ? 'string-badge in-tune' : 'string-badge active';
    } else {
      badge.className = 'string-badge';
    }
  });
}
