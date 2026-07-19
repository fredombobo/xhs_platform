/**
 * VibeCoding 灵感发现平台 - 前端主逻辑
 */

// ==================== 工具色映射 ====================
const TOOL_COLORS = {
    cursor: "#7c3aed", windsurf: "#3b82f6", bolt: "#f59e0b",
    v0: "#06b6d4", lovable: "#ec4899", replit: "#8b5cf6",
    copilot: "#22c55e", claude: "#f97316", trae: "#6366f1",
    tongyi: "#0891b2", general: "#64748b",
};
const TOOL_LABELS = {
    cursor: "Cursor", windsurf: "Windsurf", bolt: "Bolt.new",
    v0: "v0", lovable: "Lovable", replit: "Replit Agent",
    copilot: "GitHub Copilot", claude: "Claude Artifacts",
    trae: "Trae", tongyi: "通义灵码", general: "AI编程",
};
const TOOL_ICONS = {
    cursor: "🖥️", windsurf: "🌊", bolt: "⚡", v0: "▲",
    lovable: "❤️", replit: "🔄", copilot: "🤖", claude: "🧠",
    trae: "🚀", tongyi: "☁️", general: "💡",
};
const DIFF_LABELS = { beginner: "入门级", intermediate: "进阶级", advanced: "高级" };
const DIFF_COLORS = { beginner: "#22c55e", intermediate: "#f59e0b", advanced: "#ef4444" };
const CAT_LABELS = {
    tutorial: "教程教学", showcase: "项目展示", comparison: "工具对比",
    workflow: "工作流分享", tips: "技巧心得", case_study: "实战案例",
    review: "工具评测", prompt: "提示词工程",
};

// ==================== 全局状态 ====================
const state = {
    page: 1, perPage: 20, keyword: "", sortBy: "crawled",
    total: 0, totalPages: 1, items: [], isCrawling: false,
    // VibeCoding 筛选
    toolFilter: "", difficultyFilter: "", categoryFilter: "",
    tools: [], categories: {}, trendingItems: [],
};

// ==================== DOM 缓存 ====================
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
    keywordInput: $("#keywordInput"), countSelect: $("#countSelect"),
    crawlBtn: $("#crawlBtn"), realCrawlBtn: $("#realCrawlBtn"),
    loginBrowserBtn: $("#loginBrowserBtn"), checkLoginBtn: $("#checkLoginBtn"),
    crawlStatus: $("#crawlStatus"),
    modeIndicator: $("#modeIndicator"), cookieInput: $("#cookieInput"),
    saveCookieBtn: $("#saveCookieBtn"), cookieStatus: $("#cookieStatus"),
    keywordFilter: $("#keywordFilter"), sortBtns: $$(".sort-btn"),
    toolPills: $("#toolPills"), diffToggles: $("#diffToggles"),
    resetFiltersBtn: $("#resetFiltersBtn"),
    statTotal: $("#statTotal"), statTrending: $("#statTrending"),
    statAvgLikes: $("#statAvgLikes"), statMaxLikes: $("#statMaxLikes"),
    topKeywords: $("#topKeywords"),
    trendingSection: $("#trendingSection"), trendingScroll: $("#trendingScroll"),
    categoryTabs: $("#categoryTabs"),
    contentTitle: $("#contentTitle"), contentCount: $("#contentCount"),
    keywordBadge: $("#keywordBadge"),
    refreshBtn: $("#refreshBtn"),
    loadingState: $("#loadingState"), emptyState: $("#emptyState"),
    emptyMessage: $("#emptyMessage"), contentGrid: $("#contentGrid"),
    pagination: $("#pagination"),
    detailModal: $("#detailModal"), modalClose: $("#modalClose"),
    modalBody: $("#modalBody"), toast: $("#toast"),
    headerStats: $("#headerStats"),
};

