import os
import sys
import struct
from itertools import islice
from datetime import datetime
from collections import abc

import numpy as np
import h5py as h

from epycon.core._typing import (
    Union, List, Sequence, PathLike, ArrayLike, 
)

from epycon.core._validators import (
    _validate_int, _validate_str, _validate_version, _validate_reference
)

from epycon.core.bins import (
    readbin,
    readchunk,
    parsebin,
    )

from epycon.core.helpers import (
    safe_string,
    pretty_json,
)

from epycon.utils.decorators import checktypes
from epycon.core._dataclasses import (
    Header,
    Channel,
    Channels,
    Entry,    
)

from epycon.config.byteschema import (
    WMx32LogSchema, WMx32MasterSchema, WMx32EntriesSchema,
    WMx64LogSchema, WMx64MasterSchema, WMx64EntriesSchema,
)

from epycon.config.byteschema import (
    GROUP_MAP, SOURCE_MAP, MASTER_FILENAME, ENTRIES_FILENAME
)


def _twos_complement(darray: np.array, sample_size: int):
    """ Extract negative values with the Two's complement

    Args:
        darray (np.array): _description_
        sample_size (int): _description_
    """
    twos_complement = 2 ** (8 * sample_size) - 1
    darray[darray >= (twos_complement // 2 - 1)] -= twos_complement

    return darray


class LogParser(abc.Iterator):
    """_summary_

    Args:
        abc (_type_): _description_
    """
    def __init__(
        self,
        f_path: Union[str, bytes, os.PathLike],
        version: str = None,        
        samplesize: int = 1024,
        start: int = 0,
        end: Union[int, None] = None,
        **kwargs
        ) -> None:
        super().__init__()

        # validate WM version and return correct byte schema             
        if _validate_version(version) == 'x32':
            self.diary = WMx32LogSchema
        elif _validate_version(version) == 'x64':
            self.diary = WMx64LogSchema
        else:
            raise NotImplementedError

        self.f_path = f_path
        self.timestampfmt, self.timestampfactor = self.diary.timestamp_fmt
        
        self.samplesize = _validate_int("chunk size", samplesize, min_value=1024)
        self.start = _validate_int("start sample", start, min_value=0)
        self.end = _validate_int("end sample", end, min_value=start)
            
        
        # file related content required for parsing.        
        self._f_obj = None
        self._header = None
        self._stopbyte = None
        self._chunksize = None
        self._blocksize = None
        self._channel_mapping = None
        self._mount_negidx = None
        self._mount_posidx = None                


    def __enter__(self):
        try:
            self._f_obj = open(self.f_path, "rb")

            # read and store header in advance
            self._header = self._readheader()
            
            # adjust the range of datablocks to read given as the number of active channels times bytes per sample
            self._block_size = self._header.num_channels * self.diary.sample_size 

            # compute size of data block to read at once
            self._chunksize = self._block_size * self.samplesize

            # convert start sample to byte address         
            startbyte = self._header.datablock_address + self.start * self._block_size

            if self.end is not None:
                # convert end sample to byte address
                stopbyte = self._header.datablock_address + self.end * self._block_size                
            else:
                # set stop byte to the last one
                stopbyte = float("Inf")

            # get address of the last/user defined byte
            self._stopbyte = min(stopbyte, self._f_obj.seek(0, 2))                      
            
            # Seek to start position
            self._f_obj.seek(max(self._header.datablock_address, startbyte))

        except IOError as e:            
            raise IOError(e)
    
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        # Clear file header
        if self._header is not None:
            self._header = None

        # Close file object
        if self._f_obj:
            self._f_obj.close()
        
        if exc_type:
            print(f"Exception occurred: {exc_type}, {exc_value}")

    def __iter__(self):
        return self

    def __next__(self) -> np.ndarray:
        """_summary_

        Raises:
            StopIteration: _description_            

        Returns:
            np.ndarray: _description_
        """
        try:
            if self._f_obj.tell() >= self._stopbyte:
                raise StopIteration
            
            chunksize = min(self._chunksize, self._stopbyte - self._f_obj.tell())                        
            chunk = self._f_obj.read(chunksize)

            if not chunk:
                raise StopIteration
            else:
                chunk = np.frombuffer(
                    bytearray(chunk),
                    dtype=np.dtype(self.diary.datablock.fmt),
                    )
            
        except StopIteration:
            self.__exit__(exc_type=None, exc_value=None, exc_traceback=None)
            raise

        return self._process_chunk(chunk)


    def read(
        self,
    ) -> np.ndarray:
        """ Reads block of data.

        Returns:
            np.ndarray: _description_
        """
        
        chunk = self._f_obj.read(self._stopbyte-self._f_obj.tell())

        if not chunk:
            return None
        else:
            chunk = np.frombuffer(
                bytearray(chunk),
                dtype=np.dtype(self.diary.datablock.fmt),
                )
            
        return self._process_chunk(chunk)
            

    def _process_chunk(
        self,
        chunk: np.ndarray,
        ) -> np.ndarray:
        """_summary_

        Args:
            byte_chunk (_type_): _description_

        Returns:
            _type_: _description_
        """
        chunk = _twos_complement(chunk, self.diary.sample_size)

        # Multiply signal by resolution to get correct physical units.
        chunk = chunk * self._header.amp.resolution

        # Reshape array
        return chunk.reshape(
            (
                len(chunk) // self._header.num_channels,
                self._header.num_channels,
                )
            )        


    def _readheader(self) -> Header:
        """_summary_

        Args:
            f_path (str): _description_

        Returns:
            _type_: _description_
        """

        # read header bytearray
        start_byte, bytes_to_read = self.diary.header.block_size
        bheader = readbin(self.f_path, start_byte, bytes_to_read)        

        # Get timestamp
        startbyte, endbyte = self.diary.header.timestamp
        timestamp = parsebin(bheader[startbyte:endbyte], self.timestampfmt) // self.timestampfactor

        # Get number of active channels
        startbyte, endbyte = self.diary.header.num_channels
        num_channels = parsebin(bheader[startbyte:endbyte], '<H')

        # Get the address of the first data chunk
        startbyte, endbyte = self.diary.datablock.start_address
        datablock_startbyte = parsebin(bheader[startbyte:endbyte], '<H')

        # create mapping from channel id (index) into sample position (value at given index) in the data chunk
        startbyte, endbyte = self.diary.datablock.sample_mapping
        sample_mapping = parsebin(bheader[startbyte:endbyte], 'B' * (endbyte-startbyte))
        
        # Get the amplifier hardware settings
        amp_settings = dict()
        amp_settings["highpass_freq"] = parsebin(
            bheader[self.diary.amplifier.highpass_freq[0]:self.diary.amplifier.highpass_freq[1]],
            '<H',
        )

        amp_settings["notch_freq"] = parsebin(
            bheader[self.diary.amplifier.notch_freq[0]:self.diary.amplifier.notch_freq[1]],
            '<H',
        )

        amp_settings["resolution"] = parsebin(
            bheader[self.diary.amplifier.resolution[0]:self.diary.amplifier.resolution[1]],
            '<H',
        )

        amp_settings["sampling_freq"] = parsebin(
            bheader[self.diary.amplifier.sampling_freq[0]:self.diary.amplifier.sampling_freq[1]],
            '<H',
        )

        # for field_name, (startbyte, endbyte) in self.diary.amplifier.items():            
        #     amp_settings[field_name] = parsebin(bheader[startbyte:endbyte], '<H')
        
        # get info about recording channels
        channels = Channels(list(), dict())
        used_channels = set()
        
        startbyte, endbyte = self.diary.channels.block_size
        
        it = iter(bheader[startbyte:endbyte])
        i = 0
        mount = dict()
        while (bchunk := bytes(islice(
            it,
            self.diary.channels.subblock_size[1],
            ))):

            # validate channel existence
            if bchunk[:1] == b"\x00":
                continue
            
            ch_name = safe_string(
                bchunk[self.diary.channels.name[0]:self.diary.channels.name[1]].decode("unicode-escape").strip("\x00")
            )

            # skip channel duplicates
            if ch_name in used_channels:
                continue
            else:
                used_channels.add(ch_name)

            # source of data acquisition
            startbyte, endbyte = self.diary.channels.input_source
            source = SOURCE_MAP[
                parsebin(bchunk[startbyte:endbyte], 'B')
            ]            

            # retrieve and map bytes into data byte order in the stream data chunk
            startbyte, endbyte = self.diary.channels.ids
            mount_pair = parsebin(bchunk[startbyte:endbyte], 'BB')
            references = list(map(
                lambda x: sample_mapping[x] if x != 0xff else None,
                mount_pair,
            ))

            try:
                # check if channel was actively recorded
                _validate_reference(*references)
            except ValueError:
                continue

            # retrieve and filter junction box pins; pin polarity = [positive, negative]
            startbyte, endbyte = self.diary.channels.jbox_pins
            pins = parsebin(bchunk[startbyte:endbyte], 'BB')
            pins = list(map(
                lambda x: x if x != 0xff else None,
                pins,
            ))

            if any(item is None for item in references):
                # store single-reference leads (usually unipolar or surface ecg leads)
                channels.content.append(
                    Channel(ch_name, references[0], source, pins[0],)
                    )
                
                # create mapping computed channel -> index of the original channel in the channels list
                channels.mount[ch_name] = (i,)
                i += 1
            else:
                # store bipolar leads as separate unipolar channels
                channels.content.extend([
                    Channel("u+"+ch_name, references[0], source, pins[0],),
                    Channel("u-"+ch_name, references[1], source, pins[1],),
                    ])
                
                # create mapping computed channel -> index of the original channel in the channels list
                channels.mount[ch_name] = (i, i+1)
                i += 2
            
        return Header(
            timestamp,
            num_channels,
            channels,            
            amp_settings,
            datablock_startbyte,
            ) 

    def get_header(self):
        """ Returns pased datalog header.

        Returns:
            _type_: _description_
        """
        return self._header


def _mount_channels(darray, mappings):
    result = np.empty((len(mappings), darray.shape[0]), dtype=darray.dtype)

    # Iterate through the tuples, performing the selection/summation    
    for t, source in enumerate(mappings.values()):
        if len(source) == 1:
            result[t] = darray[:, source[0]]
        else:            
            result[t] = darray[:, source[0]] - darray[:, source[1]]
        
    return result.transpose()


@checktypes
def _readdata(
    f_path: str,
    **kwargs,
) -> Union[np.ndarray, LogParser]:
    """
    """ 

    # Extract some of the arguments (pass chunksize on).    
    chunksize = kwargs.get("chunksize", None)
    chunksize = _validate_int("chunksize", chunksize, min_value=1)

    nsamples = kwargs.get("nrows", None)
    
    # Instantiate data parser.
    parser = LogParser(f_path, **kwargs)

    if chunksize:
        return parser

    with parser:
        return parser.read()


@checktypes
def _readheader(
    f_path: str,
) -> Header:
    """_summary_

    Args:
        f_path (str): _description_

    Returns:
        Header: _description_
    """
    
    # Instantiate data parser.
    parser = LogParser(f_path)
    
    # with parser:
    return parser.get_header()


def _readmaster(
    f_path: Union[str, bytes, os.PathLike],
    ):
    """ Parses the content of the MASTER file.

    Args:
        f_path (Union[str, bytes, os.PathLike]): path to  MASTER file

    Raises:
        IOError: _description_

    Returns:
        _type_: _description_
    """

    try:
        # read binary file
        barray = readbin(f_path)
    except IOError as e:
        raise IOError

    start_address, end_address = WMx64MasterSchema.subject_id    

    return barray[start_address:end_address].decode("ascii", "ignore").strip("\x00")


def _readentries(
    f_path: Union[str, bytes, os.PathLike],
    version: str = None,
    ):
    """ Parses the content of the ENTRIES file.

    Args:
        f_path (Union[str, bytes, os.PathLike]): _description_

    Returns:
        _type_: _description_
    """
    # TODO: check entries at the end of procedure with invalid timestamp

    # initialize entries dictionary
    entries = list()                           
                
    # validate WM version and return correct byte schema             
    if _validate_version(version) == 'x32':
        diary = WMx32EntriesSchema
    elif _validate_version(version) == 'x64':
        diary = WMx64EntriesSchema
    else:
        raise NotImplementedError
    
    try:
        # read entire binary file
        barray = readbin(f_path)
    except IOError as e:
        raise IOError

    if barray is None:
        return entries

    # Validate expected byte size
    if (len(barray) - diary.header[1]) % diary.line_size != 0:
        sys.exit(f'Invalid length of byte array. Check byte schema version.')
        
    # Convert header type into byte format and timestamp factor
    fmt, factor = diary.timestamp_fmt

    # Read and validate timestamp format
    header_timestamp = struct.unpack(fmt, barray[diary.header_timestamp[0]:diary.header_timestamp[1]])[0]
    header_timestamp = header_timestamp // factor

    try:
        header_date = datetime.fromtimestamp(header_timestamp)
    except ValueError as err:
        sys.exit(f'Invalid timestamp format.')    

    # iterate over byte array
    for pointer in range(diary.header[1], len(barray), diary.line_size):
        # entry type
        start_byte, end_byte = diary.entry_type
        group = struct.unpack("<H", barray[pointer + start_byte:pointer + end_byte])[0]        

        # datalog file uid
        start_byte, end_byte = diary.datalog_id
        datalog_uid = struct.unpack("<L", barray[pointer + start_byte:pointer + end_byte])[0]
        datalog_uid = f"{datalog_uid:08x}"

        # timestamp
        start_byte, end_byte = diary.timestamp
        timestamp = struct.unpack(fmt, barray[pointer + start_byte:pointer + end_byte])[0] / factor

        # retrieve text annotation
        start_byte, end_byte = diary.text
        message = barray[pointer + start_byte:pointer + end_byte]
        message = "".join([char for i in struct.unpack("<" + "B" * len(message), message) if (char:= chr(i)).isprintable()])
        
        # if re.match('[\x00-\x1f\x7f]+', text):
        #     continue

        entries.append(
            Entry(
                fid=datalog_uid,
                group=GROUP_MAP.get(group, "UNKNOWN"),
                timestamp=timestamp,
                message=message,
                )
        )        

    return entries