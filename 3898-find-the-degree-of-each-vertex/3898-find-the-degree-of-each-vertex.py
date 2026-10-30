class Solution:
    def findDegrees(self, matrix: list[list[int]]) -> list[int]:
        n = len(matrix)
        ans = [0]*n
        nodeNo = 0
        for node in matrix:
            deg = 0
            for edge in node:
                if edge == 1:
                    deg += 1
            ans[nodeNo] = deg
            nodeNo += 1
        return ans