// ==================== API 封装 ====================
const api = {
    async request(url, options = {}, timeoutMs = 60000) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeoutMs);
        try {
            const resp = await fetch(url, {
                headers: { "Content-Type": "application/json" },
                signal: controller.signal,
                ...options,
            });
            clearTimeout(timer);
            const data = await resp.json();
            if (data.code !== 200) throw new Error(data.message || "请求失败");
            return data.data;
        } catch (err) {
            clearTimeout(timer);
            if (err.name === "AbortError") throw new Error("请求超时，请重试");
            throw err;
        }
    },

    getContents(params = {}) {
        const qs = new URLSearchParams({
            page: params.page || 1, per_page: params.perPage || 20,
            sort_by: params.sortBy || "likes",
        });
        if (params.keyword) qs.set("keyword", params.keyword);
        if (params.tool) qs.set("tool", params.tool);
        if (params.projectType) qs.set("project_type", params.projectType);
        if (params.difficulty) qs.set("difficulty", params.difficulty);
        if (params.category) qs.set("category", params.category);
        return this.request(`/api/contents?${qs.toString()}`);
    },

    crawl(keyword, count) {
        return this.request("/api/crawl", {
            method: "POST", body: JSON.stringify({ keyword, count }),
        });
    },

    getStats() { return this.request("/api/stats"); },
    getKeywords() { return this.request("/api/keywords"); },
    getTools() { return this.request("/api/vibecoding/tools"); },
    getCategories() { return this.request("/api/vibecoding/categories"); },
    getTrending() { return this.request("/api/vibecoding/trending"); },
    seedData(keyword, count) {
        return this.request("/api/vibecoding/seed", {
            method: "POST", body: JSON.stringify({ keyword, count }),
        });
    },
    realCrawl(keyword, count) {
        return this.request("/api/crawl/real", {
            method: "POST", body: JSON.stringify({ keyword, count }),
        });
    },
    loginStatus() { return this.request("/api/login-status"); },
    setCookie(cookie) {
        return this.request("/api/set-cookie", {
            method: "POST", body: JSON.stringify({ cookie }),
        });
    },
    crawlerMode() { return this.request("/api/crawler-mode"); },
    loginBrowser() {
        return this.request("/api/login-browser", { method: "POST" });
    },
};

// ==================== Toast ====================
function showToast(message, type = "info") {
    const toast = dom.toast;
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.remove("hidden");
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => { toast.classList.add("hidden"); }, 3000);
}

// ==================== 格式化工具 ====================
function formatNumber(n) {
    if (n >= 10000) return (n / 10000).toFixed(1) + "w";
    if (n >= 1000) return (n / 1000).toFixed(1) + "k";
    return String(n);
}

function timeAgo(dateStr) {
    if (!dateStr) return "";
    const now = Date.now();
    const then = new Date(dateStr).getTime();
    const diff = now - then;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    if (minutes < 1) return "刚刚";
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 30) return `${days}天前`;
    return dateStr.slice(0, 10);
}

function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// ==================== Badge 渲染 ====================
function renderToolBadge(toolName) {
    if (!toolName || toolName === "general") return "";
    const label = TOOL_LABELS[toolName] || toolName;
    const color = TOOL_COLORS[toolName] || "#64748b";
    const icon = TOOL_ICONS[toolName] || "";
    return `<span class="tool-badge" style="background:${color}20;color:${color};border-color:${color}40;">${icon} ${label}</span>`;
}

function renderDifficultyBadge(level) {
    if (!level) return "";
    const label = DIFF_LABELS[level] || level;
    const color = DIFF_COLORS[level] || "#64748b";
    return `<span class="diff-badge" style="background:${color}15;color:${color};border-color:${color}30;">${label}</span>`;
}

function renderCategoryBadge(category) {
    if (!category) return "";
    const label = CAT_LABELS[category] || category;
    return `<span class="cat-badge">${label}</span>`;
}

// ==================== Trending 区域 ====================
function renderTrendingSection(items) {
    if (!items || items.length === 0) {
        dom.trendingSection.classList.add("hidden");
        return;
    }

    dom.trendingSection.classList.remove("hidden");
    dom.trendingScroll.innerHTML = items.slice(0, 10).map((item, i) => {
        const coverHtml = item.cover_url
            ? `<img src="${escapeHtml(item.cover_url)}" alt="" loading="lazy" onerror="this.style.display='none'">`
            : `<div class="trending-card-placeholder">⚡</div>`;
        const toolLabel = TOOL_LABELS[item.tool_name] || "";
        const velocity = item.velocity || 0;
        const velocityLabel = velocity >= 10000 ? "🔥🔥🔥" : velocity >= 5000 ? "🔥🔥" : "🔥";

        return `
            <div class="trending-card" onclick="openDetail(${item.id})">
                <div class="trending-card-cover">${coverHtml}</div>
                <div class="trending-card-info">
                    <div class="trending-card-tool">${toolLabel}</div>
                    <div class="trending-card-title">${escapeHtml(item.title || "无标题")}</div>
                    <div class="trending-card-velocity">
                        <span class="velocity-badge">${velocityLabel} 热度 ${formatNumber(velocity)}</span>
                    </div>
                </div>
            </div>
        `;
    }).join("");
}

