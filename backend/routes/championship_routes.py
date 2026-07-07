"""
Championship Management Routes
STEP 21-23: Complete championship system with prestige tracking

Handles:
- Championship hierarchy
- Custom championship creation
- Vacancy management
- Interim champions
- Title situations
- Unification (merge titles)
- Splitting (divide titles)
- Reboot/Restart (new lineage)
- Deactivation (inactive status)
- Transfer (brand/division changes)
- Lineage tracking
- Brand exclusivity
- STEP 23: Prestige tracking and analytics
"""

from flask import Blueprint, request, jsonify
from typing import Optional

# Create blueprint
championship_bp = Blueprint('championships', __name__, url_prefix='/api/championships')


# These will be set during registration
database = None
universe = None
championship_manager = None


def register_championship_routes(app, db, universe_state):
    """Register championship routes with the Flask app"""
    global database, universe, championship_manager
    
    database = db
    universe = universe_state
    
    # Import and initialize manager
    from services.championship_manager import get_championship_manager
    championship_manager = get_championship_manager(database)
    
    # Load existing state from database
    _load_manager_state()
    
    # Register blueprint
    app.register_blueprint(championship_bp)
    
    # Register STEP 23 prestige routes (appended to main app, not blueprint)
    _register_prestige_routes(app)
    
    print("   ✅ Championship management routes registered")
    print("   ✅ Championship prestige routes registered")

def _resolve_tag_team_display(holder_id):
    """Return best-effort tag team display data for a current title holder."""
    if not holder_id or not getattr(universe, 'tag_team_manager', None):
        return None

    holder_id = str(holder_id)
    team = None

    if holder_id.startswith('team_'):
        team = universe.tag_team_manager.get_team_by_id(holder_id)
    else:
        teams = universe.tag_team_manager.get_teams_involving_wrestler(holder_id)
        active_teams = [
            candidate for candidate in teams
            if getattr(candidate, 'is_active', True) and not getattr(candidate, 'is_disbanded', False)
        ]
        team = active_teams[0] if active_teams else (teams[0] if teams else None)

    if not team and database:
        try:
            import json

            rows = database.conn.cursor().execute(
                """
                SELECT team_id, team_name, member_ids, member_names
                FROM tag_teams
                WHERE is_active = 1 AND is_disbanded = 0
                ORDER BY team_name
                """
            ).fetchall()
            for row in rows:
                member_ids = json.loads(row['member_ids'] or '[]')
                if holder_id == row['team_id'] or holder_id in member_ids:
                    return {
                        'team_id': row['team_id'],
                        'team_name': row['team_name'],
                        'member_ids': member_ids[:2],
                        'member_names': json.loads(row['member_names'] or '[]')[:2],
                    }
        except Exception:
            return None

    if not team:
        return None

    return {
        'team_id': getattr(team, 'team_id', holder_id),
        'team_name': getattr(team, 'team_name', None),
        'member_ids': (getattr(team, 'member_ids', None) or [])[:2],
        'member_names': (getattr(team, 'member_names', None) or [])[:2],
    }


def _load_manager_state():
    """Load championship manager state from database"""
    try:
        cursor = database.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='championship_manager_state'")
        if cursor.fetchone():
            cursor.execute('SELECT state_json FROM championship_manager_state WHERE id = 1')
            row = cursor.fetchone()
            if row:
                import json
                state = json.loads(row['state_json'])
                championship_manager.load_from_dict(state)
                print(f"   ✅ Loaded championship manager state")
    except Exception as e:
        print(f"   ⚠️ Could not load championship manager state: {e}")


# ============================================================================
# LIST ALL CHAMPIONSHIPS (Missing endpoint!)
# ============================================================================

@championship_bp.route('/', methods=['GET'])
@championship_bp.route('', methods=['GET'])
def api_get_all_championships():
    """Get all championships"""
    try:
        championships = universe.championships
        
        # Optional filters
        brand = request.args.get('brand')
        title_type = request.args.get('type')
        include_retired = request.args.get('include_retired', 'false').lower() == 'true'
        
        result = []
        for champ in championships:
            # Apply filters
            if brand and champ.assigned_brand != brand:
                continue
            if title_type and champ.title_type != title_type:
                continue
            
            # Check if retired (if extended data exists)
            from persistence.championship_custom_db import get_championship_extended
            extended = get_championship_extended(database, champ.id) or {}
            
            if not include_retired and extended.get('retired'):
                continue
            
            champ_dict = champ.to_dict()

            # Improve Tag Team title display: show team name and both members when possible.
            try:
                is_tag = (
                    champ_dict.get('is_tag_team') or
                    str(champ_dict.get('title_type', '')).lower().replace('-', ' ') == 'tag team'
                )
                if is_tag and not champ_dict.get('is_vacant'):
                    holder_id = champ_dict.get('current_holder_id')
                    team = _resolve_tag_team_display(holder_id)
                    if team:
                        members = team.get('member_names', [])
                        holder_display = ' & '.join(members) if members else (team.get('team_name') or champ_dict.get('current_holder_name'))
                        champ_dict['current_holder_id'] = team.get('team_id', holder_id)
                        champ_dict['current_holder_name'] = holder_display
                        champ_dict['current_holder_display'] = holder_display
                        champ_dict['current_holder_team_name'] = team.get('team_name')
                        champ_dict['current_holder_member_ids'] = team.get('member_ids', [])
                        champ_dict['current_holder_member_names'] = members
                    else:
                        champ_dict['current_holder_display'] = champ_dict.get('current_holder_name')
            except Exception:
                pass

            division = str(extended.get('division') or '').lower()
            if division in ('mens', "men's"):
                champ_dict['division'] = 'male'
            elif division in ('womens', "women's"):
                champ_dict['division'] = 'female'
            elif division:
                champ_dict['division'] = division
            elif 'women' in str(champ.title_type).lower() or 'women' in str(champ.name).lower():
                champ_dict['division'] = 'female'
            elif 'mixed' in str(champ.title_type).lower() or 'intergender' in str(champ.title_type).lower():
                champ_dict['division'] = 'intergender'
            else:
                champ_dict['division'] = 'male'
            champ_dict['current_brand'] = champ.assigned_brand
            champ_dict['retired'] = extended.get('retired', False)
            champ_dict['is_retired'] = extended.get('retired', False)
            champ_dict['is_custom'] = extended.get('is_custom', False)
            result.append(champ_dict)
        
        return jsonify({
            'success': True,
            'total': len(result),
            'championships': result
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'championships': []
        }), 500


