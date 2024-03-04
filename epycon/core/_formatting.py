import os
import json
from numpy import savetxt
from datetime import datetime
from collections import OrderedDict

from dataclasses import dataclass

from epycon.utils.decorators import checktypes
from epycon.core._dataclasses import Entry
from epycon.core._validators import (
    _validate_str,
)

from epycon.core._typing import (
    Union, PathLike, List, Dict, Tuple
)

@dataclass
class SignalPlantDefaults:
    CHANNEL_SETTINGS = OrderedDict([    
        ('Visible', 1.0),
        ('Valid', 1.0),
        ('Line_R', 127.0),
        ('Line_G', 100.0),
        ('Line_B', 192.0),
        ('Back_R', 192.0),
        ('Back_G', 192.0),
        ('Back_B', 192.0),
        ('ActiveLAyer', 0.0),
        ('YRangeManual', 0.0),
        ('YRangeMin', -1.0),
        ('YRangeMax', 1.0),
        ('PanelHeight', 100.0),
    ])

    # default datasets data types
    DATASET_DTYPE = '<f4'
    CHANNEL_DTYPES = [
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
    ]

    INFO_DTYPES = [
        ('ChannelName', 'S256'),
        ('DatacacheName', 'S256'),
        ('Units', 'S256')
    ]

    MARKS_DTYPES = [
        ('SampleLeft', '<i4'),
        ('SampleRight', '<i4'),
        ('Group', 'S256'),
        ('Validity', '<f4'),
        ('Channel', 'S256'),
        ('Info', 'S256'),
    ]

    ATTR_DTYPE = '<f4'

        
# def create_json(cfg, personal, ep_data, entries_list):
#     return Io.pretty_json({
#         'patient': {
#             'id': personal["subject_id"],
#             'age': personal["age"],
#             'sex': personal["gender"],
#         },
#         'measurement': {
#             'author': cfg["credentials"]["author"],
#             'owner': cfg["credentials"]["owner"],
#             'device': cfg["credentials"]["device"],
#             'date': datetime.fromtimestamp(
#                 ep_data["log_timestamp"]
#             ).strftime("%Y-%m-%d"),
#         },
#         'diagnosis': Io.filter_entries(entries_list, ep_data),
#         'amp_settings': ep_data["amp_settings"],
#         'channel_config': ep_data["channel_settings"],
#     })


def _tocsv(
        entries: List[Entry],
        ref_timestamp: Union[float, None] = None,
        sep: str = ',',
        ):
    """ Creates summary *.txt file with log entries.

    Args:
        entries (List[Entry]): _description_
        ref_timestamp (Union[float, None], optional): Timestamp for computing relative time of the annotation with respect to the beginning of the recording. Defaults to None.
        sep (str, optional): _description_. Defaults to ','.

    Returns:
        _type_: _description_
    """
    

    if ref_timestamp is None:
        header = f'Group{sep}FileId{sep}Time(Y-m-d_H:M:S){sep}Annotation'
    else:
        header = f'Group{sep}FileId{sep}Time(H:M:S){sep}Annotation'
        ref_dtime = datetime.fromtimestamp(ref_timestamp)    

    out = []
    for item in entries:
        dtime = datetime.fromtimestamp(item.timestamp)

        if ref_timestamp is None:
            # extract absolute date
            out.append(
                [item.group, item.fid, dtime.strftime("%Y-%m-%d_%H:%M:%S"), item.message.replace(sep, "")]
            )
        else:
            timedelta = dtime - ref_dtime
            # extract absolute date
            out.append(
                [item.group, item.fid, str(timedelta), item.message.replace(sep, "")]
            )
    
    # sort by time
    # out = sorted(out, key=lambda x: datetime.strptime(x[2], "%Y-%m-%d_%H:%M:%S"))

    out_text = header + '\n'
    for entry in out:
        tmp = ''.join([str(item) + sep for item in entry])
        out_text += tmp.rstrip(sep) + '\n'
    
    return out_text


def _tosel(
        entries: List[Entry],
        ref_timestamp: float,
        sampling_freq: Union[int, float],
        channel_names: Union[List, Tuple],
        file_name: str,
        ):
    """ Creates SignalPlant .sel file from entries.

    Args:
        entries (List[Entry]): _description_
        reference_timestamp (_type_): _description_
        channel_names (List): _description_

    Returns:
        _type_: _description_
    """
    
    
    ch_names = ''.join(['%'+item+'\t1\n' for item in channel_names])
    
    # timestamp_base = entries['timestamp_base']
    idx = 1
    validity, ch_idx, ch_name = 1, 0, channel_names[0]
    output_txt = ''

    for item in entries:
        start_sample = (datetime.fromtimestamp(item.timestamp) - datetime.fromtimestamp(ref_timestamp)).seconds
        start_sample = int(start_sample * sampling_freq)

        output_txt += f'{idx}\t{start_sample}\t{start_sample}\t{item.group}\t{validity}\t{ch_idx}\t{ch_name}\t{item.message}\n'
        idx += 1    
    
    return (
        '%SignalPlant ver.:1.2.7.3\n'
        '%Selection export from file:\n'
        f'%{file_name + ".csv"}\n'
        f'%SAMPLING_FREQ [Hz]:{sampling_freq}\n'
        '%CHANNELS_VALIDITY-----------------------\n'
        f'{ch_names}'
        '%----------------------------------------\n'
        '%Structure:\n'
        '%Index[-], Start[sample], End[sample], Group[-], Validity[-], Channel Index[-], Channel name[string], Info[string]\n'
        '%Divided by: ASCII char no. 9\n'
        '%DATA------------------------------------\n'
        f'{output_txt}\n'    
    )