// ==================== 内容卡片渲染 ====================
function renderContentCards(items) {
    if (!items || items.length === 0) {
        dom.contentGrid.classList.add("hidden");
        dom.emptyState.classList.remove("hidden");
        dom.emptyMessage.textContent = "试试其他筛选条件，或者点击「开始爬取」获取新内容";
        return;
    }

    dom.emptyState.classList.add("hidden");
    dom.contentGrid.classList.remove("hidden");

    const globalIndex = (state.page - 1) * state.perPage;

    dom.contentGrid.innerHTML = items.map((item, i) => {
        const rank = globalIndex + i + 1;
        const rankClass = rank === 1 ? "top-1" : rank === 2 ? "top-2" : rank === 3 ? "top-3" : "";
        const authorInitial = (item.author_name || "?")[0];
        const coverHtml = item.cover_url
            ? `<img src="${escapeHtml(item.cover_url)}" alt="封面" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\\'card-cover-placeholder\\'>⚡</div>'">`
            : `<div class="card-cover-placeholder">⚡</div>`;

        const toolBadge = renderToolBadge(item.tool_name);
        const diffBadge = renderDifficultyBadge(item.difficulty_level);

        return `
            <div class="content-card" data-id="${item.id}" onclick="openDetail(${item.id})">
                <div class="card-cover">
                    ${coverHtml}
                    ${rank <= 10 ? `<div class="card-rank ${rankClass}">${rank}</div>` : ""}
                    ${item.is_trending ? `<div class="card-trending-flame">🔥</div>` : ""}
                </div>
                <div class="card-body">
                    <div class="card-badges">
                        ${toolBadge}
                        ${diffBadge}
                    </div>
                    <div class="card-title">${escapeHtml(item.title || "无标题")}</div>
                    <div class="card-meta">
                        <div class="card-author-avatar">${authorInitial}</div>
                        <span class="card-author-name">${escapeHtml(item.author_name || "未知")}</span>
                    </div>
                    <div class="card-stats">
                        <span>🔥 ${formatNumber(item.likes)}</span>
                        <span>⭐ ${formatNumber(item.collects)}</span>
                        <span>💬 ${formatNumber(item.comments)}</span>
                    </div>
                    ${item.tags && item.tags.length > 0 ? `
                        <div class="card-tags">
                            ${item.tags.slice(0, 3).map(t => `<span class="card-tag">#${escapeHtml(t)}</span>`).join("")}
                        </div>
                    ` : ""}
                </div>
            </div>
        `;
    }).join("");
}

// ==================== 分页 ====================
function renderPagination() {
    if (state.totalPages <= 1) {
        dom.pagination.classList.add("hidden");
        return;
    }

    dom.pagination.classList.remove("hidden");
    const { page, totalPages } = state;
    let html = "";

    html += `<button class="page-btn" ${page <= 1 ? "disabled" : ""} onclick="goToPage(${page - 1})">‹</button>`;

    const pages = [];
    if (totalPages <= 7) {
        for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
        pages.push(1);
        if (page > 3) pages.push("...");
        for (let i = Math.max(2, page - 1); i <= Math.min(totalPages - 1, page + 1); i++) {
            pages.push(i);
        }
        if (page < totalPages - 2) pages.push("...");
        pages.push(totalPages);
    }

    pages.forEach((p) => {
        if (p === "...") {
            html += `<span class="page-info">...</span>`;
        } else {
            html += `<button class="page-btn ${p === page ? "active" : ""}" onclick="goToPage(${p})">${p}</button>`;
        }
    });

    html += `<button class="page-btn" ${page >= totalPages ? "disabled" : ""} onclick="goToPage(${page + 1})">›</button>`;
    html += `<span class="page-info">${state.total} 条</span>`;

    dom.pagination.innerHTML = html;
}

