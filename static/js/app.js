/* ══════════════════════════════════════════════════════════════════════════════
   Portfolio Tracker — JavaScript
   ══════════════════════════════════════════════════════════════════════════════ */

// ── Modal Management ─────────────────────────────────────────────────────────

function openModal(id) {
  const overlay = document.getElementById('modal-' + id);
  if (overlay) overlay.classList.add('active');
}

function closeModal(id) {
  const overlay = document.getElementById('modal-' + id);
  if (overlay) {
    overlay.classList.remove('active');
    // Reset the strategy import form if closing that modal
    if (id === 'add-strategy') {
      resetStrategyImport();
    }
  }
}

// Modals are intentionally NOT closed on overlay click.
// User must use Cancel or the X button to close.

// Escape key closes the topmost active modal
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    const activeModals = document.querySelectorAll('.modal-overlay.active');
    if (activeModals.length > 0) {
      const topModal = activeModals[activeModals.length - 1];
      const id = topModal.id.replace('modal-', '');
      closeModal(id);
    }
  }
});


// ── Strategy Import: Parse JSON & Auto-populate ──────────────────────────────

function handleExportFileChange(input) {
  const file = input.files[0];
  if (!file) return;

  const zone = input.closest('.file-upload-zone');
  const preview = document.getElementById('importPreview');
  const fileName = document.getElementById('importFileName');

  // Update upload zone appearance
  zone.classList.add('has-file');
  if (fileName) fileName.textContent = file.name;

  // Send to parse endpoint via AJAX
  const formData = new FormData();
  formData.append('export_file', file);

  fetch('/strategies/parse-export', {
    method: 'POST',
    body: formData,
  })
  .then(res => res.json())
  .then(data => {
    if (data.error) {
      alert('Error parsing file: ' + data.error);
      return;
    }
    populateStrategyFields(data);
    if (preview) preview.classList.remove('hidden');
  })
  .catch(err => {
    alert('Error parsing file: ' + err.message);
  });
}

function populateStrategyFields(data) {
  const fields = {
    'import_strategy_name': data.strategy_name,
    'import_symbol': data.symbol,
    'import_timeframe': data.timeframe,
    'import_direction': data.direction,
    'import_style': data.style,
    'import_magic_number': data.magic_number,
    'import_composite_score': data.composite_score,
    'import_complexity': data.complexity,
  };

  for (const [id, value] of Object.entries(fields)) {
    const el = document.getElementById(id);
    if (el && value !== null && value !== undefined) {
      el.value = value;
      el.classList.add('auto-filled');

      // Show the parsed indicator
      const indicator = el.parentElement.querySelector('.parsed-indicator');
      if (indicator) indicator.classList.remove('hidden');
    }
  }

  // Auto-select Market dropdown if returned from symbol lookup
  if (data.market) {
    const marketEl = document.getElementById('import_market');
    if (marketEl) {
      marketEl.value = data.market;
      marketEl.classList.add('auto-filled');
      const indicator = document.getElementById('market-indicator');
      if (indicator) indicator.classList.remove('hidden');
    }
  }

  // Update stored data indicators
  const indicators = {
    'has-backtest': data.has_backtest_data,
    'has-equity': data.has_equity_chart,
    'has-pseudocode': data.has_pseudo_code,
  };

  for (const [id, hasData] of Object.entries(indicators)) {
    const el = document.getElementById(id);
    if (el) {
      el.style.color = hasData ? 'var(--accent-green)' : 'var(--text-muted)';
      el.querySelector('.indicator-icon').textContent = hasData ? '✓' : '✗';
    }
  }
}

function resetStrategyImport() {
  const preview = document.getElementById('importPreview');
  if (preview) preview.classList.add('hidden');

  const zone = document.querySelector('#modal-add-strategy .file-upload-zone');
  if (zone) zone.classList.remove('has-file');

  // Reset auto-filled fields
  document.querySelectorAll('#modal-add-strategy .auto-filled').forEach(el => {
    el.classList.remove('auto-filled');
    el.value = '';
  });

  // Reset file input
  const fileInput = document.getElementById('exportFileInput');
  if (fileInput) fileInput.value = '';

  // Hide parsed indicators
  document.querySelectorAll('#modal-add-strategy .parsed-indicator').forEach(el => {
    el.classList.add('hidden');
  });
}


// ── Flash Messages: Auto-dismiss ─────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.flash-msg').forEach(msg => {
    setTimeout(() => {
      msg.style.opacity = '0';
      msg.style.transform = 'translateY(-8px)';
      msg.style.transition = 'all 0.3s ease';
      setTimeout(() => msg.remove(), 300);
    }, 5000);
  });
});


// ── Delete Confirmation ──────────────────────────────────────────────────────

function confirmDelete(formId, name) {
  if (confirm(`Are you sure you want to delete "${name}"? This cannot be undone.`)) {
    document.getElementById(formId).submit();
  }
}


// ── Sortable Tables ──────────────────────────────────────────────────────────
// Any <th> with a data-sort attribute becomes sortable.
// data-sort values: "string" (default), "number", "currency", "percent", "date"
// Sorting is client-side on the visible rows only.

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('th[data-sort]').forEach(th => {
    th.classList.add('sortable');
    th.addEventListener('click', () => sortTable(th));
  });
});

function sortTable(th) {
  const table = th.closest('table');
  if (!table) return;

  const tbody = table.querySelector('tbody');
  if (!tbody) return;

  const headers = Array.from(th.parentElement.children);
  const colIdx = headers.indexOf(th);
  const sortType = th.dataset.sort || 'string';

  // Determine sort direction
  const currentDir = th.dataset.sortDir || '';
  const newDir = currentDir === 'asc' ? 'desc' : 'asc';

  // Clear sort state from all headers in this table
  headers.forEach(h => {
    h.dataset.sortDir = '';
    h.classList.remove('sort-asc', 'sort-desc');
  });

  // Set new sort state
  th.dataset.sortDir = newDir;
  th.classList.add(newDir === 'asc' ? 'sort-asc' : 'sort-desc');

  // Get rows and sort
  const rows = Array.from(tbody.querySelectorAll('tr'));

  rows.sort((a, b) => {
    const cellA = a.children[colIdx];
    const cellB = b.children[colIdx];
    if (!cellA || !cellB) return 0;

    let valA = (cellA.dataset.sortValue !== undefined) ? cellA.dataset.sortValue : cellA.textContent.trim();
    let valB = (cellB.dataset.sortValue !== undefined) ? cellB.dataset.sortValue : cellB.textContent.trim();

    let cmp = 0;

    switch (sortType) {
      case 'number':
        cmp = parseNum(valA) - parseNum(valB);
        break;
      case 'currency':
        cmp = parseNum(valA) - parseNum(valB);
        break;
      case 'percent':
        cmp = parseNum(valA) - parseNum(valB);
        break;
      case 'date':
        cmp = (valA || '').localeCompare(valB || '');
        break;
      default: // string
        cmp = valA.localeCompare(valB, undefined, { sensitivity: 'base' });
    }

    return newDir === 'asc' ? cmp : -cmp;
  });

  // Re-append sorted rows
  rows.forEach(row => tbody.appendChild(row));
}

function parseNum(val) {
  if (val === '' || val === '—' || val === '-') return -Infinity;
  // Strip $, commas, %, whitespace
  const cleaned = String(val).replace(/[$,%\s]/g, '').replace(/,/g, '');
  const num = parseFloat(cleaned);
  return isNaN(num) ? -Infinity : num;
}
