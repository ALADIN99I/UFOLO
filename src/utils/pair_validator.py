"""
Centralized Currency Pair Validator
Ensures consistent pair handling across all agents and components
"""

class PairValidator:
    """Singleton validator for currency pair standardization"""
    
    # Valid pairs in standard market convention
    VALID_PAIRS = {
        'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF',
        'EURAUD', 'EURCAD', 'EURCHF', 'EURGBP', 'EURJPY', 'EURNZD',
        'GBPAUD', 'GBPCAD', 'GBPCHF', 'GBPJPY', 'GBPNZD',
        'AUDCAD', 'AUDCHF', 'AUDJPY', 'AUDNZD',
        'CADCHF', 'CADJPY', 'CHFJPY', 'NZDCAD', 'NZDCHF', 'NZDJPY',
        'NZDUSD'
    }
    
    # Mapping of invalid pairs to correct versions
    PAIR_CORRECTIONS = {
        # JPY pairs - JPY is always quote currency
        'JPYUSD': 'USDJPY',
        'JPYEUR': 'EURJPY',
        'JPYGBP': 'GBPJPY',
        'JPYAUD': 'AUDJPY',
        'JPYNZD': 'NZDJPY',
        'JPYCAD': 'CADJPY',
        'JPYCHF': 'CHFJPY',
        
        # USD pairs - USD as base where appropriate
        'CADUSD': 'USDCAD',
        'CHFUSD': 'USDCHF',
        
        # EUR pairs - EUR typically as base
        'USDEUR': 'EURUSD',
        'GBPEUR': 'EURGBP',
        'AUDEUR': 'EURAUD',
        'NZDEUR': 'EURNZD',
        'CADEUR': 'EURCAD',
        'CHFEUR': 'EURCHF',
        
        # GBP pairs - GBP typically as base
        'USDGBP': 'GBPUSD',
        'AUDGBP': 'GBPAUD',
        'NZDGBP': 'GBPNZD',
        'CADGBP': 'GBPCAD',
        'CHFGBP': 'GBPCHF',
        
        # AUD pairs
        'USDAUD': 'AUDUSD',
        'CADAUD': 'AUDCAD',
        'CHFAUD': 'AUDCHF',
        'NZDAUD': 'AUDNZD',
        
        # NZD pairs
        'USDNZD': 'NZDUSD',
        'CADNZD': 'NZDCAD',
        'CHFNZD': 'NZDCHF',
        
        # CAD/CHF crosses
        'CHFCAD': 'CADCHF'
    }
    
    @classmethod
    def validate_and_correct(cls, pair, symbol_suffix=''):
        """
        Validate and correct currency pair format
        
        Args:
            pair: Currency pair string (may be invalid)
            symbol_suffix: Broker suffix to remove (e.g., '-ECN')
            
        Returns:
            tuple: (corrected_pair, was_inverted)
                - corrected_pair: Valid pair or None if cannot be fixed
                - was_inverted: True if direction needs to be inverted
        """
        # Clean the pair
        clean_pair = pair.replace(symbol_suffix, '').replace('/', '').upper().strip()
        
        # Check if already valid
        if clean_pair in cls.VALID_PAIRS:
            return clean_pair, False
        
        # Check correction mapping
        if clean_pair in cls.PAIR_CORRECTIONS:
            corrected = cls.PAIR_CORRECTIONS[clean_pair]
            return corrected, True  # Was inverted
        
        # Try generic inversion for 6-character pairs
        if len(clean_pair) >= 6:
            base = clean_pair[:3]
            quote = clean_pair[3:6]
            inverted_pair = quote + base
            
            # Check if inverted version is valid
            if inverted_pair in cls.VALID_PAIRS:
                return inverted_pair, True
            
            # Check if inverted version needs correction
            if inverted_pair in cls.PAIR_CORRECTIONS:
                corrected = cls.PAIR_CORRECTIONS[inverted_pair]
                return corrected, True
        
        # Cannot fix this pair
        return None, False
    
    @classmethod
    def is_valid(cls, pair, symbol_suffix=''):
        """Check if a pair is valid"""
        clean_pair = pair.replace(symbol_suffix, '').replace('/', '').upper().strip()
        return clean_pair in cls.VALID_PAIRS
    
    @classmethod
    def get_all_valid_pairs(cls):
        """Get list of all valid pairs"""
        return list(cls.VALID_PAIRS)
    
    @classmethod
    def standardize_pair_list(cls, pairs, symbol_suffix=''):
        """
        Standardize a list of currency pairs
        
        Args:
            pairs: List of pair strings
            symbol_suffix: Broker suffix
            
        Returns:
            List of tuples: [(original, corrected, needs_inversion), ...]
        """
        results = []
        for pair in pairs:
            corrected, was_inverted = cls.validate_and_correct(pair, symbol_suffix)
            results.append((pair, corrected, was_inverted))
        return results
    
    @classmethod
    def extract_currencies(cls, pair, symbol_suffix=''):
        """
        Extract base and quote currencies from a pair
        
        Returns:
            tuple: (base_currency, quote_currency) or (None, None) if invalid
        """
        corrected, _ = cls.validate_and_correct(pair, symbol_suffix)
        if corrected and len(corrected) >= 6:
            return corrected[:3], corrected[3:6]
        return None, None
    
    @classmethod
    def check_correlation_conflict(cls, existing_pairs, new_pair, symbol_suffix=''):
        """
        Check if new pair creates correlation conflicts
        
        Args:
            existing_pairs: List of existing position pairs
            new_pair: Proposed new pair
            
        Returns:
            tuple: (has_conflict, conflict_reason)
        """
        new_corrected, _ = cls.validate_and_correct(new_pair, symbol_suffix)
        if not new_corrected:
            return True, "Invalid currency pair"
        
        new_base, new_quote = cls.extract_currencies(new_corrected)
        
        conflicts = []
        for existing in existing_pairs:
            exist_corrected, _ = cls.validate_and_correct(existing, symbol_suffix)
            if exist_corrected:
                exist_base, exist_quote = cls.extract_currencies(exist_corrected)
                
                # Check for same pair
                if new_corrected == exist_corrected:
                    conflicts.append(f"Duplicate pair: {new_corrected}")
                
                # Check for heavy concentration in one currency
                if new_base == exist_base:
                    conflicts.append(f"Multiple {new_base} base positions")
                if new_quote == exist_quote and new_quote in ['JPY', 'USD', 'EUR']:
                    conflicts.append(f"Multiple {new_quote} quote positions")
        
        if conflicts:
            return True, "; ".join(conflicts)
        return False, None
    
    def validate_and_normalize_pair(self, pair, symbol_suffix=''):
        """
        Instance method that validates and normalizes a currency pair.
        This is what the other components are calling.
        IMPORTANT: Preserves the broker suffix if present.
        
        Args:
            pair: Currency pair string (may be invalid) with optional suffix
            symbol_suffix: Broker suffix (if not provided, will be auto-detected)
            
        Returns:
            str: Normalized pair WITH suffix preserved, or None if invalid
        """
        # Auto-detect suffix if not provided
        if not symbol_suffix and '-' in pair:
            parts = pair.split('-')
            if len(parts) == 2:
                symbol_suffix = '-' + parts[1]
        
        # Validate the base pair
        corrected, _ = self.validate_and_correct(pair, symbol_suffix)
        
        # If valid, add back the suffix if it was present
        if corrected and symbol_suffix and '-' in pair:
            return corrected + symbol_suffix
        
        return corrected
