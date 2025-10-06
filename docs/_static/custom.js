// Custom JavaScript for Frohlich Experiment Documentation

document.addEventListener('DOMContentLoaded', function() {
    
    // Configuration Generator
    function createConfigGenerator() {
        const generators = document.querySelectorAll('.config-generator');
        
        generators.forEach(generator => {
            const form = generator.querySelector('form');
            const output = generator.querySelector('.config-output');
            
            if (form && output) {
                form.addEventListener('change', function() {
                    updateConfigOutput(form, output);
                });
                
                form.addEventListener('input', function() {
                    updateConfigOutput(form, output);
                });
            }
        });
    }
    
    function updateConfigOutput(form, output) {
        const formData = new FormData(form);
        const config = {};
        
        // Build configuration object
        for (let [key, value] of formData.entries()) {
            // Handle nested properties
            if (key.includes('.')) {
                const keys = key.split('.');
                let current = config;
                for (let i = 0; i < keys.length - 1; i++) {
                    if (!current[keys[i]]) current[keys[i]] = {};
                    current = current[keys[i]];
                }
                current[keys[keys.length - 1]] = value;
            } else {
                config[key] = value;
            }
        }
        
        // Convert to YAML-like format
        const yamlOutput = objectToYaml(config);
        output.textContent = yamlOutput;
        
        // Add syntax highlighting
        if (typeof hljs !== 'undefined') {
            hljs.highlightElement(output);
        }
    }
    
    function objectToYaml(obj, indent = 0) {
        let yaml = '';
        const spaces = '  '.repeat(indent);
        
        for (const [key, value] of Object.entries(obj)) {
            if (typeof value === 'object' && value !== null) {
                yaml += `${spaces}${key}:\n`;
                yaml += objectToYaml(value, indent + 1);
            } else {
                yaml += `${spaces}${key}: ${value}\n`;
            }
        }
        
        return yaml;
    }
    
    // Interactive Tutorials
    function initializeTutorials() {
        const tutorials = document.querySelectorAll('.tutorial-step');
        let currentStep = 0;
        
        tutorials.forEach((tutorial, index) => {
            const nextBtn = tutorial.querySelector('.tutorial-next');
            const prevBtn = tutorial.querySelector('.tutorial-prev');
            
            if (nextBtn) {
                nextBtn.addEventListener('click', function() {
                    showTutorialStep(tutorials, currentStep + 1);
                    currentStep++;
                });
            }
            
            if (prevBtn) {
                prevBtn.addEventListener('click', function() {
                    showTutorialStep(tutorials, currentStep - 1);
                    currentStep--;
                });
            }
            
            // Hide all steps except first
            if (index > 0) {
                tutorial.style.display = 'none';
            }
        });
    }
    
    function showTutorialStep(tutorials, stepIndex) {
        tutorials.forEach((tutorial, index) => {
            tutorial.style.display = index === stepIndex ? 'block' : 'none';
        });
    }
    
    // Enhanced Copy Functionality
    function enhanceCopyButtons() {
        const copyButtons = document.querySelectorAll('.copybtn');
        
        copyButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Add visual feedback
                const originalText = button.textContent;
                button.textContent = '✓ Copied!';
                button.style.background = '#059669';
                
                setTimeout(() => {
                    button.textContent = originalText;
                    button.style.background = '';
                }, 2000);
            });
        });
    }
    
    // Smooth Scrolling for Anchors
    function initializeSmoothScrolling() {
        const anchors = document.querySelectorAll('a[href^="#"]');
        
        anchors.forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                const target = document.querySelector(this.getAttribute('href'));
                
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }
    
    // Search Enhancement
    function enhanceSearch() {
        const searchInput = document.querySelector('input[type="search"]');
        
        if (searchInput) {
            // Add search suggestions
            const searchSuggestions = [
                'configuration',
                'agents',
                'experiments',
                'results analysis',
                'troubleshooting',
                'API reference',
                'installation',
                'quickstart'
            ];
            
            // Create datalist for search suggestions
            const datalist = document.createElement('datalist');
            datalist.id = 'search-suggestions';
            
            searchSuggestions.forEach(suggestion => {
                const option = document.createElement('option');
                option.value = suggestion;
                datalist.appendChild(option);
            });
            
            searchInput.setAttribute('list', 'search-suggestions');
            searchInput.parentNode.appendChild(datalist);
        }
    }
    
    // Table of Contents Enhancement
    function enhanceTOC() {
        const toc = document.querySelector('.toctree-wrapper');
        
        if (toc) {
            // Add expand/collapse functionality
            const tocItems = toc.querySelectorAll('li');
            
            tocItems.forEach(item => {
                const sublist = item.querySelector('ul');
                
                if (sublist) {
                    // Add toggle button
                    const toggle = document.createElement('button');
                    toggle.innerHTML = '▶';
                    toggle.className = 'toc-toggle';
                    toggle.style.cssText = 'background: none; border: none; cursor: pointer; margin-right: 0.5rem;';
                    
                    item.insertBefore(toggle, item.firstChild);
                    
                    toggle.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        
                        if (sublist.style.display === 'none') {
                            sublist.style.display = 'block';
                            toggle.innerHTML = '▼';
                        } else {
                            sublist.style.display = 'none';
                            toggle.innerHTML = '▶';
                        }
                    });
                    
                    // Initially collapse deep levels
                    if (item.parentElement.parentElement.tagName === 'LI') {
                        sublist.style.display = 'none';
                    }
                }
            });
        }
    }
    
    // Progress Indicator for Long Pages
    function addProgressIndicator() {
        const progressBar = document.createElement('div');
        progressBar.id = 'progress-bar';
        progressBar.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 0%;
            height: 3px;
            background: linear-gradient(90deg, #2563eb, #7c3aed);
            z-index: 9999;
            transition: width 0.2s ease;
        `;
        
        document.body.appendChild(progressBar);
        
        window.addEventListener('scroll', function() {
            const scrollTop = window.pageYOffset;
            const docHeight = document.documentElement.scrollHeight - window.innerHeight;
            const scrollPercent = (scrollTop / docHeight) * 100;
            
            progressBar.style.width = scrollPercent + '%';
        });
    }
    
    // Model Comparison Matrix
    function createModelComparison() {
        const comparisons = document.querySelectorAll('.model-comparison');
        
        comparisons.forEach(comparison => {
            // Add sorting functionality
            const headers = comparison.querySelectorAll('th');
            
            headers.forEach((header, index) => {
                if (index > 0) { // Skip first column (model names)
                    header.style.cursor = 'pointer';
                    header.addEventListener('click', function() {
                        sortTable(comparison, index);
                    });
                }
            });
        });
    }
    
    function sortTable(table, column) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        rows.sort((a, b) => {
            const aVal = a.children[column].textContent;
            const bVal = b.children[column].textContent;
            
            // Try to parse as number
            const aNum = parseFloat(aVal);
            const bNum = parseFloat(bVal);
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return bNum - aNum; // Descending for numbers
            } else {
                return aVal.localeCompare(bVal); // Ascending for text
            }
        });
        
        rows.forEach(row => tbody.appendChild(row));
    }
    
    // Lazy Loading for Heavy Content
    function initializeLazyLoading() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const element = entry.target;
                    
                    if (element.dataset.src) {
                        element.src = element.dataset.src;
                        element.removeAttribute('data-src');
                    }
                    
                    if (element.classList.contains('lazy-content')) {
                        element.classList.add('fade-in');
                        element.classList.remove('lazy-content');
                    }
                    
                    observer.unobserve(element);
                }
            });
        });
        
        document.querySelectorAll('[data-src], .lazy-content').forEach(element => {
            observer.observe(element);
        });
    }
    
    // Initialize all features
    createConfigGenerator();
    initializeTutorials();
    enhanceCopyButtons();
    initializeSmoothScrolling();
    enhanceSearch();
    enhanceTOC();
    addProgressIndicator();
    createModelComparison();
    initializeLazyLoading();
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K to focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('input[type="search"]');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // ESC to close modals or clear search
        if (e.key === 'Escape') {
            const searchInput = document.querySelector('input[type="search"]');
            if (searchInput && document.activeElement === searchInput) {
                searchInput.blur();
                searchInput.value = '';
            }
        }
    });
    
    // Add visual feedback for interactive elements
    const interactiveElements = document.querySelectorAll('button, .btn, .tab');
    interactiveElements.forEach(element => {
        element.addEventListener('click', function() {
            this.classList.add('clicked');
            setTimeout(() => {
                this.classList.remove('clicked');
            }, 200);
        });
    });
});

// Utility functions for other scripts to use
window.FrohlichDocs = {
    showNotification: function(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: ${type === 'success' ? '#059669' : type === 'error' ? '#dc2626' : '#2563eb'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    },
    
    copyToClipboard: function(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showNotification('Copied to clipboard!', 'success');
        }).catch(() => {
            this.showNotification('Failed to copy to clipboard', 'error');
        });
    }
};