/* Букифон — интерактивное веб-демо (UI/UX-модель, не прошивка).
   800×480, 4 партии ×16 шагов, 16 энкодеров, 4 страницы параметров, 4 темы экрана,
   42 клавиши, 2 фейдера, 10 джеков, Web MIDI in/out, share через URL. */
"use strict";

const W = 800, H = 480;
const cv = document.getElementById("screen");
const ctx = cv.getContext("2d");
const $ = (id) => document.getElementById(id);

/* ---------- i18n RU/EN (docs/58, docs/61): every visible string is a key ---------- */
const LANG_KEY = "bukifon-demo-lang";
const LANGS = ["ru", "en"];
const I18N = {
  ru: {
    "app.title": "Букифон — интерактивное демо интерфейса",
    "app.desc": "Виртуальный Букифон: панель как у реального синтезатора — 16 энкодеров вокруг экрана 800×480, 42 клавиши Lapka-42 двумя кластерами ±18°, 2 фейдера, 10 джеков, FM-звук, генеративные функции.",
    "app.brand": "БУКИФОН",
    "nav.site": "← сайт",
    "a11y.panel": "Виртуальная панель Букифона",
    "a11y.jacks": "10 джеков",
    "a11y.screen": "Экран Букифона 800×480",
    "a11y.keysLeft": "Левая половина клавиатуры",
    "a11y.keysRight": "Правая половина клавиатуры",
    "a11y.pages": "Страницы параметров",
    "a11y.knobsPage": "Энкодеры А–З: параметры страницы",
    "a11y.knobsMacro": "Энкодеры И–П: макросы выбранных партий",
    "a11y.faders": "Фейдеры",
    "a11y.lang": "Язык интерфейса: русский / English",
    "a11y.langGroup": "Язык интерфейса",
    "a11y.theme": "Тема экрана",
    "a11y.preset": "Слот пресета",
    "a11y.bpm": "Темп, BPM",
    "a11y.volume": "Громкость",
    "a11y.micGain": "Усиление микрофона",
    "a11y.play": "Играть или остановить секвенсор (SPACE)",
    "a11y.stop": "Остановить секвенсор",
    "a11y.rec": "Запись выхода на пэд (R)",
    "a11y.mic": "Включить или выключить микрофон",
    "a11y.beatbox": "Битбокс: стучать 4 секунды, удары станут шагами",
    "a11y.recMic": "Запись с микрофона на пэд, до 30 секунд",
    "a11y.home": "Вернуться в MAIN (HOME)",
    "a11y.undo": "Отменить последнее действие (Ctrl+Z)",
    "a11y.save": "Сохранить пресет в слот",
    "a11y.load": "Загрузить пресет из слота",
    "a11y.compare": "Сравнить A/B паттерна",
    "a11y.random": "Случайный паттерн",
    "a11y.share": "Скопировать ссылку на паттерн",
    "a11y.copyJson": "Скопировать результаты UX-теста в JSON",
    "a11y.fader": "Фейдер {n}: {label}",
    "a11y.knob": "Энкодер {l}: {label}",
    "a11y.jack": "Джек {n}: {name}",
    "a11y.transDown": "Транспонировать вниз на 12 полутонов",
    "a11y.transUp": "Транспонировать вверх на 12 полутонов",
    "a11y.key": "Клавиша {l} ({note})",
    "block.encodersPage": "ЭНКОДЕРЫ А–З · ПАРАМЕТРЫ СТРАНИЦЫ",
    "block.encodersMacro": "ЭНКОДЕРЫ И–П · МАКРОСЫ (выбранные партии)",
    "hint.screen": "Экран 800×480 · 4 темы · табы страниц кликабельны · HOME = MAIN · Shift = подсказка слоя",
    "btn.play": "ИГРА",
    "btn.stop": "СТОП",
    "btn.rec": "ЗАП",
    "btn.mic": "МИК",
    "btn.beatbox": "БИТБОКС→ШАГИ",
    "btn.recMic": "ЗАП МИК",
    "btn.home": "ГЛАВН",
    "btn.undo": "ОТМЕНА",
    "btn.save": "СОХР",
    "btn.load": "ЗАГР",
    "btn.compare": "СРАВН",
    "btn.random": "СЛУЧАЙНЫЙ",
    "btn.share": "Поделиться",
    "btn.copyJson": "COPY JSON",
    "label.bpm": "BPM",
    "label.volume": "VOL",
    "label.theme": "ТЕМА",
    "label.micGain": "УСИЛ MIC",
    "title.track": "Фейдеры: уровень партии и мастер",
    "title.scene": "Фейдеры: морфинг сцен A↔B",
    "title.dj": "Фейдеры: DJ A/B equal-power",
    "page.main": "ГЛАВН",
    "page.fm": "FM",
    "page.env": "ОГИБ",
    "page.fx": "FX",
    "page.gen": "ГЕН",
    "mode.synth": "СИНТ",
    "mode.sampler": "СЭМПЛЕР",
    "mode.daw": "DAW",
    "mode.usbKbd": "USB-КЛАВ",
    "mode.ext": "ВНЕШ",
    "theme.night": "Ночь",
    "theme.amber": "Янтарь",
    "theme.green": "Фосфор",
    "theme.cream": "Крем",
    "fader.partLevel": "УР. ПАРТ",
    "fader.master": "МАСТЕР",
    "fader.sceneAB": "SCENE A↔B",
    "fader.deckA": "DECK A",
    "fader.deckB": "DECK B",
    "fader.f1": "ФЕЙДЕР 1",
    "fader.f2": "ФЕЙДЕР 2",
    "ctx.part": "ПАРТ",
    "ctx.selected": "ВЫБРАНО",
    "ctx.page": "СТР",
    "ctx.faders": "ФЕЙД",
    "ctx.theme": "ТЕМА",
    "ctx.rec": "ЗАП",
    "ctx.mic": "МИК",
    "ctx.on": "ВКЛ",
    "ctx.off": "ВЫКЛ",
    "ctx.unsaved": "НЕ СОХР",
    "col.page": "СТРАНИЦА",
    "col.macros": "МАКРОСЫ",
    "col.ext": "EXT-ТРЕК",
    "param.cutoff": "СРЕЗ",
    "param.reson": "РЕЗОН",
    "param.envAmt": "ОГИБ",
    "param.drive": "ДРАЙВ",
    "param.atk": "АТАКА",
    "param.dec": "СПАД",
    "param.sus": "СУСТ",
    "param.rel": "РЕЛИЗ",
    "param.ratio": "РАТИО",
    "param.depth": "ГЛУБ",
    "param.detune": "ДЕТЮН",
    "param.op2": "OP2",
    "param.fmEnv": "ОГИБ FM",
    "param.feedbk": "ОС",
    "param.noise": "ШУМ",
    "param.sub": "САБ",
    "param.filtEnv": "ОГИБ Ф",
    "param.velSens": "ЧУВСТВ",
    "param.glide": "ГЛАЙД",
    "param.lfoRate": "LFO",
    "param.delayMix": "МИКС",
    "param.time": "ВРЕМЯ",
    "param.crush": "КРАШ",
    "param.width": "ШИРИНА",
    "param.reverb": "РЕВЕРБ",
    "param.master": "МАСТЕР",
    "param.prob": "ВЕРОЯТ",
    "param.euclid": "ЕВКЛИД",
    "param.mutate": "МУТАЦ",
    "param.scale": "ГАММА",
    "param.arpRate": "ТЕМП",
    "param.arpMode": "РЕЖ АРП",
    "param.evolve": "ЭВОЛЮЦ",
    "param.seed": "ЗЕРНО",
    "macro.cut": "СРЕЗ",
    "macro.res": "РЕЗ",
    "macro.atk": "АТК",
    "macro.rel": "РЕЛ",
    "macro.dly": "ЗАД",
    "macro.drv": "ДРВ",
    "macro.crsh": "КРШ",
    "macro.mst": "МАСТ",
    "ext.ch": "КАН",
    "ext.prog": "ПРОГ",
    "ext.vel": "ВЕЛ",
    "ext.len": "ДЛИН",
    "ext.cc": "CC#",
    "ext.ccVal": "CC ЗНАЧ",
    "ext.swing": "СВИНГ",
    "ext.clk": "КЛОК",
    "ext.title": "EXT MIDI · 8 ВНЕШНИХ ТРЕКОВ",
    "ext.clockOut": "CLOCK OUT 24 ppqn",
    "ext.clockOff": "CLOCK OFF — включите ENC П/CLK",
    "synth.part": "PART",
    "synth.mute": "МЬЮТ",
    "synth.off": "ВЫКЛ",
    "status.master": "МАСТЕР",
    "status.mic": "МИК",
    "status.faders": "ФЕЙД: {m} · SPACE = ИГРА · Ctrl+Z = ОТМЕНА",
    "info.bpm": "BPM",
    "info.step": "ШАГ",
    "info.page": "СТР",
    "info.theme": "ТЕМА",
    "unit.hz": "Гц",
    "unit.khz": "кГц",
    "unit.ms": "мс",
    "unit.sec": "с",
    "sampler.title": "СЭМПЛЕР · SD + РЕСЕМПЛ",
    "sampler.recIdle": "ЗАП — кнопка или клавиша R: запись выхода, затем PAD",
    "sampler.recActive": "● ЗАП {s} с / 30 с",
    "sampler.loop": "ЦИКЛ",
    "sampler.oneShot": "ОДИН-ШОТ",
    "sampler.pad": "PAD {n}",
    "sampler.empty": "пусто · нажми ЗАП",
    "sampler.dur": "{s} с",
    "sampler.hint1": "клик по пэду = играть · двойной клик = ЦИКЛ · R = ЗАП · клавиши 1–4 = пэды",
    "sampler.hint2": "записанный сэмпл можно сразу играть/зациклить и сохранить на SD (в демо — в памяти)",
    "daw.title": "DAW · USB HID + MIDI",
    "daw.hint": "Транспорт: ИГРА / СТОП · 16 энкодеров = CC · Web MIDI in/out",
    "usb.title": "USB-КЛАВИАТУРА · HID",
    "usb.hint": "42 клавиши = 42 клавиши HID; слои BASE / SHIFT / SYMBOLS; LAYER переключается энкодером E8.",
    "overlay.title": "СЛОИ И ЖЕСТЫ (удерживайте Shift)",
    "overlay.r1k": "L1 · всегда на экране",
    "overlay.r1v": "игра · 16 энкодеров · фейдеры · транспорт · mute (клик по имени партии)",
    "overlay.r2k": "L2 · страницы",
    "overlay.r2v": "MAIN / FM / ENV / FX — таб на экране или кнопки под панелью; HOME = MAIN",
    "overlay.r3k": "L3 · генеративность",
    "overlay.r3v": "GEN: PROB · EUCLID · MUTATE · SCALE · ARP · EVOLVE · SEED; клик по странице GEN",
    "overlay.r4k": "Фейдеры",
    "overlay.r4v": "TRACK — уровень партии/мастер · SCENE — морфинг A↔B · DJ — A/B equal-power",
    "overlay.r5k": "Shift + фейдер",
    "overlay.r5v": "мастер-громкость (не меняет режим)",
    "overlay.r6k": "Undo / паттерн",
    "overlay.r6v": "Ctrl+Z · Ctrl+C / Ctrl+V · COMPARE = A/B паттерна",
    "overlay.r7k": "Партии",
    "overlay.r7v": "клик по имени = mute; Shift+клик = мультивыбор для группового редактирования",
    "overlay.foot": "отпустите Shift — overlay исчезнет",
    "test.results": "РЕЗУЛЬТАТЫ UX-ТЕСТА",
    "test.line": "{ok} {task}: {sec} с",
    "test.copyHint": "Скопируйте JSON и отправьте в чат проекта. Спасибо!",
    "test.copyHint2": "Нажмите 'COPY JSON' в панели снизу.",
    "test.progress": "UX-ТЕСТ · без подсказок · таймер идёт",
    "test.auto": "Задача считается выполненной автоматически при правильном действии.",
    "test.start": "UX-тест: 8 задач, без подсказок",
    "test.copied": "результаты скопированы",
    "test.t1": "1/8 · Получи звук (клавиши, ИГРА или МИК/битбокс)",
    "test.t2": "2/8 · Открой страницу ОГИБ",
    "test.t3": "3/8 · Замьють две партии",
    "test.t4": "4/8 · Создай евклидов ритм (ГЕН → ЕВКЛИД)",
    "test.t5": "5/8 · Сделай MUTATE и верни назад (ОТМЕНА)",
    "test.t6": "6/8 · Запиши выход на пэд (ЗАП)",
    "test.t7": "7/8 · Переключи фейдеры в SCENE",
    "test.t8": "8/8 · Вернись в ГЛАВН одним жестом (кнопка ГЛАВН)",
    "task.sound": "звук",
    "task.env": "страница ОГИБ",
    "task.mute2": "мьют 2 партий",
    "task.euclid": "евклид",
    "task.mutundo": "MUTATE+UNDO",
    "task.record": "ЗАП",
    "task.scene": "SCENE",
    "task.home": "ГЛАВН",
    "msg.undo": "отмена",
    "msg.rec": "ЗАП ●",
    "msg.micOn": "МИК ON (монитор выключен)",
    "msg.micOff": "МИК OFF",
    "msg.micEnable": "включите МИК",
    "msg.micRec": "ЗАП МИК ● (до 30 с)",
    "msg.micShort": "ЗАП МИК: слишком коротко",
    "msg.micToPad": "МИК → PAD {n} ({s} с)",
    "msg.beatbox": "БИТБОКС: стучите 4 секунды…",
    "msg.beatboxDone": "БИТБОКС → {n} шагов (PART {p})",
    "msg.recShort": "ЗАП: слишком коротко",
    "msg.recToPad": "ЗАП → PAD {n} ({s} с)",
    "msg.evolve": "EVOLVE",
    "msg.modOn": "MOD ON",
    "msg.modOff": "MOD OFF",
    "msg.faders": "фейдеры: {m}",
    "msg.patternCopied": "паттерн скопирован",
    "msg.patternPasted": "паттерн вставлен",
    "msg.random": "случайный паттерн",
    "msg.transpose": "транспозиция {n}",
    "msg.presetSaved": "пресет {n} сохранён",
    "msg.presetEmpty": "пустой слот {n}",
    "msg.presetLoaded": "пресет {n} загружен",
    "msg.abSaved": "A сохранён · нажмите ещё раз для B",
    "msg.abToggled": "A/B переключено",
    "msg.home": "ГЛАВН · MAIN",
    "msg.linkCopied": "ссылка скопирована",
    "msg.micErr": "МИК: {err}",
    "midi.waiting": "MIDI: ждём",
    "midi.noInputs": "MIDI: нет входов",
    "midi.outOk": " · OUT OK",
    "midi.noAccess": "MIDI: нет доступа",
    "midi.list": "MIDI: {names}",
    "preset.option": "ПРЕСЕТ {n}",
    "footer.before": "Это",
    "footer.strong": "демо интерфейса и звука",
    "footer.after": ", а не прошивка: FM-движок упрощён, сэмплер/DAW схематичны. Реальный инструмент — ESP32-P4, RGB565 800×480, 16 энкодеров EC11, 42 клавиши Lapka-42, 2 фейдера, 10 джеков. UX-исследование и рубрика —",
  },
  en: {
    "app.title": "Bukifon — interactive interface demo",
    "app.desc": "Virtual Bukifon: a panel like the real synth — 16 encoders around the 800×480 screen, 42 Lapka-42 keys in two ±18° clusters, 2 faders, 10 jacks, FM sound, generative functions.",
    "app.brand": "BUKIFON",
    "nav.site": "← site",
    "a11y.panel": "Bukifon virtual panel",
    "a11y.jacks": "10 jacks",
    "a11y.screen": "Bukifon screen 800×480",
    "a11y.keysLeft": "Left keyboard half",
    "a11y.keysRight": "Right keyboard half",
    "a11y.pages": "Parameter pages",
    "a11y.knobsPage": "Encoders А–З: page parameters",
    "a11y.knobsMacro": "Encoders И–П: macros of selected parts",
    "a11y.faders": "Faders",
    "a11y.lang": "Interface language: English / русский",
    "a11y.langGroup": "Interface language",
    "a11y.theme": "Screen theme",
    "a11y.preset": "Preset slot",
    "a11y.bpm": "Tempo, BPM",
    "a11y.volume": "Volume",
    "a11y.micGain": "Microphone gain",
    "a11y.play": "Play or stop the sequencer (SPACE)",
    "a11y.stop": "Stop the sequencer",
    "a11y.rec": "Record output to a pad (R)",
    "a11y.mic": "Toggle microphone",
    "a11y.beatbox": "Beatbox: tap for 4 seconds, hits become steps",
    "a11y.recMic": "Record microphone to a pad, up to 30 seconds",
    "a11y.home": "Back to MAIN (HOME)",
    "a11y.undo": "Undo the last action (Ctrl+Z)",
    "a11y.save": "Save preset to slot",
    "a11y.load": "Load preset from slot",
    "a11y.compare": "Compare pattern A/B",
    "a11y.random": "Random pattern",
    "a11y.share": "Copy pattern link",
    "a11y.copyJson": "Copy UX test results as JSON",
    "a11y.fader": "Fader {n}: {label}",
    "a11y.knob": "Encoder {l}: {label}",
    "a11y.jack": "Jack {n}: {name}",
    "a11y.transDown": "Transpose down 12 semitones",
    "a11y.transUp": "Transpose up 12 semitones",
    "a11y.key": "Key {l} ({note})",
    "block.encodersPage": "ENCODERS А–З · PAGE PARAMETERS",
    "block.encodersMacro": "ENCODERS И–П · MACROS (selected parts)",
    "hint.screen": "800×480 screen · 4 themes · page tabs clickable · HOME = MAIN · Shift = layer hints",
    "btn.play": "PLAY",
    "btn.stop": "STOP",
    "btn.rec": "REC",
    "btn.mic": "MIC",
    "btn.beatbox": "BEATBOX→STEPS",
    "btn.recMic": "REC MIC",
    "btn.home": "HOME",
    "btn.undo": "UNDO",
    "btn.save": "SAVE",
    "btn.load": "LOAD",
    "btn.compare": "COMPARE",
    "btn.random": "RANDOM",
    "btn.share": "Share",
    "btn.copyJson": "COPY JSON",
    "label.bpm": "BPM",
    "label.volume": "VOL",
    "label.theme": "THEME",
    "label.micGain": "MIC GAIN",
    "title.track": "Faders: part level and master",
    "title.scene": "Faders: scene A↔B morph",
    "title.dj": "Faders: DJ A/B equal-power",
    "page.main": "MAIN",
    "page.fm": "FM",
    "page.env": "ENV",
    "page.fx": "FX",
    "page.gen": "GEN",
    "mode.synth": "SYNTH",
    "mode.sampler": "SAMPLER",
    "mode.daw": "DAW",
    "mode.usbKbd": "USB-KBD",
    "mode.ext": "EXT",
    "theme.night": "Night",
    "theme.amber": "Amber",
    "theme.green": "Phosphor",
    "theme.cream": "Cream",
    "fader.partLevel": "PART LEVEL",
    "fader.master": "MASTER",
    "fader.sceneAB": "SCENE A↔B",
    "fader.deckA": "DECK A",
    "fader.deckB": "DECK B",
    "fader.f1": "FADER 1",
    "fader.f2": "FADER 2",
    "ctx.part": "PART",
    "ctx.selected": "SELECTED",
    "ctx.page": "PAGE",
    "ctx.faders": "FADERS",
    "ctx.theme": "THEME",
    "ctx.rec": "REC",
    "ctx.mic": "MIC",
    "ctx.on": "ON",
    "ctx.off": "OFF",
    "ctx.unsaved": "UNSAVED",
    "col.page": "PAGE",
    "col.macros": "MACROS",
    "col.ext": "EXT TRACK",
    "param.cutoff": "CUTOFF",
    "param.reson": "RESON",
    "param.envAmt": "ENV AMT",
    "param.drive": "DRIVE",
    "param.atk": "ATK",
    "param.dec": "DEC",
    "param.sus": "SUS",
    "param.rel": "REL",
    "param.ratio": "RATIO",
    "param.depth": "DEPTH",
    "param.detune": "DETUNE",
    "param.op2": "OP2",
    "param.fmEnv": "FM ENV",
    "param.feedbk": "FEEDBK",
    "param.noise": "NOISE",
    "param.sub": "SUB",
    "param.filtEnv": "FILT ENV",
    "param.velSens": "VEL SENS",
    "param.glide": "GLIDE",
    "param.lfoRate": "LFO RATE",
    "param.delayMix": "DLY MIX",
    "param.time": "TIME",
    "param.crush": "CRUSH",
    "param.width": "WIDTH",
    "param.reverb": "REVERB",
    "param.master": "MASTER",
    "param.prob": "PROB",
    "param.euclid": "EUCLID",
    "param.mutate": "MUTATE",
    "param.scale": "SCALE",
    "param.arpRate": "ARP RATE",
    "param.arpMode": "ARP MOD",
    "param.evolve": "EVOLVE",
    "param.seed": "SEED",
    "macro.cut": "CUT",
    "macro.res": "RES",
    "macro.atk": "ATK",
    "macro.rel": "REL",
    "macro.dly": "DLY",
    "macro.drv": "DRV",
    "macro.crsh": "CRSH",
    "macro.mst": "MST",
    "ext.ch": "CH",
    "ext.prog": "PROG",
    "ext.vel": "VEL",
    "ext.len": "LEN",
    "ext.cc": "CC#",
    "ext.ccVal": "CC VAL",
    "ext.swing": "SWING",
    "ext.clk": "CLK",
    "ext.title": "EXT MIDI · 8 EXTERNAL TRACKS",
    "ext.clockOut": "CLOCK OUT 24 ppqn",
    "ext.clockOff": "CLOCK OFF — enable ENC П/CLK",
    "synth.part": "PART",
    "synth.mute": "MUTE",
    "synth.off": "OFF",
    "status.master": "MASTER",
    "status.mic": "MIC",
    "status.faders": "FADERS: {m} · SPACE = PLAY · Ctrl+Z = UNDO",
    "info.bpm": "BPM",
    "info.step": "STEP",
    "info.page": "PAGE",
    "info.theme": "THEME",
    "unit.hz": "Hz",
    "unit.khz": "kHz",
    "unit.ms": "ms",
    "unit.sec": "s",
    "sampler.title": "SAMPLER · SD + RESAMPLE",
    "sampler.recIdle": "REC — button or key R: record output, then PAD",
    "sampler.recActive": "● REC {s} s / 30 s",
    "sampler.loop": "LOOP",
    "sampler.oneShot": "ONE-SHOT",
    "sampler.pad": "PAD {n}",
    "sampler.empty": "empty · hit REC",
    "sampler.dur": "{s} s",
    "sampler.hint1": "click pad = play · double click = LOOP · R = REC · keys 1–4 = pads",
    "sampler.hint2": "a recorded sample can be played/looped right away and saved to SD (in-memory in the demo)",
    "daw.title": "DAW · USB HID + MIDI",
    "daw.hint": "Transport: PLAY / STOP · 16 encoders = CC · Web MIDI in/out",
    "usb.title": "USB KEYBOARD · HID",
    "usb.hint": "42 keys = 42 HID keys; BASE / SHIFT / SYMBOLS layers; LAYER is switched by encoder E8.",
    "overlay.title": "LAYERS AND GESTURES (hold Shift)",
    "overlay.r1k": "L1 · always on screen",
    "overlay.r1v": "play · 16 encoders · faders · transport · mute (click the part name)",
    "overlay.r2k": "L2 · pages",
    "overlay.r2v": "MAIN / FM / ENV / FX — tab on screen or buttons under the panel; HOME = MAIN",
    "overlay.r3k": "L3 · generative",
    "overlay.r3v": "GEN: PROB · EUCLID · MUTATE · SCALE · ARP · EVOLVE · SEED; click the GEN page",
    "overlay.r4k": "Faders",
    "overlay.r4v": "TRACK — part level/master · SCENE — A↔B morph · DJ — A/B equal-power",
    "overlay.r5k": "Shift + fader",
    "overlay.r5v": "master volume (mode unchanged)",
    "overlay.r6k": "Undo / pattern",
    "overlay.r6v": "Ctrl+Z · Ctrl+C / Ctrl+V · COMPARE = A/B of the pattern",
    "overlay.r7k": "Parts",
    "overlay.r7v": "click a name = mute; Shift+click = multi-select for group editing",
    "overlay.foot": "release Shift — the overlay disappears",
    "test.results": "UX TEST RESULTS",
    "test.line": "{ok} {task}: {sec} s",
    "test.copyHint": "Copy the JSON and send it to the project chat. Thanks!",
    "test.copyHint2": "Press 'COPY JSON' in the panel below.",
    "test.progress": "UX TEST · no hints · timer running",
    "test.auto": "A task is completed automatically on the right action.",
    "test.start": "UX test: 8 tasks, no hints",
    "test.copied": "results copied",
    "test.t1": "1/8 · Make a sound (keys, PLAY or MIC/beatbox)",
    "test.t2": "2/8 · Open the ENV page",
    "test.t3": "3/8 · Mute two parts",
    "test.t4": "4/8 · Create a Euclidean rhythm (GEN → EUCLID)",
    "test.t5": "5/8 · Do a MUTATE and undo it (UNDO)",
    "test.t6": "6/8 · Record the output to a pad (REC)",
    "test.t7": "7/8 · Switch the faders to SCENE",
    "test.t8": "8/8 · Return to MAIN in one gesture (HOME)",
    "task.sound": "sound",
    "task.env": "ENV page",
    "task.mute2": "mute 2 parts",
    "task.euclid": "euclid",
    "task.mutundo": "MUTATE+UNDO",
    "task.record": "REC",
    "task.scene": "SCENE",
    "task.home": "HOME",
    "msg.undo": "undo",
    "msg.rec": "REC ●",
    "msg.micOn": "MIC ON (monitor muted)",
    "msg.micOff": "MIC OFF",
    "msg.micEnable": "turn the MIC on",
    "msg.micRec": "REC MIC ● (up to 30 s)",
    "msg.micShort": "MIC REC: too short",
    "msg.micToPad": "MIC → PAD {n} ({s} s)",
    "msg.beatbox": "BEATBOX: tap for 4 seconds…",
    "msg.beatboxDone": "BEATBOX → {n} steps (PART {p})",
    "msg.recShort": "REC: too short",
    "msg.recToPad": "REC → PAD {n} ({s} s)",
    "msg.evolve": "EVOLVE",
    "msg.modOn": "MOD ON",
    "msg.modOff": "MOD OFF",
    "msg.faders": "faders: {m}",
    "msg.patternCopied": "pattern copied",
    "msg.patternPasted": "pattern pasted",
    "msg.random": "random pattern",
    "msg.transpose": "transpose {n}",
    "msg.presetSaved": "preset {n} saved",
    "msg.presetEmpty": "empty slot {n}",
    "msg.presetLoaded": "preset {n} loaded",
    "msg.abSaved": "A saved · press again for B",
    "msg.abToggled": "A/B toggled",
    "msg.home": "HOME · MAIN",
    "msg.linkCopied": "link copied",
    "msg.micErr": "MIC: {err}",
    "midi.waiting": "MIDI: waiting",
    "midi.noInputs": "MIDI: no inputs",
    "midi.outOk": " · OUT OK",
    "midi.noAccess": "MIDI: no access",
    "midi.list": "MIDI: {names}",
    "preset.option": "PRESET {n}",
    "footer.before": "This is a",
    "footer.strong": "UI and sound demo",
    "footer.after": ", not the firmware: the FM engine is simplified, the sampler/DAW are schematic. The real instrument is ESP32-P4, RGB565 800×480, 16 EC11 encoders, 42 Lapka-42 keys, 2 faders, 10 jacks. UX research and rubric —",
  },
};
let LANG = "ru";
const i18nMissing = [];
function t(key, vars) {
  const table = I18N[LANG] || I18N.ru;
  let s = Object.prototype.hasOwnProperty.call(table, key) ? table[key] : null;
  if (s == null) { i18nMissing.push(key); return "?" + key + "?"; }
  if (vars) for (const k in vars) s = s.split("{" + k + "}").join(String(vars[k]));
  return s;
}
function themeLabel(name) { return t("theme." + name); }
function initLang() {
  let fromUrl = null;
  try { fromUrl = (new URLSearchParams(location.search).get("lang") || "").toLowerCase(); } catch (e) {}
  let fromStore = null;
  try { fromStore = (localStorage.getItem(LANG_KEY) || "").toLowerCase(); } catch (e) {}
  if (fromUrl && LANGS.includes(fromUrl)) {
    LANG = fromUrl;
    try { localStorage.setItem(LANG_KEY, LANG); } catch (e) {}
  } else if (fromStore && LANGS.includes(fromStore)) {
    LANG = fromStore;
  }
  return LANG;
}
function syncLangUrl() {
  try {
    const u = new URL(location.href);
    if (LANG === "en") u.searchParams.set("lang", "en");
    else u.searchParams.delete("lang");
    history.replaceState(null, "", u.toString());
  } catch (e) {}
}

