"""
Role Classifier v2.2
Strict rule-based role detection with realistic team compositions.

Roles:
- Entry = takes first fights with success
- AWPer = primary AWP user
- Support = utility focused (flashes OR blinds)
- Lurker = plays alone (>800u avg distance)
- Rotator = mid-distance, trades often (600-800u)
- Trader = close-mid distance, trades (250-600u)
- SiteAnchor = holds site, minimal movement (<250u)
"""

from typing import Dict, Any, List, Tuple

# Role quotas per team
MAX_AWPERS_PER_TEAM = 1
MAX_ENTRIES_PER_TEAM = 2

class RoleClassifier:
    """
    Assigns roles based on deterministic player stats.
    
    v2.2 IMPROVEMENTS:
    1. Split Anchor into SiteAnchor (<250u) and Trader (250-600u)
    2. Support: flashes > team_avg OR enemies_blinded > 3
    3. Entry scoring includes traded_after_death consideration
    """
    
    def classify_roles(self, players: Dict[str, Any]) -> Dict[str, str]:
        """
        Assigns a role to each player ID based on features.
        """
        results = {}
        
        count = len(players)
        if count == 0: 
            return {}
        
        # Calculate team averages
        total_flashes = sum(p.flashes_thrown for p in players.values())
        avg_flashes = total_flashes / count
        
        total_blinds = sum(p.enemies_blinded for p in players.values())
        avg_blinds = total_blinds / count
        
        # Get entry thresholds - top 4 by entry_attempts
        entry_data = [(pid, p.entry_kills + p.entry_deaths) for pid, p in players.items()]
        entry_data.sort(key=lambda x: x[1], reverse=True)
        top_entry_pids = set(pid for pid, _ in entry_data[:4])
        
        # PHASE 1: Initial role assignment
        role_candidates: Dict[str, Tuple[str, float]] = {}
        
        for pid, p in players.items():
            role = "SiteAnchor"  # Default: site holder
            score = 0.0
            
            total_kills = max(1, p.kills)
            awp_ratio = p.awp_kills / total_kills
            
            entry_attempts = p.entry_kills + p.entry_deaths
            entry_success_rate = p.entry_kills / max(1, entry_attempts)
            
            # Trade involvement
            tradeable_ratio = p.tradeable_deaths / max(1, p.deaths)
            
            # Logic Hierarchy (Strict Priority)
            
            # 1. AWPer - clear weapon identity 
            if awp_ratio >= 0.25 and p.awp_kills >= 2:
                role = "AWPer"
                score = p.awp_kills * awp_ratio
                
            # 2. Entry - volume + success + trade context
            elif pid in top_entry_pids and entry_attempts >= 3:
                if entry_success_rate >= 0.25 or p.entry_kills >= 2:
                    role = "Entry"
                    # Quality score: success + tradeable + flash support potential
                    score = (entry_success_rate * p.entry_kills * 2) + (tradeable_ratio * 3)
                else:
                    role = "SiteAnchor"
                    score = 0
                    
            # 3. Support - utility focused (RELAXED: OR logic)
            elif p.flashes_thrown > avg_flashes or p.enemies_blinded > 3:
                role = "Support"
                score = p.flashes_thrown + (p.enemies_blinded * 2)
                
            # 4. Lurker - plays completely alone
            elif p.avg_teammate_dist > 800:
                role = "Lurker"
                score = p.avg_teammate_dist
            
            # 5. Rotator - far-mid distance (600-800u)
            elif 600 < p.avg_teammate_dist <= 800:
                role = "Rotator"
                score = tradeable_ratio * p.avg_teammate_dist
            
            # 6. Trader - mid-distance, trades often (250-600u)
            elif 250 < p.avg_teammate_dist <= 600 and tradeable_ratio >= 0.3:
                role = "Trader"
                score = tradeable_ratio * 100
                
            # 7. SiteAnchor - holds site, low movement (<250u)
            else:
                role = "SiteAnchor"
                score = 0
                
            role_candidates[pid] = (role, score)
        
        # PHASE 2: Enforce per-team quotas
        all_pids = list(players.keys())
        team_size = len(all_pids) // 2
        
        team1_pids = set(all_pids[:team_size])
        team2_pids = set(all_pids[team_size:])
        
        def apply_quota_per_team(role_name: str, max_per_team: int, team_pids: set):
            """Demote excess role holders."""
            candidates = [(pid, score) for pid, (role, score) in role_candidates.items() 
                         if role == role_name and pid in team_pids]
            
            if len(candidates) <= max_per_team:
                return
            
            candidates.sort(key=lambda x: x[1], reverse=True)
            
            for pid, _ in candidates[max_per_team:]:
                role_candidates[pid] = ("Trader", 0)  # Demote to Trader
        
        # Apply quotas
        apply_quota_per_team("AWPer", MAX_AWPERS_PER_TEAM, team1_pids)
        apply_quota_per_team("AWPer", MAX_AWPERS_PER_TEAM, team2_pids)
        apply_quota_per_team("Entry", MAX_ENTRIES_PER_TEAM, team1_pids)
        apply_quota_per_team("Entry", MAX_ENTRIES_PER_TEAM, team2_pids)
        
        # Extract final roles
        for pid, (role, _) in role_candidates.items():
            results[pid] = role
            
        return results
