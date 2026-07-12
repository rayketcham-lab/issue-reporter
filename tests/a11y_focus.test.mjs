// Accessibility focus-management tests for the report modal (issue #26).
//
// Drives the *real* issue-reporter.js inside jsdom and asserts the WAI-ARIA
// dialog focus contract: focus enters the dialog on open, Tab/Shift+Tab are
// trapped, the background is made inert, and focus is restored on close.
//
// Run: node tests/a11y_focus.test.mjs   (from the package dir; needs jsdom)

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { JSDOM } from "jsdom";

const here = dirname(fileURLToPath(import.meta.url));
const widgetSrc = readFileSync(join(here, "..", "issue-reporter.js"), "utf8");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let passed = 0;
let failed = 0;
function assert(cond, msg) {
  if (cond) {
    passed++;
    console.log("  ✓ " + msg);
  } else {
    failed++;
    console.error("  ✗ " + msg);
  }
}

// Fresh document + initialized widget for each test.
function setup(fetchStub) {
  const dom = new JSDOM(
    `<!DOCTYPE html><html><body>
       <header id="page-header"><a href="#main" id="skip">Skip</a></header>
       <main id="main"><button id="page-btn">Page button</button></main>
     </body></html>`,
    { url: "https://example.test/", runScripts: "outside-only", pretendToBeVisual: true }
  );
  const { window } = dom;
  // Expose globals the widget expects, then evaluate it in this window.
  const g = ["window", "document", "navigator", "location", "setTimeout", "clearTimeout", "console", "fetch"];
  const fn = new window.Function(...g, widgetSrc + "\n;return window.IssueReporter;");
  const fetchImpl = fetchStub || (() => Promise.reject(new Error("no network in test")));
  const IssueReporter = fn(
    window, window.document, window.navigator, window.location,
    window.setTimeout, window.clearTimeout, window.console, fetchImpl
  );
  IssueReporter.init({ github: { repo: "acme/app", token: "github_pat_x" }, projectName: "T" });
  // jsdom stays in readyState "loading", so the widget defers createButton to
  // DOMContentLoaded — fire it so the trigger button exists (as in a real page).
  window.document.dispatchEvent(new window.Event("DOMContentLoaded", { bubbles: true }));
  return { window, document: window.document, IssueReporter };
}

function tab(window, { shift = false } = {}) {
  const doc = window.document;
  const ev = new window.KeyboardEvent("keydown", {
    key: "Tab", shiftKey: shift, bubbles: true, cancelable: true,
  });
  doc.dispatchEvent(ev);
  return ev;
}

async function testFocusEntersOnStep0() {
  console.log("focus enters the dialog on open (step 0)");
  const { window, document, IssueReporter } = setup();
  const trigger = document.querySelector(".ir-btn");
  trigger.focus();
  assert(document.activeElement === trigger, "trigger button is focused before open");

  IssueReporter.open();
  await sleep(10); // let the deferred focusModalStart run

  const modal = document.querySelector(".ir-modal");
  assert(modal.contains(document.activeElement), "focus moved inside the dialog on step 0");
  assert(
    document.activeElement.classList.contains("ir-type-card"),
    "first type card receives focus on step 0 (not the hidden trigger)"
  );
}

async function testTabTrap() {
  console.log("Tab / Shift+Tab are trapped within the dialog");
  const { window, document, IssueReporter } = setup();
  IssueReporter.open();
  await sleep(10);
  const modal = document.querySelector(".ir-modal");

  // Walk Tab forward many times — focus must never leave the modal.
  let leaked = false;
  for (let i = 0; i < 40; i++) {
    tab(window);
    if (!modal.contains(document.activeElement)) { leaked = true; break; }
  }
  assert(!leaked, "Tab never lands on page content behind the backdrop");

  // Shift+Tab from the first control wraps to the last.
  const focusable = modal.querySelectorAll(
    "a[href], button:not([disabled]), textarea, input, select"
  );
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  first.focus();
  const ev = tab(window, { shift: true });
  assert(ev.defaultPrevented, "Shift+Tab at the first control is intercepted");
  assert(document.activeElement === last, "Shift+Tab from first wraps to last");

  // Tab from the last control wraps to the first.
  last.focus();
  const ev2 = tab(window);
  assert(ev2.defaultPrevented, "Tab at the last control is intercepted");
  assert(document.activeElement === first, "Tab from last wraps to first");
}

