/**
 * Main JavaScript functionality for SmartInventory
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    setupMobileMenu();
});

function initializeApp() {
    // Update navigation based on auth state
    updateNavigation();
    
    // Load page-specific functionality
    const path = window.location.pathname;
    
    switch (path) {
        case '/':
            initializeHomePage();
            break;
        case '/dashboard/':
            initializeDashboard();
            break;
        default:
            // Handle other pages
            break;
    }
}

function setupEventListeners() {
    // Global keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K for search (future feature)
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            // TODO: Open search modal
            showToast('Search feature coming soon!', 'info');
        }
        
        // Escape key to close modals
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });

    // Handle navigation clicks
    document.addEventListener('click', function(e) {
        const navLink = e.target.closest('.nav-link, .mobile-nav-link');
        if (navLink && navLink.dataset.page) {
            e.preventDefault();
            navigateToPage(navLink.dataset.page);
        }
    });

    // Handle form submissions
    document.addEventListener('submit', function(e) {
        const form = e.target;
        if (form.id === 'login-form') {
            e.preventDefault();
            handleLoginForm(form);
        }
    });
}

function setupMobileMenu() {
    const mobileMenuButton = document.querySelector('.mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    
    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
        
        // Close mobile menu when clicking outside
        document.addEventListener('click', function(e) {
            if (!mobileMenuButton.contains(e.target) && !mobileMenu.contains(e.target)) {
                mobileMenu.classList.add('hidden');
            }
        });
    }
}

function updateNavigation() {
    if (!isAuthenticated()) {
        return;
    }
    
    // Update active navigation state
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link, .mobile-nav-link');
    
    navLinks.forEach(link => {
        const page = link.dataset.page;
        const isActive = (page === 'dashboard' && currentPath === '/dashboard/') ||
                        (page === 'upload' && currentPath.includes('/upload/')) ||
                        (page === 'predictions' && currentPath.includes('/predictions/')) ||
                        (page === 'alerts' && currentPath.includes('/alerts/'));
        
        link.classList.toggle('active', isActive);
    });
    
    // Update user info
    const user = getCurrentUser();
    if (user) {
        authManager.updateUI();
    }
}

function navigateToPage(page) {
    switch (page) {
        case 'dashboard':
            window.location.href = '/dashboard/';
            break;
        case 'upload':
            showDataUploadModal();
            break;
        case 'predictions':
            showPredictionsView();
            break;
        case 'alerts':
            showAlertsView();
            break;
        default:
            showToast(`${page} feature coming soon!`, 'info');
    }
}

function initializeHomePage() {
    // Load quick stats if authenticated
    if (isAuthenticated()) {
        loadQuickStats();
    }
}

async function loadQuickStats() {
    try {
        const stats = await dashboardAPI.getStats();
        displayQuickStats(stats);
    } catch (error) {
        console.error('Error loading quick stats:', error);
        showToast('Failed to load statistics', 'error');
    }
}

function displayQuickStats(stats) {
    const container = document.getElementById('quick-stats');
    if (!container) return;
    
    container.innerHTML = `
        <div class="stat-card">
            <div class="text-3xl font-bold text-primary">${stats.overview.total_stores}</div>
            <div class="text-gray-600">Total Stores</div>
        </div>
        <div class="stat-card">
            <div class="text-3xl font-bold text-success">${stats.overview.total_products}</div>
            <div class="text-gray-600">Active Products</div>
        </div>
        <div class="stat-card">
            <div class="text-3xl font-bold text-secondary">${stats.overview.total_uploads}</div>
            <div class="text-gray-600">Data Uploads</div>
        </div>
        <div class="stat-card">
            <div class="text-3xl font-bold ${stats.overview.active_alerts > 0 ? 'text-warning' : 'text-success'}">${stats.overview.active_alerts}</div>
            <div class="text-gray-600">Active Alerts</div>
        </div>
    `;
}

function initializeDashboard() {
    if (!isAuthenticated()) {
        window.location.href = '/';
        return;
    }
    
    loadDashboardData();
    setupDashboardEventListeners();
}

async function loadDashboardData() {
    try {
        showLoading();
        
        const [stats, trends, accuracy] = await Promise.all([
            dashboardAPI.getStats(),
            dashboardAPI.getSalesTrends({ days: 30 }),
            dashboardAPI.getForecastAccuracy()
        ]);
        
        displayDashboardStats(stats);
        displaySalesTrends(trends);
        displayForecastAccuracy(accuracy);
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showToast('Failed to load dashboard data', 'error');
    } finally {
        hideLoading();
    }
}

function displayDashboardStats(stats) {
    // Update KPI cards
    const kpiContainer = document.getElementById('kpi-cards');
    if (kpiContainer) {
        kpiContainer.innerHTML = `
            <div class="card">
                <div class="card-body text-center">
                    <div class="text-3xl font-bold text-primary mb-2">${formatCurrency(stats.sales_summary.total_sales_30d)}</div>
                    <div class="text-gray-600">Total Sales (30 days)</div>
                    <div class="text-sm text-gray-500">${formatNumber(stats.sales_summary.records_count)} transactions</div>
                </div>
            </div>
            <div class="card">
                <div class="card-body text-center">
                    <div class="text-3xl font-bold text-warning mb-2">${stats.predictions.potential_stockouts_30d}</div>
                    <div class="text-gray-600">Potential Stockouts</div>
                    <div class="text-sm text-gray-500">Next 30 days</div>
                </div>
            </div>
            <div class="card">
                <div class="card-body text-center">
                    <div class="text-3xl font-bold ${stats.overview.active_alerts > 0 ? 'text-error' : 'text-success'} mb-2">${stats.overview.active_alerts}</div>
                    <div class="text-gray-600">Active Alerts</div>
                    <div class="text-sm text-gray-500">Requires attention</div>
                </div>
            </div>
            <div class="card">
                <div class="card-body text-center">
                    <div class="text-3xl font-bold text-secondary mb-2">${formatCurrency(stats.sales_summary.avg_price)}</div>
                    <div class="text-gray-600">Average Price</div>
                    <div class="text-sm text-gray-500">Last 30 days</div>
                </div>
            </div>
        `;
    }
}

function displaySalesTrends(trends) {
    const chartContainer = document.getElementById('sales-trend-chart');
    if (!chartContainer || !trends.daily_trends) return;
    
    const ctx = chartContainer.getContext('2d');
    const labels = trends.daily_trends.map(item => formatDate(item.date));
    const salesData = trends.daily_trends.map(item => item.total_sales);
    const priceData = trends.daily_trends.map(item => item.avg_price);
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Total Sales',
                    data: salesData,
                    borderColor: 'var(--color-primary-600)',
                    backgroundColor: 'var(--color-primary-100)',
                    tension: 0.4,
                    yAxisID: 'y'
                },
                {
                    label: 'Average Price',
                    data: priceData,
                    borderColor: 'var(--color-secondary-600)',
                    backgroundColor: 'var(--color-secondary-100)',
                    tension: 0.4,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Sales Trends (Last 30 Days)'
                },
                legend: {
                    position: 'top',
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Date'
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Sales Units'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Price ($)'
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                }
            }
        }
    });
}

function displayForecastAccuracy(accuracy) {
    const accuracyContainer = document.getElementById('forecast-accuracy');
    if (!accuracyContainer) return;
    
    const mae = accuracy.overall_metrics.mean_absolute_error;
    const mape = accuracy.overall_metrics.mean_absolute_percentage_error;
    const totalPredictions = accuracy.overall_metrics.total_predictions;
    
    accuracyContainer.innerHTML = `
        <div class="text-center">
            <div class="text-2xl font-bold mb-4">Forecast Accuracy</div>
            <div class="grid grid-cols-3 gap-4">
                <div>
                    <div class="text-lg font-semibold text-primary">${formatNumber(mae, 2)}</div>
                    <div class="text-sm text-gray-600">Mean Absolute Error</div>
                </div>
                <div>
                    <div class="text-lg font-semibold text-secondary">${formatPercentage(mape, 1)}</div>
                    <div class="text-sm text-gray-600">Mean Absolute Percentage Error</div>
                </div>
                <div>
                    <div class="text-lg font-semibold text-success">${formatNumber(totalPredictions)}</div>
                    <div class="text-sm text-gray-600">Total Predictions</div>
                </div>
            </div>
        </div>
    `;
}

function setupDashboardEventListeners() {
    // Refresh dashboard data
    const refreshButton = document.getElementById('refresh-dashboard');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            loadDashboardData();
            showToast('Dashboard data refreshed', 'success', 2000);
        });
    }
    
    // Time range selector
    const timeRangeSelect = document.getElementById('time-range-select');
    if (timeRangeSelect) {
        timeRangeSelect.addEventListener('change', function(e) {
            const days = parseInt(e.target.value);
            loadSalesTrends(days);
        });
    }
}

async function loadSalesTrends(days = 30) {
    try {
        const trends = await dashboardAPI.getSalesTrends({ days });
        displaySalesTrends(trends);
    } catch (error) {
        console.error('Error loading sales trends:', error);
        showToast('Failed to load sales trends', 'error');
    }
}

function showDataUploadModal() {
    // Create and show data upload modal
    const modal = createElement('div', 'modal');
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="text-2xl font-bold">Upload Sales Data</h2>
                <button class="close-modal" onclick="closeModal(this)">&times;</button>
            </div>
            <div class="modal-body">
                <div class="mb-4">
                    <p class="text-gray-600 mb-4">
                        Upload your historical sales data in CSV format. 
                        Required columns: date, store_id, sku_id, sales, price, on_hand, promotions_flag
                    </p>
                    <div class="drop-zone" id="file-drop-zone">
                        <div class="text-center">
                            <i class="fas fa-cloud-upload-alt text-4xl text-gray-400 mb-4"></i>
                            <p class="text-lg mb-2">Drop your CSV file here</p>
                            <p class="text-sm text-gray-500">or click to browse</p>
                        </div>
                        <input type="file" id="file-input" accept=".csv,.xlsx" style="display: none;">
                    </div>
                    <div id="upload-progress" class="hidden mt-4">
                        <div class="progress-bar">
                            <div class="progress-fill" id="upload-progress-bar"></div>
                        </div>
                        <div class="text-sm text-gray-600 mt-2" id="upload-status"></div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-secondary" onclick="closeModal(this)">Cancel</button>
                <button class="btn-primary" id="upload-button" disabled>Upload</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    setupFileUpload();
}

function setupFileUpload() {
    const dropZone = document.getElementById('file-drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadButton = document.getElementById('upload-button');
    
    // Click to select file
    dropZone.addEventListener('click', () => fileInput.click());
    
    // Drag and drop functionality
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });
    
    dropZone.addEventListener('drop', handleDrop, false);
    fileInput.addEventListener('change', handleFileSelect, false);
    uploadButton.addEventListener('click', handleUpload, false);
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight() {
        dropZone.classList.add('bg-primary-50', 'border-primary-300');
    }
    
    function unhighlight() {
        dropZone.classList.remove('bg-primary-50', 'border-primary-300');
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }
    
    function handleFileSelect(e) {
        const files = e.target.files;
        handleFiles(files);
    }
    
    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            const validation = validateFile(file, ['csv', 'xlsx'], 50 * 1024 * 1024); // 50MB limit
            
            if (validation.valid) {
                uploadButton.disabled = false;
                uploadButton.dataset.file = JSON.stringify({
                    name: file.name,
                    size: file.size,
                    type: file.type
                });
                
                dropZone.innerHTML = `
                    <div class="text-center">
                        <i class="fas fa-file-csv text-4xl text-green-500 mb-4"></i>
                        <p class="text-lg font-semibold">${file.name}</p>
                        <p class="text-sm text-gray-500">${formatFileSize(file.size)}</p>
                    </div>
                `;
            } else {
                showToast(validation.errors.join(', '), 'error');
            }
        }
    }
    
    async function handleUpload() {
        const fileData = JSON.parse(uploadButton.dataset.file || '{}');
        const file = fileInput.files[0];
        
        if (!file) {
            showToast('Please select a file to upload', 'warning');
            return;
        }
        
        try {
            const progressContainer = document.getElementById('upload-progress');
            const progressBar = document.getElementById('upload-progress-bar');
            const statusText = document.getElementById('upload-status');
            
            progressContainer.classList.remove('hidden');
            uploadButton.disabled = true;
            
            const result = await dataAPI.uploadData(file, (percentage) => {
                progressBar.style.width = `${percentage}%`;
                statusText.textContent = `Uploading... ${Math.round(percentage)}%`;
            });
            
            showToast('File uploaded successfully! Processing started.', 'success');
            closeAllModals();
            
            // Optionally redirect to uploads page or refresh current data
            
        } catch (error) {
            console.error('Upload error:', error);
            showToast('Upload failed: ' + error.message, 'error');
            uploadButton.disabled = false;
        }
    }
}

function showPredictionsView() {
    showToast('Predictions view coming soon!', 'info');
}

function showAlertsView() {
    showToast('Alerts view coming soon!', 'info');
}

function closeAllModals() {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.style.opacity = '0';
        setTimeout(() => {
            if (modal.parentNode) {
                modal.parentNode.removeChild(modal);
            }
        }, 300);
    });
}

function closeModal(element) {
    const modal = element.closest('.modal');
    if (modal) {
        closeAllModals();
    }
}

// Handle logout
function logout() {
    authManager.logout();
}

// Handle login form
async function handleLoginForm(form) {
    const formData = new FormData(form);
    const credentials = {
        username: formData.get('username'),
        password: formData.get('password')
    };
    
    try {
        showLoading();
        const result = await login(credentials);
        
        if (result.success) {
            showToast('Login successful!', 'success');
            window.location.reload(); // Refresh to update auth state
        } else {
            const errorElement = document.getElementById('login-error');
            if (errorElement) {
                errorElement.textContent = result.error;
                errorElement.classList.remove('hidden');
            }
        }
    } catch (error) {
        console.error('Login error:', error);
        showToast('Login failed. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

// Global error handler
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    showToast('An unexpected error occurred', 'error');
});

// Unhandled promise rejection handler
window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    showToast('An unexpected error occurred', 'error');
});