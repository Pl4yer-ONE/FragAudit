# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3 or commercial license.

"""
Role Classifier v2.4
Strict rule-based role detection with proper team assignment.

Roles:
- Entry = takes first fights with success + KAST > 55%
- AWPer = primary AWP user
- Support = utility focused
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
    
    IMPROVED LOGIC v2.4:
    1. AWPer: AWP kills > 25% + >= 2 kills
    2. Entry: top entry attempts + success > 35% + KAST > 55%
    3. Support: flashes > team_avg OR enemies_blinded >= 3
    4. Lurker: plays alone (>650u)
    5. Rotator: swing_kills >= 2 (momentum player)
    6. Trader: tradeable_ratio > 0.35 (trade-focused)
    7. SiteAnchor: default site holder
    
    TEAM SPLIT: Uses team_id from PlayerFeatures (not index-based)
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
            
            # Get distance, swing kills and KAST
            dist = p.avg_teammate_dist
            swing_kills = getattr(p, 'swing_kills', 0)
            kast_pct = getattr(p, 'kast_percentage', 0.5)
            raw_impact = getattr(p, 'raw_impact', 50)  # For impact check
            
            # Logic Hierarchy (Strict Priority)
            
            # 1. AWPer - clear weapon identity 
            if awp_ratio >= 0.25 and p.awp_kills >= 2:
                role = "AWPer"
                score = p.awp_kills * awp_ratio
                
            # 2. Entry - TIGHTENED: must have success > 35% AND KAST > 55%
            elif pid in top_entry_pids and entry_attempts >= 3:
                if (entry_success_rate >= 0.35 or p.entry_kills >= 2) and kast_pct >= 0.55:
                    role = "Entry"
                    flash_bonus = 1.0 if p.flashes_thrown >= 2 else 0.5
                    trade_bonus = 1.5 if tradeable_ratio >= 0.4 else 0
                    score = (entry_success_rate * p.entry_kills) + trade_bonus + flash_bonus
                else:
                    # Failed entry requirements -> Trader
                    role = "Trader"
                    score = 0
                    
            # 3. Support - utility focused
            elif p.flashes_thrown > avg_flashes or p.enemies_blinded >= 3:
                role = "Support"
                score = p.flashes_thrown + (p.enemies_blinded * 2)
                
            # 4. Lurker - plays alone
            elif dist > 650:
                role = "Lurker"
                score = dist
            
            # 5. Rotator - momentum player (swing_kills >= 2)
            # BUT: low impact players should NOT be Rotators
            elif swing_kills >= 2 and raw_impact >= 30:
                role = "Rotator"
                score = swing_kills * 10
                
            # 6. Trader - high trade involvement
            elif tradeable_ratio > 0.35:
                role = "Trader"
                score = tradeable_ratio * 10
                
            # 7. SiteAnchor - holds site (default)
            else:
                role = "SiteAnchor"
                score = 0
                
            role_candidates[pid] = (role, score)
        
        # PHASE 2: Enforce per-team quotas using REAL team_id
        # Group players by team
        teams: Dict[str, set] = {}
        for pid, p in players.items():
            team = getattr(p, 'team_id', '') or 'unknown'
            if team not in teams:
                teams[team] = set()
            teams[team].add(pid)
        
        # If no team data, fall back to index split
        if len(teams) <= 1 or 'unknown' in teams:
            all_pids = list(players.keys())
            team_size = len(all_pids) // 2
            teams = {
                'team1': set(all_pids[:team_size]),
                'team2': set(all_pids[team_size:])
            }
        
        def apply_quota_per_team(role_name: str, max_per_team: int, team_pids: set):
            """Demote excess role holders in a single team."""
            candidates = [(pid, score) for pid, (role, score) in role_candidates.items() 
                         if role == role_name and pid in team_pids]
            
            if len(candidates) <= max_per_team:
                return
            
            candidates.sort(key=lambda x: x[1], reverse=True)
            
            for pid, _ in candidates[max_per_team:]:
                role_candidates[pid] = ("Trader", 0)
        
        # Apply quotas to each team
        for team_name, team_pids in teams.items():
            apply_quota_per_team("AWPer", MAX_AWPERS_PER_TEAM, team_pids)
            apply_quota_per_team("Entry", MAX_ENTRIES_PER_TEAM, team_pids)
        
        # Extract final roles
        for pid, (role, _) in role_candidates.items():
            results[pid] = role
            
        return results
