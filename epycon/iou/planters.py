import os
from warnings import warn
import h5py as h
import numpy as np
from dataclasses import fields


from epycon.iou.constants import HDFConfig
from epycon.utils.decorators import checktypes

from epycon.core._dataclasses import Entry
from epycon.core._formatting import _tocsv, _tosel, SignalPlantDefaults

from epycon.core._typing import (
    Union, PathLike, NumpyArray, Tuple, List, Any,
    Callable, Iterator, Optional, Dict
)

from epycon.core._validators import (
    _validate_str, _validate_int, _validate_tuple,
)


class EntryPlanter:    
    def __init__(
            self,
            entries: List[Entry],
            ):
        
        self.entries = entries

    def savecsv(
            self,
            f_path: Union[str, bytes, PathLike],            
            criteria: Dict[str, Union[List, Tuple, set]] = None,
            **kwargs,
            ) -> None:
        
        ref_timestamp = kwargs.pop("ref_timestamp", None)
                
        # format entries
        content = _tocsv(
            self._filter(criteria=criteria),
            ref_timestamp=ref_timestamp if ref_timestamp is not None else None,
            )
                
        with open(f_path, 'w') as f_obj:
            f_obj.write(content)

    def savesel(
            self,
            f_path: Union[str, bytes, PathLike],
            ref_timestamp: float,
            sampling_freq: Union[int, float],
            channel_names: Union[List, Tuple],            
            criteria: Dict[str, Union[List, Tuple, set]] = None,
            **kwargs,
            ) -> None:        

        # format entries
        content = _tosel(
            self._filter(criteria=criteria),
            ref_timestamp,
            sampling_freq,
            channel_names,
            os.path.basename(f_path),
            )
                
        with open(f_path, 'w') as f_obj:
            f_obj.write(content)

    def _filter(
            self,            
            criteria: Dict[str, Union[List, Tuple, set]] = None,
        ) -> Iterator[Entry]:
            """ Returns an iterator of MyDataClass items that pass the filter function.

            Args:
                param_name (Union[str, None], optional): _description_. Defaults to None.
                valid (Union[List, Tuple, None], optional): _description_. Defaults to None.

            Returns:
                dict: _description_
            """
            # convert to set
            if criteria:
                for field in ("fids", "groups"):
                    if field in criteria:
                        if isinstance(criteria[field], str):
                            criteria[field] = {criteria[field]}
                        elif isinstance(criteria[field], (list, tuple, set)):
                            criteria[field] = set(criteria[field])
                        else:
                            raise TypeError
            
            # iterate over items
            for item in self.entries:
                valid = True
                if criteria:
                    if (
                        "fids" in criteria
                        and criteria["fids"]
                        and item.fid not in criteria["fids"]                        
                        ):
                        valid = False
                    if (
                        valid
                        and "groups" in criteria
                        and criteria["groups"]
                        and item.group not in criteria["groups"]
                        ):
                        valid = False

                if valid:
                    yield item


class DatalogPlanter:
    def __init__(
        self,
        f_path: Union[str, bytes, os.PathLike],
        column_names: Union[List, Tuple, None] = None,
        **kwargs,
    ) -> None:
        
        self.f_path = f_path
        self._f_obj = None
        self._extension = _validate_str("output file extension", os.path.splitext(f_path)[1].lower(), valid_set={".csv", ".h5"})
        self.column_names = column_names

    def __enter__(self):
        raise NotImplementedError
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        # Close file object
        if self._f_obj:
            self._f_obj.close()
        
        # set flags and attributes to defaults
        self._header_isstored = False
        self._fmt = None

        if exc_type:
            print(f"Exception occurred: {exc_type}, {exc_value}")

    def write(self):
        raise NotImplementedError


