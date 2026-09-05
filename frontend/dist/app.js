/**
 * KinetiQ Retail Sales & Inventory Copilot — Client Controller
 * Powers the White/Bright Bento Box Dashboard, Multi-Role Auth,
 * MongoDB state synchronization, and deterministic AI grounding.
 */

const API_BASE = window.location.origin;

// State
let currentUser = null;
let currentToken = null;
let currentStoreId = "STORE_01";
let currentTriage = null;
let activeTab = "stockouts";

// Lightweight Markdown Formatter
function formatMarkdown(text) {
  if (!text) return "";
  let html = text
    .replace(/^### (.*$)/gim, "<h3>$1</h3>")
    .replace(/^## (.*$)/gim, "<h2>$1</h2>")
    .replace(/^# (.*$)/gim, "<h1>$1</h1>")
    .replace(/\*\*(.*?)\*\*/gim, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/gim, "<em>$1</em>")
    .replace(/`([^`]+)`/gim, "<code>$1</code>")
    .replace(/\n\n/gim, "<br><br>")
    .replace(/^\s*-\s(.*$)/gim, "<li>$1</li>");

  if (html.includes("<li>")) {
    html = html.replace(/(<li>.*?<\/li>)+/gis, (match) => `<ul>${match}</ul>`);
  }
  return html;
}

// Toast Feedback Notification
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.innerHTML = `<span>${type === "success" ? "✅" : "ℹ️"}</span> <span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 3500);
}

// ============================================================================
// Initialization & Authentication Lifecycle
// ============================================================================

document.addEventListener("DOMContentLoaded", async () => {
  setupEventListeners();
  await checkAuthState();
});

function setupEventListeners() {
  // Brand Header click returns to dashboard or login
  document.getElementById("headerBrand").addEventListener("click", () => {
    if (currentUser) {
      refreshDashboard();
    }
  });

  // Role Switcher in Header
  const roleSelect = document.getElementById("roleSwitcherSelect");
  roleSelect.addEventListener("change", async (e) => {
    await quickLogin(e.target.value);
  });

  // Store Context Selector
  const storeSelect = document.getElementById("storeSelect");
  storeSelect.addEventListener("change", (e) => {
    currentStoreId = e.target.value;
    refreshDashboard();
  });

  // Action Queue Tab Buttons
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeTab = btn.getAttribute("data-tab");
      renderActionQueue();
    });
  });

  // Refresh Triage Button
  document.getElementById("btnRefreshTriage").addEventListener("click", () => {
    refreshDashboard();
    showToast("Operational triage updated from live store kernel.", "info");
  });

  // Sign Out Button
  document.getElementById("btnLogout").addEventListener("click", () => {
    logout();
  });

  // API Key Modal Toggles
  document.getElementById("btnOpenApiKeyModal").addEventListener("click", () => {
    openApiKeyModal();
  });
  document.getElementById("btnCloseApiKeyModal").addEventListener("click", () => {
    closeApiKeyModal();
  });

  // Tutorial Video Modal Listeners
  const btnTut = document.getElementById("btnOpenTutorialModal");
  if (btnTut) {
    btnTut.addEventListener("click", openTutorialModal);
  }
  const btnCloseTut = document.getElementById("btnCloseTutorialModal");
  if (btnCloseTut) {
    btnCloseTut.addEventListener("click", closeTutorialModal);
  }

  // Manual Login Form
  const manualForm = document.getElementById("manualLoginForm");
  if (manualForm) {
    manualForm.addEventListener("submit", handleManualLogin);
  }

  // Quick Demo Login Cards Direct Listeners
  document.querySelectorAll(".quick-demo-card").forEach((card) => {
    card.addEventListener("click", (e) => {
      e.stopPropagation();
      if (card.classList.contains("role-store_manager")) quickLogin("store_manager");
      else if (card.classList.contains("role-supply_chain_director")) quickLogin("supply_chain_director");
      else if (card.classList.contains("role-executive")) quickLogin("executive");
    });
  });

  // Simulation Sliders
  const discountSlider = document.getElementById("simDiscountSlider");
  const discountLabel = document.getElementById("sliderDiscountLabel");
  discountSlider.addEventListener("input", (e) => {
    discountLabel.textContent = `${e.target.value}%`;
    triggerSimulation();
  });

  document.getElementById("simSkuSelect").addEventListener("change", triggerSimulation);
  document.getElementById("simDurationSelect").addEventListener("change", triggerSimulation);
}

