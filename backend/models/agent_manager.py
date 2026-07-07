"""
Agent Manager (STEP 118)
Manages agent representation across the free agent pool.
"""

from typing import List, Dict, Optional
from models.free_agent import FreeAgent, AgentType, AgentInfo, assign_agent_to_free_agent
import random


class AgentManager:
    """
    Manages agents representing free agents.
    
    Responsibilities:
    - Assign agents to free agents
    - Create package deals
    - Track agent rosters
    - Handle agent-specific negotiations
    """
    
    def __init__(self):
        self.agents: Dict[str, Dict] = {}  # agent_name -> agent profile
        self.package_dealers: Dict[str, List[str]] = {}  # agent_name -> list of client IDs
    
    def assign_agents_to_pool(self, free_agents: List[FreeAgent]):
        """Assign agents to all free agents in the pool"""
        for fa in free_agents:
            if fa.agent.agent_type == AgentType.NONE:
                # Assign agent based on profile
                fa.agent = assign_agent_to_free_agent(fa)
            
                # Track agent
                if fa.agent.agent_type != AgentType.NONE:
                    self._register_agent(fa.agent, fa.id)
            else:
                # Re-register existing agents to populate tracking
                if fa.agent.agent_type != AgentType.NONE:
                    self._register_agent(fa.agent, fa.id)
    
    def _register_agent(self, agent: AgentInfo, client_id: str):
        """Register an agent in the tracking system"""
        agent_name = agent.agent_name
    
        if agent_name not in self.agents:
            self.agents[agent_name] = {
                'name': agent_name,
                'type': agent.agent_type.value,
                'clients': [],
                'commission_rate': agent.commission_rate,
                'negotiation_difficulty': agent.negotiation_difficulty
            }
    
        # Add client
        if client_id not in self.agents[agent_name]['clients']:
            self.agents[agent_name]['clients'].append(client_id)
    
        # Track package dealers
        if agent.agent_type == AgentType.PACKAGE_DEALER:
            if agent_name not in self.package_dealers:
                self.package_dealers[agent_name] = []
            if client_id not in self.package_dealers[agent_name]:
                self.package_dealers[agent_name].append(client_id)
    
    def create_package_deal(
        self,
        free_agents: List[FreeAgent],
        min_clients: int = 2,
        max_clients: int = 4
    ) -> Optional[str]:
        """
        Create a package deal by having one agent represent multiple free agents.
        
        Returns agent_name if successful, None otherwise.
        """
        # Filter available free agents without agents
        available = [fa for fa in free_agents if fa.agent.agent_type == AgentType.NONE]
        
        if len(available) < min_clients:
            return None
        
        # Select random clients for package
        package_size = random.randint(min_clients, min(max_clients, len(available)))
        package_clients = random.sample(available, package_size)
        
        # Create package dealer agent
        from models.free_agent import generate_agent_name, AgentType, AgentInfo
        
        agent_name = generate_agent_name()
        commission_rate = random.uniform(0.10, 0.15)
        difficulty = random.randint(60, 75)
        
        client_ids = [fa.id for fa in package_clients]
        
        # Assign to all clients
        for fa in package_clients:
            fa.agent = AgentInfo(
                agent_type=AgentType.PACKAGE_DEALER,
                agent_name=agent_name,
                commission_rate=commission_rate,
                other_clients=[cid for cid in client_ids if cid != fa.id],
                negotiation_difficulty=difficulty
            )
            
            self._register_agent(fa.agent, fa.id)
        
        print(f"📦 Package Deal Created: {agent_name} now represents {len(package_clients)} clients")
        
        return agent_name
    
    def get_package_deal_info(self, agent_name: str, free_agents: List[FreeAgent]) -> Optional[Dict]:
        """Get information about a package deal"""
        if agent_name not in self.package_dealers:
            return None
        
        client_ids = self.package_dealers[agent_name]
        clients = [fa for fa in free_agents if fa.id in client_ids]
        
        if not clients:
            return None
        
        total_value = sum(fa.market_value for fa in clients)
        
        return {
            'agent_name': agent_name,
            'client_count': len(clients),
            'clients': [
                {
                    'id': fa.id,
                    'name': fa.wrestler_name,
                    'role': fa.role,
                    'market_value': fa.market_value,
                    'asking_salary': fa.demands.asking_salary
                }
                for fa in clients
            ],
            'total_package_value': total_value,
            'total_asking_salary': sum(fa.demands.asking_salary for fa in clients),
            'package_discount_eligible': len(clients) >= 3  # 10% discount for 3+ clients
        }
    
    def get_agent_roster(self, agent_name: str) -> Optional[Dict]:
        """Get full roster for an agent"""
        return self.agents.get(agent_name)
    
    def get_all_agents(self) -> List[Dict]:
        """Get list of all agents"""
        return list(self.agents.values())
    
    def get_package_dealers(self) -> Dict[str, List[str]]:
        """Get all package dealers and their clients"""
        return self.package_dealers.copy()