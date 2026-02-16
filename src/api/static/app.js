const API_BASE = '/api/v1';

let currentTab = 'overview';

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    loadOverview();
});

function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            switchTab(tab.dataset.tab);
        });
    });
}

function switchTab(tabId) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    document.querySelector(`.tab[data-tab="${tabId}"]`).classList.add('active');
    document.getElementById(tabId).classList.add('active');

    currentTab = tabId;

    switch(tabId) {
        case 'overview':
            loadOverview();
            break;
        case 'memories':
            loadMemories();
            break;
        case 'configs':
            loadConfigs();
            break;
        case 'reports':
            loadReports();
            break;
        case 'trends':
            loadTrends();
            break;
    }
}

async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${url}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || error.message || '请求失败');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

function showLoading(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = '<div class="loading">加载中</div>';
    }
}

function showError(containerId, message) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `<div class="alert error">${message}</div>`;
    }
}

async function loadOverview() {
    showLoading('recent-memories');
    showLoading('recent-reports');

    try {
        const overview = await apiRequest('/dashboard/overview');

        document.getElementById('total-memories').textContent = overview.total_memories;
        document.getElementById('total-configs').textContent = overview.total_configs;
        document.getElementById('total-reports').textContent = overview.total_reports;
        document.getElementById('active-tasks').textContent = overview.active_tasks;

        const memoriesContainer = document.getElementById('recent-memories');
        if (overview.recent_memories.length > 0) {
            memoriesContainer.innerHTML = overview.recent_memories.map(mem => createMemoryCard(mem)).join('');
        } else {
            memoriesContainer.innerHTML = '<p class="alert info">暂无记忆</p>';
        }

        const reportsContainer = document.getElementById('recent-reports');
        if (overview.recent_reports.length > 0) {
            reportsContainer.innerHTML = overview.recent_reports.map(rep => createReportCard(rep)).join('');
        } else {
            reportsContainer.innerHTML = '<p class="alert info">暂无报告</p>';
        }
    } catch (error) {
        showError('recent-memories', error.message);
        showError('recent-reports', error.message);
    }
}

function createMemoryCard(memory) {
    const typeClass = memory.memory_type.replace('_', '-');
    const date = new Date(memory.created_at).toLocaleString('zh-CN');

    return `
        <div class="card">
            <h4>${escapeHtml(memory.title)}</h4>
            <p>${escapeHtml(memory.content.substring(0, 200))}${memory.content.length > 200 ? '...' : ''}</p>
            <div class="card-meta">
                <span class="badge ${typeClass}">${memory.memory_type}</span>
                <span>📅 ${date}</span>
                <span>🎯 ${memory.category}</span>
                <span>⭐ ${memory.score.toFixed(2)}</span>
            </div>
        </div>
    `;
}

function createReportCard(report) {
    const date = new Date(report.created_at).toLocaleString('zh-CN');

    return `
        <div class="card">
            <h4>${escapeHtml(report.id)}</h4>
            <p>${escapeHtml(report.content.substring(0, 200))}${report.content.length > 200 ? '...' : ''}</p>
            <div class="card-meta">
                <span class="badge">📊 ${report.report_type}</span>
                <span>📅 ${date}</span>
            </div>
        </div>
    `;
}

async function loadMemories() {
    showLoading('memories-list');

    try {
        const memories = await apiRequest('/memories/?limit=50');

        const container = document.getElementById('memories-list');
        if (memories.length > 0) {
            container.innerHTML = memories.map(mem => createMemoryCard(mem)).join('');
        } else {
            container.innerHTML = '<p class="alert info">暂无记忆</p>';
        }
    } catch (error) {
        showError('memories-list', error.message);
    }
}

function filterMemories() {
    const type = document.getElementById('memory-filter').value;
    const url = type ? `/memories/?memory_type=${type}&limit=50` : '/memories/?limit=50';

    showLoading('memories-list');

    apiRequest(url)
        .then(memories => {
            const container = document.getElementById('memories-list');
            if (memories.length > 0) {
                container.innerHTML = memories.map(mem => createMemoryCard(mem)).join('');
            } else {
                container.innerHTML = '<p class="alert info">暂无记忆</p>';
            }
        })
        .catch(error => {
            showError('memories-list', error.message);
        });
}