// ============================================================================
// Authentication Services
// ============================================================================

async function checkAuthState() {
  const savedToken = localStorage.getItem("kinetiq_token");
  if (!savedToken) {
    renderLoginView();
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
      headers: { "Authorization": `Bearer ${savedToken}` }
    });
    if (res.ok) {
      const sess = await res.json();
      setAuthenticatedUser(savedToken, sess);
    } else {
      renderLoginView();
    }
  } catch (err) {
    console.error("Auth check error:", err);
    renderLoginView();
  }
}

function setAuthenticatedUser(token, user) {
  currentToken = token;
  currentUser = user;
  localStorage.setItem("kinetiq_token", token);
  localStorage.setItem("kinetiq_user", JSON.stringify(user));

  // Update Header UI
  document.getElementById("headerControls").style.display = "flex";
  document.getElementById("headerUserName").textContent = user.name;
  document.getElementById("headerAvatar").textContent = user.avatar || "👤";
  
  const badge = document.getElementById("headerRoleBadge");
  badge.textContent = user.role_label || user.role;
  badge.className = `role-badge ${user.role}`;

  document.getElementById("roleSwitcherSelect").value = user.role;

  // Set Store Context
  if (user.role === "store_manager") {
    currentStoreId = user.assigned_store || "STORE_01";
    document.getElementById("storeSelect").value = currentStoreId;
    document.getElementById("storeSelect").disabled = true;
  } else {
    document.getElementById("storeSelect").disabled = false;
  }

  // Render Role-Tailored Prompt Suggestions
  renderRolePromptSuggestions(user.role);

  // Switch View
  document.getElementById("loginView").style.display = "none";
  document.getElementById("dashboardView").style.display = "flex";

  // Load Dashboard Data
  refreshDashboard();
  showToast(`Welcome, ${user.name}! (${user.role_label})`, "success");
}

function renderLoginView() {
  currentUser = null;
  currentToken = null;
  localStorage.removeItem("kinetiq_token");
  localStorage.removeItem("kinetiq_user");

  document.getElementById("headerControls").style.display = "none";
  document.getElementById("dashboardView").style.display = "none";
  document.getElementById("loginView").style.display = "flex";
}

async function quickLogin(role) {
  showToast(`Authenticating demo role: ${role.replace('_', ' ')}...`, "info");
  try {
    let res = await fetch(`${API_BASE}/api/auth/quick-login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role })
    });
    if (!res.ok) {
      res = await fetch(`${API_BASE}/auth/quick-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role })
      });
    }
    if (!res.ok) {
      showToast("Quick login failed. Please try again.", "info");
      return;
    }
    const sess = await res.json();
    setAuthenticatedUser(sess.token, sess);
  } catch (err) {
    showToast("Network error connecting to auth server.", "info");
  }
}

async function handleManualLogin(e) {
  e.preventDefault();
  const username = document.getElementById("inputUsername").value.trim();
  const password = document.getElementById("inputPassword").value.trim();

  try {
    let res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });
    if (!res.ok) {
      res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });
    }
    if (!res.ok) {
      showToast("Invalid credentials. Use a 1-click Quick Demo card above.", "info");
      return;
    }
    const sess = await res.json();
    setAuthenticatedUser(sess.token, sess);
  } catch (err) {
    showToast("Network error during login.", "info");
  }
}

function logout() {
  renderLoginView();
  showToast("You have been signed out.", "info");
}

// ============================================================================
// Role-Tailored UI & Prompt Suggestions
// ============================================================================