def _save_manager_state():
    """Save championship manager state to database"""
    try:
        import json
        state_json = json.dumps(championship_manager.to_dict())
        
        cursor = database.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO championship_manager_state (id, state_json, updated_at)
            VALUES (1, ?, datetime('now'))
        ''', (state_json,))
        database.conn.commit()
    except Exception as e:
        print(f"⚠️ Could not save championship manager state: {e}")


# ============================================================================
# STEP 23: PRESTIGE TRACKING ROUTES
# ============================================================================

def _register_prestige_routes(app):
    """Register prestige tracking routes (STEP 23)"""
    
    @app.route('/api/championships/<title_id>/prestige', endpoint='prestige_get_championship_prestige')
    def api_get_championship_prestige(title_id):
        """Get detailed prestige information for a championship"""
        try:
            from simulation.prestige_calculator import prestige_calculator
            
            championship = universe.get_championship_by_id(title_id)
            
            if not championship:
                return jsonify({'success': False, 'error': 'Championship not found'}), 404
            
            # Get prestige analysis
            analysis = prestige_calculator.analyze_prestige_trends(championship)
            
            # Get current champion info
            champion_info = None
            if not championship.is_vacant:
                champion = universe.get_wrestler_by_id(championship.current_holder_id)
                if champion:
                    champion_info = {
                        'id': champion.id,
                        'name': champion.name,
                        'overall_rating': champion.overall_rating,
                        'popularity': champion.popularity,
                        'role': champion.role
                    }
            
            # Calculate reign length
            reign_length_days = 0
            if not championship.is_vacant:
                reign_length_days = championship.get_current_reign_length(
                    universe.current_year,
                    universe.current_week
                )
            
            return jsonify({
                'success': True,
                'prestige': {
                    'current': championship.prestige,
                    'tier': analysis['tier'],
                    'description': analysis['description'],
                    'base_prestige': prestige_calculator.base_prestige.get(championship.title_type, 50)
                },
                'analysis': analysis,
                'champion': champion_info,
                'reign_length_days': reign_length_days,
                'total_defenses': championship.total_defenses,
                'last_defense': {
                    'year': championship.last_defense_year,
                    'week': championship.last_defense_week
                } if championship.last_defense_year else None
            })
        
        except Exception as e:
            import traceback
            return jsonify({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }), 500
    
    
    @app.route('/api/championships/prestige/leaderboard', endpoint='prestige_get_leaderboard')
    def api_get_prestige_leaderboard():
        """Get championships ranked by prestige"""
        try:
            from simulation.prestige_calculator import prestige_calculator
            
            # Get all championships
            championships = universe.championships
            
            # Sort by prestige
            sorted_champs = sorted(championships, key=lambda c: c.prestige, reverse=True)
            
            leaderboard = []
            for champ in sorted_champs:
                leaderboard.append({
                    'id': champ.id,
                    'name': champ.name,
                    'prestige': champ.prestige,
                    'tier': prestige_calculator.get_prestige_tier(champ.prestige),
                    'brand': champ.assigned_brand,
                    'title_type': champ.title_type,
                    'current_holder_name': champ.current_holder_name,
                    'is_vacant': champ.is_vacant,
                    'total_defenses': champ.total_defenses
                })
            
            return jsonify({
                'success': True,
                'total': len(leaderboard),
                'leaderboard': leaderboard
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    @app.route('/api/championships/<title_id>/prestige/history', endpoint='prestige_get_history')
    def api_get_prestige_history(title_id):
        """
        Get prestige history for a championship.
        
        Note: This requires tracking prestige changes over time in the database.
        For now, we'll return recent title defenses as a proxy.
        """
        try:
            championship = universe.get_championship_by_id(title_id)
            
            if not championship:
                return jsonify({'success': False, 'error': 'Championship not found'}), 404
            
            # Get recent title defenses from match history
            cursor = database.conn.cursor()
            cursor.execute('''
                SELECT * FROM match_history
                WHERE title_name = ? AND is_title_match = 1
                ORDER BY year DESC, week DESC
                LIMIT 20
            ''', (championship.name,))
            
            matches = [dict(row) for row in cursor.fetchall()]
            
            # Build history data
            history = []
            for match in matches:
                history.append({
                    'show_name': match['show_name'],
                    'year': match['year'],
                    'week': match['week'],
                    'star_rating': match['star_rating'],
                    'title_changed': match.get('title_changed_hands', False),
                    'is_ppv': match.get('is_ppv', False)
                })
            
            return jsonify({
                'success': True,
                'championship': {
                    'id': championship.id,
                    'name': championship.name,
                    'current_prestige': championship.prestige
                },
                'history': history
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    @app.route('/api/championships/prestige/statistics', endpoint='prestige_get_overall_statistics')
    def api_get_prestige_statistics():
        """Get overall prestige statistics across all championships"""
        try:
            from simulation.prestige_calculator import prestige_calculator
            
            championships = universe.championships
            
            if not championships:
                return jsonify({
                    'success': True,
                    'statistics': {
                        'total_championships': 0,
                        'average_prestige': 0,
                        'by_tier': {},
                        'by_type': {}
                    }
                })
            
            # Calculate statistics
            total_prestige = sum(c.prestige for c in championships)
            avg_prestige = total_prestige / len(championships)
            
            # Group by tier
            by_tier = {}
            for champ in championships:
                tier = prestige_calculator.get_prestige_tier(champ.prestige)
                if tier not in by_tier:
                    by_tier[tier] = 0
                by_tier[tier] += 1
            
            # Group by type
            by_type = {}
            for champ in championships:
                title_type = champ.title_type
                if title_type not in by_type:
                    by_type[title_type] = {
                        'count': 0,
                        'total_prestige': 0,
                        'average_prestige': 0
                    }
                by_type[title_type]['count'] += 1
                by_type[title_type]['total_prestige'] += champ.prestige
            
            # Calculate averages
            for title_type in by_type:
                by_type[title_type]['average_prestige'] = (
                    by_type[title_type]['total_prestige'] / by_type[title_type]['count']
                )
            
            # Find highest and lowest
            highest = max(championships, key=lambda c: c.prestige)
            lowest = min(championships, key=lambda c: c.prestige)
            
            return jsonify({
                'success': True,
                'statistics': {
                    'total_championships': len(championships),
                    'average_prestige': round(avg_prestige, 1),
                    'by_tier': by_tier,
                    'by_type': by_type,
                    'highest': {
                        'name': highest.name,
                        'prestige': highest.prestige,
                        'tier': prestige_calculator.get_prestige_tier(highest.prestige)
                    },
                    'lowest': {
                        'name': lowest.name,
                        'prestige': lowest.prestige,
                        'tier': prestige_calculator.get_prestige_tier(lowest.prestige)
                    }
                }
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    @app.route('/api/championships/<title_id>/prestige/manual-adjust', methods=['POST'], endpoint='prestige_manual_adjust')
    def api_manually_adjust_prestige(title_id):
        """
        Manually adjust championship prestige (for emergency fixes).
        
        Request body:
        {
            "delta": 5,  # Amount to change (-100 to +100)
            "reason": "Storyline rehabilitation"
        }
        """
        try:
            championship = universe.get_championship_by_id(title_id)
            
            if not championship:
                return jsonify({'success': False, 'error': 'Championship not found'}), 404
            
            data = request.get_json()
            delta = data.get('delta', 0)
            reason = data.get('reason', 'Manual adjustment')
            
            if not isinstance(delta, int) or delta < -100 or delta > 100:
                return jsonify({'success': False, 'error': 'Delta must be integer between -100 and +100'}), 400
            
            old_prestige = championship.prestige
            championship.adjust_prestige(delta)
            
            # Save
            universe.save_championship(championship)
            database.conn.commit()
            
            print(f"📊 Manual prestige adjustment: {championship.name} {old_prestige} → {championship.prestige} ({delta:+d}) - {reason}")
            
            return jsonify({
                'success': True,
                'message': f'Prestige adjusted by {delta:+d}',
                'championship': {
                    'id': championship.id,
                    'name': championship.name,
                    'old_prestige': old_prestige,
                    'new_prestige': championship.prestige,
                    'delta': delta
                }
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    @app.route('/api/championships/<title_id>/statistics', endpoint='prestige_get_championship_statistics')
    def api_get_championship_statistics(title_id):
        """Get detailed statistics for a championship"""
        try:
            championship = universe.get_championship_by_id(title_id)
            
            if not championship:
                return jsonify({'success': False, 'error': 'Championship not found'}), 404
            
            # Get title reigns
            total_reigns = len([r for r in championship.history if not r.is_interim])
            interim_reigns = len([r for r in championship.history if r.is_interim])
            
            # Get unique champions
            unique_champions = len(set(r.wrestler_id for r in championship.history if not r.is_interim))
            
            # Find longest reign
            completed_reigns = [r for r in championship.history if r.days_held > 0 and not r.is_interim]
            longest_reign = None
            if completed_reigns:
                longest = max(completed_reigns, key=lambda r: r.days_held)
                longest_reign = {
                    'champion': longest.wrestler_name,
                    'days': longest.days_held,
                    'won_at': longest.won_at_show_name
                }
            
            # Find shortest reign
            shortest_reign = None
            if completed_reigns:
                shortest = min(completed_reigns, key=lambda r: r.days_held)
                shortest_reign = {
                    'champion': shortest.wrestler_name,
                    'days': shortest.days_held,
                    'won_at': shortest.won_at_show_name
                }
            
            # Find most reigns
            from collections import Counter
            reign_counts = Counter(r.wrestler_id for r in championship.history if not r.is_interim)
            most_reigns = None
            if reign_counts:
                most_reigns_id = reign_counts.most_common(1)[0][0]
                most_reigns_count = reign_counts[most_reigns_id]
                # Get name
                for r in championship.history:
                    if r.wrestler_id == most_reigns_id:
                        most_reigns = {
                            'champion': r.wrestler_name,
                            'count': most_reigns_count
                        }
                        break
            
            # Get average match rating (from recent defenses)
            cursor = database.conn.cursor()
            cursor.execute('''
                SELECT AVG(star_rating) as avg_rating, COUNT(*) as match_count
                FROM match_history
                WHERE title_name = ? AND is_title_match = 1
            ''', (championship.name,))
            
            row = cursor.fetchone()
            avg_match_rating = row['avg_rating'] if row and row['avg_rating'] else 0
            total_title_matches = row['match_count'] if row else 0
            
            # Calculate average reign length
            avg_reign_length = 0
            if completed_reigns:
                avg_reign_length = sum(r.days_held for r in completed_reigns) / len(completed_reigns)
            
            return jsonify({
                'success': True,
                'statistics': {
                    'total_reigns': total_reigns,
                    'interim_reigns': interim_reigns,
                    'unique_champions': unique_champions,
                    'total_defenses': championship.total_defenses,
                    'total_title_matches': total_title_matches,
                    'average_match_rating': round(avg_match_rating, 2),
                    'longest_reign': longest_reign,
                    'shortest_reign': shortest_reign,
                    'most_reigns': most_reigns,
                    'average_reign_length': round(avg_reign_length, 1)
                }
            })
        
        except Exception as e:
            import traceback
            return jsonify({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }), 500
    
    
    @app.route('/api/championships/<title_id>/defenses', endpoint='prestige_get_championship_defenses')
    def api_get_championship_defenses(title_id):
        """Get defense history for a championship"""
        try:
            championship = universe.get_championship_by_id(title_id)
            
            if not championship:
                return jsonify({'success': False, 'error': 'Championship not found'}), 404
            
            limit = request.args.get('limit', 50, type=int)
            
            # Get title defenses from match history
            cursor = database.conn.cursor()
            cursor.execute('''
                SELECT * FROM match_history
                WHERE title_name = ? AND is_title_match = 1
                ORDER BY year DESC, week DESC
                LIMIT ?
            ''', (championship.name, limit))
            
            matches = cursor.fetchall()
            
            defenses = []
            for match in matches:
                match_dict = dict(match)
                
                # Determine result
                title_changed = match_dict.get('title_changed_hands', False)
                result = 'lost' if title_changed else 'retained'
                
                # Get champion and challenger names
                side_a_names = match_dict['side_a_names'].split(',') if match_dict.get('side_a_names') else []
                side_b_names = match_dict['side_b_names'].split(',') if match_dict.get('side_b_names') else []
                
                winner = match_dict.get('winner', 'side_a')
                
                if winner == 'side_a':
                    champion_name = side_a_names[0] if side_a_names else 'Unknown'
                    challenger_name = side_b_names[0] if side_b_names else 'Unknown'
                else:
                    champion_name = side_b_names[0] if side_b_names else 'Unknown'
                    challenger_name = side_a_names[0] if side_a_names else 'Unknown'
                
                defenses.append({
                    'show_name': match_dict['show_name'],
                    'year': match_dict['year'],
                    'week': match_dict['week'],
                    'champion_name': champion_name,
                    'challenger_name': challenger_name,
                    'result': result,
                    'star_rating': match_dict['star_rating'],
                    'finish_type': match_dict['finish_type'],
                    'is_ppv': match_dict.get('is_ppv', False)
                })
            
            return jsonify({
                'success': True,
                'title_name': championship.name,
                'total': len(defenses),
                'defenses': defenses
            })
        
        except Exception as e:
            import traceback
            return jsonify({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }), 500
    
    
    @app.route('/api/championships/<title_id>/extended', endpoint='prestige_get_championship_extended')
    def api_get_championship_extended(title_id):
        """
        Get extended championship data (for custom championships).
        
        Returns additional fields like division, weight class, appearance, etc.
        """
        try:
            championship = universe.get_championship_by_id(title_id)
            
            if not championship:
                return jsonify({'success': False, 'error': 'Championship not found'}), 404
            
            # Base championship data
            extended_data = championship.to_dict()
            
            # Add extended fields (these would be stored in a separate table for custom championships)
            # For now, we'll return basic data with placeholders
            extended_data['division'] = 'open'  # mens, womens, intergender, open
            extended_data['weight_class'] = 'open'  # heavyweight, cruiserweight, etc.
            extended_data['is_custom'] = False  # Flag for custom championships
            extended_data['description'] = None
            extended_data['retired'] = False
            
            # Defense requirements (if stored)
            extended_data['defense_requirements'] = {
                'max_days_between_defenses': 30,
                'min_defenses_per_year': 12,
                'ppv_defense_required': True,
                'weekly_tv_defense_allowed': True
            }
            
            # Appearance (for custom championships)
            extended_data['appearance'] = {
                'style': 'classic',
                'primary_color': 'gold',
                'secondary_color': None,
                'strap_color': 'black'
            }
            
            return jsonify({
                'success': True,
                'championship': extended_data
            })
        
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    
    @app.route('/api/championships/situations', endpoint='prestige_get_championship_situations')
    def api_get_championship_situations():
        """
        Get all championship situations requiring attention.
        
        Returns list of championships with issues like:
        - Overdue defenses
        - Vacant titles
        - Injured champions
        - Low prestige
        """
        try:
            from simulation.prestige_calculator import prestige_calculator
            
            championships = universe.championships
            situations = []
            
            current_year = universe.current_year
            current_week = universe.current_week
            
            for champ in championships:
                situation = {
                    'title_id': champ.id,
                    'title_name': champ.name,
                    'tier': champ.title_type.lower().replace(' ', '_'),
                    'situation_type': 'normal',
                    'has_issues': False,
                    'alerts': [],
                    'recommended_actions': []
                }
                
                # Check if vacant
                if champ.is_vacant:
                    situation['situation_type'] = 'vacant'
                    situation['has_issues'] = True
                    situation['alerts'].append(f'Title is currently vacant')
                    situation['recommended_actions'].append('Fill vacancy with tournament or match')
                
                # Check defense frequency
                if champ.last_defense_year and champ.last_defense_week:
                    weeks_since = (current_year - champ.last_defense_year) * 52 + (current_week - champ.last_defense_week)
                    
                    if weeks_since > 8:
                        situation['situation_type'] = 'defense_overdue'
                        situation['has_issues'] = True
                        situation['alerts'].append(f'No defense in {weeks_since} weeks (overdue)')
                        situation['recommended_actions'].append('Schedule title defense immediately')
                    elif weeks_since > 6:
                        situation['has_issues'] = True
                        situation['alerts'].append(f'No defense in {weeks_since} weeks (approaching limit)')
                        situation['recommended_actions'].append('Schedule defense for next show')
                
                # Check champion status
                if not champ.is_vacant:
                    champion = universe.get_wrestler_by_id(champ.current_holder_id)
                    
                    if champion:
                        # Check if injured
                        if champion.is_injured:
                            situation['situation_type'] = 'champion_injured'
                            situation['has_issues'] = True
                            situation['alerts'].append(f'{champion.name} is injured ({champion.injury.severity})')
                            situation['recommended_actions'].append('Consider vacating or interim champion')
                        
                        # Check contract status
                        if champion.contract_expires_soon:
                            situation['has_issues'] = True
                            situation['alerts'].append(f'{champion.name} contract expiring soon ({champion.contract.weeks_remaining} weeks)')
                            situation['recommended_actions'].append('Extend contract or plan title change')
                
                # STEP 23: Check prestige
                if champ.prestige < 35:
                    situation['has_issues'] = True
                    situation['alerts'].append(f'Prestige is critically low ({champ.prestige}/100)')
                    situation['recommended_actions'].append('Book high-quality title matches to rebuild prestige')
                elif champ.prestige < 50:
                    situation['has_issues'] = True
                    situation['alerts'].append(f'Prestige is below average ({champ.prestige}/100)')
                    situation['recommended_actions'].append('Focus on match quality to increase prestige')
                
                # Only include if there are issues or if requested
                if situation['has_issues']:
                    situations.append(situation)
            
            return jsonify({
                'success': True,
                'total': len(situations),
                'situations': situations
            })
        
        except Exception as e:
            import traceback
            return jsonify({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }), 500
    
    
    @app.route('/api/championships/defense-schedule', endpoint='prestige_get_defense_schedule')
    def api_get_defense_schedule():
        """
        Get upcoming defense schedule for all championships.
        Shows which titles need to be defended soon.
        """
        try:
            championships = universe.championships
            current_year = universe.current_year
            current_week = universe.current_week
            
            schedule = []
            
            for champ in championships:
                if champ.is_vacant:
                    continue
                
                # Calculate weeks since last defense
                weeks_since = 0
                if champ.last_defense_year and champ.last_defense_week:
                    weeks_since = (current_year - champ.last_defense_year) * 52 + (current_week - champ.last_defense_week)
                
                # Determine urgency
                urgency_level = 0
                urgency_label = 'Normal'
                is_overdue = False
                
                if weeks_since > 8:
                    urgency_level = 3
                    urgency_label = 'CRITICAL'
                    is_overdue = True
                elif weeks_since > 6:
                    urgency_level = 2
                    urgency_label = 'High'
                elif weeks_since > 4:
                    urgency_level = 1
                    urgency_label = 'Medium'
                
                # Get champion info
                champion_name = champ.interim_holder_name if champ.has_interim_champion else champ.current_holder_name
                
                schedule.append({
                    'title_id': champ.id,
                    'title_name': champ.name,
                    'title_tier': champ.title_type,
                    'champion_name': champion_name,
                    'is_interim': champ.has_interim_champion,
                    'days_since_defense': weeks_since * 7,
                    'weeks_since_defense': weeks_since,
                    'urgency_level': urgency_level,
                    'urgency_label': urgency_label,
                    'is_overdue': is_overdue,
                    'days_until_required': max(0, (8 - weeks_since) * 7)
                })
            
            # Sort by urgency
            schedule.sort(key=lambda x: x['urgency_level'], reverse=True)
            
            return jsonify({
                'success': True,
                'current_year': current_year,
                'current_week': current_week,
                'schedule': schedule
            })
        
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


# ============================================================================
# UNIFICATION ROUTES (STEP 22)
# ============================================================================

@championship_bp.route('/unify/check', methods=['POST'])
def api_check_unification():
    """
    Check if two titles can be unified.
    
    Request body:
    {
        "title1_id": "title001",
        "title2_id": "title002"
    }
    """
    try:
        data = request.get_json()
        
        title1_id = data.get('title1_id')
        title2_id = data.get('title2_id')
        
        if not title1_id or not title2_id:
            return jsonify({
                'success': False,
                'error': 'Both title1_id and title2_id are required'
            }), 400
        
        can_unify, message = championship_manager.can_unify_titles(
            title1_id,
            title2_id,
            universe.championships
        )
        
        # Get title details for response
        title1 = universe.get_championship_by_id(title1_id)
        title2 = universe.get_championship_by_id(title2_id)
        
        return jsonify({
            'success': True,
            'can_unify': can_unify,
            'message': message,
            'titles': {
                'title1': title1.to_dict() if title1 else None,
                'title2': title2.to_dict() if title2 else None
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@championship_bp.route('/unify', methods=['POST'])
def api_unify_championships():
    """
    Unify two championships into one.
    
    Request body:
    {
        "primary_title_id": "title001",
        "secondary_title_id": "title002",
        "winner_id": "w001",
        "unification_type": "undisputed",  # undisputed, absorbed, new_title
        "show_name": "Victory Dome",
        "resulting_title_name": "Undisputed World Championship",  # Required for new_title
        "notes": "Historic unification match"
    }
    """
    try:
        data = request.get_json()
        
        primary_title_id = data.get('primary_title_id')
        secondary_title_id = data.get('secondary_title_id')
        winner_id = data.get('winner_id')
        unification_type_str = data.get('unification_type', 'undisputed')
        show_name = data.get('show_name', f'Week {universe.current_week} Show')
        resulting_title_name = data.get('resulting_title_name')
        notes = data.get('notes', '')
        
        # Validate required fields
        if not all([primary_title_id, secondary_title_id, winner_id]):
            return jsonify({
                'success': False,
                'error': 'primary_title_id, secondary_title_id, and winner_id are required'
            }), 400
        
        # Get winner
        winner = universe.get_wrestler_by_id(winner_id)
        if not winner:
            return jsonify({'success': False, 'error': 'Winner not found'}), 404
        
        # Parse unification type
        from services.championship_manager import UnificationType
        try:
            unification_type = UnificationType(unification_type_str)
        except ValueError:
            return jsonify({
                'success': False,
                'error': f'Invalid unification_type. Must be one of: undisputed, absorbed, new_title'
            }), 400
        
        # Check if unification is valid
        can_unify, message = championship_manager.can_unify_titles(
            primary_title_id,
            secondary_title_id,
            universe.championships
        )
        
        if not can_unify:
            return jsonify({'success': False, 'error': message}), 400
        
        show_id = f"show_y{universe.current_year}_w{universe.current_week}"
        
        # Perform unification
        success, result = championship_manager.unify_championships(
            primary_title_id=primary_title_id,
            secondary_title_id=secondary_title_id,
            winner_id=winner_id,
            winner_name=winner.name,
            year=universe.current_year,
            week=universe.current_week,
            show_id=show_id,
            show_name=show_name,
            unification_type=unification_type,
            resulting_title_name=resulting_title_name,
            championships=universe.championships,
            notes=notes
        )
        
        if not success:
            return jsonify({'success': False, 'error': result.get('error', 'Unification failed')}), 400
        
        # Handle new title creation if needed
        if result.get('requires_new_title'):
            from models.championship import Championship
            
            new_data = result['new_title_data']
            new_championship = Championship(
                title_id=new_data['id'],
                name=new_data['name'],
                assigned_brand=new_data['assigned_brand'],
                title_type=new_data['title_type'],
                prestige=new_data['prestige']
            )
            
            # Award to winner
            new_championship.award_title(
                wrestler_id=winner_id,
                wrestler_name=winner.name,
                show_id=show_id,
                show_name=show_name,
                year=universe.current_year,
                week=universe.current_week
            )
            
            # Save new championship
            database.save_championship(new_championship)
            
            # Save extended data
            from persistence.championship_custom_db import save_championship_extended
            save_championship_extended(database, new_data['id'], {
                'is_custom': True,
                'created_year': universe.current_year,
                'created_week': universe.current_week,
                'description': f"Created through unification of {result['primary_title'].name} and {result['secondary_title'].name}"
            })
            
            result['new_championship'] = new_championship.to_dict()
        
        # Save updated championships
        if result.get('primary_title'):
            universe.save_championship(result['primary_title'])
        if result.get('secondary_title'):
            universe.save_championship(result['secondary_title'])
        
        # Save manager state
        _save_manager_state()
        database.conn.commit()
        
        # Log the historic moment
        from persistence.championship_custom_db import log_championship_action
        log_championship_action(
            database,
            result.get('resulting_title_id', primary_title_id),
            'unification',
            universe.current_year,
            universe.current_week,
            f"Unified {result.get('primary_title', {}).name if hasattr(result.get('primary_title'), 'name') else 'title'} and {result.get('secondary_title', {}).name if hasattr(result.get('secondary_title'), 'name') else 'title'} by {winner.name}"
        )
        
        return jsonify({
            'success': True,
            'result': {
                'unification_id': result.get('unification_id'),
                'resulting_title_id': result.get('resulting_title_id'),
                'resulting_title_name': result.get('resulting_title_name'),
                'message': result.get('message'),
                'new_championship': result.get('new_championship')
            }
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@championship_bp.route('/unification-history')
def api_get_unification_history():
    """Get all unification history"""
    try:
        title_id = request.args.get('title_id')
        
        history = championship_manager.get_unification_history(title_id)
        
        return jsonify({
            'success': True,
            'total': len(history),
            'history': history
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# SPLIT ROUTES (STEP 22)
# ============================================================================

@championship_bp.route('/<title_id>/split', methods=['POST'])
def api_split_championship(title_id):
    """
    Split one championship into multiple titles.
    
    Request body:
    {
        "new_titles": [
            {
                "name": "ROC Alpha World Championship",
                "assigned_brand": "ROC Alpha",
                "prestige": 85
            },
            {
                "name": "ROC Velocity World Championship",
                "assigned_brand": "ROC Velocity",
                "prestige": 85
            }
        ],
        "reason": "brand_split",
        "show_name": "Draft Night",
        "notes": "Following the brand split..."
    }
    """
    try:
        data = request.get_json()
        
        new_titles_data = data.get('new_titles', [])
        reason = data.get('reason', 'brand_split')
        show_name = data.get('show_name', f'Week {universe.current_week} Show')
        notes = data.get('notes', '')
        
        if len(new_titles_data) < 2:
            return jsonify({
                'success': False,
                'error': 'At least 2 new titles required for a split'
            }), 400
        
        # Get original championship
        original = universe.get_championship_by_id(title_id)
        if not original:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        show_id = f"show_y{universe.current_year}_w{universe.current_week}"
        
        # Generate IDs for new titles
        from models.championship_factory import ChampionshipFactory
        
        for title_data in new_titles_data:
            if 'id' not in title_data:
                title_data['id'] = ChampionshipFactory.generate_championship_id(database)
            if 'title_type' not in title_data:
                title_data['title_type'] = original.title_type
        
        # Perform split
        success, result = championship_manager.split_championship(
            original_title_id=title_id,
            new_titles_data=new_titles_data,
            year=universe.current_year,
            week=universe.current_week,
            show_id=show_id,
            show_name=show_name,
            reason=reason,
            championships=universe.championships,
            notes=notes
        )
        
        if not success:
            return jsonify({'success': False, 'error': result.get('error')}), 400
        
        # Create new championships
        from models.championship import Championship
        
        created_championships = []
        for title_data in result['new_titles_to_create']:
            new_champ = Championship(
                title_id=title_data['id'],
                name=title_data['name'],
                assigned_brand=title_data['assigned_brand'],
                title_type=title_data['title_type'],
                prestige=title_data.get('prestige', original.prestige)
            )
            
            database.save_championship(new_champ)
            
            # Save extended data
            from persistence.championship_custom_db import save_championship_extended
            save_championship_extended(database, title_data['id'], {
                'is_custom': True,
                'created_year': universe.current_year,
                'created_week': universe.current_week,
                'description': f"Created through split of {original.name}",
                'split_from': title_id
            })
            
            # Initialize lineage
            championship_manager.initialize_lineage(
                title_data['id'],
                title_data['name'],
                universe.current_year,
                universe.current_week
            )
            
            created_championships.append(new_champ.to_dict())
        
        # Mark original as retired/split
        from persistence.championship_custom_db import save_championship_extended, get_championship_extended
        
        extended = get_championship_extended(database, title_id) or {}
        extended['status'] = 'split'
        extended['split_year'] = universe.current_year
        extended['split_week'] = universe.current_week
        extended['split_into'] = [t['id'] for t in new_titles_data]
        save_championship_extended(database, title_id, extended)
        
        # Save original championship
        universe.save_championship(original)
        
        # Save manager state
        _save_manager_state()
        database.conn.commit()
        
        # Log action
        from persistence.championship_custom_db import log_championship_action
        log_championship_action(
            database,
            title_id,
            'split',
            universe.current_year,
            universe.current_week,
            f"Split into {len(new_titles_data)} new championships"
        )
        
        return jsonify({
            'success': True,
            'result': {
                'split_id': result.get('split_id'),
                'original_title': original.to_dict(),
                'new_championships': created_championships,
                'message': result.get('message')
            }
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@championship_bp.route('/split-history')
def api_get_split_history():
    """Get all split history"""
    try:
        title_id = request.args.get('title_id')
        
        history = championship_manager.get_split_history(title_id)
        
        return jsonify({
            'success': True,
            'total': len(history),
            'history': history
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# REBOOT/RESTART ROUTES (STEP 22)
# ============================================================================

@championship_bp.route('/<title_id>/reboot', methods=['POST'])
def api_reboot_championship(title_id):
    """
    Reboot a championship with a fresh lineage.
    
    Request body:
    {
        "keep_name": true,
        "new_name": "New Championship Name",  # Only if keep_name is false
        "reset_prestige": false,
        "notes": "Fresh start for the championship"
    }
    """
    try:
        data = request.get_json() if request.is_json else {}
        
        keep_name = data.get('keep_name', True)
        new_name = data.get('new_name')
        reset_prestige = data.get('reset_prestige', False)
        notes = data.get('notes', '')
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        # Perform reboot
        success, result = championship_manager.reboot_championship(
            title_id=title_id,
            year=universe.current_year,
            week=universe.current_week,
            championships=universe.championships,
            keep_name=keep_name,
            new_name=new_name,
            reset_prestige=reset_prestige,
            notes=notes
        )
        
        if not success:
            return jsonify({'success': False, 'error': result.get('error')}), 400
        
        # Save championship
        universe.save_championship(result['championship'])
        
        # Save manager state
        _save_manager_state()
        database.conn.commit()
        
        # Log action
        from persistence.championship_custom_db import log_championship_action
        log_championship_action(
            database,
            title_id,
            'rebooted',
            universe.current_year,
            universe.current_week,
            f"Lineage #{result['lineage_number']} started. {notes}"
        )
        
        return jsonify({
            'success': True,
            'result': {
                'lineage_id': result.get('lineage_id'),
                'lineage_number': result.get('lineage_number'),
                'championship': result['championship'].to_dict(),
                'message': result.get('message')
            }
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@championship_bp.route('/<title_id>/lineages')
def api_get_championship_lineages(title_id):
    """Get all lineages for a championship"""
    try:
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        lineages = championship_manager.get_championship_lineages(title_id)
        current = championship_manager.get_current_lineage(title_id)
        
        return jsonify({
            'success': True,
            'title_id': title_id,
            'title_name': championship.name,
            'total_lineages': len(lineages),
            'current_lineage': current.to_dict() if current else None,
            'lineages': [l.to_dict() for l in lineages]
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# DEACTIVATION ROUTES (STEP 22)
# ============================================================================

@championship_bp.route('/<title_id>/deactivate', methods=['POST'])
def api_deactivate_championship(title_id):
    """
    Deactivate a championship (make inactive but not retired).
    
    Request body:
    {
        "reason": "Not enough competitors in division"
    }
    """
    try:
        data = request.get_json() if request.is_json else {}
        reason = data.get('reason', 'Championship deactivated')
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        success, result = championship_manager.deactivate_championship(
            title_id=title_id,
            year=universe.current_year,
            week=universe.current_week,
            championships=universe.championships,
            reason=reason
        )
        
        if not success:
            return jsonify({'success': False, 'error': result.get('error')}), 400
        
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'result': result
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@championship_bp.route('/<title_id>/activate', methods=['POST'])
def api_activate_championship(title_id):
    """Reactivate an inactive championship"""
    try:
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        success, result = championship_manager.reactivate_championship(
            title_id=title_id,
            year=universe.current_year,
            week=universe.current_week,
            championships=universe.championships
        )
        
        if not success:
            return jsonify({'success': False, 'error': result.get('error')}), 400
        
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'result': result
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# TRANSFER ROUTES (STEP 22)
# ============================================================================

@championship_bp.route('/<title_id>/transfer', methods=['POST'])
def api_transfer_championship(title_id):
    """
    Transfer a championship between brands/divisions.
    
    Request body:
    {
        "transfer_type": "brand_change",  # brand_change, division_change, brand_exclusive_toggle
        "new_value": "ROC Velocity",
        "reason": "Brand shake-up"
    }
    """
    try:
        data = request.get_json()
        
        transfer_type_str = data.get('transfer_type')
        new_value = data.get('new_value')
        reason = data.get('reason', '')
        
        if not transfer_type_str or not new_value:
            return jsonify({
                'success': False,
                'error': 'transfer_type and new_value are required'
            }), 400
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        from services.championship_manager import TransferType
        try:
            transfer_type = TransferType(transfer_type_str)
        except ValueError:
            return jsonify({
                'success': False,
                'error': f'Invalid transfer_type. Must be one of: brand_change, division_change, brand_exclusive_toggle'
            }), 400
        
        success, result = championship_manager.transfer_championship(
            title_id=title_id,
            transfer_type=transfer_type,
            new_value=new_value,
            year=universe.current_year,
            week=universe.current_week,
            championships=universe.championships,
            reason=reason
        )
        
        if not success:
            return jsonify({'success': False, 'error': result.get('error')}), 400
        
        # Save championship if brand changed
        if transfer_type == TransferType.BRAND_CHANGE:
            universe.save_championship(championship)
        
        # Save manager state
        _save_manager_state()
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'result': result
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@championship_bp.route('/transfer-history')
def api_get_transfer_history():
    """Get all transfer history"""
    try:
        title_id = request.args.get('title_id')
        
        history = championship_manager.get_transfer_history(title_id)
        
        return jsonify({
            'success': True,
            'total': len(history),
            'history': history
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# BRAND EXCLUSIVITY ROUTES (STEP 22)
# ============================================================================

@championship_bp.route('/<title_id>/check-eligibility/<wrestler_id>')
def api_check_wrestler_title_eligibility(title_id, wrestler_id):
    """Check if a wrestler is eligible to compete for a championship"""
    try:
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        eligible, message = championship_manager.check_brand_eligibility(
            title_id,
            wrestler.primary_brand,
            universe.championships
        )
        
        # Also check division eligibility
        from persistence.championship_custom_db import get_championship_extended
        extended = get_championship_extended(database, title_id) or {}
        
        division = extended.get('division', 'open')
        division_eligible = True
        division_message = ""
        
        if division == 'mens' and wrestler.gender != 'Male':
            division_eligible = False
            division_message = "This is a men's division championship"
        elif division == 'womens' and wrestler.gender != 'Female':
            division_eligible = False
            division_message = "This is a women's division championship"
        
        final_eligible = eligible and division_eligible
        
        return jsonify({
            'success': True,
            'eligible': final_eligible,
            'brand_eligible': eligible,
            'brand_message': message,
            'division_eligible': division_eligible,
            'division_message': division_message,
            'wrestler': {
                'id': wrestler.id,
                'name': wrestler.name,
                'brand': wrestler.primary_brand,
                'gender': wrestler.gender
            },
            'championship': {
                'id': championship.id,
                'name': championship.name,
                'brand': championship.assigned_brand,
                'division': division
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@championship_bp.route('/<title_id>/eligible-wrestlers')
def api_get_eligible_wrestlers(title_id):
    """Get all wrestlers eligible to compete for a championship"""
    try:
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        from persistence.championship_custom_db import get_championship_extended
        extended = get_championship_extended(database, title_id) or {}
        
        division = extended.get('division', 'open')
        brand_exclusive = extended.get('brand_exclusive', True)
        
        eligible_wrestlers = []
        
        for wrestler in universe.get_active_wrestlers():
            # Skip current champion
            if wrestler.id == championship.current_holder_id:
                continue
            
            # Check brand
            if brand_exclusive and championship.assigned_brand != 'Cross-Brand':
                if wrestler.primary_brand != championship.assigned_brand:
                    continue
            
            # Check division
            if division == 'mens' and wrestler.gender != 'Male':
                continue
            if division == 'womens' and wrestler.gender != 'Female':
                continue
            
            eligible_wrestlers.append({
                'id': wrestler.id,
                'name': wrestler.name,
                'brand': wrestler.primary_brand,
                'role': wrestler.role,
                'popularity': wrestler.popularity,
                'momentum': wrestler.momentum
            })
        
        # Sort by popularity
        eligible_wrestlers.sort(key=lambda w: w['popularity'], reverse=True)
        
        return jsonify({
            'success': True,
            'title_id': title_id,
            'title_name': championship.name,
            'total': len(eligible_wrestlers),
            'wrestlers': eligible_wrestlers
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# FULL HISTORY ROUTES (STEP 22)
# ============================================================================

@championship_bp.route('/<title_id>/full-history')
def api_get_full_title_history(title_id):
    """Get complete history for a championship"""
    try:
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        history = championship_manager.get_full_title_history(title_id)
        
        # Add reign history
        history['reigns'] = [r.to_dict() for r in championship.history]
        
        # Add action log
        from persistence.championship_custom_db import get_championship_action_log
        history['action_log'] = get_championship_action_log(database, title_id, 50)
        
        return jsonify({
            'success': True,
            'title_id': title_id,
            'title_name': championship.name,
            'history': history
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# STRIP CHAMPION ROUTE (STEP 22)
# ============================================================================

@championship_bp.route('/<title_id>/strip', methods=['POST'])
def api_strip_champion(title_id):
    """
    Strip the current champion (authority removes title).
    
    Request body:
    {
        "reason": "Failure to defend",
        "grant_rematch": true,
        "show_name": "Monday Night Alpha"
    }
    """
    try:
        data = request.get_json() if request.is_json else {}
        
        reason = data.get('reason', 'Stripped by authority')
        grant_rematch = data.get('grant_rematch', True)
        show_name = data.get('show_name', f'Week {universe.current_week} Show')
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        if championship.is_vacant:
            return jsonify({'success': False, 'error': 'Championship is already vacant'}), 400
        
        stripped_champion_id = championship.current_holder_id
        stripped_champion_name = championship.current_holder_name
        
        show_id = f"show_y{universe.current_year}_w{universe.current_week}"
        
        # Vacate the title
        championship.vacate_title(
            show_id=show_id,
            show_name=show_name,
            year=universe.current_year,
            week=universe.current_week,
            reason=f"Stripped: {reason}"
        )
        
        # Grant rematch clause if requested
        guaranteed_shot = None
        if grant_rematch and stripped_champion_id:
            from models.championship_hierarchy import championship_hierarchy
            
            shot = championship_hierarchy.grant_title_shot(
                wrestler_id=stripped_champion_id,
                wrestler_name=stripped_champion_name,
                title_id=title_id,
                title_name=championship.name,
                reason='rematch_clause',
                year=universe.current_year,
                week=universe.current_week,
                notes=f"Rematch clause after being stripped. Reason: {reason}"
            )
            
            from persistence.championship_db import save_guaranteed_shot
            save_guaranteed_shot(database, shot.to_dict())
            
            guaranteed_shot = shot.to_dict()
        
        # Save championship
        universe.save_championship(championship)
        database.conn.commit()
        
        # Log action
        from persistence.championship_custom_db import log_championship_action
        log_championship_action(
            database,
            title_id,
            'stripped',
            universe.current_year,
            universe.current_week,
            f"{stripped_champion_name} stripped. Reason: {reason}"
        )
        
        return jsonify({
            'success': True,
            'message': f'{stripped_champion_name} has been STRIPPED of the {championship.name}!',
            'stripped_champion': {
                'id': stripped_champion_id,
                'name': stripped_champion_name
            },
            'guaranteed_shot': guaranteed_shot,
            'championship': championship.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# ============================================================================
# MANAGER STATE ROUTE (STEP 22)
# ============================================================================

@championship_bp.route('/manager/state')
def api_get_manager_state():
    """Get current championship manager state (for debugging)"""
    try:
        return jsonify({
            'success': True,
            'state': championship_manager.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# RETIREMENT & DELETION ROUTES (STEP 23)
# ============================================================================

@championship_bp.route('/<title_id>/retire', methods=['POST'])
def api_retire_championship(title_id):
    """
    Retire a championship (make it inactive permanently).
    
    Request body:
    {
        "reason": "Championship deactivated due to brand merger"
    }
    """
    try:
        championship = universe.get_championship_by_id(title_id)
        
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        # Check if it's already retired
        from persistence.championship_custom_db import get_championship_extended
        extended = get_championship_extended(database, title_id) or {}
        
        if extended.get('retired'):
            return jsonify({'success': False, 'error': 'Championship is already retired'}), 400
        
        data = request.get_json() if request.is_json else {}
        reason = data.get('reason', 'Championship retired')
        
        # Mark as retired in extended data
        from persistence.championship_custom_db import retire_championship
        retire_championship(
            database,
            title_id,
            universe.current_year,
            universe.current_week,
            reason
        )
        
        # Update extended data with retired flag
        extended['retired'] = True
        extended['retired_year'] = universe.current_year
        extended['retired_week'] = universe.current_week
        
        from persistence.championship_custom_db import save_championship_extended
        save_championship_extended(database, title_id, extended)
        
        database.conn.commit()
        
        print(f"🗃️ Championship retired: {championship.name}")
        print(f"   Reason: {reason}")
        
        return jsonify({
            'success': True,
            'message': f'{championship.name} has been retired',
            'championship': championship.to_dict()
        })
    
    except Exception as e:
        import traceback
        database.conn.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@championship_bp.route('/<title_id>/reactivate', methods=['POST'])
def api_reactivate_championship(title_id):
    """
    Reactivate a retired championship.
    """
    try:
        championship = universe.get_championship_by_id(title_id)
        
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        from persistence.championship_custom_db import get_championship_extended, reactivate_championship
        extended = get_championship_extended(database, title_id)
        
        if not extended or not extended.get('retired'):
            return jsonify({'success': False, 'error': 'Championship is not retired'}), 400
        
        # Reactivate
        reactivate_championship(
            database,
            title_id,
            universe.current_year,
            universe.current_week
        )
        
        # Update extended data
        extended['retired'] = False
        extended['retired_year'] = None
        extended['retired_week'] = None
        
        from persistence.championship_custom_db import save_championship_extended
        save_championship_extended(database, title_id, extended)
        
        database.conn.commit()
        
        print(f"🔄 Championship reactivated: {championship.name}")
        
        return jsonify({
            'success': True,
            'message': f'{championship.name} has been reactivated',
            'championship': championship.to_dict()
        })
    
    except Exception as e:
        import traceback
        database.conn.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@championship_bp.route('/<title_id>/delete', methods=['DELETE'])
def api_delete_championship(title_id):
    """
    Permanently delete a championship.
    
    ⚠️ WARNING: This action cannot be undone!
    All title history, defenses, and records will be permanently removed.
    """
    try:
        championship = universe.get_championship_by_id(title_id)
        
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        title_name = championship.name
        
        # Perform deletion
        from persistence.championship_custom_db import delete_championship
        delete_championship(database, title_id)
        
        database.conn.commit()
        
        print(f"🗑️ Championship DELETED: {title_name}")
        print(f"   ⚠️ All associated data has been permanently removed")
        
        return jsonify({
            'success': True,
            'message': f'{title_name} has been permanently deleted'
        })
    
    except Exception as e:
        import traceback
        database.conn.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@championship_bp.route('/<title_id>/update', methods=['PUT'])
def api_update_championship(title_id):
    """
    Update championship extended data.
    
    Request body:
    {
        "description": "New description",
        "defense_requirements": {
            "max_days_between_defenses": 30,
            "min_defenses_per_year": 12,
            "ppv_defense_required": true,
            "weekly_tv_defense_allowed": true
        }
    }
    """
    try:
        championship = universe.get_championship_by_id(title_id)
        
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        from persistence.championship_custom_db import get_championship_extended, save_championship_extended
        
        extended = get_championship_extended(database, title_id) or {}
        data = request.get_json()
        
        # Update allowed fields
        if 'description' in data:
            extended['description'] = data['description']
        
        if 'defense_requirements' in data:
            extended['defense_requirements'] = data['defense_requirements']
        
        # Save
        save_championship_extended(database, title_id, extended)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Championship updated successfully'
        })
    
    except Exception as e:
        import traceback
        database.conn.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
