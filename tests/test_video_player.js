const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const template = fs.readFileSync(path.join(__dirname,
  "../plugins/reverse-engineer-any-video/skills/reverse-engineer-any-video/assets/video-report.html"), "utf8");
const script = template.match(/<script>\s*([\s\S]*?)<\/script>/)[1];

class Element {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.handlers = new Map();
    this.dataset = {};
    this.style = {setProperty() {}};
    this.classList = {add() {}, remove() {}};
    this.readyState = 1;
    this.duration = 22;
    this.currentTime = 0;
    this.textContent = "";
  }

  get childNodes() { return this.children; }
  get lastElementChild() { return this.children.at(-1); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  setAttribute() {}
  focus() {}
  addEventListener(name, action) { this.handlers.set(name, action); }
  fire(name) {
    this.handlers.get(name)({currentTarget: this, preventDefault() {}, stopPropagation() {}});
  }
}

function initialize(report) {
  const ids = new Map();
  const created = [];
  const get = (id) => {
    if (!ids.has(id)) ids.set(id, new Element(id));
    return ids.get(id);
  };
  get("report-data").textContent = JSON.stringify(report);
  const document = {
    getElementById: get,
    querySelectorAll: () => [],
    createTextNode: (text) => String(text),
    createElement: (tag) => {
      const node = new Element(tag);
      created.push(node);
      return node;
    },
  };
  vm.runInNewContext(script, {document, URL});
  return {get, created};
}

test("finds a multiword on-screen phrase and seeks both videos on their picture clocks", () => {
  const first = {duration: 20, pictureOffset: 0.75, label: "Reference", words: [], coverage: {}, events: [],
    frames: [{t: 6, text: "Calibration pending\nCalibration complete", image: "frame.jpg"},
      {t: 7, text: "Calibration complete"}, {t: 8, text: "Ready"}]};
  const second = {duration: 20, pictureOffset: 1.5, label: "Candidate", words: [], coverage: {}, events: [],
    frames: []};
  const {get, created} = initialize({videos: [first, second],
    metrics: [{label: "Calls", values: ["1", "2"], delta: "+1"}]});
  get("link-seek").checked = true;
  get("link-seek").fire("change");
  get("query").value = "Calibration complete!";
  get("search-form").fire("submit");
  assert.equal(get("results").children.length, 1);
  const result = get("results").children[0];
  assert.equal(result.className, "result");
  result.fire("click");
  assert.deepEqual(created.filter(node => node.tag === "video").map(node => node.currentTime), [6.75, 7.5]);
  assert.ok(created.some(node => node.tag === "td" && node.textContent === "+1"));
});

test("speech results seek to the first matching word", () => {
  const first = {duration: 20, pictureOffset: 0, label: "Reference", coverage: {}, events: [], frames: [],
    words: [{word: "Copper,", start: 1.65, end: 2}, {word: "valve.", start: 2, end: 2.4}]};
  const {get, created} = initialize({videos: [first], metrics: []});
  get("query").value = "copper valve";
  get("search-form").fire("submit");
  assert.equal(get("results").children[0].className, "result");
  get("results").children[0].fire("click");
  assert.equal(created.find(node => node.tag === "video").currentTime, 1.65);
});

test("caption search accepts accents and seeks to the caption cue start", () => {
  const video = {duration: 20, pictureOffset: 0.5, label: "Reference", coverage: {},
    events: [], frames: [], words: [], captions: [{text: "Adélie penguins", start: 4.2, end: 6}]};
  const {get, created} = initialize({videos: [video], metrics: []});
  get("query").value = "adelie penguins";
  get("search-form").fire("submit");
  assert.equal(get("results").children[0].className, "result");
  get("results").children[0].fire("click");
  assert.equal(created.find(node => node.tag === "video").currentTime, 4.7);
  assert.ok(created.some(node => node.textContent === "caption"));
});