function renderRolePromptSuggestions(role) {
  const container = document.getElementById("promptSuggestionsContainer");
  const roleBadge = document.getElementById("copilotRoleBadge");
  const copilotPill = document.getElementById("copilotPill");

  container.innerHTML = "";

  let suggestions = [];
  if (role === "store_manager") {
    roleBadge.textContent = "Persona: Store General Manager";
    copilotPill.textContent = "Store Floor Focus";
    copilotPill.className = "role-badge store_manager";
    suggestions = [
      "Which SKU runs out first today?",
      "Check Dairy inventory runway for STORE_01",
      "What is the supplier lead time for SKU_001?",
      "Summarize my morning priority actions"
    ];
  } else if (role === "supply_chain_director") {
    roleBadge.textContent = "Persona: Supply Chain Director";
    copilotPill.textContent = "Multi-Store Logistics";
    copilotPill.className = "role-badge supply_chain_director";
    suggestions = [
      "Show all inter-store rebalancing arbitrage routes",
      "Where is surplus stock located across Westside?",
      "Detect phantom inventory and dead capital",
      "Compare courier freight transit times across stores"
    ];
  } else {
    roleBadge.textContent = "Persona: Executive & CFO";
    copilotPill.textContent = "Portfolio Financial Health";
    copilotPill.className = "role-badge executive";
    suggestions = [
      "What is total capital locked in dead inventory?",
      "How much revenue is protected by stock rebalancing?",
      "Simulate 15% discount impact on net margin lift",
      "Benchmark gross margin efficiency across all stores"
    ];
  }

  suggestions.forEach((text) => {
    const chip = document.createElement("button");
    chip.className = "prompt-chip";
    chip.textContent = text;
    chip.onclick = () => {
      document.getElementById("chatInput").value = text;
      document.getElementById("chatForm").dispatchEvent(new Event("submit"));
    };
    container.appendChild(chip);
  });
}

// ============================================================================
// Dashboard Data Loading & Triage Queue
// ============================================================================