const MODES = ["mode.synth", "mode.sampler", "mode.daw", "mode.usbKbd", "mode.ext"];
const PAGES = ["page.main", "page.fm", "page.env", "page.fx", "page.gen"];
const PAGE_PARAM_KEYS = [
  ["param.cutoff", "param.reson", "param.envAmt", "param.drive", "param.atk", "param.dec", "param.sus", "param.rel"],
  ["param.ratio", "param.depth", "param.detune", "param.op2", "param.fmEnv", "param.feedbk", "param.noise", "param.sub"],
  ["param.atk", "param.dec", "param.sus", "param.rel", "param.filtEnv", "param.velSens", "param.glide", "param.lfoRate"],
  ["param.delayMix", "param.feedbk", "param.time", "param.drive", "param.crush", "param.width", "param.reverb", "param.master"],
  ["param.prob", "param.euclid", "param.mutate", "param.scale", "param.arpRate", "param.arpMode", "param.evolve", "param.seed"],
];
const PAGE_MIN = [[80,0,0,0,1,20,0,20],[1,0,0,0,0,0,0,0],[1,20,0,20,0,0,0,0],[0,0,20,0,0,0,0,0],[0,0,0,0,0,0,0,0]];
const PAGE_MAX = [[12000,100,100,100,2000,3000,100,3000],[8,100,50,100,100,100,100,100],[2000,3000,100,3000,100,100,500,100],[100,100,800,100,100,100,100,100],[100,16,12,4,3,2,1,999]];
const THEMES = {
  night:  { name:"Night",   bg:"#0a1a1d", panel:"#0d2428", card:"#0e2024", line:"#1e3a3f", text:"#d7ecef", muted:"#7fb6bc", accent:"#4fd1e0", green:"#38c172", orange:"#f6993f", blue:"#4aa3ff", red:"#ff5c5c", purple:"#b07cff" },
  amber:  { name:"Amber",   bg:"#0e0b08", panel:"#1a130c", card:"#1f1710", line:"#3a2a16", text:"#f2e6d2", muted:"#b99b74", accent:"#ffb347", green:"#7fbf5f", orange:"#f08a24", blue:"#5fa8d3", red:"#e5544b", purple:"#c9a0dc" },
  green:  { name:"Phosphor",bg:"#0a140c", panel:"#102016", card:"#12261a", line:"#23402c", text:"#d8f5dc", muted:"#7fbf92", accent:"#5cff8a", green:"#38c172", orange:"#c9d96b", blue:"#6fd3c0", red:"#ff6b5c", purple:"#9ccf7a" },
  cream:  { name:"Cream",   bg:"#e8e2d4", panel:"#dcd4c4", card:"#f2ede2", line:"#b9ae9a", text:"#2a241c", muted:"#5f5548", accent:"#a8321f", green:"#3f6f2e", orange:"#9a4a10", blue:"#3d6e8f", red:"#9c2a1a", purple:"#8a5a9e" },
};
const PART_NAMES = ["FAT SAW", "FM BELL", "POLY VOX", "LADDER LEAD"];
const SCALES = [[0,0,7,12,3,10,5,7],[0,12,7,16,19,24,14,21],[0,7,12,16,19,21,24,28],[0,2,5,7,12,14,17,19]];
const NOTE_SCALES=[[0,2,3,5,7,8,10],[0,2,4,5,7,9,11],[0,2,4,7,9],[0,2,3,5,7,9,10]];
const SCALE_NAMES=["OFF","MINOR","MAJOR","PENTA","DORIAN"];
const ARP_RATES=[0.5,0.25,0.125]; const ARP_MODES=["UP","DOWN","UPDOWN"];
const EXT_PARAM_KEYS = ["ext.ch", "ext.prog", "ext.vel", "ext.len", "ext.cc", "ext.ccVal", "ext.swing", "ext.clk"];
const EXT_MIN=[1,0,1,1,0,0,50,0], EXT_MAX=[16,127,127,16,127,127,75,1];
const JACKS = ["CV OUT 1","CV OUT 2","CV OUT 3","CV OUT 4","CV IN 1","CV IN 2","GATE OUT","GATE IN","CLK OUT","CLK IN"];
const CC_BASE = [[74,71,73,91,73,75,76,72],[20,21,22,23,24,25,26,27],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0]];

