// Piano Music MCP - Multi-Tool Frontend Client

document.addEventListener("DOMContentLoaded", () => {
  // Tab Management
  const tabBtns = document.querySelectorAll(".tab-btn");
  const formSections = {
    get_chord: document.getElementById("form-get_chord"),
    get_scale: document.getElementById("form-get_scale"),
    transpose_chord: document.getElementById("form-transpose_chord"),
  };

  let currentTool = "get_chord";

  // Elements: get_chord
  const chordInput = document.getElementById("chord-input");
  const analyzeChordBtn = document.getElementById("analyze-chord-btn");

  // Elements: get_scale
  const scaleRootInput = document.getElementById("scale-root-input");
  const scaleTypeSelect = document.getElementById("scale-type-select");
  const exploreScaleBtn = document.getElementById("explore-scale-btn");

  // Elements: transpose_chord
  const transposeChordInput = document.getElementById("transpose-chord-input");
  const transposeSemitonesInput = document.getElementById("transpose-semitones-input");
  const transposeBtn = document.getElementById("transpose-btn");

  // Results & Errors
  const resultsSection = document.getElementById("results-section");
  const errorBanner = document.getElementById("error-banner");
  const errorText = document.getElementById("error-text");

  const resultTitle = document.getElementById("result-title");
  const resultBadge1 = document.getElementById("result-badge-1");
  const resultBadge2 = document.getElementById("result-badge-2");
  const resultToolTag = document.getElementById("result-tool-tag");

  const notesContainer = document.getElementById("notes-container");
  const formulaContainer = document.getElementById("formula-container");
  const intervalsContainer = document.getElementById("intervals-container");
  const extraInfoBox = document.getElementById("extra-info-box");
  const extraInfoText = document.getElementById("extra-info-text");

  const toolsStatus = document.getElementById("tools-status");

  // 1. Initial Tool Discovery from MCP Server
  discoverTools();

  // 2. Tab Navigation
  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      currentTool = btn.dataset.tool;
      Object.entries(formSections).forEach(([name, el]) => {
        if (name === currentTool) {
          el.classList.remove("hidden");
        } else {
          el.classList.add("hidden");
        }
      });

      hideError();
    });
  });

  // 3. Tool Triggers
  analyzeChordBtn.addEventListener("click", () => runChordTool());
  chordInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runChordTool();
  });

  exploreScaleBtn.addEventListener("click", () => runScaleTool());
  scaleRootInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runScaleTool();
  });

  transposeBtn.addEventListener("click", () => runTransposeTool());
  transposeChordInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runTransposeTool();
  });
  transposeSemitonesInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runTransposeTool();
  });

  // Quick Preset Pills
  document.querySelectorAll(".chord-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      chordInput.value = pill.dataset.val;
      runChordTool();
    });
  });

  document.querySelectorAll(".scale-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      scaleRootInput.value = pill.dataset.root;
      scaleTypeSelect.value = pill.dataset.type;
      runScaleTool();
    });
  });

  document.querySelectorAll(".transpose-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      transposeChordInput.value = pill.dataset.chord;
      transposeSemitonesInput.value = pill.dataset.semi;
      runTransposeTool();
    });
  });

  // Default initial run
  runChordTool();

  // -------------------------------------------------------------
  // Tool Execution Handlers
  // -------------------------------------------------------------

  async function discoverTools() {
    try {
      const resp = await fetch("/api/tools");
      const data = await resp.json();
      if (data.tools && data.tools.length > 0) {
        toolsStatus.textContent = `${data.tools.length} MCP Tools Active`;
      }
    } catch (err) {
      console.warn("Tool discovery error:", err);
    }
  }

  async function runChordTool() {
    const chord = chordInput.value.trim();
    if (!chord) {
      showError("Please enter a chord symbol.");
      return;
    }

    await callMcpTool(analyzeChordBtn, "get_chord", { chord }, (data) => {
      renderChordResults(data);
    });
  }

  async function runScaleTool() {
    const root = scaleRootInput.value.trim();
    const scale_type = scaleTypeSelect.value;
    if (!root) {
      showError("Please enter a root note.");
      return;
    }

    await callMcpTool(exploreScaleBtn, "get_scale", { root, scale_type }, (data) => {
      renderScaleResults(data);
    });
  }

  async function runTransposeTool() {
    const chord = transposeChordInput.value.trim();
    const semitones = parseInt(transposeSemitonesInput.value, 10);
    if (!chord) {
      showError("Please enter a chord symbol to transpose.");
      return;
    }
    if (isNaN(semitones)) {
      showError("Please enter a valid integer for semitones.");
      return;
    }

    await callMcpTool(transposeBtn, "transpose_chord", { chord, semitones }, (data) => {
      renderTransposeResults(data);
    });
  }

  async function callMcpTool(btnElement, toolName, args, onSuccess) {
    setLoading(btnElement, true);
    hideError();

    try {
      const response = await fetch("/api/call-tool", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool: toolName, arguments: args }),
      });

      const data = await response.json();

      if (!response.ok || data.error) {
        showError(data.error || "Tool execution failed.");
        resultsSection.classList.add("hidden");
      } else {
        resultToolTag.textContent = `✓ Tool: ${toolName}`;
        onSuccess(data);
      }
    } catch (err) {
      showError("Network or server connection error: " + err.message);
      resultsSection.classList.add("hidden");
    } finally {
      setLoading(btnElement, false);
    }
  }

  // -------------------------------------------------------------
  // Rendering Results
  // -------------------------------------------------------------

  function renderChordResults(data) {
    resultTitle.textContent = data.chord;
    resultBadge1.textContent = data.quality;
    resultBadge1.className = "badge badge-quality";

    if (data.is_inversion || data.slash_bass) {
      resultBadge2.classList.remove("hidden");
      resultBadge2.textContent = "Inversion";
      extraInfoBox.classList.remove("hidden");
      extraInfoText.textContent = data.inversion_details || `Slash chord over ${data.slash_bass} bass`;
    } else {
      resultBadge2.classList.add("hidden");
      extraInfoBox.classList.add("hidden");
    }

    renderNotes(data.notes || [], data.formula || []);
    renderTheory(data.formula || [], data.intervals_semitones || []);
    resultsSection.classList.remove("hidden");
  }

  function renderScaleResults(data) {
    resultTitle.textContent = data.name;
    resultBadge1.textContent = data.scale_type.toUpperCase();
    resultBadge1.className = "badge badge-inversion";
    resultBadge2.classList.add("hidden");
    extraInfoBox.classList.add("hidden");

    renderNotes(data.notes || [], data.formula || []);
    renderTheory(data.formula || [], data.intervals_semitones || []);
    resultsSection.classList.remove("hidden");
  }

  function renderTransposeResults(data) {
    const analysis = data.analysis || {};
    const sign = data.semitones >= 0 ? `+${data.semitones}` : `${data.semitones}`;

    resultTitle.textContent = data.transposed_chord;
    resultBadge1.textContent = `${sign} semitones`;
    resultBadge1.className = "badge badge-quality";
    resultBadge2.classList.add("hidden");

    extraInfoBox.classList.remove("hidden");
    extraInfoText.textContent = `Transposed from ${data.original_chord} (${analysis.quality || ""}) by ${data.semitones} half-step(s).`;

    renderNotes(analysis.notes || [], analysis.formula || []);
    renderTheory(analysis.formula || [], analysis.intervals_semitones || []);
    resultsSection.classList.remove("hidden");
  }

  function renderNotes(notes, formula) {
    notesContainer.innerHTML = "";
    notes.forEach((note, index) => {
      const card = document.createElement("div");
      card.className = "note-card";

      const letter = document.createElement("span");
      letter.className = "note-letter";
      letter.textContent = note;

      const degree = document.createElement("span");
      degree.className = "note-degree";
      degree.textContent = formula[index] || `deg ${index + 1}`;

      card.appendChild(letter);
      card.appendChild(degree);
      notesContainer.appendChild(card);
    });
  }

  function renderTheory(formula, intervals) {
    formulaContainer.innerHTML = "";
    formula.forEach((deg) => {
      const tag = document.createElement("span");
      tag.className = "theory-tag";
      tag.textContent = deg;
      formulaContainer.appendChild(tag);
    });

    intervalsContainer.innerHTML = "";
    intervals.forEach((semi) => {
      const tag = document.createElement("span");
      tag.className = "theory-tag";
      tag.textContent = `+${semi} st`;
      intervalsContainer.appendChild(tag);
    });
  }

  function setLoading(btnElement, isLoading) {
    const text = btnElement.querySelector(".btn-text");
    const loader = btnElement.querySelector(".btn-loader");
    if (isLoading) {
      text.classList.add("hidden");
      loader.classList.remove("hidden");
      btnElement.disabled = true;
    } else {
      text.classList.remove("hidden");
      loader.classList.add("hidden");
      btnElement.disabled = false;
    }
  }

  function showError(message) {
    errorText.textContent = message;
    errorBanner.classList.remove("hidden");
  }

  function hideError() {
    errorBanner.classList.add("hidden");
  }
});
