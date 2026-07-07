/**
 * Championship Management JavaScript
 * STEP 23: Prestige tracking integration
 */

// Add prestige display to championship cards
function renderChampionshipCard(champ) {
    var champId = champ.id || champ.title_id;
    var tierClass = 'tier-' + champ.title_type.toLowerCase().replace(' ', '-');
    
    // STEP 23: Prestige visual indicator
    var prestigeClass = champ.prestige >= 70 ? 'prestige-high' : 
                       champ.prestige >= 40 ? 'prestige-medium' : 'prestige-low';
    
    var prestigeTier = getPrestigeTier(champ.prestige);
    var prestigeColor = getPrestigeColor(champ.prestige);
    
    var badges = '';
    if (champ.is_vacant) {
        badges += '<span class="vacant-badge me-1">VACANT</span>';
    }
    if (champ.has_interim_champion) {
        badges += '<span class="interim-badge me-1">INTERIM</span>';
    }
    if (champ.is_custom) {
        badges += '<span class="custom-badge me-1">CUSTOM</span>';
    }
    if (champ.retired) {
        badges += '<span class="retired-badge me-1">RETIRED</span>';
    }
    
    // STEP 23: Add prestige tier badge
    badges += '<span class="badge bg-' + prestigeColor + ' ms-1">' + prestigeTier + '</span>';
    
    var situation = situations.find(function(s) { return s.title_id === champId; });
    var hasIssues = situation && situation.situation_type !== 'normal';
    var issueIcon = hasIssues ? '<i class="bi bi-exclamation-triangle text-warning float-end"></i>' : '';
    
    var championDisplay = '';
    if (champ.is_vacant) {
        championDisplay = '<em class="text-warning">Vacant</em>';
    } else if (champ.has_interim_champion) {
        championDisplay = '<span class="text-muted">' + (champ.current_holder_name || 'Unknown') + '</span> / <strong>' + (champ.interim_holder_name || 'Unknown') + '</strong>';
    } else {
        championDisplay = champ.current_holder_name || '<em class="text-muted">No champion</em>';
    }
    
    var actionsHtml = '';
    if (champ.is_vacant) {
        actionsHtml = '<button class="btn btn-sm btn-outline-success" onclick="event.stopPropagation(); showFillVacancyModal(\'' + champId + '\')">' +
            '<i class="bi bi-trophy"></i></button>';
    } else {
        actionsHtml = '<button class="btn btn-sm btn-outline-secondary" onclick="event.stopPropagation(); showChampionshipActions(\'' + champId + '\')">' +
            '<i class="bi bi-gear"></i></button>';
    }
    
    return '<div class="col-md-6 col-lg-4">' +
        '<div class="card championship-card h-100 ' + tierClass + (champ.retired ? ' opacity-50' : '') + '" onclick="showChampionshipDetail(\'' + champId + '\')">' +
        '<div class="card-body">' +
        '<div class="d-flex justify-content-between align-items-start mb-2">' +
        '<h6 class="card-title mb-0">' + champ.name + '</h6>' +
        issueIcon +
        '</div>' +
        '<div class="mb-2">' + badges + '</div>' +
        '<p class="text-muted small mb-2">' +
        '<i class="bi bi-building"></i> ' + champ.assigned_brand + ' • ' +
        '<span class="text-capitalize">' + champ.title_type + '</span>' +
        '</p>' +
        '<div class="mb-2">' +
        '<small class="text-muted">Champion:</small><br>' +
        '<span class="fw-bold">' + championDisplay + '</span>' +
        '</div>' +
        '<div class="mb-2">' +
        '<div class="d-flex justify-content-between align-items-center mb-1">' +
        '<small class="text-muted">Prestige</small>' +
        '<small class="fw-bold">' + champ.prestige + '</small>' +
        '</div>' +
        '<div class="prestige-bar">' +
        '<div class="prestige-fill ' + prestigeClass + '" style="width: ' + champ.prestige + '%"></div>' +
        '</div>' +
        '</div>' +
        '</div>' +
        '<div class="card-footer bg-transparent py-2">' +
        '<div class="d-flex justify-content-between">' +
        '<button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); showChampionshipDetail(\'' + champId + '\')">' +
        '<i class="bi bi-eye"></i> Details</button>' +
        actionsHtml +
        '</div>' +
        '</div>' +
        '</div>' +
        '</div>';
}

// STEP 23: Prestige helper functions
function getPrestigeTier(prestige) {
    if (prestige >= 90) return 'Legendary';
    if (prestige >= 75) return 'Prestigious';
    if (prestige >= 60) return 'Established';
    if (prestige >= 45) return 'Average';
    if (prestige >= 30) return 'Declining';
    return 'Damaged';
}

function getPrestigeColor(prestige) {
    if (prestige >= 90) return 'success';
    if (prestige >= 75) return 'primary';
    if (prestige >= 60) return 'info';
    if (prestige >= 45) return 'secondary';
    if (prestige >= 30) return 'warning';
    return 'danger';
}