const state = { mode:0, page:0, theme:"night", faderMode:"TRACK", selParts:new Set([0]), modOn:true, seed:7, extSel:0, extStep:0, extTracks:[], extClock:false, mic:{on:false,gain:1,level:0,beat:false}, test:{active:false,idx:0,t0:0,results:[],done:false}, bpm:120, playing:false, step:0, selPart:0, volume:0.7, delayMix:0.25, cables:new Set(), parts:[], capture:false, pads:[], recording:false, recStarted:0 };
function defaultPart(i) {
  return {
    name: PART_NAMES[i], active: i < 2, mute:false, level: 0.85, sceneX: 0,
    root: [48,72,60,55][i],
    steps: Array.from({length:16},(_,s)=>({on:s%4===0||(s%7===3), note:SCALES[i][s%8], accent:s%4===0})),
    pages: [
      [3200-i*700, 20+i*15, 40, 15, 10+i*15, 240+i*80, 60, 420],
      [[2,3,1.5,4][i], 55-i*8, 6, 40, 30, 10, 0, 25],
      [10+i*15, 240+i*80, 60, 420, 30, 60, 0, 20],
      [25, 30, 280, 10, 0, 50, 15, 70],
      [i===0?100:70, 4+i*2, 0, 1, 0, 0, 0, 7+i*13],
    ],
  };
}
state.parts = [0,1,2,3].map(defaultPart);
state.extTracks = Array.from({length:8},(_,i)=>({ch:i+1, prog:i, vel:100, ccNum:74+i, steps:Array.from({length:16},(_,s2)=>({on:s2%4===0, note:[0,7,12,3][s2%4], vel:100, cc:64}))}));
let T = THEMES[state.theme];
if (typeof window !== "undefined") window.state = state;
const COLOR = [T.green, T.orange, T.blue, T.purple];
const undoStack = [];

/* ---------- helpers ---------- */
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
function partColor(i){ return [T.green,T.orange,T.blue,T.purple][i]; }
function roundRect(x,y,w,h,r){ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath();}
function pmin(page,i){ return PAGE_MIN[page][i]; }
function pmax(page,i){ return PAGE_MAX[page][i]; }
function pval(){ return state.parts[state.selPart].pages[state.page]; }
function selectedParts(){ return [...state.selParts].filter(i=>state.parts[i]); }
function extTrack(){ return state.extTracks[state.extSel]; }
function extVal(i){ const tr=extTrack(); return [tr.ch,tr.prog,(tr.vel??100),tr.len||4,tr.ccNum,tr.steps[state.extStep].cc,state.extSwing??50,state.extClock?1:0][i]; }
function extSet(i,v){ const tr=extTrack(); if(i===0)tr.ch=clamp(Math.round(v),1,16); else if(i===1)tr.prog=clamp(Math.round(v),0,127); else if(i===2)tr.vel=clamp(Math.round(v),1,127); else if(i===3)tr.len=clamp(Math.round(v),1,16); else if(i===4)tr.ccNum=clamp(Math.round(v),0,127); else if(i===5)tr.steps[state.extStep].cc=clamp(Math.round(v),0,127); else if(i===6)state.extSwing=clamp(Math.round(v),50,75); else if(i===7)state.extClock=!!Math.round(v); }
function applyParam(page,i,val){ for(const pi of selectedParts()) state.parts[pi].pages[page][i]=val; }
function snapshot(){ try { undoStack.push(JSON.stringify(state.parts)); if (undoStack.length>30) undoStack.shift(); } catch(e){} }
function undo(){ const s=undoStack.pop(); if(!s) return; if(TEST && TEST.chgMutate) TEST.mutundo=true; try { state.parts=JSON.parse(s); paintKnobs(); save(); flashMsg(t("msg.undo")); } catch(e){} }

/* ---------- audio ---------- */
let AC=null, master, comp, delay, delayGain, analyser, masterData, recNode=null;
function audioInit(){
  if (AC) return;
  AC = new (window.AudioContext||window.webkitAudioContext)();
  master=AC.createGain(); master.gain.value=state.volume;
  comp=AC.createDynamicsCompressor(); comp.threshold.value=-12; comp.knee.value=12; comp.ratio.value=6;
  delay=AC.createDelay(1.2); delay.delayTime.value=0.28;
  const fb=AC.createGain(); fb.gain.value=0.32;
  delayGain=AC.createGain(); delayGain.gain.value=state.delayMix;
  analyser=AC.createAnalyser(); analyser.fftSize=512; masterData=new Uint8Array(analyser.fftSize);
  master.connect(comp); comp.connect(AC.destination); comp.connect(analyser);
  // запись выхода: ScriptProcessor-тап (без аллокаций в реальном железе — здесь для демо)
  recNode = AC.createScriptProcessor(4096, 2, 2);
  const silent = AC.createGain(); silent.gain.value = 0;
  comp.connect(recNode); recNode.connect(silent); silent.connect(AC.destination);
  recNode.onaudioprocess = (ev) => {
    if (!state.recording) return;
    const l = ev.inputBuffer.getChannelData(0), r = ev.inputBuffer.getChannelData(1);
    recChunks.push([new Float32Array(l), new Float32Array(r)]);
    if (AC.currentTime - state.recStarted > 30) finishRec();
  };
  master.connect(delay); delay.connect(fb); fb.connect(delay); delay.connect(delayGain); delayGain.connect(comp);
}
const mtof=(m)=>440*Math.pow(2,(m-69)/12);
const voices=[];
let recChunks=[];
function noteOn(midi, vel=0.8, part=state.parts[state.selPart]){
  if(TEST) TEST.sound=true;
  audioInit(); if (AC.state==="suspended") AC.resume();
  const now=AC.currentTime;
  const m=part.pages[0], f=part.pages[1], e=part.pages[2], x=part.pages[3];
  vel = vel * (part.level != null ? part.level : 1);
  const v={midi, part, vel, dead:false,
    carrier:AC.createOscillator(), mod:AC.createOscillator(), modGain:AC.createGain(),
    amp:AC.createGain(), filt:AC.createBiquadFilter()};
  const cutoff=clamp(m[0],80,12000), q=clamp(m[1],0,100), drive=(clamp(m[3],0,100)+clamp(x[3],0,100))/200;
  const ratio=clamp(f[0],1,8), depth=f[1]/100, detune=f[2]/100;
  v.carrier.frequency.value=mtof(midi)*(1+detune*0.02);
  v.mod.frequency.value=mtof(midi)*ratio;
  v.modGain.gain.value=mtof(midi)*(0.4+depth*3);
  v.mod.connect(v.modGain); v.modGain.connect(v.carrier.frequency);
  v.filt.type="lowpass"; v.filt.frequency.value=cutoff; v.filt.Q.value=q/12;
  v.carrier.connect(v.filt); v.filt.connect(v.amp); v.amp.connect(master);
  const atk=Math.max(0.002,e[0]/1000), dec=Math.max(0.02,e[1]/1000), sus=clamp(e[2]/100,0,1), rel=Math.max(0.02,e[3]/1000);
  v.amp.gain.setValueAtTime(0,now);
  v.amp.gain.linearRampToValueAtTime(vel*0.9,now+atk);
  v.amp.gain.linearRampToValueAtTime(vel*0.9*(0.25+sus*0.75),now+atk+dec);
  v.carrier.start(now); v.mod.start(now); voices.push(v);
  if (voices.length>24) killVoice(voices.shift());
  return v;
}
function killVoice(v, rel=null){
  if(!v||v.dead) return;
  v.dead=true; audioInit();
  const now=AC.currentTime, r=rel ?? Math.max(0.02, v.part.pages[2][3]/1000);
  try{ v.amp.gain.cancelScheduledValues(now); v.amp.gain.setValueAtTime(Math.max(0.0001,v.amp.gain.value),now); v.amp.gain.exponentialRampToValueAtTime(0.0001,now+r); v.carrier.stop(now+r+0.05); v.mod.stop(now+r+0.05);}catch(e){try{v.carrier.stop();v.mod.stop();}catch(e2){}}
}
function noteOff(midi){ voices.filter(v=>v.midi===midi&&!v.dead).forEach(v=>killVoice(v)); }
function allNotesOff(){ voices.forEach(v=>killVoice(v)); }

/* ---------- UX-тест (blind-usability): ?test=1 ---------- */
const UTASKS=[
 {id:"sound",   text:"test.t1"},
 {id:"env",     text:"test.t2"},
 {id:"mute2",   text:"test.t3"},
 {id:"euclid",  text:"test.t4"},
 {id:"mutundo", text:"test.t5"},
 {id:"record",  text:"test.t6"},
 {id:"scene",   text:"test.t7"},
 {id:"home",    text:"test.t8"},
];
const TFLAGS={sound:false,env:false,mute2:false,euclid:false,chgMutate:false,mutundo:false,record:false,scene:false,home:false,leftMain:false};
let TEST=null;
function startTest(){ state.test={active:true,idx:0,t0:performance.now(),results:[],done:false}; TEST=TFLAGS; if(typeof window!=="undefined") window.TEST=TEST; for(const k in TEST) TEST[k]=false; state.page=0; state.mode=0; flashMsg(t("test.start")); }
function finishTest(){ state.test.active=false; state.test.done=true; }
function copyTestResults(){ const r={date:new Date().toISOString(),lang:LANG,tasks:state.test.results,score:state.test.results.filter(x=>x.ok).length,total:UTASKS.length}; const t2=JSON.stringify(r,null,1); if(navigator.clipboard) navigator.clipboard.writeText(t2).catch(()=>{}); flashMsg(t("test.copied")); }
function checkTest(){
  if(!state.test.active) return;
  const t=TEST, idx=state.test.idx, task=UTASKS[idx]; if(!task) return;
  let ok=false;
  switch(task.id){
    case "sound": ok=t.sound; break;
    case "env": ok=(state.page===2); break;
    case "mute2": ok=state.parts.filter(p=>p.mute).length>=2; break;
    case "euclid": ok=(t.euclid); break;
    case "mutundo": ok=t.mutundo; break;
    case "record": ok=(state.pads.length>0 || t.record); break;
    case "scene": ok=(state.faderMode==="SCENE"); break;
    case "home": ok=(state.page===0 && t.leftMain); break;
  }
  if((state.page!==0)||state.mode!==0) t.leftMain=true;
  if(ok){ state.test.results.push({task:task.id, ok:true, sec:Math.round((performance.now()-state.test.t0)/100)/10}); state.test.idx++; state.test.t0=performance.now(); if(state.test.idx>=UTASKS.length) finishTest(); }
}
function drawTestOverlay(){
  const res=state.test;
  ctx.fillStyle="rgba(4,10,12,0.9)"; roundRect(20,64,W-40,H-160,10); ctx.fill();
  ctx.strokeStyle=T.accent; ctx.lineWidth=2; roundRect(20,64,W-40,H-160,10); ctx.stroke();
  if(res.done){
    ctx.fillStyle=T.accent; ctx.font="700 18px Inter"; ctx.fillText(t("test.results"),40,96);
    ctx.fillStyle=T.text; ctx.font="600 13px Inter";
    let y=128; res.results.forEach(r=>{ ctx.fillText(t("test.line",{ok:r.ok?"✅":"❌",task:t("task."+r.task),sec:r.sec}),48,y); y+=24; });
    ctx.fillStyle=T.muted; ctx.font="600 12px Inter"; ctx.fillText(t("test.copyHint"),40,y+12);
    ctx.fillStyle=T.text; ctx.font="700 13px Inter"; ctx.fillText(t("test.copyHint2"),40,y+36);
    return;
  }
  const task=UTASKS[res.idx];
  ctx.fillStyle=T.muted; ctx.font="600 12px Inter"; ctx.fillText(t("test.progress"),40,96);
  ctx.fillStyle=T.text; ctx.font="700 18px Inter"; ctx.fillText(task?t(task.text):"",40,130);
  const sec=((performance.now()-res.t0)/1000).toFixed(1); ctx.fillStyle=T.accent; ctx.font="700 28px Inter"; ctx.fillText(sec+" "+t("unit.sec"),40,178);
  ctx.fillStyle=T.muted; ctx.font="600 12px Inter"; ctx.fillText(t("test.auto"),40,214);
  ctx.fillStyle=T.line; ctx.fillRect(40,240,W-80,6); ctx.fillStyle=T.green; ctx.fillRect(40,240,(W-80)*(res.idx/UTASKS.length),6);
}
/* ---------- микрофон: уровень, запись, битбокс ---------- */
let micStream=null, micAnalyser=null, micData=null, beatTimer=null, beatHits=[], micRecNode=null, micChunks=[], micRecording=false, micSrcNode=null, micGainNode=null;
async function micToggle(){
  if(state.mic.on){ micStop(); flashMsg(t("msg.micOff")); return; }
  try{
    micStream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:false,noiseSuppression:false,autoGainControl:false}});
    audioInit();
    const src=AC.createMediaStreamSource(micStream);
    const g=AC.createGain(); g.gain.value=state.mic.gain;
    micAnalyser=AC.createAnalyser(); micAnalyser.fftSize=1024; micData=new Uint8Array(micAnalyser.fftSize);
    src.connect(g); g.connect(micAnalyser); // НЕ в destination — без обратной связи
    micSrcNode=src; micGainNode=g;
    micRecNode=AC.createScriptProcessor(4096,1,1);
    micRecNode.onaudioprocess=(ev)=>{ if(!micRecording) return; const d=ev.inputBuffer.getChannelData(0); micChunks.push(new Float32Array(d)); if(micChunks.length> (30*48000/4096)) stopMicRec(); };
    g.connect(micRecNode); const silent=AC.createGain(); silent.gain.value=0; micRecNode.connect(silent); silent.connect(AC.destination);
    state.mic.on=true; $("btnMic").classList.add("on");
    flashMsg(t("msg.micOn")); renderContextBar();
  }catch(e){ state.mic.err=String(e && e.message || e); flashMsg(t("msg.micErr",{err:state.mic.err})); }
}
function micStop(){ if(micRecording) stopMicRec(); if(micStream){ micStream.getTracks().forEach(t=>t.stop()); micStream=null; } micAnalyser=null; micRecNode=null; state.mic.on=false; state.mic.level=0; $("btnMic").classList.remove("on"); renderContextBar(); }
function startMicRec(){ if(!state.mic.on){ flashMsg(t("msg.micEnable")); return; } if(micRecording) return; micChunks=[]; micRecording=true; $("btnRecMic").classList.add("on"); flashMsg(t("msg.micRec")); }
function stopMicRec(){
  if(!micRecording) return; micRecording=false; $("btnRecMic").classList.remove("on");
  let len=0; for(const c of micChunks) len+=c.length;
  if(len<2048 || !AC){ flashMsg(t("msg.micShort")); micChunks=[]; return; }
  const buf=AC.createBuffer(1,len,AC.sampleRate); const ch=buf.getChannelData(0); let off=0;
  for(const c of micChunks){ ch.set(c,off); off+=c.length; }
  state.pads.push({name:`VOICE ${String(state.pads.length+1).padStart(2,"0")}`, buffer:buf, loop:false});
  micChunks=[]; flashMsg(t("msg.micToPad",{n:state.pads.length,s:(len/AC.sampleRate).toFixed(1)})); if(TEST) TEST.record=true; save();
}
function toggleMicRec(){ micRecording?stopMicRec():startMicRec(); }
function micLevel(){ if(!micAnalyser) return 0; micAnalyser.getByteTimeDomainData(micData); let s=0; for(let i=0;i<micData.length;i++){const v=(micData[i]-128)/128; s+=v*v;} return Math.sqrt(s/micData.length); }
async function beatboxToSteps(){
  if(!state.mic.on){ await micToggle(); if(!state.mic.on) return; }
  if(state.mic.beat){ return; }
  state.mic.beat=true; beatHits=[]; $("btnBeatbox").classList.add("on"); flashMsg(t("msg.beatbox"));
  const t0=performance.now(); let last=0, prev=0, prevPrev=0;
  beatTimer=setInterval(()=>{
    const lvl=micLevel(); const now=performance.now(); const elapsed=(now-t0)/1000;
    const onset = lvl>0.06 && lvl>prev*1.6 && now-last>110;
    if(onset){ beatHits.push({t:elapsed, vel:Math.min(1,lvl*3)}); last=now; }
    prevPrev=prev; prev=lvl;
    if(elapsed>=4){ clearInterval(beatTimer); beatTimer=null; state.mic.beat=false; $("btnBeatbox").classList.remove("on");
      // заполнить шаги выбранной партии по найденным ударам (квантизация 1/16)
      const part=state.parts[state.selPart]; part.steps.forEach(st=>{ st.on=false; st.accent=false; });
      let n=0;
      beatHits.slice(0,16).forEach(h=>{ const step=Math.min(15,Math.floor((h.t/4)*16)); part.steps[step].on=true; if(h.vel>0.5){part.steps[step].accent=true;} n++; });
      paintKnobs(); save(); flashMsg(t("msg.beatboxDone",{n:n,p:state.selPart+1}));
    }
  },20);
}

