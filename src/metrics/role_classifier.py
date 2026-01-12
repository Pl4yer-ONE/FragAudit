"""
Role Classifier
Strict rule-based role detection with per-team quotas.

Roles:
- Entry = takes first fights with success
- AWPer = primary AWP user
- Support = utility focused
- Lurker = plays alone (>800u avg distance)
- Rotator = mid-distance, trades often (NEW)
- Anchor = site holder, low movement (default)
"""

from typing import Dict, Any, List, Tuple

# Role quotas per team (realistic constraints)
MAX_AWPERS_PER_TEAM = 1
MAX_ENTRIES_PER_TEAM = 2

class RoleClassifier:
    """
    Assigns roles based on deterministic player stats.
    
    IMPROVED LOGIC v2.1.1:
    1. AWP Kills > 25% of total -> AWPer (max 1 per team)
    2. Entry: top entry attempts + success rate OR kills
    3. Support: utility focused (>1.2x avg flashes)
    4. Lurker: plays alone (>800u avg teammate dist)
    5. Rotator: mid-distance (400-800u), good trade rate (NEW)
    6. Anchor: default site holder
    """
    
    def classify_roles(self, players: Dict[str, Any]) -> Dict[str, str]:
        """
        Assigns a role to each player ID based on features.
        """
        results = {}
        
        count = len(players)
        if count == 0: 
            return {}
        
        # Calculate averages
        total_flashes = sum(p.flashes_thrown for p in players.values())
        avg_flashes = total_flashes / count
        
        avg_teammate_dist_lobby = sum(p.avg_teammate_dist for p in players.values()) / count
        
        # Get entry thresholds - top 4 by entry_attempts
        entry_data = [(pid, p.entry_kills + p.entry_deaths) for pid, p in players.items()]
        entry_data.sort(key=lambda x: x[1], reverse=True)
        top_entry_pids = set(pid for pid, _ in entry_data[:4])
        
        # PHASE 1: Initial role assignment with scores
        role_candidates: Dict[str, Tuple[str, float]] = {}
        
        for pid, p in players.items():
            role = "Anchor"
            score = 0.0
            
            total_kills = max(1, p.kills)
            awp_ratio = p.awp_kills / total_kills
            
            entry_attempts = p.entry_kills + p.entry_deaths
            entry_success_rate = p.entry_kills / max(1, entry_attempts)
            
            # Calculate trade involvement
            tradeable_ratio = p.tradeable_deaths / max(1, p.deaths)
            
            # Logic Hierarchy (Strict Priority)
            
            # 1. AWPer - clear weapon identity 
            if awp_ratio >= 0.25 and p.awp_kills >= 2:
                role = "AWPer"
                score = p.awp_kills * awp_ratio
                
            # 2. Entry - must have volume AND success
            elif pid in top_entry_pids and entry_attempts >= 3:
                if entry_success_rate >= 0.25 or p.entry_kills >= 2:
                    role = "Entry"
                    # Better score: consider trade success and flash support
                    score = (entry_success_rate * p.entry_kills) + (tradeable_ratio * 2)
                else:
                    # Failed entry = Anchor
                    role = "Anchor"
                    score = 0
                    
            # 3. Support - utility focused
            elif p.flashes_thrown > avg_flashes * 1.2 and p.flashes_thrown >= 3:
                role = "Support"
                score = p.flashes_thrown
                
            # 4. Lurker - plays completely alone
            elif p.avg_teammate_dist > 800:
                role = "Lurker"
                score = p.avg_teammate_dist
            
            # 5. Rotator - mid-distance, good at trading (NEW)
            elif 400 < p.avg_teammate_dist <= 800 and tradeable_ratio >= 0.4:
                role = "Rotator"
                score = tradeable_ratio * p.avg_teammate_dist
                
            # 6. Default - Anchor (site holder)
            else:
                role = "Anchor"
                score = 0
                
            role_candidates[pid] = (role, score)
        
        # PHASE 2: Enforce per-team quotas
        all_pids = list(players.keys())
        team_size = len(all_pids) // 2
        
        team1_pids = set(all_pids[:team_size])
        team2_pids = set(all_pids[team_size:])
        
        def apply_quota_per_team(role_name: str, max_per_team: int, team_pids: set):
            """Demote excess role holders in a single team."""
            candidates = [(pid, score) for pid, (role, score) in role_candidates.items() 
                         if role == role_name and pid in team_pids]
            
            if len(candidates) <= max_per_team:
                return
            
            candidates.sort(key=lambda x: x[1], reverse=True)
            
            for pid, _ in candidates[max_per_team:]:
                # Demote to Rotator instead of straight to Anchor
                role_candidates[pid] = ("Rotator", 0)
        
        # Apply quotas
        apply_quota_per_team("AWPer", MAX_AWPERS_PER_TEAM, team1_pids)
        apply_quota_per_team("AWPer", MAX_AWPERS_PER_TEAM, team2_pids)
        apply_quota_per_team("Entry", MAX_ENTRIES_PER_TEAM, team1_pids)
        apply_quota_per_team("Entry", MAX_ENTRIES_PER_TEAM, team2_pids)
        
        # Extract final roles
        for pid, (role, _) in role_candidates.items():
            results[pid] = role
            
        return results
