/**
 * TR4CKING - Main JavaScript
 * Sistema de Gestión de Buses y Encomiendas
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initTooltips();
    
    // Initialize HTMX event listeners
    initHtmx();
    
    // Initialize search with debounce
    initSearch();
    
    // Auto-dismiss alerts
    initAlerts();
});


/**
 * Initialize Bootstrap tooltips
 */
function initTooltips() {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggerList.forEach(function(tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });
}


/**
 * Initialize HTMX event listeners
 */
function initHtmx() {
    // Show loading indicator
    document.body.addEventListener('htmx:beforeRequest', function(event) {
        const target = event.detail.target;
        if (target) {
            target.classList.add('htmx-loading');
        }
    });
    
    // Hide loading indicator
    document.body.addEventListener('htmx:afterRequest', function(event) {
        const target = event.detail.target;
        if (target) {
            target.classList.remove('htmx-loading');
        }
    });
    
    // Reinitialize tooltips after HTMX swap
    document.body.addEventListener('htmx:afterSwap', function() {
        initTooltips();
    });
}


/**
 * Initialize search with debounce
 */
function initSearch() {
    const searchInputs = document.querySelectorAll('input[name="search"]');
    
    searchInputs.forEach(function(input) {
        let timeout = null;
        
        input.addEventListener('input', function() {
            clearTimeout(timeout);
            
            // Visual feedback
            const form = this.closest('form');
            const button = form ? form.querySelector('button[type="submit"]') : null;
            
            if (button) {
                button.innerHTML = '<span class="spinner"></span>';
            }
            
            // Debounce submit (if using HTMX, this triggers automatically)
            timeout = setTimeout(function() {
                if (button) {
                    button.innerHTML = '<i class="bi bi-funnel me-2"></i>Filtrar';
                }
            }, 500);
        });
    });
}


/**
 * Auto-dismiss alerts after 5 seconds
 */
function initAlerts() {
    const alerts = document.querySelectorAll('.alert-dismissible');
    
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });
}


/**
 * Format number as currency (Guaraníes)
 */
function formatCurrency(number) {
    return new Intl.NumberFormat('es-PY', {
        style: 'currency',
        currency: 'PYG',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(number);
}


/**
 * Format date for display
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('es-PY', {
        dateStyle: 'medium',
        timeStyle: 'short'
    }).format(date);
}


/**
 * Confirm action dialog
 */
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}


/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    // Add to container or create one
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
    }
    
    container.appendChild(toast);
    
    // Initialize and show
    const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
    bsToast.show();
    
    // Remove after hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}