class CSVPlanter(DatalogPlanter):
    def __init__(
        self,
        f_path: Union[str, bytes, os.PathLike],
        column_names: Union[List, Tuple, None] = None,
        **kwargs
    ):        

        super().__init__(f_path, column_names)        

        self._delimiter = kwargs.pop("delimiter", ",")
        self._header_isstored = False
        self._fmt = None

    def __enter__(self):
        try:            
            self._f_obj = open(self.f_path, "w")
        except IOError as e:
            raise IOError(e)
        return self

    def write(
        self,
        darray: NumpyArray,        
        **kwargs,
        ) -> None:
        """_summary_

        Args:
            darray (NumpyArray): _description_
            column_names (Union[list, tuple, None], optional): _description_. Defaults to None.
        """

        # write header
        if not self._header_isstored:
            if self.column_names is None:
                # create arbitrary column names if not provided
                self.column_names = [str(i) for i in range(darray.shape[1])]
            else:
                assert len(self.column_names) == darray.shape[1]
            
            self._f_obj.writelines(self.delimiter.join(self.column_names) + '\n')
            self._header_isstored = True

        # create csv formatting
        if self._fmt is None:
            string_fmt = kwargs.pop("delimiter", "%d")
            self._fmt = self.delimiter.join([string_fmt]*darray.shape[1])

        # write data
        self._f_obj.write(('\n'.join([self._fmt]*darray.shape[0]) + '\n') % tuple(darray.ravel()))



