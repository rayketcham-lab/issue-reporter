/**
 * issue-reporter.js — Embeddable GitHub issue reporter widget
 *
 * Drop a single <script> tag on any page to add a floating feedback button
 * that creates structured GitHub issues via a lightweight backend server.
 *
 * No dependencies. No framework. No build step.
 *
 * Usage (minimal):
 *   <script src="issue-reporter.js"></script>
 *   <script>
 *     IssueReporter.init({ endpoint: "https://your-server.com/api/report" });
 *   </script>
 *
 * Usage (all options):
 *   IssueReporter.init({
 *     endpoint: "https://your-server.com/api/report",
 *     projectName: "My App",
 *     position: "bottom-right",       // "bottom-right" or "bottom-left"
 *     buttonText: "Report Issue",
 *     issueTypes: [
 *       { id: "bug", label: "Bug Report" },
 *       { id: "feature_request", label: "Feature Request" },
 *     ],
 *     token: "optional-auth-token",   // sent as Authorization: Bearer header
 *   });
 *
 * @license MIT
 * @see https://github.com/rayketcham-lab/issue-reporter
 */
(function () {
  "use strict";

  // Guard against double-init
  if (window.IssueReporter && window.IssueReporter._initialized) {
    return;
  }

  // -------------------------------------------------------------------------
  // Default configuration
  // -------------------------------------------------------------------------

  var DEFAULTS = {
    endpoint: "",
    projectName: "",
    position: "bottom-right",
    buttonText: "Report Issue",
    issueTypes: [
      { id: "bug", label: "Bug Report" },
      { id: "feature_request", label: "Feature Request" },
      { id: "data_issue", label: "Data Issue" },
      { id: "ui_bug", label: "UI / Display Bug" },
      { id: "performance", label: "Performance" },
      { id: "other", label: "Other" },
    ],
    token: "",
  };

  var config = {};
  var modalEl = null;
  var backdropEl = null;
  var buttonEl = null;

  // -------------------------------------------------------------------------
  // SVG icon (hardcoded, safe — no user input)
  // -------------------------------------------------------------------------

  var BUG_ICON_SVG = '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">' +
    '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 ' +
    '15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>';

  // -------------------------------------------------------------------------
  // CSS — scoped under .ir- prefix to avoid conflicts
  // -------------------------------------------------------------------------

  var CSS = (
    /* Floating trigger button */
    ".ir-btn{" +
      "position:fixed;z-index:2147483646;" +
      "display:flex;align-items:center;gap:6px;" +
      "padding:10px 18px;border:none;border-radius:8px;" +
      "background:#1a1a2e;color:#fff;font:600 14px/1 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;" +
      "cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.25);transition:background .15s,transform .15s;" +
    "}" +
    ".ir-btn:hover{background:#16213e;transform:translateY(-1px);}" +
    ".ir-btn:active{transform:translateY(0);}" +
    ".ir-btn svg{width:16px;height:16px;fill:currentColor;flex-shrink:0;}" +
    ".ir-btn--br{bottom:20px;right:20px;}" +
    ".ir-btn--bl{bottom:20px;left:20px;}" +

    /* Backdrop */
    ".ir-backdrop{" +
      "position:fixed;inset:0;z-index:2147483647;" +
      "background:rgba(0,0,0,.4);display:flex;align-items:center;justify-content:center;" +
      "opacity:0;transition:opacity .2s;" +
    "}" +
    ".ir-backdrop--visible{opacity:1;}" +

    /* Modal */
    ".ir-modal{" +
      "background:#fff;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,.3);" +
      "width:90%;max-width:480px;max-height:90vh;overflow-y:auto;" +
      "font:400 14px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;" +
      "color:#1a1a2e;transform:translateY(12px);transition:transform .2s;" +
    "}" +
    ".ir-backdrop--visible .ir-modal{transform:translateY(0);}" +

    /* Header */
    ".ir-header{" +
      "display:flex;align-items:center;justify-content:space-between;" +
      "padding:20px 24px 0;" +
    "}" +
    ".ir-header h2{margin:0;font-size:18px;font-weight:700;color:#1a1a2e;}" +
    ".ir-close{" +
      "background:none;border:none;cursor:pointer;padding:4px;" +
      "color:#888;font-size:20px;line-height:1;" +
    "}" +
    ".ir-close:hover{color:#333;}" +

    /* Form */
    ".ir-form{padding:16px 24px 24px;}" +
    ".ir-field{margin-bottom:14px;}" +
    ".ir-field label{display:block;margin-bottom:4px;font-weight:600;font-size:13px;color:#444;}" +
    ".ir-field select,.ir-field textarea,.ir-field input[type=text]{" +
      "width:100%;padding:8px 10px;border:1px solid #d1d5db;border-radius:6px;" +
      "font:inherit;font-size:14px;color:#1a1a2e;background:#fafafa;" +
      "box-sizing:border-box;transition:border-color .15s;" +
    "}" +
    ".ir-field select:focus,.ir-field textarea:focus,.ir-field input[type=text]:focus{" +
      "outline:none;border-color:#3b82f6;background:#fff;" +
    "}" +
    ".ir-field textarea{resize:vertical;min-height:100px;}" +

    /* Severity pills */
    ".ir-severity{display:flex;gap:6px;flex-wrap:wrap;}" +
    ".ir-severity label{" +
      "display:inline-flex;align-items:center;gap:4px;" +
      "padding:5px 12px;border:1px solid #d1d5db;border-radius:20px;" +
      "cursor:pointer;font-size:13px;font-weight:500;color:#555;transition:all .15s;" +
      "user-select:none;" +
    "}" +
    ".ir-severity input{display:none;}" +
    ".ir-severity input:checked+span{}" +
    ".ir-severity label:has(input:checked){border-color:#3b82f6;background:#eff6ff;color:#1d4ed8;}" +

    /* Buttons row */
    ".ir-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:18px;}" +
    ".ir-actions button{" +
      "padding:9px 20px;border-radius:6px;font:600 14px/1 inherit;cursor:pointer;transition:all .15s;" +
    "}" +
    ".ir-submit{background:#1a1a2e;color:#fff;border:none;}" +
    ".ir-submit:hover:not(:disabled){background:#16213e;}" +
    ".ir-submit:disabled{opacity:.5;cursor:not-allowed;}" +
    ".ir-cancel{background:#fff;color:#555;border:1px solid #d1d5db;}" +
    ".ir-cancel:hover{background:#f9fafb;}" +

    /* Status messages */
    ".ir-status{padding:16px 24px 24px;text-align:center;}" +
    ".ir-status p{margin:8px 0;}" +
    ".ir-status a{color:#3b82f6;text-decoration:underline;}" +
    ".ir-status .ir-icon{font-size:36px;margin-bottom:4px;}" +
    ".ir-status--success .ir-icon{color:#16a34a;}" +
    ".ir-status--error .ir-icon{color:#dc2626;}" +
    ".ir-status button{" +
      "margin-top:12px;padding:8px 20px;border-radius:6px;border:1px solid #d1d5db;" +
      "background:#fff;cursor:pointer;font:600 14px/1 inherit;color:#555;" +
    "}" +
    ".ir-status button:hover{background:#f9fafb;}" +

    /* Spinner */
    ".ir-spinner{" +
      "display:inline-block;width:24px;height:24px;" +
      "border:3px solid #e5e7eb;border-top-color:#3b82f6;border-radius:50%;" +
      "animation:ir-spin .6s linear infinite;" +
    "}" +
    "@keyframes ir-spin{to{transform:rotate(360deg);}}" +

    /* Mobile */
    "@media(max-width:500px){" +
      ".ir-modal{width:96%;max-width:none;margin:8px;border-radius:10px;}" +
      ".ir-form{padding:14px 18px 18px;}" +
      ".ir-header{padding:16px 18px 0;}" +
    "}"
  );

  // -------------------------------------------------------------------------
  // CSS injection
  // -------------------------------------------------------------------------

  function injectStyles() {
    if (document.getElementById("ir-styles")) {
      return;
    }
    var style = document.createElement("style");
    style.id = "ir-styles";
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  // -------------------------------------------------------------------------
  // DOM helpers
  // -------------------------------------------------------------------------

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (key) {
        if (key === "className") {
          node.className = attrs[key];
        } else if (key.indexOf("on") === 0) {
          node.addEventListener(key.slice(2).toLowerCase(), attrs[key]);
        } else if (key === "htmlFor") {
          node.setAttribute("for", attrs[key]);
        } else {
          node.setAttribute(key, attrs[key]);
        }
      });
    }
    if (children) {
      if (!Array.isArray(children)) {
        children = [children];
      }
      children.forEach(function (child) {
        if (typeof child === "string") {
          node.appendChild(document.createTextNode(child));
        } else if (child) {
          node.appendChild(child);
        }
      });
    }
    return node;
  }

  /** Remove all child nodes from an element (safe alternative to innerHTML = "") */
  function clearChildren(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  // -------------------------------------------------------------------------
  // Build floating button
  // -------------------------------------------------------------------------

  function createButton() {
    var posClass = config.position === "bottom-left" ? "ir-btn--bl" : "ir-btn--br";

    buttonEl = el("button", {
      className: "ir-btn " + posClass,
      onClick: openModal,
      "aria-label": config.buttonText,
      type: "button",
    });

    // Icon — built from a hardcoded constant, not user input
    var iconContainer = document.createElement("span");
    iconContainer.innerHTML = BUG_ICON_SVG; // safe: hardcoded SVG constant
    if (iconContainer.firstChild) {
      buttonEl.appendChild(iconContainer.firstChild);
    }

    buttonEl.appendChild(document.createTextNode(" " + config.buttonText));
    document.body.appendChild(buttonEl);
  }

  // -------------------------------------------------------------------------
  // Build modal
  // -------------------------------------------------------------------------

  function buildTypeOptions() {
    return config.issueTypes.map(function (t) {
      return el("option", { value: t.id }, t.label);
    });
  }

  function buildSeverityPills() {
    var severities = ["low", "medium", "high", "critical"];
    return severities.map(function (sev) {
      var radio = el("input", {
        type: "radio",
        name: "ir-severity",
        value: sev,
        id: "ir-sev-" + sev,
      });
      if (sev === "medium") {
        radio.checked = true;
      }
      var span = el("span", null, sev.charAt(0).toUpperCase() + sev.slice(1));
      return el("label", { htmlFor: "ir-sev-" + sev }, [radio, span]);
    });
  }

  function buildForm() {
    var typeSelect = el("select", { id: "ir-type" }, buildTypeOptions());

    var descArea = el("textarea", {
      id: "ir-desc",
      placeholder: "Describe the issue...",
      "aria-label": "Description",
    });

    var contextInput = el("input", {
      type: "text",
      id: "ir-context",
      placeholder: "Page URL, steps to reproduce, etc. (optional)",
      "aria-label": "Context",
    });

    var submitBtn = el("button", {
      className: "ir-submit",
      type: "submit",
    }, "Submit");

    var cancelBtn = el("button", {
      className: "ir-cancel",
      type: "button",
      onClick: closeModal,
    }, "Cancel");

    var form = el("form", {
      className: "ir-form",
      onSubmit: handleSubmit,
    }, [
      el("div", { className: "ir-field" }, [
        el("label", { htmlFor: "ir-type" }, "Issue Type"),
        typeSelect,
      ]),
      el("div", { className: "ir-field" }, [
        el("label", null, "Severity"),
        el("div", { className: "ir-severity" }, buildSeverityPills()),
      ]),
      el("div", { className: "ir-field" }, [
        el("label", { htmlFor: "ir-desc" }, "Description"),
        descArea,
      ]),
      el("div", { className: "ir-field" }, [
        el("label", { htmlFor: "ir-context" }, "Context"),
        contextInput,
      ]),
      el("div", { className: "ir-actions" }, [cancelBtn, submitBtn]),
    ]);

    return form;
  }

  function createModal() {
    var titleText = "Report an Issue";
    if (config.projectName) {
      titleText = "Report Issue \u2014 " + config.projectName;
    }

    var closeBtn = el("button", {
      className: "ir-close",
      onClick: closeModal,
      "aria-label": "Close",
      type: "button",
    }, "\u2715");

    var header = el("div", { className: "ir-header" }, [
      el("h2", null, titleText),
      closeBtn,
    ]);

    var formContent = el("div", { id: "ir-content" }, [buildForm()]);

    modalEl = el("div", { className: "ir-modal", role: "dialog", "aria-modal": "true" }, [
      header,
      formContent,
    ]);

    backdropEl = el("div", {
      className: "ir-backdrop",
      onClick: function (e) {
        if (e.target === backdropEl) {
          closeModal();
        }
      },
    }, [modalEl]);

    document.body.appendChild(backdropEl);
  }

  // -------------------------------------------------------------------------
  // Modal open / close
  // -------------------------------------------------------------------------

  function openModal() {
    if (!modalEl) {
      createModal();
    }
    // Reset form to initial state
    var content = document.getElementById("ir-content");
    clearChildren(content);
    content.appendChild(buildForm());

    backdropEl.style.display = "flex";
    // Force reflow before adding visible class for animation
    void backdropEl.offsetHeight;
    backdropEl.classList.add("ir-backdrop--visible");
    buttonEl.style.display = "none";

    // Focus the description field after transition
    setTimeout(function () {
      var desc = document.getElementById("ir-desc");
      if (desc) {
        desc.focus();
      }
    }, 200);
  }

  function closeModal() {
    if (!backdropEl) {
      return;
    }
    backdropEl.classList.remove("ir-backdrop--visible");
    setTimeout(function () {
      backdropEl.style.display = "none";
      buttonEl.style.display = "";
    }, 200);
  }

  // -------------------------------------------------------------------------
  // Form submission
  // -------------------------------------------------------------------------

  function handleSubmit(e) {
    e.preventDefault();

    var typeEl = document.getElementById("ir-type");
    var descEl = document.getElementById("ir-desc");
    var contextEl = document.getElementById("ir-context");
    var sevEl = document.querySelector('input[name="ir-severity"]:checked');

    var description = (descEl.value || "").trim();
    if (!description) {
      descEl.style.borderColor = "#dc2626";
      descEl.focus();
      return;
    }

    if (!config.endpoint) {
      showError("No endpoint configured. Call IssueReporter.init({ endpoint: '...' }).");
      return;
    }

    var payload = {
      type: typeEl.value,
      severity: sevEl ? sevEl.value : "medium",
      description: description,
      context: (contextEl.value || "").trim(),
      project_name: config.projectName || "",
      page_url: window.location.href,
    };

    showLoading();

    var headers = { "Content-Type": "application/json" };
    if (config.token) {
      headers["Authorization"] = "Bearer " + config.token;
    }

    fetch(config.endpoint, {
      method: "POST",
      headers: headers,
      body: JSON.stringify(payload),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (result.ok && result.data.success) {
          showSuccess(result.data.url);
        } else {
          showError(result.data.error || "Server returned an error.");
        }
      })
      .catch(function (err) {
        showError("Network error: " + err.message);
      });
  }

  // -------------------------------------------------------------------------
  // Status screens (loading, success, error)
  // -------------------------------------------------------------------------

  function showLoading() {
    var content = document.getElementById("ir-content");
    clearChildren(content);
    content.appendChild(
      el("div", { className: "ir-status" }, [
        el("div", { className: "ir-spinner" }),
        el("p", null, "Submitting..."),
      ])
    );
  }

  function showSuccess(url) {
    var content = document.getElementById("ir-content");
    clearChildren(content);

    var children = [
      el("div", { className: "ir-icon" }, "\u2713"),
      el("p", { style: "font-weight:600;font-size:16px;" }, "Issue created!"),
    ];

    if (url) {
      children.push(
        el("p", null, [
          el("a", { href: url, target: "_blank", rel: "noopener" }, "View on GitHub"),
        ])
      );
    }

    children.push(
      el("button", { onClick: closeModal, type: "button" }, "Close")
    );

    content.appendChild(
      el("div", { className: "ir-status ir-status--success" }, children)
    );
  }

  function showError(message) {
    var content = document.getElementById("ir-content");
    clearChildren(content);
    content.appendChild(
      el("div", { className: "ir-status ir-status--error" }, [
        el("div", { className: "ir-icon" }, "\u2717"),
        el("p", { style: "font-weight:600;font-size:16px;" }, "Something went wrong"),
        el("p", { style: "color:#666;font-size:13px;" }, message),
        el("button", { onClick: openModal, type: "button" }, "Try Again"),
      ])
    );
  }

  // -------------------------------------------------------------------------
  // Keyboard handling
  // -------------------------------------------------------------------------

  function handleKeydown(e) {
    if (e.key === "Escape" && backdropEl && backdropEl.classList.contains("ir-backdrop--visible")) {
      closeModal();
    }
  }

  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------

  window.IssueReporter = {
    _initialized: false,

    /**
     * Initialize the issue reporter widget.
     * @param {Object} options - Configuration options
     * @param {string} options.endpoint - Backend URL to POST reports to (required)
     * @param {string} [options.projectName] - Project name shown in modal header
     * @param {string} [options.position="bottom-right"] - Button position: "bottom-right" or "bottom-left"
     * @param {string} [options.buttonText="Report Issue"] - Floating button text
     * @param {Array}  [options.issueTypes] - Array of {id, label} objects for the type dropdown
     * @param {string} [options.token] - Auth token sent as Bearer header
     */
    init: function (options) {
      if (this._initialized) {
        console.warn("IssueReporter.init() called more than once. Ignoring.");
        return;
      }

      options = options || {};
      config = {
        endpoint: options.endpoint || DEFAULTS.endpoint,
        projectName: options.projectName || DEFAULTS.projectName,
        position: options.position || DEFAULTS.position,
        buttonText: options.buttonText || DEFAULTS.buttonText,
        issueTypes: options.issueTypes || DEFAULTS.issueTypes,
        token: options.token || DEFAULTS.token,
      };

      if (!config.endpoint) {
        console.error(
          "IssueReporter: endpoint is required. " +
          'Call IssueReporter.init({ endpoint: "https://..." }).'
        );
        return;
      }

      injectStyles();
      document.addEventListener("keydown", handleKeydown);

      // Wait for DOM to be ready
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", createButton);
      } else {
        createButton();
      }

      this._initialized = true;
    },

    /** Open the modal programmatically. */
    open: function () {
      if (!this._initialized) {
        console.error("IssueReporter: call init() first.");
        return;
      }
      openModal();
    },

    /** Close the modal programmatically. */
    close: function () {
      closeModal();
    },

    /** Remove the widget from the page entirely. */
    destroy: function () {
      if (buttonEl && buttonEl.parentNode) {
        buttonEl.parentNode.removeChild(buttonEl);
      }
      if (backdropEl && backdropEl.parentNode) {
        backdropEl.parentNode.removeChild(backdropEl);
      }
      var styleEl = document.getElementById("ir-styles");
      if (styleEl) {
        styleEl.parentNode.removeChild(styleEl);
      }
      document.removeEventListener("keydown", handleKeydown);
      buttonEl = null;
      modalEl = null;
      backdropEl = null;
      config = {};
      this._initialized = false;
    },
  };
})();