async function refreshDashboard() {
  try {
    const res = await fetch(`${API_BASE}/api/triage/today?store_id=${currentStoreId}`);
    if (!res.ok) return;

    currentTriage = await res.json();

    // Update Scope Label
    const storeLabel = currentStoreId === "STORE_01" ? "Downtown Metro Express" : 
                       currentStoreId === "STORE_02" ? "Westside Supercenter" : "North Corridor Hub";
    document.getElementById("triageScopeLabel").textContent = `Context: ${storeLabel} (${currentStoreId})`;

    const stockoutCount = currentTriage.imminent_stockouts_count ?? (currentTriage.top_imminent_stockouts ? currentTriage.top_imminent_stockouts.length : 0);
    const deadCapital = currentTriage.total_dead_capital_locked ?? 0;
    const deadCount = currentTriage.dead_capital_skus_count ?? (currentTriage.top_dead_stock_items ? currentTriage.top_dead_stock_items.length : 0);
    const transferCount = currentTriage.available_transfers_count ?? (currentTriage.recommended_transfers ? currentTriage.recommended_transfers.length : 0);
    const surgeCount = currentTriage.velocity_anomalies_count ?? (currentTriage.top_velocity_anomalies ? currentTriage.top_velocity_anomalies.length : 0);

    // Update KPIs
    document.getElementById("kpiStockouts").textContent = `${stockoutCount} SKUs`;
    document.getElementById("kpiDeadCapital").textContent = `₹${deadCapital.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById("kpiDeadCount").textContent = `${deadCount} SKUs`;
    document.getElementById("kpiArbitrage").textContent = `${transferCount} Transfers`;

    // Update Tab Counts
    document.getElementById("tabCountStockouts").textContent = stockoutCount;
    document.getElementById("tabCountDead").textContent = deadCount;
    document.getElementById("tabCountSurges").textContent = surgeCount;
    document.getElementById("tabCountRebalance").textContent = transferCount;

    // Update Narrative
    const health = currentTriage.health_score !== undefined ? currentTriage.health_score : 85;
    const totalSkus = currentTriage.total_active_skus || 250;
    const narrative = `Store Health Index: ${health}/100 across ${totalSkus} tracked products. Identified ${stockoutCount} imminent stockouts needing immediate attention, ₹${deadCapital.toFixed(2)} in dormant inventory, and ${transferCount} inter-store peer transfer routes ready for dispatch.`;
    document.getElementById("triageNarrative").textContent = narrative;

    // Render Action Queue & Sandbox
    renderActionQueue();
    renderRebalanceMatrix();
    populateSimulatorSkus();
    triggerSimulation();
  } catch (err) {
    console.error("Dashboard refresh error:", err);
  }
}

function renderActionQueue() {
  const container = document.getElementById("actionQueueContainer");
  container.innerHTML = "";

  if (!currentTriage) return;

  if (activeTab === "stockouts") {
    const items = currentTriage.top_imminent_stockouts || currentTriage.imminent_stockouts || [];
    if (items.length === 0) {
      container.innerHTML = `<div style="text-align: center; color: var(--text-tertiary); padding: 2rem;">No imminent stockouts detected in current store runway.</div>`;
      return;
    }
    items.forEach((item) => {
      const el = document.createElement("div");
      el.className = "action-item";
      el.innerHTML = `
        <div>
          <div class="action-sku-title">${item.sku_id} — ${item.product_name || item.sku_name || 'Product'} (${item.category || 'Retail'})</div>
          <div class="action-meta">
            <span>📦 On Hand: <strong>${item.on_hand ?? item.units_on_hand}</strong></span>
            <span>⏱️ Runway: <strong>${item.days_of_inventory} days</strong></span>
            <span>🚚 Supplier Lead: <strong>${item.lead_time_days} days</strong></span>
            <span class="role-badge ${item.urgency_level === 'CRITICAL' ? 'executive' : 'store_manager'}">${item.urgency_level || 'ALERT'}</span>
          </div>
        </div>
        <button class="btn-commit-action" onclick="requestArbitrageForSku('${item.sku_id}')">
          ⚡ Request Transfer
        </button>
      `;
      container.appendChild(el);
    });
  } else if (activeTab === "deadStock") {
    const items = currentTriage.top_dead_stock_items || currentTriage.dead_inventory || [];
    if (items.length === 0) {
      container.innerHTML = `<div style="text-align: center; color: var(--text-tertiary); padding: 2rem;">No dead inventory detected.</div>`;
      return;
    }
    items.forEach((item) => {
      const el = document.createElement("div");
      el.className = "action-item";
      const idleDays = item.days_since_last_sale ?? item.days_idle ?? item.days_stagnant ?? 0;
      const lockedCap = item.locked_capital ?? item.capital_locked ?? item.capital_locked_usd ?? 0;
      el.innerHTML = `
        <div>
          <div class="action-sku-title">${item.sku_id} — ${item.product_name || item.sku_name}</div>
          <div class="action-meta">
            <span>💤 Idle: <strong>${idleDays} days</strong></span>
            <span>💵 Capital Locked: <strong>₹${lockedCap.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong></span>
            <span>📦 Quantity: <strong>${item.on_hand ?? item.units_idle} units</strong></span>
          </div>
        </div>
        <button class="btn-header" onclick="selectSkuForSimulation('${item.sku_id}')">
          🎯 Markdown Simulator
        </button>
      `;
      container.appendChild(el);
    });
  } else if (activeTab === "surges") {
    const items = currentTriage.top_velocity_anomalies || currentTriage.sales_anomalies || [];
    if (items.length === 0) {
      container.innerHTML = `<div style="text-align: center; color: var(--text-tertiary); padding: 2rem;">No abnormal demand shifts detected today.</div>`;
      return;
    }
    items.forEach((item) => {
      const el = document.createElement("div");
      el.className = "action-item";
      el.innerHTML = `
        <div>
          <div class="action-sku-title">${item.sku_id} — ${item.product_name || item.sku_name}</div>
          <div class="action-meta">
            <span>📈 Shift Z-Score: <strong>+${(item.z_score || 0).toFixed(1)}σ</strong></span>
            <span>⚡ Recent: <strong>${item.actual_sales ?? item.recent_units} units</strong> vs μ=${(item.expected_sales ?? item.mean_units ?? 0).toFixed(1)}</span>
          </div>
        </div>
        <span class="role-badge supply_chain_director">${item.anomaly_type || 'Surge Alert'}</span>
      `;
      container.appendChild(el);
    });
  } else if (activeTab === "rebalance") {
    const items = currentTriage.recommended_transfers || currentTriage.rebalance_opportunities || [];
    if (items.length === 0) {
      container.innerHTML = `<div style="text-align: center; color: var(--text-tertiary); padding: 2rem;">No network rebalance manifests currently available.</div>`;
      return;
    }
    items.forEach((m) => {
      const el = document.createElement("div");
      el.className = "action-item";
      const qty = m.quantity ?? m.transfer_quantity ?? 0;
      const freight = m.estimated_courier_cost_inr ?? m.estimated_courier_cost ?? m.estimated_courier_cost_usd ?? 0;
      const savings = m.net_savings ?? m.net_financial_benefit_usd ?? 0;
      el.innerHTML = `
        <div>
          <div class="action-sku-title">Transfer Manifest ${m.manifest_id}: ${m.sku_id} — ${m.product_name || 'Stock Rebalance'}</div>
          <div class="action-meta">
            <span>Route: <strong>${m.from_store_id} ➔ ${m.to_store_id}</strong></span>
            <span>Quantity: <strong>${qty} units</strong></span>
            <span>Freight Cost: <strong>₹${freight}</strong></span>
            <span>Net Protection: <strong>+₹${savings.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong></span>
          </div>
        </div>
        <button class="btn-commit-action" onclick="commitTransfer('${m.manifest_id}', '${m.from_store_id}', '${m.to_store_id}', '${m.sku_id}', ${qty})">
          Approve &amp; Dispatch ➔
        </button>
      `;
      container.appendChild(el);
    });
  }
}

async function commitTransfer(manifestId, fromStore, toStore, skuId, quantity) {
  try {
    const res = await fetch(`${API_BASE}/api/actions/transfer`, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentToken}`
      },
      body: JSON.stringify({
        manifest_id: manifestId,
        from_store_id: fromStore,
        to_store_id: toStore,
        sku_id: skuId,
        quantity: quantity
      })
    });
    if (res.ok) {
      showToast(`Transfer ${manifestId} (${quantity} units) committed to logistics route!`, "success");
      refreshDashboard();
    } else {
      showToast("Transfer commit failed.", "info");
    }
  } catch (err) {
    showToast("Network error committing transfer.", "info");
  }
}