async function testBackgroundInert() {
  console.log("background is inert + hidden from assistive tech while open");
  const { window, document, IssueReporter } = setup();
  const header = document.getElementById("page-header");
  const main = document.getElementById("main");

  IssueReporter.open();
  await sleep(10);

  assert(header.hasAttribute("inert") && header.getAttribute("aria-hidden") === "true",
    "page header is inert + aria-hidden while modal open");
  assert(main.hasAttribute("inert") && main.getAttribute("aria-hidden") === "true",
    "page main is inert + aria-hidden while modal open");
  const backdrop = document.querySelector(".ir-backdrop");
  assert(!backdrop.hasAttribute("inert"), "the dialog's own backdrop is NOT inert");

  IssueReporter.close();
  await sleep(300);
  assert(!header.hasAttribute("inert") && !header.hasAttribute("aria-hidden"),
    "page header inert + aria-hidden removed after close");
  assert(!main.hasAttribute("inert") && !main.hasAttribute("aria-hidden"),
    "page main inert + aria-hidden removed after close");
}

async function testFocusRestoredOnClose(label, closeFn) {
  console.log("focus restored to trigger on close via " + label);
  const { window, document, IssueReporter } = setup();
  const trigger = document.querySelector(".ir-btn");
  trigger.focus();
  IssueReporter.open();
  await sleep(10);
  const modal = document.querySelector(".ir-modal");
  assert(modal.contains(document.activeElement), "focus is inside modal before close");

  closeFn({ window, document, IssueReporter });
  await sleep(300); // close animation timeout + focus restore

  assert(document.activeElement === trigger,
    "focus returned to the trigger button after " + label);
}

function pressEscape({ window, document }) {
  document.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
}
function clickBackdrop({ window, document }) {
  document.querySelector(".ir-backdrop").dispatchEvent(new window.Event("click", { bubbles: true }));
}
function clickCloseX({ window, document }) {
  document.querySelector(".ir-close").dispatchEvent(new window.Event("click", { bubbles: true }));
}

async function testDoneRestoresFocus() {
  console.log("focus restored to trigger on close via the Done button (after submit)");
  const okFetch = () =>
    Promise.resolve({ ok: true, status: 201, json: () => Promise.resolve({ html_url: "https://github.com/acme/app/issues/1" }) });
  const { window, document, IssueReporter } = setup(okFetch);
  const trigger = document.querySelector(".ir-btn");
  trigger.focus();

  IssueReporter.open();
  await sleep(10);
  // Step 0: pick the first type.
  document.querySelector(".ir-type-card").dispatchEvent(new window.Event("click", { bubbles: true }));
  document.querySelector(".ir-footer-next").dispatchEvent(new window.Event("click", { bubbles: true }));
  await sleep(60);
  // Step 1: fill the description.
  const desc = document.getElementById("ir-desc");
  desc.value = "Something is broken on this page";
  desc.dispatchEvent(new window.Event("input", { bubbles: true }));
  document.querySelector(".ir-footer-next").dispatchEvent(new window.Event("click", { bubbles: true }));
  await sleep(60);
  // Step 2: submit.
  document.querySelector(".ir-footer-submit").dispatchEvent(new window.Event("click", { bubbles: true }));
  await sleep(60);

  const done = document.querySelector(".ir-status-action");
  assert(!!done, "result screen with a Done button is shown after successful submit");
  done.dispatchEvent(new window.Event("click", { bubbles: true }));
  await sleep(300);
  assert(document.activeElement === trigger, "focus returned to the trigger button after Done");
}

