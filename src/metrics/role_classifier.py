"""
Role Classifier
Strict rule-based role detection with team quotas.

Entry = intentionally takes first fights AND has success
Anchor = plays for trades/late round
AWPer = primary AWP user
Support = utility focus
Lurker = plays alone
"""

from typing import Dict, Any, List, Tuple

# Role quotas per team (realistic constraints)
MAX_AWPERS = 2
MAX_ENTRIES = 3

class RoleClassifier:
    """
    Assigns roles based on deterministic player stats.
    
    IMPROVED LOGIC:
    1. AWP Kills > 25% of total -> AWPer (max 2 per team)
    2. Entry role requires BOTH:
       - High entry attempts (top 4 in lobby)
       - Entry success rate > 25% (not just dying first)
       OR entry_kills >= 2 (proven opener)
       Max 3 entries per team
    3. Utility Usage > Team Avg -> Support
    4. Avg Distance from Team > Threshold -> Lurker
    5. Default -> Anchor (plays for trades)
    """
    
    def classify_roles(self, players: Dict[str, Any]) -> Dict[str, str]:
        """
        Assigns a role to each player ID based on features.
        Expects 'players' to be a dict of PlayerFeatures objects.
        """
        results = {}
        
        count = len(players)
        if count == 0: 
            return {}
        
        # Calculate averages
        total_flashes = sum(p.flashes_thrown for p in players.values())
        avg_flashes = total_flashes / count
        
        # Get entry thresholds - top 4 by entry_attempts (2 per team approx)
        entry_data = [(pid, p.entry_kills + p.entry_deaths) for pid, p in players.items()]
        entry_data.sort(key=lambda x: x[1], reverse=True)
        
        # Top 4 entry attempt players
        top_entry_pids = set(pid for pid, _ in entry_data[:4])
        
        # PHASE 1: Initial role assignment with scores for priority
        role_candidates: Dict[str, Tuple[str, float]] = {}  # pid -> (role, score)
        
        for pid, p in players.items():
            role = "Anchor"  # Default
            score = 0.0  # Higher = more qualified for role
            
            # Safe division
            total_kills = max(1, p.kills)
            awp_ratio = p.awp_kills / total_kills
            
            # Entry attempts = kills + deaths in opening duels
            entry_attempts = p.entry_kills + p.entry_deaths
            entry_success_rate = p.entry_kills / max(1, entry_attempts)
            
            # Logic Hierarchy (Strict Priority)
            
            # 1. AWPer - clear weapon identity 
            if awp_ratio >= 0.25 and p.awp_kills >= 2:
                role = "AWPer"
                score = p.awp_kills * awp_ratio  # More AWP kills = more qualified
                
            # 2. Entry - must have BOTH volume AND success
            elif pid in top_entry_pids and entry_attempts >= 3:
                if entry_success_rate >= 0.25 or p.entry_kills >= 2:
                    role = "Entry"
                    score = entry_success_rate * p.entry_kills  # Success matters
                else:
                    role = "Anchor"
                    score = 0
                    
            # 3. Support - utility focused
            elif p.flashes_thrown > avg_flashes * 1.2 and p.flashes_thrown >= 3:
                role = "Support"
                score = p.flashes_thrown
                
            # 4. Lurker - plays alone
            elif p.avg_teammate_dist > 800:
                role = "Lurker"
                score = p.avg_teammate_dist
                
            # 5. Default - Anchor
            else:
                role = "Anchor"
                score = 0
                
            role_candidates[pid] = (role, score)
        
        # PHASE 2: Enforce team quotas
        # Split by team (assume 5v5 split by player index for now)
        # In reality, you'd use team_id from demo
        all_pids = list(players.keys())
        
        # Get all AWPers and Entries, sorted by score
        awpers = [(pid, score) for pid, (role, score) in role_candidates.items() if role == "AWPer"]
        entries = [(pid, score) for pid, (role, score) in role_candidates.items() if role == "Entry"]
        
        awpers.sort(key=lambda x: x[1], reverse=True)
        entries.sort(key=lambda x: x[1], reverse=True)
        
        # Demote excess AWPers (keep top MAX_AWPERS)
        if len(awpers) > MAX_AWPERS:
            for pid, _ in awpers[MAX_AWPERS:]:
                role_candidates[pid] = ("Anchor", 0)  # Demote to Anchor
        
        # Demote excess Entries (keep top MAX_ENTRIES)
        if len(entries) > MAX_ENTRIES:
            for pid, _ in entries[MAX_ENTRIES:]:
                role_candidates[pid] = ("Anchor", 0)  # Demote to Anchor
        
        # Extract final roles
        for pid, (role, _) in role_candidates.items():
            results[pid] = role
            
        return results
