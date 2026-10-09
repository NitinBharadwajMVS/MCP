// Piano Music MCP - Multi-Tool Frontend Client

document.addEventListener("DOMContentLoaded", () => {
  // Tab Management
  const tabBtns = document.querySelectorAll(".tab-btn");
  const formSections = {
    get_chord: document.getElementById("form-get_chord"),
    get_scale: document.getElementById("form-get_scale"),
    transpose_chord: document.getElementById("form-transpose_chord"),
    search_music: document.getElementById("form-search_music"),
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

  // Elements: search_music
  const musicSearchInput = document.getElementById("music-search-input");
  const searchMusicBtn = document.getElementById("search-music-btn");

  // Results & Errors
  const resultsSection = document.getElementById("results-section");
  const errorBanner = document.getElementById("error-banner");
  const errorText = document.getElementById("error-text");

  const resultTitle = document.getElementById("result-title");
  const resultBadge1 = document.getElementById("result-badge-1");
  const resultBadge2 = document.getElementById("result-badge-2");
  const resultToolTag = document.getElementById("result-tool-tag");

  const musicResultsContainer = document.getElementById("music-results-container");
  const songDetailsContainer = document.getElementById("song-details-container");
  const theoryResultsWrapper = document.getElementById("theory-results-wrapper");

  // Song Details Elements
  const backToResultsBtn = document.getElementById("back-to-results-btn");
  const detailsRecordingId = document.getElementById("details-recording-id");
  const detailSongTitle = document.getElementById("detail-song-title");
  const detailArtistName = document.getElementById("detail-artist-name");
  const detailDurationBadge = document.getElementById("detail-duration-badge");
  const detailFirstReleaseBadge = document.getElementById("detail-first-release-badge");
  const detailComposers = document.getElementById("detail-composers");
  const detailLyricists = document.getElementById("detail-lyricists");
  const detailWork = document.getElementById("detail-work");
  const detailCompDate = document.getElementById("detail-comp-date");
  const detailPerfArtist = document.getElementById("detail-perf-artist");
  const detailPerfDate = document.getElementById("detail-perf-date");
  const detailFirstRel = document.getElementById("detail-first-rel");
  const detailDurationText = document.getElementById("detail-duration-text");
  const detailReleasesList = document.getElementById("detail-releases-list");
  const detailRecLink = document.getElementById("detail-rec-link");
  const detailWorkLink = document.getElementById("detail-work-link");
  const detailDataNotes = document.getElementById("detail-data-notes");

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

  searchMusicBtn.addEventListener("click", () => runSearchTool());
  musicSearchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runSearchTool();
  });

  if (backToResultsBtn) {
    backToResultsBtn.addEventListener("click", () => {
      if (songDetailsContainer) songDetailsContainer.classList.add("hidden");
      if (musicResultsContainer) musicResultsContainer.classList.remove("hidden");
      resultTitle.textContent = `"${musicSearchInput.value.trim()}"`;
      resultBadge1.textContent = "Search Results";
      resultBadge1.className = "badge badge-quality";
    });
  }

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

  document.querySelectorAll(".music-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      musicSearchInput.value = pill.dataset.query;
      runSearchTool();
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

  async function runSearchTool() {
    const query = musicSearchInput.value.trim();
    if (!query) {
      showError("Please enter a song title, artist, or album to search.");
      return;
    }

    // Immediate visual feedback in the results panel
    hideError();
    resultTitle.textContent = `Searching for "${query}"...`;
    resultBadge1.textContent = "Querying MCP...";
    resultBadge1.className = "badge badge-quality";
    resultBadge2.classList.add("hidden");
    extraInfoBox.classList.add("hidden");
    if (theoryResultsWrapper) theoryResultsWrapper.classList.add("hidden");
    if (musicResultsContainer) {
      musicResultsContainer.classList.remove("hidden");
      musicResultsContainer.innerHTML = `
        <div class="search-loading-box">
          <span class="inline-loader"></span>
          <span>Searching MusicBrainz via MCP <code>search_music</code> tool...</span>
        </div>
      `;
    }
    resultsSection.classList.remove("hidden");

    await callMcpTool(searchMusicBtn, "search_music", { query, limit: 6 }, (data) => {
      renderMusicResults(data);
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

      if (!response.ok || (data.status && data.status.endsWith("_error")) || data.error) {
        showError(data.error || data.message || "Tool execution failed.");
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
    if (songDetailsContainer) songDetailsContainer.classList.add("hidden");
    if (theoryResultsWrapper) theoryResultsWrapper.classList.remove("hidden");
    if (musicResultsContainer) musicResultsContainer.classList.add("hidden");

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
    if (songDetailsContainer) songDetailsContainer.classList.add("hidden");
    if (theoryResultsWrapper) theoryResultsWrapper.classList.remove("hidden");
    if (musicResultsContainer) musicResultsContainer.classList.add("hidden");

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
    if (songDetailsContainer) songDetailsContainer.classList.add("hidden");
    if (theoryResultsWrapper) theoryResultsWrapper.classList.remove("hidden");
    if (musicResultsContainer) musicResultsContainer.classList.add("hidden");

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

  function renderMusicResults(data) {
    if (songDetailsContainer) songDetailsContainer.classList.add("hidden");
    if (theoryResultsWrapper) theoryResultsWrapper.classList.add("hidden");
    if (musicResultsContainer) musicResultsContainer.classList.remove("hidden");

    const queryDisplay = data.query || musicSearchInput.value.trim();
    resultTitle.textContent = `"${queryDisplay}"`;
    resultBadge2.classList.add("hidden");
    extraInfoBox.classList.add("hidden");

    musicResultsContainer.innerHTML = "";

    if (!data.results || data.results.length === 0 || data.status === "no_results") {
      resultBadge1.textContent = "0 Tracks Found";
      resultBadge1.className = "badge badge-inversion";

      const emptyBox = document.createElement("div");
      emptyBox.className = "empty-results-box";
      emptyBox.innerHTML = `
        <span class="empty-icon">🔎</span>
        <div class="empty-content">
          <h4>No Recordings Found</h4>
          <p>${data.message || `No music recordings matched "${queryDisplay}". Try searching with a broader title, different artist, or check spelling.`}</p>
        </div>
      `;
      musicResultsContainer.appendChild(emptyBox);
    } else {
      resultBadge1.textContent = `${data.count || data.results.length} Track(s) Found`;
      resultBadge1.className = "badge badge-quality";

      data.results.forEach((track) => {
        const card = document.createElement("div");
        card.className = "music-card";
        card.title = "Click to inspect song details & composition provenance";

        const header = document.createElement("div");
        header.className = "music-card-header";

        const titleSpan = document.createElement("span");
        titleSpan.className = "music-title";
        titleSpan.textContent = track.title || "Untitled";
        header.appendChild(titleSpan);

        if (track.length_ms) {
          const totalSec = Math.floor(track.length_ms / 1000);
          const min = Math.floor(totalSec / 60);
          const sec = (totalSec % 60).toString().padStart(2, "0");
          const durSpan = document.createElement("span");
          durSpan.className = "music-duration";
          durSpan.textContent = `⏱️ ${min}:${sec}`;
          header.appendChild(durSpan);
        }
        card.appendChild(header);

        const metaRow = document.createElement("div");
        metaRow.className = "music-meta";

        const artistSpan = document.createElement("span");
        artistSpan.className = "music-artist";
        artistSpan.textContent = `🎤 ${track.artist || "Unknown Artist"}`;
        metaRow.appendChild(artistSpan);

        if (track.release) {
          const albumSpan = document.createElement("span");
          albumSpan.className = "music-album";
          albumSpan.textContent = `💿 ${track.release}${track.release_date ? ` (${track.release_date})` : ""}`;
          metaRow.appendChild(albumSpan);
        } else if (track.release_date) {
          const dateSpan = document.createElement("span");
          dateSpan.className = "music-album";
          dateSpan.textContent = `📅 ${track.release_date}`;
          metaRow.appendChild(dateSpan);
        }
        card.appendChild(metaRow);

        if (track.id) {
          const idRow = document.createElement("div");
          idRow.className = "music-id-row";

          const idLabel = document.createElement("span");
          idLabel.className = "music-id-label";
          idLabel.textContent = "MusicBrainz ID:";

          const idCode = document.createElement("code");
          idCode.className = "music-id-code";
          idCode.textContent = track.id;

          idRow.appendChild(idLabel);
          idRow.appendChild(idCode);
          card.appendChild(idRow);
        }

        const actionRow = document.createElement("div");
        actionRow.className = "music-card-action";
        actionRow.textContent = "✨ Click to inspect song details & composition provenance →";
        card.appendChild(actionRow);

        // Click to inspect details
        card.addEventListener("click", () => {
          if (track.id) {
            loadSongDetails(track.id);
          }
        });

        musicResultsContainer.appendChild(card);
      });
    }

    resultsSection.classList.remove("hidden");
  }

  async function loadSongDetails(recordingId) {
    hideError();
    resultTitle.textContent = "Loading Song Details...";
    resultBadge1.textContent = "Querying MCP...";
    resultBadge1.className = "badge badge-quality";
    resultBadge2.classList.add("hidden");
    extraInfoBox.classList.add("hidden");

    if (musicResultsContainer) musicResultsContainer.classList.add("hidden");
    if (songDetailsContainer) songDetailsContainer.classList.add("hidden");
    if (theoryResultsWrapper) theoryResultsWrapper.classList.add("hidden");

    // Show temporary inline loading indicator
    let loadingBox = document.getElementById("song-details-loading-box");
    if (!loadingBox) {
      loadingBox = document.createElement("div");
      loadingBox.id = "song-details-loading-box";
      loadingBox.className = "search-loading-box";
      loadingBox.innerHTML = `
        <span class="inline-loader"></span>
        <span>Fetching song relationships and composition metadata via MCP <code>get_song_details</code>...</span>
      `;
      resultsSection.appendChild(loadingBox);
    }
    loadingBox.classList.remove("hidden");
    resultsSection.classList.remove("hidden");

    await callMcpTool(searchMusicBtn, "get_song_details", { recording_id: recordingId }, (data) => {
      if (loadingBox) loadingBox.classList.add("hidden");
      renderSongDetails(data);
    });
  }

  function renderSongDetails(data) {
    const loadingBox = document.getElementById("song-details-loading-box");
    if (loadingBox) loadingBox.classList.add("hidden");

    if (theoryResultsWrapper) theoryResultsWrapper.classList.add("hidden");
    if (musicResultsContainer) musicResultsContainer.classList.add("hidden");
    if (songDetailsContainer) songDetailsContainer.classList.remove("hidden");

    resultTitle.textContent = `"${data.title || "Song Details"}"`;
    resultBadge1.textContent = "Song Details";
    resultBadge1.className = "badge badge-quality";
    resultBadge2.classList.add("hidden");
    extraInfoBox.classList.add("hidden");

    // Hero Section
    if (detailsRecordingId) detailsRecordingId.textContent = `MBID: ${data.id}`;
    if (detailSongTitle) detailSongTitle.textContent = data.title || "Untitled";
    if (detailArtistName) detailArtistName.textContent = `🎤 ${data.artist || "Unknown Artist"}`;
    if (detailDurationBadge) {
      detailDurationBadge.textContent = data.duration_formatted ? `⏱️ ${data.duration_formatted}` : "⏱️ Unknown";
    }
    if (detailFirstReleaseBadge) {
      detailFirstReleaseBadge.textContent = data.first_release_date ? `📅 First Release: ${data.first_release_date}` : "📅 First Release: Unknown";
    }

    // Authorship
    if (detailComposers) {
      if (data.composers && data.composers.length > 0) {
        detailComposers.textContent = data.composers.join(", ");
        detailComposers.className = "detail-value";
      } else {
        detailComposers.textContent = "Not documented in MusicBrainz";
        detailComposers.className = "detail-value muted-note";
      }
    }

    if (detailLyricists) {
      if (data.lyricists && data.lyricists.length > 0) {
        detailLyricists.textContent = data.lyricists.join(", ");
        detailLyricists.className = "detail-value";
      } else {
        detailLyricists.textContent = "Not documented in MusicBrainz";
        detailLyricists.className = "detail-value muted-note";
      }
    }

    if (detailWork) {
      if (data.work && data.work.title) {
        detailWork.textContent = data.work.title;
        detailWork.className = "detail-value";
      } else {
        detailWork.textContent = "No linked composition work in MusicBrainz";
        detailWork.className = "detail-value muted-note";
      }
    }

    if (detailCompDate) {
      if (data.composition_date) {
        detailCompDate.textContent = data.composition_date;
        detailCompDate.className = "detail-value";
      } else {
        detailCompDate.textContent = "Not documented (distinct from release date)";
        detailCompDate.className = "detail-value muted-note";
      }
    }

    // Performance & Dates
    if (detailPerfArtist) detailPerfArtist.textContent = data.artist || "Unknown Artist";
    if (detailPerfDate) {
      if (data.performance_date) {
        detailPerfDate.textContent = data.performance_date;
        detailPerfDate.className = "detail-value";
      } else {
        detailPerfDate.textContent = "Not documented in MusicBrainz";
        detailPerfDate.className = "detail-value muted-note";
      }
    }
    if (detailFirstRel) detailFirstRel.textContent = data.first_release_date || "Unknown";
    if (detailDurationText) {
      if (data.duration_formatted) {
        detailDurationText.textContent = `${data.duration_formatted} (${data.duration_ms ? data.duration_ms.toLocaleString() : 0} ms)`;
      } else {
        detailDurationText.textContent = "Unknown";
      }
    }

    // Releases List
    if (detailReleasesList) {
      detailReleasesList.innerHTML = "";
      if (data.releases && data.releases.length > 0) {
        data.releases.forEach((rel) => {
          const item = document.createElement("div");
          item.className = "release-item";

          const titleSpan = document.createElement("span");
          titleSpan.className = "release-item-title";
          titleSpan.textContent = `💿 ${rel.title}`;
          item.appendChild(titleSpan);

          const badgesDiv = document.createElement("div");
          badgesDiv.className = "release-item-badges";

          if (rel.date) {
            const dateB = document.createElement("span");
            dateB.className = "mini-badge";
            dateB.textContent = rel.date;
            badgesDiv.appendChild(dateB);
          }

          if (rel.country) {
            const countryB = document.createElement("span");
            countryB.className = "mini-badge";
            countryB.textContent = rel.country;
            badgesDiv.appendChild(countryB);
          }

          if (rel.format) {
            const formatB = document.createElement("span");
            formatB.className = "mini-badge";
            formatB.textContent = rel.format;
            badgesDiv.appendChild(formatB);
          }

          item.appendChild(badgesDiv);
          detailReleasesList.appendChild(item);
        });
      } else {
        detailReleasesList.innerHTML = '<div class="detail-value muted-note">No documented album releases found.</div>';
      }
    }

    // Provenance Links & Data Notes
    if (detailRecLink) {
      detailRecLink.href = data.source_url || `https://musicbrainz.org/recording/${data.id}`;
    }

    if (detailWorkLink) {
      if (data.work && data.work.url) {
        detailWorkLink.href = data.work.url;
        detailWorkLink.classList.remove("hidden");
      } else {
        detailWorkLink.classList.add("hidden");
      }
    }

    if (detailDataNotes) {
      const notes = data.data_notes || {};
      const noteKeys = Object.keys(notes);
      if (noteKeys.length > 0) {
        detailDataNotes.classList.remove("hidden");
        detailDataNotes.innerHTML = `<strong>Data Verification Notes:</strong><ul style="margin: 6px 0 0 16px; padding: 0;">${noteKeys
          .map((k) => `<li>${notes[k]}</li>`)
          .join("")}</ul>`;
      } else {
        detailDataNotes.classList.add("hidden");
      }
    }

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