function requestArbitrageForSku(skuId) {
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
  document.querySelector('.tab-btn[data-tab="rebalance"]').classList.add("active");
  activeTab = "rebalance";
  renderActionQueue();
  showToast(`Scanning network arbitrage opportunities for ${skuId}...`, "info");
}

function selectSkuForSimulation(skuId) {
  const select = document.getElementById("simSkuSelect");
  let found = false;
  for (let opt of select.options) {
    if (opt.value === skuId) {
      select.value = skuId;
      found = true;
      break;
    }
  }
  if (!found) {
    const newOpt = document.createElement("option");
    newOpt.value = skuId;
    newOpt.textContent = `${skuId} (Selected SKU)`;
    select.appendChild(newOpt);
    select.value = skuId;
  }
  triggerSimulation();
  showToast(`Loaded ${skuId} into What-If Simulator`, "info");
}

function renderRebalanceMatrix() {
  const container = document.getElementById("rebalanceMatrixContainer");
  if (!currentTriage) return;

  const list = currentTriage.recommended_transfers || currentTriage.rebalance_opportunities || [];
  if (list.length === 0) {
    container.innerHTML = `
      <div style="background: var(--bg-surface-secondary); padding: 1.5rem; border-radius: var(--radius-md); text-align: center; color: var(--text-secondary); font-size: 0.88rem;">
        No active transfers pending. Peer store buffers are operating within optimal safety stock.
      </div>
    `;
    return;
  }

  let html = `<div style="display: flex; flex-direction: column; gap: 0.75rem;">`;
  list.slice(0, 3).forEach((item) => {
    html += `
      <div style="background: var(--bg-surface-secondary); padding: 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
        <div>
          <div style="font-weight: 700; font-size: 0.9rem; color: var(--text-primary);">
            ${item.sku_id} — ${item.from_store_id} ➔ ${item.to_store_id}
          </div>
          <div style="font-size: 0.78rem; color: var(--text-secondary); margin-top: 0.2rem;">
            Estimated Courier Transit: ${item.assumptions ? item.assumptions.transit_time_hours : 2.5} hrs • Cost: ₹${item.estimated_courier_cost_inr ?? item.estimated_courier_cost ?? item.estimated_courier_cost_usd}
          </div>
        </div>
        <span class="role-badge supply_chain_director">Ready</span>
      </div>
    `;
  });
  html += `</div>`;
  container.innerHTML = html;
}

