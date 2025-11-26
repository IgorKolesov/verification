from typing import List, Tuple, Any


RangeRecord = Tuple[int, int, Any]  # (start, end, owner)


class Memory:
    @staticmethod
    def is_contained(ranges: List[RangeRecord], start: int, end: int) -> bool:
        for s, e, _ in ranges:
            if start >= s and end <= e:
                return True
        return False

    @staticmethod
    def ranges_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
        return not (a_end < b_start or a_start > b_end)

    @staticmethod
    def check_conflict(ranges: List[RangeRecord], start: int, end: int, owner, ignore_none: bool = False) -> bool:
        for s, e, o in ranges:
            if o is owner:
                continue
            if ignore_none and o is None:
                continue
            if Memory.ranges_overlap(start, end, s, e):
                return True
        return False

    @staticmethod
    def allocate(ranges: List[RangeRecord], start: int, end: int, owner: Any, ignore_none: bool = False) -> bool:
        if start > end:
            raise Exception(f"Invalid memory range: start ({start}) > end ({end})")

        for idx, (s, e, o) in enumerate(ranges):
            if s == start and e == end and o is None:
                ranges[idx] = (start, end, owner)
                return True

        if Memory.check_conflict(ranges, start, end, owner, ignore_none=ignore_none):
            raise Exception(f"Memory range conflict detected for [{start}, {end}]")

        ranges.append((start, end, owner))
        return True

    @staticmethod
    def release(ranges: List[RangeRecord], start: int, end: int) -> None:
        ranges[:] = [(s, e, o) for (s, e, o) in ranges if not (s == start and e == end)]

    @staticmethod   
    def free_owner(ranges: List[RangeRecord], start: int, end: int):
        for i, (s, e, o) in enumerate(ranges):
            if s == start and e == end:
                ranges[i] = (s, e, None)
                return True
        return False
    