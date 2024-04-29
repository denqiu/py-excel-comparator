import numpy


class Adjacent:
    def count_adjacent_elements(self, data: numpy.ndarray):
        """
        1: Find positions of the last matching adjacent elements.

        2: We can assume that elements at current and previous positions (adjacent elements) don't match.
        Therefore, we can calculate counts of adjacent elements.

        3: This works on data that contains at least 2 sets of adjacents elements sharing the same element.
        Example: ['a', 'a', 'a', 'b', 'b', 'a', 'c', 'c', 'd' ,'d']
        a - 3
        b - 2
        a - 1
        c - 2
        d - 2
        """
        # Find where elements don't match. Then add the last position.
        indices_last_match = numpy.concatenate([numpy.where(data[:-1] != data[1:])[0], [data.shape[0] - 1]])
        prev_indices = numpy.concatenate([numpy.array([-1]), indices_last_match[:-1]])
        elements = data[indices_last_match]
        counts = indices_last_match - prev_indices
        return (
            elements,
            counts
        )
