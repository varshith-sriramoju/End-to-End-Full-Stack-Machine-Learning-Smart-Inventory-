/**
 * Utility functions for SmartInventory
 */

// Toast notification system
class ToastManager {
    constructor() {
        this.container = document.getElementById('toast-container');
        if (!this.container) {
            this.createContainer();
        }
    }

    createContainer() {
        this.container = document.createElement('div');
        this.container.id = 'toast-container';
        this.container.className = 'fixed top-4 right-4 z-50 space-y-2';
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = 5000) {
        const toast = this.createToast(message, type);
        this.container.appendChild(toast);

        // Auto-remove toast after duration
        if (duration > 0) {
            setTimeout(() => {
                this.remove(toast);
            }, duration);
        }

        return toast;
    }

    createToast(message, type) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const icon = this.getIcon(type);
        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '×';
        closeBtn.className = 'ml-auto text-lg font-bold opacity-60 hover:opacity-100';
        closeBtn.onclick = () => this.remove(toast);

        toast.innerHTML = `
            <i class="${icon}"></i>
            <span class="flex-1">${message}</span>
        `;
        toast.appendChild(closeBtn);

        return toast;
    }

    getIcon(type) {
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };
        return icons[type] || icons.info;
    }

    remove(toast) {
        if (toast && toast.parentNode) {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }
    }

    clear() {
        while (this.container.firstChild) {
            this.container.removeChild(this.container.firstChild);
        }
    }
}

// Global toast instance
const toastManager = new ToastManager();
const showToast = (message, type, duration) => toastManager.show(message, type, duration);

// Loading state management
let loadingCount = 0;
const loadingSpinner = document.getElementById('loading-spinner');

const showLoading = () => {
    loadingCount++;
    if (loadingSpinner) {
        loadingSpinner.style.display = 'flex';
    }
};

const hideLoading = () => {
    loadingCount = Math.max(0, loadingCount - 1);
    if (loadingCount === 0 && loadingSpinner) {
        loadingSpinner.style.display = 'none';
    }
};

// Date formatting utilities
const formatDate = (date, format = 'short') => {
    if (!date) return '';
    
    const d = typeof date === 'string' ? new Date(date) : date;
    
    const options = {
        short: { year: 'numeric', month: 'short', day: 'numeric' },
        long: { year: 'numeric', month: 'long', day: 'numeric' },
        datetime: { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }
    };
    
    return d.toLocaleDateString('en-US', options[format] || options.short);
};

const formatDateTime = (date) => formatDate(date, 'datetime');

const getRelativeTime = (date) => {
    if (!date) return '';
    
    const now = new Date();
    const then = typeof date === 'string' ? new Date(date) : date;
    const diffMs = now - then;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    
    return formatDate(date);
};

// Number formatting utilities
const formatNumber = (num, decimals = 0) => {
    if (num === null || num === undefined || isNaN(num)) return '0';
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(num);
};

const formatCurrency = (amount, currency = 'USD') => {
    if (amount === null || amount === undefined || isNaN(amount)) return '$0.00';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency
    }).format(amount);
};

const formatPercentage = (value, decimals = 1) => {
    if (value === null || value === undefined || isNaN(value)) return '0%';
    return `${formatNumber(value, decimals)}%`;
};

// File size formatting
const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// URL and query parameter utilities
const getQueryParam = (name) => {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
};

const setQueryParam = (name, value) => {
    const url = new URL(window.location);
    if (value) {
        url.searchParams.set(name, value);
    } else {
        url.searchParams.delete(name);
    }
    window.history.replaceState({}, '', url);
};

const buildQueryString = (params) => {
    const filtered = Object.entries(params)
        .filter(([_, value]) => value !== null && value !== undefined && value !== '')
        .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`);
    
    return filtered.length > 0 ? `?${filtered.join('&')}` : '';
};

// Validation utilities
const validateEmail = (email) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
};

const validateRequired = (value) => {
    return value !== null && value !== undefined && value.toString().trim() !== '';
};

const validateNumber = (value, min = null, max = null) => {
    const num = parseFloat(value);
    if (isNaN(num)) return false;
    if (min !== null && num < min) return false;
    if (max !== null && num > max) return false;
    return true;
};

const validateDate = (dateString) => {
    const date = new Date(dateString);
    return date instanceof Date && !isNaN(date);
};

// File validation
const validateFile = (file, allowedTypes = [], maxSize = null) => {
    const errors = [];
    
    if (allowedTypes.length > 0) {
        const fileExtension = file.name.split('.').pop().toLowerCase();
        if (!allowedTypes.includes(fileExtension)) {
            errors.push(`File type .${fileExtension} not allowed. Allowed types: ${allowedTypes.join(', ')}`);
        }
    }
    
    if (maxSize && file.size > maxSize) {
        errors.push(`File size ${formatFileSize(file.size)} exceeds maximum ${formatFileSize(maxSize)}`);
    }
    
    return {
        valid: errors.length === 0,
        errors: errors
    };
};

// DOM utilities
const createElement = (tag, className = '', innerHTML = '') => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (innerHTML) element.innerHTML = innerHTML;
    return element;
};

const removeElement = (element) => {
    if (element && element.parentNode) {
        element.parentNode.removeChild(element);
    }
};

const toggleClass = (element, className, force = null) => {
    if (force === null) {
        element.classList.toggle(className);
    } else {
        element.classList.toggle(className, force);
    }
};

// Local storage utilities with error handling
const setLocalStorage = (key, value) => {
    try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
    } catch (error) {
        console.error('Error saving to localStorage:', error);
        return false;
    }
};

const getLocalStorage = (key, defaultValue = null) => {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
        console.error('Error reading from localStorage:', error);
        return defaultValue;
    }
};

const removeLocalStorage = (key) => {
    try {
        localStorage.removeItem(key);
        return true;
    } catch (error) {
        console.error('Error removing from localStorage:', error);
        return false;
    }
};

// Debounce utility for search inputs
const debounce = (func, wait) => {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

// Throttle utility for scroll events
const throttle = (func, limit) => {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
};

// Progress bar utility
class ProgressBar {
    constructor(element) {
        this.element = element;
        this.bar = element.querySelector('.progress-fill') || this.createProgressBar();
        this.percentage = 0;
    }

    createProgressBar() {
        this.element.className = 'progress-bar';
        const fill = createElement('div', 'progress-fill');
        this.element.appendChild(fill);
        return fill;
    }

    setProgress(percentage) {
        this.percentage = Math.max(0, Math.min(100, percentage));
        this.bar.style.width = `${this.percentage}%`;
        this.element.setAttribute('aria-valuenow', this.percentage);
    }

    getProgress() {
        return this.percentage;
    }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        showToast, showLoading, hideLoading,
        formatDate, formatDateTime, getRelativeTime,
        formatNumber, formatCurrency, formatPercentage, formatFileSize,
        getQueryParam, setQueryParam, buildQueryString,
        validateEmail, validateRequired, validateNumber, validateDate, validateFile,
        createElement, removeElement, toggleClass,
        setLocalStorage, getLocalStorage, removeLocalStorage,
        debounce, throttle, ProgressBar
    };
}