/* ---------- запись выхода (ресемплинг) ---------- */
function toggleRec(){ audioInit(); if (AC.state==="suspended") AC.resume(); if(state.recording){ finishRec(); } else { recChunks=[]; state.recording=true; state.recStarted=AC.currentTime; flashMsg(t("msg.rec")); } }
function finishRec(){
  if(!state.recording) return;
  state.recording=false;
  let len=0; for(const c of recChunks) len+=c[0].length;
  if(len<2048){ flashMsg(t("msg.recShort")); return; }
  const buf=AC.createBuffer(2, len, AC.sampleRate);
  const L=buf.getChannelData(0), R=buf.getChannelData(1);
  let off=0; for(const [l,r] of recChunks){ L.set(l,off); R.set(r,off); off+=l.length; }
  const n=state.pads.length+1;
  state.pads.push({name:`REC ${String(n).padStart(2,"0")}`, buffer:buf, loop:false}); if(TEST) TEST.record=true;
  recChunks=[];
  flashMsg(t("msg.recToPad",{n:state.pads.length,s:(len/AC.sampleRate).toFixed(1)}));
  save();
}
function playPad(i){
  const pad=state.pads[i]; if(!pad||!AC) return;
  const src=AC.createBufferSource(); src.buffer=pad.buffer; src.loop=!!pad.loop;
  const g=AC.createGain(); g.gain.value=0.9;
  src.connect(g); g.connect(master); src.start();
  pad._src=src;
}
function stopAllPads(){ state.pads.forEach(p=>{ try{ p._src && p._src.stop(); }catch(e){} p._src=null; }); }

/* ---------- генеративные функции ---------- */
function rng(seed){ let x=(seed||1)>>>0; return ()=>{ x^=x<<13; x>>>=0; x^=x>>17; x<<=5; x>>>=0; return (x>>>0)/4294967296; }; }
function genParams(part){ return part.pages[4]; }
function applyScale(part, midi){
  const sp=genParams(part), si=Math.round(sp[3]);
  if(si<=0) return midi;
  const sc=NOTE_SCALES[Math.min(si,NOTE_SCALES.length-1)];
  const rel=midi-part.root; if(rel<0) return midi;
  const oct=Math.floor(rel/12), deg=rel%12;
  let best=sc[0]; for(const d of sc){ if(Math.abs(d-deg)<Math.abs(best-deg)) best=d; }
  return part.root+oct*12+best;
}
function mutateNote(part, step, note){
  const sp=genParams(part), amt=Math.round(sp[2]); if(amt<=0) return note;
  const r=rng((state.seed||1)+part.root*7+step*131);
  const off=Math.round((r()*2-1)*amt/3);
  return note+off;
}
function euclidPattern(density){
  const n=16, k=Math.max(0,Math.min(16,Math.round(density)));
  if(k===0) return new Array(n).fill(false);
  if(k===n) return new Array(n).fill(true);
  // алгоритм Бьорклунда: ближайшее распределение
  const pat=[]; for(let i=0;i<n;i++) pat.push(Math.floor((i*k)/n)!==Math.floor(((i+1)*k)/n));
  return pat;
}
function regenerateEuclid(part){
  const sp=genParams(part), density=Math.round(sp[1]);
  const pat=euclidPattern(density);
  part.steps.forEach((st,i)=>{ st.on=pat[i]; st.accent=pat[i]&&i%4===0; });
}
function evolvePart(part){
  const r=rng((state.seed||1)+Math.floor(Date.now()/4000));
  part.steps.forEach(st=>{ if(st.on && r()<0.5) st.note=clamp(st.note+Math.round((r()*2-1)*3),-12,24); });
  flashMsg(t("msg.evolve"));
}

/* ---------- sequencer ---------- */
let seqTimer=null, nextStepTime=0, lookahead=0.1;
const stepDur=()=>60/state.bpm/4;
let midiClockTimer=null;
function startMidiClock(){ if(!midiOut||midiClockTimer) return; try{ midiOut.send([0xFA]); }catch(e){} midiClockTimer=setInterval(()=>{ if(!state.playing) return; try{ midiOut.send([0xF8]); }catch(e){} }, 60000/state.bpm/24); }
function stopMidiClock(){ if(midiClockTimer){ clearInterval(midiClockTimer); midiClockTimer=null; } if(midiOut){ try{ midiOut.send([0xFC]); }catch(e){} } }
function startSeq(){ if(TEST) TEST.sound=true; audioInit(); startMidiClock(); if(midiOut){ state.extTracks.forEach(t=>{ try{ midiOut.send([0xC0|((t.ch-1)&0xF), t.prog&0x7F]); }catch(e){} }); } if(AC.state==="suspended")AC.resume(); state.playing=true; nextStepTime=AC.currentTime+0.05; state.step=0; if(seqTimer)clearInterval(seqTimer); seqTimer=setInterval(scheduler,25); save(); }
function stopSeq(){ state.playing=false; stopMidiClock(); if(seqTimer){clearInterval(seqTimer);seqTimer=null;} voices.forEach(v=>killVoice(v,0.08)); save(); }
function scheduler(){ if(!state.playing) return; while(nextStepTime<AC.currentTime+lookahead){ scheduleStep(state.step,nextStepTime); nextStepTime+=stepDur(); state.step=(state.step+1)%16; } }
function scheduleStep(step,when){
  // внешние MIDI-треки
  if(midiOut){
    state.extTracks.forEach((t,ti)=>{
      const st=t.steps[step]; if(!st.on) return;
      try{ midiOut.send([0xB0|((t.ch-1)&0xF), t.ccNum&0x7F, st.cc&0x7F]); }catch(e){}
      try{ midiOut.send([0x90|((t.ch-1)&0xF), clamp(t.root??60,0,127), clamp(st.vel,0,127)]); }catch(e){}
      setTimeout(()=>{ try{ midiOut.send([0x80|((t.ch-1)&0xF), clamp(t.root??60,0,127), 0]); }catch(e){} }, Math.max(30,(60/state.bpm/4)*500));
    });
  }
  for (const part of state.parts){
    if(!part.active||part.mute) continue;
    const s=part.steps[step]; if(!s.on) continue;
    const gp=genParams(part);
    if(Math.random()*100 > gp[0]) continue;                 // PROB
    let n=mutateNote(part, step, s.note);                    // MUTATE
    n=applyScale(part, part.root+n)-part.root;               // SCALE
    if(Math.round(gp[6])>0 && step===0 && state.playing){ }  // EVOLVE по бару — ниже
    const dt=Math.max(0,(when-AC.currentTime)*1000);
    setTimeout(()=>{ noteOn(part.root+n, s.accent?1:0.65, part); },dt);
    if(Math.round(gp[6])>0 && step===15){ setTimeout(()=>evolvePart(part), dt+30); }
  }
}

/* ---------- MIDI ---------- */
let midiAccess=null, midiOut=null;
let midiInfo={names:"", out:false, err:false};
function renderMidiState(){
  const el=$("midiState"); if(!el) return;
  if(midiInfo.err){ el.textContent=t("midi.noAccess"); return; }
  const base=midiInfo.names?t("midi.list",{names:midiInfo.names}):t("midi.noInputs");
  el.textContent=base+(midiInfo.out?t("midi.outOk"):"");
}
function sendCC(cc,val){ if(midiOut){ try{ midiOut.send([0xB0,cc,clamp(Math.round(val),0,127)]); }catch(e){} } }
function midiInit(){
  if(!navigator.requestMIDIAccess){ renderMidiState(); return; }
  navigator.requestMIDIAccess({sysex:false}).then((access)=>{
    midiAccess=access;
    const bind=()=>{
      const inputs=[...access.inputs.values()], outputs=[...access.outputs.values()];
      midiOut=outputs[0]||null;
      midiInfo={names:inputs.map(i=>i.name).join(", ").slice(0,26), out:!!midiOut, err:false};
      renderMidiState();
      inputs.forEach(input=>{ input.onmidimessage=onMidi; });
    };
    bind(); access.onstatechange=bind;
  }).catch(()=>{ midiInfo={names:"", out:false, err:true}; renderMidiState(); });
}
function onMidi(msg){
  const [st,d1,d2]=msg.data, cmd=st&0xf0;
  if(cmd===0x90&&d2>0){ noteOn(d1,d2/127); markKey(d1,true); }
  else if(cmd===0x80||(cmd===0x90&&d2===0)){ noteOff(d1); markKey(d1,false); }
  else if(cmd===0xB0){ // CC из внешнего мира двигает текущую страницу
    const idx=CC_BASE[state.page].indexOf(d1);
    if(idx>=0){ const p=pval(); p[idx]=pmin(state.page,idx)+(d2/127)*(pmax(state.page,idx)-pmin(state.page,idx)); paintKnobs(); }
  }
}

