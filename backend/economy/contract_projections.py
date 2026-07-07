"""
Contract Financial Projections
Generates multi-year financial forecasts based on current contracts,
expected escalators, and roster planning.
"""

from typing import Dict, Any, List
from models.wrestler import Wrestler
from economy.contracts import contract_manager


class ContractProjector:
    """
    Projects future contract costs and obligations.
    
    Useful for:
    - Budget planning
    - Identifying contract cliffs (mass expirations)
    - Forecasting salary cap issues
    - Planning extensions
    """
    
    def __init__(self):
        self.weeks_per_year = 52
        self.assumed_shows_per_week = 3
    
    def project_wrestler_cost(
        self,
        wrestler: Wrestler,
        years_ahead: int = 3
    ) -> Dict[str, Any]:
        """
        Project a single wrestler's cost over time.
        
        Args:
            wrestler: Wrestler object
            years_ahead: How many years to project
        
        Returns:
            Yearly breakdown of costs
        """
        projections = []
        current_salary = wrestler.contract.salary_per_show
        weeks_remaining = wrestler.contract.weeks_remaining
        
        for year in range(1, years_ahead + 1):
            year_weeks = min(weeks_remaining, self.weeks_per_year)
            
            if year_weeks <= 0:
                # Contract expired
                projections.append({
                    'year': year,
                    'weeks_under_contract': 0,
                    'base_cost': 0,
                    'escalator_potential': 0,
                    'total_cost': 0,
                    'status': 'expired'
                })
            else:
                base_cost = current_salary * year_weeks * self.assumed_shows_per_week
                
                # Estimate escalator potential (20% of base)
                escalator_potential = int(base_cost * 0.2)
                
                total_cost = base_cost + escalator_potential
                
                projections.append({
                    'year': year,
                    'weeks_under_contract': year_weeks,
                    'base_cost': base_cost,
                    'escalator_potential': escalator_potential,
                    'total_cost': total_cost,
                    'status': 'active'
                })
                
                weeks_remaining -= self.weeks_per_year
        
        return {
            'wrestler_id': wrestler.id,
            'wrestler_name': wrestler.name,
            'current_salary': current_salary,
            'projections': projections,
            'total_projected_cost': sum(p['total_cost'] for p in projections)
        }
    
    def project_roster_costs(
        self,
        wrestlers: List[Wrestler],
        years_ahead: int = 3
    ) -> Dict[str, Any]:
        """
        Project total roster costs.
        
        Returns:
            Year-by-year breakdown of total payroll
        """
        yearly_totals = {year: {
            'base_cost': 0,
            'escalator_potential': 0,
            'total_cost': 0,
            'active_contracts': 0,
            'expiring_contracts': 0
        } for year in range(1, years_ahead + 1)}
        
        wrestler_projections = []
        
        for wrestler in wrestlers:
            if wrestler.is_retired:
                continue
            
            projection = self.project_wrestler_cost(wrestler, years_ahead)
            wrestler_projections.append(projection)
            
            for year_data in projection['projections']:
                year = year_data['year']
                yearly_totals[year]['base_cost'] += year_data['base_cost']
                yearly_totals[year]['escalator_potential'] += year_data['escalator_potential']
                yearly_totals[year]['total_cost'] += year_data['total_cost']
                
                if year_data['status'] == 'active':
                    yearly_totals[year]['active_contracts'] += 1
                    
                    # Check if expiring this year
                    if year_data['weeks_under_contract'] < self.weeks_per_year:
                        yearly_totals[year]['expiring_contracts'] += 1
        
        return {
            'roster_size': len(wrestlers),
            'active_wrestlers': len([w for w in wrestlers if not w.is_retired]),
            'yearly_breakdown': yearly_totals,
            'wrestler_projections': wrestler_projections,
            'total_obligation': sum(yearly_totals[year]['total_cost'] for year in yearly_totals)
        }
    
    def identify_contract_cliffs(
        self,
        wrestlers: List[Wrestler],
        years_ahead: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Identify "contract cliffs" - periods where many contracts expire.
        
        Returns:
            List of cliff periods with wrestler details
        """
        expirations_by_year_week = {}
        
        for wrestler in wrestlers:
            if wrestler.is_retired:
                continue
            
            weeks_remaining = wrestler.contract.weeks_remaining
            
            if weeks_remaining <= 0 or weeks_remaining > years_ahead * self.weeks_per_year:
                continue
            
            # Calculate which year/week contract expires
            expiry_year = (weeks_remaining // self.weeks_per_year) + 1
            expiry_week = weeks_remaining % self.weeks_per_year
            
            key = (expiry_year, expiry_week)
            
            if key not in expirations_by_year_week:
                expirations_by_year_week[key] = []
            
            expirations_by_year_week[key].append({
                'wrestler_id': wrestler.id,
                'wrestler_name': wrestler.name,
                'current_salary': wrestler.contract.salary_per_show,
                'market_value': contract_manager.calculate_market_value(wrestler)
            })
        
        # Find cliffs (5+ contracts expiring within 4 weeks)
        cliffs = []
        
        for (year, week), wrestlers_list in expirations_by_year_week.items():
            if len(wrestlers_list) >= 5:
                total_salary_impact = sum(w['current_salary'] for w in wrestlers_list)
                
                cliffs.append({
                    'year': year,
                    'week': week,
                    'wrestler_count': len(wrestlers_list),
                    'total_salary_impact': total_salary_impact,
                    'wrestlers': wrestlers_list,
                    'severity': 'critical' if len(wrestlers_list) >= 10 else 'high'
                })
        
        return sorted(cliffs, key=lambda c: (c['year'], c['week']))
    
    def budget_scenario_analysis(
        self,
        wrestlers: List[Wrestler],
        annual_budget: int,
        years_ahead: int = 3
    ) -> Dict[str, Any]:
        """
        Analyze if current contracts fit within budget constraints.
        
        Args:
            wrestlers: List of wrestlers
            annual_budget: Annual payroll budget
            years_ahead: Years to project
        
        Returns:
            Budget vs actual analysis with recommendations
        """
        projection = self.project_roster_costs(wrestlers, years_ahead)
        
        scenarios = []
        
        for year, breakdown in projection['yearly_breakdown'].items():
            total_cost = breakdown['total_cost']
            budget_utilization = (total_cost / annual_budget * 100) if annual_budget > 0 else 0
            
            over_budget = total_cost > annual_budget
            shortfall = total_cost - annual_budget if over_budget else 0
            
            scenarios.append({
                'year': year,
                'projected_cost': total_cost,
                'budget': annual_budget,
                'utilization_percentage': round(budget_utilization, 1),
                'over_budget': over_budget,
                'shortfall': shortfall if over_budget else 0,
                'surplus': annual_budget - total_cost if not over_budget else 0,
                'active_contracts': breakdown['active_contracts'],
                'expiring_contracts': breakdown['expiring_contracts']
            })
        
        # Overall health assessment
        avg_utilization = sum(s['utilization_percentage'] for s in scenarios) / len(scenarios)
        
        if avg_utilization > 120:
            health = 'critical'
            recommendation = "Immediate action required: Payroll exceeds budget by >20%"
        elif avg_utilization > 100:
            health = 'concerning'
            recommendation = "Budget cuts or revenue increases needed"
        elif avg_utilization > 85:
            health = 'tight'
            recommendation = "Limited flexibility for new signings"
        elif avg_utilization > 70:
            health = 'healthy'
            recommendation = "Good balance with room for strategic signings"
        else:
            health = 'excellent'
            recommendation = "Significant budget flexibility available"
        
        return {
            'annual_budget': annual_budget,
            'years_analyzed': years_ahead,
            'scenarios': scenarios,
            'budget_health': health,
            'average_utilization': round(avg_utilization, 1),
            'recommendation': recommendation
        }


# Global projector instance
contract_projector = ContractProjector()