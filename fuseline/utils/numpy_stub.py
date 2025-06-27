class NDArray(list):
    pass

# Alias commonly used lowercase name
ndarray = NDArray

def array(iterable):
    return NDArray(iterable)
