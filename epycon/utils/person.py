import secrets
from datetime import datetime
from dateutil.relativedelta import relativedelta
from collections import OrderedDict


class Tokenize:
    def __init__(self, num_bytes, used_tokens):
        self.num_bytes = num_bytes
        self.used_tokens = used_tokens

    def __call__(self):
        token = secrets.token_hex(self.num_bytes)
        while token in self.used_tokens:
            token = secrets.token_hex(self.num_bytes)
        self.used_tokens[token] = {"sid": "", "procedure_date": ""}
        return token


class CzechPersonID:
    @staticmethod
    def _validate_sid(sid):
        try:
            sid = int(sid)
        except ValueError:
            raise ValueError(f"")
        
        if len(sid) >= 12 or len(sid) <= 8:
            raise ValueError(f"")

        return sid

    @staticmethod
    def _validate_sex(sid):
        """
        Returns persons sex based on personal id (currently for Czech ids)
        :return: (str): sex
        """
        valid_sex = 'male,female,none'.split(',')

        # is female
        if sid[2] in "5678":
            return valid_sex[1]

        # is male
        if sid[2] in "0123":
            return valid_sex[0]

        # is unidentified
        return valid_sex[2]

    @staticmethod
    def age(birth_date, datetime_ref):
        """
        Returns persons age relative to reference datetime obj
        :return: (int): age in years
        """
        raise NotImplementedError