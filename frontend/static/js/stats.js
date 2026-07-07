/**
 * Statistics & Records Management
 */

// Load all stats on page load
document.addEventListener('DOMContentLoaded', function() {
    loadLeaderboards();
    loadPromotionRecords();
    loadRecentMilestones();
    loadWrestlerSelect();
});

// ============================================================================
// LEADERBOARDS
// ============================================================================

async function loadLeaderboards() {
    try {
        // Load all leaderboards in parallel
        const [wins, winPct, titles, rating] = await Promise.all([
            getAPI('/api/stats/leaderboard/wins?limit=10'),
            getAPI('/api/stats/leaderboard/win_percentage?limit=10'),
            getAPI('/api/stats/leaderboard/title_reigns?limit=10'),
            getAPI('/api/stats/leaderboard/star_rating?limit=10')
        ]);

        renderLeaderboard('winsLeaderboard', wins.leaderboard, 'wins');
        renderLeaderboard('winPercentageLeaderboard', winPct.leaderboard, 'win_pct');
        renderLeaderboard('titleReignsLeaderboard', titles.leaderboard, 'total_title_reigns');
        renderLeaderboard('starRatingLeaderboard', rating.leaderboard, 'avg_rating');

    } catch (error) {
        console.error('Failed to load leaderboards:', error);
        showError('Failed to load leaderboards');
    }
}

