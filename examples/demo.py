
from epycon.iou.parsers import (
    LogParser,
)

file_path = ""

# Example usage for reading entire file:
with LogParser(file_path, start=0, end=2500) as parser:
    data = parser.read()
    # Access parsed data from parsed_data variable


with LogParser(file_path, start=0, end=2500) as parser:
    for chunk in parser:
        print(chunk.shape)
    # Access parsed data from parsed_data variable
    # TODO: write test: start < 0, end > file size, combinations
        

# Example usage for reading entire file:
# with LogParser(file_path, start=0, end=2500) as parser:
#     data = parser.read()

    # Access parsed data from parsed_data variable

# def _mount_data():
#     if self.lead:                                        
#         # mount bipolar channel
#         chunk[:, self._mount_posidx] = chunk[:, self._mount_posidx] - chunk[:, self._mount_negidx]
#         return np.transpose(chunk[:, self._channel_mapping])
#     else:
#         # TODO: duplacated unipolar singals in self._channel_mapping in case of HD-G
#         return np.transpose(chunk)
        