from pathlib import Path
from typing import Any


class ConfigResolver:
    """Resolves configuration values from CLI arguments and config file.
    
    Validates that CLI and config values match when both are provided.
    """
    
    def __init__(self, config_section: dict):
        self.config_section = config_section
    
    def resolve(
        self,
        field_name: str,
        cli_value: Any,
        is_path: bool = False,
        required: bool = True,
    ) -> Any:
        """Resolve a configuration field from CLI and config sources.
        
        Args:
            field_name: Name of the field in the config file
            cli_value: Value provided via CLI (None if not provided)
            is_path: Whether the value is a filesystem path
            required: Whether the field is required
            
        Returns:
            The resolved value
            
        Raises:
            ValueError: If required field is missing or values conflict
        """
        config_value = self.config_section.get(field_name)
        
        # Both provided - they must match
        if cli_value is not None and config_value is not None:
            config_compare = Path(config_value) if is_path else config_value
            cli_compare = Path(cli_value) if is_path else cli_value
            
            if config_compare != cli_compare:
                raise ValueError(
                    f"Conflict for '{field_name}': "
                    f"CLI specifies '{cli_value}' but config has '{config_value}'. "
                    f"Values must match when both are provided."
                )
            return cli_value
        
        # Only CLI provided
        elif cli_value is not None:
            return cli_value
        
        # Only config provided
        elif config_value is not None:
            return config_value
        
        # Neither provided
        else:
            if required:
                raise ValueError(
                    f"Missing required field '{field_name}' "
                    f"(provide via config or --{field_name.replace('_', '-')})"
                )
            return None