function renderLeaderboard(containerId, data, statKey) {
    const container = document.getElementById(containerId);
    
    if (!data || data.length === 0) {
        container.innerHTML = '<p class="text-muted text-center py-3">No data available</p>';
        return;
    }

    let html = '';
    
    data.forEach((wrestler, index) => {
        const rank = index + 1;
        const rankClass = rank === 1 ? 'rank-1' : rank === 2 ? 'rank-2' : rank === 3 ? 'rank-3' : 'rank-default';
        
        let statValue = wrestler[statKey];
        let statDisplay = '';
        
        // Format stat display based on type
        if (statKey === 'wins') {
            statDisplay = `${wrestler.wins} wins (${wrestler.losses} losses)`;
        } else if (statKey === 'win_pct') {
            statDisplay = `${statValue.toFixed(1)}% (${wrestler.wins}-${wrestler.losses})`;
        } else if (statKey === 'total_title_reigns') {
            statDisplay = `${wrestler.total_title_reigns} reign${wrestler.total_title_reigns !== 1 ? 's' : ''}`;
        } else if (statKey === 'avg_rating') {
            statDisplay = `${statValue.toFixed(2)} ⭐ (${wrestler.total_matches} matches)`;
        }

        html += `
            <div class="leaderboard-item">
                <div class="leaderboard-rank ${rankClass}">${rank}</div>
                <div class="flex-grow-1">
                    <a href="#" class="wrestler-link" onclick="showWrestlerStats('${wrestler.wrestler_id}'); return false;">
                        ${wrestler.name}
                    </a>
                    <div class="text-muted small">${wrestler.role} • ${wrestler.primary_brand}</div>
                </div>
                <div class="text-end">
                    <div class="fw-bold">${statDisplay}</div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// ============================================================================
// PROMOTION RECORDS
// ============================================================================

async function loadPromotionRecords() {
    try {
        const response = await getAPI('/api/stats/promotion/records');
        const records = response.records;

        renderPromotionRecords(records);

    } catch (error) {
        console.error('Failed to load promotion records:', error);
    }
}

function renderPromotionRecords(records) {
    const container = document.getElementById('recordsContainer');
    
    let html = '';

    // Match Records
    if (records.match_records) {
        html += `
            <div class="col-lg-6 mb-3">
                <div class="record-card">
                    <div class="record-title">Highest Rated Match</div>
                    ${records.match_records.highest_rated ? `
                        <div class="record-value">${records.match_records.highest_rated.star_rating.toFixed(2)} ⭐</div>
                        <div class="record-details">
                            ${records.match_records.highest_rated.participants}<br>
                            ${records.match_records.highest_rated.show_name}
                        </div>
                    ` : '<div class="text-muted">No data</div>'}
                </div>
            </div>
        `;
    }

    // Wrestler Records
    if (records.wrestler_records) {
        if (records.wrestler_records.longest_title_reign) {
            html += `
                <div class="col-lg-6 mb-3">
                    <div class="record-card">
                        <div class="record-title">Longest Title Reign</div>
                        <div class="record-value">${records.wrestler_records.longest_title_reign.days_held} days</div>
                        <div class="record-details">
                            ${records.wrestler_records.longest_title_reign.wrestler_name}<br>
                            ${records.wrestler_records.longest_title_reign.title_name}
                        </div>
                    </div>
                </div>
            `;
        }

        if (records.wrestler_records.best_win_percentage) {
            html += `
                <div class="col-lg-6 mb-3">
                    <div class="record-card">
                        <div class="record-title">Best Win Percentage</div>
                        <div class="record-value">${records.wrestler_records.best_win_percentage.win_percentage}%</div>
                        <div class="record-details">
                            ${records.wrestler_records.best_win_percentage.wrestler_name}<br>
                            Record: ${records.wrestler_records.best_win_percentage.record}
                        </div>
                    </div>
                </div>
            `;
        }
    }

    // Streak Records
    if (records.streak_records) {
        if (records.streak_records.longest_winning) {
            html += `
                <div class="col-lg-6 mb-3">
                    <div class="record-card">
                        <div class="record-title">Longest Winning Streak</div>
                        <div class="record-value">${records.streak_records.longest_winning.streak_length} matches</div>
                        <div class="record-details">
                            ${records.streak_records.longest_winning.wrestler_name}
                        </div>
                    </div>
                </div>
            `;
        }
    }

    // Show Records
    if (records.show_records) {
        if (records.show_records.highest_rated) {
            html += `
                <div class="col-lg-6 mb-3">
                    <div class="record-card">
                        <div class="record-title">Highest Rated Show</div>
                        <div class="record-value">${records.show_records.highest_rated.rating.toFixed(2)} ⭐</div>
                        <div class="record-details">
                            ${records.show_records.highest_rated.show_name}<br>
                            Year ${records.show_records.highest_rated.year}, Week ${records.show_records.highest_rated.week}
                        </div>
                    </div>
                </div>
            `;
        }

        if (records.show_records.highest_attendance) {
            html += `
                <div class="col-lg-6 mb-3">
                    <div class="record-card">
                        <div class="record-title">Highest Attendance</div>
                        <div class="record-value">${records.show_records.highest_attendance.attendance.toLocaleString()}</div>
                        <div class="record-details">
                            ${records.show_records.highest_attendance.show_name}<br>
                            Year ${records.show_records.highest_attendance.year}, Week ${records.show_records.highest_attendance.week}
                        </div>
                    </div>
                </div>
            `;
        }
    }

    container.innerHTML = html || '<p class="text-muted text-center">No records available yet</p>';
}

// ============================================================================
// MILESTONES
// ============================================================================

async function loadRecentMilestones() {
    try {
        const response = await getAPI('/api/stats/milestones/recent?limit=20');
        renderMilestones(response.milestones);

    } catch (error) {
        console.error('Failed to load milestones:', error);
    }
}

function renderMilestones(milestones) {
    const container = document.getElementById('recentMilestones');
    
    if (!milestones || milestones.length === 0) {
        container.innerHTML = '<p class="text-muted text-center py-3">No milestones achieved yet</p>';
        return;
    }

    let html = '';
    
    milestones.forEach(milestone => {
        const icon = getMilestoneIcon(milestone.milestone_type);
        
        html += `
            <div class="milestone-item">
                <div class="milestone-icon">
                    <i class="bi ${icon}"></i>
                </div>
                <div class="milestone-content">
                    <div class="milestone-title">
                        <a href="#" class="wrestler-link" onclick="showWrestlerStats('${milestone.wrestler_id}'); return false;">
                            ${milestone.wrestler_name}
                        </a>
                    </div>
                    <div>${milestone.description}</div>
                    <div class="milestone-date">
                        ${milestone.achieved_at_show_name} • Year ${milestone.year}, Week ${milestone.week}
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function getMilestoneIcon(type) {
    const icons = {
        'debut': 'bi-star',
        'first_win': 'bi-trophy',
        'first_title': 'bi-award',
        'match_100': 'bi-hash',
        'match_250': 'bi-hash',
        'match_500': 'bi-hash',
        'win_100': 'bi-star-fill',
        'win_250': 'bi-star-fill',
        'five_star_match': 'bi-stars',
        'streak_10': 'bi-fire',
        'streak_25': 'bi-fire',
        'main_event_50': 'bi-tv',
        'ppv_50': 'bi-calendar-event',
        'retirement': 'bi-door-closed'
    };
    
    return icons[type] || 'bi-flag-fill';
}

// ============================================================================
// WRESTLER STATS
// ============================================================================

async function loadWrestlerSelect() {
    try {
        const response = await getAPI('/api/roster?active_only=false');
        const wrestlers = response.wrestlers;
        
        const select = document.getElementById('wrestlerSelect');
        let options = '<option value="">Select a wrestler...</option>';
        
        // Sort by name
        wrestlers.sort((a, b) => a.name.localeCompare(b.name));
        
        wrestlers.forEach(wrestler => {
            const status = wrestler.is_retired ? ' (Retired)' : '';
            options += `<option value="${wrestler.id}">${wrestler.name}${status} - ${wrestler.role}</option>`;
        });
        
        select.innerHTML = options;
        
        // Add event listener
        select.addEventListener('change', function() {
            if (this.value) {
                loadWrestlerStats(this.value);
            } else {
                document.getElementById('wrestlerStatsDisplay').style.display = 'none';
            }
        });
        
        // Search functionality
        document.getElementById('wrestlerSearch').addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const options = select.querySelectorAll('option');
            
            options.forEach(option => {
                if (option.value === '') return; // Skip placeholder
                
                const text = option.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    option.style.display = '';
                } else {
                    option.style.display = 'none';
                }
            });
        });
        
    } catch (error) {
        console.error('Failed to load wrestler list:', error);
    }
}