async function searchMemories() {
    const keyword = document.getElementById('search-input').value;
    const hybrid = document.getElementById('hybrid-search').checked;

    if (!keyword) {
        showError('search-results', '请输入搜索关键词');
        return;
    }

    showLoading('search-results');

    try {
        const results = await apiRequest('/query/search', {
            method: 'POST',
            body: JSON.stringify({ keyword, hybrid })
        });

        const container = document.getElementById('search-results');
        if (results.results.length > 0) {
            container.innerHTML = `<p class="alert success">找到 ${results.total} 条结果</p>` +
                results.results.map(mem => createMemoryCard(mem)).join('');
        } else {
            container.innerHTML = '<p class="alert info">未找到匹配的记忆</p>';
        }
    } catch (error) {
        showError('search-results', error.message);
    }
}

async function loadConfigs() {
    showLoading('configs-list');

    try {
        const configs = await apiRequest('/configs/');

        const container = document.getElementById('configs-list');
        if (configs.length > 0) {
            container.innerHTML = configs.map(config => createConfigCard(config)).join('');
        } else {
            container.innerHTML = '<p class="alert info">暂无配置</p>';
        }
    } catch (error) {
        showError('configs-list', error.message);
    }
}

function createConfigCard(config) {
    const date = new Date(config.updated_at).toLocaleString('zh-CN');

    return `
        <div class="card">
            <h4>Agent: ${escapeHtml(config.agent_id)}</h4>
            <pre>${escapeHtml(JSON.stringify(config.config_data, null, 2))}</pre>
            <div class="card-meta">
                <span>📅 ${date}</span>
                <span>ID: ${config.id.substring(0, 8)}...</span>
            </div>
        </div>
    `;
}

async function loadReports() {
    showLoading('reports-list');

    try {
        const reports = await apiRequest('/reports/recent?limit=20');

        const container = document.getElementById('reports-list');
        if (reports.length > 0) {
            container.innerHTML = reports.map(rep => createReportCard(rep)).join('');
        } else {
            container.innerHTML = '<p class="alert info">暂无报告</p>';
        }
    } catch (error) {
        showError('reports-list', error.message);
    }
}

async function generateReport(type) {
    showLoading('reports-list');

    try {
        const report = await apiRequest(`/reports/${type}`);
        alert(`报告生成成功！\n\n${report.content.substring(0, 500)}...`);
        loadReports();
    } catch (error) {
        showError('reports-list', error.message);
    }
}

async function loadTrends() {
    showLoading('daily-trend-chart');
    showLoading('weekly-trend-chart');
    showLoading('types-distribution-chart');
    showLoading('categories-distribution-chart');

    try {
        const [dailyTrend, weeklyTrend, types, categories] = await Promise.all([
            apiRequest('/dashboard/trends/memories/daily?days=30'),
            apiRequest('/dashboard/trends/memories/weekly?weeks=12'),
            apiRequest('/dashboard/top/types?limit=10'),
            apiRequest('/dashboard/top/categories?limit=10')
        ]);

        renderChart('daily-trend-chart', dailyTrend.data, '每日新增');
        renderChart('weekly-trend-chart', weeklyTrend.data, '每周新增');
        renderChart('types-distribution-chart', types, '类型分布');
        renderChart('categories-distribution-chart', categories, '类别分布');
    } catch (error) {
        showError('daily-trend-chart', error.message);
        showError('weekly-trend-chart', error.message);
        showError('types-distribution-chart', error.message);
        showError('categories-distribution-chart', error.message);
    }
}

