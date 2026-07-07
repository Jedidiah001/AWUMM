/**
 * Awards Management
 */

let allCeremonies = [];
let currentCeremony = null;

// Load on page load
document.addEventListener('DOMContentLoaded', function() {
    loadAllAwards();
});

// ============================================================================
// LOAD AWARDS
// ============================================================================

async function loadAllAwards() {
    try {
        const response = await getAPI('/api/awards/all');
        
        if (response.success) {
            allCeremonies = response.ceremonies;
            populateYearSelect();
            
            if (allCeremonies.length > 0) {
                // Load most recent ceremony
                loadCeremony(allCeremonies[0]);
            }
        }
        
    } catch (error) {
        console.error('Failed to load awards:', error);
        showEmptyState('No awards ceremonies found');
    }
}

function populateYearSelect() {
    const select = document.getElementById('yearSelect');
    
    if (allCeremonies.length === 0) {
        select.innerHTML = '<option value="">No awards yet - Complete Year 1!</option>';
        return;
    }
    
    let options = '';
    
    allCeremonies.forEach((ceremony, index) => {
        const selected = index === 0 ? 'selected' : '';
        options += `<option value="${ceremony.year}" ${selected}>Year ${ceremony.year} Awards</option>`;
    });
    
    select.innerHTML = options;
    
    // Add event listener
    select.addEventListener('change', function() {
        const year = parseInt(this.value);
        const ceremony = allCeremonies.find(c => c.year === year);
        if (ceremony) {
            loadCeremony(ceremony);
        }
    });
}

function loadCeremony(ceremony) {
    currentCeremony = ceremony;
    
    // Update summary
    document.getElementById('awardsSummary').style.display = 'block';
    document.getElementById('summaryYear').textContent = ceremony.year;
    document.getElementById('summaryTotal').textContent = ceremony.total_awards;
    
    // Render awards
    renderAwards(ceremony.awards);
}

// ============================================================================
// RENDER AWARDS
// ============================================================================

function renderAwards(awards) {
    const container = document.getElementById('awardsContainer');
    
    if (!awards || awards.length === 0) {
        showEmptyState('No awards for this year');
        return;
    }
    
    let html = '';
    
    // Group awards by type
    const wrestlerAwards = awards.filter(a => 
        a.category.includes('wrestler') || 
        a.category.includes('breakout') || 
        a.category.includes('improved') ||
        a.category.includes('comeback')
    );
    
    const matchAwards = awards.filter(a => 
        a.category.includes('match') || 
        a.category.includes('feud')
    );
    
    const championshipAwards = awards.filter(a => 
        a.category.includes('champion') || 
        a.category.includes('reign')
    );
    
    const tagAwards = awards.filter(a => 
        a.category.includes('tag')
    );
    
    const performanceAwards = awards.filter(a => 
        a.category.includes('technical') || 
        a.category.includes('flyer') || 
        a.category.includes('brawler') ||
        a.category.includes('mic')
    );
    
    const showAwards = awards.filter(a => 
        a.category.includes('show') || 
        a.category.includes('brand')
    );
    
    // Render each group
    if (wrestlerAwards.length > 0) {
        html += '<h3 class="mt-4 mb-3"><i class="bi bi-person-badge"></i> Wrestler Awards</h3>';
        wrestlerAwards.forEach(award => {
            html += renderAwardCard(award);
        });
    }
    
    if (championshipAwards.length > 0) {
        html += '<h3 class="mt-4 mb-3"><i class="bi bi-trophy"></i> Championship Awards</h3>';
        championshipAwards.forEach(award => {
            html += renderAwardCard(award);
        });
    }
    
    if (matchAwards.length > 0) {
        html += '<h3 class="mt-4 mb-3"><i class="bi bi-lightning"></i> Match & Feud Awards</h3>';
        matchAwards.forEach(award => {
            html += renderAwardCard(award);
        });
    }
    
    if (tagAwards.length > 0) {
        html += '<h3 class="mt-4 mb-3"><i class="bi bi-people"></i> Tag Team Awards</h3>';
        tagAwards.forEach(award => {
            html += renderAwardCard(award);
        });
    }
    
    if (performanceAwards.length > 0) {
        html += '<h3 class="mt-4 mb-3"><i class="bi bi-star"></i> Performance Awards</h3>';
        performanceAwards.forEach(award => {
            html += renderAwardCard(award);
        });
    }
    
    if (showAwards.length > 0) {
        html += '<h3 class="mt-4 mb-3"><i class="bi bi-tv"></i> Show Awards</h3>';
        showAwards.forEach(award => {
            html += renderAwardCard(award);
        });
    }
    
    container.innerHTML = html;
}

function renderAwardCard(award) {
    const isPrestigious = award.category.includes('wrestler_of_the_year') || 
                          award.category.includes('match_of_the_year');
    
    const headerClass = isPrestigious ? 'award-category-header gold' : 'award-category-header';
    
    let html = `
        <div class="award-category-card">
            <div class="${headerClass}">
                <div class="award-icon">${getAwardIcon(award.category)}</div>
                <div class="award-category-title">${award.category_display}</div>
            </div>
            
            <div class="award-winner-section">
                <div class="winner-badge">
                    <i class="bi bi-trophy-fill"></i>
                    WINNER
                </div>
                <div class="winner-name">${award.winner_name}</div>
                <div class="winner-reason">${award.nominees[0].reason}</div>
            </div>
            
            ${award.nominees.length > 1 ? `
                <div class="nominees-section">
                    <h6 class="text-muted mb-3">Other Nominees</h6>
                    ${award.nominees.slice(1).map((nominee, index) => `
                        <div class="nominee-item">
                            <div class="nominee-rank">${index + 2}</div>
                            <div class="nominee-info">
                                <div class="nominee-name">${nominee.nominee_name}</div>
                                <div class="nominee-reason">${nominee.reason}</div>
                            </div>
                            <div class="nominee-score">${nominee.score.toFixed(1)}</div>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
        </div>
    `;
    
    return html;
}

function getAwardIcon(category) {
    const icons = {
        'wrestler_of_the_year': '👑',
        'breakout_star': '🌟',
        'most_improved': '📈',
        'comeback_of_the_year': '🔄',
        'match_of_the_year': '⚡',
        'feud_of_the_year': '🔥',
        'moment_of_the_year': '💫',
        'champion_of_the_year': '🏆',
        'title_reign_of_the_year': '👑',
        'tag_team_of_the_year': '👥',
        'tag_match_of_the_year': '⚔️',
        'best_technical_wrestler': '🎯',
        'best_high_flyer': '🦅',
        'best_brawler': '👊',
        'promo_of_the_year': '🎤',
        'best_on_the_mic': '🎙️',
        'best_brand': '📺',
        'show_of_the_year': '🎪'
    };
    
    return icons[category] || '🏆';
}

function showEmptyState(message) {
    const container = document.getElementById('awardsContainer');
    container.innerHTML = `
        <div class="empty-awards">
            <i class="bi bi-trophy"></i>
            <h4>${message}</h4>
            <p>Awards ceremonies appear at the end of each year (Week 52)</p>
        </div>
    `;
}