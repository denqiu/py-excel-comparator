import os
import logging
import unittest

import numpy

from utils.num_alpha_conversions import NumAlphaConversions, LetterType
from load_comparators import files_directory

logging.basicConfig(level=logging.INFO)


class TestNumAlpha(unittest.TestCase):
    def __init__(self, methodName="test"):
        super().__init__(methodName=methodName)
        self.tester = NumAlphaConversions()
    
    def _write_alpha_output(self, func, indices, letter_type: LetterType):
        outputs, pow_indices = func(indices, letter_type)
        test_completed = numpy.char.add(numpy.char.add(indices.astype(str), ' - '), outputs)
        test_completed = numpy.char.add(numpy.char.add(test_completed, ' - '), pow_indices.astype(str))
        with open(os.path.join(files_directory, f"output_{func.__name__}.txt"), 'w') as f:
            f.writelines("\n".join(test_completed))

    @unittest.skip(reason="Slow. Don't need to use timer.")
    def test_slow_num_to_alpha(self):
        # indices = numpy.array([26, 27])
        # indices = numpy.arange(675, 728)
        # indices = numpy.arange(676, 728)
        # indices = numpy.arange(10000)
        # indices = numpy.arange(pow(self.tester.base, 2))
        indices = numpy.arange(pow(self.tester.base, 3) * 4)
        self._write_alpha_output(self.tester.slow_num_to_alpha, indices, LetterType.UPPER_CASE)

    def test_fast_alt_num_to_alpha(self):
        # indices = numpy.arange(675, 728)
        # indices = numpy.arange(676, 728)
        # indices = numpy.arange(10000)
        # indices = numpy.arange(pow(self.tester.base, 3) * 4)
        # indices = numpy.arange(pow(self.tester.base, 3), pow(tester.base, 4) * 2)
        indices = numpy.arange(pow(self.tester.base, 4) * 4)
        self._write_alpha_output(self.tester.fast_alt_num_to_alpha, indices, LetterType.UPPER_CASE)

    def TODO_test_alpha_output(self):
        """
        Check letter alignment (A-Z) to determine whether output is correct or not.
        """
        indices = numpy.arange(pow(self.tester.base, 4) * 4)
        outputs, pow_indices = self.tester.fast_alt_num_to_alpha(indices, LetterType.UPPER_CASE)


if __name__ == '__main__':
    unittest.main()