// ============================================================================
// What-If Price Elasticity Sandbox Simulation
// ============================================================================

function populateSimulatorSkus() {
  const select = document.getElementById("simSkuSelect");
  if (!select) return;
  const currentVal = select.value;
  select.innerHTML = "";
  
  const defaultSkus = [
    { id: "SKU_1001", label: "SKU_1001 — Classic White Bread 400g (Bakery)" },
    { id: "SKU_1002", label: "SKU_1002 — Whole Wheat Loaf 400g (Bakery)" },
    { id: "SKU_1005", label: "SKU_1005 — Pasture Raised Milk 105g (Dairy)" },
    { id: "SKU_1004", label: "SKU_1004 — Stone-Ground Sauce 104g (Pantry)" },
  ];

  if (currentTriage && currentTriage.top_imminent_stockouts) {
    currentTriage.top_imminent_stockouts.forEach((s) => {
      if (!defaultSkus.some((item) => item.id === s.sku_id)) {
        defaultSkus.push({ id: s.sku_id, label: `${s.sku_id} — ${s.product_name} (${s.category})` });
      }
    });
  }

  defaultSkus.forEach((s) => {
    const opt = document.createElement("option");
    opt.value = s.id;
    opt.textContent = s.label;
    select.appendChild(opt);
  });

  if (currentVal && defaultSkus.some((s) => s.id === currentVal)) {
    select.value = currentVal;
  }
}

async function triggerSimulation() {
  const skuId = document.getElementById("simSkuSelect").value;
  const duration = parseInt(document.getElementById("simDurationSelect").value, 10);
  const discount = parseFloat(document.getElementById("simDiscountSlider").value);

  try {
    const res = await fetch(`${API_BASE}/api/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sku_id: skuId,
        store_id: currentStoreId,
        discount_percent: discount,
        duration_days: duration
      })
    });
    if (!res.ok) return;

    const data = await res.json();
    const units = data.projected_units_sold ?? data.projected_demand_units ?? 0;
    const liftPct = data.velocity_lift_percent ?? data.projected_demand_lift_pct ?? 0;
    const profitDelta = data.gross_profit_delta ?? data.net_profit_variance_usd ?? 0;
    const isAtRisk = data.stockout_risk ?? data.stockout_risk_triggered ?? false;

    document.getElementById("simDemandVal").textContent = `+${units} units (+${liftPct.toFixed(1)}%)`;
    document.getElementById("simMarginVal").textContent = `${liftPct >= 0 ? '+' : ''}${liftPct.toFixed(1)}%`;
    document.getElementById("simProfitVal").textContent = `${profitDelta >= 0 ? '+' : ''}₹${profitDelta.toFixed(2)}`;

    // Risk Banner
    const banner = document.getElementById("simRiskBanner");
    const riskText = document.getElementById("simRiskText");

    if (isAtRisk) {
      banner.className = "risk-banner risk-high";
      riskText.textContent = `CRITICAL EXHAUSTION: Projected demand exceeds on-hand runway (${data.on_hand || 0} units) within ${duration}d.`;
    } else if (discount >= 25) {
      banner.className = "risk-banner risk-medium";
      riskText.textContent = "ELEVATED RISK: Steep discount velocity will rapidly accelerate inventory drawdown.";
    } else {
      banner.className = "risk-banner risk-low";
      riskText.textContent = "SAFE RUNWAY: Supply chain buffer remains stable through campaign window.";
    }
  } catch (err) {
    console.error("Simulation error:", err);
  }
}

// ============================================================================
// AI Copilot Conversational Chat
// ============================================================================

async function handleChatSubmit(e) {
  e.preventDefault();
  const input = document.getElementById("chatInput");
  const query = input.value.trim();
  if (!query) return;

  const stream = document.getElementById("chatMessageStream");

  // Append user bubble
  const userBubble = document.createElement("div");
  userBubble.className = "chat-msg user";
  userBubble.textContent = query;
  stream.appendChild(userBubble);
  input.value = "";
  stream.scrollTop = stream.scrollHeight;

  // Append loading assistant bubble
  const assistantBubble = document.createElement("div");
  assistantBubble.className = "chat-msg assistant";
  assistantBubble.innerHTML = `<em>Reasoning over ground-truth SQL kernel...</em>`;
  stream.appendChild(assistantBubble);
  stream.scrollTop = stream.scrollHeight;

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentToken}`
      },
      body: JSON.stringify({
        message: query,
        store_id: currentStoreId,
        role: currentUser ? currentUser.role : null
      })
    });

    if (!res.ok) {
      assistantBubble.textContent = "Sorry, I encountered an issue querying the analytical engine.";
      return;
    }

    const data = await res.json();
    assistantBubble.innerHTML = formatMarkdown(data.response);
  } catch (err) {
    assistantBubble.textContent = "Network error connecting to Copilot engine.";
  }
  stream.scrollTop = stream.scrollHeight;
}