// STEP 23: Load and display prestige leaderboard
async function loadPrestigeLeaderboard() {
    try {
        var response = await fetch('/api/championships/prestige/leaderboard');
        var data = await response.json();
        
        if (data.success) {
            displayPrestigeLeaderboard(data.leaderboard);
        }
    } catch (error) {
        console.error('Error loading prestige leaderboard:', error);
    }
}

function displayPrestigeLeaderboard(leaderboard) {
    var container = document.getElementById('prestigeLeaderboard');
    if (!container) return;
    
    var html = '<div class="list-group">';
    
    leaderboard.forEach(function(champ, index) {
        var rank = index + 1;
        var medal = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : rank + '.';
        var tierColor = getPrestigeColor(champ.prestige);
        
        html += '<div class="list-group-item d-flex justify-content-between align-items-center">' +
            '<div>' +
            '<span class="fs-5 me-2">' + medal + '</span>' +
            '<strong>' + champ.name + '</strong>' +
            '<br><small class="text-muted">' + champ.brand + ' • ' + champ.title_type + '</small>' +
            '</div>' +
            '<div class="text-end">' +
            '<div class="fs-4 fw-bold text-' + tierColor + '">' + champ.prestige + '</div>' +
            '<small class="badge bg-' + tierColor + '">' + champ.tier + '</small>' +
            '</div>' +
            '</div>';
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// STEP 23: Show prestige details in championship detail modal
async function showChampionshipDetail(titleId) {
    var champ = championships.find(function(c) { return c.id === titleId; });
    if (!champ) {
        champ = customChampionships.find(function(c) { 
            return c.id === titleId || c.title_id === titleId; 
        });
    }
    if (!champ) return;
    
    var champId = champ.id || champ.title_id;
    
    var modal = new bootstrap.Modal(document.getElementById('championshipDetailModal'));
    document.getElementById('championshipDetailTitle').textContent = champ.name;
    
    // Load additional data including prestige
    var stats = null;
    var extended = null;
    var prestige = null;
    
    try {
        var responses = await Promise.all([
            fetch('/api/championships/' + champId + '/statistics'),
            fetch('/api/championships/' + champId + '/extended'),
            fetch('/api/championships/' + champId + '/prestige')
        ]);
        
        var statsData = await responses[0].json();
        if (statsData.success) stats = statsData.statistics;
        
        var extData = await responses[1].json();
        if (extData.success) extended = extData.championship;
        
        var prestigeData = await responses[2].json();
        if (prestigeData.success) prestige = prestigeData;
    } catch (error) {
        console.error('Error loading details:', error);
    }
    
    var body = document.getElementById('championshipDetailBody');
    
    var championHtml = champ.is_vacant ? 
        '<div class="alert alert-warning mb-0"><i class="bi bi-exclamation-triangle"></i> VACANT</div>' :
        '<h5 class="mb-0">' + (champ.current_holder_name || 'Unknown') + '</h5>';
    
    // STEP 23: Add prestige section
    var prestigeHtml = '';
    if (prestige) {
        var tierColor = getPrestigeColor(prestige.prestige.current);
        
        prestigeHtml = '<h6 class="mt-3">Prestige</h6>' +
            '<div class="card bg-' + tierColor + ' bg-opacity-10 border-' + tierColor + '">' +
            '<div class="card-body">' +
            '<div class="row text-center">' +
            '<div class="col-4">' +
            '<div class="display-4 fw-bold text-' + tierColor + '">' + prestige.prestige.current + '</div>' +
            '<small class="text-muted">Current</small>' +
            '</div>' +
            '<div class="col-4">' +
            '<div class="h2 mb-0 text-' + tierColor + '">' + prestige.prestige.tier + '</div>' +
            '<small class="text-muted">Tier</small>' +
            '</div>' +
            '<div class="col-4">' +
            '<div class="h4 mb-0">' + prestige.total_defenses + '</div>' +
            '<small class="text-muted">Defenses</small>' +
            '</div>' +
            '</div>' +
            '<p class="mb-0 mt-3 small text-muted">' + prestige.prestige.description + '</p>' +
            '</div>' +
            '</div>';
        
        // Add prestige factors
        if (prestige.analysis.factors && prestige.analysis.factors.length > 0) {
            prestigeHtml += '<div class="mt-2">';
            prestige.analysis.factors.forEach(function(factor) {
                var iconClass = {
                    'positive': 'bi-check-circle text-success',
                    'negative': 'bi-x-circle text-danger',
                    'warning': 'bi-exclamation-triangle text-warning',
                    'info': 'bi-info-circle text-info'
                }[factor.type] || 'bi-info-circle';
                
                prestigeHtml += '<div class="alert alert-' + factor.type + ' py-1 px-2 mb-1 small">' +
                    '<i class="bi ' + iconClass + '"></i> ' + factor.message +
                    '</div>';
            });
            prestigeHtml += '</div>';
        }
    }
    
    var extendedHtml = '';
    if (extended) {
        extendedHtml = '<h6 class="mt-3">Extended Info</h6>' +
            '<table class="table table-sm">' +
            '<tr><td>Division:</td><td class="text-capitalize">' + (extended.division || 'Open') + '</td></tr>' +
            '<tr><td>Weight Class:</td><td class="text-capitalize">' + (extended.weight_class || 'Open').replace('_', ' ') + '</td></tr>' +
            '<tr><td>Custom Title:</td><td>' + (extended.is_custom ? '<span class="badge bg-info">Yes</span>' : 'No') + '</td></tr>' +
            '</table>';
        
        if (extended.description) {
            extendedHtml += '<p class="text-muted"><em>' + extended.description + '</em></p>';
        }
    }
    
    var statsHtml = '';
    if (stats) {
        statsHtml = '<h6>Statistics</h6>' +
            '<div class="row text-center">' +
            '<div class="col-4"><div class="h4 mb-0">' + stats.total_reigns + '</div><small class="text-muted">Total Reigns</small></div>' +
            '<div class="col-4"><div class="h4 mb-0">' + stats.unique_champions + '</div><small class="text-muted">Unique Champions</small></div>' +
            '<div class="col-4"><div class="h4 mb-0">' + stats.total_defenses + '</div><small class="text-muted">Total Defenses</small></div>' +
            '</div>';
        
        if (stats.longest_reign) {
            statsHtml += '<div class="mt-3"><strong>Longest Reign:</strong> ' + stats.longest_reign.champion + ' (' + stats.longest_reign.days + ' days)</div>';
        }
        if (stats.most_reigns) {
            statsHtml += '<div><strong>Most Reigns:</strong> ' + stats.most_reigns.champion + ' (' + stats.most_reigns.count + 'x)</div>';
        }
        if (stats.average_match_rating > 0) {
            statsHtml += '<div><strong>Avg Match Rating:</strong> ' + stats.average_match_rating.toFixed(2) + ' ★</div>';
        }
    }
    
    var historyHtml = '';
    if (champ.history && champ.history.length > 0) {
        historyHtml = '<h6 class="mt-3">Recent Title History</h6>' +
            '<div class="table-responsive"><table class="table table-sm"><thead><tr>' +
            '<th>Champion</th><th>Won At</th><th>Days Held</th></tr></thead><tbody>';
        var recentReigns = champ.history.slice(-5).reverse();
        recentReigns.forEach(function(reign) {
            var rowClass = reign.is_interim ? 'table-info' : '';
            historyHtml += '<tr class="' + rowClass + '">' +
                '<td>' + reign.wrestler_name + (reign.is_interim ? ' <span class="badge bg-info">Interim</span>' : '') + '</td>' +
                '<td>' + reign.won_at_show_name + '</td>' +
                '<td>' + (reign.days_held || '<em>Current</em>') + '</td>' +
                '</tr>';
        });
        historyHtml += '</tbody></table></div>';
    }
    
    var actionsHtml = '';
    if (extended && extended.is_custom) {
        actionsHtml = '<div class="mt-3 pt-3 border-top">' +
            '<h6>Custom Championship Actions</h6>' +
            '<div class="btn-group">' +
            '<button class="btn btn-sm btn-outline-primary" onclick="showEditChampionshipModal(\'' + champId + '\')">' +
            '<i class="bi bi-pencil"></i> Edit</button>';
        
        if (champ.is_vacant) {
            if (!extended.retired) {
                actionsHtml += '<button class="btn btn-sm btn-outline-warning" onclick="retireChampionship(\'' + champId + '\')">' +
                    '<i class="bi bi-archive"></i> Retire</button>';
            } else {
                actionsHtml += '<button class="btn btn-sm btn-outline-success" onclick="reactivateChampionship(\'' + champId + '\')">' +
                    '<i class="bi bi-arrow-counterclockwise"></i> Reactivate</button>';
            }
            actionsHtml += '<button class="btn btn-sm btn-outline-danger" onclick="showDeleteChampionshipModal(\'' + champId + '\', \'' + champ.name + '\')">' +
                '<i class="bi bi-trash"></i> Delete</button>';
        }
        
        actionsHtml += '</div></div>';
    }
    
    body.innerHTML = '<div class="row">' +
        '<div class="col-md-6">' +
        '<h6>Championship Info</h6>' +
        '<table class="table table-sm">' +
        '<tr><td>Brand:</td><td><strong>' + champ.assigned_brand + '</strong></td></tr>' +
        '<tr><td>Type:</td><td><strong>' + champ.title_type + '</strong></td></tr>' +
        '<tr><td>Prestige:</td><td><strong>' + champ.prestige + '/100</strong></td></tr>' +
        '</table>' +
        '<h6 class="mt-3">Current Champion</h6>' +
        championHtml +
        prestigeHtml +
        extendedHtml +
        '</div>' +
        '<div class="col-md-6">' +
        statsHtml +
        historyHtml +
        '</div>' +
        '</div>' +
        actionsHtml;
    
    modal.show();
}