class HDFPlanter(DatalogPlanter):
    """_summary_

    Args:
        MarksMixin (_type_): _description_
        AttributesMixin (_type_): _description_
    """

    # class-specific constants
    _DATASET_DNAME = 'Data'
    _INFO_DNAME = 'Info'
    _CHANNEL_DNAME = 'ChannelSettings'
    _MARKS_DNAME = 'Marks'
    _DATACACHE_NAME = 'RAW'
    _LEFT_INDEX = 0
    _RIGHT_INDEX = 100
    _UNITS = 'mV'
    _PARSER = 'Epycon'
    
    def __init__(
        self,
        f_path,
        column_names: Union[List, Tuple, None] = None,
        **kwargs,        
        ):
        
        super().__init__(f_path, column_names) 
        
        self.cfg = SignalPlantDefaults()

        self.sampling_freq = kwargs.pop("sampling_freq", 1)
        self.units = kwargs.pop("units", "uV")
        self.entries = kwargs.pop("entries", None)
        self.factor = kwargs.pop("factor", 1000)

        self._header_isstored = False

    def __enter__(self):
        try:            
            self._f_obj = h.File(self.f_path, "w")
        except IOError as e:
            raise IOError(e)
        return self
    
    def write(
            self,
            darray: NumpyArray,            
        ) -> None:
                
        # write header
        if not self._header_isstored:
            if self.column_names is None:
                # create arbitrary column names if not provided
                self.column_names = [str(i) for i in range(darray.shape[1])]
            else:
                assert len(self.column_names) == darray.shape[1]
            
            # make a list of encoded channel names with removed white spaces
            self.column_names = [''.join(item.split()).encode('UTF-8') for item in self.column_names]

            # write attributes
            self._generate_attributes()
            # write channel info
            self._generate_channel_info()
            # write channel settings
            self._generate_channel_settings()

            self._header_isstored = True
        
        self.add_samples(darray)

    
    def _generate_attributes(self) -> None:
        """_summary_

        Args:
            data_arr (_type_): _description_
        """
        
        # Add attributes with mandatory parameters
        self._f_obj.attrs['Fs'] = np.array([self.sampling_freq], dtype=self.cfg.ATTR_DTYPE)        
        self._f_obj.attrs['GeneratedBy'] = self._PARSER
        self._f_obj.attrs['LeftI'] = self._LEFT_INDEX
        self._f_obj.attrs['RightI'] = self._RIGHT_INDEX


    def _generate_channel_settings(
            self,            
            ):
            """Generates channel settings for Signal Plant

            Args:
                self.f_obj (obj): file obj. handle
                ch_names (list): List of channel names

            Raises:
                TypeError: Check for strings in <ch_names> list

            Returns:
                self.f_obj (obj): file obj. handle
            """

            # Generate content
            content = list()

            for ch_name in self.column_names:                
                # Generate single channel settings and append to content
                temp = [ch_name]
                temp.extend(list(self.cfg.CHANNEL_SETTINGS.values()))
                content.append(tuple(temp))

            content = np.array(
                content,
                dtype=self.cfg.CHANNEL_DTYPES,
                )

            # add/append dataset
            if self._CHANNEL_DNAME in self._f_obj:
                del self._f_obj[self._CHANNEL_DNAME]
            
            self._f_obj.create_dataset(self._CHANNEL_DNAME, data=content)


    def _generate_channel_info(
            self,            
            ) -> None:
            """Generates channel info for Signal Plant

            Args:
                self.f_obj (obj): file obj. handle
                ch_names (list): List of channel names
                datacache_names (list, optional): List of channel names. If None names are generated using default values.
                unit_names (list, optional): List of physical unit names. If None names are generated using default values.

            Returns:
                self.f_obj (obj): file obj. handle
            """
            
            datacache_names = [self._DATACACHE_NAME.encode('UTF-8') for _ in self.column_names]

            # make a list of physical units
            if self.units is None:
                self.units = self._UNITS
            
            if isinstance(self.units, (tuple, list)):
                self.units = [item.encode('UTF-8') for item in self.units]
            elif isinstance(self.units, str):
                self.units = [self.units.encode('UTF-8')] * len(self.column_names)
            else:
                raise TypeError

            # Generate content
            content = list(zip(self.column_names, datacache_names, self.units))

            content = np.array(
                content,
                dtype=self.cfg.INFO_DTYPES,
                )    

            # add/append dataset
            if self._INFO_DNAME in self._f_obj:
                current_content = self._f_obj[self._INFO_DNAME][:]
                content = np.append(current_content, content)

                del self._f_obj[self._INFO_DNAME]
            
            self._f_obj.create_dataset(self._INFO_DNAME, data=content)

    def add_samples(
            self,
            darray: NumpyArray,            
            ):
        """_summary_

        Args:
            data_arr (_type_): ndarray of the same length as data.shape[1]

        Raises:
            ValueError: Incosistent shape of the input data.
        """
        # TODO: export json with fs, resolution and units
        # columns -> samples, rows -> channels
        darray = darray.transpose()

        # Only float32 supported by SignalPlant
        if not np.issubdtype(darray.dtype, np.float32):
            darray = darray.astype(np.float32) / self.factor

        # Create new dataset if not exists
        if not self._DATASET_DNAME in self._f_obj:
            self._f_obj.create_dataset(self._DATASET_DNAME, data=darray, shape=darray.shape, dtype=self.cfg.DATASET_DTYPE, chunks=True, maxshape=(darray.shape[0], None))            
            return
    
        # Check for data shape consistency, raise error if does not match
        if self._f_obj[self._DATASET_DNAME].shape[0] != darray.shape[0]:
            raise ValueError(
                f"""Inconsistent shape of the input data.
                Expected to be {self.f_obj[self._DATASET_DNAME].shape[0]}, 
                got {darray.shape[0]} instead."""
                )            

        # reshape hdf dataset
        self._f_obj[self._DATASET_DNAME].resize(
            self._f_obj[self._DATASET_DNAME].shape[1] + darray.shape[1],
            axis=1,
            )
                
        # append samples
        self._f_obj[self._DATASET_DNAME][:, -darray.shape[1]:] = darray 
        
    def add_marks(
        self,
        positions: Union[List, Tuple],
        groups: Union[List, Tuple],
        messages: Union[List, Tuple],
        ) -> None:

        """_summary_

        Args:
            start_sample (_type_): _description_
            end_sample (_type_): _description_
            group_id (bytes, optional): _description_. Defaults to ''.
            validity (float, optional): _description_. Defaults to 0.0.
            channel_id (bytes, optional): _description_. Defaults to ''.
            info (bytes, optional): _description_. Defaults to b'a'.
        """
        
        # TODO: add mutiple marks at once

        marks = list()
        for position, group, message in zip(positions, groups, messages):
            # filter out negative samples
            position = max(1, position)

            marks.append((
                int(position),
                int(position),
                group.encode('UTF-8'),
                1.0,
                self.column_names[0],
                message.encode('UTF-8')
            ))

        # create NumPy array
        content = np.array(marks, dtype=self.cfg.MARKS_DTYPES)

        if self._MARKS_DNAME in self._f_obj:           
            # remove old dataset and store the new one
            del self._f_obj[self._MARKS_DNAME]

        self._f_obj.create_dataset(self._MARKS_DNAME, data=content)
    