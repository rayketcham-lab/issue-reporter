// Security regression test: the fetch-capture wrapper must not leak query
// strings (which can carry secrets like ?token=) into the submitted issue.
//
// Run: node tests/fetch_capture_redaction.test.mjs   (needs jsdom)

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { JSDOM } from "jsdom";

const here = dirname(fileURLToPath(import.meta.url));
const widgetSrc = readFileSync(join(here, "..", "issue-reporter.js"), "utf8");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let passed = 0, failed = 0;
function assert(cond, msg) {
  if (cond) { passed++; console.log("  ✓ " + msg); }
  else { failed++; console.error("  ✗ " + msg); }
}

async function run() {
  console.log("\nfetch-capture query-string redaction (security)\n");

  const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", {
    url: "https://app.test/", runScripts: "outside-only", pretendToBeVisual: true,
  });
  const { window } = dom;

  // A host-app fetch that the widget's capture wrapper will wrap. Returns a
  // minimal Response-like object with clone().text().
  window.fetch = function () {
    return Promise.resolve({
      status: 200,
      clone: function () { return { text: function () { return Promise.resolve("{}"); } }; },
    });
  };

  // Separate recording mock for the widget's OWN submit (bare `fetch` global),
  // capturing the JSON body sent to the GitHub API.
  let sentBody = null;
  const submitFetch = (url, opts) => {
    sentBody = opts && opts.body;
    return Promise.resolve({ ok: true, status: 201, json: () => Promise.resolve({ html_url: "https://github.com/a/b/issues/1" }) });
  };

  const g = ["window", "document", "navigator", "location", "setTimeout", "clearTimeout", "console", "fetch"];
  const fn = new window.Function(...g, widgetSrc + "\n;return window.IssueReporter;");
  const IssueReporter = fn(
    window, window.document, window.navigator, window.location,
    window.setTimeout, window.clearTimeout, window.console, submitFetch
  );
  IssueReporter.init({ github: { repo: "a/b", token: "github_pat_x" }, projectName: "T" });
  window.document.dispatchEvent(new window.Event("DOMContentLoaded", { bubbles: true }));

  // Host app makes an API call with a secret in the query string.
  await window.fetch("/api/session?token=SECRET_TOKEN_123&user=bob");
  await sleep(20); // let the capture's clone().text().then() settle

  // Drive a full submit through the wizard.
  const doc = window.document;
  IssueReporter.open();
  await sleep(10);
  doc.querySelector(".ir-type-card").dispatchEvent(new window.Event("click", { bubbles: true }));
  doc.querySelector(".ir-footer-next").dispatchEvent(new window.Event("click", { bubbles: true }));
  await sleep(60);
  const desc = doc.getElementById("ir-desc");
  desc.value = "A description of the problem here";
  desc.dispatchEvent(new window.Event("input", { bubbles: true }));
  doc.querySelector(".ir-footer-next").dispatchEvent(new window.Event("click", { bubbles: true }));
  await sleep(60);
  doc.querySelector(".ir-footer-submit").dispatchEvent(new window.Event("click", { bubbles: true }));
  await sleep(60);

  assert(sentBody != null, "the widget submitted an issue payload");
  const body = String(sentBody);
  assert(body.indexOf("/api/session") !== -1, "the captured API path is still reported (feature preserved)");
  assert(body.indexOf("SECRET_TOKEN_123") === -1, "the query-string secret is NOT in the issue payload");
  assert(body.indexOf("token=") === -1, "no raw query string leaked into the issue payload");

  console.log(`\n${passed} passed, ${failed} failed\n`);
  process.exit(failed === 0 ? 0 : 1);
}

run();