// ==================== 统计面板 ====================
function renderStats(stats) {
    dom.statTotal.textContent = formatNumber(stats.total_contents);
    dom.statTrending.textContent = formatNumber(stats.total_trending || 0);
    dom.statAvgLikes.textContent = formatNumber(stats.avg_likes);
    dom.statMaxLikes.textContent = formatNumber(stats.max_likes);
    dom.headerStats.innerHTML = `
        <span class="stat-badge">📊 ${stats.total_contents} 条内容</span>
        <span class="stat-badge trend-badge">🔥 ${stats.total_trending || 0} 热门</span>
    `;

    if (stats.top_keywords && stats.top_keywords.length > 0) {
        dom.topKeywords.innerHTML = stats.top_keywords
            .map(kw => `<span class="kw-tag" onclick="searchKeyword('${escapeHtml(kw.keyword)}')">${escapeHtml(kw.keyword)} (${kw.count})</span>`)
            .join("");
    }
}

function updateKeywordFilter(keywords) {
    const select = dom.keywordFilter;
    const currentVal = select.value;
    select.innerHTML = '<option value="">全部关键词</option>';
    if (keywords && keywords.length > 0) {
        keywords.forEach((kw) => {
            select.innerHTML += `<option value="${escapeHtml(kw.keyword)}">${escapeHtml(kw.keyword)} (${kw.count})</option>`;
        });
    }
    select.value = currentVal;
}

// ==================== Tool 筛选 Pills ====================
function renderToolFilters(tools) {
    if (!tools || tools.length === 0) return;

    let html = '<button class="tool-pill active" data-tool="">全部</button>';
    tools.forEach((t) => {
        const activeClass = state.toolFilter === t.tool ? "active" : "";
        html += `<button class="tool-pill ${activeClass}" data-tool="${escapeHtml(t.tool)}" style="--pill-color:${t.color || '#64748b'};">${t.icon || ''} ${t.label} <span class="pill-count">${t.count}</span></button>`;
    });
    dom.toolPills.innerHTML = html;

    // 绑定事件
    dom.toolPills.querySelectorAll(".tool-pill").forEach(pill => {
        pill.addEventListener("click", () => {
            dom.toolPills.querySelectorAll(".tool-pill").forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            state.toolFilter = pill.dataset.tool;
            state.page = 1;
            loadContents();
        });
    });
}

// ==================== 难度筛选 ====================
function bindDifficultyToggles() {
    dom.diffToggles.querySelectorAll(".diff-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            dom.diffToggles.querySelectorAll(".diff-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            state.difficultyFilter = btn.dataset.diff;
            state.page = 1;
            loadContents();
        });
    });
}

// ==================== 分类 Tab ====================
function bindCategoryTabs() {
    dom.categoryTabs.querySelectorAll(".category-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            dom.categoryTabs.querySelectorAll(".category-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            state.categoryFilter = tab.dataset.category;
            state.page = 1;
            loadContents();
        });
    });
}

