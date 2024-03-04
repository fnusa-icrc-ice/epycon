from epycon.core._typing import Tuple
from dataclasses import dataclass


@dataclass(frozen=True)
class HDFDataConfig:
    NAME: str = 'Data'
    DTYPE: str = '<f4'


@dataclass(frozen=True)
class HDFInfoConfig:
    NAME: str = 'Info'
    DTYPE: Tuple = (
        ('ChannelName', 'S256'),
        ('DatacacheName', 'S256'),
        ('Units', 'S256')
    )


@dataclass(frozen=True)
class HDFChannelConfig:
    NAME: str = 'ChannelConfig'
    DTYPE: Tuple = (
        ('Channel', 'S256'),
        ('Visible', '<f4'),
        ('Valid', '<f4'),
        ('Line_R', '<f4'),
        ('Line_G', '<f4'),
        ('Line_B', '<f4'),
        ('Back_R', '<f4'),
        ('Back_G', '<f4'),
        ('Back_B', '<f4'),
        ('ActiveLAyer', '<f4'),
        ('YRangeManual', '<f4'),
        ('YRangeMin', '<f4'),
        ('YRangeMax', '<f4'),
        ('PanelHeight', '<f4')
    )    

@dataclass(frozen=True)
class HDFDisplayConfig:
        Visible: float = 1.0
        Valid: float = 1.0
        Line_R: float = 127.0
        Line_G: float = 100.0
        Line_B: float = 192.0
        Back_R: float = 192.0
        Back_G: float = 192.0
        Back_B: float = 192.0
        ActiveLayer: float = 0.0
        YRangeManual: float = 0.0
        YRangeMin: float = -1.0
        YRangeMax: float = 1.0
        PanelHeight: float = 100.0


@dataclass(frozen=True)
class HDFMarksConfig:
    NAME: str = 'Marks'
    DTYPE: Tuple = (
        ('SampleLeft', '<i4'),
        ('SampleRight', '<i4'),
        ('Group', 'S256'),
        ('Validity', '<f4'),
        ('Channel', 'S256'),
        ('Info', 'S256'),
    )
    DEFAULT_VALIDITY: float = 0.0
    DEFAULT_GROUP: str = 'GROUP_1'.encode('UTF-8')


@dataclass(frozen=True)
class HDFAttrsConfig:
    DEFAULT_DATACACHE = 'RAW'
    DEFAULT_UNITS = 'uV'
    DEFAULT_FS: int = 2000
    generated_by: str = 'epycon'.encode('UTF-8')
    left_idx: int = 0
    right_idx: int = 100
    

@dataclass
class HDFConfig:    
    data = HDFDataConfig()
    info = HDFInfoConfig()
    channel = HDFChannelConfig()
    marks = HDFMarksConfig()
    attrs = HDFAttrsConfig()
    display = HDFDisplayConfig()