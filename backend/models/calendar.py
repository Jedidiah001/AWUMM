"""
Calendar System
Manages the in-game calendar with weekly shows and PPV/PLE events.
Generates shows infinitely based on a 52-week year cycle.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class ScheduledShow:
    """Represents a single scheduled show"""
    show_id: str
    year: int
    week: int
    day_of_week: str  # 'Monday', 'Friday', 'Saturday', 'Sunday'
    brand: str  # 'ROC Alpha', 'ROC Velocity', 'ROC Vanguard', 'Cross-Brand'
    name: str  # e.g., 'ROC Alpha Weekly', 'Victory Dome', etc.
    show_type: str  # 'weekly_tv', 'minor_ppv', 'major_ppv', 'ple'
    is_ppv: bool
    tier: str  # 'weekly', 'minor', 'major'
    location: str = ''
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'show_id': self.show_id,
            'year': self.year,
            'week': self.week,
            'day_of_week': self.day_of_week,
            'brand': self.brand,
            'name': self.name,
            'show_type': self.show_type,
            'is_ppv': self.is_ppv,
            'tier': self.tier,
            'location': self.location
        }


class Calendar:
    """
    Manages the in-game calendar system.
    
    Weekly Schedule (every week):
    - Monday: ROC Alpha Weekly
    - Friday: ROC Velocity Weekly
    - Saturday: ROC Vanguard Weekly
    
    PPV/PLE Events (specific weeks each year):
    1. Rumble Royale - Week 4 (January)
    2. Clash of Titans - Week 12 (March)
    3. Overdrive - Week 20 (May)
    4. Champions' Ascent - Week 24 (June)
    5. Summer Slamfest - Week 32 (August)
    6. Autumn Annihilation - Week 40 (October)
    7. Night of Glory - Week 44 (November)
    8. Elimination Chamber - Week 48 (December)
    9. LegacyMania Night 1 - Week 51 (December)
    10. LegacyMania Night 2 - Week 52 (December)
    """
    
    # PPV/PLE Configuration
    PPV_SCHEDULE = [
        {
            'week': 4,
            'name': 'Rumble Royale',
            'brand': 'Cross-Brand',
            'tier': 'major',
            'description': 'Royal Rumble-style battle royal kickoff',
            'replaces_show': 'ROC Velocity'  # Takes Friday slot
        },
        {
            'week': 12,
            'name': 'Clash of Titans',
            'brand': 'Cross-Brand',
            'tier': 'minor',
            'description': 'Big singles and multi-man matches',
            'replaces_show': 'ROC Velocity'
        },
        {
            'week': 20,
            'name': 'Overdrive',
            'brand': 'ROC Velocity',
            'tier': 'minor',
            'description': 'High-speed, high-action PPV for Velocity',
            'replaces_show': 'ROC Velocity'
        },
        {
            'week': 24,
            'name': 'Champions\' Ascent',
            'brand': 'Cross-Brand',
            'tier': 'minor',
            'description': 'Title-focused PPV with multiple championship matches',
            'replaces_show': 'ROC Alpha'  # Takes Monday slot
        },
        {
            'week': 32,
            'name': 'Summer Slamfest',
            'brand': 'Cross-Brand',
            'tier': 'major',
            'description': 'Summer blockbuster event (SummerSlam equivalent)',
            'replaces_show': 'ROC Velocity'
        },
        {
            'week': 40,
            'name': 'Autumn Annihilation',
            'brand': 'Cross-Brand',
            'tier': 'major',
            'description': 'Grudge matches and storyline conclusions',
            'replaces_show': 'ROC Velocity'
        },
        {
            'week': 44,
            'name': 'Night of Glory',
            'brand': 'Cross-Brand',
            'tier': 'major',
            'description': 'Major PLE event with brand-specific showcases',
            'replaces_show': 'ROC Alpha'
        },
        {
            'week': 48,
            'name': 'Elimination Chamber',
            'brand': 'Cross-Brand',
            'tier': 'major',
            'description': 'Six-person chamber wars to shape the LegacyMania world-title scene',
            'replaces_show': 'ROC Velocity'
        },
        {
            'week': 51,
            'name': 'LegacyMania Night 1',
            'brand': 'Cross-Brand',
            'tier': 'major',
            'description': 'LegacyMania two-night spectacular begins',
            'replaces_show': 'ROC Velocity'
        },
        {
            'week': 52,
            'name': 'LegacyMania Night 2',
            'brand': 'Cross-Brand',
            'tier': 'major',
            'description': 'LegacyMania climax with world title main events',
            'replaces_show': 'ROC Vanguard'
        }
    ]
    
    def __init__(self):
        self.current_show_index = 0  # Tracks which show we're on
        self.generated_shows: List[ScheduledShow] = []
        self._generate_initial_shows(num_weeks=104)  # Generate 2 years ahead
    
    def _generate_initial_shows(self, num_weeks: int):
        """Generate shows for the next N weeks"""
        for week_offset in range(num_weeks):
            year = 1 + (week_offset // 52)
            week = (week_offset % 52) + 1
            
            self._generate_week_shows(year, week)
    
    def _generate_week_shows(self, year: int, week: int):
        """Generate all shows for a specific week"""
        # Check if this week has a PPV/PLE
        ppv_config = self._get_ppv_for_week(week)
        
        if ppv_config:
            # This week has a PPV - it replaces one of the weekly shows
            self._add_ppv_show(year, week, ppv_config)
            
            # Add the other two weekly shows that aren't replaced
            if ppv_config['replaces_show'] != 'ROC Alpha':
                self._add_weekly_show(year, week, 'Monday', 'ROC Alpha')
            if ppv_config['replaces_show'] != 'ROC Velocity':
                self._add_weekly_show(year, week, 'Friday', 'ROC Velocity')
            if ppv_config['replaces_show'] != 'ROC Vanguard':
                self._add_weekly_show(year, week, 'Saturday', 'ROC Vanguard')
        else:
            # Normal week - all three weekly shows
            self._add_weekly_show(year, week, 'Monday', 'ROC Alpha')
            self._add_weekly_show(year, week, 'Friday', 'ROC Velocity')
            self._add_weekly_show(year, week, 'Saturday', 'ROC Vanguard')
    
    def _get_ppv_for_week(self, week: int) -> Optional[Dict[str, Any]]:
        """Check if given week has a PPV/PLE"""
        for ppv in self.PPV_SCHEDULE:
            if ppv['week'] == week:
                return ppv
        return None
    
    def _add_weekly_show(self, year: int, week: int, day: str, brand: str):
        """Add a regular weekly TV show"""
        show_id = f"show_y{year}_w{week}_{brand.replace(' ', '_').lower()}"
        
        show = ScheduledShow(
            show_id=show_id,
            year=year,
            week=week,
            day_of_week=day,
            brand=brand,
            name=f"{brand} Weekly",
            show_type='weekly_tv',
            is_ppv=False,
            tier='weekly'
        )
        
        self.generated_shows.append(show)
    
    def _add_ppv_show(self, year: int, week: int, ppv_config: Dict[str, Any]):
        """Add a PPV/PLE event"""
        show_id = f"ppv_y{year}_w{week}_{ppv_config['name'].replace(' ', '_').lower()}"
        
        # Determine day based on what show it replaces
        day_map = {
            'ROC Alpha': 'Monday',
            'ROC Velocity': 'Friday',
            'ROC Vanguard': 'Saturday'
        }
        day = day_map.get(ppv_config['replaces_show'], 'Sunday')
        
        # Determine show type
        if ppv_config['tier'] == 'major':
            show_type = 'major_ppv'
        else:
            show_type = 'minor_ppv'
        
        show = ScheduledShow(
            show_id=show_id,
            year=year,
            week=week,
            day_of_week=day,
            brand=ppv_config['brand'],
            name=ppv_config['name'],
            show_type=show_type,
            is_ppv=True,
            tier=ppv_config['tier']
        )
        
        self.generated_shows.append(show)
    
    def get_current_show(self) -> Optional[ScheduledShow]:
        """Get the current show (the one we're about to book/simulate)"""
        if self.current_show_index < len(self.generated_shows):
            return self.generated_shows[self.current_show_index]
        
        # If we've run out, generate more shows
        self._extend_calendar(52)  # Generate another year
        return self.generated_shows[self.current_show_index] if self.current_show_index < len(self.generated_shows) else None
    
    def get_next_show(self) -> Optional[ScheduledShow]:
        """Get the show after the current one"""
        next_index = self.current_show_index + 1
        if next_index < len(self.generated_shows):
            return self.generated_shows[next_index]
        
        self._extend_calendar(52)
        return self.generated_shows[next_index] if next_index < len(self.generated_shows) else None
    
    def advance_to_next_show(self):
        """Move to the next show"""
        self.current_show_index += 1
        
        # If we're getting close to the end of generated shows, extend
        if self.current_show_index >= len(self.generated_shows) - 20:
            self._extend_calendar(52)
    
    def _extend_calendar(self, num_weeks: int):
        """Extend the calendar by generating more weeks"""
        if not self.generated_shows:
            start_year = 1
            start_week = 1
        else:
            last_show = self.generated_shows[-1]
            start_year = last_show.year
            start_week = last_show.week
        
        for week_offset in range(num_weeks):
            total_week = (start_year - 1) * 52 + start_week + week_offset
            year = 1 + ((total_week - 1) // 52)
            week = ((total_week - 1) % 52) + 1
            
            # Only generate if we haven't already
            existing = [s for s in self.generated_shows if s.year == year and s.week == week]
            if not existing:
                self._generate_week_shows(year, week)
    
    def get_upcoming_ppvs(self, count: int = 3) -> List[ScheduledShow]:
        """Get the next N PPV/PLE events from current position"""
        ppvs = []
        for i in range(self.current_show_index, len(self.generated_shows)):
            show = self.generated_shows[i]
            if show.is_ppv:
                ppvs.append(show)
                if len(ppvs) >= count:
                    break
        
        return ppvs
    
    def get_next_ppv(self) -> Optional[ScheduledShow]:
        """Get the very next PPV/PLE event"""
        upcoming = self.get_upcoming_ppvs(1)
        return upcoming[0] if upcoming else None
    
    def get_shows_until_ppv(self, ppv_name: str) -> int:
        """Count how many shows until a specific PPV"""
        for i in range(self.current_show_index, len(self.generated_shows)):
            show = self.generated_shows[i]
            if show.is_ppv and show.name == ppv_name:
                return i - self.current_show_index
        return -1
    
    def get_current_year_week(self) -> tuple:
        """Get current year and week"""
        current = self.get_current_show()
        if current:
            return (current.year, current.week)
        return (1, 1)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize calendar state"""
        current_show = self.get_current_show()
        next_show = self.get_next_show()
        next_ppv = self.get_next_ppv()
        
        return {
            'current_show_index': self.current_show_index,
            'current_year': current_show.year if current_show else 1,
            'current_week': current_show.week if current_show else 1,
            'total_shows_generated': len(self.generated_shows),
            'current_show': current_show.to_dict() if current_show else None,
            'next_show': next_show.to_dict() if next_show else None,
            'next_ppv': next_ppv.to_dict() if next_ppv else None,
            'upcoming_ppvs': [ppv.to_dict() for ppv in self.get_upcoming_ppvs(3)]
        }
    
    def __repr__(self):
        current = self.get_current_show()
        if current:
            return f"<Calendar Year {current.year}, Week {current.week} - {current.name}>"
        return "<Calendar - No shows scheduled>"
