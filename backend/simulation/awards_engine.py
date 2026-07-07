"""
Awards Engine
Calculates nominees and winners for end-of-year awards.
"""

from typing import List, Dict, Any, Optional
from models.awards import Award, AwardNominee, AwardCategory, AwardsCeremony
from persistence.database import Database
import json


class AwardsEngine:
    """
    Awards calculation engine.
    Analyzes the year's statistics to determine nominees and winners.
    """
    
    def __init__(self):
        pass
    
    def calculate_year_end_awards(
        self,
        year: int,
        database: Database,
        universe_state
    ) -> AwardsCeremony:
        """
        Calculate all awards for the completed year.
        Called at the end of Week 52.
        """
        
        print(f"\n{'='*60}")
        print(f"🏆 CALCULATING YEAR {year} AWARDS")
        print(f"{'='*60}\n")
        
        awards = []
        
        # Wrestler Awards
        awards.append(self._calculate_wrestler_of_the_year(year, database, universe_state))
        awards.append(self._calculate_breakout_star(year, database, universe_state))
        awards.append(self._calculate_most_improved(year, database, universe_state))
        awards.append(self._calculate_comeback_of_the_year(year, database, universe_state))
        
        # Match Awards
        awards.append(self._calculate_match_of_the_year(year, database))
        awards.append(self._calculate_feud_of_the_year(year, database, universe_state))
        
        # Championship Awards
        awards.append(self._calculate_champion_of_the_year(year, database))
        awards.append(self._calculate_title_reign_of_the_year(year, database))
        
        # Tag Team Awards
        awards.append(self._calculate_tag_team_of_the_year(year, database, universe_state))
        awards.append(self._calculate_tag_match_of_the_year(year, database))
        
        # Performance Awards
        awards.append(self._calculate_best_technical(year, database, universe_state))
        awards.append(self._calculate_best_high_flyer(year, database, universe_state))
        awards.append(self._calculate_best_brawler(year, database, universe_state))
        
        # Microphone Awards
        awards.append(self._calculate_best_on_mic(year, database, universe_state))
        
        # Show Awards
        awards.append(self._calculate_show_of_the_year(year, database))
        awards.append(self._calculate_best_brand(year, database))
        
        # Filter out None awards (categories with no valid nominees)
        awards = [a for a in awards if a is not None]
        
        # Ceremony happens at Week 52
        ceremony = AwardsCeremony(
            year=year,
            awards=awards,
            ceremony_date_week=52
        )
        
        print(f"✅ Calculated {len(awards)} awards for Year {year}\n")
        
        return ceremony
    
    # ========================================================================
    # WRESTLER AWARDS
    # ========================================================================
    
    def _calculate_wrestler_of_the_year(
        self,
        year: int,
        database: Database,
        universe_state
    ) -> Optional[Award]:
        """
        Wrestler of the Year - Overall best performer.
        Criteria: Wins, star ratings, popularity, title reigns
        """
        
        cursor = database.conn.cursor()
        
        # Get all wrestlers who competed this year
        cursor.execute('''
            SELECT DISTINCT wrestler_id FROM (
                SELECT json_each.value as wrestler_id
                FROM match_history, json_each(side_a_ids)
                WHERE year = ?
                UNION
                SELECT json_each.value as wrestler_id
                FROM match_history, json_each(side_b_ids)
                WHERE year = ?
            )
        ''', (year, year))
        
        wrestler_ids = [row[0] for row in cursor.fetchall()]
        
        if not wrestler_ids:
            return None
        
        nominees_data = []
        
        for wrestler_id in wrestler_ids:
            wrestler = universe_state.get_wrestler_by_id(wrestler_id)
            if not wrestler or wrestler.is_retired:
                continue
            
            # Get year stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as matches,
                    SUM(CASE WHEN (side_a_ids LIKE ? AND winner = 'side_a') 
                             OR (side_b_ids LIKE ? AND winner = 'side_b') 
                        THEN 1 ELSE 0 END) as wins,
                    AVG(star_rating) as avg_rating,
                    MAX(star_rating) as best_rating,
                    SUM(CASE WHEN is_title_match = 1 THEN 1 ELSE 0 END) as title_matches
                FROM match_history
                WHERE (side_a_ids LIKE ? OR side_b_ids LIKE ?)
                  AND year = ?
            ''', (f'%{wrestler_id}%', f'%{wrestler_id}%', 
                  f'%{wrestler_id}%', f'%{wrestler_id}%', year))
            
            stats = cursor.fetchone()
            
            if not stats or stats[0] < 5:  # Minimum 5 matches
                continue
            
            matches, wins, avg_rating, best_rating, title_matches = stats
            
            # Get title reigns this year
            cursor.execute('''
                SELECT COUNT(*) FROM title_reigns
                WHERE wrestler_id = ? 
                  AND won_date_year = ?
            ''', (wrestler_id, year))
            
            title_reigns = cursor.fetchone()[0]
            
            # Calculate score
            score = 0.0
            score += wins * 5  # Wins
            score += (avg_rating or 0) * 10  # Match quality
            score += wrestler.popularity * 0.5  # Popularity
            score += title_reigns * 20  # Title reigns
            score += title_matches * 2  # Title matches
            
            nominees_data.append({
                'wrestler_id': wrestler_id,
                'wrestler_name': wrestler.name,
                'score': score,
                'stats': {
                    'matches': matches,
                    'wins': wins,
                    'avg_rating': round(avg_rating or 0, 2),
                    'best_rating': round(best_rating or 0, 2),
                    'title_reigns': title_reigns,
                    'popularity': wrestler.popularity
                }
            })
        
        # Sort by score and take top 5
        nominees_data.sort(key=lambda x: x['score'], reverse=True)
        nominees_data = nominees_data[:5]
        
        if not nominees_data:
            return None
        
        # Create nominees
        nominees = []
        for data in nominees_data:
            reason = f"{data['stats']['wins']} wins, {data['stats']['avg_rating']}⭐ avg rating"
            if data['stats']['title_reigns'] > 0:
                reason += f", {data['stats']['title_reigns']} title reign(s)"
            
            nominee = AwardNominee(
                nominee_id=data['wrestler_id'],
                nominee_name=data['wrestler_name'],
                nominee_type='wrestler',
                stats=data['stats'],
                reason=reason,
                score=data['score']
            )
            nominees.append(nominee)
        
        # Winner is highest score
        winner = nominees_data[0]
        
        return Award(
            category=AwardCategory.WRESTLER_OF_THE_YEAR,
            year=year,
            nominees=nominees,
            winner_id=winner['wrestler_id'],
            winner_name=winner['wrestler_name']
        )
    
    def _calculate_breakout_star(
        self,
        year: int,
        database: Database,
        universe_state
    ) -> Optional[Award]:
        """
        Breakout Star - Wrestler who made the biggest impact in their first year.
        Criteria: High performance in first year of competition
        """
        
        cursor = database.conn.cursor()
        
        # Get wrestlers who debuted this year - JOIN with wrestlers table
        cursor.execute('''
            SELECT m.wrestler_id, w.name
            FROM milestones m
            JOIN wrestlers w ON m.wrestler_id = w.id
            WHERE m.milestone_type = 'debut'
              AND m.year = ?
        ''', (year,))
        
        debut_wrestlers = cursor.fetchall()
        
        if not debut_wrestlers:
            return None
        
        nominees_data = []
        
        for row in debut_wrestlers:
            wrestler_id, wrestler_name = row
            wrestler = universe_state.get_wrestler_by_id(wrestler_id)
            
            if not wrestler:
                continue
            
            # Get stats from debut year
            cursor.execute('''
                SELECT 
                    COUNT(*) as matches,
                    SUM(CASE WHEN (side_a_ids LIKE ? AND winner = 'side_a') 
                             OR (side_b_ids LIKE ? AND winner = 'side_b') 
                        THEN 1 ELSE 0 END) as wins,
                    AVG(star_rating) as avg_rating
                FROM match_history
                WHERE (side_a_ids LIKE ? OR side_b_ids LIKE ?)
                  AND year = ?
            ''', (f'%{wrestler_id}%', f'%{wrestler_id}%',
                  f'%{wrestler_id}%', f'%{wrestler_id}%', year))
            
            stats = cursor.fetchone()
            matches, wins, avg_rating = stats
            
            if matches < 3:  # Minimum 3 matches
                continue
            
            # Score based on immediate impact
            score = 0.0
            score += (wins or 0) * 10
            score += (avg_rating or 0) * 15
            score += wrestler.momentum * 0.3
            score += wrestler.popularity * 0.4
            
            nominees_data.append({
                'wrestler_id': wrestler_id,
                'wrestler_name': wrestler_name,
                'score': score,
                'stats': {
                    'matches': matches,
                    'wins': wins or 0,
                    'avg_rating': round(avg_rating or 0, 2),
                    'momentum': wrestler.momentum
                }
            })
        
        nominees_data.sort(key=lambda x: x['score'], reverse=True)
        nominees_data = nominees_data[:5]
        
        if not nominees_data:
            return None
        
        nominees = []
        for data in nominees_data:
            reason = f"Debuted Year {year}, {data['stats']['wins']} wins in {data['stats']['matches']} matches"
            
            nominee = AwardNominee(
                nominee_id=data['wrestler_id'],
                nominee_name=data['wrestler_name'],
                nominee_type='wrestler',
                stats=data['stats'],
                reason=reason,
                score=data['score']
            )
            nominees.append(nominee)
        
        winner = nominees_data[0]
        
        return Award(
            category=AwardCategory.BREAKOUT_STAR,
            year=year,
            nominees=nominees,
            winner_id=winner['wrestler_id'],
            winner_name=winner['wrestler_name']
        )
    
    def _calculate_most_improved(
        self,
        year: int,
        database: Database,
        universe_state
    ) -> Optional[Award]:
        """
        Most Improved - Wrestler who showed the biggest improvement.
        Criteria: Popularity gain, momentum gain, performance improvement
        """
        
        # This would require tracking stats changes over time
        # For now, we'll base it on current year vs debut performance
        
        cursor = database.conn.cursor()
        
        # Get wrestlers who have competed in both this year and previous year
        if year == 1:
            return None  # Can't calculate improvement in first year
        
        cursor.execute('''
            SELECT DISTINCT wrestler_id FROM (
                SELECT json_each.value as wrestler_id
                FROM match_history, json_each(side_a_ids)
                WHERE year = ?
                UNION
                SELECT json_each.value as wrestler_id
                FROM match_history, json_each(side_b_ids)
                WHERE year = ?
            )
        ''', (year, year))
        
        current_year_wrestlers = {row[0] for row in cursor.fetchall()}
        
        cursor.execute('''
            SELECT DISTINCT wrestler_id FROM (
                SELECT json_each.value as wrestler_id
                FROM match_history, json_each(side_a_ids)
                WHERE year = ?
                UNION
                SELECT json_each.value as wrestler_id
                FROM match_history, json_each(side_b_ids)
                WHERE year = ?
            )
        ''', (year - 1, year - 1))
        
        previous_year_wrestlers = {row[0] for row in cursor.fetchall()}
        
        # Wrestlers in both years
        eligible_wrestlers = current_year_wrestlers & previous_year_wrestlers
        
        if not eligible_wrestlers:
            return None
        
        nominees_data = []
        
        for wrestler_id in eligible_wrestlers:
            wrestler = universe_state.get_wrestler_by_id(wrestler_id)
            if not wrestler:
                continue
            
            # Get previous year avg rating
            cursor.execute('''
                SELECT AVG(star_rating), COUNT(*)
                FROM match_history
                WHERE (side_a_ids LIKE ? OR side_b_ids LIKE ?)
                  AND year = ?
            ''', (f'%{wrestler_id}%', f'%{wrestler_id}%', year - 1))
            
            prev_stats = cursor.fetchone()
            prev_rating = prev_stats[0] or 0
            prev_matches = prev_stats[1]
            
            # Get current year avg rating
            cursor.execute('''
                SELECT AVG(star_rating), COUNT(*)
                FROM match_history
                WHERE (side_a_ids LIKE ? OR side_b_ids LIKE ?)
                  AND year = ?
            ''', (f'%{wrestler_id}%', f'%{wrestler_id}%', year))
            
            curr_stats = cursor.fetchone()
            curr_rating = curr_stats[0] or 0
            curr_matches = curr_stats[1]
            
            if prev_matches < 5 or curr_matches < 5:
                continue
            
            # Calculate improvement
            rating_improvement = curr_rating - prev_rating
            
            # Must show actual improvement
            if rating_improvement <= 0:
                continue
            
            score = rating_improvement * 100
            score += wrestler.popularity * 0.3  # Current popularity
            score += wrestler.momentum * 0.2
            
            nominees_data.append({
                'wrestler_id': wrestler_id,
                'wrestler_name': wrestler.name,
                'score': score,
                'stats': {
                    'prev_rating': round(prev_rating, 2),
                    'curr_rating': round(curr_rating, 2),
                    'improvement': round(rating_improvement, 2),
                    'matches': curr_matches
                }
            })
        
        nominees_data.sort(key=lambda x: x['score'], reverse=True)
        nominees_data = nominees_data[:5]
        
        if not nominees_data:
            return None
        
        nominees = []
        for data in nominees_data:
            reason = f"Improved from {data['stats']['prev_rating']}⭐ to {data['stats']['curr_rating']}⭐ (+{data['stats']['improvement']})"
            
            nominee = AwardNominee(
                nominee_id=data['wrestler_id'],
                nominee_name=data['wrestler_name'],
                nominee_type='wrestler',
                stats=data['stats'],
                reason=reason,
                score=data['score']
            )
            nominees.append(nominee)
        
        winner = nominees_data[0]
        
        return Award(
            category=AwardCategory.MOST_IMPROVED,
            year=year,
            nominees=nominees,
            winner_id=winner['wrestler_id'],
            winner_name=winner['wrestler_name']
        )
    
    def _calculate_comeback_of_the_year(
        self,
        year: int,
        database: Database,
        universe_state
    ) -> Optional[Award]:
        """
        Comeback of the Year - Wrestler who returned from retirement/injury.
        Criteria: Impact after return
        """
        
        # This would track wrestlers who returned from injury/retirement
        # For now, we'll skip this if no tracking is available
        
        return None  # Placeholder
    
    # ========================================================================
    # MATCH AWARDS
    # ========================================================================
    
    def _calculate_match_of_the_year(
        self,
        year: int,
        database: Database
    ) -> Optional[Award]:
        """
        Match of the Year - Highest rated match.
        Criteria: Star rating, importance
        """
        
        cursor = database.conn.cursor()
        
        # Get top 5 matches by star rating
        cursor.execute('''
            SELECT 
                match_id,
                show_name,
                side_a_names,
                side_b_names,
                star_rating,
                is_title_match,
                duration_minutes,
                week
            FROM match_history
            WHERE year = ?
            ORDER BY star_rating DESC, duration_minutes DESC
            LIMIT 5
        ''', (year,))
        
        matches = cursor.fetchall()
        
        if not matches:
            return None
        
        nominees = []
        
        for match in matches:
            match_id, show_name, side_a_json, side_b_json, star_rating, is_title, duration, week = match
            
            side_a_names = json.loads(side_a_json)
            side_b_names = json.loads(side_b_json)
            
            participants = ' & '.join(side_a_names) + ' vs ' + ' & '.join(side_b_names)
            
            reason = f"{star_rating}⭐ on {show_name}"
            if is_title:
                reason += " (Title Match)"
            
            nominee = AwardNominee(
                nominee_id=match_id,
                nominee_name=participants,
                nominee_type='match',
                stats={
                    'star_rating': star_rating,
                    'show_name': show_name,
                    'is_title_match': bool(is_title),
                    'duration': duration,
                    'week': week
                },
                reason=reason,
                score=star_rating
            )
            nominees.append(nominee)
        
        # Winner is highest rated
        winner_match = matches[0]
        winner_side_a = json.loads(winner_match[2])
        winner_side_b = json.loads(winner_match[3])
        winner_name = ' & '.join(winner_side_a) + ' vs ' + ' & '.join(winner_side_b)
        
        return Award(
            category=AwardCategory.MATCH_OF_THE_YEAR,
            year=year,
            nominees=nominees,
            winner_id=winner_match[0],
            winner_name=winner_name
        )
    
    def _calculate_feud_of_the_year(
        self,
        year: int,
        database: Database,
        universe_state
    ) -> Optional[Award]:
        """
        Feud of the Year - Best feud/rivalry.
        Criteria: Match quality, intensity, storyline progression
        """
        
        cursor = database.conn.cursor()
        
        # Get feuds that were active this year
        cursor.execute('''
            SELECT 
                id,
                participant_names,
                intensity,
                match_count
            FROM feuds
            WHERE start_year <= ?
              AND (status != 'resolved' OR start_year = ?)
            ORDER BY intensity DESC, match_count DESC
            LIMIT 5
        ''', (year, year))
        
        feuds = cursor.fetchall()
        
        if not feuds:
            return None
        
        nominees = []
        
        for feud_row in feuds:
            feud_id, participant_names_json, intensity, match_count = feud_row
            
            participant_names = json.loads(participant_names_json)
            feud_name = ' vs '.join(participant_names)
            
            reason = f"Intensity: {intensity}, {match_count} matches"
            
            nominee = AwardNominee(
                nominee_id=feud_id,
                nominee_name=feud_name,
                nominee_type='feud',
                stats={
                    'intensity': intensity,
                    'match_count': match_count
                },
                reason=reason,
                score=intensity + (match_count * 5)
            )
            nominees.append(nominee)
        
        # Sort by score
        nominees.sort(key=lambda x: x.score, reverse=True)
        
        # Winner is highest intensity + matches
        winner_feud = feuds[0]
        winner_names = json.loads(winner_feud[1])
        winner_name = ' vs '.join(winner_names)
        
        return Award(
            category=AwardCategory.FEUD_OF_THE_YEAR,
            year=year,
            nominees=nominees,
            winner_id=winner_feud[0],
            winner_name=winner_name
        )
    
    # ========================================================================
    # CHAMPIONSHIP AWARDS
    # ========================================================================
    
    def _calculate_champion_of_the_year(
        self,
        year: int,
        database: Database
    ) -> Optional[Award]:
        """
        Champion of the Year - Best title holder performance.
        Criteria: Title defenses, reign length, match quality as champion
        """
        
        cursor = database.conn.cursor()
        
        # Get wrestlers who held titles this year
        cursor.execute('''
            SELECT 
                wrestler_id,
                wrestler_name,
                COUNT(*) as reigns,
                SUM(days_held) as total_days,
                MAX(days_held) as longest_reign
            FROM title_reigns
            WHERE won_date_year = ?
               OR (won_date_year < ? AND (lost_date_year IS NULL OR lost_date_year >= ?))
            GROUP BY wrestler_id
            ORDER BY total_days DESC, reigns DESC
            LIMIT 5
        ''', (year, year, year))
        
        champions = cursor.fetchall()
        
        if not champions:
            return None
        
        nominees = []
        
        for champ in champions:
            wrestler_id, wrestler_name, reigns, total_days, longest_reign = champ
            
            # Get match quality as champion
            # (This would require tracking title match star ratings)
            
            score = total_days + (reigns * 50) + (longest_reign * 0.5)
            
            reason = f"{reigns} reign(s), {total_days} days as champion"
            
            nominee = AwardNominee(
                nominee_id=wrestler_id,
                nominee_name=wrestler_name,
                nominee_type='wrestler',
                stats={
                    'reigns': reigns,
                    'total_days': total_days,
                    'longest_reign': longest_reign
                },
                reason=reason,
                score=score
            )
            nominees.append(nominee)
        
        # Sort by score
        nominees.sort(key=lambda x: x.score, reverse=True)
        
        winner = champions[0]
        
        return Award(
            category=AwardCategory.CHAMPION_OF_THE_YEAR,
            year=year,
            nominees=nominees,
            winner_id=winner[0],
            winner_name=winner[1]
        )
    
    def _calculate_title_reign_of_the_year(
        self,
        year: int,
        database: Database
    ) -> Optional[Award]:
        """
        Title Reign of the Year - Single best title reign.
        Criteria: Length, defenses, prestige
        """
        
        cursor = database.conn.cursor()
        
        # Get all reigns that occurred during this year
        cursor.execute('''
            SELECT 
                tr.id,
                tr.wrestler_name,
                tr.days_held,
                c.name as title_name,
                c.prestige
            FROM title_reigns tr
            JOIN championships c ON tr.title_id = c.id
            WHERE tr.won_date_year = ?
               OR (tr.won_date_year < ? AND (tr.lost_date_year IS NULL OR tr.lost_date_year >= ?))
            ORDER BY (tr.days_held * c.prestige) DESC
            LIMIT 5
        ''', (year, year, year))
        
        reigns = cursor.fetchall()
        
        if not reigns:
            return None
        
        nominees = []
        
        for reign in reigns:
            reign_id, wrestler_name, days_held, title_name, prestige = reign
            
            score = days_held * (prestige / 50)
            
            reason = f"{title_name}, {days_held} days"
            
            nominee = AwardNominee(
                nominee_id=str(reign_id),
                nominee_name=f"{wrestler_name} ({title_name})",
                nominee_type='title_reign',
                stats={
                    'wrestler': wrestler_name,
                    'title': title_name,
                    'days_held': days_held,
                    'prestige': prestige
                },
                reason=reason,
                score=score
            )
            nominees.append(nominee)
        
        winner = reigns[0]
        
        return Award(
            category=AwardCategory.TITLE_REIGN_OF_THE_YEAR,
            year=year,
            nominees=nominees,
            winner_id=str(winner[0]),
            winner_name=f"{winner[1]} ({winner[3]})"
        )
    
        # ========================================================================
    # TAG TEAM AWARDS
    # ========================================================================
    
    def _calculate_tag_team_of_the_year(
        self,
        year: int,
        database: Database,
        universe_state
    ) -> Optional[Award]:
        """
        Tag Team of the Year - Best tag team performance.
        Criteria: Wins, chemistry, title reigns
        """
        
        # Get tag teams from database
        tag_teams = database.get_all_tag_teams(active_only=False)
        
        if not tag_teams:
            return None
        
        nominees_data = []
        cursor = database.conn.cursor()
        
        for team_dict in tag_teams:
            team_id = team_dict['team_id']
            team_name = team_dict['team_name']
            chemistry = team_dict['chemistry']
            team_wins = team_dict['team_wins']
            team_losses = team_dict['team_losses']
            title_reigns = team_dict['total_title_reigns']
            
            total_matches = team_wins + team_losses
            
            if total_matches < 3:  # Minimum matches
                continue
            
            # Score based on performance
            score = 0.0
            score += team_wins * 10
            score += chemistry * 0.5
            score += title_reigns * 30
            
            nominees_data.append({
                'team_id': team_id,
                'team_name': team_name,
                'score': score,
                'stats': {
                    'wins': team_wins,
                    'losses': team_losses,
                    'chemistry': chemistry,
                    'title_reigns': title_reigns
                }
            })
        
        nominees_data.sort(key=lambda x: x['score'], reverse=True)
        nominees_data = nominees_data[:5]
        
        if not nominees_data:
            return None
        
        nominees = []
        for data in nominees_data:
            reason = f"{data['stats']['wins']}-{data['stats']['losses']}, Chemistry: {data['stats']['chemistry']}"
            if data['stats']['title_reigns'] > 0:
                reason += f", {data['stats']['title_reigns']} title reign(s)"
            
            nominee = AwardNominee(
                nominee_id=data['team_id'],
                nominee_name=data['team_name'],
                nominee_type='tag_team',
                stats=data['stats'],
                reason=reason,
                score=data['score']
            )
            nominees.append(nominee)
        
        winner = nominees_data[0]
        
        return Award(
            category=AwardCategory.TAG_TEAM_OF_THE_YEAR,
            year=year,
            nominees=nominees,
            winner_id=winner['team_id'],
            winner_name=winner['team_name']
        )
    
    def _calculate_tag_match_of_the_year(
        self,
        year: int,
        database: Database
    ) -> Optional[Award]:
        """
        Tag Team Match of the Year - Best tag team match.
        Criteria: Star rating for tag matches
        """
        
        cursor = database.conn.cursor()
        
        # Get top tag team matches (4 wrestlers involved)
        cursor.execute('''
            SELECT 
                match_id,
                show_name,
                side_a_names,
                side_b_names,
                star_rating,
                week
            FROM match_history
            WHERE year = ?
              AND json_array_length(side_a_ids) >= 2
              AND json_array_length(side_b_ids) >= 2
            ORDER BY star_rating DESC
            LIMIT 5
        ''', (year,))
        
        matches = cursor.fetchall()
        
        if not matches:
            return None
        
        nominees = []
        
        for match in matches:
            match_id, show_name, side_a_json, side_b_json, star_rating, week = match
            
            side_a_names = json.loads(side_a_json)
            side_b_names = json.loads(side_b_json)
            
            participants = ' & '.join(side_a_names) + ' vs ' + ' & '.join(side_b_names)
            
            reason = f"{star_rating}⭐ on {show_name}"
            
            nominee = AwardNominee(
                nominee_id=match_id,
                nominee_name=participants,
                nominee_type='match',
                stats={
                    'star_rating': star_rating,
                    'show_name': show_name,
                    'week': week
                },
                reason=reason,
                score=star_rating
            )
            nominees.append(nominee)
        
        winner_match = matches[0]
        winner_side_a = json.loads(winner_match[2])
        winner_side_b = json.loads(winner_match[3])
        winner_name = ' & '.join(winner_side_a) + ' vs ' + ' & '.join(winner_side_b)
        
        return Award(
            category=AwardCategory.TAG_MATCH_OF_THE_YEAR,
            year=year,
            nominees=nominees,
            winner_id=winner_match[0],
            winner_name=winner_name
        )
    
    # ========================================================================
    # PERFORMANCE AWARDS
    # ========================================================================
    
    def _calculate_best_technical(
        self,
        year: int,
        database: Database,
        universe_state
    ) -> Optional[Award]:
        """
        Best Technical Wrestler - Highest technical attribute + performance.
        Criteria: Technical skill, submission wins
        """
        
        cursor = database.conn.cursor()
        
        # Get wrestlers with high technical skills who competed this year
        cursor.execute('''
            SELECT DISTINCT wrestler_id FROM (
                SELECT json_each.value as wrestler_id
                FROM match_history, json_each(side_a_ids)
                WHERE year = ?
                UNION
                SELECT json_each.value as wrestler_id
                FROM match_history, json_each(side_b_ids)
                WHERE year = ?
            )
        ''', (year, year))
        
        wrestler_ids = [row[0] for row in cursor.fetchall()]
        
        nominees_data = []
        
        for wrestler_id in wrestler_ids:
            wrestler = universe_state.get_wrestler_by_id(wrestler_id)
            if not wrestler or wrestler.is_retired:
                continue
            
            # Get submission wins
            cursor.execute('''
                SELECT COUNT(*)
                FROM match_history
                WHERE (side_a_ids LIKE ? AND winner = 'side_a' AND finish_type = 'submission')
                   OR (side_b_ids LIKE ? AND winner = 'side_b' AND finish_type = 'submission')
                   AND year = ?
            ''', (f'%{wrestler_id}%', f'%{wrestler_id}%', year))
            
            submission_wins = cursor.fetchone()[0]
            
            # Score based on technical skill and submissions
            score = wrestler.technical + (submission_wins * 10)
            
            if score < 60:  # Minimum threshold
                continue
            
            nominees_data.append({
                'wrestler_id': wrestler_id,
                'wrestler_name': wrestler.name,
                'score': score,
                'stats': {
                    'technical': wrestler.technical,
                    'submission_wins': submission_wins
                }
            })
        
        nominees_data.sort(key=lambda x: x['score'], reverse=True)
        nominees_data = nominees_data[:5]
        
        if not nominees_data:
            return None
        
        nominees = []
        for data in nominees_data:
            reason = f"Technical: {data['stats']['technical']}"
            if data['stats']['submission_wins'] > 0:
                reason += f", {data['stats']['submission_wins']} submission wins"
            
            nominee = AwardNominee(
                nominee_id=data['wrestler_id'],
                nominee_name=data['wrestler_name'],
                nominee_type='wrestler',
                stats=data['stats'],
                reason=reason,
                score=data['score']
            )
            nominees.append(nominee)
        
        winner = nominees_data[0]
        
        return Award(
            category=AwardCategory.BEST_TECHNICAL_WRESTLER,
            year=year,
            nominees=nominees,
            winner_id=winner['wrestler_id'],
            winner_name=winner['wrestler_name']
        )
    
    def _calculate_best_high_flyer(
        self,
        year: int,
        database: Database,
        universe_state
    ) -> Optional[Award]:
        """
        Best High-Flyer - Highest speed attribute + performance.
        Criteria: Speed skill, exciting matches
        """
        
        cursor = database.conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT wrestler_id FROM (
                SELECT json_each.value as wrestler_id
                FROM match_history, json_each(side_a_ids)
                WHERE year = ?
                UNION
                SELECT json_each.value as wrestler_id
                FROM match_history, json_each(side_b_ids)
                WHERE year = ?
            )
        ''', (year, year))
        
        wrestler_ids = [row[0] for row in cursor.fetchall()]
        
        nominees_data = []
        
        for wrestler_id in wrestler_ids:
            wrestler = universe_state.get_wrestler_by_id(wrestler_id)
            if not wrestler or wrestler.is_retired:
                continue
            
            # Get average match rating
            cursor.execute('''
                SELECT AVG(star_rating), COUNT(*)
                FROM match_history
                WHERE (side_a_ids LIKE ? OR side_b_ids LIKE ?)
                  AND year = ?
            ''', (f'%{wrestler_id}%', f'%{wrestler_id}%', year))
            
            avg_rating, match_count = cursor.fetchone()
            
            if match_count < 5:
                continue
            
            # Score based on speed and match quality
            score = wrestler.speed + ((avg_rating or 0) * 10)
            
            if score < 70:  # Minimum threshold
                continue
            
            nominees_data.append({
                'wrestler_id': wrestler_id,
                'wrestler_name': wrestler.name,
                'score': score,
                'stats': {
                    'speed': wrestler.speed,
                    'avg_rating': round(avg_rating or 0, 2),
                    'matches': match_count
                }
            })
        
        nominees_data.sort(key=lambda x: x['score'], reverse=True)
        nominees_data = nominees_data[:5]
        
        if not nominees_data:
            return None
        
        nominees = []
        for data in nominees_data:
            reason = f"Speed: {data['stats']['speed']}, {data['stats']['avg_rating']}⭐ avg"
            
            nominee = AwardNominee(
                nominee_id=data['wrestler_id'],
                nominee_name=data['wrestler_name'],
                nominee_type='wrestler',
                stats=data['stats'],
                reason=reason,
                score=data['score']
            )
            nominees.append(nominee)
        
        winner = nominees_data[0]
        
        return Award(
            category=AwardCategory.BEST_HIGH_FLYER,
            year=year,
            nominees=nominees,
            winner_id=winner['wrestler_id'],
            winner_name=winner['wrestler_name']
        )
    
    def _calculate_best_brawler(
        self,
        year: int,
        database: Database,
        universe_state
    ) -> Optional[Award]:
        """
        Best Brawler - Highest brawling attribute + performance.
        Criteria: Brawling skill, hard-hitting matches
        """
        
        cursor = database.conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT wrestler_id FROM (
                SELECT json_each.value as wrestler_id
                FROM match_history, json_each(side_a_ids)
                WHERE year = ?
                UNION
                SELECT json_each.value as wrestler_id
                FROM match_history, json_each(side_b_ids)
                WHERE year = ?
            )
        ''', (year, year))
        
        wrestler_ids = [row[0] for row in cursor.fetchall()]
        
        nominees_data = []
        
        for wrestler_id in wrestler_ids:
            wrestler = universe_state.get_wrestler_by_id(wrestler_id)
            if not wrestler or wrestler.is_retired:
                continue
            
            # Get total wins
            cursor.execute('''
                SELECT COUNT(*)
                FROM match_history
                WHERE ((side_a_ids LIKE ? AND winner = 'side_a')
                   OR (side_b_ids LIKE ? AND winner = 'side_b'))
                  AND year = ?
            ''', (f'%{wrestler_id}%', f'%{wrestler_id}%', year))
            
            wins = cursor.fetchone()[0]
            
            # Score based on brawling and wins
            score = wrestler.brawling + (wins * 5)
            
            if score < 70:  # Minimum threshold
                continue
            
            nominees_data.append({
                'wrestler_id': wrestler_id,
                'wrestler_name': wrestler.name,
                'score': score,
                'stats': {
                    'brawling': wrestler.brawling,
                    'wins': wins
                }
            })
        
        nominees_data.sort(key=lambda x: x['score'], reverse=True)
        nominees_data = nominees_data[:5]
        
        if not nominees_data:
            return None
        
        nominees = []
        for data in nominees_data:
            reason = f"Brawling: {data['stats']['brawling']}, {data['stats']['wins']} wins"
            
            nominee = AwardNominee(
                nominee_id=data['wrestler_id'],
                nominee_name=data['wrestler_name'],
                nominee_type='wrestler',
                stats=data['stats'],
                reason=reason,
                score=data['score']
            )
            nominees.append(nominee)
        
        winner = nominees_data[0]
        
        return Award(
            category=AwardCategory.BEST_BRAWLER,
            year=year,
            nominees=nominees,
            winner_id=winner['wrestler_id'],
            winner_name=winner['wrestler_name']
        )
    
    # ========================================================================
    # MICROPHONE AWARDS
    # ========================================================================
    
    def _calculate_best_on_mic(
        self,
        year: int,
        database: Database,
        universe_state
    ) -> Optional[Award]:
        """
        Best on the Mic - Highest mic skill + segment performance.
        Criteria: Mic skill, promo segment ratings
        """
        
        cursor = database.conn.cursor()
        
        # Get all wrestlers
        wrestlers = universe_state.get_active_wrestlers()
        
        nominees_data = []
        
        for wrestler in wrestlers:
            if wrestler.is_retired:
                continue
            
            # Score based on mic skill and popularity
            score = wrestler.mic + (wrestler.popularity * 0.3)
            
            if score < 60:  # Minimum threshold
                continue
            
            nominees_data.append({
                'wrestler_id': wrestler.id,
                'wrestler_name': wrestler.name,
                'score': score,
                'stats': {
                    'mic': wrestler.mic,
                    'popularity': wrestler.popularity
                }
            })
        
        nominees_data.sort(key=lambda x: x['score'], reverse=True)
        nominees_data = nominees_data[:5]
        
        if not nominees_data:
            return None
        
        nominees = []
        for data in nominees_data:
            reason = f"Mic Skill: {data['stats']['mic']}, Popularity: {data['stats']['popularity']}"
            
            nominee = AwardNominee(
                nominee_id=data['wrestler_id'],
                nominee_name=data['wrestler_name'],
                nominee_type='wrestler',
                stats=data['stats'],
                reason=reason,
                score=data['score']
            )
            nominees.append(nominee)
        
        winner = nominees_data[0]
        
        return Award(
            category=AwardCategory.BEST_ON_THE_MIC,
            year=year,
            nominees=nominees,
            winner_id=winner['wrestler_id'],
            winner_name=winner['wrestler_name']
        )
    
    # ========================================================================
    # SHOW AWARDS
    # ========================================================================
    
    def _calculate_show_of_the_year(
        self,
        year: int,
        database: Database
    ) -> Optional[Award]:
        """
        Show of the Year - Best overall show.
        Criteria: Overall rating, attendance
        """
        
        cursor = database.conn.cursor()
        
        # Get top 5 shows by rating
        cursor.execute('''
            SELECT 
                show_id,
                show_name,
                overall_rating,
                total_attendance,
                week,
                brand
            FROM show_history
            WHERE year = ?
            ORDER BY overall_rating DESC, total_attendance DESC
            LIMIT 5
        ''', (year,))
        
        shows = cursor.fetchall()
        
        if not shows:
            return None
        
        nominees = []
        
        for show in shows:
            show_id, show_name, rating, attendance, week, brand = show
            
            reason = f"{rating:.2f}⭐, {attendance:,} attendance, Week {week}"
            
            nominee = AwardNominee(
                nominee_id=show_id,
                nominee_name=show_name,
                nominee_type='show',
                stats={
                    'rating': rating,
                    'attendance': attendance,
                    'week': week,
                    'brand': brand
                },
                reason=reason,
                score=rating * 10 + (attendance / 1000)
            )
            nominees.append(nominee)
        
        winner = shows[0]
        
        return Award(
            category=AwardCategory.SHOW_OF_THE_YEAR,
            year=year,
            nominees=nominees,
            winner_id=winner[0],
            winner_name=winner[1]
        )
    
    def _calculate_best_brand(
        self,
        year: int,
        database: Database
    ) -> Optional[Award]:
        """
        Brand of the Year - Best performing brand.
        Criteria: Average show rating, total attendance
        """
        
        cursor = database.conn.cursor()
        
        brands = ['ROC Alpha', 'ROC Velocity', 'ROC Vanguard']
        nominees_data = []
        
        for brand in brands:
            # Get brand stats for the year
            cursor.execute('''
                SELECT 
                    COUNT(*) as show_count,
                    AVG(overall_rating) as avg_rating,
                    SUM(total_attendance) as total_attendance,
                    SUM(net_profit) as total_profit
                FROM show_history
                WHERE year = ?
                  AND brand = ?
            ''', (year, brand))
            
            stats = cursor.fetchone()
            show_count, avg_rating, total_attendance, total_profit = stats
            
            if show_count == 0:
                continue
            
            # Score based on quality and financials
            score = (avg_rating or 0) * 20 + (total_attendance or 0) / 1000 + (total_profit or 0) / 100000
            
            nominees_data.append({
                'brand': brand,
                'score': score,
                'stats': {
                    'show_count': show_count,
                    'avg_rating': round(avg_rating or 0, 2),
                    'total_attendance': total_attendance or 0,
                    'total_profit': total_profit or 0
                }
            })
        
        nominees_data.sort(key=lambda x: x['score'], reverse=True)
        
        if not nominees_data:
            return None
        
        nominees = []
        for data in nominees_data:
            reason = f"{data['stats']['avg_rating']}⭐ avg, ${data['stats']['total_profit']:,} profit"
            
            nominee = AwardNominee(
                nominee_id=data['brand'],
                nominee_name=data['brand'],
                nominee_type='brand',
                stats=data['stats'],
                reason=reason,
                score=data['score']
            )
            nominees.append(nominee)
        
        winner = nominees_data[0]
        
        return Award(
            category=AwardCategory.BEST_BRAND,
            year=year,
            nominees=nominees,
            winner_id=winner['brand'],
            winner_name=winner['brand']
        )


# Global awards engine instance
awards_engine = AwardsEngine()