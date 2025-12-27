"""MarketQL makes GraphQL requests to query market data."""

import requests
from typing import Dict, Any, Optional, Tuple


class MarketQL:
    """Makes GraphQL requests to query Polymarket data."""
    
    def __init__(self, url: str):
        """
        Initialize MarketQL with the GraphQL endpoint URL.
        
        Args:
            url: The GraphQL endpoint URL
        """
        self.url = url
    
    def resolved(self, condition_id: str) -> Tuple[bool, Optional[int]]:
        """
        Check if a condition is resolved by querying payoutNumerators.
        
        Args:
            condition_id: The condition ID to query (hex string)
            
        Returns:
            A tuple of (is_resolved, winning_index):
            - is_resolved: True if payoutNumerators is not empty, False otherwise
            - winning_index: The index of the payout numerator whose value equals payoutDenominator if resolved, None otherwise
        """
        # Format the query with the condition_id inline
        query = f'''{{
  condition(id:"{condition_id}"){{
    id
    positionIds
    payoutNumerators
    payoutDenominator
  }}
}}'''
        
        payload = {
            "query": query
        }
        
        try:
            response = requests.post(self.url, json=payload)
            response.raise_for_status()
            data: Dict[str, Any] = response.json()
            
            # Check if we have data and a condition
            if "data" in data and "condition" in data["data"]:
                condition = data["data"]["condition"]
                payout_numerators = condition.get("payoutNumerators", [])
                payout_denominator = str(condition.get("payoutDenominator", "0"))
                
                # Check if resolved (payoutNumerators is not empty)
                if len(payout_numerators) > 0:
                    # Find the index whose value equals payoutDenominator (winning outcome)
                    for idx, numerator in enumerate(payout_numerators):
                        # Handle both string and numeric values
                        if str(numerator) == payout_denominator:
                            return (True, idx)
                    # If we have numerators but none matches the denominator, still return resolved but no winning index
                    return (True, None)
                
                return (False, None)
            
            return (False, None)
            
        except requests.exceptions.RequestException as e:
            print(f"Error making GraphQL request: {e}")
            return (False, None)
        except (KeyError, ValueError) as e:
            print(f"Error parsing GraphQL response: {e}")
            return (False, None)

