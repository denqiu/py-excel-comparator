import numpy

from enum import Enum


class LetterType(Enum):
    UPPER_CASE = 64
    LOWER_CASE = 96


class NumAlphaConversions:
    """
    Author: Dennis Qiu <dennisqiu123@gmail.com>

    Uses base-26 system to:
    1: Convert a number to letters (like column letters in Excel).
    2: Convert letters back to numbers.

    Note: Excel has maximum of 16384 columns (both online and offline).
    """

    def __init__(self):
        self.base = 26

    def _offset(self, pow_indices) -> numpy.ndarray:
        """
        Returns pow_indices - 1.

        Inspired by n-= pow(26, i) and n - 1. Formerly returns indices + 1.

        Notes about indices + 1:
        1: Multiples like 727 had ZAZ when it should be AAZ. indices - (pow_indices - 1) solves issue.
        2: Managing multiples previously looked like this: alphabet_positions[are_multiples] -= 1.
        3: With indices + 1 as offset,
        727 wrongly output ZAZ in numpy.arange(675, 728).
        727 correctly output AAZ in numpy.arange(676, 728).
        727 correctly output AAZ in numpy.array([727]) or 727.
        4: Without multiple management (2), 727 consistently output ABZ in all inputs (3).
        """
        return pow_indices - 1

    def _append_alpha_output(self, not_stopping, outputs, alphabet_positions, letter_type: LetterType) -> numpy.ndarray:
        """
        Assigning numpy.char.add to outputs[not_stopping] did not prefix the new letter.

        numpy.where automatically applied mask to all arrays and prefixed the new letter.
        """
        return numpy.where(
            not_stopping,
            numpy.char.add(
                numpy.char.mod("%c", alphabet_positions + letter_type.value),
                outputs
            ),
            outputs
        )

    def _dict_alpha(self, letter_type: LetterType):
        """
        Maps letters of the alphabet to their respective indices.
        """
        alphabet = numpy.char.mod("%c", numpy.arange(self.base) + 1 + letter_type.value)
        return {alpha: shape[0] for shape, alpha in numpy.ndenumerate(alphabet)}

    def alpha_to_num(self, alphas, letter_type: LetterType):
        """
        In progress.

        TODO: See what empty strings and non-alpha strings are converted to.
        """
        if numpy.isscalar(alphas):
            alphas = numpy.array([alphas])
        outputs = numpy.repeat(0, repeats=alphas.shape[0])
        pow_indices = numpy.repeat(0, repeats=alphas.shape[0])
        not_stopping = numpy.repeat(True, repeats=alphas.shape[0])
        alpha_lengths = numpy.char.str_len(alphas)

        while not_stopping.any():
            # $r += pow(26, $i) *(ord($a[$l - $i - 1]) - 0x40);
            outputs = numpy.where(
                not_stopping,
                outputs + numpy.power(self.base, pow_indices) * numpy.char.mod(
                    "%d", numpy.vectorize(lambda alpha, index: alpha[index])(
                        alphas, alpha_lengths - pow_indices - 1) - letter_type.value),
                outputs
            )
            not_stopping = pow_indices < alpha_lengths
            pow_indices[not_stopping] += 1
        outputs -= 1
        return outputs

    def _pre_process_indices(self, indices) -> numpy.ndarray:
        if numpy.isscalar(indices):
            # Convert to array because masks don't work on individual numbers.
            # They only work with arrays.
            indices = numpy.array([indices])
        if numpy.issubdtype(indices.dtype, float):
            indices = indices.astype(int)
        return indices

    def slow_num_to_alpha(self, indices, letter_type: LetterType):
        """
        Stack overflow solution translated to numpy.

        This is too slow.

        Returns (outputs, pow_indices).
        """
        indices = self._pre_process_indices(indices)
        outputs = numpy.repeat('', repeats=indices.shape[0])
        pow_indices = numpy.repeat(0, repeats=indices.shape[0])
        not_stopping = numpy.repeat(True, repeats=indices.shape[0])

        # Ignore negative indices.
        not_stopping[indices < 0] = False

        while not_stopping.any():
            alphabet_positions = numpy.where(
                not_stopping,
                numpy.remainder(
                    indices + 1,
                    # self._offset(indices, pow_indices),
                    numpy.power(self.base, pow_indices + 1)
                ) // numpy.power(self.base, pow_indices),
                -1
            )
            alphabet_positions[alphabet_positions == 0] = self.base
            outputs = self._append_alpha_output(not_stopping, outputs, alphabet_positions, letter_type)
            indices = numpy.where(
                not_stopping,
                indices - numpy.power(self.base, pow_indices + 1),
                indices
            )
            not_stopping = indices >= 0
        return (
            outputs,
            pow_indices
        )

    def _find_affected_array_indices(self, adjust_alpha: bool, sum_pow: numpy.ndarray, array_indices: numpy.ndarray,
                                     indices: numpy.ndarray, pow_indices: numpy.ndarray) -> numpy.ndarray:
        """
        SUMMARY
        1: Find affected indices based on power index.

        2: Take action to stop power increment or adjust alphabet position.

        FOR DEBUGGING
        1: Comment/uncomment line at the top to compare output before/after fix.

        2: Comment/uncomment 3 lines to see searched indices and pow_indices.

        NOTES (P[n] is short for power index at some n)
        Correct, 0-24 (A-Y), pow index=0
        Wrong, 25 (ZZ), should be Z, pow index=1 (should be 0), stop Z-P0

        Correct, 26-675 (AA-YZ), pow index=1
        Wrong, 676 (ZZA), should be ZA, pow index=2 (should be 1), stop Z-P1
        Wrong, 677-701 (AZB-AZZ), should be ZB-ZZ, pow index=2 (should be 1), range[1-25], stop Z-P1
        ...repeat for each multiple(26, 2)

        Correct, 702-1352 (AAA-AZA), pow index=2
        Wrong, 1353-1377 (BZB-BZZ), should be AZB-AZZ, pow index=2, range[1-25], alpha Z-P1

        Correct, 1378-2028 (BAA-BZA), pow index=2
        Wrong, 2029-2053 (CZB-CZZ), should be BZB-BZZ, pow index=2, range[1-25], alpha Z-P1
        ...repeat until 17576, which is pow(26, 3)

        Correct, 17576 (YZA), pow index=2
        Wrong, 17577-17601 (ZZZB-AZZZ) should be YZB-YZZ, pow index=3 (should be 2), range[1-25], alpha Z-P1, stop Z-P2
        Wrong, 17602-18252 (AZAA-AZZA) should be ZAA-ZZA, pow index=3 (should be 2), range[26-676], stop Z-P2
        Wrong, 18253-18277 (AAZB-AAZZ) should be ZZB-ZZZ, pow index=3 (should be 2), range[1-25], alpha Z-P1, stop Z-P2
        TOTAL: Wrong, 17577-18277, range[1-(676+25)], stop Z-P2

        Correct, 18278-18928 (AAAA-AAZA), pow index=3
        Wrong, 18929-18953 (ABZB-ABZZ) should be AAZB-AAZZ, pow index=3, range[1-25], alpha Z-P1

        Correct, 18954-19604 (ABAA-ABZA), pow index=3
        Wrong, 19605-19629 (ACZB-ACZZ) should be ABZB-ABZZ, pow index=3, range[1-25], alpha Z-P1

        Correct, 19630-20280 (ACAA-ACZA), pow index=3
        Wrong, 20281-20305 (ADZB-ADZZ) should be ACZB-ACZZ, pow index=3, range[1-25], alpha Z-P1
        ...repeat until 35152, which is pow(26, 3) * 2

        Correct, 35152 (AYZA), pow index=3
        Wrong, 35153 (AZZB) should be AYZB, pow index=3, alpha Z-P1
        Wrong, 35154-35177 (BZZC-BZZZ) should be AYZC-AYZZ, pow index=3, range[2-25], alpha Z-P1, alpha Z-P2
        Wrong, 35178-35828 (BZAA-BZZA) should be AZAA-AZZA, pow index=3, range[26-676], alpha Z-P2
        Wrong, 35829-35853 (BAZB-BAZZ) should be AZZB-AZZZ, pow index=3, range[1-25], alpha Z-P1, alpha Z-P2
        TOTAL: Wrong, 35154-35853, range[2-(676+25)], alpha Z-P2

        Correct, 35854-36504 (BAAA-BAZA), pow index=3
        Wrong, 36505-36529 (BBZB-BBZZ) should be BAZB-BAZZ, pow index=3, range[1-25], alpha Z-P1
        ...repeat until 52728, which is pow(26, 3) * 3

        Correct, 52728 (BYZA), pow index=3
        Wrong, 52729 (BZZB) should be BYZB, pow index=3, alpha Z-P1
        Wrong, 52730-52753 (CZZC-CZZZ) should be BYZC-BYZZ, pow index=3, range[2-25], alpha Z-P1, alpha Z-P2
        Wrong, 52754-53404 (CZAA-CZZA) should be BZAA-BZZA, pow index=3, range[26-676], alpha Z-P2
        Wrong, 53405-53429 (CAZB-CAZZ) should be BZZB-BZZZ, pow index=3, range[1-25], alpha Z-P1, alpha Z-P2
        TOTAL: Wrong, 52730-53429, range[2-(676+25)], alpha Z-P2
        ...repeat until 456976, which is pow(26, 4)

        Correct, 456976-475253 (YYZA-ZZZZ), pow index=3
        Wrong, 475254-475279 (AAAA-AAAZ) should be AAAAA-AAAAZ, pow index=3 (should be 4)
        FIX: Take sum of current and previous powers.
        Prior to fix, exclusive end range took the sum of current power and all previous powers.

        PATTERN
        offset = pow_index - 1
        inclusive start range = 1 if [adjust stop, multiple == power] else (1 + offset)
        exclusive end range = pow(26, pow_index) + pow(26, pow_index - 1)
        At Z-P0, stop 25=multiples(26, 1) + offset
        At Z-P1, stop 676, stop multiple(26, 2) + range[1-26], alpha multiples(26, 2) > power + range[1-26]
        At Z-P2, stop multiple(26, 3) + range[1-702], alpha multiples(26, 3) > power + range[2-702]
        """
        # Useful for debugging purposes to compare output before/after fix.
        # return []
        # boolean mask
        # 25=pow(26, 0+1) + (-1), 676=pow(26, 1+1) + (0)
        search_exact_numbers = numpy.logical_and.reduce([
            numpy.repeat(not adjust_alpha, repeats=indices.shape[0]),
            pow_indices <= 1,
            indices == numpy.power(self.base, pow_indices + 1) + self._offset(pow_indices)
        ])
        # Search for multiples, then figure out affected indices according to range.
        # boolean mask
        # %pow(26, 1+1) == 0, %pow(26, 2+1) == 0
        # Adjust alpha on multiples that are not exact powers of 26.
        # Adjust stop on multiples that are exact powers of 26.
        search_multiples = numpy.logical_and.reduce([
            pow_indices > 0,
            numpy.remainder(indices, numpy.power(self.base, pow_indices + 1)) == 0,
            numpy.isin(
                indices,
                invert=adjust_alpha,
                test_elements=[numpy.power(self.base, pow_indices + 1)]
            )
        ])
        # Useful for debugging purposes to see searched indices and powers.
        # searched_indices = indices[search_multiples]
        # searched_powers = pow_indices[search_multiples]
        # searched_sums = sum_pow[search_multiples]
        affected_non_multiples = []
        if search_multiples.any():
            # int array
            # +1 if multiple == power else +1+(1-1), +1+(2-1)
            inclusive_start_range = indices[search_multiples] + 1
            if adjust_alpha:
                inclusive_start_range += self._offset(pow_indices[search_multiples])

            # int array
            # +pow(26, 1), +pow(26, 2)+pow(26, 1)
            exclusive_end_range = indices[search_multiples] + sum_pow[search_multiples]

            # (From Gemini) Numpy equivalent of zip, range, and flatten functions combined.
            # Note: vectorize doesn't work.
            # int array
            affected_non_multiples = numpy.concatenate(numpy.frompyfunc(numpy.arange, nin=2, nout=1)(
                inclusive_start_range, exclusive_end_range
            ))
        # int array
        affected_indices = numpy.concatenate([indices[search_exact_numbers], affected_non_multiples])
        return array_indices[numpy.isin(indices, affected_indices)]

    def fast_alt_num_to_alpha(self, indices, letter_type: LetterType) -> tuple[numpy.ndarray, numpy.ndarray]:
        """
        OVERVIEW
        Ref: https://stackoverflow.com/a/57655623

        Returns (outputs, pow_indices).

        Alternate numpy translation of stack overflow solution. Doesn't subtract from indices.

        Indices can be a number or array-like of numbers. Decimals are converted to numbers.
        Negative numbers are not evaluated and have empty values.

        Equation: (index - (pow_index - 1) % pow(26, pow_index + 1)) // pow(26, pow_index)

        Stop condition: index - (pow_index - 1) < pow(26, pow_index + 1)

        Pow index: Index used to determine power.
        It also represents the letter position in the column (output) from right to left.

        ALGORITHM LOGIC
        1: There are 26 letters in the alphabet, A-Z.

        2: Determine alphabet positions depending on current power index.

        3: Repeat until stop condition is met for all indices.

        4: The alphabet position tells us the remainder value in base-26, from 1 to 25 (A to Y).
        0 is replaced with 26 for Z.

        EXAMPLE
        index = 1460
        pow index at 0 is 'E', [look forward] 1460 - (-1), (1461 % pow(26, 1)) // pow(26, 0)
        pow index at 1 is 'D', [look at self] 1460 - (0), (1460 % pow(26, 2)) // pow(26, 1)
        pow index at 2 is 'B', [look backward] 1460 - (1), (1459 % pow(26, 3)) // pow(26, 2)
        Column (output) = BDE
        """
        indices = self._pre_process_indices(indices)
        outputs = numpy.repeat('', repeats=indices.shape[0])
        pow_indices = numpy.repeat(0, repeats=indices.shape[0])
        not_stopping = numpy.repeat(True, repeats=indices.shape[0])
        sum_pow = pow_indices.copy()

        # Ignore negative indices.
        not_stopping[indices < 0] = False

        positive_indices = indices >= 0
        # Represents index position of each index number to be converted to letter.
        array_indices = numpy.arange(indices.shape[0])
        adjust_stop, adjust_alpha = ([], [])
        while not_stopping.any():
            alphabet_positions = numpy.where(
                not_stopping,
                numpy.remainder(
                    indices - self._offset(pow_indices), numpy.power(self.base, pow_indices + 1)
                ) // numpy.power(self.base, pow_indices),
                -1
            )
            alphabet_positions[adjust_alpha] -= 1
            alphabet_positions[numpy.logical_and(
                not_stopping,
                alphabet_positions <= 0
            )] += self.base
            outputs = self._append_alpha_output(not_stopping, outputs, alphabet_positions, letter_type)
            # Overall this logic works pretty well, except for where alphabet position is a Z.
            # It's easier to use another function to handle the Z's.
            not_stopping = numpy.logical_and(
                positive_indices,
                indices - self._offset(pow_indices) >= numpy.power(self.base, pow_indices + 1)
            )
            adjust_stop = self._find_affected_array_indices(
                False, sum_pow, array_indices, indices, pow_indices)
            adjust_alpha = self._find_affected_array_indices(
                True, sum_pow, array_indices, indices, pow_indices)
            not_stopping[adjust_stop] = False
            pow_indices[not_stopping] += 1

            sum_pow = numpy.where(
                not_stopping,
                sum_pow + numpy.power(self.base, pow_indices),
                sum_pow
            )
        return (
            outputs,
            pow_indices
        )
