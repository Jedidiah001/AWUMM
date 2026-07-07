/**
 * AWUM API Client
 * Wrapper functions for all backend API calls
 * 
 * Protected against re-declaration when views are dynamically loaded
 */

// Guard against re-declaration
if (typeof window.fetchAPI === 'undefined') {
    
    const API_BASE = '';  // Same origin

    /**
     * Generic fetch wrapper with error handling
     */
    window.fetchAPI = async function(endpoint, options = {}) {
        try {
            const response = await fetch(API_BASE + endpoint, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ message: response.statusText }));
                throw new Error(error.message || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    };

    /**
     * GET request wrapper
     */
    window.getAPI = async function(endpoint) {
        return window.fetchAPI(endpoint, { method: 'GET' });
    };

    /**
     * POST request wrapper
     */
    window.postAPI = async function(endpoint, data) {
        return window.fetchAPI(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    };

    /**
     * PUT request wrapper
     */
    window.putAPI = async function(endpoint, data) {
        return window.fetchAPI(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    };

    /**
     * DELETE request wrapper
     */
    window.deleteAPI = async function(endpoint) {
        return window.fetchAPI(endpoint, { method: 'DELETE' });
    };
    
    console.log('✅ AWUM API client loaded');
}

// Also create local references for convenience
const fetchAPI = window.fetchAPI;
const getAPI = window.getAPI;
const postAPI = window.postAPI;
const putAPI = window.putAPI;
const deleteAPI = window.deleteAPI;