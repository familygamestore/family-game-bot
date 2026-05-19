/**
 * FAMILY GAME STORE BOT - MAIN JAVASCRIPT
 */

// ============================================
// GLOBAL VARIABLES
// ============================================

let currentPage = 'dashboard';
let autoRefreshInterval = null;
let broadcastInterval = null;

// ============================================
// DOM Ready
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    initializeNavigation();
    initializeModals();
    initializeForms();
    loadDashboardData();
    startAutoRefresh();
}

// ============================================
// NAVIGATION
// ============================================

function initializeNavigation() {
    // Mobile menu toggle
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', toggleMobileMenu);
    }
    
    // Sidebar navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.dataset.page;
            if (page) {
                switchPage(page);
            }
        });
    });
}

function toggleMobileMenu() {
    const menu = document.getElementById('mobileMenu');
    if (menu) {
        menu.classList.toggle('hidden');
    }
}

function switchPage(page) {
    // Update active nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === page) {
            item.classList.add('active');
        }
    });
    
    // Show/hide pages
    document.querySelectorAll('.page').forEach(pageEl => {
        pageEl.classList.remove('active');
    });
    
    const targetPage = document.getElementById(`${page}-page`);
    if (targetPage) {
        targetPage.classList.add('active');
        currentPage = page;
        loadPageData(page);
    }
}

function loadPageData(page) {
    switch(page) {
        case 'dashboard':
            loadDashboardData();
            break;
        case 'accounts':
            loadAccountsData();
            break;
        case 'servers':
            loadServersData();
            break;
        case 'analytics':
            loadAnalyticsData();
            break;
    }
}

// ============================================
// MODALS
// ============================================

function initializeModals() {
    // Close modal on backdrop click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal(this.id);
            }
        });
    });
    
    // Close modal on X button
    document.querySelectorAll('.modal .close').forEach(closeBtn => {
        closeBtn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            if (modal) {
                closeModal(modal.id);
            }
        });
    });
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
    }
}

// ============================================
// FORMS
// ============================================

function initializeForms() {
    // Add server form
    const addServerForm = document.getElementById('addServerForm');
    if (addServerForm) {
        addServerForm.addEventListener('submit', handleAddServer);
    }
    
    // Activate license form
    const activateLicenseForm = document.getElementById('activateLicenseForm');
    if (activateLicenseForm) {
        activateLicenseForm.addEventListener('submit', handleActivateLicense);
    }
}

