/**
 * H₂SENSE — Global Application Helpers & Toast Notifications
 */

window.H2Sense = {
    showNotification: function(message, type = 'info') {
        const toastContainer = document.getElementById('toastContainer') || this.createToastContainer();
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show shadow-lg border-0`;
        toast.style.minWidth = '300px';
        toast.style.background = type === 'success' ? '#065f46' : (type === 'error' ? '#991b1b' : '#1e293b');
        toast.style.color = '#ffffff';
        toast.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fa-solid ${type === 'success' ? 'fa-circle-check' : (type === 'error' ? 'fa-triangle-exclamation' : 'fa-circle-info')} me-2 fs-5"></i>
                <div class="flex-grow-1 small">${message}</div>
                <button type="button" class="btn-close btn-close-white ms-2" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            if (toast && toast.parentNode) {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 250);
            }
        }, 4500);
    },

    createToastContainer: function() {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.position = 'fixed';
        container.style.bottom = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        container.style.display = 'flex';
        container.style.flexDirection = 'column';
        container.style.gap = '10px';
        document.body.appendChild(container);
        return container;
    }
};