// Alias for compatibility
const handleUserMessage = handleChatSubmit;

// ============================================================================
// Gemini API Key Management Modal
// ============================================================================

function openApiKeyModal() {
  const modal = document.getElementById("apiKeyModal");
  const statusLabel = document.getElementById("modalCurrentKeyPreview");

  if (currentUser && currentUser.custom_api_key) {
    const key = currentUser.custom_api_key;
    statusLabel.textContent = `Active (****${key.slice(-4)})`;
  } else {
    statusLabel.textContent = "Configured in Environment / Local Grounded Mode";
  }

  modal.classList.add("active");
}

function closeApiKeyModal() {
  document.getElementById("apiKeyModal").classList.remove("active");
}

async function handleApiKeySubmit(e) {
  e.preventDefault();
  const keyInput = document.getElementById("inputApiKey");
  const key = keyInput.value.trim();

  try {
    const res = await fetch(`${API_BASE}/api/auth/api-key`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentToken}`
      },
      body: JSON.stringify({ api_key: key })
    });
    if (res.ok) {
      const data = await res.json();
      if (currentUser) {
        currentUser.custom_api_key = key;
        localStorage.setItem("kinetiq_user", JSON.stringify(currentUser));
      }
      showToast(data.message, "success");
      closeApiKeyModal();
    } else {
      showToast("Failed to save API key.", "info");
    }
  } catch (err) {
    showToast("Network error updating API key.", "info");
  }
}

async function testAiConnection() {
  showToast("Testing live Google Gemini copilot connectivity...", "info");
  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentToken}`
      },
      body: JSON.stringify({
        message: "Verify live copilot connection status",
        store_id: currentStoreId
      })
    });
    if (res.ok) {
      showToast("Gemini Copilot connected and responding with ground truth!", "success");
    } else {
      showToast("Copilot fallback engaged.", "info");
    }
  } catch (err) {
    showToast("Could not reach Copilot API.", "info");
  }
}

// ============================================================================
// Tutorial Video Modal Controls
// ============================================================================

function openTutorialModal() {
  const modal = document.getElementById("tutorialModal");
  if (!modal) return;
  modal.classList.add("active");
  const video = document.getElementById("tutorialVideoPlayer");
  if (video) {
    video.currentTime = 0;
  }
}

function closeTutorialModal() {
  const modal = document.getElementById("tutorialModal");
  if (!modal) return;
  modal.classList.remove("active");
  const video = document.getElementById("tutorialVideoPlayer");
  if (video) {
    video.pause();
  }
}

function loadCustomVideoUrl() {
  const input = document.getElementById("inputCustomVideoUrl");
  const url = input ? input.value.trim() : "";
  if (!url) {
    showToast("Please enter a valid video link.", "info");
    return;
  }
  const video = document.getElementById("tutorialVideoPlayer");
  if (video) {
    video.src = url;
    video.load();
    video.play().catch(() => {});
    showToast("Custom tutorial video loaded!", "success");
  }
}

