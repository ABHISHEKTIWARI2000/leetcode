class Solution:
    def finalPrices(self, prices: List[int]) -> List[int]:
        answer = prices[:]
        stack = []  # This will truly behave as a monotonic stack
        
        for i in range(len(prices) - 1, -1, -1):
            # Maintain the monotonic property: pop elements greater than current price
            while stack and stack[-1] > prices[i]:
                stack.pop()
            
            # If stack is not empty, the top element is our discount
            if stack:
                answer[i] = prices[i] - stack[-1]
                
            # Push the current price onto the stack
            stack.append(prices[i])
            
        return answer