// ==================== 详情弹窗 ====================
function openDetail(id) {
    const item = state.items.find((i) => i.id === id);
    if (!item) return;

    const coverHtml = item.cover_url
        ? `<img src="${escapeHtml(item.cover_url)}" alt="封面" onerror="this.parentElement.innerHTML='<div style=\\'width:100%;aspect-ratio:16/10;display:flex;align-items:center;justify-content:center;font-size:64px;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:8px;\\'>⚡</div>'">`
        : `<div style="width:100%;aspect-ratio:16/10;display:flex;align-items:center;justify-content:center;font-size:64px;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:8px;">⚡</div>`;

    const toolBadge = renderToolBadge(item.tool_name);
    const diffBadge = renderDifficultyBadge(item.difficulty_level);
    const catBadge = renderCategoryBadge(item.content_category);
    const sourceLink = item.source_url
        ? `<a href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener" class="modal-source-link">🔗 查看小红书原文</a>`
        : "";

    dom.modalBody.innerHTML = `
        <div class="modal-cover">${coverHtml}</div>
        <div class="modal-badges-row">
            ${toolBadge} ${diffBadge} ${catBadge}
            ${item.is_trending ? '<span class="trending-flame-badge">🔥 热门</span>' : ""}
        </div>
        <h2 class="modal-title">${escapeHtml(item.title || "无标题")}</h2>
        <div class="modal-author">
            <div class="modal-author-icon">${(item.author_name || "?")[0]}</div>
            <span>${escapeHtml(item.author_name || "未知")}</span>
            <span style="margin-left:8px;font-size:12px;color:#999;">${item.author_id || ""}</span>
        </div>
        ${item.description ? `<div class="modal-desc">${escapeHtml(item.description).replace(/\n/g, '<br>')}</div>` : ""}
        <div class="modal-interact">
            <div class="modal-interact-item">🔥 <strong>${formatNumber(item.likes)}</strong> 点赞</div>
            <div class="modal-interact-item">⭐ <strong>${formatNumber(item.collects)}</strong> 收藏</div>
            <div class="modal-interact-item">💬 <strong>${formatNumber(item.comments)}</strong> 评论</div>
            <div class="modal-interact-item">📤 <strong>${formatNumber(item.shares)}</strong> 分享</div>
        </div>
        ${item.tags && item.tags.length > 0 ? `
            <div class="modal-tags">
                ${item.tags.map(t => `<span class="modal-tag">#${escapeHtml(t)}</span>`).join("")}
            </div>
        ` : ""}
        <div class="modal-footer-info">
            <span>🕐 ${item.publish_time ? timeAgo(item.publish_time) : "未知时间"}</span>
            <span>🔑 关键词: ${escapeHtml(item.keyword || "")}</span>
            ${sourceLink}
        </div>
        <div class="modal-actions">
            ${item.tool_name ? `<button class="btn btn-sm btn-outline" onclick="closeDetail();searchByTool('${escapeHtml(item.tool_name)}')">🔍 查看更多 ${TOOL_LABELS[item.tool_name] || item.tool_name} 内容</button>` : ""}
            ${item.difficulty_level ? `<button class="btn btn-sm btn-outline" onclick="closeDetail();searchByDifficulty('${escapeHtml(item.difficulty_level)}')">📊 查看${DIFF_LABELS[item.difficulty_level] || ''}全部内容</button>` : ""}
        </div>
    `;

    dom.detailModal.classList.remove("hidden");
    document.body.style.overflow = "hidden";
}

function closeDetail() {
    dom.detailModal.classList.add("hidden");
    document.body.style.overflow = "";
}

