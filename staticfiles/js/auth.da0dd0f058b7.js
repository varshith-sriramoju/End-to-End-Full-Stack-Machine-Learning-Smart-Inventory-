/**
 * Authentication utilities for SmartInventory
 */

class AuthManager {
    constructor() {
        this.tokenKey = 'auth_token';
        this.userDataKey = 'user_data';
        this.currentUser = null;
        this.isAuthenticated = false;
        
        // Initialize auth state
        this.initializeAuth();
    }

    initializeAuth() {
        const token = localStorage.getItem(this.tokenKey);
        const userData = localStorage.getItem(this.userDataKey);
        
        if (token && userData) {
            try {
                this.currentUser = JSON.parse(userData);
                this.isAuthenticated = true;
                this.updateUI();
            } catch (error) {
                console.error('Error parsing user data:', error);
                this.logout();
            }
        }
    }

    async login(credentials) {
        try {
            const response = await authAPI.login(credentials);
            
            if (response.token && response.user) {
                // Store auth data
                localStorage.setItem(this.tokenKey, response.token);
                localStorage.setItem(this.userDataKey, JSON.stringify(response.user));
                
                this.currentUser = response.user;
                this.isAuthenticated = true;
                this.updateUI();
                
                return { success: true, user: response.user };
            } else {
                return { success: false, error: 'Invalid response format' };
            }
        } catch (error) {
            console.error('Login error:', error);
            return { 
                success: false, 
                error: error.response?.message || error.message || 'Login failed'
            };
        }
    }

    async logout() {
        try {
            // Call logout API to invalidate token on server
            await authAPI.logout();
        } catch (error) {
            console.error('Logout API call failed:', error);
            // Continue with local logout even if API call fails
        }
        
        // Clear local storage
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem(this.userDataKey);
        
        this.currentUser = null;
        this.isAuthenticated = false;
        
        // Redirect to home page
        window.location.href = '/';
    }

    getToken() {
        return localStorage.getItem(this.tokenKey);
    }

    getCurrentUser() {
        return this.currentUser;
    }

    isLoggedIn() {
        return this.isAuthenticated && this.getToken();
    }

    hasRole(role) {
        if (!this.currentUser || !this.currentUser.profile) {
            return false;
        }
        return this.currentUser.profile.role === role;
    }

    isAdmin() {
        return this.hasRole('admin');
    }

    isManager() {
        return this.hasRole('manager');
    }

    isAnalyst() {
        return this.hasRole('analyst');
    }

    canAccessStore(storeId) {
        if (this.isAdmin()) {
            return true;
        }
        
        if (!this.currentUser || !this.currentUser.profile || !this.currentUser.profile.stores) {
            return false;
        }
        
        return this.currentUser.profile.stores.includes(storeId);
    }

    updateUI() {
        if (this.isAuthenticated && this.currentUser) {
            // Update username display
            const usernameElements = document.querySelectorAll('#username');
            usernameElements.forEach(el => {
                el.textContent = this.currentUser.first_name || this.currentUser.username;
            });

            // Update user info display
            const userInfoElements = document.querySelectorAll('#user-info');
            userInfoElements.forEach(el => {
                const role = this.currentUser.profile?.role || 'user';
                el.innerHTML = `
                    <i class="fas fa-user-circle mr-1"></i>
                    <span>${this.currentUser.first_name || this.currentUser.username}</span>
                    <span class="text-xs text-gray-500 ml-1">(${role})</span>
                `;
            });

            // Show/hide role-specific elements
            this.updateRoleBasedUI();
        }
    }

    updateRoleBasedUI() {
        // Hide admin-only elements for non-admin users
        const adminElements = document.querySelectorAll('[data-role="admin"]');
        adminElements.forEach(el => {
            el.style.display = this.isAdmin() ? 'block' : 'none';
        });

        // Hide manager-only elements for analysts
        const managerElements = document.querySelectorAll('[data-role="manager"]');
        managerElements.forEach(el => {
            el.style.display = (this.isAdmin() || this.isManager()) ? 'block' : 'none';
        });
    }

    async changePassword(passwordData) {
        try {
            await authAPI.changePassword(passwordData);
            return { success: true };
        } catch (error) {
            console.error('Change password error:', error);
            return {
                success: false,
                error: error.response?.message || error.message || 'Password change failed'
            };
        }
    }

    async refreshProfile() {
        try {
            const profile = await authAPI.getProfile();
            this.currentUser = profile;
            localStorage.setItem(this.userDataKey, JSON.stringify(profile));
            this.updateUI();
            return { success: true, user: profile };
        } catch (error) {
            console.error('Profile refresh error:', error);
            return {
                success: false,
                error: error.response?.message || error.message || 'Profile refresh failed'
            };
        }
    }
}

// Create global auth manager instance
const authManager = new AuthManager();

// Global functions for backward compatibility
const login = (credentials) => authManager.login(credentials);
const logout = () => authManager.logout();
const isAuthenticated = () => authManager.isLoggedIn();
const getCurrentUser = () => authManager.getCurrentUser();
const hasRole = (role) => authManager.hasRole(role);

// Auto-redirect to dashboard if already authenticated
document.addEventListener('DOMContentLoaded', function() {
    // Only redirect if we're on the home page and authenticated
    if (window.location.pathname === '/' && authManager.isLoggedIn()) {
        // Don't redirect if there's a hash in the URL (might be intentional)
        if (!window.location.hash) {
            window.location.href = '/dashboard/';
        }
    }
});

// Handle auth state changes across tabs
window.addEventListener('storage', function(e) {
    if (e.key === authManager.tokenKey || e.key === authManager.userDataKey) {
        // Auth state changed in another tab
        authManager.initializeAuth();
        
        // If logged out in another tab, redirect
        if (!authManager.isLoggedIn() && window.location.pathname !== '/') {
            window.location.href = '/';
        }
    }
});

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { authManager, login, logout, isAuthenticated, getCurrentUser, hasRole };
}