function renderChart(containerId, data, title) {
    const container = document.getElementById(containerId);
    if (!data || data.length === 0) {
        container.innerHTML = '<p class="alert info">暂无数据</p>';
        return;
    }

    const maxValue = Math.max(...data.map(d => d.value));

    container.innerHTML = data.map(d => {
        const height = (d.value / maxValue * 100) || 0;
        return `
            <div class="chart-bar" style="height: ${height}%">
                <div class="chart-bar-value">${d.value}</div>
                <div class="chart-bar-label">${escapeHtml(d.label.substring(0, 10))}</div>
            </div>
        `;
    }).join('');
}

function showCreateMemoryModal() {
    const form = `
        <h2>新建记忆</h2>
        <form onsubmit="createMemory(event)">
            <div class="form-group">
                <label>标题</label>
                <input type="text" class="input" name="title" required>
            </div>
            <div class="form-group">
                <label>内容</label>
                <textarea class="textarea" name="content" required></textarea>
            </div>
            <div class="form-group">
                <label>类型</label>
                <select class="select" name="memory_type">
                    <option value="long_term">长期记忆</option>
                    <option value="short_term">短期记忆</option>
                    <option value="session">会话上下文</option>
                </select>
            </div>
            <div class="form-group">
                <label>类别</label>
                <select class="select" name="category">
                    <option value="general">通用</option>
                    <option value="success_case">成功案例</option>
                    <option value="failure_lesson">失败教训</option>
                    <option value="skill_growth">技能成长</option>
                    <option value="user_preference">用户偏好</option>
                </select>
            </div>
            <div class="form-group">
                <label>标签（逗号分隔）</label>
                <input type="text" class="input" name="tags" placeholder="tag1, tag2, tag3">
            </div>
            <button type="submit" class="btn primary">创建</button>
        </form>
    `;
    showModal(form);
}

function showCreateConfigModal() {
    const form = `
        <h2>新建配置</h2>
        <form onsubmit="createConfig(event)">
            <div class="form-group">
                <label>Agent ID</label>
                <input type="text" class="input" name="agent_id" required>
            </div>
            <div class="form-group">
                <label>配置数据（JSON）</label>
                <textarea class="textarea" name="config_data" placeholder='{"temperature": 0.7, "max_tokens": 2000}' required></textarea>
            </div>
            <div class="form-group">
                <label>
                    <input type="checkbox" name="auto_apply"> 自动应用
                </label>
            </div>
            <button type="submit" class="btn primary">创建</button>
        </form>
    `;
    showModal(form);
}

async function createMemory(event) {
    event.preventDefault();
    const form = event.target;

    const memoryData = {
        title: form.title.value,
        content: form.content.value,
        memory_type: form.memory_type.value,
        category: form.category.value,
        tags: form.tags.value.split(',').map(t => t.trim()).filter(t => t),
        source: 'web_ui'
    };

    try {
        await apiRequest('/memories/', {
            method: 'POST',
            body: JSON.stringify(memoryData)
        });

        closeModal();
        alert('记忆创建成功！');
        loadMemories();
    } catch (error) {
        alert(`创建失败: ${error.message}`);
    }
}

async function createConfig(event) {
    event.preventDefault();
    const form = event.target;

    try {
        const configData = JSON.parse(form.config_data.value);
    } catch (error) {
        alert('配置数据必须是有效的 JSON 格式');
        return;
    }

    const config = {
        agent_id: form.agent_id.value,
        config_data: JSON.parse(form.config_data.value),
        auto_apply: form.auto_apply.checked
    };

    try {
        await apiRequest('/configs/', {
            method: 'POST',
            body: JSON.stringify(config)
        });

        closeModal();
        alert('配置创建成功！');
        loadConfigs();
    } catch (error) {
        alert(`创建失败: ${error.message}`);
    }
}

function showModal(content) {
    const modal = document.getElementById('modal');
    const modalBody = document.getElementById('modal-body');
    modalBody.innerHTML = content;
    modal.classList.add('show');
}

function closeModal() {
    const modal = document.getElementById('modal');
    modal.classList.remove('show');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.querySelector('.close').addEventListener('click', closeModal);

window.addEventListener('click', (e) => {
    const modal = document.getElementById('modal');
    if (e.target === modal) {
        closeModal();
    }
});
