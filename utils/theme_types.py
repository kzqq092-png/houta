"""
Theme Types Module

This module defines theme-related enums and types.
"""

from enum import Enum, auto

class Theme(Enum):
    """Theme enumeration for application appearance"""
    LIGHT = auto()
    DARK = auto()
    SYSTEM = auto()
    CUSTOM = auto()
    BLUE = auto()

    @property
    def value(self) -> str:
        """Get theme value as lowercase string"""
        return self.name.lower()

    @classmethod
    def from_str(cls, theme_str: str) -> 'Theme':
        """Convert string to Theme enum
        
        Args:
            theme_str: Theme string
            
        Returns:
            Theme enum value
            
        Raises:
            ValueError: If theme string is invalid
        """
        try:
            # 尝试直接匹配主题名称
            theme_str = theme_str.upper()
            if hasattr(cls, theme_str):
                return getattr(cls, theme_str)
                
            # 如果找不到匹配的主题，尝试从枚举值中查找
            for theme in cls:
                if theme.name.lower() == theme_str.lower():
                    return theme
                    
            raise ValueError(f"Invalid theme: {theme_str}")
        except Exception as e:
            raise ValueError(f"Invalid theme: {theme_str} ({str(e)})")
            
    def __str__(self) -> str:
        """Convert Theme enum to string
        
        Returns:
            Theme name in lowercase
        """
        return self.name.lower()
        
    def __repr__(self) -> str:
        """Get string representation of Theme enum
        
        Returns:
            Theme name
        """
        return f"Theme.{self.name}" 