import hashlib


def file_as_bytes(file):
    """file read"""
    with file:
        return file.read()


def file_md5sum(filepath):
    """ Usage file_md5sum(file_as_bytes(open(current_file, 'rb')))"""
    return hashlib.md5(file_as_bytes(open(filepath, 'rb'))).hexdigest()


def file_as_byte_md5sum(file_byte):
    return hashlib.md5(file_byte).hexdigest()
