"""ResolveViewer monitors ConditionResolution events from the CTF contract."""

import threading
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

from web3 import Web3
from web3.types import LogReceipt


@dataclass
class ResolutionEvent:
    """Represents a ConditionResolution event."""
    condition_id: str
    oracle: str
    question_id: str
    outcome_slot_count: int
    payout_numerators: list[int]
    block_number: int
    transaction_hash: str


class ResolveViewer:
    """
    Monitors ConditionResolution events from the CTF contract in a background thread.
    
    Periodically polls the blockchain for new resolution events and stores them
    in memory for quick lookup. Supports graceful shutdown.
    """
    
    def __init__(
        self,
        web3_url: str,
        ctf_address: str,
        poll_interval: float = 10.0,
        from_block: Optional[int] = None,
    ):
        """
        Initialize the ResolveViewer.
        
        Args:
            web3_url: Polygon RPC endpoint URL
            ctf_address: Address of the CTF contract
            poll_interval: How often to poll for new events (in seconds)
            from_block: Starting block number to search from (None = latest)
        """
        self.web3 = Web3(Web3.HTTPProvider(web3_url))
        self.ctf_address = Web3.to_checksum_address(ctf_address)
        self.poll_interval = poll_interval
        self.from_block = from_block
        
        # Thread-safe storage for resolution events
        self._resolutions: Dict[str, ResolutionEvent] = {}
        self._lock = threading.Lock()
        
        # Thread control
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
        # Load CTF ABI to get event signature
        self._ctf_abi = self._load_ctf_abi()
        self._ctf_contract = self.web3.eth.contract(
            address=self.ctf_address,
            abi=self._ctf_abi
        )
        
        # Event signature for ConditionResolution
        self._condition_resolution_event = self._ctf_contract.events.ConditionResolution
        
        # Track the last processed block to avoid reprocessing
        self._last_processed_block: Optional[int] = None
    
    def _load_ctf_abi(self) -> list[Dict[str, Any]]:
        """Load CTF ABI from file."""
        import json
        from pathlib import Path
        
        ctf_abi_path = Path(__file__).parent.parent / "abi" / "ctf.abi"
        with open(ctf_abi_path, "r") as f:
            return json.load(f)
    
    def start(self) -> None:
        """Start the background thread to monitor for resolution events."""
        if self._thread is not None and self._thread.is_alive():
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop running in background thread."""
        # Initialize from_block if not set
        if self._last_processed_block is None:
            if self.from_block is not None:
                self._last_processed_block = self.from_block
            else:
                # Start from a reasonable recent block (e.g., 1000 blocks ago)
                try:
                    latest = self.web3.eth.block_number
                    self._last_processed_block = max(0, latest - 1000)
                except Exception as e:
                    print(f"Error getting latest block: {e}")
                    self._last_processed_block = 0
        
        while not self._stop_event.is_set():
            try:
                self._fetch_new_resolutions()
            except Exception as e:
                print(f"Error fetching resolutions: {e}")
            
            # Wait for poll_interval or until stop event is set
            self._stop_event.wait(self.poll_interval)
    
    def _fetch_new_resolutions(self) -> None:
        """Fetch new ConditionResolution events from the blockchain."""
        try:
            latest_block = self.web3.eth.block_number
            from_block = self._last_processed_block + 1 if self._last_processed_block is not None else 0
            to_block = latest_block
            
            # Don't query if we're already at the latest block
            if from_block > to_block:
                return
            
            # Query events
            events = self._condition_resolution_event.get_logs(
                fromBlock=from_block,
                toBlock=to_block,
                argument_filters={}
            )
            
            # Process and store events
            with self._lock:
                for event in events:
                    # Normalize condition_id to lowercase hex string for consistent lookup
                    condition_id = Web3.to_hex(event.args.conditionId).lower()
                    
                    # Parse payout numerators
                    payout_numerators = [int(x) for x in event.args.payoutNumerators]
                    
                    resolution = ResolutionEvent(
                        condition_id=condition_id,
                        oracle=event.args.oracle,
                        question_id=Web3.to_hex(event.args.questionId),
                        outcome_slot_count=int(event.args.outcomeSlotCount),
                        payout_numerators=payout_numerators,
                        block_number=event.blockNumber,
                        transaction_hash=Web3.to_hex(event.transactionHash)
                    )
                    
                    self._resolutions[condition_id] = resolution
                
                # Update last processed block
                self._last_processed_block = to_block
            
            if events:
                print(f"Found {len(events)} new resolution event(s)")
        
        except Exception as e:
            print(f"Error in _fetch_new_resolutions: {e}")
            raise
    
    def is_resolved(self, condition_id: str) -> bool:
        """
        Check if a market (condition) has been resolved.
        
        Args:
            condition_id: The condition ID to check (hex string)
            
        Returns:
            True if the condition has been resolved, False otherwise
        """
        # Normalize condition_id to hex string
        if isinstance(condition_id, str):
            if not condition_id.startswith('0x'):
                condition_id = '0x' + condition_id
            condition_id = condition_id.lower()
        
        with self._lock:
            return condition_id in self._resolutions
    
    def get_outcome(self, condition_id: str) -> Optional[ResolutionEvent]:
        """
        Get the resolution outcome for a market (condition).
        
        Args:
            condition_id: The condition ID to query (hex string)
            
        Returns:
            ResolutionEvent if resolved, None otherwise
        """
        # Normalize condition_id to hex string
        if isinstance(condition_id, str):
            if not condition_id.startswith('0x'):
                condition_id = '0x' + condition_id
            condition_id = condition_id.lower()
        
        with self._lock:
            return self._resolutions.get(condition_id)
    
    def get_winning_outcome_index(self, condition_id: str) -> Optional[int]:
        """
        Get the winning outcome index (0-based) for a resolved condition.
        
        Args:
            condition_id: The condition ID to query (hex string)
            
        Returns:
            The index of the winning outcome (the one with non-zero payout),
            or None if not resolved or no clear winner
        """
        resolution = self.get_outcome(condition_id)
        if resolution is None:
            return None
        
        # Find the index with non-zero payout numerator
        for idx, numerator in enumerate(resolution.payout_numerators):
            if numerator > 0:
                return idx
        
        return None
    
    def close(self) -> None:
        """
        Gracefully shutdown the ResolveViewer.
        
        Signals the background thread to stop and waits for it to finish.
        """
        if self._thread is None or not self._thread.is_alive():
            return
        
        self._stop_event.set()
        self._thread.join(timeout=5.0)
        
        if self._thread.is_alive():
            print("Warning: ResolveViewer thread did not stop within timeout")
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

