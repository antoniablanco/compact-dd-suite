import numpy as np
from bitarray import bitarray


def pack_bitarrays(states: list[bitarray]) -> np.ndarray:
    '''
    Packs bitarrays of the same length into a matrix with one row of bytes per state, so a whole
    layer can be compared with a mask at once.

    Parameters:
    - states (list[bitarray]): The states to pack, in layer order.

    Returns:
    - np.ndarray: A (len(states), bytes per state) uint8 matrix.
    '''
    if not states:
        return np.zeros((0, 0), dtype=np.uint8)
    return np.frombuffer(b"".join(state.tobytes() for state in states), dtype=np.uint8).reshape(len(states), -1)


def disjoint_positions(packed_states: np.ndarray, mask: bitarray) -> list[int]:
    '''
    Positions, in ascending order, of the packed states that share no bit with the mask.

    Parameters:
    - packed_states (np.ndarray): Matrix returned by pack_bitarrays.
    - mask (bitarray): A bitarray with the length of the packed states.

    Returns:
    - list[int]: The positions of the states disjoint from the mask.
    '''
    mask_bytes: np.ndarray = np.frombuffer(mask.tobytes(), dtype=np.uint8)
    columns: np.ndarray = np.flatnonzero(mask_bytes)
    if columns.size == 0 or packed_states.shape[0] == 0:
        return list(range(packed_states.shape[0]))
    shared: np.ndarray = (packed_states[:, columns] & mask_bytes[columns]).any(axis=1)
    return np.flatnonzero(~shared).tolist()