function searchByTool(tool) {
    state.toolFilter = tool;
    state.page = 1;
    state.categoryFilter = "";
    state.difficultyFilter = "";
    // 更新 UI 状态
    dom.toolPills.querySelectorAll(".tool-pill").forEach(p => {
        p.classList.toggle("active", p.dataset.tool === tool);
    });
    dom.categoryTabs.querySelectorAll(".category-tab").forEach(t => {
        t.classList.toggle("active", t.dataset.category === "");
    });
    dom.diffToggles.querySelectorAll(".diff-btn").forEach(b => {
        b.classList.toggle("active", b.dataset.diff === "");
    });
    loadContents();
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function searchByDifficulty(diff) {
    state.difficultyFilter = diff;
    state.page = 1;
    dom.diffToggles.querySelectorAll(".diff-btn").forEach(b => {
        b.classList.toggle("active", b.dataset.diff === diff);
    });
    loadContents();
    window.scrollTo({ top: 0, behavior: "smooth" });
}

// ==================== 数据加载 ====================
async function loadContents() {
    dom.loadingState.classList.remove("hidden");
    dom.contentGrid.classList.add("hidden");
    dom.emptyState.classList.add("hidden");
    dom.pagination.classList.add("hidden");

    try {
        const data = await api.getContents({
            page: state.page, perPage: state.perPage,
            keyword: state.keyword, sortBy: state.sortBy,
            tool: state.toolFilter, difficulty: state.difficultyFilter,
            category: state.categoryFilter,
        });

        state.items = data.items;
        state.total = data.total;
        state.totalPages = data.total_pages || 1;

        dom.loadingState.classList.add("hidden");
        dom.contentCount.textContent = `共 ${state.total} 条`;

        // 更新标题
        const parts = [];
        if (state.toolFilter && TOOL_LABELS[state.toolFilter]) parts.push(TOOL_LABELS[state.toolFilter]);
        if (state.difficultyFilter && DIFF_LABELS[state.difficultyFilter]) parts.push(DIFF_LABELS[state.difficultyFilter]);
        if (state.categoryFilter && CAT_LABELS[state.categoryFilter]) parts.push(CAT_LABELS[state.categoryFilter]);
        if (state.keyword) parts.push(`"${state.keyword}"`);

        dom.contentTitle.textContent = parts.length > 0 ? `🔍 ${parts.join(" · ")}` : "🔥 热门内容";

        // 显示/隐藏关键词筛选标签
        if (state.keyword) {
            dom.keywordBadge.textContent = `🔑 筛选: "${state.keyword}"`;
            dom.keywordBadge.classList.remove("hidden");
        } else {
            dom.keywordBadge.classList.add("hidden");
        }

        renderContentCards(data.items);
        renderPagination();

        if (data.items.length === 0) {
            dom.emptyState.classList.remove("hidden");
            dom.emptyMessage.textContent = "没有找到符合条件的内容，试试重置筛选条件或爬取新内容";
        }
    } catch (err) {
        dom.loadingState.classList.add("hidden");
        dom.emptyState.classList.remove("hidden");
        dom.emptyMessage.textContent = "加载失败: " + err.message;
        showToast("加载内容失败: " + err.message, "error");
    }
}

async function loadStats() {
    try {
        const stats = await api.getStats();
        renderStats(stats);
    } catch { /* 静默失败 */ }
}

async function loadKeywords() {
    try {
        const data = await api.getKeywords();
        updateKeywordFilter(data);
    } catch { /* 静默失败 */ }
}

async function loadTools() {
    try {
        const tools = await api.getTools();
        state.tools = tools;
        renderToolFilters(tools);
    } catch { /* 静默失败 */ }
}

async function loadCategories() {
    try {
        state.categories = await api.getCategories();
    } catch { /* 静默失败 */ }
}

async function loadTrending() {
    try {
        const items = await api.getTrending();
        state.trendingItems = items;
        renderTrendingSection(items);
    } catch { /* 静默失败 */ }
}

// ==================== 操作 ====================
async function startCrawl() {
    if (state.isCrawling) return;

    const keyword = dom.keywordInput.value.trim();
    if (!keyword) {
        showToast("请输入搜索关键词", "error");
        return;
    }

    const count = parseInt(dom.countSelect.value) || 50;

    state.isCrawling = true;
    dom.crawlBtn.disabled = true;
    dom.crawlBtn.innerHTML = '<span class="spinner" style="width:16px;height:16px;border-width:2px;margin:0;"></span> 爬取中...';
    dom.crawlStatus.classList.remove("hidden", "success", "error");
    dom.crawlStatus.textContent = "正在爬取数据，请稍候...";

    try {
        const result = await api.crawl(keyword, count);
        dom.crawlStatus.textContent = `✅ 成功爬取 ${result.saved_count || result.saved} 条内容`;
        dom.crawlStatus.classList.add("success");
        showToast(`成功爬取 ${result.saved_count || result.saved} 条内容`, "success");

        state.page = 1;
        state.keyword = keyword;
        state.sortBy = "crawled";  // 按最新爬取排序，新数据优先显示
        dom.keywordFilter.value = keyword;
        // 更新排序按钮状态
        dom.sortBtns.forEach(b => b.classList.remove("active"));
        const crawledBtn = document.querySelector('.sort-btn[data-sort="crawled"]');
        if (crawledBtn) crawledBtn.classList.add("active");
        await Promise.all([
            loadContents(), loadStats(), loadKeywords(),
            loadTools(), loadCategories(), loadTrending(),
        ]);
    } catch (err) {
        dom.crawlStatus.textContent = `❌ ${err.message}`;
        dom.crawlStatus.classList.add("error");
        showToast("爬取失败: " + err.message, "error");
    } finally {
        state.isCrawling = false;
        dom.crawlBtn.disabled = false;
        dom.crawlBtn.innerHTML = '<span class="btn-icon">🚀</span> 模拟爬取';
    }
}

async function startRealCrawl() {
    if (state.isCrawling) return;

    const keyword = dom.keywordInput.value.trim();
    if (!keyword) {
        showToast("请输入搜索关键词", "error");
        return;
    }

    const count = parseInt(dom.countSelect.value) || 30;

    state.isCrawling = true;
    dom.realCrawlBtn.disabled = true;
    dom.realCrawlBtn.innerHTML = '<span class="spinner" style="width:16px;height:16px;border-width:2px;margin:0;"></span> 浏览器爬取中...';
    dom.crawlStatus.classList.remove("hidden", "success", "error");
    dom.crawlStatus.textContent = "🌐 正在使用真实浏览器爬取小红书数据，请稍候（可能需要30秒-1分钟）...";

    try {
        const result = await api.realCrawl(keyword, count);
        if (result.need_login) {
            dom.crawlStatus.textContent = "⚠️ 需要先登录小红书。请打开 https://www.xiaohongshu.com 登录后重试。";
            dom.crawlStatus.classList.add("error");
            showToast("需要先登录小红书账号", "error");
        } else {
            dom.crawlStatus.textContent = `✅ 真实爬取完成！新增 ${result.saved_count || result.saved} 条内容`;
            dom.crawlStatus.classList.add("success");
            showToast(`真实爬取完成！获取 ${result.saved_count || result.saved} 条真实数据`, "success");
            updateModeIndicator("real");
        }

        state.page = 1;
        state.keyword = keyword;
        state.sortBy = "crawled";
        dom.keywordFilter.value = keyword;
        dom.sortBtns.forEach(b => b.classList.remove("active"));
        const crawledBtn2 = document.querySelector('.sort-btn[data-sort="crawled"]');
        if (crawledBtn2) crawledBtn2.classList.add("active");
        await Promise.all([
            loadContents(), loadStats(), loadKeywords(),
            loadTools(), loadCategories(), loadTrending(),
        ]);
    } catch (err) {
        dom.crawlStatus.textContent = `❌ ${err.message}`;
        dom.crawlStatus.classList.add("error");
        showToast("真实爬取失败: " + err.message, "error");
    } finally {
        state.isCrawling = false;
        dom.realCrawlBtn.disabled = false;
        dom.realCrawlBtn.innerHTML = '<span class="btn-icon">🌐</span> 真实浏览器爬取';
    }
}

async function saveCookie() {
    const cookie = dom.cookieInput.value.trim();
    if (!cookie) {
        showToast("请输入 Cookie", "error");
        return;
    }

    dom.saveCookieBtn.disabled = true;
    dom.saveCookieBtn.textContent = "保存中...";

    try {
        await api.setCookie(cookie);
        dom.cookieStatus.textContent = "✅ Cookie 已保存";
        dom.cookieStatus.className = "cookie-status success";
        updateModeIndicator("cookie");
        showToast("Cookie 已保存，现在可以使用真实 API 模式", "success");
    } catch (err) {
        dom.cookieStatus.textContent = `❌ ${err.message}`;
        dom.cookieStatus.className = "cookie-status error";
    } finally {
        dom.saveCookieBtn.disabled = false;
        dom.saveCookieBtn.textContent = "💾 保存 Cookie";
    }
}

function updateModeIndicator(mode) {
    if (mode === "real" || mode === "cookie") {
        dom.modeIndicator.textContent = "真实数据";
        dom.modeIndicator.className = "mode-badge mode-real";
    } else {
        dom.modeIndicator.textContent = "模拟数据";
        dom.modeIndicator.className = "mode-badge mode-mock";
    }
}

async function checkCrawlerMode() {
    try {
        const mode = await api.crawlerMode();
        if (mode.has_cookie) {
            updateModeIndicator("cookie");
        }
    } catch { /* ignore */ }
}

async function openLoginBrowser() {
    if (state.isCrawling) return;
    state.isCrawling = true;
    dom.loginBrowserBtn.disabled = true;
    dom.loginBrowserBtn.textContent = "⏳ 等待登录...";
    dom.crawlStatus.classList.remove("hidden", "success", "error");
    dom.crawlStatus.textContent = "🔐 浏览器窗口已打开，请在弹出窗口中扫码登录小红书...";
    dom.crawlStatus.classList.add("success");

    try {
        const result = await api.loginBrowser();
        if (result.success) {
            showToast("✅ 登录成功！现在可以真实爬取了", "success");
            updateModeIndicator("real");
            dom.crawlStatus.textContent = "✅ 登录成功！点击「真实浏览器爬取」开始获取数据";
        } else {
            showToast("⚠️ 登录超时，请重试", "error");
            dom.crawlStatus.textContent = "⚠️ 登录超时，请重试";
        }
    } catch (err) {
        showToast("登录失败: " + err.message, "error");
        dom.crawlStatus.textContent = `❌ ${err.message}`;
    } finally {
        state.isCrawling = false;
        dom.loginBrowserBtn.disabled = false;
        dom.loginBrowserBtn.textContent = "🔐 登录小红书";
    }
}

async function checkLogin() {
    try {
        const status = await api.loginStatus();
        if (status.logged_in) {
            showToast("✅ 已登录小红书", "success");
            updateModeIndicator("real");
        } else {
            showToast("❌ 尚未登录，请先点击「登录小红书」按钮", "info");
        }
    } catch (err) {
        showToast("检查失败: " + err.message, "error");
    }
}

function goToPage(page) {
    if (page < 1 || page > state.totalPages) return;
    state.page = page;
    loadContents();
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function setSortBy(sortBy) {
    state.sortBy = sortBy;
    state.page = 1;
    loadContents();
}

function searchKeyword(keyword) {
    state.keyword = keyword;
    state.page = 1;
    dom.keywordFilter.value = keyword;
    loadContents();
}

function filterByKeyword() {
    state.keyword = dom.keywordFilter.value;
    state.page = 1;
    loadContents();
}

function resetAllFilters() {
    state.toolFilter = "";
    state.difficultyFilter = "";
    state.categoryFilter = "";
    state.keyword = "";
    state.page = 1;

    // 重置 Tool pills
    dom.toolPills.querySelectorAll(".tool-pill").forEach(p => {
        p.classList.toggle("active", p.dataset.tool === "");
    });
    // 重置难度
    dom.diffToggles.querySelectorAll(".diff-btn").forEach(b => {
        b.classList.toggle("active", b.dataset.diff === "");
    });
    // 重置分类 tab
    dom.categoryTabs.querySelectorAll(".category-tab").forEach(t => {
        t.classList.toggle("active", t.dataset.category === "");
    });
    // 重置关键词
    dom.keywordFilter.value = "";
    // 重置排序
    dom.sortBtns.forEach(b => b.classList.remove("active"));
    const likesBtn = document.querySelector('.sort-btn[data-sort="likes"]');
    if (likesBtn) likesBtn.classList.add("active");
    state.sortBy = "likes";

    loadContents();
    window.scrollTo({ top: 0, behavior: "smooth" });
}

// ==================== 事件绑定 ====================
function bindEvents() {
    dom.crawlBtn.addEventListener("click", startCrawl);
    dom.realCrawlBtn.addEventListener("click", startRealCrawl);
    dom.loginBrowserBtn.addEventListener("click", openLoginBrowser);
    dom.checkLoginBtn.addEventListener("click", checkLogin);
    dom.saveCookieBtn.addEventListener("click", saveCookie);
    dom.keywordInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") startCrawl();
    });

    // 预设搜索按钮
    document.querySelectorAll(".preset-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            dom.keywordInput.value = btn.dataset.keyword;
            startCrawl();
        });
    });

    dom.modalClose.addEventListener("click", closeDetail);
    dom.detailModal.addEventListener("click", (e) => {
        if (e.target === dom.detailModal) closeDetail();
    });
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeDetail();
    });

    dom.refreshBtn.addEventListener("click", () => {
        Promise.all([
            loadContents(), loadStats(), loadKeywords(),
            loadTools(), loadTrending(),
        ]);
    });

    dom.keywordFilter.addEventListener("change", filterByKeyword);
    dom.resetFiltersBtn.addEventListener("click", resetAllFilters);

    // 排序按钮
    dom.sortBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
            dom.sortBtns.forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            setSortBy(btn.dataset.sort);
        });
    });

    bindDifficultyToggles();
    bindCategoryTabs();
}

// ==================== 初始化 ====================
(async function init() {
    bindEvents();
    await Promise.all([
        loadContents(), loadStats(), loadKeywords(),
        loadTools(), loadCategories(), loadTrending(),
        checkCrawlerMode(),
    ]);
})();
