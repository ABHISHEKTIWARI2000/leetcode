class Solution:
    def exclusiveTime(self, n: int, logs: List[str]) -> List[int]:
        execution = []
        total_time = [0]*n
        curr_time = 0
        for data in logs:
            curr_data = [int(x) if x.isnumeric() else x for x in data.split(":")]
            if curr_data[1] == 'start':
                if execution:
                    total_time[execution[-1][0]] += curr_data[2] - curr_time
                    curr_time = curr_data[2]
                execution.append(curr_data)
            else:
                total_time[execution[-1][0]] += curr_data[2] - curr_time + 1
                curr_time = curr_data[2] + 1
                execution.pop()

        return total_time