async function loadWrestlerStats(wrestlerId) {
    try {
        const response = await getAPI(`/api/stats/wrestler/${wrestlerId}`);
        
        if (response.success) {
            renderWrestlerStats(response.stats, response.milestones);
        }
        
    } catch (error) {
        console.error('Failed to load wrestler stats:', error);
        showError('Failed to load wrestler statistics');
    }
}

async function showWrestlerStats(wrestlerId) {
    // Switch to wrestler stats tab
    const tab = new bootstrap.Tab(document.getElementById('wrestler-stats-tab'));
    tab.show();
    
    // Set the select value
    document.getElementById('wrestlerSelect').value = wrestlerId;
    
    // Load stats
    await loadWrestlerStats(wrestlerId);
}

function renderWrestlerStats(stats, milestones) {
    const container = document.getElementById('wrestlerStatsDisplay');
    
    let html = `
        <div class="stats-card">
            <div class="stats-card-header">
                <h5><i class="bi bi-person-badge"></i> ${stats.wrestler_name}</h5>
            </div>
            <div class="stats-card-body">
                <div class="row">
                    <!-- Record -->
                    <div class="col-md-6 mb-3">
                        <h6 class="text-muted">Career Record</h6>
                        <div class="row g-2">
                            <div class="col-6">
                                <div class="p-2 bg-light rounded text-center">
                                    <div class="fw-bold">${stats.record.total_matches}</div>
                                    <small>Total Matches</small>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="p-2 bg-light rounded text-center">
                                    <div class="fw-bold text-success">${stats.record.wins}</div>
                                    <small>Wins</small>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="p-2 bg-light rounded text-center">
                                    <div class="fw-bold text-danger">${stats.record.losses}</div>
                                    <small>Losses</small>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="p-2 bg-light rounded text-center">
                                    <div class="fw-bold">${stats.record.win_percentage}%</div>
                                    <small>Win Rate</small>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Match Quality -->
                    <div class="col-md-6 mb-3">
                        <h6 class="text-muted">Match Quality</h6>
                        <div class="row g-2">
                            <div class="col-6">
                                <div class="p-2 bg-light rounded text-center">
                                    <div class="fw-bold">${stats.match_quality.average_star_rating} ⭐</div>
                                    <small>Avg Rating</small>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="p-2 bg-light rounded text-center">
                                    <div class="fw-bold">${stats.match_quality.highest_star_rating} ⭐</div>
                                    <small>Best Match</small>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="p-2 bg-light rounded text-center">
                                    <div class="fw-bold">${stats.match_quality.five_star_matches}</div>
                                    <small>5-Star Matches</small>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="p-2 bg-light rounded text-center">
                                    <div class="fw-bold">${stats.match_quality.four_star_plus_matches}</div>
                                    <small>4+ Star Matches</small>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Championships -->
                    <div class="col-md-6 mb-3">
                        <h6 class="text-muted">Championship History</h6>
                        <div class="row g-2">
                            <div class="col-6">
                                <div class="p-2 bg-light rounded text-center">
                                    <div class="fw-bold">${stats.title_history.total_reigns}</div>
                                    <small>Title Reigns</small>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="p-2 bg-light rounded text-center">
                                    <div class="fw-bold">${stats.title_history.total_days}</div>
                                    <small>Days as Champion</small>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Streaks -->
                    <div class="col-md-6 mb-3">
                        <h6 class="text-muted">Streaks</h6>
                        <div class="row g-2">
                            <div class="col-6">
                                <div class="p-2 bg-light rounded text-center">
                                    <div class="fw-bold ${stats.streaks.current_win_streak > 0 ? 'text-success' : ''}">${stats.streaks.current_win_streak}</div>
                                    <small>Current Win Streak</small>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="p-2 bg-light rounded text-center">
                                    <div class="fw-bold">${stats.streaks.longest_win_streak}</div>
                                    <small>Best Win Streak</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Milestones -->
                ${milestones && milestones.length > 0 ? `
                    <hr class="my-4">
                    <h6 class="text-muted mb-3">Career Milestones</h6>
                    <div class="milestones-list">
                        ${milestones.map(m => `
                            <div class="milestone-item mb-2">
                                <div class="milestone-icon">
                                    <i class="bi ${getMilestoneIcon(m.milestone_type)}"></i>
                                </div>
                                <div class="milestone-content">
                                    <div>${m.description}</div>
                                    <div class="milestone-date">
                                        ${m.achieved_at_show_name} • Year ${m.year}, Week ${m.week}
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    container.style.display = 'block';
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function showError(message) {
    const alertHtml = `
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <i class="bi bi-exclamation-triangle"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Add to top of container
    const container = document.querySelector('.container');
    container.insertAdjacentHTML('afterbegin', alertHtml);
}