/* ---------- keyboard ---------- */
const QWERTY=["KeyA","KeyW","KeyS","KeyE","KeyD","KeyF","KeyT","KeyG","KeyY","KeyH","KeyU","KeyJ","KeyK","KeyO","KeyL","KeyP","Semicolon"];
const pressed=new Map(), keyEls=new Map();
function buildKeys(){
  // Два кластера 3×7 = 42 клавиши, как на реальной панели Lapka-42: левый −18°, правый +18°.
  const CLUSTERS = {
    keysLeft:  { rot:-18, base:48, rows:[["Й","Ц","У","К","Е","Н","Г"],["Ф","Ы","В","А","П","Р","О"],["Я","Ч","С","М","И","Т","Ь"]] },
    keysRight: { rot:18,  base:69, rows:[["Ш","Щ","З","Х","Ъ","Ж","Э"],["Л","Д","Ж","Э","Ю","Б","⇧"],["Ё",",",".","/","⏎","⏫","⌫"]] },
  };
  for (const side of ["keysLeft","keysRight"]){
    const cfg=CLUSTERS[side], host=$(side);
    host.innerHTML=""; host.className="cluster"+(side==="keysRight"?" right":" left");
    host.style.setProperty("--rot",cfg.rot+"deg");
    let idx=0;
    cfg.rows.forEach((row,ri)=>{
      const r=document.createElement("div"); r.className="krow";
      row.forEach((label,ci)=>{
        const midi=cfg.base+idx; idx++;
        const b=document.createElement("button"); b.className="glabel";
        b.innerHTML=`<b>${label}</b><i>${noteName(midi)}</i>`;
        b.dataset.midi=midi;
        const ka=t("a11y.key",{l:label,note:noteName(midi)}); b.setAttribute("aria-label",ka); b.title=ka;
        bindKey(b,midi); r.appendChild(b); keyEls.set(midi,b);
      });
      host.appendChild(r);
    });
  }
}
function bindKey(b,midi){
  b.setAttribute("aria-pressed","false");
  b.addEventListener("pointerdown",(e)=>{e.preventDefault();noteOn(midi,0.85);markKey(midi,true);b.setPointerCapture(e.pointerId);});
  b.addEventListener("pointerup",()=>{noteOff(midi);markKey(midi,false);});
  b.addEventListener("pointerleave",()=>{noteOff(midi);markKey(midi,false);});
  b.addEventListener("keydown",(e)=>{ if(e.key==="Enter"||e.key===" "){ e.preventDefault(); e.stopPropagation(); noteOn(midi,0.85); markKey(midi,true); } });
  b.addEventListener("keyup",(e)=>{ if(e.key==="Enter"||e.key===" "){ e.preventDefault(); e.stopPropagation(); noteOff(midi); markKey(midi,false); } });
}
const noteName=(m)=>{const n=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"];return n[m%12]+(Math.floor(m/12)-1);};
function markKey(midi,on){ const el=keyEls.get(midi); if(el){ el.classList.toggle("on",on); el.setAttribute("aria-pressed",on?"true":"false"); } }
addEventListener("keydown",(e)=>{
  if(e.repeat) return;
  const n=QWERTY.indexOf(e.code);
  if(n>=0 && !e.metaKey && !e.ctrlKey){ const midi=48+n; noteOn(midi,0.8); pressed.set(e.code,midi); markKey(midi,true); e.preventDefault(); }
  if(e.code==="Space"){ state.playing?stopSeq():startSeq(); e.preventDefault(); }
  if(e.code==="KeyR" && !e.metaKey && !e.ctrlKey){ toggleRec(); e.preventDefault(); }
  if(["Digit1","Digit2","Digit3","Digit4"].includes(e.code)){ if(state.mode===4){ state.extSel=+e.code.slice(-1)-1; paintKnobs(); save(); } else playPad(+e.code.slice(-1)-1); e.preventDefault(); }
  if(state.mode===4 && ["Digit5","Digit6","Digit7","Digit8"].includes(e.code)){ state.extSel=+e.code.slice(-1)-1; paintKnobs(); save(); e.preventDefault(); }
  if(e.code==="KeyM" && !e.metaKey && !e.ctrlKey){ state.modOn=!state.modOn; save(); flashMsg(state.modOn?t("msg.modOn"):t("msg.modOff")); e.preventDefault(); }
  if(e.code==="Home" && !e.metaKey && !e.ctrlKey){ goHome(); e.preventDefault(); }
  if(e.code==="PageUp"){ state.page=(state.page+4)%5; paintKnobs(); syncPageChips(); if(state.page===2&&TEST)TEST.env=true; e.preventDefault(); }
  if(e.code==="PageDown"){ state.page=(state.page+1)%5; paintKnobs(); syncPageChips(); if(state.page===2&&TEST)TEST.env=true; e.preventDefault(); }
  if((e.metaKey||e.ctrlKey) && e.code==="KeyZ"){ undo(); if(TEST && TEST.chgMutate) TEST.mutundo=true; e.preventDefault(); }
  if((e.metaKey||e.ctrlKey) && e.code==="KeyC"){ copyPattern(); e.preventDefault(); }
  if((e.metaKey||e.ctrlKey) && e.code==="KeyV"){ pastePattern(); e.preventDefault(); }
});
addEventListener("keyup",(e)=>{ const n=pressed.get(e.code); if(n!=null){noteOff(n);markKey(n,false);pressed.delete(e.code);} });

/* ---------- knobs/faders/jacks ---------- */
const knobEls=[], macroEls=[];
const MACRO = [
  { key:"cut",  get:()=>state.parts[state.selPart].pages[0][0], set:(v)=>state.parts[state.selPart].pages[0][0]=v, min:80, max:12000 },
  { key:"res",  get:()=>state.parts[state.selPart].pages[0][1], set:(v)=>state.parts[state.selPart].pages[0][1]=v, min:0, max:100 },
  { key:"atk",  get:()=>state.parts[state.selPart].pages[2][0], set:(v)=>state.parts[state.selPart].pages[2][0]=v, min:1, max:2000 },
  { key:"rel",  get:()=>state.parts[state.selPart].pages[2][3], set:(v)=>state.parts[state.selPart].pages[2][3]=v, min:20, max:3000 },
  { key:"dly",  get:()=>state.parts[state.selPart].pages[3][0], set:(v)=>state.parts[state.selPart].pages[3][0]=v, min:0, max:100 },
  { key:"drv",  get:()=>state.parts[state.selPart].pages[0][3], set:(v)=>state.parts[state.selPart].pages[0][3]=v, min:0, max:100 },
  { key:"crsh", get:()=>state.parts[state.selPart].pages[3][4], set:(v)=>state.parts[state.selPart].pages[3][4]=v, min:0, max:100 },
  { key:"mst",  get:()=>state.volume*100, set:(v)=>{ state.volume=v/100; if(master) master.gain.value=state.volume; }, min:0, max:100 },
];
const LETTERS_L=["А","Б","В","Г","Д","Е","Ж","З"], LETTERS_R=["И","Й","К","Л","М","Н","О","П"];
function knobA11y(){
  const page=state.page, ext=state.mode===4;
  knobEls.forEach((k,i)=>{
    const w=k.parentElement, letter=w.dataset.letter||"";
    const lab=t(ext?EXT_PARAM_KEYS[i]:PAGE_PARAM_KEYS[page][i]);
    const v=ext?extVal(i):pval()[i], min=ext?EXT_MIN[i]:pmin(page,i), max=ext?EXT_MAX[i]:pmax(page,i);
    const s=t("a11y.knob",{l:letter,label:lab});
    k.setAttribute("aria-label",s); k.title=s;
    k.setAttribute("aria-valuemin",String(min)); k.setAttribute("aria-valuemax",String(max));
    k.setAttribute("aria-valuenow",String(Math.round(v)));
    k.setAttribute("aria-valuetext",lab+" "+(ext?String(Math.round(v)):fmtParam(page,i,v)));
  });
  macroEls.forEach((k,i)=>{
    const m=MACRO[i], letter=(k.parentElement.dataset.letter||"");
    const s=t("a11y.knob",{l:letter,label:t("macro."+m.key)});
    k.setAttribute("aria-label",s); k.title=s;
    k.setAttribute("aria-valuemin",String(m.min)); k.setAttribute("aria-valuemax",String(m.max));
    k.setAttribute("aria-valuenow",String(Math.round(m.get())));
    k.setAttribute("aria-valuetext",t("macro."+m.key)+" "+Math.round(m.get()));
  });
}
function makeKnob(host, i, opts){
  const wrap=document.createElement("div"); wrap.className="k";
  const k=document.createElement("div"); k.className="knob"; k.dataset.i=i;
  k.tabIndex=0; k.setAttribute("role","slider");
  const label=document.createElement("span"); label.textContent="—";
  wrap.appendChild(k); wrap.appendChild(label); host.appendChild(wrap);
  let startY=null,startVal=0,keySnap=false;
  const lo=()=>typeof opts.min==="function"?opts.min():opts.min;
  const hi=()=>typeof opts.max==="function"?opts.max():opts.max;
  const stepSize=()=>typeof opts.step==="function"?opts.step():(opts.step!=null?opts.step:(hi()-lo())/100);
  const bigSize=()=>typeof opts.step==="function"||opts.step!=null?stepSize()*10:(hi()-lo())/10;
  const commit=(val)=>{ opts.set(clamp(val,lo(),hi())); paintKnobs(); save(); if(opts.onChange) opts.onChange(); };
  const beginKey=()=>{ if(!keySnap){ snapshot(); keySnap=true; } };
  const down=(e)=>{ e.preventDefault(); audioInit(); snapshot(); startY=e.clientY; startVal=opts.get(); k.setPointerCapture(e.pointerId); };
  const move=(e)=>{ if(startY==null) return; const range=hi()-lo(); const val=clamp(startVal+(startY-e.clientY)/120*range,lo(),hi());
    opts.set(val); paintKnobs(); save(); if(opts.onChange) opts.onChange(); };
  const up=()=>{ startY=null; };
  k.addEventListener("pointerdown",down); k.addEventListener("pointermove",move); k.addEventListener("pointerup",up); k.addEventListener("pointercancel",up);
  k.addEventListener("keydown",(e)=>{
    const step=stepSize();
    if(e.key==="ArrowUp"||e.key==="ArrowRight"){ e.preventDefault(); e.stopPropagation(); beginKey(); commit(opts.get()+step*(e.shiftKey?10:1)); }
    else if(e.key==="ArrowDown"||e.key==="ArrowLeft"){ e.preventDefault(); e.stopPropagation(); beginKey(); commit(opts.get()-step*(e.shiftKey?10:1)); }
    else if(e.key==="PageUp"){ e.preventDefault(); e.stopPropagation(); beginKey(); commit(opts.get()+bigSize()); }
    else if(e.key==="PageDown"){ e.preventDefault(); e.stopPropagation(); beginKey(); commit(opts.get()-bigSize()); }
    else if(e.key==="Home"){ e.preventDefault(); e.stopPropagation(); beginKey(); commit(lo()); }
    else if(e.key==="End"){ e.preventDefault(); e.stopPropagation(); beginKey(); commit(hi()); }
  });
  k.addEventListener("keyup",()=>{ keySnap=false; });
  k.addEventListener("blur",()=>{ keySnap=false; });
  return k;
}
function buildKnobs(){
  const host=$("knobs"); host.innerHTML=""; knobEls.length=0;
  for(let i=0;i<8;i++){
    const k=makeKnob(host,i,{
      // в режиме EXT левые 8 энкодеров управляют полями выбранного внешнего трека,
      // на остальных экранах — параметрами текущей страницы (диапазоны EXT_MIN/MAX).
      get:()=>state.mode===4?extVal(i):pval()[i],
      set:(v)=>{
        if(state.mode===4){ extSet(i,v); paintKnobs(); save(); return; }
        pval()[i]=v; if(state.page===3) applyFx();
        if(state.page===4){
          if(i===1){ regenerateEuclid(state.parts[state.selPart]); if(TEST) TEST.euclid=true; }
          if(i===2 && TEST) TEST.chgMutate=true;
          if(i===7) state.seed=Math.round(v);
        }
        if(TEST && state.page===2) TEST.env=true;
        try{ sendCC((CC_BASE[state.page]&&CC_BASE[state.page][i]!=null)?CC_BASE[state.page][i]:74+i, (v-pmin(state.page,i))/(pmax(state.page,i)-pmin(state.page,i))*127); }catch(e){}
      },
      min:()=>state.mode===4?EXT_MIN[i]:pmin(state.page,i),
      max:()=>state.mode===4?EXT_MAX[i]:pmax(state.page,i),
      step:()=>state.mode===4?1:(pmax(state.page,i)-pmin(state.page,i))/100,
      onChange:null
    });
    k.parentElement.dataset.letter=LETTERS_L[i];
    knobEls.push(k);
  }
  const host2=$("knobsMacro"); if(host2){ host2.innerHTML=""; macroEls.length=0;
    for(let i=0;i<8;i++){
      const m=MACRO[i];
      const k=makeKnob(host2,i,{ get:()=>m.get(), set:(v)=>{ m.set(v); if(m.key==="dly"&&AC) delayGain.gain.value=clamp(m.get()/100,0,1); }, min:m.min, max:m.max });
      k.parentElement.dataset.letter=LETTERS_R[i];
      macroEls.push(k);
    }
  }
}
function paintKnobs(){
  const p=pval(), page=state.page;
  if(state.mode===4){
    knobEls.forEach((k,i)=>{ const v=extVal(i), frac=(v-EXT_MIN[i])/(EXT_MAX[i]-EXT_MIN[i]);
      k.style.setProperty("--a",(frac*260-130).toFixed(1)+"deg");
      const lab=k.parentElement.querySelector("span"); if(lab) lab.textContent=(k.parentElement.dataset.letter?k.parentElement.dataset.letter+" · ":"")+t(EXT_PARAM_KEYS[i]);
    });
    macroEls.forEach((k,i)=>{ const m=MACRO[i], frac=(m.get()-m.min)/(m.max-m.min); k.style.setProperty("--a",(frac*260-130).toFixed(1)+"deg"); const lab=k.parentElement.querySelector("span"); if(lab) lab.textContent=(k.parentElement.dataset.letter?k.parentElement.dataset.letter+" · ":"")+t("macro."+m.key); });
    knobA11y(); return;
  }
  knobEls.forEach((k,i)=>{
    const frac=(p[i]-pmin(page,i))/(pmax(page,i)-pmin(page,i));
    k.style.setProperty("--a",(frac*260-130).toFixed(1)+"deg");
    const lab=k.parentElement.querySelector("span");
    if(lab) lab.textContent=(k.parentElement.dataset.letter?k.parentElement.dataset.letter+" · ":"") + (PAGE_PARAM_KEYS[page][i]?t(PAGE_PARAM_KEYS[page][i]):"");
  });
  macroEls.forEach((k,i)=>{
    const m=MACRO[i], frac=(m.get()-m.min)/(m.max-m.min);
    k.style.setProperty("--a",(frac*260-130).toFixed(1)+"deg");
    const lab=k.parentElement.querySelector("span");
    if(lab) lab.textContent=(k.parentElement.dataset.letter?k.parentElement.dataset.letter+" · ":"") + t("macro."+m.key);
  });
  knobA11y();
}
function applyFx(){
  const p=state.parts[state.selPart].pages[3];
  if(!AC) return;
  delay.delayTime.value=clamp(p[2]/1000,0.02,1);
}
/* ---------- фейдеры: режимы ---------- */
function sceneTargets(){ return state.parts[state.selPart]; }
function applyScene(x){
  const part=state.parts[state.selPart];
  const A=part.sceneA, B=part.sceneB; if(!A||!B) return;
  const p0=part.pages[0], p2=part.pages[2], p1=part.pages[1];
  const keys=[["p0",0],["p0",1],["p0",3],["p2",0],["p2",1],["p2",3],["p1",1],["p1",5]];
  const valsA=[A.cut,A.res,A.drive,A.atk,A.dec,A.rel,A.depth,A.fbk];
  const valsB=[B.cut,B.res,B.drive,B.atk,B.dec,B.rel,B.depth,B.fbk];
  keys.forEach(([page,idx],k)=>{ const v=valsA[k]+(valsB[k]-valsA[k])*x; if(page==="p0")p0[idx]=v; else if(page==="p2")p2[idx]=v; else p1[idx]=v; });
  part.sceneX=x; paintKnobs(); save();
}
function ensureScenes(part){
  if(!part.sceneA){
    const p0=part.pages[0];
    part.sceneA={cut:p0[0],res:p0[1],drive:p0[3],atk:part.pages[2][0],dec:part.pages[2][1],rel:part.pages[2][3],depth:part.pages[1][1],fbk:part.pages[3][1]};
    part.sceneB={cut:Math.min(12000,p0[0]*2.2),res:Math.min(100,p0[1]+35),drive:Math.min(100,p0[3]+30),atk:Math.max(2,part.pages[2][0]*0.5),dec:Math.max(30,part.pages[2][1]*0.7),rel:Math.max(40,part.pages[2][3]*0.7),depth:Math.min(100,part.pages[1][1]+30),fbk:Math.min(100,part.pages[3][1]+25)};
  }
}
function setFaderMode(m){ if(TEST && m==="SCENE") TEST.scene=true;
  state.faderMode=m;
  document.querySelectorAll("[data-fmode]").forEach(b=>{ const on=b.dataset.fmode===m; b.classList.toggle("active",on); b.setAttribute("aria-pressed",on?"true":"false"); });
  paintFaderLabels(); save(); flashMsg(t("msg.faders",{m:m}));
}
function paintFaderLabels(){
  const f0=document.querySelector('[data-fader="0"] span'), f1=document.querySelector('[data-fader="1"] span');
  const L={TRACK:[t("fader.partLevel"),t("fader.master")],SCENE:[t("fader.sceneAB"),t("fader.master")],DJ:[t("fader.deckA"),t("fader.deckB")]}[state.faderMode]||[t("fader.f1"),t("fader.f2")];
  if(f0) f0.textContent=L[0]; if(f1) f1.textContent=L[1];
  document.querySelectorAll(".fader").forEach(f=>{ const n=+f.dataset.fader+1, isF=f.dataset.fader==="0", s=t("a11y.fader",{n:n,label:(isF?L[0]:L[1])}); f.setAttribute("aria-label",s); f.title=s;
    let v;
    if(state.faderMode==="TRACK") v=isF?state.parts[state.selPart].level:state.volume;
    else if(state.faderMode==="SCENE") v=isF?(state.parts[state.selPart].sceneX||0):state.volume;
    else if(state.faderMode==="DJ") v=isF?state.parts[0].level:state.parts[2].level;
    else v=state.volume;
    f.setAttribute("aria-valuenow",String(Math.round(clamp(v,0,1)*100)));
  });
}
function buildFaders(){
  document.querySelectorAll(".fader").forEach(f=>{
    let startY=null,startVal=0;
    f.tabIndex=0; f.setAttribute("role","slider"); f.setAttribute("aria-valuemin","0"); f.setAttribute("aria-valuemax","100");
    const currentVal=()=>{
      if(state.faderMode==="TRACK") return f.dataset.fader==="0"?state.parts[state.selPart].level:state.volume;
      if(state.faderMode==="SCENE") return f.dataset.fader==="0"?state.parts[state.selPart].sceneX||0:state.volume;
      if(state.faderMode==="DJ") return f.dataset.fader==="0"?state.parts[0].level:state.parts[2].level;
      return state.volume;
    };
    const applyVal=(val,isShift)=>{
      const v=clamp(val,0,1);
      if(isShift){ state.volume=v; if(master)master.gain.value=v; }
      else if(state.faderMode==="TRACK"){ if(f.dataset.fader==="0"){state.parts[state.selPart].level=v;} else {state.volume=v; if(master)master.gain.value=v;} }
      else if(state.faderMode==="SCENE"){ if(f.dataset.fader==="0"){ ensureScenes(state.parts[state.selPart]); applyScene(v); } else {state.volume=v; if(master)master.gain.value=v;} }
      else if(state.faderMode==="DJ"){ if(f.dataset.fader==="0"){ state.parts[0].level=v; state.parts[1].level=v; } else { state.parts[2].level=v; state.parts[3].level=v; } }
      f.style.setProperty("--top",((1-v)*100).toFixed(1)+"%");
      f.setAttribute("aria-valuenow",String(Math.round(currentVal()*100)));
      paintFaderLabels(); save();
    };
    const down=(e)=>{e.preventDefault();audioInit();startY=e.clientY;startVal=currentVal();if(state.faderMode==="SCENE")ensureScenes(state.parts[state.selPart]);f.setPointerCapture(e.pointerId);};
    const move=(e)=>{ if(startY==null)return; const dy=startY-e.clientY, val=clamp(startVal+dy/140,0,1); applyVal(val,e.shiftKey); };
    const up=()=>{startY=null;};
    f.addEventListener("pointerdown",down);f.addEventListener("pointermove",move);f.addEventListener("pointerup",up);f.addEventListener("pointercancel",up);
    f.addEventListener("keydown",(e)=>{
      let d=0;
      if(e.key==="ArrowUp"||e.key==="ArrowRight") d=0.02;
      else if(e.key==="ArrowDown"||e.key==="ArrowLeft") d=-0.02;
      else if(e.key==="PageUp") d=0.1;
      else if(e.key==="PageDown") d=-0.1;
      else if(e.key==="Home"){ e.preventDefault(); e.stopPropagation(); applyVal(0,false); return; }
      else if(e.key==="End"){ e.preventDefault(); e.stopPropagation(); applyVal(1,false); return; }
      else return;
      e.preventDefault(); e.stopPropagation(); applyVal(currentVal()+d*(e.shiftKey?5:1),false);
    });
    applyVal(f.dataset.fader==="0"?state.volume:state.delayMix,false);
  });
}
function buildJacks(){
  const host=$("jacks"); host.innerHTML="";
  JACKS.forEach((name,i)=>{
    const d=document.createElement("div"); d.className="jack"; d.dataset.i=i;
    d.tabIndex=0; d.setAttribute("role","button"); d.setAttribute("aria-pressed","false");
    d.innerHTML=`<i></i><span>${name}</span>`;
    const lbl=t("a11y.jack",{n:i+1,name:name}); d.setAttribute("aria-label",lbl); d.title=lbl;
    const toggle=()=>{ state.cables.has(i)?state.cables.delete(i):state.cables.add(i); const on=state.cables.has(i); d.classList.toggle("active",on); d.setAttribute("aria-pressed",on?"true":"false"); };
    d.addEventListener("click",toggle);
    d.addEventListener("keydown",(e)=>{ if(e.key==="Enter"||e.key===" "){ e.preventDefault(); e.stopPropagation(); toggle(); } });
    host.appendChild(d);
  });
}

/* ---------- pattern copy/paste ---------- */
let clipboard=null;
function copyPattern(){ clipboard=JSON.stringify(state.parts); flashMsg(t("msg.patternCopied")); }
function pastePattern(){ if(!clipboard) return; snapshot(); state.parts=JSON.parse(clipboard); paintKnobs(); save(); flashMsg(t("msg.patternPasted")); }
let msg="", msgT=0, lastPadClick=null, lastCtx=0;
function flashMsg(txt){ msg=txt; msgT=Date.now(); const live=$("live"); if(live) live.textContent=txt; }

/* ---------- доп. фишки ---------- */
function randomizePattern(){ snapshot();
  state.parts.forEach((p,pi)=>{ p.steps.forEach((st,si)=>{ const r=Math.random(); st.on=r<0.35; st.accent=st.on&&si%4===0; st.note=SCALES[pi][Math.floor(Math.random()*SCALES[pi].length)]; }); });
  paintKnobs(); save(); flashMsg(t("msg.random"));
}
function transpose(semi){ snapshot(); state.parts.forEach(p=>{ p.steps.forEach(st=>{ st.note=clamp(st.note+semi,-24,48); }); }); save(); flashMsg(t("msg.transpose",{n:semi})); }

/* ---------- пресеты и A/B ---------- */
function loadPresets(){ try{ return JSON.parse(localStorage.getItem("bukifon-presets-v1")||"[]"); }catch(e){ return []; } }
function storePresets(list){ try{ localStorage.setItem("bukifon-presets-v1", JSON.stringify(list)); }catch(e){} }
function savePresetTo(slot){ const list=loadPresets(); list[slot]={parts:JSON.parse(JSON.stringify(state.parts)),page:state.page,theme:state.theme,at:Date.now()}; storePresets(list); flashMsg(t("msg.presetSaved",{n:slot})); }
function loadPresetFrom(slot){ const list=loadPresets(); const p=list[slot]; if(!p) { flashMsg(t("msg.presetEmpty",{n:slot})); return; } snapshot(); state.parts=p.parts; state.page=p.page??0; if(p.theme) setTheme(p.theme); paintKnobs(); save(); flashMsg(t("msg.presetLoaded",{n:slot})); }
let abSnapshot=null;
function toggleAB(){ if(!abSnapshot){ abSnapshot=JSON.stringify(state.parts); flashMsg(t("msg.abSaved")); } else { const cur=JSON.stringify(state.parts); state.parts=JSON.parse(abSnapshot); abSnapshot=cur; paintKnobs(); save(); flashMsg(t("msg.abToggled")); } }

/* ---------- themes ---------- */
function setTheme(name){ if(!THEMES[name]) return; state.theme=name; T=THEMES[name]; document.documentElement.style.setProperty("--accent",T.accent); save(); }
function drawThemeSwatches(){
  const names=Object.keys(THEMES);
  names.forEach((n,i)=>{
    const x=700-i*0, y=0; // swatches рисуются внизу справа
  });
}

/* ---------- контекст: панель, страницы, HOME, overlay ---------- */
function renderContextBar(){
  const el=$("contextbar"); if(!el) return;
  const sel=[...state.selParts].map(i=>i+1).join(",")||"-";
  const fm=state.faderMode;
  const f={TRACK:[t("fader.partLevel"),t("fader.master")],SCENE:[t("fader.sceneAB"),t("fader.master")],DJ:[t("fader.deckA"),t("fader.deckB")]}[fm]||[t("fader.f1"),t("fader.f2")];
  const chips=[
    {t:`${t("ctx.part")} <b>${state.selPart+1}</b>`, w:true},
    {t:`${t("ctx.selected")} <b>${sel}</b>`, w:state.selParts.size>1},
    {t:`${t("ctx.page")} <b>${t(PAGES[state.page])}</b>`},
    {t:`${t("ctx.faders")} <b>${fm}</b> (F1 ${f[0]}, F2 ${f[1]})`},
    {t:`${t("ctx.theme")} <b>${themeLabel(state.theme)}</b>`},
    {t:`${t("ctx.rec")} ${state.recording?"●":"○"}`, rec:state.recording},
    {t:`${t("ctx.mic")} ${state.mic.on?t("ctx.on"):t("ctx.off")} ${state.mic.on?("· "+Math.round(state.mic.level*100)):""}`, w:state.mic.on},
    {t:t("ctx.unsaved"), w:true},
  ];
  el.innerHTML=chips.map(c=>`<span class="chip${c.w?" warn":""}${c.rec?" rec":""}">${c.t}</span>`).join("");
}
function buildPageChips(){ if(TEST && state.page===2) TEST.env=true;
  const host=$("pagechips"); if(!host) return; host.innerHTML="";
  PAGES.forEach((pg,i)=>{ const b=document.createElement("button"); b.type="button"; b.textContent=t(pg); b.dataset.page=pg.split(".")[1]; b.className=i===state.page?"active":""; b.setAttribute("aria-pressed",i===state.page?"true":"false"); b.addEventListener("click",()=>{ state.page=i; paintKnobs(); syncPageChips(); if(i===2&&TEST)TEST.env=true; save(); }); host.appendChild(b); });
}
function syncPageChips(){ document.querySelectorAll("#pagechips button").forEach((b,i)=>{ const on=i===state.page; b.classList.toggle("active",on); b.setAttribute("aria-pressed",on?"true":"false"); }); }
function goHome(){ state.page=0; paintKnobs(); syncPageChips(); if(TEST && TEST.leftMain) TEST.home=true; save(); flashMsg(t("msg.home")); }
let shiftOverlay=false;
addEventListener("keydown",(e)=>{ if(e.key==="Shift"){ shiftOverlay=true; } });
addEventListener("keyup",(e)=>{ if(e.key==="Shift"){ shiftOverlay=false; } });

/* ---------- canvas UI ---------- */
function draw(){
  ctx.clearRect(0,0,W,H); ctx.fillStyle=T.bg; ctx.fillRect(0,0,W,H);
  // header
  ctx.fillStyle=T.panel; ctx.fillRect(0,0,W,44);
  ctx.fillStyle=T.accent; ctx.font="700 26px Inter, system-ui, sans-serif"; ctx.fillText(t("app.brand"),14,32);
  MODES.forEach((m,i)=>{
    const x=196+i*104,y=8;
    ctx.fillStyle=i===state.mode?T.accent:T.card; roundRect(x,y,96,22,5); ctx.fill();
    ctx.fillStyle=i===state.mode?"#04140b":T.muted; ctx.font="700 12px Inter"; ctx.textAlign="center"; ctx.fillText(t(m),x+48,y+15); ctx.textAlign="left";
  });
  // info
  const info=[[t("info.bpm"),String(state.bpm)],[t("info.step"),String(state.step).padStart(2,"0")],[t("info.page"),t(PAGES[state.page])],[t("info.theme"),themeLabel(state.theme)]];
  info.forEach(([k,v],i)=>{ ctx.fillStyle=T.muted; ctx.font="600 11px Inter"; ctx.fillText(k,20+i*70,62); ctx.fillStyle=T.text; ctx.font="700 16px Inter"; ctx.fillText(v,20+i*70,80); });
  if(state.playing){ ctx.fillStyle=T.green; ctx.fillRect(300,58,8,8); ctx.fillStyle=T.muted; ctx.font="600 11px Inter"; ctx.fillText(t("btn.play"),312,66); }
  if(state.recording){ const a=0.5+0.5*Math.sin(Date.now()/180); ctx.fillStyle=`rgba(255,92,92,${a.toFixed(2)})`; ctx.beginPath(); ctx.arc(372,62,6,0,Math.PI*2); ctx.fill(); ctx.fillStyle=T.red; ctx.font="700 10px Inter"; ctx.fillText(t("btn.rec"),384,66); }

  if(state.mode===0) drawSynth();
  else if(state.mode===4) drawExt();
  else if(state.mode===1) drawSampler();
  else if(state.mode===2) drawDaw();
  else drawUsbKbd();
  drawStatusBar();
  if(shiftOverlay) drawShiftOverlay();
  if(state.test.active) drawTestOverlay();
  if(Date.now()-lastCtx>400){ lastCtx=Date.now(); renderContextBar(); }
  if(msg && Date.now()-msgT<1600){ ctx.fillStyle=T.accent; ctx.font="700 12px Inter"; ctx.fillText(msg,W-220,462); }
}
function drawShiftOverlay(){
  ctx.fillStyle="rgba(4,10,12,0.92)"; roundRect(60,70,W-120,H-160,10); ctx.fill();
  ctx.strokeStyle=T.accent; ctx.lineWidth=2; roundRect(60,70,W-120,H-160,10); ctx.stroke();
  ctx.fillStyle=T.accent; ctx.font="700 14px Inter"; ctx.fillText(t("overlay.title"),84,100);
  const rows=[
    [t("overlay.r1k"),t("overlay.r1v")],
    [t("overlay.r2k"),t("overlay.r2v")],
    [t("overlay.r3k"),t("overlay.r3v")],
    [t("overlay.r4k"),t("overlay.r4v")],
    [t("overlay.r5k"),t("overlay.r5v")],
    [t("overlay.r6k"),t("overlay.r6v")],
    [t("overlay.r7k"),t("overlay.r7v")],
  ];
  rows.forEach(([k,v],i)=>{ ctx.fillStyle=T.muted; ctx.font="600 11px Inter"; ctx.fillText(k,84,130+i*28); ctx.fillStyle=T.text; ctx.fillText(v,300,130+i*28); });
  ctx.fillStyle=T.muted; ctx.font="600 10px Inter"; ctx.fillText(t("overlay.foot"),84,H-110);
}
function drawStatusBar(){
  const lvl=analyser?analyseLevel():0;
  ctx.fillStyle=T.panel; ctx.fillRect(0,444,W,36);
  ctx.fillStyle=T.muted; ctx.font="600 11px Inter"; ctx.fillText(t("status.master"),14,466);
  ctx.fillStyle=T.line; ctx.fillRect(70,456,220,10);
  ctx.fillStyle=T.green; ctx.fillRect(70,456,220*clamp(lvl,0,1),10);
  ctx.fillStyle=T.muted; ctx.font="600 11px Inter"; ctx.fillText(t("status.faders",{m:state.faderMode}),306,466);
  if(state.mic.on){ state.mic.level=micLevel(); const w=70, x=W-90, y=458; ctx.fillStyle=T.line; ctx.fillRect(x,y,w,8); ctx.fillStyle=state.mic.beat?T.orange:T.accent; ctx.fillRect(x,y,w*clamp(state.mic.level*3,0,1),8); ctx.fillStyle=T.muted; ctx.font="600 9px Inter"; ctx.fillText(t("status.mic"),x+2,y-2); }
}
function drawSynth(){
  // 4 партии × 16 шагов (компактно), затем 16 параметров зеркально ручкам панели:
  // левые 4 колонки = А–З (страница), правые 4 = И–П (макросы).
  const top=96, rowH=56;
  for(let pi=0;pi<4;pi++){
    const part=state.parts[pi], y=top+pi*rowH, color=partColor(pi);
    ctx.fillStyle=T.card; roundRect(8,y,W-16,rowH-6,6); ctx.fill();
    if(state.selParts.has(pi)){ ctx.strokeStyle=T.accent; ctx.lineWidth=1.5; roundRect(8,y,W-16,rowH-6,6); ctx.stroke(); }
    if(pi===state.selPart){ ctx.fillStyle=T.accent; ctx.beginPath(); ctx.arc(W-20,y+14,4,0,Math.PI*2); ctx.fill(); }
    const partTxt=t("synth.part")+" "+(pi+1), suffix=(part.mute?" · "+t("synth.mute"):"")+(part.active?"":" · "+t("synth.off"));
    ctx.fillStyle=color; ctx.font="700 13px Inter"; ctx.fillText(partTxt,16,y+18);
    const partTxtW=ctx.measureText(partTxt).width;
    if(suffix){ ctx.fillStyle=part.mute?T.red:T.muted; ctx.font="600 11px Inter"; ctx.fillText(suffix,16+partTxtW,y+18); }
    ctx.fillStyle=part.mute?T.red:T.muted; ctx.font="600 11px Inter";
    ctx.fillText(part.name,16,y+34);
    ctx.fillStyle=color; ctx.fillRect(16,y+42,60*clamp(part.pages[0][0]/12000,0,1),4);
    for(let s2=0;s2<16;s2++){
      const x=112+s2*42, sy=y+10, sw=38, sh=rowH-30, st=part.steps[s2];
      ctx.fillStyle=state.playing&&state.step===s2?T.line:T.bg; roundRect(x,sy,sw,sh,4); ctx.fill();
      if(st.on){ ctx.fillStyle=st.accent?T.orange:(s2%4===0?color:T.green); roundRect(x+2,sy+2,sw-4,sh-4,3); ctx.fill(); }
      if(state.playing&&state.step===s2){ ctx.strokeStyle=T.accent; ctx.lineWidth=2; roundRect(x-1,sy-1,sw+2,sh+2,5); ctx.stroke(); }
      ctx.fillStyle=T.muted; ctx.font="600 10px Inter"; ctx.fillText(String(s2+1),x+2,sy-2);
    }
  }
  // --- 16 параметров: зеркально 16 ручкам (левые 4 колонки А–З, правые 4 И–П) ---
  const gy=326, cellH=44;
  const cellW=(W-24-16)/8;
  for(let i=0;i<16;i++){
    const row=Math.floor(i/8), col=i%8;
    const x=12+col*cellW, y=gy+row*cellH, w=cellW-6;
    ctx.fillStyle=T.card; roundRect(x,y,w,cellH-6,5); ctx.fill();
    let label, val, frac, letter, isMacro=col>=4;
    if(!isMacro){ const p=pval(); const pi=row*4+col; label=t(PAGE_PARAM_KEYS[state.page][pi]); val=fmtParam(state.page,pi,p[pi]); frac=clamp((p[pi]-pmin(state.page,pi))/(pmax(state.page,pi)-pmin(state.page,pi)),0,1); letter=LETTERS_L[row*4+col]; }
    else { const mi=(row*4)+(col-4); const m=MACRO[mi]; label=t("macro."+m.key); const v=m.get(); val=fmtParam(0, mi<8? [0,1,3,4,5,6,7,2][mi] : 0, v); frac=clamp((v-m.min)/(m.max-m.min),0,1); letter=LETTERS_R[row*4+(col-4)]; }
    ctx.fillStyle=T.muted; ctx.font="600 12px Inter"; ctx.fillText(`${letter} · ${label}`,x+5,y+13);
    ctx.fillStyle=T.text; ctx.font="700 18px Inter"; ctx.fillText(val,x+5,y+32);
    ctx.fillStyle=T.line; ctx.fillRect(x+5,y+cellH-13,w-10,4);
    ctx.fillStyle=T.accent; ctx.fillRect(x+5,y+cellH-13,(w-10)*frac,4);
  }
  // разделитель «страница | макросы»
  ctx.fillStyle=T.line; ctx.fillRect(12+4*cellW-3,gy-2,2,cellH*2-8);
  ctx.fillStyle=T.muted; ctx.font="600 9px Inter"; ctx.fillText(t("col.page"),12+cellW*1.1,gy-5); ctx.fillText(t("col.macros"),12+cellW*4.6,gy-5);
  // табы страниц
  PAGES.forEach((pg,i)=>{
    const x=12+i*84,y=412;
    ctx.fillStyle=i===state.page?T.accent:T.line; roundRect(x,y,78,20,4); ctx.fill();
    ctx.fillStyle=i===state.page?"#04140b":T.muted; ctx.font="700 12px Inter"; ctx.textAlign="center"; ctx.fillText(t(pg),x+39,y+15); ctx.textAlign="left";
  });
  // темы — кружки в шапке
  Object.keys(THEMES).forEach((n,i)=>{
    const x=W-74+i*18, y=22;
    ctx.beginPath(); ctx.arc(x,y,7,0,Math.PI*2); ctx.fillStyle=THEMES[n].bg; ctx.fill();
    ctx.strokeStyle=n===state.theme?T.accent:T.line; ctx.lineWidth=n===state.theme?2:1; ctx.stroke();
  });
}
function fmtParam(page,i,v){
  if(state.page===0&&i===0) return v>=1000?(v/1000).toFixed(1)+" "+t("unit.khz"):Math.round(v)+" "+t("unit.hz");
  if((state.page===0&&(i===4||i===5||i===7))||(state.page===2&&(i===0||i===1||i===3))) return Math.round(v)+" "+t("unit.ms");
  if(state.page===3&&i===2) return Math.round(v)+" "+t("unit.ms");
  if(state.page===3&&i===0) return Math.round(v)+"%";
  return String(Math.round(v));
}
function drawExt(){
  ctx.fillStyle=T.accent; ctx.font="700 17px Inter"; ctx.fillText(t("ext.title"),16,104);
  ctx.fillStyle=T.muted; ctx.font="600 11px Inter"; ctx.fillText(state.extClock?t("ext.clockOut"):t("ext.clockOff"),16,120);
  const top=132,rowH=23;
  for(let ti=0;ti<8;ti++){
    const tt=state.extTracks[ti], y=top+ti*rowH;
    const sel=ti===state.extSel;
    ctx.fillStyle=sel?T.card:T.bg; roundRect(8,y,W-16,rowH-3,4); ctx.fill();
    if(sel){ ctx.strokeStyle=T.accent; ctx.lineWidth=1.5; roundRect(8,y,W-16,rowH-3,4); ctx.stroke(); }
    ctx.fillStyle=T.muted; ctx.font="700 12px Inter"; ctx.fillText(`T${ti+1}`,14,y+15);
    ctx.fillStyle=sel?T.accent:T.text; ctx.font="600 11px Inter"; ctx.fillText(`CH${tt.ch} PC${tt.prog}`,46,y+15);
    for(let s2=0;s2<16;s2++){
      const x=140+s2*34, st=tt.steps[s2];
      ctx.fillStyle=st.on?(s2%4===0?T.green:T.orange):T.line; roundRect(x,y+5,30,16,3); ctx.fill();
      if(s2===state.extStep&&sel){ ctx.strokeStyle=T.accent; ctx.lineWidth=1.5; roundRect(x-1,y+4,32,18,4); ctx.stroke(); }
    }
  }
  // параметры: левые 8 = EXT, правые 8 = макросы (зеркально ручкам)
  const gy=326, cellH=44, cellW=(W-24-16)/8;
  for(let i=0;i<16;i++){
    const row=Math.floor(i/8), col=i%8, x=12+col*cellW, y=gy+row*cellH, w=cellW-6;
    ctx.fillStyle=T.card; roundRect(x,y,w,cellH-6,5); ctx.fill();
    let label,val,frac,letter;
    if(col<4){ label=t(EXT_PARAM_KEYS[row*4+col]); val=String(Math.round(extVal(row*4+col))); frac=(extVal(row*4+col)-EXT_MIN[row*4+col])/(EXT_MAX[row*4+col]-EXT_MIN[row*4+col]); letter=LETTERS_L[row*4+col]; }
    else { const mi=row*4+(col-4), m=MACRO[mi]; label=t("macro."+m.key); val=String(Math.round(m.get())); frac=(m.get()-m.min)/(m.max-m.min); letter=LETTERS_R[mi]; }
    ctx.fillStyle=T.muted; ctx.font="600 12px Inter"; ctx.fillText(`${letter} · ${label}`,x+5,y+13);
    ctx.fillStyle=T.text; ctx.font="700 18px Inter"; ctx.fillText(val,x+5,y+32);
    ctx.fillStyle=T.line; ctx.fillRect(x+5,y+cellH-13,w-10,4);
    ctx.fillStyle=T.accent; ctx.fillRect(x+5,y+cellH-13,(w-10)*clamp(frac,0,1),4);
  }
  ctx.fillStyle=T.line; ctx.fillRect(12+4*cellW-3,gy-2,2,cellH*2-8);
  ctx.fillStyle=T.muted; ctx.font="600 9px Inter"; ctx.fillText(t("col.ext"),12+cellW*1.1,gy-5); ctx.fillText(t("col.macros"),12+cellW*4.6,gy-5);
}
function drawSampler(){
  ctx.fillStyle=T.accent; ctx.font="700 16px Inter"; ctx.fillText(t("sampler.title"),20,110);
  const recTxt = state.recording ? t("sampler.recActive",{s:(AC? (AC.currentTime-state.recStarted):0).toFixed(1)}) : t("sampler.recIdle");
  ctx.fillStyle = state.recording ? T.red : T.muted; ctx.font="600 11px Inter"; ctx.fillText(recTxt, 20, 132);
  const pads = state.pads.length ? state.pads.slice(0,4) : [];
  for(let i=0;i<4;i++){
    const x=18+i*192, y=148, w=180, h=150;
    ctx.fillStyle=T.card; roundRect(x,y,w,h,6); ctx.fill();
    if(i===state.selPart%4){ ctx.strokeStyle=T.accent; ctx.lineWidth=1.5; roundRect(x,y,w,h,6); ctx.stroke(); }
    const pad=pads[i];
    ctx.fillStyle=pad?T.text:T.muted; ctx.font="700 14px Inter";
    ctx.fillText(pad?pad.name:t("sampler.pad",{n:i+1}),x+12,y+24);
    ctx.fillStyle=T.muted; ctx.font="600 10px Inter";
    ctx.fillText(pad?(pad.loop?t("sampler.loop"):t("sampler.oneShot")):t("sampler.empty"),x+12,y+40);
    if(pad){
      const data=pad.buffer.getChannelData(0), step=Math.max(1,Math.floor(data.length/w));
      ctx.fillStyle=T.line; ctx.fillRect(x+12,y+52,w-24,70);
      for(let px=0;px<w-24;px++){
        let peak=0; for(let k=0;k<step;k+=8){ const v=Math.abs(data[px*step+k]||0); if(v>peak)peak=v; }
        const hh=Math.min(1,peak*1.5)*(70/2);
        ctx.fillStyle=T.accent; ctx.fillRect(x+12+px, y+52+35-hh, 1, hh*2);
      }
      ctx.fillStyle=T.muted; ctx.font="10px Inter"; ctx.fillText(t("sampler.dur",{s:(pad.buffer.duration).toFixed(2)}),x+12,y+138);
    } else {
      ctx.fillStyle=T.line; ctx.fillRect(x+12,y+52,w-24,70);
    }
  }
  ctx.fillStyle=T.muted; ctx.font="600 11px Inter"; ctx.fillText(t("sampler.hint1"),20,330);
  ctx.fillStyle=T.muted; ctx.font="600 11px Inter"; ctx.fillText(t("sampler.hint2"),20,352);
}
function drawDaw(){
  ctx.fillStyle=T.accent; ctx.font="700 16px Inter"; ctx.fillText(t("daw.title"),20,110);
  [["CC 16-31","CUTOFF 74","RESO 71","DRIVE 91","ATK 73"],["CC 32-47","DEC 75","SUS 76","REL 72","PAN 10"]].forEach((bank,bi)=>{
    ctx.fillStyle=T.card; roundRect(14,126+bi*110,W-28,96,6); ctx.fill();
    ctx.fillStyle=T.muted; ctx.font="600 11px Inter"; ctx.fillText(bank[0],26,148+bi*110);
    for(let i=0;i<16;i++){
      const x=120+i*40,y=158+bi*110; ctx.fillStyle=i<4?T.blue:T.line; roundRect(x,y,34,38,4); ctx.fill();
      ctx.fillStyle=i<4?"#04140b":T.muted; ctx.font="700 10px Inter"; ctx.fillText(String(i+16+bi*16),x+5,y+15);
      ctx.font="8px Inter"; ctx.fillText(i<4?bank[1+i].split(" ")[0]:"",x+2,y+30);
    }
  });
  ctx.fillStyle=T.muted; ctx.font="600 11px Inter"; ctx.fillText(t("daw.hint"),20,390);
}
function drawUsbKbd(){
  ctx.fillStyle=T.accent; ctx.font="700 16px Inter"; ctx.fillText(t("usb.title"),20,110);
  ctx.fillStyle=T.card; roundRect(14,126,W-28,180,6); ctx.fill();
  ["q w e r t y u i o p","a s d f g h j k l ;","z x c v b n m , . /"].forEach((r,i)=>{ ctx.fillStyle=T.text; ctx.font="600 18px ui-monospace, monospace"; ctx.fillText(r,34,170+i*46); });
  ctx.fillStyle=T.muted; ctx.font="600 11px Inter";
  ctx.fillText(t("usb.hint"),20,340);
}
function analyseLevel(){ if(!analyser) return 0; analyser.getByteTimeDomainData(masterData); let s=0; for(let i=0;i<masterData.length;i++){const v=(masterData[i]-128)/128;s+=v*v;} return Math.sqrt(s/masterData.length); }

/* ---------- canvas hit testing ---------- */
function canvasPos(e){ const r=cv.getBoundingClientRect(); return {x:(e.clientX-r.left)*(W/r.width), y:(e.clientY-r.top)*(H/r.height)}; }
cv.addEventListener("pointerdown",(e)=>{
  const {x,y}=canvasPos(e);
  if(y<44){ const i=Math.floor((x-196)/104); if(i>=0&&i<5){ state.mode=i; paintKnobs(); save(); } return; }
  if(state.mode===4){
    if(y>126&&y<322&&x>8&&x<W-8){ const ti=Math.floor((y-132)/23); if(ti>=0&&ti<8){ state.extSel=ti; const s2=Math.floor((x-140)/34); if(s2>=0&&s2<16&&x>=140){ state.extStep=s2; snapshot(); const t=state.extTracks[ti], st=t.steps[s2]; st.on=!st.on; } paintKnobs(); save(); } }
    return;
  }
  if(state.mode===1){
    if(y>140&&y<310&&x>18&&x<786){ const i=Math.floor((x-18)/192); if(i>=0&&i<4){ lastPadClick = lastPadClick && (Date.now()-lastPadClick.t<350) && lastPadClick.i===i ? {i,t:Date.now(),dbl:true} : {i,t:Date.now(),dbl:false};
        if(lastPadClick.dbl){ if(state.pads[i]) state.pads[i].loop=!state.pads[i].loop; } else playPad(i); } }
    return;
  }
  if(state.mode!==0) return;
  // страницы параметров
  if(y>370&&y<390&&x>18&&x<18+5*92){ const i=Math.floor((x-18)/92); if(i>=0&&i<5){ state.page=i; paintKnobs(); syncPageChips(); if(i===2&&TEST)TEST.env=true; save(); return; } }
  // смена темы — правый нижний угол
  if(y>12&&y<32&&x>W-90){ const names=Object.keys(THEMES); const idx=Math.round((x-(W-74))/18); const n=names[idx]; if(n) setTheme(n); return; }
  const pi=Math.floor((y-96)/66);
  if(pi<0||pi>3) return;
  // mute по клику на имя партии
  if(x<120){
    if(e.shiftKey){ state.selParts.has(pi)?state.selParts.delete(pi):state.selParts.add(pi); if(!state.selParts.size) state.selParts.add(pi); state.selPart=pi; paintKnobs(); }
    else { state.parts[pi].mute=!state.parts[pi].mute; if(TEST && state.parts.filter(p=>p.mute).length>=2) TEST.mute2=true; }
    save(); return;
  }
  if(x>120&&x<776){ const s=Math.floor((x-128)/40); if(s>=0&&s<=15){ snapshot(); const part=state.parts[pi], st=part.steps[s]; st.on=!st.on; if(st.on) st.accent=s%4===0; state.selPart=pi; paintKnobs(); save(); startPreview(part,s); } }
});
function startPreview(part,s){ if(!state.playing){ const n=part.root+part.steps[s].note; noteOn(n,0.8,part); setTimeout(()=>noteOff(n),180); } }

/* ---------- share ---------- */
function encodeState(){
  const compact={b:state.bpm,s:state.selPart,p:state.parts.map(p=>({r:p.root,a:p.active?1:0,m:p.mute?1:0,pg:p.pages.map(pg=>pg.map(x=>Math.round(x))),st:p.steps.map(x=>(x.on?(x.accent?2:1):0)*128+x.note)}))};
  return btoa(JSON.stringify(compact)).replace(/=+$/,"");
}
function decodeState(b64){
  try{ const c=JSON.parse(atob(b64)); if(c.b) state.bpm=clamp(c.b,40,220); if(c.s!=null) state.selPart=clamp(c.s,0,3);
    (c.p||[]).forEach((cp,i)=>{ const p=state.parts[i]; if(!p)return; p.root=cp.r; p.active=!!cp.a; p.mute=!!cp.m;
      if(cp.pg) p.pages=cp.pg;
      (cp.st||[]).forEach((v,s)=>{ const on=Math.floor(v/128)>0; p.steps[s].on=on; p.steps[s].accent=Math.floor(v/128)===2; p.steps[s].note=v%128; });
    }); paintKnobs(); return true; }catch(e){ return false; }
}
function copyShareLink(){ const url=location.origin+location.pathname+"#p="+encodeState(); if(navigator.clipboard) navigator.clipboard.writeText(url).catch(()=>{}); flashMsg(t("msg.linkCopied")); $("shareState").textContent=t("msg.linkCopied"); setTimeout(()=>{$("shareState").textContent="";},2000); }
function loadFromHash(){ const m=location.hash.match(/#p=(.+)/); if(m) return decodeState(m[1]); return false; }

/* ---------- storage / init ---------- */
const KEY="bukifon-demo-v2";
function save(){ try{ localStorage.setItem(KEY, JSON.stringify({bpm:state.bpm,volume:state.volume,delayMix:state.delayMix,faderMode:state.faderMode,parts:state.parts,page:state.page,theme:state.theme,mode:state.mode,sel:state.selPart})); }catch(e){} }
function load(){
  try{ const p=JSON.parse(localStorage.getItem(KEY)||"null"); if(!p) return;
    state.bpm=p.bpm??120; state.volume=p.volume??0.7; state.delayMix=p.delayMix??0.25; state.faderMode=p.faderMode||"TRACK";
    state.page=p.page??0; state.theme=p.theme||"night"; state.mode=p.mode??0; state.selPart=p.sel??0;
    if(Array.isArray(p.parts)) p.parts.forEach((x,i)=>{ if(x&&x.pages){ state.parts[i]=x; } });
  }catch(e){}
}
/* ---------- language switching + applying the string table ---------- */
function setLang(l){
  if(!LANGS.includes(l) || l===LANG) return;
  LANG=l;
  try{ localStorage.setItem(LANG_KEY,LANG); }catch(e){}
  syncLangUrl();
  applyLang();
  paintKnobs();
  flashMsg("");
}
function applyLang(){
  document.documentElement.lang = LANG;
  document.title = t("app.title");
  const md=document.querySelector('meta[name="description"]'); if(md) md.setAttribute("content", t("app.desc"));
  document.querySelectorAll("[data-i18n]").forEach(el=>{ el.textContent=t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-label]").forEach(el=>{ const s=t(el.dataset.i18nLabel); el.title=s; el.setAttribute("aria-label",s); });
  document.querySelectorAll("[data-i18n-aria]").forEach(el=>{ el.setAttribute("aria-label",t(el.dataset.i18nAria)); });
  document.querySelectorAll("[data-i18n-title]").forEach(el=>{ el.title=t(el.dataset.i18nTitle); });
  document.querySelectorAll("[data-lang]").forEach(b=>{ const on=b.dataset.lang===LANG; b.classList.toggle("active",on); b.setAttribute("aria-pressed",on?"true":"false"); });
  const lg=document.getElementById("langSwitch"); if(lg) lg.setAttribute("aria-label",t("a11y.langGroup"));
  fillPresetOptions(); fillThemeOptions();
  buildPageChips(); syncPageChips();
  paintFaderLabels();
  if(knobEls.length) paintKnobs();
  document.querySelectorAll("#keysLeft button, #keysRight button").forEach(b=>{ const midi=+b.dataset.midi, lab=b.querySelector("b"); const ka=t("a11y.key",{l:lab?lab.textContent:"",note:noteName(midi)}); b.setAttribute("aria-label",ka); b.title=ka; });
  renderContextBar(); renderMidiState();
  const share=$("shareState"); if(share) share.textContent="";
  const tb=document.getElementById("btnTest"); if(tb && tb.style.display!=="none") tb.textContent=t("btn.copyJson");
}
function fillPresetOptions(){
  const psel=$("presetSel"); if(!psel) return;
  const cur=psel.value; psel.innerHTML="";
  for(let i=0;i<8;i++){ const o=document.createElement("option"); o.value=i; o.textContent=t("preset.option",{n:i+1}); psel.appendChild(o); }
  if(cur!=="") psel.value=cur;
}
function fillThemeOptions(){
  const themeSel=$("themeSel"); if(!themeSel) return;
  themeSel.innerHTML="";
  Object.keys(THEMES).forEach(n=>{ const o=document.createElement("option"); o.value=n; o.textContent=themeLabel(n); themeSel.appendChild(o); });
  themeSel.value=state.theme;
}

/* ---------- текст в ячейках: аудит ширины (docs/61: строка ≤ ячейки) ---------- */
function measureTextW(str, font){ const old=ctx.font; ctx.font=font; const w=ctx.measureText(str).width; ctx.font=old; return w; }
function textFitAudit(lang){
  const prev=LANG; if(lang && LANGS.includes(lang)) LANG=lang;
  const rows=[];
  const add=(where,str,font,max)=>{ const w=measureTextW(str,font); rows.push({where:where,str:str,w:Math.round(w*10)/10,max:max,ok:w<=max+0.5}); };
  const cellW=(W-24-16)/8, avail=cellW-6-12;
  for(let p=0;p<5;p++) for(let i=0;i<8;i++){
    add("param cell page "+p, LETTERS_L[i]+" · "+t(PAGE_PARAM_KEYS[p][i]), "600 12px Inter", avail);
    add("macro cell", LETTERS_R[i]+" · "+t("macro."+MACRO[i].key), "600 12px Inter", avail);
  }
  for(let i=0;i<8;i++) add("ext cell", LETTERS_L[i]+" · "+t(EXT_PARAM_KEYS[i]), "600 12px Inter", avail);
  for(let i=0;i<5;i++){ add("page tab", t(PAGES[i]), "700 12px Inter", 72); add("mode tab", t(MODES[i]), "700 12px Inter", 90); }
  const info=[[t("info.bpm"),String(state.bpm)],[t("info.step"),"00"],[t("info.page"),t(PAGES[state.page])],[t("info.theme"),themeLabel(state.theme)]];
  info.forEach((kv)=>{ add("info label",kv[0],"600 11px Inter",66); add("info value",kv[1],"700 16px Inter",66); });
  for(let pi=0;pi<4;pi++){ const pt=t("synth.part")+" "+(pi+1), sfx=" · "+t("synth.mute"); add("part line "+pi, pt+sfx, "700 13px Inter", 96); add("part name "+pi, PART_NAMES[pi], "600 11px Inter", 92); }
  add("header brand", t("app.brand"), "700 26px Inter, system-ui, sans-serif", 178);
  add("status master", t("status.master"), "600 11px Inter", 52);
  add("status faders", t("status.faders",{m:"TRACK"}), "600 11px Inter", 400);
  add("status mic", t("status.mic"), "600 9px Inter", 44);
  add("ext title", t("ext.title"), "700 17px Inter", 768);
  add("ext clock", t("ext.clockOff"), "600 11px Inter", 768);
  add("col page", t("col.page"), "600 9px Inter", 70);
  add("col macros", t("col.macros"), "600 9px Inter", 70);
  add("sampler title", t("sampler.title"), "700 16px Inter", 760);
  add("sampler rec", t("sampler.recIdle"), "600 11px Inter", 760);
  add("sampler hint1", t("sampler.hint1"), "600 11px Inter", 760);
  add("sampler hint2", t("sampler.hint2"), "600 11px Inter", 760);
  add("daw title", t("daw.title"), "700 16px Inter", 760);
  add("daw hint", t("daw.hint"), "600 11px Inter", 760);
  add("usb title", t("usb.title"), "700 16px Inter", 760);
  add("usb hint", t("usb.hint"), "600 11px Inter", 760);
  add("overlay title", t("overlay.title"), "700 14px Inter", 660);
  for(let i=1;i<=7;i++){ add("overlay r"+i+"k", t("overlay.r"+i+"k"), "600 11px Inter", 206); add("overlay r"+i+"v", t("overlay.r"+i+"v"), "600 11px Inter", 460); }
  add("overlay foot", t("overlay.foot"), "600 10px Inter", 660);
  add("test progress", t("test.progress"), "600 12px Inter", 720);
  add("test auto", t("test.auto"), "600 12px Inter", 720);
  add("test copyHint", t("test.copyHint"), "600 12px Inter", 720);
  add("test copyHint2", t("test.copyHint2"), "700 13px Inter", 720);
  add("test results", t("test.results"), "700 18px Inter", 720);
  for(let i=1;i<=8;i++) add("test task "+i, t("test.t"+i), "700 18px Inter", 720);
  Object.keys(I18N[LANG]).filter(k=>k.indexOf("msg.")===0).forEach(k=>{ add("flash "+k, t(k).replace(/\{[a-z]+\}/g,"1"), "700 12px Inter", 218); });
  LANG=prev;
  return {lang:lang||prev, rows:rows, overflows:rows.filter(r=>!r.ok)};
}
if(typeof window!=="undefined"){
  window.__i18n={
    lang:()=>LANG,
    set:(l)=>setLang(l),
    table:()=>I18N,
    missing:()=>i18nMissing.slice(),
    audit:()=>({
      ru:Object.keys(I18N.ru).length, en:Object.keys(I18N.en).length,
      missingEn:Object.keys(I18N.ru).filter(k=>!(k in I18N.en)),
      missingRu:Object.keys(I18N.en).filter(k=>!(k in I18N.ru)),
      empty:Object.keys(I18N.ru).filter(k=>!I18N.ru[k] || !I18N.en[k]),
      usedMissing:i18nMissing.slice(),
    }),
    textFit:(l)=>textFitAudit(l),
  };
}

function bindUI(){
  $("btnPlay").addEventListener("click",()=>state.playing?stopSeq():startSeq());
  $("btnStop").addEventListener("click",()=>stopSeq());
  const share=$("btnShare"); if(share) share.addEventListener("click",copyShareLink);
  const recBtn=$("btnRec"); if(recBtn) recBtn.addEventListener("click",toggleRec);
  const micBtn=$("btnMic"); if(micBtn) micBtn.addEventListener("click",micToggle);
  const bbBtn=$("btnBeatbox"); if(bbBtn) bbBtn.addEventListener("click",beatboxToSteps);
  const mg=$("micGain"); if(mg) mg.addEventListener("input",(e)=>{ state.mic.gain=+e.target.value/100; });
  const rm=$("btnRecMic"); if(rm) rm.addEventListener("click",toggleMicRec);
  const home=$("btnHome"); if(home) home.addEventListener("click",goHome);
  const undoBtn=$("btnUndo"); if(undoBtn) undoBtn.addEventListener("click",undo);
  document.querySelectorAll("[data-lang]").forEach(b=>b.addEventListener("click",()=>setLang(b.dataset.lang)));
  if(new URLSearchParams(location.search).get("test")==="1"){ startTest(); setInterval(checkTest,100); const tb=document.getElementById("btnTest"); if(tb){tb.textContent=t("btn.copyJson"); tb.onclick=copyTestResults; tb.style.display="inline-block";} }
  buildPageChips(); syncPageChips(); renderContextBar();
  const rand=$("btnRandom"); if(rand) rand.addEventListener("click",randomizePattern);
  const td=$("btnTransDown"); if(td) td.addEventListener("click",()=>transpose(-12));
  fillPresetOptions();
  const psel=$("presetSel");
  const psave=$("btnPresetSave"); if(psave) psave.addEventListener("click",()=>savePresetTo(+(psel.value||0)));
  const pload=$("btnPresetLoad"); if(pload) pload.addEventListener("click",()=>loadPresetFrom(+(psel.value||0)));
  const ab=$("btnAB"); if(ab) ab.addEventListener("click",toggleAB);
  const tu=$("btnTransUp"); if(tu) tu.addEventListener("click",()=>transpose(12));
  fillThemeOptions();
  const themeSel=$("themeSel");
  if(themeSel) themeSel.addEventListener("change",(e)=>setTheme(e.target.value));
  $("bpm").value=state.bpm; $("bpm").addEventListener("change",(e)=>{ state.bpm=clamp(+e.target.value||120,40,220); save(); });
  $("volume").value=Math.round(state.volume*100); $("volume").addEventListener("input",(e)=>{ state.volume=+e.target.value/100; if(master)master.gain.value=state.volume; save(); });
  document.querySelectorAll("[data-fmode]").forEach(b=>b.addEventListener("click",()=>setFaderMode(b.dataset.fmode)));
  setFaderMode(state.faderMode); paintFaderLabels();
  document.querySelectorAll(".fader").forEach(f=>{ const v=f.dataset.fader==="0"?state.volume:state.delayMix; f.style.setProperty("--top",((1-v)*100).toFixed(1)+"%"); });
}
initLang();
load(); if(loadFromHash()) {}
const params = new URLSearchParams(location.search);
if (params.get("theme") && THEMES[params.get("theme")]) state.theme = params.get("theme");
if (params.get("page") != null) state.page = clamp(+params.get("page")||0, 0, 4);
if (params.get("mode") != null) state.mode = clamp(+params.get("mode")||0, 0, 4);
if (params.get("capture") === "1") document.body.classList.add("capture");
setTheme(state.theme); buildKeys(); buildKnobs(); buildFaders(); buildJacks(); bindUI(); paintKnobs(); midiInit();
applyLang();
// если язык пришёл из localStorage (EN) — отразить его и в URL, чтобы ссылкой можно было поделиться
if (LANG === "en" && !/[?&]lang=/.test(location.search)) syncLangUrl();

(function loop(){ draw(); requestAnimationFrame(loop); })();
