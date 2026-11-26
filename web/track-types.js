// What each audio track is. Pre-filled from the file name with the mixer's own rules
// (ZuckerMixer ROLE_SYNONYMS / SYNTH_BRANDS); the person can change it. A type the person
// picks also tells the mixer the track is music, so it is never muted as noise.
// Keep the values in step with track_types.py (tests/test_track_types.py checks it).
const TrackTypes = (() => {
  const TYPES = [
    ['kick', 'Kick'], ['snare', 'Snare'], ['hh', 'Hi-hat'], ['overhead', 'Overhead'], ['drums', 'Drums (other)'],
    ['percussion', 'Percussion'], ['bass', 'Bass'], ['guitar_electric', 'Electric guitar'], ['guitar_acoustic', 'Acoustic guitar'],
    ['keys', 'Piano / keys'], ['synth', 'Synth'], ['sax', 'Saxophone'], ['trumpet', 'Trumpet'], ['trombone', 'Trombone'],
    ['flute', 'Flute'], ['violin', 'Violin'], ['strings', 'Strings'], ['vocal', 'Lead vocal'], ['co_lead_vocal', 'Co-lead vocal'], ['backing_vocal', 'Backing vocal'], ['choir', 'Choir / group vocals'],
    ['podcast_voice', 'Podcast voice'], ['narration', 'Narration voice'], ['room', 'Room / audience'], ['other', 'Other'],
  ];
  const SYN = {
    kick: ['kick', 'kickdrum', 'bd', 'bdjam', 'bombo', 'bass drum', 'low drum'],
    snare: ['snare', 'snr'],
    hh: ['hh', 'hihat', 'hi-hat', 'hi hat', 'high hat', 'cymbal'],
    overhead: ['overhead', 'overheads', 'ov', 'ovjam', 'oh', 'ohl', 'ohr'],
    percussion: ['percussion', 'perc', 'conga', 'bongo', 'cajon', 'shaker', 'tambourine'],
    drums: ['drum', 'drums', 'kit', 'beatbox', 'tom', 'toms', 'floor tom'],
    bass: ['bass', 'bassgtr', 'bass gtr', 'low end', 'electric bass'],
    keys: ['keys', 'keybd', 'keyboard', 'piano', 'organ', 'epiano', 'rhodes', 'synth keys'],
    guitar_acoustic: ['acoustic guitar', 'acoustic', 'acgtr'],
    guitar_electric: ['guit', 'gtr', 'guitar', 'electric guitar'],
    sax: ['sax', 'saxophone', 'alto sax', 'tenor sax', 'baritone sax'],
    trumpet: ['trumpet', 'trump', 'trompeta'],
    trombone: ['trombone', 'bone'],
    flute: ['flute', 'flauta'],
    violin: ['violin', 'fiddle', 'viola', 'cello'],
    strings: ['strings', 'string'],
    synth: ['synth', 'synthesizer', ' moog', 'pad', 'lead synth'],
    podcast_voice: ['podcast', 'host', 'guest'],
    narration: ['narration', 'narrator', 'voiceover', 'voice over', 'vo', 'relato'],
    co_lead_vocal: ['co-lead', 'co lead', 'colead', 'duet vocal', 'duo vocal'],
    choir: ['choir', 'chorus voices', 'choir vocals', 'coro', 'coros'],
    backing_vocal: ['backing', 'bv', 'bvs', 'harmony'],
    vocal: ['vocal', 'vocals', 'vox', 'voice', 'mic', 'microphone', 'singer', 'talkback', 'announcer', 'box'],
    room: ['room', 'ambience', 'ambient', 'amb', 'far mic', 'crowd', 'audience'],
  };
  // Order matters (same as the mixer): brands first, then kit pieces, bass, keys...
  const ORDER = ['kick', 'snare', 'hh', 'overhead', 'percussion', 'drums', 'bass', 'keys', 'guitar_acoustic', 'guitar_electric', 'sax',
    'trumpet', 'trombone', 'flute', 'violin', 'strings', 'synth', 'podcast_voice', 'narration', 'co_lead_vocal', 'choir', 'backing_vocal', 'vocal', 'room'];
  const BRANDS = ['novation', 'nord', 'moog', 'korg', 'juno', 'jupiter', 'prophet', 'sequential', 'minilogue', 'microkorg', 'arturia',
    'microfreak', 'minibrute', 'mininova', 'bass station', 'oberheim', 'dx7', 'op 1', 'op1', 'eurorack', 'modular', 'polysynth'];

  const label = name => String(name || '').replace(/(\.(wav|flac|wv|opus|aiff?|mp3|m4a|ogg))+$/i, '');
  // Recorder prefixes, suffixes, file formats and concert identifiers
  // are metadata, not the instrument. The original filename stays a unique
  // upload/render key; shortened labels are for identification and UI only.
  const sourceLabel = name => {
    let stem = label(String(name || '').split('/').pop()).replace(/\.tracks$/i, '');
    stem = stem.replace(/^[0-9]{8,14}(?=[A-Za-zÀ-ÿ])/, '');
    stem = stem.replace(/t4tinsel$/i, '');
    return stem.replace(/^[\s_\-.]+|[\s_\-.]+$/g, '').replace(/_/g, ' ').replace(/\s+/g, ' ').trim();
  };
  const words = s => s.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const has = (low, list) => {
    const n = words(low), compact = n.replace(/ /g, '');
    return list.some(s => n.includes(s.trim()) || compact.includes(s.trim().replace(/ /g, '')));
  };
  // Short labels (bd, ov, vo, bv...) only as whole words: "Robi" is not "bd", "Novo" not "ov".
  const SHORT = new Set(['bd', 'ov', 'oh', 'ohl', 'ohr', 'hh', 'vo', 'bv', 'amb', 'bone', 'box', 'mic', 'kit', 'perc', 'host']);
  const hasWord = (low, list) => {
    const n = ` ${words(low)} `;
    return list.some(s => SHORT.has(s.trim()) ? n.includes(` ${s.trim()} `) : has(low, [s]));
  };

  function guess(name) {
    const low = sourceLabel(name).toLowerCase(), n = ` ${words(low)} `;
    if (BRANDS.some(b => n.includes(` ${b} `) || words(low).startsWith(b.replace(/ /g, '')))) return 'synth';
    for (const type of ORDER) if (hasWord(low, SYN[type])) return type;
    // Personal names on concert recorder tracks are usually voice mics.
    // Do not guess a generic unstructured filename as a person.
    const cleaned = sourceLabel(name);
    if (/^[A-ZÀ-Ý][a-zà-ÿ]{2,}$/.test(cleaned) && /t4tinsel/i.test(name))
      return 'vocal';
    return 'other';
  }
  // Left / right from the name: "Keys L", "Piano_R", "OH Left".
  // Glued forms too: "KeysL", "PianoR", "OHL" (an instrument word followed by L or R).
  const SIDE_WORDS = new Set(['keys', 'key', 'piano', 'pno', 'synth', 'oh', 'ov', 'overhead', 'gtr', 'guit', 'guitar', 'strings', 'str', 'room', 'amb', 'bv', 'vox', 'pad', 'organ', 'rhodes']);
  function guessSide(name) {
    const n = ` ${words(sourceLabel(name))} `;
    if (/ (l|left|izq|izquierda) $/.test(n)) return 'L';
    if (/ (r|right|der|derecha) $/.test(n)) return 'R';
    const compact = words(sourceLabel(name)).replace(/ /g, '');
    const glued = compact.match(/^(.*?)(l|r)$/);
    if (glued && SIDE_WORDS.has(glued[1])) return glued[2].toUpperCase();
    return '';
  }

  const key = name => label(String(name).split('/').pop()).toLowerCase();
  const chosen = {};  // key -> {type, side, chosen:true} set by the person
  const of = name => chosen[key(name)] || { type: guess(name), side: guessSide(name), chosen: false };
  function set(name, change) { chosen[key(name)] = { ...of(name), ...change, chosen: true }; }
  // For the server: {file name: {type, side, chosen}}.
  const forFiles = files => Object.fromEntries(files.map(f => [String(f).split('/').pop(), of(f)]));

  function controls(name) {
    const now = of(name), esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
    return `<span class="track-type">
      <select data-track-type="${esc(name)}" aria-label="What ${esc(label(name))} is" title="What this track is">${TYPES.map(([v, l]) => `<option value="${v}" ${now.type === v ? 'selected' : ''}>${l}</option>`).join('')}</select>
      <select data-track-side="${esc(name)}" aria-label="Stereo side of ${esc(label(name))}" title="One side of a stereo pair">${[['', 'Mono'], ['L', 'Stereo L'], ['R', 'Stereo R']].map(([v, l]) => `<option value="${v}" ${now.side === v ? 'selected' : ''}>${l}</option>`).join('')}</select>
      ${now.chosen ? '<small>Manual choice</small>' : now.type === 'other' ? '<small>Unknown — select manually</small>' : '<small>Filename suggestion — verify by listening</small>'}
    </span>`;
  }

  document.addEventListener('change', event => {
    const type = event.target.closest('[data-track-type]'), side = event.target.closest('[data-track-side]');
    if (type) set(type.dataset.trackType, { type: type.value });
    if (side) set(side.dataset.trackSide, { side: side.value });
    if (type || side) { const note=event.target.closest('.track-type')?.querySelector('small'); if(note)note.textContent='Manual choice'; }
  });

  const labelOf = name => (TYPES.find(([v]) => v === of(name).type) || [, 'Other'])[1];
  return { TYPES, guess, guessSide, sourceLabel, of, set, forFiles, controls, label: labelOf };
})();