async function handleAddServer(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());
    
    showLoading('Adding server...');
    
    try {
        const response = await fetch('/api/add-server', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('Server added successfully!', 'success');
            closeModal('addServerModal');
            loadServersData();
        } else {
            showToast(result.error || 'Failed to add server', 'error');
        }
    } catch (error) {
        showToast('Network error: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function handleActivateLicense(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());
    
    showLoading('Activating license...');
    
    try {
        const response = await fetch('/api/activate-license', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast(`License activated! Plan: ${result.plan}`, 'success');
            closeModal('activateLicenseModal');
            loadServersData();
        } else {
            showToast(result.error || 'Failed to activate license', 'error');
        }
    } catch (error) {
        showToast('Network error: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// API CALLS
// ============================================

async function loadDashboardData() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        updateDashboardStats(stats);
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

async function loadAccountsData() {
    try {
        const response = await fetch('/api/accounts');
        const accounts = await response.json();
        
        renderAccountsTable(accounts);
    } catch (error) {
        console.error('Error loading accounts:', error);
    }
}

async function loadServersData() {
    try {
        const response = await fetch('/api/servers');
        const servers = await response.json();
        
        renderServersList(servers);
    } catch (error) {
        console.error('Error loading servers:', error);
    }
}

async function loadAnalyticsData() {
    try {
        const response = await fetch('/api/analytics');
        const analytics = await response.json();
        
        renderAnalyticsCharts(analytics);
    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

// ============================================
// RENDER FUNCTIONS
// ============================================

function updateDashboardStats(stats) {
    const elements = {
        totalServers: document.getElementById('totalServers'),
        totalUsers: document.getElementById('totalUsers'),
        totalMessages: document.getElementById('totalMessages'),
        premiumServers: document.getElementById('premiumServers')
    };
    
    if (elements.totalServers) elements.totalServers.textContent = stats.total_servers || 0;
    if (elements.totalUsers) elements.totalUsers.textContent = stats.total_users || 0;
    if (elements.totalMessages) elements.totalMessages.textContent = stats.total_messages || 0;
    if (elements.premiumServers) elements.premiumServers.textContent = stats.premium_servers || 0;
}

function renderAccountsTable(accounts) {
    const tbody = document.getElementById('accountsTableBody');
    if (!tbody) return;
    
    if (!accounts || accounts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No accounts found</td></tr>';
        return;
    }
    
    tbody.innerHTML = accounts.map(acc => `
        <tr>
            <td>${acc.id}</td>
            <td><strong>${escapeHtml(acc.name)}</strong></td>
            <td><span class="badge ${acc.status === 'active' ? 'badge-success' : 'badge-danger'}">${acc.status}</span></td>
            <td>${acc.total_sent}</td>
            <td>${acc.group_count}</td>
            <td>${acc.delay}s</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="editAccount(${acc.id})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteAccount(${acc.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function renderServersList(servers) {
    const container = document.getElementById('serversList');
    if (!container) return;
    
    if (!servers || servers.length === 0) {
        container.innerHTML = '<div class="text-center py-8"><p class="text-gray-400">No servers registered</p></div>';
        return;
    }
    
    container.innerHTML = servers.map(server => `
        <div class="card mb-4">
            <div class="card-body">
                <div class="d-flex justify-between align-center">
                    <div class="d-flex align-center gap-3">
                        ${server.icon ? `<img src="${server.icon}" class="w-12 h-12 rounded-full">` : 
                            `<div class="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
                                <i class="fas fa-hashtag text-white"></i>
                            </div>`}
                        <div>
                            <h3 class="font-semibold">${escapeHtml(server.name)}</h3>
                            <p class="text-sm text-gray-400">ID: ${server.server_id}</p>
                        </div>
                    </div>
                    <div>
                        ${server.license_key ? 
                            `<span class="badge badge-success">Premium</span>` :
                            `<button class="btn btn-sm btn-primary" onclick="openActivateLicenseModal('${server.server_id}')">
                                Activate License
                            </button>`
                        }
                    </div>
                </div>
                ${server.license_key ? `
                <div class="mt-4 pt-4 border-t border-gray-700">
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                            <p class="text-xs text-gray-400">License Key</p>
                            <p class="text-sm font-mono">${server.license_key}</p>
                        </div>
                        <div>
                            <p class="text-xs text-gray-400">Expires</p>
                            <p class="text-sm">${server.expires || 'Never'}</p>
                        </div>
                        <div>
                            <p class="text-xs text-gray-400">Members</p>
                            <p class="text-sm">${server.member_count || 0}</p>
                        </div>
                        <div>
                            <p class="text-xs text-gray-400">Messages</p>
                            <p class="text-sm">${server.message_count || 0}</p>
                        </div>
                    </div>
                </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}

function renderAnalyticsCharts(analytics) {
    // This would integrate with Chart.js or similar
    console.log('Analytics data:', analytics);
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="d-flex align-center gap-2">
            <i class="fas ${getToastIcon(type)}"></i>
            <span>${escapeHtml(message)}</span>
        </div>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

function getToastIcon(type) {
    switch(type) {
        case 'success': return 'fa-check-circle';
        case 'error': return 'fa-exclamation-circle';
        case 'warning': return 'fa-exclamation-triangle';
        default: return 'fa-info-circle';
    }
}

function showLoading(message = 'Loading...') {
    const loader = document.getElementById('loadingOverlay');
    if (loader) {
        loader.querySelector('.loading-message').textContent = message;
        loader.classList.remove('hidden');
    }
}

function hideLoading() {
    const loader = document.getElementById('loadingOverlay');
    if (loader) {
        loader.classList.add('hidden');
    }
}

function startAutoRefresh() {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    
    autoRefreshInterval = setInterval(() => {
        if (currentPage === 'dashboard') {
            loadDashboardData();
        } else if (currentPage === 'servers') {
            loadServersData();
        }
    }, 30000); // Refresh every 30 seconds
}

// ============================================
// ACTION FUNCTIONS
// ============================================

function openAddServerModal() {
    openModal('addServerModal');
}

function openActivateLicenseModal(serverId) {
    const input = document.getElementById('licenseServerId');
    if (input) input.value = serverId;
    openModal('activateLicenseModal');
}

async function editAccount(accountId) {
    // Fetch account details and open edit modal
    showToast('Edit feature coming soon', 'info');
}

async function deleteAccount(accountId) {
    if (!confirm('Are you sure you want to delete this account?')) return;
    
    try {
        const response = await fetch(`/api/accounts/${accountId}`, { method: 'DELETE' });
        const result = await response.json();
        
        if (result.success) {
            showToast('Account deleted successfully', 'success');
            loadAccountsData();
        } else {
            showToast(result.error || 'Failed to delete account', 'error');
        }
    } catch (error) {
        showToast('Network error: ' + error.message, 'error');
    }
}

async function refreshData() {
    showLoading('Refreshing data...');
    await loadDashboardData();
    await loadServersData();
    hideLoading();
    showToast('Data refreshed!', 'success');
}

// ============================================
// EXPORT FUNCTIONS (Global)
// ============================================

window.openAddServerModal = openAddServerModal;
window.openActivateLicenseModal = openActivateLicenseModal;
window.editAccount = editAccount;
window.deleteAccount = deleteAccount;
window.refreshData = refreshData;
window.closeModal = closeModal;