async function testReopenDuringCloseAnimation() {
  console.log("re-opening within the close animation window is not torn down");
  const { window, document, IssueReporter } = setup();
  document.querySelector(".ir-btn").focus();
  IssueReporter.open();
  await sleep(10);
  IssueReporter.close();        // schedules a 250ms teardown
  await sleep(20);              // still within the window
  IssueReporter.open();         // re-open before teardown fires
  await sleep(10);
  const modal = document.querySelector(".ir-modal");
  assert(modal.contains(document.activeElement), "focus is inside the re-opened modal");

  await sleep(300);            // let the stale teardown timer fire
  const backdrop = document.querySelector(".ir-backdrop");
  assert(backdrop.classList.contains("ir-backdrop--visible"),
    "re-opened modal stays visible after the stale timer fires");
  assert(backdrop.style.display !== "none", "backdrop was not hidden by the stale timer");
  assert(modal.contains(document.activeElement),
    "focus was not stolen back to the trigger by the stale timer");
}

async function testInspectPreservesRestoreTarget() {
  console.log("inspect mode round-trip preserves the focus-restore target");
  const { window, document, IssueReporter } = setup();
  const trigger = document.querySelector(".ir-btn");
  trigger.focus();
  IssueReporter.open();
  await sleep(10);
  // Advance to step 1 where the inspect button lives.
  document.querySelector(".ir-type-card").dispatchEvent(new window.Event("click", { bubbles: true }));
  document.querySelector(".ir-footer-next").dispatchEvent(new window.Event("click", { bubbles: true }));
  await sleep(60);

  const inspectBtn = document.querySelector(".ir-inspect-btn");
  assert(!!inspectBtn, "inspect button is present on step 1");
  inspectBtn.dispatchEvent(new window.Event("click", { bubbles: true }));
  await sleep(300); // silent close animation

  // Background must be interactive again during inspect (not inert).
  assert(!document.getElementById("main").hasAttribute("inert"),
    "background is NOT inert while inspecting the page");

  // Simulate picking a page element (fires the capture-phase click handler → reopens modal).
  document.getElementById("page-btn").dispatchEvent(new window.Event("click", { bubbles: true }));
  await sleep(60);
  assert(document.querySelector(".ir-modal") && isVisible(document), "modal re-opened after capture");

  // Now close for real — focus must go back to the ORIGINAL trigger, not <body>.
  IssueReporter.close();
  await sleep(300);
  assert(document.activeElement === trigger,
    "focus restored to the original trigger after an inspect round-trip");
}

function isVisible(document) {
  const b = document.querySelector(".ir-backdrop");
  return b && b.classList.contains("ir-backdrop--visible");
}

async function testAriaModalWiring() {
  console.log("dialog semantics are present");
  const { document, IssueReporter } = setup();
  IssueReporter.open();
  await sleep(10);
  const modal = document.querySelector(".ir-modal");
  assert(modal.getAttribute("role") === "dialog", 'role="dialog" present');
  assert(modal.getAttribute("aria-modal") === "true", 'aria-modal="true" present');
  assert(modal.getAttribute("tabindex") === "-1", "modal has tabindex=-1 fallback");
}

const run = async () => {
  console.log("\nA11y focus-management tests (issue #26)\n");
  await testAriaModalWiring();
  await testFocusEntersOnStep0();
  await testTabTrap();
  await testBackgroundInert();
  await testFocusRestoredOnClose("Escape", pressEscape);
  await testFocusRestoredOnClose("backdrop click", clickBackdrop);
  await testFocusRestoredOnClose("the ✕ button", clickCloseX);
  await testDoneRestoresFocus();
  await testInspectPreservesRestoreTarget();
  await testReopenDuringCloseAnimation();

  console.log(`\n${passed} passed, ${failed} failed\n`);
  process.exit(failed === 0 ? 0 : 1);
};

run();
