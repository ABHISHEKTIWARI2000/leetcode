class Solution:
    def largestRectangleArea(self, heights: List[int]) -> int:
        stack = []
        answer = heights[0]
        heights.append(0)
        for i in range(len(heights)):

            while stack and heights[stack[-1]] > heights[i]:
                height = heights[stack.pop()]
                width = i if not stack else i - stack[-1] - 1
                answer = max(answer, height * width)
            stack.append(i) 
            # print(stack)
        return answer