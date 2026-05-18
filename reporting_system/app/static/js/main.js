/**
 * Main JavaScript for Internal Reporting System
 * Vanilla JS only - no external libraries
 */

(function() {
    'use strict';

    /**
     * Initialize the application when DOM is ready
     */
    document.addEventListener('DOMContentLoaded', function() {
        initFlashMessages();
        initFormValidation();
        initNumberInputs();
    });

    /**
     * Auto-dismiss flash messages after a delay
     */
    function initFlashMessages() {
        const flashMessages = document.querySelectorAll('.flash');
        
        flashMessages.forEach(function(flash) {
            // Auto-dismiss after 5 seconds
            setTimeout(function() {
                fadeOut(flash);
            }, 5000);
        });
    }

    /**
     * Fade out and remove an element
     */
    function fadeOut(element) {
        element.style.transition = 'opacity 0.3s ease-out';
        element.style.opacity = '0';
        
        setTimeout(function() {
            element.remove();
        }, 300);
    }

    /**
     * Initialize basic form validation
     */
    function initFormValidation() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(function(form) {
            form.addEventListener('submit', function(e) {
                const requiredFields = form.querySelectorAll('[required]');
                let isValid = true;
                
                requiredFields.forEach(function(field) {
                    if (!field.value.trim()) {
                        isValid = false;
                        highlightError(field);
                    } else {
                        clearError(field);
                    }
                });
                
                if (!isValid) {
                    e.preventDefault();
                    showNotification('Please fill in all required fields.', 'error');
                }
            });
        });
    }

    /**
     * Highlight a field with an error
     */
    function highlightError(field) {
        field.style.borderColor = 'var(--color-error)';
        field.style.boxShadow = '0 0 0 3px rgba(220, 38, 38, 0.1)';
    }

    /**
     * Clear error highlighting from a field
     */
    function clearError(field) {
        field.style.borderColor = '';
        field.style.boxShadow = '';
    }

    /**
     * Initialize number input enhancements
     */
    function initNumberInputs() {
        const numberInputs = document.querySelectorAll('input[type="number"]');
        
        numberInputs.forEach(function(input) {
            // Prevent scroll wheel from changing value
            input.addEventListener('wheel', function(e) {
                if (document.activeElement === this) {
                    e.preventDefault();
                }
            });
            
            // Select all on focus
            input.addEventListener('focus', function() {
                this.select();
            });
        });
    }

    /**
     * Show a notification message
     */
    function showNotification(message, type) {
        type = type || 'info';
        
        // Check if flash messages container exists
        let container = document.querySelector('.flash-messages');
        
        if (!container) {
            container = document.createElement('div');
            container.className = 'flash-messages';
            
            const mainContent = document.querySelector('.main-content');
            if (mainContent) {
                mainContent.parentNode.insertBefore(container, mainContent);
            } else {
                document.body.insertBefore(container, document.body.firstChild);
            }
        }
        
        // Create flash message
        const flash = document.createElement('div');
        flash.className = 'flash flash-' + type;
        flash.innerHTML = message + 
            '<button type="button" class="flash-close" onclick="this.parentElement.remove()">×</button>';
        
        container.appendChild(flash);
        
        // Auto-dismiss
        setTimeout(function() {
            fadeOut(flash);
        }, 5000);
    }

    /**
     * Confirm before destructive actions
     */
    window.confirmAction = function(message) {
        return confirm(message || 'Are you sure you want to proceed?');
    };

    /**
     * Toggle visibility of an element
     */
    window.toggleElement = function(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = element.style.display === 'none' ? 'block' : 'none';
        }
    };

    /**
     * Format a number for display
     */
    window.formatNumber = function(value, decimals) {
        decimals = decimals !== undefined ? decimals : 2;
        
        if (value === null || value === undefined || isNaN(value)) {
            return 'N/A';
        }
        
        return Number(value).toLocaleString(undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: decimals
        });
    };

    /**
     * Debounce function for rate-limiting
     */
    window.debounce = function(func, wait) {
        let timeout;
        return function executedFunction() {
            const context = this;
            const args = arguments;
            
            clearTimeout(timeout);
            timeout = setTimeout(function() {
                func.apply(context, args);
            }, wait);
        };
    };

})();
