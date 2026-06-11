from .kakasi import convert as convert_kakasi
from .fugashi import convert as convert_fugashi

__BACKEND = 'kakasi'

def set_backend(new_backend):
  global __BACKEND
  __BACKEND = new_backend

def convert(text):
    if __BACKEND == 'kakasi':
        return convert_kakasi(text)
    elif __BACKEND == 'fugashi':
        return convert_fugashi(text)
    raise Exception(f'unknown backend {BACKEND}')
