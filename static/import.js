// Upload tickets on the list page.
// The file is read in the browser, then each ticket is posted to /tickets/import on its own.
// Waiting for one before sending the next means every row appears as soon as it is triaged.
(function () {
  "use strict";

  const panel = document.querySelector(".import-panel");
  if (!panel) return;

  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("import-file");
  const statusBox = document.getElementById("import-status");
  const progressText = document.getElementById("import-progress");
  const progressBar = document.getElementById("import-bar");
  const problemList = document.getElementById("import-problems");
  const tableWrap = document.getElementById("ticket-table-wrap");
  const rows = document.getElementById("ticket-rows");

  const maxTickets = Number(panel.dataset.maxTickets);
  const maxBytes = Number(panel.dataset.maxBytes);
  const sortByPriority = panel.dataset.sort === "priority";

  // Send the current filters so the server can say whether a new ticket belongs in this view.
  const query = new URLSearchParams();
  for (const key of ["status", "priority", "category"]) {
    if (panel.dataset[key]) query.set(key, panel.dataset[key]);
  }
  const importUrl = panel.dataset.importUrl + (query.toString() ? "?" + query : "");

  let busy = false;

  // ---- Drag and drop ----
  // Stop the browser from opening a file dropped anywhere else on the page.
  window.addEventListener("dragover", (e) => e.preventDefault());
  window.addEventListener("drop", (e) => e.preventDefault());

  ["dragenter", "dragover"].forEach((type) =>
    dropZone.addEventListener(type, (e) => {
      e.preventDefault();
      if (!busy) dropZone.classList.add("is-dragover");
    })
  );
  ["dragleave", "dragend", "drop"].forEach((type) =>
    dropZone.addEventListener(type, () => dropZone.classList.remove("is-dragover"))
  );
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    const files = e.dataTransfer && e.dataTransfer.files;
    if (!files || files.length === 0) return;
    if (files.length > 1) {
      showOnlyMessage("Please drop one JSON file at a time.");
      return;
    }
    handleFile(files[0]);
  });
  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) handleFile(fileInput.files[0]);
    fileInput.value = ""; // allow choosing the same file again
  });

  window.addEventListener("beforeunload", (e) => {
    if (busy) {
      e.preventDefault();
      e.returnValue = ""; // the browser shows its own "leave page?" message
    }
  });

  // ---- Reading the file ----
  async function handleFile(file) {
    if (busy) return;

    if (!/\.json$/i.test(file.name) && file.type !== "application/json") {
      showOnlyMessage(`"${file.name}" is not a JSON file. Please upload a .json file.`);
      return;
    }
    if (file.size > maxBytes) {
      showOnlyMessage(`The file is too large (${formatKB(file.size)}). The limit is ${formatKB(maxBytes)}.`);
      return;
    }

    let tickets;
    try {
      tickets = JSON.parse(await file.text());
    } catch (err) {
      showOnlyMessage(`"${file.name}" is not valid JSON: ${err.message}`);
      return;
    }
    if (!Array.isArray(tickets)) {
      showOnlyMessage("The file must contain a list of tickets, like [ { ... }, { ... } ].");
      return;
    }
    if (tickets.length === 0) {
      showOnlyMessage("The file has no tickets in it.");
      return;
    }
    if (tickets.length > maxTickets) {
      showOnlyMessage(`The file has ${tickets.length} tickets. Please upload ${maxTickets} or fewer at a time.`);
      return;
    }

    await importTickets(tickets);
  }

  // ---- Sending tickets one at a time ----
  async function importTickets(tickets) {
    setBusy(true);
    problemList.replaceChildren();
    statusBox.hidden = false;
    progressBar.max = tickets.length;
    progressBar.value = 0;

    const totals = { added: 0, skipped: 0, problems: 0, hidden: 0, ai: 0, rules: 0 };
    let stoppedAt = null;

    for (let i = 0; i < tickets.length; i++) {
      const number = i + 1;
      const subject = ticketSubject(tickets[i]);
      progressText.textContent =
        `Triaging ticket ${number} of ${tickets.length}` + (subject ? `: ${subject}` : "") + "…";

      let response, data;
      try {
        response = await fetch(importUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify(tickets[i]),
        });
      } catch (err) {
        stoppedAt = number; // the server is not reachable: every later ticket would fail too
        break;
      }
      try {
        data = await response.json();
      } catch (err) {
        data = null;
      }

      if (data && data.result === "added") {
        totals.added++;
        totals[data.triage_source === "ai" ? "ai" : "rules"]++;
        if (data.matches_filters) {
          insertRow(data.row_html);
        } else {
          totals.hidden++;
        }
        updateCounts(data.open_counts);
      } else if (data && data.result === "skipped") {
        totals.skipped++;
      } else if (data && data.result === "invalid") {
        totals.problems++;
        addProblem(number, subject, (data.messages || Object.values(data.errors)).join(" "));
      } else {
        totals.problems++;
        addProblem(number, subject, `The server could not save this ticket (error ${response.status}).`);
      }
      progressBar.value = number;
    }

    progressText.textContent = summaryText(totals, tickets.length, stoppedAt);
    setBusy(false);
  }

  // ---- Putting a row in the table ----
  function insertRow(html) {
    const template = document.createElement("template");
    template.innerHTML = html.trim(); // rendered and escaped by Flask
    const row = template.content.firstElementChild;

    // Keep the list in its current sort order.
    const next = Array.from(rows.children).find((existing) => comesBefore(row, existing));
    rows.insertBefore(row, next || null);

    tableWrap.hidden = false;
    const empty = document.getElementById("empty-state");
    if (empty) empty.remove();

    row.classList.add("row-new");
    setTimeout(() => row.classList.remove("row-new"), 4000);
  }

  // Same order as db.list_tickets: newest first, or priority first then newest.
  function comesBefore(a, b) {
    if (sortByPriority) {
      const rankA = Number(a.dataset.rank);
      const rankB = Number(b.dataset.rank);
      if (rankA !== rankB) return rankA < rankB;
    }
    if (a.dataset.created !== b.dataset.created) return a.dataset.created > b.dataset.created;
    return Number(a.dataset.id) > Number(b.dataset.id);
  }

  function updateCounts(counts) {
    if (!counts) return;
    document.querySelectorAll(".summary-count[data-priority]").forEach((el) => {
      const value = counts[el.dataset.priority];
      if (value !== undefined) el.textContent = value;
    });
  }

  // ---- Messages ----
  function summaryText(t, total, stoppedAt) {
    const parts = [];
    if (stoppedAt) {
      parts.push(`Stopped at ticket ${stoppedAt} of ${total}: the server could not be reached.`);
    } else {
      parts.push(`Done. ${total} ticket${total === 1 ? "" : "s"} in the file.`);
    }
    parts.push(`${t.added} added`);
    if (t.added) parts.push(`(${t.ai} triaged by the AI, ${t.rules} by keyword rules)`);
    parts.push(`· ${t.skipped} skipped as already in the list · ${t.problems} with problems.`);
    if (t.hidden) {
      parts.push(`${t.hidden} added ticket${t.hidden === 1 ? " is" : "s are"} hidden by the current filters.`);
    }
    return parts.join(" ");
  }

  function addProblem(number, subject, message) {
    const li = document.createElement("li");
    li.textContent = `Ticket ${number}${subject ? ` (${subject})` : ""}: ${message}`;
    problemList.appendChild(li);
  }

  function showOnlyMessage(message) {
    problemList.replaceChildren();
    progressBar.value = 0;
    statusBox.hidden = false;
    progressText.textContent = message;
  }

  function setBusy(value) {
    busy = value;
    fileInput.disabled = value;
    dropZone.classList.toggle("is-busy", value);
    dropZone.setAttribute("aria-disabled", String(value));
  }

  function ticketSubject(ticket) {
    return ticket && typeof ticket.subject === "string" ? ticket.subject.trim().slice(0, 80) : "";
  }

  function formatKB(bytes) {
    return `${Math.round(bytes / 1024)} KB`;
  }
})();