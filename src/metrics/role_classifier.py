"""
Role Classifier v2.3
Strict rule-based role detection with behavior-based differentiation.

Roles:
- Entry = takes first fights with success + flash/trade support
- AWPer = primary AWP user
- Support = utility focused (flashes OR blinded enemies)
- Lurker = plays alone (>650u avg distance)
- Rotator = momentum player (swing_kills >= 2)
- Trader = high trade involvement (tradeable_ratio > 0.35)
- SiteAnchor = holds site, low movement (default)
"""

from typing import Dict, Any, List, Tuple

# Role quotas per team
MAX_AWPERS_PER_TEAM = 1
MAX_ENTRIES_PER_TEAM = 2

class RoleClassifier:
    """
    Assigns roles based on deterministic player stats.
    
    IMPROVED LOGIC v2.3:
    1. AWPer: AWP kills > 25% + >= 2 kills
    2. Entry: top entry attempts + success rate + trade/flash support
    3. Support: flashes > team_avg OR enemies_blinded >= 3
    4. Lurker: plays alone (>650u) - FIXED threshold
    5. Rotator: swing_kills >= 2 (momentum player) - BEHAVIOR based
    6. Trader: tradeable_ratio > 0.35 (trade-focused) - BEHAVIOR based
    7. SiteAnchor: default site holder
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
        avg_flashes = total_flashes / count if count > 0 else 0
        
        total_blinded = sum(p.enemies_blinded for p in players.values())
        avg_blinded = total_blinded / count if count > 0 else 0
        
        # Get entry thresholds - top 4 by entry_attempts
        entry_data = [(pid, p.entry_kills + p.entry_deaths) for pid, p in players.items()]
        entry_data.sort(key=lambda x: x[1], reverse=True)
        top_entry_pids = set(pid for pid, _ in entry_data[:4])
        
        # PHASE 1: Initial role assignment with scores
        role_candidates: Dict[str, Tuple[str, float]] = {}
        
        for pid, p in players.items():
            role = "SiteAnchor"  # Default
            score = 0.0
            
            total_kills = max(1, p.kills)
            awp_ratio = p.awp_kills / total_kills
            
            entry_attempts = p.entry_kills + p.entry_deaths
            entry_success_rate = p.entry_kills / max(1, entry_attempts)
            
            # Calculate trade involvement
            tradeable_ratio = p.tradeable_deaths / max(1, p.deaths)
            
            # Get distance and swing kills
            dist = p.avg_teammate_dist
            swing_kills = getattr(p, 'swing_kills', 0)
            
            # Logic Hierarchy (Strict Priority)
            
            # 1. AWPer - clear weapon identity 
            if awp_ratio >= 0.25 and p.awp_kills >= 2:
                role = "AWPer"
                score = p.awp_kills * awp_ratio
                
            # 2. Entry - must have volume AND success
            elif pid in top_entry_pids and entry_attempts >= 3:
                if entry_success_rate >= 0.25 or p.entry_kills >= 2:
                    role = "Entry"
                    # Quality score: success + tradeable position + flash support
                    flash_bonus = 1.0 if p.flashes_thrown >= 2 else 0.5
                    trade_bonus = 1.5 if tradeable_ratio >= 0.4 else 0  # Traded after entry
                    score = (entry_success_rate * p.entry_kills) + trade_bonus + flash_bonus
                else:
                    # Failed entry -> Trader
                    role = "Trader"
                    score = 0
                    
            # 3. Support - utility focused (looser criteria)
            elif p.flashes_thrown > avg_flashes or p.enemies_blinded >= 3:
                role = "Support"
                score = p.flashes_thrown + (p.enemies_blinded * 2)
                
            # 4. Lurker - plays alone (FIXED: lowered to 650u)
            elif dist > 650:
                role = "Lurker"
                score = dist
            
            # 5. Rotator - momentum player (BEHAVIOR: swing_kills >= 2)
            elif swing_kills >= 2:
                role = "Rotator"
                score = swing_kills * 10
                
            # 6. Trader - high trade involvement (BEHAVIOR: tradeable_ratio > 0.35)
            elif tradeable_ratio > 0.35:
                role = "Trader"
                score = tradeable_ratio * 10
                
            # 7. SiteAnchor - holds site (default)
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
            """Demote excess role holders in a single team."""
            candidates = [(pid, score) for pid, (role, score) in role_candidates.items() 
                         if role == role_name and pid in team_pids]
            
            if len(candidates) <= max_per_team:
                return
            
            candidates.sort(key=lambda x: x[1], reverse=True)
            
            for pid, _ in candidates[max_per_team:]:
                # Demote to Trader
                role_candidates[pid] = ("Trader", 0)
        
        # Apply quotas
        apply_quota_per_team("AWPer", MAX_AWPERS_PER_TEAM, team1_pids)
        apply_quota_per_team("AWPer", MAX_AWPERS_PER_TEAM, team2_pids)
        apply_quota_per_team("Entry", MAX_ENTRIES_PER_TEAM, team1_pids)
        apply_quota_per_team("Entry", MAX_ENTRIES_PER_TEAM, team2_pids)
        
        # Extract final roles
        for pid, (role, _) in role_candidates.items():
            results[pid] = role
            
        return results
