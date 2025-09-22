/**
 * API utility functions for SmartInventory
 */

class APIError extends Error {
    constructor(message, status, response) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.response = response;
    }
}

class APIClient {
    constructor() {
        this.baseURL = '';
        this.defaultHeaders = {
            'Content-Type': 'application/json',
        };
    }

    getAuthHeaders() {
        const token = localStorage.getItem('auth_token');
        return token ? { 'Authorization': `Token ${token}` } : {};
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        
        const config = {
            headers: {
                ...this.defaultHeaders,
                ...this.getAuthHeaders(),
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            // Handle different response types
            let data;
            const contentType = response.headers.get('content-type');
            
            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else {
                data = await response.text();
            }

            if (!response.ok) {
                throw new APIError(
                    data.message || data.error || `HTTP ${response.status}`,
                    response.status,
                    data
                );
            }

            return data;
        } catch (error) {
            if (error instanceof APIError) {
                throw error;
            }
            throw new APIError(
                'Network error or server unavailable',
                0,
                error.message
            );
        }
    }

    // HTTP Methods
    async get(endpoint, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        return this.request(url, { method: 'GET' });
    }

    async post(endpoint, data = null, options = {}) {
        const config = {
            method: 'POST',
            ...options
        };

        if (data) {
            if (data instanceof FormData) {
                delete config.headers;
                config.body = data;
            } else {
                config.body = JSON.stringify(data);
            }
        }

        return this.request(endpoint, config);
    }

    async put(endpoint, data = null) {
        return this.request(endpoint, {
            method: 'PUT',
            body: data ? JSON.stringify(data) : null
        });
    }

    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    // File upload helper
    async uploadFile(endpoint, file, progressCallback = null) {
        const formData = new FormData();
        formData.append('file', file);

        const xhr = new XMLHttpRequest();
        
        return new Promise((resolve, reject) => {
            xhr.upload.addEventListener('progress', (event) => {
                if (event.lengthComputable && progressCallback) {
                    const percentComplete = (event.loaded / event.total) * 100;
                    progressCallback(percentComplete);
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (e) {
                        resolve(xhr.responseText);
                    }
                } else {
                    reject(new APIError(
                        `Upload failed: ${xhr.statusText}`,
                        xhr.status,
                        xhr.responseText
                    ));
                }
            });

            xhr.addEventListener('error', () => {
                reject(new APIError('Upload failed', 0, 'Network error'));
            });

            xhr.open('POST', `${this.baseURL}${endpoint}`);
            
            // Add auth header
            const authHeaders = this.getAuthHeaders();
            Object.keys(authHeaders).forEach(key => {
                xhr.setRequestHeader(key, authHeaders[key]);
            });

            xhr.send(formData);
        });
    }
}

// Create global API client instance
const api = new APIClient();

// API endpoint functions
const apiCall = async (endpoint, method = 'GET', data = null, options = {}) => {
    try {
        switch (method.toLowerCase()) {
            case 'get':
                return await api.get(endpoint, data);
            case 'post':
                return await api.post(endpoint, data, options);
            case 'put':
                return await api.put(endpoint, data);
            case 'delete':
                return await api.delete(endpoint);
            default:
                throw new Error(`Unsupported HTTP method: ${method}`);
        }
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
};

// Specific API functions
const authAPI = {
    login: async (credentials) => {
        return api.post('/api/auth/login/', credentials);
    },
    
    logout: async () => {
        return api.post('/api/auth/logout/');
    },
    
    getProfile: async () => {
        return api.get('/api/auth/profile/');
    },
    
    changePassword: async (passwordData) => {
        return api.put('/api/auth/change-password/', passwordData);
    }
};

const dataAPI = {
    uploadData: async (file, progressCallback) => {
        return api.uploadFile('/api/data/upload/', file, progressCallback);
    },
    
    getUploads: async (params = {}) => {
        return api.get('/api/data/uploads/', params);
    },
    
    getUploadStatus: async (uploadId) => {
        return api.get(`/api/data/uploads/${uploadId}/status/`);
    },
    
    getSalesData: async (params = {}) => {
        return api.get('/api/data/sales/', params);
    },
    
    getQualityReports: async (params = {}) => {
        return api.get('/api/data/quality/reports/', params);
    },
    
    triggerQualityCheck: async (dateRange) => {
        return api.post('/api/data/quality/check/', dateRange);
    }
};

const forecastAPI = {
    getModels: async (params = {}) => {
        return api.get('/api/forecasting/models/', params);
    },
    
    getPredictions: async (params = {}) => {
        return api.get('/api/forecasting/predictions/', params);
    },
    
    predictDemand: async (params) => {
        return api.get('/api/forecasting/predict/', params);
    },
    
    batchPredict: async (data) => {
        return api.post('/api/forecasting/predict/batch/', data);
    },
    
    retrainModel: async (data = {}) => {
        return api.post('/api/forecasting/models/retrain/', data);
    },
    
    getBatchJobs: async (params = {}) => {
        return api.get('/api/forecasting/batch-jobs/', params);
    },
    
    getBatchJobStatus: async (jobId) => {
        return api.get(`/api/forecasting/batch-jobs/${jobId}/status/`);
    },
    
    getAlerts: async (params = {}) => {
        return api.get('/api/forecasting/alerts/', params);
    },
    
    acknowledgeAlert: async (alertId) => {
        return api.post(`/api/forecasting/alerts/${alertId}/acknowledge/`);
    }
};

const dashboardAPI = {
    getStats: async () => {
        return api.get('/api/dashboard/stats/');
    },
    
    getSalesTrends: async (params = {}) => {
        return api.get('/api/dashboard/sales-trends/', params);
    },
    
    getForecastAccuracy: async () => {
        return api.get('/api/dashboard/forecast-accuracy/');
    }
};

// Response interceptor for handling auth errors
const originalRequest = api.request.bind(api);
api.request = async function(endpoint, options = {}) {
    try {
        return await originalRequest(endpoint, options);
    } catch (error) {
        if (error.status === 401) {
            // Token expired or invalid
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user_data');
            
            // Redirect to login if not already there
            if (!window.location.pathname.includes('login') && !window.location.pathname === '/') {
                showToast('Session expired. Please login again.', 'warning');
                window.location.href = '/';
            }
        }
        throw error;
    }
};

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { api, apiCall, authAPI, dataAPI, forecastAPI, dashboardAPI };
}