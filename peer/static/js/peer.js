/**
 * Scripts JavaScript pour l'application Peer P2P
 */

// ========== Variables globales ==========
let notificationTimeout;
let statsUpdateInterval;

// ========== Initialisation ==========
$(document).ready(function() {
    console.log('Application Peer P2P chargée');
    
    // Initialiser les tooltips Bootstrap
    initTooltips();
    
    // Démarrer la mise à jour des stats
    startStatsUpdate();
    
    // Gérer la fermeture des alertes
    initAlertHandlers();
});

// ========== Tooltips ==========
function initTooltips() {
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// ========== Alertes ==========
function initAlertHandlers() {
    $('.alert .btn-close').on('click', function() {
        $(this).closest('.alert').fadeOut(300, function() {
            $(this).remove();
        });
    });
}

// ========== Notifications ==========
function showNotification(type, message, duration = 5000) {
    // Types: success, error, info, warning
    
    const iconMap = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-triangle',
        'info': 'fa-info-circle',
        'warning': 'fa-exclamation-circle'
    };
    
    const bgMap = {
        'success': 'bg-success',
        'error': 'bg-danger',
        'info': 'bg-info',
        'warning': 'bg-warning'
    };
    
    const icon = iconMap[type] || 'fa-info-circle';
    const bg = bgMap[type] || 'bg-primary';
    
    // Créer le conteneur de toast s'il n'existe pas
    if ($('.toast-container').length === 0) {
        $('body').append('<div class="toast-container"></div>');
    }
    
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white ${bg} border-0 slide-in" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas ${icon} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    $('.toast-container').append(toastHtml);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: duration
    });
    
    toast.show();
    
    // Supprimer après fermeture
    toastElement.addEventListener('hidden.bs.toast', function() {
        $(this).remove();
    });
}

// ========== Mise à jour des statistiques ==========
function startStatsUpdate() {
    updateNavbarStats();
    updateDashboardStats();
    
    // Mettre à jour toutes les 5 secondes
    statsUpdateInterval = setInterval(function() {
        updateNavbarStats();
        updateDashboardStats();
    }, 5000);
}

function stopStatsUpdate() {
    if (statsUpdateInterval) {
        clearInterval(statsUpdateInterval);
    }
}

function updateNavbarStats() {
    // Statut du tracker
    $.get('/api/tracker/status', function(data) {
        if (data.success && data.status.is_connected) {
            $('#tracker-status')
                .removeClass('text-danger text-warning')
                .addClass('text-success')
                .attr('title', 'Connecté au tracker');
            $('#tracker-status-text').text('Tracker');
        } else {
            $('#tracker-status')
                .removeClass('text-success')
                .addClass('text-danger')
                .attr('title', 'Déconnecté du tracker');
            $('#tracker-status-text').text('Hors ligne');
        }
    }).fail(function() {
        // En cas d'erreur, considérer comme déconnecté
        $('#tracker-status')
            .removeClass('text-success')
            .addClass('text-danger')
            .attr('title', 'Erreur de connexion');
        $('#tracker-status-text').text('Erreur');
    });
    
    // Nombre de peers
    $.get('/api/peers/discovered', function(data) {
        if (data.success) {
            $('#peers-count').text(data.peers.length);
        }
    }).fail(function() {
        // Ignorer silencieusement l'erreur
        console.warn('Erreur récupération peers');
    });
}

function updateDashboardStats() {
    // Uniquement sur la page d'accueil
    if (!$('.dashboard-card').length) return;
    
    $.get('/api/statistics', function(data) {
        if (data.success) {
            const stats = data.statistics;
            
            // Fichiers partagés
            if (stats.files) {
                $('#stats-files-count').text(stats.files.total_files || 0);
                $('#stats-files-size').text(stats.files.total_size_formatted || '0 B');
            }
            
            // Téléchargements
            if (stats.downloads) {
                $('#stats-downloads-total').text(stats.downloads.total || 0);
                $('#stats-downloads-completed').text(stats.downloads.completed || 0);
            }
            
            // Peers découverts
            if (stats.discovery) {
                $('#stats-peers-discovered').text(stats.discovery.peers_count || 0);
            }
            
            // Cache
            if (stats.cache) {
                $('#stats-cache-files').text(stats.cache.files_count || 0);
            }
        }
    }).fail(function(xhr, status, error) {
        // Erreur silencieuse - ne pas spammer l'utilisateur
        console.warn('Erreur récupération stats:', status, error);
    });
}

// ========== Formatage ==========
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDuration(seconds) {
    if (seconds < 60) {
        return Math.round(seconds) + ' s';
    } else if (seconds < 3600) {
        return Math.round(seconds / 60) + ' min';
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.round((seconds % 3600) / 60);
        return hours + ' h ' + minutes + ' min';
    }
}

function formatDate(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('fr-FR');
}

// ========== Confirmation ==========
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// ========== Copie dans le presse-papier ==========
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showNotification('success', 'Copié dans le presse-papier');
    }).catch(function() {
        showNotification('error', 'Échec de la copie');
    });
}

// ========== Gestion des erreurs AJAX ==========
$(document).ajaxError(function(event, jqxhr, settings, thrownError) {
    console.error('Erreur AJAX:', thrownError);
    
    if (jqxhr.status === 0) {
        showNotification('error', 'Impossible de contacter le serveur');
    } else if (jqxhr.status === 404) {
        showNotification('error', 'Ressource non trouvée');
    } else if (jqxhr.status === 500) {
        showNotification('error', 'Erreur serveur');
    } else {
        showNotification('error', 'Une erreur est survenue');
    }
});

// ========== Nettoyage à la fermeture ==========
$(window).on('beforeunload', function() {
    stopStatsUpdate();
});

// ========== Export des fonctions utilitaires ==========
window.peerApp = {
    showNotification: showNotification,
    formatFileSize: formatFileSize,
    formatDuration: formatDuration,
    formatDate: formatDate,
    confirmAction: confirmAction,
    copyToClipboard: copyToClipboard
};