const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function setup() {
  const elements = new Map();
  const element = (id) => {
    if (!elements.has(id)) elements.set(id, {
      value: '', disabled: false, hidden: false, textContent: '',
      handlers: {}, attributes: {},
      classList: { add() {}, remove() {}, toggle() {} },
      addEventListener(name, handler) { this.handlers[name] = handler; },
      setAttribute(name, value) { this.attributes[name] = value; },
      removeAttribute() {}, load() {}, focus() {},
    });
    return elements.get(id);
  };
  let now = 0, permissionCalls = 0, stops = 0, released = 0;
  let interval;
  let activeRecorder;
  const requests = [];
  class MediaRecorder {
    static isTypeSupported() { return true; }
    constructor() { this.state = 'inactive'; this.mimeType = 'audio/webm'; activeRecorder = this; }
    start() { this.state = 'recording'; }
    stop() { stops++; this.state = 'inactive'; }
  }
  const context = vm.createContext({
    document: { getElementById: element, querySelectorAll: () => [], body: element('body') },
    window: { MediaRecorder, addEventListener() {} }, MediaRecorder,
    navigator: { mediaDevices: { async getUserMedia() {
      permissionCalls++;
      return { getTracks: () => [{ stop() { released++; } }] };
    } } },
    localStorage: { getItem: () => '+2348012345678', setItem() {} },
    Date: { now: () => now }, Blob, FormData, AbortController, setTimeout, clearTimeout,
    async fetch(url, options) {
      requests.push({ url, options });
      return { ok: true, async json() { return { transcript: 'Mo ta epo pupa fun 1515,000' }; } };
    },
    URL: { createObjectURL: () => 'blob:recording', revokeObjectURL() {} },
    setInterval(callback) { interval = callback; return 1; }, clearInterval() { interval = null; },
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../app/static/app.js'), 'utf8'), context);
  return {
    element, requests, click: () => element('record').handlers.click(),
    advance(ms) { now += ms; interval?.(); },
    finish() {
      activeRecorder.ondataavailable({ data: new Blob(['audio']) });
      activeRecorder.onstop();
    },
    stats: () => ({ permissionCalls, stops, released }),
  };
}

test('a second tap stops recording while other controls are locked, then shows preview', async () => {
  const app = setup();
  await app.click();
  assert.equal(app.element('record').disabled, false);
  assert.equal(app.element('send').disabled, true);
  assert.equal(app.element('record').attributes['aria-label'], 'Stop recording');
  app.advance(1000);
  await app.click();
  assert.equal(app.stats().stops, 1);
  // Another tap while the final audio is being collected must not start again.
  await app.click();
  assert.equal(app.stats().permissionCalls, 1);
  app.finish();
  assert.equal(app.stats().released, 1);
  assert.equal(app.element('recording-review').hidden, false);
  assert.equal(app.element('send').disabled, false);
  assert.equal(app.element('record').attributes['aria-label'], 'Start recording');
  await app.click();
  assert.equal(app.stats().permissionCalls, 2);
});

test('recording also stops automatically at its time limit', async () => {
  const app = setup();
  await app.click();
  app.advance(119000);
  assert.equal(app.stats().stops, 1);
  app.finish();
  assert.equal(app.stats().released, 1);
  assert.equal(app.element('recording-review').hidden, false);
});

test('voice review displays the unmodified transcript without submitting a bookkeeping instruction', async () => {
  const app = setup();
  await app.click();
  app.advance(1000);
  await app.click();
  app.finish();
  await app.element('send-voice').handlers.click();
  assert.equal(app.requests.length, 1);
  assert.equal(app.requests[0].url, '/ai/voice');
  assert.equal(app.requests[0].options.body.get('transcribe_only'), 'true');
  assert.equal(app.element('message').value, 'Mo ta epo pupa fun 1515,000');
  assert.match(app.element('status').textContent, /Nothing has been saved/);
  assert.equal(app.element('message').disabled, false);
});
